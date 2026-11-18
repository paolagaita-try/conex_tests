# Definition of Done (DoD) — checklist de salida **por slice** (inner loop)

Un slice (épica) **no se archiva ni se mergea** hasta cumplir TODO esto. Lo valida
`dor-dod-gatekeeper` leyendo los gates del slice (`slice-ops.sh status`; en modo legacy, del fichero). Es el DoD **reducido**: las revisiones
pesadas (seguridad, diseño, UX, coherencia triple, arquitectura, integración) **no** se piden aquí
— se piden una vez por release en el **Release Gate** (`release-dod.md` de la skill
`releasing-a-version`).

- [ ] **`tdd`** — cada escenario AC (G/W/T) de **cada HU de la épica** tiene test; ciclo red→green→refactor completo; suite verde; ningún item `BND-*` en `failing`.
- [ ] **`journey_smoke`** — la app arranca y el **journey-hasta-aquí** (backbone del Story Map cubierto hasta esta épica) **se recorre end-to-end** sin romperse. Se verifica con la skill `verify`/`run` (+ MCP `chrome-devtools` si la app corre). El esqueleto que camina sigue caminando.
- [ ] **`coherence_link`** — `change-epic-coherence` confirma el enlace change↔épica (bloque `## Trazabilidad`, `openspec validate` ok). Es el chequeo **barato**; la trazabilidad triple completa va al Release Gate.
- [ ] **`data`** — `data-consistency-checker` valida invariantes de datos (salida de servicios externos validada contra esquema antes de alimentar la capa de decisión determinista del dominio) (si el slice toca datos).
- [ ] **`api`** — `api-contract-tester` (Newman) 100% verde (o `null` si el slice no tiene endpoints).
- [ ] **`fidelity` (slices con UI)** — `ux-fidelity-reviewer` devuelve **FIEL** (o DESVIACIONES todas
  justificadas/documentadas) → `gates.fidelity: true`; `null` si el slice no tiene UI. **ESTRICTO para
  UI** (`design_source.applies===true`): solo `true` con **verificación visual real** vía MCP
  chrome-devtools (screenshot app vs prototipo). **INCONCLUSO ya NO pasa**: sin MCP queda `false` y el
  `dod` no cierra (corre el slice donde haya MCP). Mantén **cobertura** (ninguna pantalla del prototipo
  en alcance sin construir; ninguna pantalla de la app sin HU/EP). Es gate **vivo** de inner loop (no la
  revisión Krug, que sigue en el Release Gate).
- [ ] **Sub-slices completos** — si la épica se descompuso (`sub_slices[]` no vacío), **todos** en
  `status: done` con su `journey_smoke` verde. No se cierra `dod` con sub-slices pendientes.
- [ ] **`wiring_verified`** — el `wiring-adversarial-verifier` (subagente **independiente**, contexto
  virgen) intentó **refutar** el slice (stubs, rutas sin cablear, AC sin test, items de
  `wiring_checklist[]` aún `failing`) y no halló huecos → `gates.wiring_verified: true`. **Prerequisito
  duro de `dod`**: el DoD declarativo de este checklist es un **piso, no el arreglo** (la auto-confirmación
  surge de reusar el mismo agente como generador y verificador). Esa verificación puede conducirse,
  opcionalmente, con la plantilla read-only `../workflows/wiring-verify.workflow.js` (envuelve al verificador;
  `build-orchestrator` es quien escribe el gate a partir de su veredicto y estampa `verified_at_sha`
  en los items cuya evidencia fue reproducida — las pasadas 2+ son **incrementales**: solo re-ejecutan
  items cuyo código cambió desde su sha).
  **Condición de parada: máximo 2 pasadas completas por slice.** Hallazgos de la 2ª pasada en código
  nuevo del cierre → se arreglan y se cierran con **mutación verificada**, sin tercera pasada; la
  revisión independiente restante se **difiere explícitamente al Release Gate** y se declara en el PR
  (gates honestos, no recorte en silencio). Excepción: un hallazgo ALTA en código **preexistente**
  durante la 2ª pasada habilita una pasada extra **acotada** a ese frente.
- [ ] **OpenSpec**: todas las tasks `[x]`; el archive del change va **en el mismo PR** (no PR aparte).
- [ ] **Docs/trazabilidad**: back-ref del change añadida en la épica y en cada HU de `hus[]`. Si la
  condición de parada del bucle adversarial aplicó, el **PR declara** qué revisión quedó diferida al
  Release Gate.
- [ ] **`na` de frontera declarados en el PR**: si el slice registró algún `na` en
  `boundaries[].verified[]` (catálogo cerrado de `boundary-check.md`), el PR lleva **una línea por
  cada uno** con su `reason_code` y su `detail`. Un `na` que nadie lee llega al Release Gate sin
  haber sido visto.
- [ ] **Hooks verdes (automáticos, no son gates de agente)**: `lint-typecheck.sh` (lint + chequeo de tipos del stack declarado), `stack-guard.sh` (deps en allowlist según la sección de requisitos técnicos del PRD del consumidor, ruta declarada en `stack-allowlist.json#source`), `gitflow-guard.sh` (rama `feature/*`, sin commits directos a `main`).

**Todo ✓** → `gates.dod: true`; se hace `opsx:archive` + se abre/mergea el PR. **Algo ✗** → listar
gates abiertos y devolver al `build-orchestrator`.

> **Lo que NO se valida aquí (va al Release Gate, `releasing-a-version`):** `security`, `smell`
> (diseño), `ux` (Krug), `coherence` (trazabilidad triple completa) y `stack_arch` (arquitectura
> según el contrato de stack del PRD del consumidor: servicios externos/IA en la frontera declarada
> server-side, capa de decisión determinista del dominio sin IA). Las **deps** sí se vigilan por
> slice, pero vía el hook `stack-guard.sh`, no vía subagente.

## Delimitación: fronteras, datos, cableado propio e integración

Cuatro piezas distintas, cuatro preguntas distintas. Ninguna sustituye a otra.

| Pieza | Qué prueba | Cuándo |
|---|---|---|
| `BND-*` (inner) | El camino contra la frontera **existe**: un intercambio real por forma de mensaje, antes del código | Al sembrar el checklist, antes del primer test contra esa forma |
| `data` (inner) | La salida de esa frontera cumple el esquema; consume el resumen, **no** vuelve a llamar | Fase `api`/`data` |
| `integration_point` propio (inner) | Capas **nuestras** cableadas entre sí | Fase `dod` |
| `integration` (outer) | Journey completo con dependencias reales; **custodia los `na`** de `boundaries[].verified[]` | Release Gate |

Detalle de los `BND-*` (declaración de fronteras, join determinista, evidencia válida, memoria por
proyecto y catálogo de `na`): [`boundary-check.md`](boundary-check.md).
