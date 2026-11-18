---
name: bonita-construir-unidad
description: Construye, continúa o cierra una unidad del plan de construcción Bonita (U0…U4, E-<familia>, S-<subproceso>, SUB) reclamada al hub. Conduce el loop de la unidad fase a fase (dor, change, red, green, refactor, smoke, api, data, dod, pr, archived) con slice-ops.sh, delega el trabajo de cada componente en las skills bonita-construir-*, la verificación en los agentes bonita-* y los changes en /opsx:*, y cierra cada gate con evidencia ejecutada. Úsala con /bonita:unidad, /bonita:work o /bonita:resume, o cuando haya que construir lo que dice docs/07-bonita/.
---

# Construir una unidad Bonita

Workflow maestro de **construcción**. Una unidad = una épica del hub = un change de OpenSpec = una rama = un PR que
incluye el archive. Esta skill **orquesta y delega**: el trabajo de cada componente lo explican las skills
`bonita-construir-*`, los cambios los conduce `/opsx:*` y los veredictos independientes los dan los agentes. Aquí se
secuencia y se reporta al hub.

> **¿Es un cambio pequeño y no una unidad?** Un claim con `work_type: micro_work`, una corrección o un ajuste sin
> capacidad nueva van por la skill `bonita-micro-cambio` (`/bonita:bugfix`, `/bonita:microwork`).

## Principio de operación

- **El hub es la fuente de verdad.** Fases, gates, wiring y checkpoints son suyos. Todo cambio de estado pasa por
  `.claude/hooks/bonita/slice-ops.sh` (aquí, `slice-ops.sh`): **una transición = una llamada**. Nunca armes peticiones
  a mano ni edites `.claude/state/` (es caché y cola) ni `.claude/hub-context/` (caché de solo lectura de los assets
  del hub).
- **Ramifica por el código de salida, no por el texto.** `0` sigue; `5` sigue y avisa; `6` para y muestra la razón del
  hub; `9` pide a la persona que registre este árbol. Tabla completa y casos (lease perdido, presupuesto agotado,
  grafo desfasado): `references/ciclo-en-el-hub.md`.
- **Una unidad activa a la vez.** Un gate no se salta. El journey nunca queda en rojo al cerrar una fase.
- **Divulgación progresiva.** Carga cada `references/<tema>.md` cuando la fase lo pida, no antes.
- **La documentación manda.** `docs/07-bonita/` es la fuente aprobada; un generado no se edita: se cambia la fuente y
  se regenera con `tools/arnes.sh generar`. Editar `docs/07-bonita/` es un punto de parada (pregunta antes).

## Paso 0 · Precondiciones

1. `trycore-bonita doctor` sale 0: eso solo dice que están los requisitos duros (Node, python3, git, openspec, JDK 17,
   Maven, newman, parent del pom). Si sale 1, arregla lo que diga o para y pregúntalo. **Lee además sus secciones**
   «Avisos» (marcadores sin resolver en el bloque de `CLAUDE.md` → `/bonita:onboard`; hooks sin bit ejecutable) y
   «Runtime (hub)» (`Credenciales: ✗ sin registrar` → registro, ver `references/ciclo-en-el-hub.md`; `Último contacto`
   sin red; `Grafo` por detrás). Esas líneas no cambian el código de salida.
2. El plan de unidades existe (`docs/08-construccion/plan.md`) y el ADMIN ya importó su grafo en el hub
   (`references/plan-de-unidades.md`). Si `slice-ops.sh status` no muestra proyecto o el claim da `7` en un proyecto
   recién creado, el grafo aún no está: dilo a la persona (lo importa el ADMIN, no tú) y para.

## Paso 1 · Reclamar

```bash
bash .claude/hooks/bonita/slice-ops.sh claim                    # la siguiente unidad lista
bash .claude/hooks/bonita/slice-ops.sh claim --unidad U1        # preferencia: el hub la honra si está lista
```

- `7` (204 del hub, sin trabajo): dilo en una línea y termina limpio. Si el texto es «otro agente tomó la tarea»,
  reclama **una** vez más.
