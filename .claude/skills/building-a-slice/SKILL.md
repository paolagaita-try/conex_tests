---
name: building-a-slice
description: Use when building, continuing, or shipping a product epic (EP-XXX) end to end — drives the fast inner-loop pipeline (DoR → OpenSpec change linked to its epic → TDD → journey-smoke → api/data → reduced DoD → PR+archive → ask for Release Gate) synchronizing agents through the Agent Orchestrator Runtime (slice-ops.sh) — or the local state file in legacy mode. Heavy reviews (security/design/UX/three-way coherence/architecture/integration) run once per release in the releasing-a-version skill, not per epic. The epic is the build unit; the HUs it covers are its internal scope. Delegates to opsx:* for changes and superpowers:test-driven-development for TDD; never reimplements them.
---

# Construir un slice (épica EP-XXX) — Build

Workflow maestro de **construcción**. Extiende la discovery de Trycore (que termina en flows)
hacia el código. **Orquesta y delega**: el motor de changes es `opsx:*`, el motor de tests es
`superpowers:test-driven-development`. Esta skill NO los reimplementa: los secuencia y registra
el avance en el estado.

> **Unidad de construcción: la épica (`EP-XXX`).** Un slice = una épica = un OpenSpec change = una
> rama = un PR. Las HU de la épica (que siguen viviendo en `docs/04-historias/`) son el **alcance
> interno** del change y se listan en `active_slice.hus[]`. Construir por HU suelta es sobre-ingeniería.

> **¿Mantenimiento, no producto nuevo?** Un typo, un bump de dependencia ya permitida, un ajuste de
> copy/config/docs o un fix de pocas líneas **sin nueva capacidad** NO abren una épica: usa la skill
> **`building-a-micro-change`** (carril ligero `fix/*`|`chore/*` → cambio → PR). Si aparece una
> **señal de forma** (dependencia nueva, API/endpoint nuevo, migración de datos), escala **aquí** y
> ábrelo como épica; si aparece una **señal de requisito** (un AC cambia o falta), vuelve a discovery.
> Entradas: `/build:bugfix` y `/build:microwork`.

## Principio de operación
- **Una sola fuente de verdad, según el modo**: pregunta primero
  `bash .claude/hooks/build/slice-ops.sh mode`. En `dual`/`runtime` el estado vive en el
  **Agent Orchestrator Runtime** y toda transición pasa por `slice-ops.sh`
  (`references/runtime-protocol.md`); en modo `legacy` la fuente es el fichero local
  (`references/state-protocol.md`). Lee antes de actuar; una transición = una llamada.
- **Secuencial**: un slice activo a la vez. Un gate no se salta.
- **Divulgación progresiva**: carga el `references/<tema>.md` solo cuando la fase lo necesita.
- **Delega en subagentes** para revisión pesada y para **explorar** (devuelven síntesis condensada,
  protegen el presupuesto de atención de la sesión principal para **cablear**, no para descubrir).
- **Refresh de contexto = estado por defecto**: cada iteración nace **headless / contexto virgen** y
  reconstruye el estado **desde disco** (git + `build-state.json` en modo legacy + logs), no desde la conversación
  viva. Mantén el **checklist de cableado** (un item por escenario AC y por punto de integración
  entre capas): nace `failing`, pasa a `passing` **solo tras prueba real ejecutada**
  (`slice-ops.sh wiring update … --evidence-file`). Deja una nota por hito
  (`slice-ops.sh progress`). **Mientras quede un item `failing`, el slice NO está terminado.**
  Protocolo: `references/runtime-protocol.md` (modos `dual`/`runtime`).

## Dos loops

Esta skill conduce el **inner loop** (rápido, por épica, sin subagentes pesados). Las revisiones
profundas (seguridad, diseño, UX, coherencia triple, arquitectura, integración) **NO** corren por
épica: corren **una vez por release** en la skill `releasing-a-version` (outer loop). Objetivo del
inner loop: **≤ ~20 min por épica** y producto que **camina end-to-end en todo momento**.

