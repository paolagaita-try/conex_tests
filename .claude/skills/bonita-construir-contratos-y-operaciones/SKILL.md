---
name: bonita-construir-contratos-y-operaciones
description: Úsala cuando la unidad del claim construya contratos (instanciación y tareas humanas, con sus constraints) u operaciones (lo que cada tarea escribe en el BDM y en las process variables), en v1 dentro de U1 «Datos, organización y procesos», también para los pools llamados. Lee contratos.md, escribe el Groovy de constraints y scripts en expresiones.md, genera con tools/arnes.sh generar y cierra el gate api con los payloads del journey y un rechazo por constraint contra el runtime.
---

# Construir contratos y operaciones

Componente del loop (`bonita-construir-unidad`). Contratos y operaciones van **dentro** del `.proc` de cada pool (lo
escribe la misma pasada que el proceso: `../bonita-construir-unidad/references/generacion-de-una-pasada.md`). En
Bonita el contrato es la interfaz pública del proceso; la operación, lo único que escribe datos al completar una tarea.

**Dónde corre (v1):** dentro de `U1` «Datos, organización y procesos», la unidad que genera; `generar` es de una pasada y escribe a la vez BDM, organización, perfiles y todos los procesos. `U2` y `S-<subproceso>` están reservadas (no se proponen).

## Lo que lees: `docs/07-bonita/contratos.md`

Plantilla `contratos-bonita.template.md` v0.8.0, con lo que el lector exige además (**[+]**; si falta, `generar` sale 2:
para y pregunta antes de tocar `docs/07-bonita/` y anótalo como hueco,
`../bonita-construir-unidad/references/huecos-del-arnes.md`):

| Sección | Qué toma el generador |
|---|---|
| «Contrato de instanciación» | **[+]** una subsección por pool titulada «`Pool` versión» (también con un solo pool); su tabla de inputs, su tabla de constraints y **una** línea que empieza por «Operaciones al instanciar:» y nombra la plantilla |
| «Contratos de tarea humana» | una subsección `ctr_<tarea>` por tarea humana con la línea **Tarea** (`bpmn.md`) y el ID entre comillas invertidas (más «(pool `X`)» si el ID se repite en dos pools), sus dos tablas y la línea **Operaciones** |
| «Operaciones de tareas de servicio y script» | por fila: Tarea, Conector, Operaciones (plantilla / literales), **Escribe** (debe ser lo que escriben sus operaciones y su conector), **Process variables** (ídem) |

«Matriz tarea ↔ contrato ↔ formulario» y «Cobertura de las reglas de validación de los AC» no los lee (son del gate de
documentación y de los formularios).

**Inputs** (columnas Input, Tipo, Múltiple, Obligatorio, Hijos, Destino): tipos `TEXT`, `INTEGER`, `DECIMAL`,
`BOOLEAN`, `DATE`, `COMPLEX`, `FILE`, `LONG`, `LOCALDATE`, `LOCALDATETIME`, `OFFSETDATETIME` (la plantilla v0.8.0 deja
como `[no verificado]` todo salvo `TEXT` y `COMPLEX`; el arnés los comprobó en el modelo EMF de 2026.2). Los hijos de
un `COMPLEX`: «nombre (TIPO, sí|no[, múltiple])» separados por «; », con obligatoriedad propia (si llega el padre, el
hijo no es nulo); un hijo `COMPLEX` lleva los suyos entre corchetes. La forma vieja «nombre (TIPO)» sigue valiendo y
hereda la obligatoriedad del padre. **Destino**: `Objeto.atributo`, `pv variable`, «doc. `documento`» (inputs `FILE`),
«op. `op_<ctx>.<bv>`» o «— (solo lectura)»; en un `COMPLEX`, «hijo → `destino`» por hijo. Todo input tiene destino de
tipo compatible (`TEXT` → `STRING`/`TEXT`, `DECIMAL` → `DOUBLE`/`FLOAT`, el resto igual). Detalle en
[`references/contratos-anidados-y-documentos.md`](references/contratos-anidados-y-documentos.md).

**Operaciones**, en el texto de la línea (siempre en una sola línea, en orden):

