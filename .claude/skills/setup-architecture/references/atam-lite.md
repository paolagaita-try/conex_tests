# ATAM-lite — evaluación de la arquitectura en papel (ADD Paso 7) — referencia

Análisis de cada ADR **antes de programar**, para descubrir riesgos y trade-offs. Es una versión ligera
de ATAM (Architecture Tradeoff Analysis Method): no se hace un taller formal con stakeholders, sino un
barrido adversarial delegado en el agente `architecture-evaluator` (read-only). Alimenta §5/§6 del ADR y
la sección de riesgos del backlog (estructura completa del backlog — tablero por driver, riesgos
abiertos, bitácora — en `assets/_backlog-arquitectonico.template.md` de esta skill).

## Qué produce el evaluador, por ADR

- **Veredicto por driver**: para cada driver que el ADR dice satisfacer, ✅/⚠️/❌ con la **evidencia o
  medida** que lo respalda (o la que falta). Un ⚠️/❌ es un riesgo, no un rechazo.
- **Puntos de sensibilidad**: propiedades del diseño donde una decisión afecta fuertemente a un atributo
  (p.ej. "el tamaño del pool de conexiones determina QA-1 rendimiento de lectura").
- **Trade-offs**: puntos donde una decisión mejora un atributo y empeora otro (p.ej. "el backoff
  1s/3s/9s da robustez pero puede exceder el P99 ≤ 10 s de la integración externa").
- **Riesgos**: decisiones sin evidencia, drivers no cubiertos, supuestos sin validar. Cada uno con
  driver, mitigación planificada e iteración.
- **Drivers no resueltos**: se devuelven explícitamente al backlog (estado `PENDIENTE`/`EN DISEÑO`).

## Conceptos ATAM que se usan

- **Sensitivity point** — una decisión de la que depende crítica­mente una respuesta de calidad.
- **Tradeoff point** — un sensitivity point que afecta a más de un atributo en direcciones opuestas.
- **Risk** — una decisión (o su ausencia) que puede impedir alcanzar la medida de respuesta.
- **Non-risk** — una decisión que, analizada, se confirma segura para los drivers en juego.

## Reglas del análisis

- **Adversarial y honesto**: el evaluador busca **refutar** que el ADR satisface sus drivers. Ante la
  duda, marca riesgo, no lo omitas. Es más barato un riesgo en papel que un rediseño en código.
- **Medida, no opinión**: un driver solo se marca ✅ si hay una medida verificable o un plan de
  verificación (k6, prueba de carga, matriz de RBAC, etc.). "Parece suficiente" es ⚠️.
- **No decide negocio**: si el riesgo se resuelve con una decisión de negocio (exponer o no un dato,
  fijar o aplazar un objetivo de DR), lo marca como **trade-off de negocio** → sube a la revisión única
  (fase 5), no lo resuelve el modelo.
- **Cierre trazable**: al mitigar un riesgo en una iteración posterior, se marca ✅ CERRADO en el backlog
  con el ADR que lo cerró; no se borra la fila.

## Cobertura (invariante del backlog)

Al cerrar la capa, **todo driver del 0000 debe tener estado ≥ ABORDADO** o un riesgo abierto explícito
que explique por qué no. Un driver crítico (A,A) en `PENDIENTE` sin riesgo declarado es un fallo de la
capa: no está lista para habilitar el build.
