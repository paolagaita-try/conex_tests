---
name: bonita-construir-proceso
description: Úsala cuando la unidad del claim construya el esqueleto de un proceso (en v1, dentro de U1 «Datos, organización y procesos», la unidad que genera). Lee bpmn.md (pools, lanes, tareas, compuertas, eventos, transiciones, process variables), escribe las condiciones en expresiones.md y los caminos del journey en caminos.md, genera el .proc y su .conf con tools/arnes.sh generar y prueba cada camino de compuerta por REST API, sin UI, hasta su evento de fin.
---

# Construir el proceso

Componente del loop (`bonita-construir-unidad`). Produce `bonita-project/app/diagrams/<Pool>-<versión>.proc` (XMI con
su diagrama, `bonitaModelVersion="9"`), su `process_configurations/<id del pool>.conf` (actor mapping y parámetros de
Local) y el journey `journey/<nombre>.postman_collection.json`. Todo es **generado**. Contratos y operaciones:
`bonita-construir-contratos-y-operaciones`; conectores: `bonita-construir-conectores`; pools llamados:
`bonita-construir-subproceso`. Antes de la primera `green`, lee
`../bonita-construir-unidad/references/generacion-de-una-pasada.md`.

**Dónde corre (v1):** dentro de `U1` «Datos, organización y procesos», la unidad que genera; `generar` es de una pasada y escribe a la vez BDM, organización, perfiles y todos los procesos. `U2` y `S-<subproceso>` están reservadas (no se proponen).

## Lo que lees: `docs/07-bonita/bpmn.md`

Plantilla `bpmn-bonita.template.md` de `trycore-spec-product-flow` (la copia fijada en `tests/fixtures/plantillas-flow/`
del arnés, que vigila la prueba de contrato), con lo que el lector exige además (marcado **[+]**; si falta, `generar` sale
2 nombrando la sección: añadirlo es editar `docs/07-bonita/`, así que para y pregunta, y anótalo como hueco del arnés,
`../bonita-construir-unidad/references/huecos-del-arnes.md`):

| Sección | Qué toma el generador |
|---|---|
| frontmatter | `pool` y `version` del pool principal (versión `1`, `1.0`, `2.1`…) |
| «Pool y lanes» | **[+]** una subsección por pool titulada «`Pool` versión»; la tabla de lanes (Lane, Actor, Grupo/rol, **Actor Bonita** opcional, Actor filter); **[+]** la línea **Iniciador** («`Actor`.» —actor de negocio o Actor Bonita de una lane— o «—» si lo instancia una call activity); la tabla opcional **Actor Bonita** (Nivel, Mapeo, Tareas, Filtro) directamente en la subsección del pool (ver «Lanes y actores») |
| «Inventario de tareas» › pool **[+]** | ID, Nombre, **Tipo Bonita** (`human`, `service`, `script`, `call activity`), Lane / actor, Contrato (`ctr_<id>` solo en las humanas), Conector, Operaciones previstas; **Notas** se vuelve la documentación del elemento (máximo 255 caracteres) |
| «Compuertas» › pool | Tipo (`exclusive (XOR)` o `parallel (AND)`), Después de, Variable que decide, **Salidas** («condición → `destino`» separadas por «; », **en orden de evaluación**, la de por defecto al final con «(por defecto)»), Salida por defecto |
| «Eventos» › pool | inicio `none`; fin `none` o `terminate` (R-12: `process:EndTerminatedEvent`; la doc 2026.2 `events.adoc` lo recomienda si el proceso tiene un solo fin); timer con posición «borde de `<tarea>` (interruptor)» o «… (no interruptor)» y su `param_*` como duración; Destino |
| «Transiciones» › pool | Desde, Hacia, **Condición** (el mismo texto que la salida de la compuerta; «(por defecto)»; «—» si no hay) |
| «Process variables» › pool | Variable, Tipo (`TEXT`, `BOOLEAN`, `INTEGER`, `LONG`, `DOUBLE`, `DECIMAL`, `DATE`, `LOCALDATE`, `LOCALDATETIME`, `OFFSETDATETIME`), Valor por defecto, Transitoria (`sí`/`no`) |
| «Documentos del proceso» › pool | una fila por documento (R-09): **Documento**, **Múltiple** (`sí`/`no`), **Atributo del BDM** opcional (el `LONG` que guarda su ID; lo escribe una operación posterior, nunca la instanciación: D-57) y **Tarea que lo aporta** (los contextos cuyos inputs `FILE` llevan «doc. `<documento>`», «(instanciación)» incluida); vacía si el proceso no tiene documentos. Formato y lo que genera: [`contratos-anidados-y-documentos.md`](../bonita-construir-contratos-y-operaciones/references/contratos-anidados-y-documentos.md) |