- la plantilla, «según plantilla `<nombre>`» (o «`<nombre>` / …» en la tabla de servicio): un nombre de la fila
  «Plantilla de persistencia» de `bdm.md › Decisión de persistencia`, que puede ser una **familia**
  («`persistirDesdeContrato` (tareas humanas); `persistirDesdeServicio` (servicio, script e instanciación)»);
- literales: «`Solicitud.estado` = `aprobada`»;
- scripts: «`Solicitud.numero` ← `"VAC-" + caseId` (`op_instanciacion.numero`)», con su marca
  `op_<tarea o instanciacion>.<atributo>` (sin marca, 2);
- scripts sobre la **business variable entera**: «`bv solicitud` ← `registra la solicitud…` (`op_instanciacion.solicitud`)»
  (abajo, «Persistencia por helpers»);
- los inputs con destino ya son operaciones y van antes que la línea (no se repiten aquí); un input que consume una
  operación entera lleva el destino «op. `op_<ctx>.<bv>`» y uno que solo lee una constraint, «— (solo lectura)» (los
  formatos de inputs anidados, destinos `op.`/`doc.` y documentos los explica
  [`references/contratos-anidados-y-documentos.md`](references/contratos-anidados-y-documentos.md)).

Una celda de Operaciones de servicio vacía («—», «— (sin escritura)») no tiene operaciones ni nombra plantilla.

## Persistencia por helpers (familia de plantillas, R-07 y R-08)

`asignacion-directa` es la única plantilla que el arnés conoce: una operación por atributo, sin helpers, y **no admite**
destinos `bv`. Cualquier otro nombre es una plantilla **del proyecto**: el arnés no la lee ni genera sus helpers, solo
escribe cada «`bv x` ← …» como un `ASSIGNMENT` sobre la variable entera con el Groovy de `expresiones.md`, tal cual.

| Pieza | Quién la escribe | Regla |
|---|---|---|
| Biblioteca de helpers (`bonita-project/extensions/<proyecto>-helpers/`, p. ej. `Persistencia.registrarSolicitud`) | tú, a mano, como `parametros-adaptador`: módulo del pom de extensiones y dependencia de `app/pom.xml` | Devuelve la business variable entera (el objeto o la lista). No nombra clases del BDM de forma estática: las crea por nombre con el cargador del objeto recibido o el del hilo (D-63). Recibe el DAO del script si lo necesita |
| Groovy de cada `op_<ctx>.<bv>` | tú, en `expresiones.md` | Una llamada al helper que devuelve la variable: `return com.empresa.compras.helpers.Persistencia.eventoNuevo(solicitud, "pagada", eventos)` |
| Operación `ASSIGNMENT` sobre la variable | `generar` | Una por variable y contexto; en la instanciación es el valor por defecto («entera primero, atributos después»; si el Groovy nombra la propia variable, vale `null`) |
| `<objeto>DAO` en el script (`solicitudDAO`, `eventoDAO`) | `generar` lo declara si el script lo usa | Solo de objetos con business variable en el pool. `newInstance(…)` del DAO recibe los atributos obligatorios en el orden del BDM (D-62) |

**Business variables** (`bdm.md`, fila «Business variables del pool»): «`solicitud: Solicitud`; `eventos: Evento`
(múltiple)». Una múltiple es `multiple="true"` en el `.proc`, su valor es una `java.util.List` y solo admite operaciones
enteras (D-60). Sin operación de instanciación no tiene valor por defecto; varias operaciones `bv` en la instanciación
crean varias variables, en el orden de `bdm.md` (la referenciada antes: D-61). Un agregado nuevo y quien lo referencia
pueden persistirse en la misma tarea si la línea crea el agregado primero (D-64). Los nombres de business y process
variables de un pool no pueden coincidir.

**«Escribe»** de servicio y script: lo que pertenece al objeto de una variable con operación entera es informativo
(vale el objeto solo, `` `Solicitud` ``); lo que escriben las operaciones por atributo y los conectores debe estar.

## Lo que escribes: filas de `docs/08-construccion/expresiones.md`