- La salida dice `micro-work:` en vez de `unidad:` → no es una unidad: sigue la skill `bonita-micro-cambio`.
- `preferencia: … NO honrada` → el hub entregó otra unidad y dice por qué; trabaja la que entregó.
- Lee del claim: `unidad`, `fase`, `gates abiertos`, `rama` (la rama de trabajo de la unidad), `integración` (la
  rama de la que parte y contra la que va el PR), `change` (el nombre del change OpenSpec, ya resuelto: si el hub no
  lo trae, el claim lo deriva y lo marca `(derivado: el hub no lo trae)`),
  `docs` (`docs_ref`: rutas de `docs/07-bonita/`), `ficheros` (lo que la unidad puede tocar del proyecto, además de lo que escribe siempre: ver «Reglas duras») y `tareas`
  (`T-*.md` de `docs/04-tareas-proceso/`).
- **`CHECKPOINT:` presente → continúa desde ahí, jamás reinicies.** `git switch <rama>` del checkpoint, comprueba que
  `HEAD` es su commit o lo contiene, y sigue con `slice-ops.sh next-step`, que da la siguiente acción derivada del hub
  (resume hint → item de wiring en `failing` → primer gate abierto).

## Paso 2 · Rama y componentes

- Rama: la `rama` del claim, creada desde la de `integración` si no existe (`references/gitflow.md`).
- Qué skill de componente explica el trabajo de cada unidad. En v1 `tools/arnes.sh generar` es de **una pasada**
  (escribe BDM, organización, perfiles y todos los procesos a la vez:
  `references/generacion-de-una-pasada.md`), así que la unidad que genera es `U1` y reúne lo que el §6.2 del diseño
  repartía entre las unidades 1 y 2:

| Unidad | Skills de componente |
|---|---|
| `U0` plantilla configurada | `bonita-construir-plantilla` |
| `U1` datos, organización y procesos | `bonita-construir-bdm`, `bonita-construir-organizacion`, `bonita-construir-parametros-y-entornos`, `bonita-construir-proceso`, `bonita-construir-contratos-y-operaciones`, `bonita-construir-conectores` y, si hay pools llamados, `bonita-construir-subproceso` |
| `U2`, `S-<subproceso>` | **reservadas**: no se proponen en v1 mientras no haya generación por alcance (hueco conocido del arnés) |
| `U3` | `bonita-construir-parametros-y-entornos` (adaptador de parámetros), `bonita-construir-conectores`; la extensión de consultas se describe en su `README.md` |
| `U4`, `E-<familia>` | `bonita-construir-formularios` |
| `SUB` | aún sin skill de componente: lo que el arnés no soporta va a `references/huecos-del-arnes.md` |

Si el plan reparte distinto, manda la fila de la unidad en el plan: usa las skills de los componentes cuyos ficheros
están en su columna **Ficheros** y cuyas fuentes están en **Entrada**. Si esa fila no cubre todo lo que escribe
`generar`, es el hueco «generación por alcance» (`references/generacion-de-una-pasada.md`).

## Paso 3 · El loop de la unidad

**Al entrar en cada fase**, `slice-ops.sh phase <fase>` (idempotente; rellena la cadena que falte, el hub exige
orden estricto). **Al cerrar cada gate**, `slice-ops.sh gate <gate> pass --evidence-file evidencia/<unidad>/<gate>.md`
con la evidencia **ejecutada** (formato en `references/reporte.md`; `evidencia/` está fuera de git, créala con
`mkdir -p evidencia/<unidad>`). Tras cada fase, una nota
`slice-ops.sh progress «…»`; tras cada commit, `slice-ops.sh checkpoint --note «…»`.