«Diagrama» (Mermaid) y «Verificaciones de diseño» no los lee: son para personas y para el gate de documentación. Los
`fin_*` salen de «Eventos» y de los destinos; compuertas y eventos sin lane van en la de su primer predecesor (el
borde, en la de su tarea; el inicio, en la del iniciador). Las business variables del pool principal salen de
`bdm.md › Decisión de persistencia`.

### Lanes y actores (R-02)

```markdown
| Lane | Actor (actores-proceso.md) | Grupo/rol (bdm.md → Organización) | Actor Bonita | Actor filter |
|---|---|---|---|---|
| Compras / Área Nacional | Compras | `/empresa/compras/nacional`; roles `Comprador`, `JefeCompras` | `compras` | `filtroCompradorDelCaso` |
| Sistema | Sistema | — | — | No aplica |

**Iniciador**: `Solicitante`.

| Actor Bonita | Nivel | Mapeo | Tareas | Filtro |
|---|---|---|---|---|
| `compras` | pool → lane Compras | `Comprador`, `JefeCompras` | (lane) | `filtroCompradorDelCaso` |
| `aprobadorMonto` | tarea | `JefeCompras` | `4_aprobarMonto` | — |
```

- **Actor Bonita** (columna opcional, **después** de la del actor de negocio): nombre del actor en el `.proc` y el
  `.conf`; su mapeo sale del actor de negocio de la fila (`bdm.md`). «—»: lane **sin actor**, solo si ninguna de sus
  tareas es humana (el actor de negocio va «— / —» en `bdm.md`). Sin la columna, el actor es el de negocio (como antes).
- **Grupo/rol**: los tokens de la ruta y los roles del actor, en cualquier orden; se comparan como conjunto con
  `bdm.md`.
- **Actor filter**: primer token, el filtro de las tareas humanas de la lane sin actor de tarea; «—» o «No aplica…»:
  ninguno. Lo declara y lo escribe `bonita-construir-conectores`.
- Tabla **Actor Bonita**: Nivel `pool…` es informativa (el nombre debe ser el Actor Bonita de alguna lane). Nivel
  `tarea`: un actor más del pool; Mapeo = roles (cualquier grupo) o membresías «`ruta` / `rol`», separados por «; »;
  Tareas = tareas **humanas** del pool, que lo toman con `overrideActorsOfTheLane="true"`; Filtro sustituye al de la
  lane. Una tarea, como mucho un actor de tarea.
- El iniciador del `.proc` es el Actor Bonita de la lane del evento de inicio.
- `check_inventario` (vía `inventario_organizacion`) compara lanes, actores del pool y actores de tarea con el `.proc`.

## Lo que escribes en `docs/08-construccion/`

**`expresiones.md`**: una fila por salida no por defecto de cada compuerta exclusiva, con ID `<compuerta>→<destino>`.
Copia la cabecera y la tabla del ejemplo `vacaciones` (`| ID | Origen | Huella | Groovy |`):

```markdown
| `gwXor_1→3_consultarSaldo` | bpmn.md › Transiciones › SolicitudVacaciones › gwXor_1→3_consultarSaldo › Condición (si aplica) | `652a7cea7b76` | `return resultadoJefe == "aprobar"` |
```

- **Origen**: `fichero › sección › pool › fila › columna`; la fila se busca por su primera celda o por «Desde→Hacia».
- **Huella**: los 12 primeros hexadecimales del sha1 del texto de origen con los espacios colapsados. Calcúlala:
  `python3 -c 'import sys; sys.path.insert(0, "tools/arnes"); from generadores.leer.construccion import huella; print(huella(sys.argv[1]))' 'resultadoJefe = aprobar'`.
  Si la documentación cambia, la huella deja de coincidir y `generar` da la nueva: revisa el Groovy antes de copiarla.