Mismo formato y reglas de Groovy que en `bonita-construir-proceso` (ID, Origen, Huella, Groovy):

| ID | Groovy debe… |
|---|---|
| `ctr_<instanciacion o tarea>.<constraint>` | devolver un booleano mirando **solo los inputs** del contrato (`solicitudInput.dias`), sin BDM ni conectores |
| `op_<instanciacion o tarea>.<atributo>` | devolver el valor del atributo destino, del tipo del atributo |
| `op_<instanciacion o tarea>.<business variable>` | devolver la business variable entera (el objeto, o la lista si es múltiple), normalmente con una llamada a la biblioteca de helpers |

Variables que el Groovy de proceso puede usar sin declararlas: `processInstanceId` y `apiAccessor` (doc 2026.2
`process/expressions-and-scripts.adoc`); las business variables y process variables del pool por su nombre; en
operaciones de tarea, los inputs del contrato. Lo que la documentación llama `caseId` es `processInstanceId`. Una API
Java nueva se comprueba en el MCP `bonita-doc-index` o se marca `[no verificado]` en la nota de `expresiones.md`.

## Lo que hace el generador

- Cada input obligatorio se vuelve una constraint `mandatory_<ruta>` (también los hijos); una constraint de la
  documentación con ese nombre se rechaza.
- Bonita no tiene operaciones de instanciación: las de `(instanciación)` se convierten en el valor inicial de la
  business variable (un script que crea el objeto desde el contrato).
- Dos operaciones que escriben el mismo destino en la misma tarea → 2.
- `check_inventario` compara inputs (con los hijos de los `COMPLEX`, por ruta y tipo) y constraints de `contratos.md`
  con cada `.proc`; `check_expresiones`, que cada constraint y script tenga su fila, con huella y origen correctos.

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Filas `ctr_…` y `op_…` en `expresiones.md`; `tools/arnes.sh verificar` = 1 | `[check_inventario]` con los inputs y constraints que faltan en el `.proc` (o, si el `.proc` aún no existe, el pool) |
| `green` | `tools/arnes.sh generar` = 0 y `verificar` = 0 | los mismos custodios en verde |
| `smoke` | `tools/arnes.sh journey`: cada paso de cada camino instancia (200) o ejecuta (204) contra el contrato real | requests, assertions, fallos |
| `api` | Los payloads del journey pasan el contrato y **cada constraint rechaza** un payload que la viola (abajo) | por constraint: payload, código 400 y el mensaje |
| `data` | Agente `bonita-verificador-datos`: cada operación igual a su plantilla (`asignacion-directa` salvo los literales declarados, o una llamada al helper de la plantilla del proyecto) y cada destino escrito como dice `contratos.md` | su informe |

### El rechazo de cada constraint (gate `api`, items `kind: regla`)

El journey solo prueba payloads válidos. Cada constraint se prueba además con uno que la viola, contra el runtime vivo
(`tools/arnes.sh journey --mantener` deja el bundle en `http://localhost:8096/bonita` y dice su carpeta):

```bash
B=http://localhost:8096/bonita
sesion() { J=$(mktemp); curl -s -o /dev/null -c "$J" -d "username=$1&password=$2&redirect=false" "$B/loginservice"
  T=$(curl -s -b "$J" -D - -o /dev/null "$B/API/system/session/unusedId" | awk -F': ' 'tolower($1)=="x-bonita-api-token"{print $2}' | tr -d '\r'); }
api() { curl -s -w '\n%{http_code}\n' -b "$J" -H "X-Bonita-API-Token: $T" -H 'Content-Type: application/json' "$@"; }
sesion ana bpm
ID=$(curl -s -b "$J" "$B/API/bpm/process?f=name=SolicitudVacaciones&f=version=1.0&p=0&c=1" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
api -d '{"solicitudInput":{"dias":45,"fechaInicio":"2026-12-01"}}' "$B/API/bpm/process/$ID/instantiation" > evidencia/U1/regla-dias_validos.txt
```

