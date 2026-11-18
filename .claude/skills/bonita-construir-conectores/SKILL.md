---
name: bonita-construir-conectores
description: Úsala cuando la unidad del claim construya un conector de una tarea (REST GET contra un mock, o un conector propio del proyecto como el correo) o un actor filter propio (en v1 dentro de U1 «Datos, organización y procesos»; el servicio real es de U3). Lee bpmn.md › Conectores por tarea y bdm.md › Organización › Actor filter, escribe el Groovy de las entradas en expresiones.md, el .def/.impl y la clase del filtro o conector en bonita-project/extensions/<modulo>/ (lo registra con herramientas/registrar_extension.py), genera con tools/arnes.sh generar y lo prueba con el journey.
---

# Construir conectores

Componente del loop (`bonita-construir-unidad`). Un conector va **dentro** del `.proc` del pool (lo escribe la misma
pasada que el proceso: `../bonita-construir-unidad/references/generacion-de-una-pasada.md`), con su
`definitionMapping` en el `.conf` y en las configuraciones embebidas. En `U1` apunta a un **mock** local; contra el
servicio real se prueba en `U3` (integraciones).

**Dónde corre (v1):** dentro de `U1` «Datos, organización y procesos», la unidad que genera; `generar` es de una pasada y escribe a la vez BDM, organización, perfiles y todos los procesos. `U2` y `S-<subproceso>` están reservadas (no se proponen).

## Lo que lees

| Fuente | Qué toma el generador |
|---|---|
| `bpmn.md` § «Inventario de tareas» › pool | la columna Conector de la tarea («`conn_x`»); debe coincidir con la tabla de conectores |
| `bpmn.md` § «Conectores por tarea» › pool | **Una fila por invocación**, en el orden de ejecución (el mismo conector puede ir en varias tareas y varias veces en una tarea). **Conector**: «`conn_x` (REST GET)» o «`conn_x` (propio `<definitionId>`)»; **Modo**: «síncrono» (único valor); **Momento**: «entrada» u «salida» de la tarea; **Entrada**: REST GET, el texto de la URL (ID `conn_x.url`) o «`url` ← `texto` (`<ID>`)»; propio, «`entrada` ← `texto` (`<ID>`)» separadas por «; », una por input del `.def` (los obligatorios, todos), con ID `conn_x.<tarea>.<entrada>` o, si la tarea lo invoca varias veces, `conn_x.<tarea>.<n>.<entrada>`; **Salida (destino)**: «`destino` ← `campo`» (REST GET, ruta del JSON) o «`destino` ← `salida`» (propio, output del `.def`), con `destino` = `Objeto.atributo` o `pv variable`; **Manejo de fallo**: `IGNORE` → el caso sigue aunque falle; otro texto → fallo visible; `THROW ERROR` no se genera |
| `bdm.md` § «Organización», tabla «Actor filter» | **Actor filter** (ID), **Tarea que asigna** (las tareas a las que `bpmn.md` lo aplica, en todos los pools), **Definición** (`definitionId` del `.def`), **Entradas** «`entrada` ← `texto` (`flt_<filtro>.<entrada>`)». El filtro se aplica en `bpmn.md` desde la columna «Actor filter» de la lane o desde un actor de nivel tarea (`bonita-construir-proceso`) |
| `bonita-project/extensions/<modulo>/src/main/resources-filtered/` | el `.def` (id, versión, `<input>` con `type` y `mandatory`, `<output>`) y el `.impl` (implementación y versión) de cada filtro o conector propio, con los `${…}` de las `<properties>` del pom del módulo |
| `contratos.md` § «Operaciones de tareas de servicio y script» | en la fila de la tarea, **Conector** = el conjunto de sus conectores (`conn_a`, `conn_b`); «Escribe» y «Process variables» incluyen lo que escriben sus salidas |
| `bdm.md` § «Parámetros» | el `param_*` de la URL base o del servidor (`param_smtpHost`, `param_smtpPuerto`): técnicos por entorno, Local apunta al mock o al SMTP de prueba |
| `docs/02-flujo-proceso/catalogo-conectores.md` | qué servicio es, su contrato de negocio y sus escenarios (para el mock y, en `U3`, para el real) |

