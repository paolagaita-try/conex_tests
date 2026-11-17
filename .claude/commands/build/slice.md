---
name: "BUILD: Slice"
description: Punto de entrada del inner loop. Abre o continúa un slice (épica EP-XXX) y conduce el pipeline DoR → change → TDD → smoke → api/data → dod → PR+archive delegando en la skill building-a-slice (o el agente build-orchestrator para épicas multicapa). Respeta el orden estricto de gates y el scaffold como precondición.
category: Workflow
tags: [build-harness, inner-loop, slice, trycore]
---

Lanza el **inner loop** de construcción sobre una épica. Este comando es un **adaptador delgado**: no
reimplementa el pipeline — **delega** en la skill `building-a-slice` (motor del inner loop) y en `opsx:*`
(motor de changes). Si algo aquí contradice `METODOLOGIA.md`, **gana la metodología**.

**Entrada:** `EP-XXX` o una descripción de la épica. Si viene vacío, usa **AskUserQuestion** para elegir la
épica desde `docs/03-backlog/epicas.md`.

---

## 1. Preflight

```bash
test -f .claude/.build-harness-version || echo "NOT_INSTALLED"
command -v python3 >/dev/null 2>&1 || echo "NO_PYTHON3"
```

**Si `NOT_INSTALLED`:** este proyecto no tiene el arnés instalado → ejecuta `trycore-build init` y vuelve.
Stop si no está instalado o falta `python3`.

---

## 2. Leer el estado y decidir punto de entrada

```bash
MODE="$(bash .claude/hooks/build/slice-ops.sh mode)"
bash .claude/hooks/build/slice-ops.sh status
```

- `MODE=legacy` → el fichero es primario: sigue `building-a-slice/references/state-protocol.md`
  (comportamiento v0.8.5 exacto, sin red).
- `MODE=dual|runtime` → el estado vive en el runtime
  (`building-a-slice/references/runtime-protocol.md`).
- **Sin slice activo** (`slice: ninguno reclamado`): en `runtime`, recláma­lo con
  `bash .claude/hooks/build/slice-ops.sh claim --epic EP-XXX` — `rc 7` = sin trabajo disponible,
  `rc 6` = rechazo del servidor (muestra su razón, no reintentes). En `legacy|dual` (rc 3) abre el
  slice por **dor** con el protocolo del fichero.
- **Con slice activo** → **reanuda donde toca**:
  `bash .claude/hooks/build/slice-ops.sh next-step` (no abras otro: el modelo es
  secuencial, un solo slice activo).

---

## 3. Precondición de scaffold (y fuente de diseño si hay UI)

Antes de escribir código de slice, verifica los gates de proyecto:

**Dónde se leen esos hechos depende del modo:**

- **`legacy`/`dual`** — la fuente es `.claude/state/build-state.json` (`scaffold.confirmed`,
  `design_source.confirmed`, `project_kind`, `foundation.completed_at`):
  ```bash
  python3 -c "import json;d=json.load(open('.claude/state/build-state.json'));print(d.get('scaffold',{}).get('confirmed'),d.get('design_source',{}).get('confirmed'),d.get('project_kind'))"
  ```
- **`runtime`** — la línea `hechos:` que imprime `bash .claude/hooks/build/slice-ops.sh status`
  (`scaffold_confirmed`, `design_source_confirmed`, `project_kind`, `foundation_done`).

- **scaffold** confirmado (`scaffold_confirmed`). Si no → **STOP**: delega en la **Fase 0** de
  `building-a-slice` (pregunta explícita; el arnés **no genera** el scaffold). No abras el slice.
- Si el proyecto tiene UI, **fuente de diseño** confirmada (`design_source_confirmed`, Fase 0-bis). Si
  no → **STOP** igual.
- **Caparazón (solo greenfield)**: si `project_kind` es `greenfield` y `foundation_done` es `false`, y
  la épica objetivo es `layer: business` → **STOP**: solo la épica caparazón u otra fundacional puede
  abrir. `status` no identifica **cuál** es la épica caparazón (eso vive hoy en el fichero legacy,
  leído directo por `dor-dod-gatekeeper`); pregunta o consúltalo ahí. En modo `runtime` puede no
  existir todavía porque la propuesta está **pendiente de aprobación del hub**
  (`/build:epic --check` lo dice): entonces el STOP es **esperar**, y no volver a proponerla.
  Lo valida en detalle el `dor-dod-gatekeeper` (criterio 7-bis). Brownfield → N/A, no preguntes.

El hook `scaffold-guard.sh` respalda esto en tiempo real.

---

## 4. Conducir el pipeline (delegar)

Invoca la skill **`building-a-slice`** para conducir el inner loop. Para una épica **multicapa / grande**
(superó el gate de tamaño → `sub_slices[]`), invoca el agente **`build-orchestrator`** (trabaja por fases
encadenadas y, opcionalmente, conduce la exploración solo-lectura con `workflows/explore-fanout.workflow.js`).

- **No** ejecutes `opsx:apply` directamente ni saltes gates: el orden es estricto
  (`dor → change → tdd → smoke → api/data → dod → pr`).
- **No** dispares reviewers pesados aquí (`security`, `smell`, `ux`, `coherence`, `stack_arch`): pertenecen
  al **Release Gate** (`/build:release`). Hacerlo por slice rompería el modelo de dos loops.

---

## 5. Resumen

Reporta según `### Cómo reportar` del CLAUDE.md del proyecto (gana sobre cualquier otro formato de
cierre): incluye fase actual, gates cerrados/abiertos y el siguiente gate como parte de esa
estructura, no como un resumen libre aparte. Si la épica quedó archivada, recuerda el default del
Release Gate (ver `/build:release`).

---

## Guardrails

- **Un solo slice activo** (secuencial). No abras un segundo mientras haya uno reclamado; en
  `runtime` el propio claim es idempotente y devuelve el mismo slice con el lease vigente.
- **Todo acto de dominio pasa por `slice-ops.sh`**; en modo `runtime` no se escribe el fichero local.
- **Orden estricto de gates**; un gate no se salta. `dod` exige `wiring_verified: true`. El bucle
  adversarial tiene condición de parada: **máximo 2 pasadas completas por slice** (pasadas 2+
  incrementales por `verified_at_sha`; lo diferido se declara en el PR y lo custodia el Release
  Gate — ver METODOLOGIA §1-bis).
- **Sin scaffold confirmado, no hay slice** (el arnés lo exige pero no lo genera).
- **Agnóstico**: este comando no asume dominio; lo específico entra por `/build:onboard` y `stack-allowlist.json`.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
