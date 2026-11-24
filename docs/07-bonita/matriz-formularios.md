---
actualizado: 2026-11-24
capa: 3
motor: Bonita
deriva_de: docs/07-bonita/contratos.md, docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/00-parametros/catalogo-parametros.md, docs/08-construccion/plan-v2-bonita-first.md
total_formularios: 4
umbral_campos_unidad_propia: 10
---

# Capa 3 — Matriz de formularios y aplicación — Gestión de Preventa

> Fuente: `contratos.md`, `bpmn.md` y la decisión «Bonita-first» del 2026-11-24. La consultora asignada trabaja en dos formularios de Bonita (validar la solicitud y diseñar la propuesta) y en la vista del caso. Cada formulario **precarga todo** el ticket, el Negocio, la empresa y los contactos de HubSpot, **de solo lectura**, y deja editables solo los campos de su etapa. El diseño visual (marca Trycore) lo define la unidad de formularios; aquí, los campos.

## Convenciones

- **ID**: `frm_instanciacion`, `frm_<id-tarea>`, `frm_overview`.
- **Tipo**: `Instantiation form`, `Task form`, `Case overview`.
- **Form mapping**: `Svelte` (página de la Living Application del proyecto) o `No form`. `frm_instanciacion` es `No form`: el caso lo instancia el middleware por la API REST y ningún usuario lo abre.
- **Familia**: formularios con el mismo rol y la misma estructura de contrato.
- **Campo**: escribe en un input del contrato o lee de un objeto de `bdm.md` o de la REST API extension `preventaContexto`.
- **`preventaContexto`**: REST API extension de solo lectura (`GET …/API/extension/preventa/contexto?ticketId=<id>`) que devuelve un JSON con `ticket`, `deal`, `company`, `contacts` y `owner` leídos de HubSpot del lado servidor (el token nunca llega al navegador). La implementa otra unidad de trabajo (agente B). En la tabla de campos, `ctx.<objeto>.<propiedad>` es una propiedad de ese JSON; `ctx.<objeto>.*` es «todas las propiedades que devuelva, de solo lectura».

## Matriz de formularios

| Formulario | Tipo | Tarea BPMN | Actor | Contrato | Entradas del contrato | Objetos de negocio (lee / escribe) | Form mapping | Familia | Validaciones (resumen) | Componentes de galería |
|---|---|---|---|---|---|---|---|---|---|---|
| `frm_instanciacion` | Instantiation form | (inicio) | — (lo instancia el middleware) | `ctr_instanciacion` | `ticketId` | — / `Preventa` | No form | — | — | — |
| `frm_10_validarSolicitud` | Task form | `10_validarSolicitud` | Consultora (la asignada) | `ctr_10_validarSolicitud` | `resultado`, `conceptoViabilidad`, `notaValidacion`, `supuestos` | `Preventa` + `preventaContexto` / `Preventa` | Svelte | FAM-consultoras | espeja `resultado_valido`, `notaValidacion_presente`, `conceptoViabilidad_si_concluye` | — |
| `frm_20_disenarPropuesta` | Task form | `20_disenarPropuesta` | Consultora (la asignada) | `ctr_20_disenarPropuesta` | `valoracionOperaciones`, `urlPptaPreventa`, `linkRepoPreventa`, `notaPropuesta`, `adjuntos` | `Preventa` + `preventaContexto` / `Preventa` | Svelte | FAM-consultoras | espeja `valoracionOperaciones_presente`, `urlPptaPreventa_valida`, `linkRepoPreventa_valido` | — |
| `frm_overview` | Case overview | (pool) | Consultora | — | — | `Preventa` + `preventaContexto` / — | Svelte | FAM-consultoras | — | — |

## Detalle por formulario

### `frm_10_validarSolicitud` — Validar la solicitud