El inventario de tareas (columna «Conector / comunicación») nombra el **conjunto** de conectores de la tarea
(`conn_correo` aunque la invoque dos veces). «Asíncrono» no es un modo técnico: `generar` sale 2 y dice que se
escriba «síncrono» con `IGNORE`. Si la documentación dice otra cosa, `generar` sale 2: hueco
(`../bonita-construir-unidad/references/huecos-del-arnes.md`).

## Lo que escribes

**Fila de `docs/08-construccion/expresiones.md`** con ID `conn_x.url` (formato y reglas de Groovy en
`bonita-construir-proceso`). La URL **siempre** desde un parámetro, nunca literal:

```markdown
| `conn_saldo.url` | bpmn.md › Conectores por tarea › SolicitudVacaciones › 3_consultarSaldo › Entrada (process variable o atributo) | `7af8102aae01` | `return param_urlSaldo + "/" + solicitud.empleado` |
```

**Conector o filtro propio** (el arnés no genera su código): un módulo en `bonita-project/extensions/<modulo>/` con
el arquetipo de Bonita (`connector-archetype.adoc`, `actor-filter-archetype.adoc`), escrito a mano:

- `pom.xml` con padre `<nombre>-extensions`, `<properties>` `definition-id`, `definition-version`, `impl-id`,
  `impl-version`, `impl-main-class`, las dependencias del motor (`org.bonitasoft.engine`) y de Groovy en `provided`, y
  `src/main/resources-filtered` como recurso con `filtering`.
- `<definicion>.def` (inputs con `type` y `mandatory`, outputs) y `<definicion>.impl` con
  `<jarDependency>${project.artifactId}-${project.version}.jar</jarDependency>`: así el motor carga la clase (D-41).
- La clase: un filtro extiende `AbstractUserFilter` (`filter(actorName)` devuelve los IDs de usuario); un conector,
  `AbstractConnector` (`executeBusinessLogic()`). Ejemplos: `ejemplos/compras/bonita-project/extensions/compras-filtros/`
  (`usuario-del-caso`) y `…/compras-correo/` (`correo-smtp`, cliente SMTP mínimo sobre `java.net.Socket`).
- `python3 tools/arnes/herramientas/registrar_extension.py . <modulo>` (o la ruta del arnés instalado): añade el
  módulo a `extensions/pom.xml` y la dependencia a `app/pom.xml`. Idempotente.

Un `.def` puede servir a varios filtros o invocaciones. Reintentos, activación por código o bitácora de envíos son
lógica del conector, no del arnés. Un filtro que devuelve la lista vacía deja la tarea en fallo (D-43): da un
respaldo en su Groovy de entrada si el dato puede faltar.

**`mock.json`** en la raíz del proyecto (lo arranca `tools/arnes.sh journey` en el puerto 8099, o `MOCK_PUERTO`; si el
plan no lo pone en los `ficheros` de la unidad, escala). Una entrada por petición que hacen los caminos; la clave es
«MÉTODO /ruta» exacta (sin query string) y lo que no está responde 404:

```json
{"GET /saldo/ana": {"status": 200, "json": {"saldo": 20}},
 "GET /saldo/luis": {"status": 200, "json": {"saldo": 2}}}
```

**`caminos.md`**: los datos del mock eligen el camino (en el ejemplo, `ana` va por `aprobada` con saldo 20 y `luis`
por `sin_saldo` con saldo 2); el atributo esperado que guarda la salida del conector (`solicitud.saldoConsultado`) es
la prueba de que llegó.

## Lo que hace el generador

- Tipo `rest-get` con la definición y la implementación de `tools/arnes/versiones/2026.2.json`; el conector REST no
  viene en el runtime: la dependencia Maven ya está en el pom de la plantilla.
- `definitionMappings type="CONNECTOR"` en mayúsculas (con minúsculas el `.bar` sale sin la implementación y el
  proceso no arranca).
