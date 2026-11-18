---
name: releasing-a-version
description: Use when closing a release of the product — runs the heavy review gates ONCE over the accumulated diff of a release line (security, design/smell, UX/Krug, three-way coherence, architecture, and full end-to-end integration with real deps), instead of per epic. This is the outer loop; the per-epic inner loop lives in building-a-slice. Trigger after archiving an epic when the user accepts the Release Gate, or when a Story Map release line is complete. Reports the six measured verdicts through the agent surface (release-ops.sh verdict); closing the release stays a human act in the hub console.
---

# Release Gate (outer loop) — Build

El **outer loop** del arnés. Mientras `building-a-slice` (inner loop) construye épica a épica de
forma barata y rápida, esta skill ejecuta las **revisiones profundas una sola vez por release**,
sobre el **diff acumulado** de todas las épicas de esa release. Así el costo de los agentes pesados
pasa de `O(épicas)` a `O(releases)`.

## Qué es una release
Una **línea de release del Story Map** (`docs/02-user-story-map/`). P.ej. **R1-mvp** = EP-001 +
EP-002 + EP-003 + EP-004 ("Resolver un caso de punta a punta con resultado explicable"). El conjunto
de épicas de la release son las que vas a auditar en bloque.

## Cuándo se invoca
- Tras archivar una épica, `building-a-slice` pregunta con un default computado y el usuario acepta.
- O explícitamente: "corre el Release Gate de R1".

## Principio de operación
- **Una sola fuente de verdad, según el modo** (`bash .claude/hooks/build/slice-ops.sh mode`): en
  `dual`/`runtime` la release vive en el runtime y cada gate se reporta con
  `bash .claude/hooks/build/release-ops.sh verdict <line> <gate> <pass|fail|na>`; en `legacy`, en el
  array `releases[]` del fichero local (protocolo en `building-a-slice/references/state-protocol.md`).
- **Reportar es de agentes; el cierre en verde es del runtime; el degradado es humano** (política
  A-con-B). El agente mide y reporta los seis veredictos; con el último veredicto de los 6 gates
  canónicos en PASS **el hub auto-cierra** la release (`closed_by: AUTO_6_OF_6_PASS`, audit trail).
  Si algún gate queda `fail`/`partial` o hay deudas por decidir, **el cierre es decisión humana en
  la consola** — el gobierno humano vive donde hay decisión real, no en el clic de un resultado
  derivable. `release-ops.sh close-hint <line>` imprime la política.
- **Sobre el diff acumulado**: el alcance es el rango de commits de todas las épicas de la release
  (desde el merge anterior a la primera épica de la release hasta `main`).
- **Delega en subagentes** (devuelven síntesis, protegen el contexto).

## Workflows (plantillas, no scripts)

Esta skill es el **hogar primario** de los workflows del arnés: el Release Gate corre **una vez por release**
(`O(releases)`), fuera del camino caliente del inner loop, y **no** duplica el inner loop (ni TDD ni gates por
slice). Los `*.workflow.js` bajo `workflows/` son **plantillas de referencia** (no scripts a correr verbatim;
si contradicen `METODOLOGIA.md`, gana la metodología). Reglas duras:
- **Read-only sobre el estado.** La plantilla devuelve veredictos; **esta skill** es la única que los
  reporta (un `release-ops.sh verdict` por gate; en modo legacy, una entrada en `releases[]` del
  fichero). El agregado lo hace el runtime: **parciales no promueven a `passed`**.
- **`integration` fuera del paralelo.** Los 5 reviewers pesados van en `parallel()`; el gate `integration`
  (journey completo con **deps reales**) es **secuencial** vía `verify`/`run` y **no** delega en un reviewer.

Ver `workflows/README.md`. Hoy: `workflows/release-gate.workflow.js`.

## Pipeline del Release Gate