> **Regla del esqueleto que camina.** El **primer** slice de una release construye el journey
> completo más delgado posible (de la 1ª a la última actividad del backbone del Story Map), aunque
> cada paso sea un stub. Cada épica posterior **engorda** un paso de ese esqueleto y mantiene el
> `journey_smoke` verde. Nunca se construyen capas horizontales aisladas que "se juntan al final".

> **Cimiento antes que negocio (épicas fundacionales).** Las épicas marcadas `layer: foundational`
> (autenticación, acceso a datos, arquitectura base, design-system/componentes base) se construyen
> **antes** que las `layer: business`. El DoR **rechaza** abrir una épica de negocio que arrastra
> cimiento no construido y lo extrae a una épica fundacional previa (ver `dor.md`). Así cada slice de
> negocio **solo toca lógica aplicable** y no quema contexto creando infra.

> **Descomposición por tamaño (no one-shot).** Una épica que supera el **gate de tamaño**
> (heurística por defecto: **> 3 HU** ó **≥ 3 capas tocadas**; configurable por proyecto) es
> demasiado grande para una pasada: el DoR obliga a trocearla en **sub-slices verificables**
> (`sub_slices[]`) construidos **de a uno**, con `journey_smoke` verde entre cada uno antes de pasar
> al siguiente. El orquestador trabaja por **fases encadenadas** (mapear → generar → revisar →
> fix-loop → optimizar) y reparte la exploración **"ancho antes que profundo"** con subagentes
> **solo-lectura por área** (frontend/backend/datos); el **cableado** lo hace la sesión, no
> subagentes que escriben en paralelo. Trocear acota además el tamaño del `wiring_checklist[]`.
> Para épicas troceadas, esa exploración solo-lectura **puede** conducirse con la plantilla (opcional)
> `workflows/explore-fanout.workflow.js` — contrato en `references/exploration-fanout.md`. **No** se usa en
> épicas atómicas (inflaría el inner loop barato); es read-only (no escribe estado) y el cableado sigue
> siendo de la sesión.

## Workflows (plantillas, no scripts)

Los archivos `*.workflow.js` bajo `workflows/` son **plantillas de referencia** que esta skill **conduce**,
no scripts a correr verbatim (si contradicen `METODOLOGIA.md`, gana la metodología). Reglas duras:
- **Opt-in y solo para épicas grandes.** Los workflows del inner loop solo aplican a épicas troceadas por el
  gate de tamaño (`sub_slices[]` no vacío); **nunca** en el camino caliente ≤ ~20 min de una épica atómica.
- **Read-only sobre el estado.** Ningún workflow transiciona el estado (ni por `slice-ops.sh` ni, en modo legacy,
  escribiendo en `build-state.json`—legacy protocol—): devuelven un diagnóstico y `build-orchestrator` (o el agente dueño del gate)
  aplica el mapeo respetando el protocolo (una transición = una escritura; gates monótonos; en legacy, validar contra
  el schema tras escribir).
- **Subagentes de exploración = solo-lectura** (Read/Grep/Glob); el cableado lo hace la sesión.

Ver `workflows/README.md`. Hoy: `workflows/explore-fanout.workflow.js` (exploración fan-out) y
`workflows/wiring-verify.workflow.js` (conducción del verificador adversarial del gate `wiring_verified`).

## Fase 0 · Scaffold (Paso 1 fundamental — precondición restrictiva)

Antes de abrir **cualquier** slice, el scaffold runnable del proyecto debe **existir y estar
confirmado explícitamente**. El arnés **NO genera** el scaffold (es agnóstico al stack), pero
**bloquea el avance** hasta confirmarlo. Es la precondición del primer slice; el *esqueleto que
camina* se construye **encima** del scaffold ya existente.

1. Consulta el hecho: `bash .claude/hooks/build/slice-ops.sh status` (campo `scaffold`). Si ya
   está confirmado → continúa a la Fase 1 (dor).
