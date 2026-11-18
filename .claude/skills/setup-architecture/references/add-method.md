# Método ADD — iterar el diseño (Pasos 2–7) — referencia

ADD (Attribute-Driven Design, Len Bass) diseña por **rondas**. Cada ronda ejecuta 7 pasos sobre un
subconjunto priorizado de drivers del catálogo `0000`. Una ronda produce **un ADR** (a veces refactoriza
uno previo). Usa la plantilla `assets/adr-add.template.md` de esta skill —instalada junto a estas
references— (7 secciones = los 7 pasos, con su frontmatter `id/title/date/status/authors/tags/add`).

## Los 7 pasos por iteración

1. **Review inputs** — ya está en `0000-drivers-y-asrs.md`.
2. **Establecer el objetivo de la iteración** — elige la fase/release y el subconjunto de drivers
   (empieza por los ASRs críticos, cuadrante (A,A) de la matriz). → §1 del ADR.
3. **Elegir el elemento a refinar** — sistema completo (primera ronda, top-down) o un módulo/servicio
   interno (rondas posteriores). → §1 del ADR.
4. **Elegir conceptos de diseño** — **tácticas** (Bass), **patrones**/estilos, componentes externos o
   arquitecturas de referencia. Registra las **alternativas descartadas** y por qué. → §2 del ADR.
5. **Instanciar** — convierte los conceptos en componentes/módulos reales con responsabilidades e
   **interfaces/contratos**. → §3 del ADR.
6. **Bocetar vistas y registrar la decisión** — al menos una vista (módulos, C&C o despliegue) en
   `mermaid`, con la **decisión** y sus **trade-offs**. → §4 del ADR.
7. **Analizar** (ATAM-lite) — cada driver con veredicto y evidencia; drivers no resueltos vuelven al
   backlog. → §5 del ADR (delegado a `architecture-evaluator`; ver `atam-lite.md`).

## Tácticas ↔ atributos (guía rápida, no exhaustiva)

| Atributo (QA) | Tácticas típicas (Bass) | Estilos/patrones que las agrupan |
|---|---|---|
| Disponibilidad | redundancia, detección (heartbeat/ping), recuperación (rollback, reintento con backoff) | activo-pasivo, health-check, circuit breaker |
| Rendimiento | gestión de recursos (índices, caché), gestión de demanda (paginación, rate-limit) | CQRS de lectura, caché-aside |
| Seguridad | resistir (authN/authZ, secretos fuera de código), detectar (auditoría), recuperar | RBAC central, gateway de seguridad, WORM/SIEM |
| Modificabilidad | encapsular, intermediario, restringir dependencias | capas, hexagonal/puertos-adaptadores, contrato OpenAPI como fuente |
| Integrabilidad | adaptador, orquestación, límite (bulkhead) | adaptadores por integración, anti-corruption layer |
| Escalabilidad | replicación, particionamiento, trabajo asíncrono | workers, colas, outbox |
| Integridad transaccional | transacción, compensación (saga), idempotencia | saga orquestada + outbox |

## Estrategia de iteración

- **Ancho antes que profundo**: primera ronda decide el estilo estructural y el stack del **sistema
  completo**; rondas posteriores refinan piezas (worker, motor de notificaciones, servicio de RBAC…).
- **Cimiento primero**: las decisiones fundacionales (identidad/authN, acceso a datos, arquitectura base,
  design-system) van en las primeras iteraciones — son las que el DoR exigirá antes de abrir épicas de
  negocio (`layer: foundational`).
- **Un ADR por decisión coherente**, no por archivo tocado. Si una decisión supersede a otra, marca la
  vieja `superseded` y enlaza; no borres.
- **Stack como decisión trazada**: las elecciones de lenguaje/framework/BD/infra son ADRs con su §2
  (alternativas descartadas). En la fase 5 se consolidan en `stack-allowlist.json`. Si el stack elegido
  **diverge** del PRD §técnica, regístralo explícitamente como riesgo/restricción (no lo escondas).

## Salida por ronda

1. Escribe `docs/adr/000N-<slug>.md` desde la plantilla, con §1–§4 completas.
2. Corre `architecture-evaluator` sobre el ADR → completa §5 y §6.
3. Actualiza `_backlog-arquitectonico.md`: estado de cada driver, riesgos nuevos, fila de bitácora.
