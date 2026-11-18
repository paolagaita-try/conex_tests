# Release Gate — checklist de salida (outer loop)

Una **release** (línea de release del Story Map) no se da por cerrada hasta cumplir TODO esto. Se
corre **una vez** sobre el diff acumulado de todas sus épicas. Resultado en el runtime (veredictos por `release-ops.sh verdict`; en modo legacy, en `build-state.json` →
`releases[]`). El **cierre** de la release lo hace una persona en la consola del hub, nunca el agente.

- [ ] **`security`** — `security-reviewer` sin hallazgos CRÍTICO/ALTO sobre el diff completo de la release; claves de servicios externos solo server-side; datos sensibles / PII regulados (según el PRD del consumidor) no persistidos crudos; salida de cualquier servicio externo/IA tratada como input no confiable y validada contra esquema antes de alimentar la capa de decisión.
- [ ] **`smell`** — `simple-design-reviewer` sin bloqueantes sobre el diff acumulado; 4 reglas de Beck respetadas.
- [ ] **`ux`** — `ux-krug-reviewer` ok sobre la UI ensamblada (o `null` si la release no tiene UI). Lighthouse/accesibilidad si la app corre.
- [ ] **`coherence`** — `coherence-three-way` confirma trazabilidad AC↔change↔código de **todas** las HU de **todas** las épicas de la release, sin huérfanos.
- [ ] **`stack_arch`** — `stack-guardian` confirma la arquitectura del PRD del consumidor: la capa de servicios externos/IA en la frontera declarada server-side (no decide), la capa de decisión determinista del dominio sin IA, sin claves de servicios externos en cliente. Si existe `docs/adr/` (capa de arquitectura, `/build:architect`), confirma además que el diff acumulado **no contradice** los ADRs `accepted` (estilo, tácticas por driver, divergencias de stack registradas); sin la capa, esa parte es N/A.
- [ ] **`integration`** — el **journey completo** de la release se recorre end-to-end con **dependencias reales** del proyecto (servicios externos/IA y capa de decisión reales, según el PRD del consumidor), no stubs. Verificado con la skill `verify`/`run` (+ MCP `chrome-devtools`). Se corre **fuera** del fan-out
  paralelo de reviewers (es **secuencial**, con deps reales); ver `../workflows/release-gate.workflow.js`.
  Además, **custodia los `na` de frontera**: enumera `boundaries[].verified[?status == na]` de
  `config/build-config.json` y, por cada uno, o bien el journey con dependencias reales lo cubre, o
  bien queda **declarado como riesgo de la release** (una línea, con su `reason_code` y su motivo).
  Nunca un verde silencioso: un `na` sin cubrir ni declarar es un `fail` de `integration`.

**Todo ✓ (o `na` cuando N/A)** → los seis veredictos quedan reportados con `release-ops.sh verdict`
(en modo legacy, `releases[].status: "passed"` en el fichero); el **cierre** lo hace una persona en la
consola del hub, nunca el agente. **Algo ✗** → se reporta `fail` con la evidencia y se lista el
hallazgo bloqueante; se corrige como un slice normal en `building-a-slice` y se re-corre el Release
Gate.

> El gate `integration` es el que faltaba en la era anterior: todos los gates por-slice estaban en
> verde y aun así el producto no caminaba de punta a punta. Sin `integration` con deps reales no hay
> release.