| Gate | Acción | Delega en | Referencia |
|---|---|---|---|
| `security` | Vectores generales + foco de dominio del consumidor (PII/secretos/authz, claves de servicios externos server-side) sobre todo el diff | `security-reviewer` | — |
| `smell` | 4 reglas de Beck + code smells sobre el diff acumulado | `simple-design-reviewer` | `building-a-slice/references/simple-design.md` |
| `ux` | Krug + lighthouse sobre la UI ensamblada de la release (o `null` si sin UI) | `ux-krug-reviewer` | `building-a-slice/references/krug-ux.md` |
| `coherence` | Trazabilidad triple AC↔change↔código de **todas** las HU de la release | `coherence-three-way` | — |
| `stack_arch` | Arquitectura del PRD del consumidor (capa de servicios externos en la frontera declarada, capa de decisión determinista del dominio sin IA) y, si el proyecto adoptó la capa de arquitectura (`/build:architect`), conformidad del diff con los ADRs `accepted` de `docs/adr/` | `stack-guardian` | — |
| `integration` | Recorrer el **journey completo** de la release con **deps reales** del proyecto, no stubs | skill `verify` / `run` (+ MCP chrome-devtools) | `release-dod.md` |

Checklist de cierre: `references/release-dod.md`.

## Cómo proceder
1. Identifica la release y sus épicas: `bash .claude/hooks/build/slice-ops.sh status` + el Story Map
   (`docs/02-user-story-map/`).
2. No hay entrada que crear: la línea de release existe en el runtime; los veredictos la van poblando.
3. Dispara los subagentes **en paralelo** sobre el diff acumulado (devuelven síntesis).
4. Corre el gate de **integración** con la skill `verify`/`run`: el journey completo, deps reales.
5. Reporta **cada** gate en cuanto lo tengas medido, con su evidencia:
   `release-ops.sh verdict R1-mvp security pass --evidence-file informe.txt` (usa `na` cuando el gate
   no aplique — p. ej. `ux` en una release sin UI). Un `rc 6` es el servidor rechazando: muestra su
   razón, no reintentes. Sin red, el veredicto **no** tiene camino por la cola offline (`rc 5`,
   issue #44): reintenta el mismo comando cuando vuelva la red, antes de pedir el cierre.

   **Contrastar antes de aceptar un PASS.** Un shard que afirma `pass` no cierra nada por sí solo.
   Antes de reportar el gate, abre **una** pieza de la evidencia que el shard citó: el `archivo:línea`
   o el comando. Si no existe, no abre o no se puede ejecutar → el gate es `false`. Es una
   comprobación, no una segunda revisión.
6. Con los seis reportados **en verde, el hub cierra solo** (la respuesta del último `verdict`
   anuncia `release CERRADA … closed_by: AUTO_6_OF_6_PASS`) — no hay paso manual. Si algún gate quedó `fail`,
   lista los hallazgos bloqueantes; el usuario los corrige como un slice normal (fix en
   `building-a-slice`) y se re-corre el Release Gate.

> **Opcional — conducir con workflow (releases grandes).** El fan-out del paso 3 puede conducirse con la
> plantilla `workflows/release-gate.workflow.js` (referencia, no obligatoria): SOLO paraleliza los 5 reviewers
> pesados; el gate `integration` (paso 4) sigue siendo **secuencial**, vía `verify`/`run` con **deps reales**,
> **fuera** del `parallel()`. Pasa por `args` lo que computes **read-only**: `diffRange`, `hasUI` y **`hus[]`**
> (los IDs de todas las HU de las épicas de la release) — con ≥ 3 HUs el carril `coherence` se shardea por HU
> (lossless, fail-closed) en vez de recorrerlas en un solo agente; con menos, corre monolítico como siempre.
> El resultado se reporta igual, gate a gate, con `release-ops.sh verdict`; esta skill sigue siendo la
> única que reporta veredictos de release. Parciales NO promueven a `passed` (lo agrega el runtime).

## Reglas duras
- **No dupliques el inner loop.** Aquí no se hace TDD ni se cierran gates por slice.
- **Integración con deps reales es obligatoria** para que la release pueda cerrarse — es el gate que faltaba y
  por el que el producto "no funcionaba al terminar". No se acepta con todo stubbeado.
- Si una regla aquí contradice la metodología Trycore (`METODOLOGIA.md`), **gana la metodología**.