- **Groovy** (Bonita 2026.2): una sentencia por línea (`<br>` separa líneas), **ninguna línea empieza por un operador**
  (la línea que sigue a un `return x` y empieza por `+` o `&&` es código muerto silencioso), la última devuelve un
  booleano. Lee process variables y business variables por nombre (`saldo`, `solicitud.dias`); protege los nulos
  (`saldo != null && …`).
- Sin la fila, `generar` sale 2 con «falta en expresiones.md (ID «…», texto «…»)»: esa lista es tu lista de filas.

**`caminos.md`**: un camino por evento de fin del pool principal, y entre todos, cada salida de cada compuerta
exclusiva (`check_caminos` lo exige). Formato de cada camino (el del ejemplo):

```markdown
## Camino `sin_saldo`

**Fin esperado**: `fin_sin_saldo`

**Salidas cubiertas**: `gwXor_1→3_consultarSaldo`; `gwXor_2→fin_sin_saldo`

| Paso | Tarea | Usuario | Payload |
|---|---|---|---|
| 1 | (instanciación) | luis | `{"solicitudInput":{"dias":5,"fechaInicio":"2026-12-01"}}` |
| 2 | `2_revisarJefe` | carla | `{"decisionInput":{"resultado":"aprobar","comentario":"Aprobada"}}` |

| Atributo | Valor esperado |
|---|---|
| `solicitud.estado` | `sin_saldo` |
```

- **Tarea**: «(instanciación)», el ID de una tarea humana (también las de un pool llamado) o «(esperar `evTimer_1`)».
- **Usuario**: uno de `bdm.md › Organización`; el journey comprueba que la tarea está entre **sus** pendientes (actor
  mapping) antes de asignarla.
- **Payload**: JSON con los inputs del contrato; los obligatorios, siempre (lo valida `generar`). Los opcionales que
  falten los manda el journey a `null` (el motor exige todos, D-52).
- **Atributos esperados**: `<business variable>.<atributo>`; que cada camino deje un valor distinto (p. ej. `estado`)
  es lo que permite distinguir los caminos: los eventos de fin no se archivan en el runtime 11.1.0 y el journey deduce
  el fin del nodo previo completado.
- Los criterios Given/When/Then de las tareas `T-*.md` de la unidad se vuelven pasos y atributos esperados de un camino.
- **Formato ampliado (R-15, Plan 5)**: un camino también admite subida de archivos en el payload
  (`{"$archivo": "<nombre.ext>"}` en un input FILE), pasos negativos «(no ve `<tarea>`)» y
  «(denegado `MÉTODO ruta`)» con su lista de códigos (« [subscription]» lo omite en Community), **Correos esperados** y
  **Consultas esperadas** (varias filas del BDM). Para editar una fila que ya existe (un contrato con
  `persistenceId_string`), un texto del payload nombra la fila del caso: `{solicitud}`, `{modificacion[1]}` (n-ésima
  fila de una business variable múltiple), `{solicitud.documentos[1]}` (n-ésima de una relación) o `{caso}`; el journey
  pone su `persistenceId` antes de ejecutar la tarea. El formato exacto está en §2.14 de
  `docs/plan-5/contrato-de-formato.md` y la convención en `conocimiento/convenciones.md` › «Plan 5 — `journey`»; el
  ejemplo completo es `ejemplos/compras/docs/08-construccion/caminos.md` del arnés. El
  usuario de cada paso debe ser candidato de la tarea según `candidato()` (actor de tarea, varios roles, membresías
  extra y subgrupos). El journey busca el proceso y las tareas como ese usuario (`f=user_id`), igual que la bandeja:
  así pasa también con el dynamic check activo (D-75).

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | `expresiones.md` y `caminos.md` escritos; `tools/arnes.sh verificar` = 1 | `[check_inventario] <Pool>: falta en el .proc el pool que describe bpmn.md` (o los nodos y transiciones nuevos) y `[check_generados] …/<Pool>-<versión>.proc: falta…` |
| `green` | Cobertura de `ficheros` (pasada única); `tools/arnes.sh generar` = 0; `verificar` = 0 | `[check_inventario]`, `[check_expresiones]`, `[check_caminos]` y `[check_generados]` en verde |
| `refactor` | Limpiar `caminos.md` y `expresiones.md` sin cambiar el Groovy ni los payloads; `generar` sin diff | todo sigue verde |
| `smoke` | `tools/arnes.sh journey` (build `-Pbundle`, bundle en 8096, mock si hay `mock.json`, una carpeta por camino) | requests, assertions, fallos y caminos verdes |
| `api` | Los payloads de los caminos contra los contratos: `bonita-construir-contratos-y-operaciones` | su evidencia |
| `data` | Agente `bonita-verificador-datos` (operaciones contra `contratos.md`, atributos esperados contra `bdm.md`) | su informe |

