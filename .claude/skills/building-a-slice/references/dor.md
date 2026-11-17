# Definition of Ready (DoR) — checklist de entrada

Una **épica** (`EP-XXX`) **no entra a construcción** hasta cumplir TODO esto. La unidad del slice es
la épica; lo de abajo aplica a la épica y a **cada HU** que cubre (`hus[]`). Lo valida `dor-dod-gatekeeper`.

**Precondición — gate del grafo (#86, §5-ter):** antes de la checklist, corre
`bash .claude/hooks/build/slice-ops.sh graph-check --epic EP-XXX`. Si devuelve **rc 2** (P2 tope de
tamaño, P3 sin HU con AC, P4 ciclo, P10 línea posterior) → **no se abre el slice**; se corrige en los
docs (se parte en **épicas**, no en tramos; el PO no lo salta). rc 1/5 (docs ilegibles o sin python3)
no bloquean: avisan y se sigue (fail-open sobre la infraestructura).

- [ ] **Épica válida**: `EP-XXX` existe en `docs/03-backlog/epicas.md` con trazabilidad a objetivos del PRD.
- [ ] **HU enumeradas**: la épica tiene ≥1 HU; todas las que entran se listan en `hus[]`.
- [ ] **Frontmatter completo** en cada `docs/04-historias/HU-XXX.md`: `id, titulo, epica, prioridad, complejidad, estado` y `estado: lista`.
- [ ] **AC en Given/When/Then** por HU, **proporcional a `complejidad`** (cubre los modos de fallo que *realmente existen*, no una cuota fija): `trivial`/baja → **1–2** (happy + el error/edge crítico si existe); `media` → **3** (happy + error + edge); `alta` → **3–5** (cobertura completa). Regla dura Trycore: si existe una rama de error/edge, **debe** tener su escenario (lo que se elimina es fabricar 3–5 para una HU trivial).
- [ ] **INVEST** por HU: pasa los 6 criterios (Independent, Negotiable, Valuable, Estimable, Small, Testable).
- [ ] **Dependencias resueltas**: las épicas/HU de las que depende están archivadas (`history[]`) o explícitamente no bloquean. **Excepción dura — cimiento:** si la dependencia es **infraestructura fundacional** (autenticación, acceso a datos, arquitectura base, design-system/componentes base), la cláusula "explícitamente no bloquean" **NO aplica**: debe estar **construida y archivada** antes (ver criterio "Cimiento construido").
- [ ] **Cimiento construido (épicas de negocio)**: si esta épica es `layer: business`, todo el cimiento que arrastra (auth, acceso a datos, arquitectura base, design-system/componentes base) ya existe como épica(s) `layer: foundational` **archivada(s)** en `history[]`. Si arrastra cimiento no construido → **STOP**: extráelo a una épica fundacional previa y constrúyela primero. Las épicas fundacionales se priorizan **antes** que las de negocio.
- [ ] **Caparazón construido (solo greenfield — gate PROACTIVO)**: si `project_kind === "greenfield"`
  y la caparazón está **requerida**, ninguna épica `layer: business` entra a construcción mientras
  la caparazón no esté **construida y archivada con su checklist evidenciada**. Las épicas
  `layer: foundational` (la caparazón u otras fundacionales) sí pueden abrir. A diferencia de
  "Cimiento construido" (reactivo: bloquea si *detecta* arrastre), este criterio bloquea
  **siempre** en greenfield hasta que el cimiento exista archivado — no depende de detectar nada.
  **Dónde se leen esos hechos depende del modo**, y no son los mismos:
  - **`legacy`/`dual`** — `build-state.json`: `foundation.required`, `foundation.epic` (el
    `EP-XXX` concreto) y `foundation.completed_at`. Si `foundation.epic` es `null` → **STOP**: la
    épica caparazón no existe aún; se define en `/build:onboard` Fase 2c o en discovery.
  - **`runtime`** — la proyección solo trae `foundation_done` (booleano), vía
    `slice-ops.sh status` (línea `hechos:`). **Nadie fija `foundation.epic` en este modo**: la
    Fase 2c propone la épica al hub sin código y la identidad la asigna el hub al aprobar
    (issue #62). Así que aquí **no preguntes por `foundation.epic`** — no existe. Con
    `foundation_done: false`, el estado real de la caparazón lo dice `slice-ops.sh epic-status`
    (o `/build:epic --check`): si hay una propuesta `PROPOSED`, el STOP es **esperar la
    aprobación**, no re-onboardear (repetir la Fase 2c propondría la misma épica dos veces); si
    no hay ninguna propuesta, entonces sí → Fase 2c o discovery.

  Brownfield o caparazón no requerida (`foundation.required: false` en `legacy`/`dual`;
  `foundation_done: true` en `runtime`) → **N/A** (no bloquea).
  Contrato: `references/foundation-contract.md`.
- [ ] **Tamaño acotado (gate de descomposición, blando)**: si la épica supera el umbral —heurística por defecto **> 3 HU** ó **≥ 3 capas tocadas** (configurable por proyecto)— **no entra como slice único**: se descompone en `sub_slices[]` verificables construidos de a uno, con `journey_smoke` verde entre cada uno. El umbral es proporcional (no cuota rígida): una épica de 1 capa y pocas HU entra directa.
- [ ] **Tope duro de tamaño (P2, §5-ter)**: por encima del gate de descomposición, **> 6 HU** ó **> 2 tramos** **no se descompone, se rechaza** —se parte en **épicas**, no en más tramos; el PO no lo salta—. Lo fuerza la Precondición del gate del grafo (`graph-check`, rc 2).
- [ ] **Cabe en el stack** del PRD §7 (no requiere tecnología fuera de `stack-allowlist.json`).
- [ ] **Cobertura arquitectónica (ADR)** *(opt-in, retrocompatible)*: si el proyecto adoptó la capa de
  arquitectura (existe `docs/adr/_backlog-arquitectonico.md`, de `/build:architect`), los drivers
  arquitecturalmente significativos que la épica ejerce tienen un ADR con estado ≥ `ABORDADO`. El join
  épica↔driver es por la columna **Trazabilidad (EP/HU)** del tablero del backlog (fallback: la columna
  Trazabilidad del `0000`). **Duro para épicas `layer: foundational`** (auth/datos/arquitectura
  base/design-system): sin ADR que cubra su cimiento → **STOP**, corre `/build:architect` primero. Para
  `layer: business` es advertencia si algún driver sigue `PENDIENTE`. Sin `docs/adr/` (proyecto sin la
  capa) → **N/A** (no bloquea; sugiere la capa).
- [ ] **Datos de prueba disponibles** o identificables (p.ej. los datos de ejemplo / fixtures sintéticos del dominio del consumidor).
- [ ] **Fuente de diseño identificada (slices con UI)**: la fuente visual de verdad del slice
  (el `DESIGN_SOURCE` del dominio) está declarada y confirmada (`design_source.confirmed`), y este
  slice apunta a la(s) pantalla(s) equivalente(s). Si la fuente es un prototipo generado
  (`docs/05-prototipo/`), esas pantallas existen en `manifest.json` con `estado: "aprobada"`
  (un `borrador` no satisface el criterio; genera/aprueba primero con `/build:prototype`).
  No se construye UI fuera de la fuente declarada.
- [ ] **Clasificación `layer`**: `foundational` (auth/datos/design-system/arquitectura base) | `business`. Se escribe en `active_slice.layer`. Gatea el front paralelo (foundational nunca en paralelo).
- [ ] **`files_scope`**: globs de los archivos que la épica tocará (p.ej. `src/reports/**`). Fuente de la disjunción inter-épica. Se escribe en `active_slice.files_scope`.

**Si todo ✓** → el slice se abre por el claim del runtime (`slice-ops.sh claim --epic EP-XXX`), que
devuelve `slice_id`, épica, historias,
`phase: dor`, `gates.dor: true` y el resto en `false` —incluido **`wiring_verified: false`**—
(`fidelity`/`api` en `null` si la épica no toca UI/endpoints; `fidelity` arranca en `false` si toca UI).
**Si algo ✗** → no se abre el slice; se reporta qué falta y se vuelve a discovery (Trycore).