- Momento «entrada» = `ON_ENTER`, «salida» = `ON_FINISH`. Un conector de entrada de una tarea de servicio escribe sus
  salidas **antes** de las operaciones de la tarea: una operación puede leer la salida (comprobado en el bundle).
- Cada salida se convierte con `as <Tipo>` según el tipo del destino (texto, entero, decimal, booleano…); un destino
  múltiple o de fecha no se admite.
- `ignoreErrors="false"` por defecto: si el servicio no responde, la tarea queda en fallo visible (se reintenta
  desde la administración); un 404 deja la salida en nulo y el flujo decide (protege los nulos en las condiciones).
  Con `IGNORE`, `ignoreErrors="true"`: la tarea termina y el caso sigue (D-45).
- Varias invocaciones en una tarea: primero las de «entrada», después las de «salida», cada grupo en el orden de la
  tabla (el motor las corre en ese orden, D-46); cada una se llama `conn_x` o, si se repite, `conn_x_1`, `conn_x_2`.
- Conector propio: ids y versiones de su `.def`/`.impl`; cada entrada con el `type` de su `<input>`; cada salida,
  una operación `outputs` desde el `<output>`. `definitionMappings type="CONNECTOR"`.
- Actor filter: un `process:ActorFilter` en cada tarea humana con filtro (el del actor de tarea o, si no, el de la
  lane; nunca en la lane), con sus entradas, y `definitionMappings type="ACTOR_FILTER"` (D-40). El filtro corre al
  crear la tarea, antes que sus conectores de entrada; con un solo candidato la autoasigna (D-43).
- `check_inventario` compara una fila de `bpmn.md` por invocación y el filtro de cada tarea humana con el `.proc`.

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Fila `conn_x.url`, `mock.json` y los caminos que pasan por el conector; `tools/arnes.sh verificar` = 1 | `[check_inventario]` / `[check_generados]` con la tarea o el `.proc` que faltan |
| `green` | `tools/arnes.sh generar` = 0; `verificar` = 0 | custodios en verde |
| `smoke` | `tools/arnes.sh journey` con el mock arrancado | cada camino que pasa por el conector, verde, con su atributo esperado |
| `api` | Lo del contrato de la tarea (`bonita-construir-contratos-y-operaciones`) | — |
| `data` | El verificador de datos comprueba que cada salida escribe su destino y nada más | su informe |

## Wiring

Un item `kind: integracion` por conector:

```json
[{"item_id": "INT-conn_saldo", "kind": "integracion", "ref": "docs/07-bonita/bpmn.md#conectores-por-tarea"}]
```

Pasa a `passing` con la salida verde de los caminos que lo atraviesan
(`tools/arnes.sh journey -- --folder preparación --folder aprobada --folder sin_saldo`). La evidencia dice que es
**contra un mock**: «probado contra `mock.json` (doble); el servicio real, en `U3`».

## Trampas

- Dos conectores casi gemelos: cada salida a **su** variable (copiar y pegar deja la del original).
- Las claves del JSON de la respuesta: solo identificadores (`a.b`), sin guiones ni índices de lista.
- El mock responde con `Content-Type: application/json`; el conector solo rellena el cuerpo como objeto con ese tipo.
- El conector REST no expone reintentos ni fallo por código HTTP; una API de Bonita como destino exige sesión.
- Puerto 8099 libre durante el journey.

## Subscription

Nada del conector REST, de los conectores propios ni de los actor filters propios es solo Subscription.

## Lo que el arnés no soporta (hueco, no se rodea)

Los conectores estándar de Bonita que no son REST GET (POST, PUT, correo estándar, SOAP…: escribe un conector
propio), el modo **asíncrono** (usa `IGNORE`), `THROW ERROR`, salidas JSON a destinos múltiples o de fecha y un
filtro o conector propio sin su `.def` en `extensions/`: `generar` sale 2 con el error de la fila. Sigue
`../bonita-construir-unidad/references/huecos-del-arnes.md`.