Un camino solo: `tools/arnes.sh journey -- --folder preparación --folder <camino>` (la carpeta «preparación» comprueba
que los usuarios están en el perfil User, que mapeó `tools/arnes.sh perfiles`; va siempre primero). En el ejemplo
`vacaciones`, el journey completo da 85 requests y 108 assertions con 0 fallos (Community 2026.2-u0, tarea 13 del Plan 4).

## Wiring

Un item por camino y uno por condición de compuerta:

```json
[{"item_id": "CAM-aprobada", "kind": "camino", "ref": "docs/08-construccion/caminos.md#camino-aprobada"},
 {"item_id": "REG-gwXor_2-gwAnd_1", "kind": "regla", "ref": "docs/08-construccion/expresiones.md#expresiones"}]
```

`CAM-<camino>` pasa a `passing` con la salida verde de su carpeta del journey; `REG-<compuerta>-<destino>`, con la del
camino que cubre esa salida (y, por la salida por defecto, el camino que la cubre). Sin prueba ejecutada, `failing`.

| Gate | Evidencia |
|---|---|
| `tdd` | rojo: `verificar` → 1 con el pool o los nodos que faltan; verde: `generar` → 0, `verificar` → 0 |
| `journey_smoke` | `verificar` = 0; journey: requests / assertions / fallos y la lista de caminos verdes |

## Trampas

- **Sube la versión del pool** (frontmatter `version` y el título de cada subsección del pool) en cada cambio del
  proceso: con la misma versión el runtime sigue con la definición vieja. El `.proc` cambia de nombre; `generar` borra
  el anterior (lo lista en `build/generados.json`). Es un cambio de `docs/07-bonita/`: pregunta antes.
- **Orden de las salidas de un XOR**: gana la primera condición verdadera; la de por defecto va al final. El orden de
  la tabla de transiciones debe ser el de «Salidas» (si no, 2).
- **Un timer de borde solo cuelga de una tarea humana o de una call activity**; un borde interruptor sobre una rama
  que alimenta un join AND cuelga el caso y `generar` lo rechaza.
- **El journey espera un timer como máximo 60 s**: el valor Local del parámetro de su duración tiene que ser menor
  (en el ejemplo, 20 000 ms).
- IDs de nodo únicos dentro de su pool (los nombres también: el custodio compara por nombre).
- Las business variables solo existen en el pool principal; un pool llamado no escribe el BDM por variable.
- Lane: cualquier texto sin backticks ni «|» (`Analista / Líder de Proyectos SyP`); se compara literal con la celda
  «Lane / actor» de cada tarea.
- Una lane sin actor con una tarea humana, un actor de tarea sobre una tarea no humana o con un rol que no está en la
  organización, y un actor «— / —» usado por una lane con actor salen 2.
- `hola` desaparece con la primera generación; su colección ya no se usa en cuanto existe la del proyecto.

## Subscription

Nada del esqueleto es solo Subscription. El actor mapping y los parámetros de Qualification y Production van
embebidos en el `.proc` y se prueban construyendo (`bonita-construir-parametros-y-entornos`); su ejecución en esos
entornos, «pendiente de prueba en Subscription».

## Lo que el arnés no soporta (hueco, no se rodea)

`generar` sale 2 «no soportado» con: tareas `abstract`, `receive` o `send`; compuertas `inclusive`; eventos `message`,
`signal`, `error`, timer de inicio o intermedio y event subprocess; **multi-instancia** (el inventario no tiene dónde declararla). Sigue
`../bonita-construir-unidad/references/huecos-del-arnes.md`; ni se dibuja en el Studio ni se cambia la documentación
para esquivarlo.