2. Si es `false` → **pregunta explícitamente** (AskUserQuestion): *"¿Existe un scaffold runnable del
   proyecto (arranca vacío: el script de build/dev corre sin error)?"*
   - **No** → **STOP**. Indica crearlo según el stack permitido (`.claude/config/stack-allowlist.json`
     / el PRD técnico). **No lo generes tú.** No abras el slice.
   - **Sí** → reporta el hecho confirmado por la persona:
     `slice-ops.sh fact scaffold-confirmed --by «quién» --notes «build/dev arranca vacío sin error»`
     (en modo `legacy` el comando devuelve rc 3 y lo escribes en el fichero) y continúa.
3. El gate lo valida también el `dor-dod-gatekeeper` (criterio duro de DoR) y lo respalda el hook
   determinista `scaffold-guard.sh` (bloquea escribir código de slice sin scaffold confirmado).

## Fase 0-bis · Fuente de diseño (seguro para slices con UI)

Espejo de la Fase 0, para proyectos **con UI**. Antes de abrir el primer slice con UI:
1. Consulta la fuente de diseño con `slice-ops.sh status` (campo `design_source`).
   - `applies` indeterminado (ausente) → pregunta *"¿este proyecto tiene UI?"* y fija `applies`.
   - `applies === false` → N/A, salta esta fase.
   - `confirmed === true` → continúa.
2. `applies===true && confirmed===false` → **pregunta explícita** (AskUserQuestion): *"¿Existe una
   fuente de diseño declarada (prototipo/export) para la UI de este proyecto?"*
   - **No** → **STOP**. Ofrece dos salidas: **generarla con `/build:prototype`** (skill
     `prototyping-screens`; la confirmación sigue siendo humana) o declarar una fuente externa
     (ruta/URL del prototipo o export). No abras el slice con UI sin fuente confirmada.
   - **Sí** → repórtalo:
     `slice-ops.sh fact design-source --applies true --source «ruta/URL» --confirmed true --by «quién»`.
3. Lo respalda el hook determinista `design-source-guard.sh` (bloquea código de slice UI sin fuente
   confirmada) y lo valida el `dor-dod-gatekeeper` (criterio duro de DoR).

## Pipeline — inner loop (carga la referencia indicada en cada paso)

| Fase | Acción | Delega en | Gate | Referencia |
|---|---|---|---|---|
| 1 · dor | Validar Definition of Ready | `dor-dod-gatekeeper` | `dor` | `dor.md` |
| 2 · change | `opsx:new` + bloque `## Trazabilidad`; validar enlace (barato) | `opsx:new`, `change-epic-coherence` | `coherence_link` | `link-change-epic.md` |
| 3 · tdd | red → green → refactor (sin `BND-*` failing; `references/boundary-check.md`) | `superpowers:test-driven-development` | `tdd` | `boundary-check.md` |
| 4 · smoke | Recorrer el journey-hasta-aquí end-to-end con el **runner determinista fuera-de-chat** (`integration-check`: suite+build+reporte) en **sesión/contexto virgen**; **slices con UI:** fidelidad por **verificación visual REAL** (MCP chrome-devtools, screenshot app vs prototipo) | runner `integration-check`, skill `verify`/`run` + MCP chrome-devtools, `ux-fidelity-reviewer` | `journey_smoke`,`fidelity` | `integration-check.md`, `mcp-map.md` |
| 5 · api/data | contratos + consistencia (si aplican al slice) | `api-contract-tester`, `data-consistency-checker` | `api`,`data` | `newman-tests.md`, `data-consistency.md` |
| 6 · dod | **Primero** verificación adversarial INDEPENDIENTE del cableado (contexto virgen: refuta stubs/rutas sin cablear/AC sin test/items `failing`) → `wiring_verified`; **solo entonces** Definition of Done. **Máximo 2 pasadas completas por slice** (condición de parada, ver abajo) | `wiring-adversarial-verifier`, `dor-dod-gatekeeper` | `wiring_verified`,`dod` | `dod.md`, `integration-check.md` |
| 7 · pr | Abrir PR + archivar change en el mismo PR | `opsx:archive`, `opsx:sync` | — | `gitflow.md` |
| 8 · release? | Preguntar si correr el Release Gate ahora | usuario (default computado) | — | abajo |