- **Tarea / contrato / actor**: `10_validarSolicitud` / `ctr_10_validarSolicitud` / Consultora (solo la asignada, actor filter `filtroConsultoraDelCaso`).
- **Form mapping**: Svelte.
- **Datos que carga al abrir** (solo lectura): `Preventa` del caso (ticket, asunto, consultor, fechas y, si la solicitud volvió de un bloqueo, la validación anterior) y, por `preventaContexto` con `Preventa.ticketId`, **todo** el ticket, el Negocio, la empresa, los contactos y el owner.
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId`, `ctx.ticket.subject`, `ctx.ticket.content`, `ctx.ticket.hs_ticket_priority`, `ctx.ticket.hs_pipeline_stage` | — | — | — | — | — |
| Todas las propiedades del ticket | Lista clave-valor (solo lectura, plegable) | — | `ctx.ticket.*` | — | — | — | — | — |
| Negocio | Text (solo lectura) | — | `ctx.deal.dealname`, `ctx.deal.amount`, `ctx.deal.dealstage`, `ctx.deal.*` (MEDDPICC y demás) | — | — | — | — | — |
| Empresa | Text (solo lectura) | — | `ctx.company.name`, `ctx.company.domain`, `ctx.company.*` | — | — | — | — | — |
| Contactos | Tabla (solo lectura) | — | `ctx.contacts[].firstname`, `lastname`, `email`, `phone`, `jobtitle` | — | — | — | — | — |
| Comercial / owner | Text (solo lectura) | — | `ctx.owner` | — | — | — | — | — |
| Consultora asignada | Text (solo lectura) | — | `Preventa.consultor`, `Preventa.fechaAsignacion` | — | — | — | — | — |
| Validación anterior | Text (solo lectura, solo si hubo bloqueo) | — | `Preventa.resultadoValidacion`, `Preventa.notaValidacion`, `Preventa.fechaValidacion` | — | — | — | — | — |
| Resultado | Radio buttons (viable / bloqueado / no viable) | `resultado` | — | sí | espeja `resultado_valido` | — | — | — |
| Concepto de viabilidad | Text area | `conceptoViabilidad` | `Preventa.conceptoViabilidad` (valor inicial) | no | espeja `conceptoViabilidad_si_concluye` | Resultado | — | — |
| Nota de validación | Text area (texto largo) | `notaValidacion` | — | sí | espeja `notaValidacion_presente` | — | — | — |
| Supuestos | Text area | `supuestos` | `Preventa.supuestos` (valor inicial) | no | — | — | — | — |

**Acciones**: Enviar (fija `resultado`, `conceptoViabilidad`, `notaValidacion`, `supuestos`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno (los conectores a HubSpot corren a la salida de la tarea).

### `frm_20_disenarPropuesta` — Diseñar la propuesta

- **Tarea / contrato / actor**: `20_disenarPropuesta` / `ctr_20_disenarPropuesta` / Consultora (solo la asignada, actor filter `filtroConsultoraDelCaso`).
- **Form mapping**: Svelte.
- **Datos que carga al abrir** (solo lectura): `Preventa` del caso, incluida la validación (resultado, concepto, nota, supuestos), y, por `preventaContexto`, **todo** el ticket, el Negocio, la empresa, los contactos y el owner.
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId`, `ctx.ticket.*` | — | — | — | — | — |
| Negocio | Text (solo lectura) | — | `ctx.deal.*` | — | — | — | — | — |
| Empresa | Text (solo lectura) | — | `ctx.company.*` | — | — | — | — | — |
| Contactos | Tabla (solo lectura) | — | `ctx.contacts[]` | — | — | — | — | — |
| Validación | Text (solo lectura) | — | `Preventa.resultadoValidacion`, `Preventa.conceptoViabilidad`, `Preventa.notaValidacion`, `Preventa.supuestos`, `Preventa.fechaValidacion` | — | — | — | — | — |
| Valoración de operaciones | Text area | `valoracionOperaciones` | `ctx.deal.valoracion_operaciones` (valor inicial) | sí | espeja `valoracionOperaciones_presente` | — | — | — |
| URL propuesta (presentación) | Text (URL) | `urlPptaPreventa` | `ctx.deal.url_ppta_preventa` (valor inicial) | sí | espeja `urlPptaPreventa_valida` | — | — | — |
| Link repositorio preventa | Text (URL) | `linkRepoPreventa` | `ctx.deal.link_repo_preventa` (valor inicial) | sí | espeja `linkRepoPreventa_valido` | — | — | — |
| Nota de propuesta | Text area | `notaPropuesta` | — | no | — | — | — | — |
| Adjuntos | File upload (múltiple) | `adjuntos` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `valoracionOperaciones`, `urlPptaPreventa`, `linkRepoPreventa`, `notaPropuesta`, `adjuntos`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_overview` — Vista del caso

- **Tarea / contrato / actor**: (pool) / — / Consultora.
- **Form mapping**: Svelte.
- **Datos que carga al abrir** (solo lectura): `Preventa` completo (estado, consultor, validación, artefactos, fechas de cada etapa) y, por `preventaContexto`, el ticket, el Negocio, la empresa y los contactos.
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Estado y etapas | Línea de tiempo (solo lectura) | — | `Preventa.estado`, `Preventa.fechaRecepcion`, `fechaAsignacion`, `fechaValidacion`, `fechaPropuesta`, `fechaEntrega` | — | — | — | — | — |
| Validación | Text (solo lectura) | — | `Preventa.resultadoValidacion`, `conceptoViabilidad`, `notaValidacion`, `supuestos` | — | — | — | — | — |
| Artefactos | Enlaces (solo lectura) | — | `Preventa.valoracionOperaciones`, `urlPptaPreventa`, `linkRepoPreventa`, `notaPropuesta` | — | — | — | — | — |
| CRM | Text (solo lectura) | — | `ctx.ticket.*`, `ctx.deal.*`, `ctx.company.*`, `ctx.contacts[]` | — | — | — | — | — |

**Acciones**: ninguna.
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

## Familias y unidades de trabajo

| Familia | Formularios | Rol | Campos (cada uno) | Unidad de trabajo propuesta | Justificación |
|---|---|---|---|---|---|
| FAM-consultoras | `frm_10_validarSolicitud`, `frm_20_disenarPropuesta`, `frm_overview` | `consultora` | 4–12 | una épica (`E-consultoras`) | los formularios de la consultora asignada comparten la precarga de `preventaContexto` y el diseño de marca |

## Aplicación (Living Application)

| Elemento | Valor |
|---|---|
| Application descriptor | la del proyecto (las páginas Svelte de los formularios; la bandeja es la de la Bonita User Application) |
| Perfiles con acceso | `User` (las consultoras) |
| Página de inicio | la de defecto |
| Layout / tema | los de la plantilla (marca Trycore en la unidad de formularios) |

## Acceso al BDM y permisos (decisión tomada en la capa 0, detallada aquí)

| Recurso | Mecanismo (BDM access control / REST API extension / consulta directa) | Perfiles o actores con acceso | Objetos y atributos expuestos | Fuente (visibilidad-por-familia.md) |
|---|---|---|---|---|
| `Preventa` | REST API extension de consultas del proyecto | `User`; actor `Consultora` | `Preventa` (el objeto raíz del caso) | — (sin restricciones por familia) |
| CRM de HubSpot | REST API extension `preventaContexto` (`GET …/API/extension/preventa/contexto?ticketId=`; solo lectura; token del lado servidor) | `User`; actor `Consultora` | ticket, Negocio, empresa, contactos, owner | — |

## Verificaciones de diseño (las revisa el gate)

- [x] Un registro por instanciación, por tarea humana y para el overview (o `No form` explícito).
- [x] Todo formulario con form mapping fijado.
- [x] Todo input del contrato tiene un campo; toda constraint está espejada en la UI.
- [x] Acceso al BDM decidido (REST API extensions; nada directo a `/API/bdm`).

## Pendientes de definición

- **Lista final de campos visibles por objeto**: hoy «todo de solo lectura» (`ctx.<objeto>.*`). La lista y el orden se ajustan tras leer el esquema real del Negocio y del ticket con el token ampliado.
- **`preventaContexto` sin permiso a un objeto** (p. ej. sin scope de empresas): el formulario debe mostrar «no disponible» y no bloquear el envío `[no verificado]`.
