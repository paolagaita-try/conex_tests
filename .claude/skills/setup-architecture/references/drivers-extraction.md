# Extracción de drivers / ASRs (ADD Paso 1) — referencia

Objetivo de la fase: producir `docs/adr/0000-drivers-y-asrs.md` **leyendo `docs/`** (solo lectura),
sobre la plantilla `assets/0000-drivers-y-asrs.template.md` de esta skill (frontmatter + §1–§7). Se
delega el barrido a `asr-extractor` (fan-out) y la sesión principal consolida. Un **ASR**
(Architecturally Significant Requirement) es un requisito que, si cambia, cambia la arquitectura.

## De dónde sale cada bloque del 0000

| Bloque del 0000 | Fuente en `docs/` | Cómo derivarlo |
|---|---|---|
| **OE** (objetivos de negocio) | `01-prd/` §objetivos, `02-user-story-map/` | Copiar los objetivos específicos + su métrica/meta. Si el PRD no da métrica, proponerla y marcarla como *a validar*. |
| **UC** (funcionales significativos) | `03-backlog/epicas.md`, `04-historias/HU-*.md` | **Solo** los casos que moldean la arquitectura (integraciones externas, transaccionalidad, RBAC, asincronía, auditoría). No es el backlog completo. |
| **QA** (escenarios de calidad) | PRD §requisitos no funcionales, AC de las HUs, §técnica | Un escenario de **6 partes** por atributo (rendimiento, disponibilidad, seguridad, integrabilidad, modificabilidad, observabilidad, escalabilidad…). La **medida** debe ser cuantificable. |
| **CON** (restricciones) | PRD §técnica/§7, política de datos, identidad | Lo que **no** es negociable (stack impuesto, prohibiciones, headers, gates de CI). |
| **CRN** (concerns) | PRD riesgos, capacidades del equipo, costos | Preocupaciones que condicionan el diseño aunque no sean requisitos formales. |
| **Prioridad** | juicio + importancia del PRD | Par `(Importancia de negocio, Impacto arquitectónico)` en {A,M,B}. El cuadrante (A,A) son los **ASRs críticos**. |
| **Plan de iteraciones** | fases del PRD / líneas de release del story map | Una iteración por fase; lista los drivers que ataca cada una. |

## Escenario QA de 6 partes (formato Bass)

Cada QA-N se escribe con exactamente estas seis partes:

- **Fuente** del estímulo (quién/qué lo genera)
- **Estímulo** (el evento)
- **Artefacto** (qué parte del sistema recibe el estímulo)
- **Entorno** (condiciones: normal, pico, degradado)
- **Respuesta** (qué hace el sistema)
- **Medida de respuesta** (cuantificable: P95 ≤ X ms, uptime ≥ X%, 0 incidentes…)

Sin medida cuantificable no es un ASR: es un deseo. Si el PRD no la da, **propón** una razonable y déjala
marcada para validación en la revisión (fase 5), no bloquees.

## Reglas

- **Traza siempre**: cada UC/QA cita las HU/OE/§PRD de las que sale (columna Trazabilidad).
- **No inventes dominio**: si un atributo no tiene sustento en `docs/`, no lo agregues; si es un hueco
  real (p.ej. el PRD no fija disponibilidad), decláralo como CRN o riesgo, no como QA fabricado.
- **Documento vivo**: en re-corridas, añade drivers nuevos de HUs/épicas nuevas; no borres los previos.