> **Reporta la fase al runtime en cada transición** (modos `dual`/`runtime`; en `legacy` el
> comando devuelve rc 3 y no haces nada): `bash .claude/hooks/build/slice-ops.sh phase <to>`
> **al entrar** en cada fase. Las fases del hub son más finas que las de esta tabla:
> `dor → change → red → green → refactor → smoke → api → data → dod → pr` — la fase 3 · tdd
> reporta **tres** (`phase red` al escribir el test rojo, `phase green` al pasarlo,
> `phase refactor` al refactorizar) y la 5 reporta `api` y luego `data`; la 7 · pr reporta
> `phase pr` al abrir el PR. El subcomando es idempotente y rellena huecos solo (cadena
> completa, el orden del hub es estricto); sin estos reportes el slice queda «en
> construcción» en el hub aunque su PR ya esté mergeado. Ver `references/runtime-protocol.md`.

Los gates `stack`, `security`, `smell`, `ux` y la coherencia triple completa **ya no se cierran
aquí**: pertenecen al Release Gate. Las **deps** siguen vigiladas en tiempo real por el hook
`stack-guard.sh`; lint/tsc/gitflow por sus hooks.

El gate `fidelity` (fidelidad a la fuente de diseño) **sí** es de inner loop: se computa en `smoke`,
con la app ya levantada, y es vivo por-slice; complementa al `ux-krug-reviewer` (usabilidad), que
sigue en el Release Gate. **Estricto para UI:** una UI no mejora su fidelidad por el prompt sino
porque el agente **carga la página, observa la salida real y lee la consola**. Para slices con UI
(`design_source.applies===true`), `fidelity` **solo cierra con verificación visual real vía MCP
chrome-devtools** (screenshot app vs prototipo). Sin MCP, `fidelity` queda `false` (INCONCLUSO ya
**no** pasa) → el `dod` no cierra: corre el slice donde haya MCP. Mantén **cobertura** (ninguna
pantalla del prototipo en alcance sin construir; ninguna pantalla de la app sin HU/EP) y el
**journey-smoke de clic real como tenant no-admin**.

**Condición de parada del bucle adversarial (fase dod): máximo 2 pasadas completas por slice.** Sin
esta cota, tres reglas legítimas (sesgo «está incompleto», «nadie cierra sus propios gates» y el
patrón medido de que los arreglos siembran hallazgos nuevos) se combinan en un bucle sin salida. La
salida definida es esta y no depende de que alguien corte el bucle a mano:
- **Pasada 1** completa; **pasada 2** incremental (solo items cuyo código cambió desde su
  `verified_at_sha` + el diff de los arreglos y sus rutas gemelas).
- Los hallazgos de la 2ª pasada que estén en **código nuevo del cierre** se arreglan y se cierran
  con **mutación verificada** (re-ejecutar la evidencia del item afectado tras el fix) — **sin
  tercera pasada**.
- La revisión independiente restante se **difiere EXPLÍCITAMENTE al Release Gate**
  (`releasing-a-version`), declarándolo en el PR del slice: los gates `wiring_verified`/`dod` se
  cierran **honestos** (todo lo verificado, verificado; lo diferido, declarado — no es recorte en
  silencio, lo custodia el gate que ya existe para eso).
- **Excepción única**: un hallazgo ALTA en código **preexistente** durante la 2ª pasada habilita una
  pasada extra **acotada a ese frente** (nunca una tercera pasada completa).

MCP/LSP por gate: ver `references/mcp-map.md`. Protocolo de estado: **`references/runtime-protocol.md`**
(modos `dual`/`runtime`, vía `slice-ops.sh`) o `references/state-protocol.md` (modo `legacy`).
Presupuesto de mutación y anclaje de la evidencia (determinista vs viva): `references/evidence-budget.md`.
¿Suite del destino con rojos heredados? Medición de regresión con baseline cacheado por sha: `references/regression-baseline.md` (script `assets/baseline-verdict.sh`).

## Fase 8 · ¿Release Gate ahora? (default computado, humano decide)