Para la constraint de una tarea: instancia con un payload válido, entra como su usuario, busca la tarea
(`GET $B/API/bpm/humanTask?f=caseId=<caso>&f=name=<Nombre de la tarea>`), asígnala
(`PUT $B/API/bpm/humanTask/<id>` con `{"assigned_id":"<user_id de la sesión>"}`) y ejecútala con el payload que viola
(`POST $B/API/bpm/userTask/<id>/execution`). Pasa si responde **400 y el cuerpo contiene el «Mensaje de error» de la
constraint** en `contratos.md`. Medido en el runtime 11.1.0: la ejecución de tarea responde
`ContractViolationException` con `explanations`, como la doc (`data/contracts-and-contexts.adoc`); la instanciación
responde `IllegalArgumentException` con el mensaje dentro de `message`. Después, para el bundle:
`(cd <carpeta> && bash stop-bonita.sh)`; si el puerto 8096 sigue ocupado al minuto, termina el proceso cuyo comando
contiene esa carpeta (es lo que hace `tools/run-journey.sh` al salir).

## Wiring

Un item `kind: regla` por constraint de `contratos.md` y uno por operación con script:

```json
[{"item_id": "REG-ctr_instanciacion-dias_validos", "kind": "regla", "ref": "docs/07-bonita/contratos.md#contrato-de-instanciación-ctr_instanciacion"},
 {"item_id": "REG-op_2_revisarJefe-estado", "kind": "regla", "ref": "docs/08-construccion/expresiones.md#expresiones"}]
```

Una constraint pasa con su rechazo (400 y mensaje) más un camino que la cumple; una operación, con el camino cuyo
atributo esperado lee lo que escribe (p. ej. `solicitud.estado` = `rechazada`).

| Gate | Evidencia |
|---|---|
| `api` | «payloads del journey: N pasos, 0 fallos» y una línea por constraint: payload → 400 → mensaje; REST API extensions: no aplica hasta `U3` |

## Trampas

- Una constraint **solo ve los inputs**: lo que necesita datos del BDM o de un servicio es validación de formulario o
  una tarea de servicio.
- Un cambio de contrato es un cambio de la interfaz pública: sube la versión del pool y revisa los payloads de
  `caminos.md` (si no, el journey falla con 400).
- Groovy: nunca una línea que empieza por operador; protege los nulos (`?: []`, `!= null`).
- Un `COMPLEX` múltiple llega como lista de mapas; un hijo `COMPLEX` anidado solo admite el destino entero de su raíz
  (`op.` o solo lectura).
- En la instanciación las operaciones no ven los documentos que inicializa el contrato (D-57): su ID lo guarda la
  primera tarea o una tarea script posterior; si el Groovy de una operación de instanciación nombra el documento,
  `generar` sale 2.
- El motor exige en el cuerpo todos los inputs del contrato, también los opcionales (D-52): el formulario generado y el
  journey los mandan a `null`.
- **Lo que la línea de operaciones dice en prosa y no es un literal ni un script marcado se ignora sin error** ("crea
  `Solicitud`" no genera nada por sí mismo). `check_inventario` no mira operaciones (sí las business variables y su
  multiplicidad): lo ven el verificador de datos y los atributos esperados de los caminos.
- El `newInstance()` sin argumentos de un DAO solo existe si el objeto no tiene atributos obligatorios (D-62): con
  obligatorios, `MissingMethodException` y la tarea queda en fallo.
- Un helper que nombra una clase del BDM con `import` compila contra el jar del BDM pero no la encuentra en el bundle
  (el jar va en `WEB-INF/lib`, padre del cargador del BDM): créala por nombre (D-63).

## Subscription

Nada de contratos ni operaciones es solo Subscription. La autorización dinámica de la REST API está desactivada en el
bundle del journey (`BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=false`): permisos por recurso, desde `U3`.

## Lo que el arnés no soporta (hueco, no se rodea)

- Que el arnés lea los literales de una plantilla del proyecto (`mapeoCampos`, `camposDecision`…) y genere los
  scripts: no lo hace (veredicto R-07); la plantilla vive en los helpers y el Groovy de `expresiones.md` los llama.
- Añadir a una lista sin reescribirla: la operación entera devuelve la lista completa (el helper la recompone).