| Fase | Qué haces | Delega en | Gate y evidencia |
|---|---|---|---|
| `dor` | Comprobar el DoR de la unidad (`references/dor.md`) | agente `bonita-gatekeeper-dor-dod` | `dor`: informe del gatekeeper |
| `change` | `/opsx:new <change>`; `proposal.md` con `## Trazabilidad` a `docs/07-bonita/` y a las tareas `T-*.md`; `openspec validate <change> --strict` | `/opsx:new`, agente `bonita-coherencia-unidad` | `coherence_link`: change ↔ `docs/07-bonita/` ↔ `docs_ref` de la unidad en el hub |
| `red` | Expectativas primero y fallando: casos del journey por camino de compuerta en `docs/08-construccion/caminos.md`, inventario esperado (lo que `docs/07-bonita/` declara), pruebas Spock si hay código propio. Sembrar el wiring | skill de componente | (abre `tdd`): `tools/arnes.sh verificar` = 1 nombrando lo nuevo; Spock en rojo |
| `green` | `tools/arnes.sh generar` y `mvn clean install -Pbundle` hasta que custodios y casos nuevos pasan | skill de componente | `tdd`: la salida roja y después la verde **de los mismos** casos y custodios |
| `refactor` | Limpiar `docs/08-construccion/` y el código propio sin cambiar comportamiento | — | todo sigue verde (`verificar` = 0, journey verde) |
| `smoke` | Journey completo, todos los caminos, contra el bundle: `tools/arnes.sh journey` | — | `journey_smoke`: `tools/arnes.sh verificar` = 0 y journey verde (requests, assertions, fallos); `fidelity`: formularios contra `matriz-formularios.md` o «no aplica: unidad sin formularios» |
| `api` | Contratos de proceso (los payloads del journey contra `contratos.md`) y, desde `U3`, REST API extensions | skill de componente | `api`: contratos y REST API probados |
| `data` | BDM y operaciones contra `bdm.md` y `contratos.md` | agente `bonita-verificador-datos` | `data`: informe del verificador de datos |
| `dod` | Loop del verificador (abajo) y después el DoD (`references/dod.md`) | agentes `bonita-verificador-adversarial` y `bonita-gatekeeper-dor-dod` | `wiring_verified` y luego `dod` |
| `pr` | PR con el archive dentro (Paso 4) | `/opsx:archive` | `slice-ops.sh submit` y `slice-ops.sh archive` |
| `archived` | La produce `slice-ops.sh archive`; reporte final | — | — |

Detalles que no caben en la tabla:

- **Un rojo válido es un rojo de expectativa**: `verificar` = 1 (hallazgos que nombran lo que falta) o una prueba que
  falla en su assertion. Un `2` (no se puede verificar) es un error de herramienta o de documentación, no un rojo: si
  dice «no soportado» o «el generador falla», sigue `references/huecos-del-arnes.md`. El journey no sirve como rojo
  cuando la colección de la unidad aún no existe (cae a la colección «hola»).
- **Gate que no aplica a la unidad** (`fidelity` sin formularios, `api` sin contratos ni REST API, `data` sin BDM ni
  operaciones): `pass` con la evidencia «no aplica: unidad sin …» y el porqué. Nunca `na` (el hub no lo admite) y nunca
  en silencio.
- **Wiring checklist** (fase `red`): `slice-ops.sh wiring seed --file evidencia/<unidad>/wiring.json` con un item por
  camino de `caminos.md` (`kind: camino`), por regla (constraint de `contratos.md` o condición de `expresiones.md`,
  `kind: regla`) y por integración (conector o REST API, `kind: integracion`); en `SUB`, uno por función solo de
  Subscription (`kind: subscription`). El hub exige al menos uno: si la unidad no tiene caminos, reglas ni
  integraciones propias (`U0`), siembra uno por criterio de su gate de salida (`references/dod.md`,
  `kind: salida`, p. ej. `SAL-U0-journey-hola`). Cada item nace `failing` y pasa con
  `slice-ops.sh wiring update <item_id> passing --evidence-file …` **solo tras una prueba real ejecutada**.
- **Subscription**: lo que solo se puede probar en Subscription nunca bloquea. En `SUB` son items de wiring; en el
  resto, la línea «pendiente de prueba en Subscription: …» dentro de la evidencia del gate.
- **Versión del pool**: cada cambio de proceso sube la versión del pool en `docs/07-bonita/bpmn.md`; si no, el runtime
  sigue con la definición anterior y el journey mide lo viejo.

### Loop del verificador (fase `dod`)

