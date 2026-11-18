# `workflows/` — plantillas de workflow del outer loop (`releasing-a-version`)

> **Plantillas, NO scripts a correr verbatim.** Conducidas por la skill `releasing-a-version`. Si contradicen
> `METODOLOGIA.md`, **gana la metodología**.

## Reglas duras
1. **Hogar primario de los workflows.** El Release Gate corre **una vez por release** (`O(releases)`), fuera
   del camino caliente del inner loop. **No duplica** el inner loop (ni TDD ni gates por slice).
2. **Read-only sobre el estado.** La plantilla devuelve veredictos; la skill `releasing-a-version` es la
   **única** que reporta los veredictos de release (uno por gate vía `release-ops.sh verdict`; en modo
   legacy, una entrada en `releases[]` validada contra el schema local,
   `updated_by: releasing-a-version`). Parciales **no** promueven a `passed`.
3. **`integration` fuera del paralelo.** Los 5 reviewers pesados van en `parallel()`; el gate `integration`
   (journey completo con **deps reales**) es **secuencial**, lo corre la skill `verify`/`run`, y **no** delega
   en un reviewer. Es el gate no negociable.
4. **Agnóstico.** Sin vocabulario de dominio/cliente (`scripts/check-agnostic.sh` incluye `*.js`).

## Plantillas
- **`release-gate.workflow.js`** — `parallel(5 reviewers)` → `integration` secuencial → síntesis a
  `releases[].gates.{security, smell, ux, coherence, stack_arch, integration}`. El carril **`coherence`**
  se shardea **por HU** cuando la release tiene ≥ 3 HUs (`args.hus[]`, computadas read-only por la skill):
  la trazabilidad triple de cada HU es independiente → el sharding es *lossless* y el carril más lento pasa
  de O(HUs) a O(1) + consolidación **fail-closed** con cobertura completa (shard fallido/ausente = gate
  false, nunca muestreo). `security`/`smell`/`ux`/`stack_arch` quedan **monolíticos a propósito**:
  shardearlos por archivos puede perder hallazgos cross-cutting.