Tras archivar la épica, **pregunta al usuario** si correr el Release Gate, con un **default
calculado** desde las líneas de release del Story Map (`docs/02-user-story-map/`):

- Si la épica **cierra una línea de release** (todas las épicas de esa línea ya están en
  `history[]`) → default **"Sí, correr `releasing-a-version` ahora"**.
- Si no la cierra → default **"Continuar a la siguiente épica"**. Excepción (*nudge*): si hay
  **≥ 2 épicas** archivadas desde el último entry de `releases[]`, recomienda correrlo igual.

El usuario siempre puede sobreescribir el default. Si acepta, invoca la skill
**`releasing-a-version`** sobre la release correspondiente.

## Cómo empezar
1. **Fase 0 — scaffold**: verifica `scaffold.confirmed` (ver arriba). Si no está confirmado, resuélvelo
   primero (pregunta explícita; STOP si no existe). Sin scaffold confirmado no se abre slice.
2. Pregunta/identifica la **épica** objetivo (`EP-XXX` en `docs/03-backlog/epicas.md`) y reúne las
   **HU que cubre** (las que tienen `epica: EP-XXX` en `docs/04-historias/`) → poblarán `hus[]`.
3. Reclama o retoma: `slice-ops.sh claim --epic EP-XXX` (rc 7 = sin trabajo; rc 3 = modo legacy o
   dual, donde el slice lo decide el fichero). Luego `slice-ops.sh next-step` te dice dónde seguir;
   si no hay slice, arranca en **dor**.
4. Invoca al `build-orchestrator` para conducir el pipeline, o ejecuta fase a fase tú mismo
   respetando los gates.

## Reglas duras
- **Paso 1 fundamental**: sin `scaffold.confirmed=true` no se abre slice ni se escribe código de
  slice (lo respalda `scaffold-guard.sh`). El arnés exige el scaffold pero **no lo genera**.
- En `harness_phase` = `authoring` (sin `package.json`) puedes hacer la Fase 0 (crear/confirmar el
  scaffold) + dor + change, pero los gates de código (tdd, journey_smoke, api, data) NO se cierran
  hasta tener el scaffold confirmado.
- El enlace change↔épica va en `## Trazabilidad` del `proposal.md`, **nunca** en frontmatter YAML
  (rompe `openspec validate`). Ver `link-change-epic.md`.
- Integración solo por **PR** a `main` (el hook `gitflow-guard.sh` bloquea commits/push directos).
- **`dod` exige `wiring_verified: true`** (verificación adversarial independiente, contexto virgen).
  El DoD declarativo del gatekeeper es un **piso, no el arreglo**: reusar el mismo agente como
  generador y verificador produce auto-confirmación. La generación y la verificación van separadas.
  Opcionalmente, esa verificación se **conduce** con la plantilla read-only
  `workflows/wiring-verify.workflow.js` (envuelve al `wiring-adversarial-verifier`); `build-orchestrator`
  sigue siendo quien **escribe** `gates.wiring_verified` a partir del veredicto que la plantilla devuelve
  y quien **estampa** `verified_at_sha` en los items reproducidos. **Máximo 2 pasadas completas por
  slice** (condición de parada de la fase dod, ver arriba); lo diferido se declara en el PR y lo
  custodia el Release Gate.
- **Producto completo, no MVP.** El alcance acordado se construye entero. **Recortar o diferir es
  bloqueante explícito** que requiere acuerdo del equipo — nunca una decisión del modelo. No derives
  en lo complejo. La verificación es **ejecutada, no por inspección** (ver `METODOLOGIA.md` y el
  bloque del arnés en `CLAUDE.md`).
- **Todo acto de dominio pasa por `slice-ops.sh`**: nunca armes peticiones al runtime a mano ni
  edites el fichero de estado en modo `runtime`. Un `rc 6` es la compuerta del servidor funcionando:
  muestra su razón y corrige la causa, no lo reintentes.
- Si una regla aquí contradice la metodología Trycore (`METODOLOGIA.md`), **gana la metodología**.