Máximo **2 pasadas** (`cycle_budget: 2` del proyecto en el hub; cada `fail` de un gate gasta una y un lease vencido
también). Cuando el presupuesto llega a 0, **el hub escala la unidad por su cuenta**: la pasada 2 (o cualquier
operación posterior) puede salir `6`. Entonces reporta lo que dice el hub y para; no reintentes.

1. **Pasada 1**: lanza `bonita-verificador-adversarial` con contexto virgen (no le pases tus conclusiones, solo la
   unidad, la rama y el wiring). Intenta refutar la unidad: stubs, caminos sin cablear, reglas sin prueba, items en
   `failing`; ejecuta `verificar`, el journey y una mutación. Con el árbol limpio (commitea antes). Informe en `evidencia/<unidad>/wiring_verified-pasada-1.md`. Sin hallazgos → `gate wiring_verified pass`.
2. Con hallazgos → `slice-ops.sh gate wiring_verified fail --evidence-file …`, corrige cada uno con prueba ejecutada y
   lanza la **pasada 2** (incremental: lo que cambió desde la pasada 1 y sus caminos gemelos), pasándole la ruta del informe de la pasada 1; escribe `wiring_verified-pasada-2.md` sin pisar el primero.
3. Si la pasada 2 aún encuentra algo: **no hay tercera**. `slice-ops.sh escalate --file … --gate wiring_verified` con
   los hallazgos y para: decide el equipo.
4. Con `wiring_verified` en `pass`, el gatekeeper comprueba el DoD (`references/dod.md`) y emite `gate dod`.

Un `fail` solo lo reporta un verificador independiente; un rojo propio del trabajo en curso no es un `fail` (no
gastes presupuesto: sigue trabajando, o escala si estás bloqueado).

## Paso 4 · Cierre

1. `slice-ops.sh phase pr`; push de la rama y `gh pr create` con la plantilla de `references/gitflow.md`.
2. `slice-ops.sh submit --pr-url <url> --openspec-change <change>` (el hub exige `dod` en `pass`).
3. `/opsx:archive <change>` en la misma rama: mueve el change al archivo, se commitea y se empuja **al mismo PR**, e
   invoca `slice-ops.sh archive`. Si no lo invocó o salió `5`, invócalo tú: es idempotente y va por la cola.
4. Reporte a la persona (`references/reporte.md`). El merge lo decide una persona.

## Paradas

Continúa sin preguntar mientras el siguiente paso sea el que da `slice-ops.sh next-step`. **Para y pregunta** solo ante
lo que dice el bloque del arnés en `CLAUDE.md`: acción irreversible, recortar o diferir alcance, editar
`docs/07-bonita/`, el generador no soporta un elemento (`references/huecos-del-arnes.md`), el hub rechaza (`6`). Y,
propias de esta skill: DoR no cumplido, presupuesto del verificador agotado, lease perdido, árbol sin registrar (`9`).

## Reglas duras

- **Producto completo.** El alcance de la unidad (su fila del plan, su `docs_ref`, sus tareas) se construye entero.
  Recortar o diferir es un bloqueo explícito (`slice-ops.sh escalate`), nunca una decisión del modelo.
- **Evidencia ejecutada, no por inspección.** Ningún `pass` ni `passing` sin la salida de un comando que lo pruebe.
- **Lo que la unidad puede escribir.** Siempre: la carpeta de su change (`openspec/changes/<change>/` y, al archivar,
  `openspec/changes/archive/`), `docs/08-construccion/` (caminos, expresiones, consultas, huecos del arnés) y
  `evidencia/<unidad>/` (fuera de git). Todo lo demás, solo dentro de los `ficheros` del claim; si hace falta otro
  fichero, escala.
- **Dudas sobre Bonita**: MCP `bonita-doc-index`; si no está conectado, marca «[no verificado]». Las convenciones del
  arnés están en `tools/arnes/conocimiento/` (`conocimiento/convenciones.md`, `conocimiento/patrones-bonita.md`).
- **El agente no gobierna.** No importa el grafo, no aprueba propuestas, no mergea: prepara, propone y reporta.
