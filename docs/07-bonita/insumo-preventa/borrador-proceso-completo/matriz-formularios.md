---
actualizado: 2026-11-12
capa: 3
motor: Bonita
deriva_de: docs/07-bonita/contratos.md, docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/00-parametros/catalogo-parametros.md
total_formularios: 36
umbral_campos_unidad_propia: 10
---

# Capa 3 — Matriz de formularios y aplicación — Gestión de Preventa

> Fuente: `contratos.md`, `bpmn.md` y `bdm.md`. Un registro por formulario de instanciación, por formulario de tarea y por case overview. No hay prototipo ni diseño visual todavía (`docs/05-prototipo/` vacío): los controles son los widgets estándar de la plantilla Svelte.

## Convenciones

- **ID**: `frm_instanciacion`, `frm_<id-tarea>`, `frm_overview`.
- **Tipo**: `Instantiation form`, `Task form`, `Case overview`.
- **Form mapping**: `Svelte` (página de la Living Application `preventa`, mapeada por URL `/bonita/portal/resource/app/preventa/<formulario>/content/`) o `No form`. `frm_instanciacion` es `No form`: el caso lo instancia el middleware por la API REST y ningún usuario lo abre.
- **Familia**: formularios con el mismo rol y la misma estructura de contrato.
- **Campo**: escribe en un input del contrato o lee de un objeto de `bdm.md`.

## Matriz de formularios

| Formulario | Tipo | Tarea BPMN | Actor | Contrato | Entradas del contrato | Objetos de negocio (lee / escribe) | Form mapping | Familia | Validaciones (resumen) | Componentes de galería |
|---|---|---|---|---|---|---|---|---|---|---|
| `frm_instanciacion` | Instantiation form | (inicio) | — (lo instancia el middleware Ofelia) | `ctr_instanciacion` | `ticketId` | — / `Preventa` | No form | — | — | — |
| `frm_7_analizarRequerimiento` | Task form | `7_analizarRequerimiento` | ConsultorPreventa | `ctr_7_analizarRequerimiento` | `tipoAtencion`, `informacionSuficiente`, `requiereViabilidad` | `Preventa` / `Preventa` | Svelte | FAM-consultor-decision | espeja `tipoAtencion_valido` | — |
| `frm_8_identificarProducto` | Task form | `8_identificarProducto` | ConsultorPreventa | `ctr_8_identificarProducto` | `productoDemo`, `origenDocumentosDemo` | `Preventa` / `Preventa` | Svelte | FAM-consultor-decision | espeja `productoDemo_valido`; espeja `origenDocumentosDemo_valido` | — |
| `frm_9_prepararDemoCliente` | Task form | `9_prepararDemoCliente` | ConsultorPreventa | `ctr_9_prepararDemoCliente` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_10_prepararDemoGuia` | Task form | `10_prepararDemoGuia` | ConsultorPreventa | `ctr_10_prepararDemoGuia` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_11_construirDocumentosEjemplo` | Task form | `11_construirDocumentosEjemplo` | ConsultorPreventa | `ctr_11_construirDocumentosEjemplo` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_12_ejecutarDemo` | Task form | `12_ejecutarDemo` | ConsultorPreventa | `ctr_12_ejecutarDemo` | `clienteAvanza`, `informacionSuficiente`, `observacionDemo`, `requiereViabilidad` | `Preventa` / `Preventa` | Svelte | FAM-consultor-decision | obligatorios del contrato | — |
| `frm_13_registrarNoContinua` | Task form | `13_registrarNoContinua` | Comercial | `ctr_13_registrarNoContinua` | `motivoDescarte` | `Preventa` / `Preventa` | Svelte | FAM-comercial-captura | obligatorios del contrato | — |
| `frm_32_analizarLicitacion` | Task form | `32_analizarLicitacion` | ConsultorPreventa | `ctr_32_analizarLicitacion` | `requierePreguntas`, `requiereViabilidad` | `Preventa` / — | Svelte | FAM-consultor-decision | obligatorios del contrato | — |
| `frm_33_elaborarPreguntas` | Task form | `33_elaborarPreguntas` | ConsultorPreventa | `ctr_33_elaborarPreguntas` | `preguntasAclaratorias` | `Preventa` / `Preventa` | Svelte | FAM-consultor-captura | obligatorios del contrato | — |
| `frm_37_radicarPreguntas` | Task form | `37_radicarPreguntas` | Comercial | `ctr_37_radicarPreguntas` | — | `Preventa` / `Preventa` | Svelte | FAM-comercial-confirmacion | — | — |
| `frm_34_esperarRespuestas` | Task form | `34_esperarRespuestas` | ConsultorPreventa | `ctr_34_esperarRespuestas` | `respuestasCompletas`, `respuestasEntidad`, `requiereViabilidad` | `Preventa` / `Preventa` | Svelte | FAM-consultor-decision | obligatorios del contrato | — |
| `frm_35_definirSupuestos` | Task form | `35_definirSupuestos` | ConsultorPreventa | `ctr_35_definirSupuestos` | `supuestos`, `requiereViabilidad` | `Preventa` / `Preventa` | Svelte | FAM-consultor-captura | obligatorios del contrato | — |
| `frm_14_realizarLevantamiento` | Task form | `14_realizarLevantamiento` | ConsultorPreventa | `ctr_14_realizarLevantamiento` | `entregaDocumentos`, `enlaceGrabacion`, `requiereViabilidad` | `Preventa` / `Preventa` | Svelte | FAM-consultor-decision | obligatorios del contrato | — |
| `frm_42_analizarDocumentos` | Task form | `42_analizarDocumentos` | ConsultorPreventa | `ctr_42_analizarDocumentos` | `requiereViabilidad` | `Preventa` / — | Svelte | FAM-consultor-captura | — | — |
| `frm_38_validarViabilidad` | Task form | `38_validarViabilidad` | LiderTecnico | `ctr_38_validarViabilidad` | `esViable`, `conceptoViabilidad` | `Preventa` / `Preventa` | Svelte | FAM-lider | obligatorios del contrato | — |
| `frm_39_notificarNoViabilidad` | Task form | `39_notificarNoViabilidad` | ConsultorPreventa | `ctr_39_notificarNoViabilidad` | — | `Preventa` / `Preventa` | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_31_prepararAnalisis` | Task form | `31_prepararAnalisis` | ConsultorPreventa | `ctr_31_prepararAnalisis` | `enlaceInsumos` | `Preventa` / `Preventa` | Svelte | FAM-consultor-captura | obligatorios del contrato | — |
| `frm_15_cargarInsumos` | Task form | `15_cargarInsumos` | ConsultorPreventa | `ctr_15_cargarInsumos` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_17_revisarArtefactos` | Task form | `17_revisarArtefactos` | ConsultorPreventa | `ctr_17_revisarArtefactos` | `enlacePropuesta`, `enlacePresentacion` | `Preventa` / `Preventa` | Svelte | FAM-consultor-captura | obligatorios del contrato | — |
| `frm_36_revisarEstimacion` | Task form | `36_revisarEstimacion` | LiderTecnico | `ctr_36_revisarEstimacion` | `enlaceEstimacion` | `Preventa` / `Preventa` | Svelte | FAM-lider | obligatorios del contrato | — |
| `frm_18_cargarArtefactos` | Task form | `18_cargarArtefactos` | ConsultorPreventa | `ctr_18_cargarArtefactos` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_19_socializarPropuesta` | Task form | `19_socializarPropuesta` | ConsultorPreventa | `ctr_19_socializarPropuesta` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_41_presentarPropuestaTecnica` | Task form | `41_presentarPropuestaTecnica` | ConsultorPreventa | `ctr_41_presentarPropuestaTecnica` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_20_presentarPropuestaEconomica` | Task form | `20_presentarPropuestaEconomica` | Comercial | `ctr_20_presentarPropuestaEconomica` | — | `Preventa` / — | Svelte | FAM-comercial-confirmacion | — | — |
| `frm_21_validarAlcance` | Task form | `21_validarAlcance` | Comercial | `ctr_21_validarAlcance` | `alcanceCorrecto`, `observacionAlcance` | `Preventa` / `Preventa` | Svelte | FAM-comercial-decision | obligatorios del contrato | — |
| `frm_22_ajustarPropuesta` | Task form | `22_ajustarPropuesta` | ConsultorPreventa | `ctr_22_ajustarPropuesta` | `ajustesPropuesta` | `Preventa` / `Preventa` | Svelte | FAM-consultor-captura | obligatorios del contrato | — |
| `frm_23_validarAjustes` | Task form | `23_validarAjustes` | Comercial | `ctr_23_validarAjustes` | — | `Preventa` / `Preventa` | Svelte | FAM-comercial-confirmacion | — | — |
| `frm_24_enviarPropuestaFormal` | Task form | `24_enviarPropuestaFormal` | Comercial | `ctr_24_enviarPropuestaFormal` | — | `Preventa` / `Preventa` | Svelte | FAM-comercial-confirmacion | — | — |
| `frm_25_confirmarPropuesta` | Task form | `25_confirmarPropuesta` | Comercial | `ctr_25_confirmarPropuesta` | `propuestaAprobada` | `Preventa` / — | Svelte | FAM-comercial-decision | obligatorios del contrato | — |
| `frm_26_registrarRechazo` | Task form | `26_registrarRechazo` | Comercial | `ctr_26_registrarRechazo` | `motivoRechazo` | `Preventa` / `Preventa` | Svelte | FAM-comercial-captura | obligatorios del contrato | — |
| `frm_27_cerrarGanado` | Task form | `27_cerrarGanado` | Comercial | `ctr_27_cerrarGanado` | — | `Preventa` / `Preventa` | Svelte | FAM-comercial-confirmacion | — | — |
| `frm_28_presentarAlcanceTraspaso` | Task form | `28_presentarAlcanceTraspaso` | ConsultorPreventa | `ctr_28_presentarAlcanceTraspaso` | — | `Preventa` / — | Svelte | FAM-consultor-confirmacion | — | — |
| `frm_29_entregarCarpeta` | Task form | `29_entregarCarpeta` | ConsultorPreventa | `ctr_29_entregarCarpeta` | `enlaceCarpeta` | `Preventa` / `Preventa` | Svelte | FAM-consultor-captura | obligatorios del contrato | — |
| `frm_30_iniciarEjecucion` | Task form | `30_iniciarEjecucion` | EquipoInterno | `ctr_30_iniciarEjecucion` | — | `Preventa` / `Preventa` | Svelte | FAM-interno | — | — |
| `frm_overview` | Case overview | (pool) | Comercial, ConsultorPreventa, LiderTecnico, EquipoInterno | — | — | `Preventa` / — | No form | — | — | — |

## Detalle por formulario

### `frm_7_analizarRequerimiento` — Analizar MEDDPICC y requerimiento

- **Tarea / contrato / actor**: `7_analizarRequerimiento` / `ctr_7_analizarRequerimiento` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm7AnalizarRequerimiento` (URL `/bonita/portal/resource/app/preventa/frm7AnalizarRequerimiento/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.descripcion`, `Preventa.medpicc`, `Preventa.tipoRequerimiento`, `Preventa.comercialCreador`, `Preventa.linkRepositorio` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Descripcion | Text (solo lectura) | — | `Preventa.descripcion` | — | — | — | — | — |
| Medpicc | Text (solo lectura) | — | `Preventa.medpicc` | — | — | — | — | — |
| TipoRequerimiento | Text (solo lectura) | — | `Preventa.tipoRequerimiento` | — | — | — | — | — |
| ComercialCreador | Text (solo lectura) | — | `Preventa.comercialCreador` | — | — | — | — | — |
| LinkRepositorio | Text (solo lectura) | — | `Preventa.linkRepositorio` | — | — | — | — | — |
| Tipo de atención | Radio buttons (demo / licitacion / propuesta) | `tipoAtencion` | — | sí | espeja `tipoAtencion_valido` | — | — | — |
| ¿La información es suficiente para la propuesta? | Radio buttons (sí / no) | `informacionSuficiente` | — | sí | propia de UI: una opción elegida | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `tipoAtencion`, `informacionSuficiente`, `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_8_identificarProducto` — Identificar producto del demo (DocFly / Oriuno)

- **Tarea / contrato / actor**: `8_identificarProducto` / `ctr_8_identificarProducto` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm8IdentificarProducto` (URL `/bonita/portal/resource/app/preventa/frm8IdentificarProducto/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Producto del demo | Radio buttons (docfly / oriuno) | `productoDemo` | — | sí | espeja `productoDemo_valido` | — | — | — |
| Documentos con los que se prepara la demo | Radio buttons (cliente / guia / ejemplo) | `origenDocumentosDemo` | — | sí | espeja `origenDocumentosDemo_valido` | — | — | — |

**Acciones**: Enviar (fija `productoDemo`, `origenDocumentosDemo`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_9_prepararDemoCliente` — Preparar demo con documentos del cliente

- **Tarea / contrato / actor**: `9_prepararDemoCliente` / `ctr_9_prepararDemoCliente` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm9PrepararDemoCliente` (URL `/bonita/portal/resource/app/preventa/frm9PrepararDemoCliente/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_10_prepararDemoGuia` — Preparar demo con documentos guía

- **Tarea / contrato / actor**: `10_prepararDemoGuia` / `ctr_10_prepararDemoGuia` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm10PrepararDemoGuia` (URL `/bonita/portal/resource/app/preventa/frm10PrepararDemoGuia/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_11_construirDocumentosEjemplo` — Construir documentos de ejemplo para el caso

- **Tarea / contrato / actor**: `11_construirDocumentosEjemplo` / `ctr_11_construirDocumentosEjemplo` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm11ConstruirDocumentosEjemplo` (URL `/bonita/portal/resource/app/preventa/frm11ConstruirDocumentosEjemplo/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_12_ejecutarDemo` — Ejecutar demo con el cliente

- **Tarea / contrato / actor**: `12_ejecutarDemo` / `ctr_12_ejecutarDemo` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm12EjecutarDemo` (URL `/bonita/portal/resource/app/preventa/frm12EjecutarDemo/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| ¿El cliente avanza? | Radio buttons (sí / no) | `clienteAvanza` | — | sí | propia de UI: una opción elegida | — | — | — |
| ¿La información es suficiente para la propuesta? | Radio buttons (sí / no) | `informacionSuficiente` | — | sí | propia de UI: una opción elegida | — | — | — |
| Observaciones de la demo | Text area | `observacionDemo` | — | no | — | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `clienteAvanza`, `informacionSuficiente`, `observacionDemo`, `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_13_registrarNoContinua` — Actualizar estado en HubSpot (no continúa)

- **Tarea / contrato / actor**: `13_registrarNoContinua` / `ctr_13_registrarNoContinua` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm13RegistrarNoContinua` (URL `/bonita/portal/resource/app/preventa/frm13RegistrarNoContinua/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Motivo por el que no continúa | Text area | `motivoDescarte` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `motivoDescarte`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_32_analizarLicitacion` — Analizar insumos de la licitación (pliegos / TDR)

- **Tarea / contrato / actor**: `32_analizarLicitacion` / `ctr_32_analizarLicitacion` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm32AnalizarLicitacion` (URL `/bonita/portal/resource/app/preventa/frm32AnalizarLicitacion/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| ¿Requiere preguntas aclaratorias? | Radio buttons (sí / no) | `requierePreguntas` | — | sí | propia de UI: una opción elegida | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `requierePreguntas`, `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_33_elaborarPreguntas` — Elaborar preguntas y cargarlas en el ticket

- **Tarea / contrato / actor**: `33_elaborarPreguntas` / `ctr_33_elaborarPreguntas` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm33ElaborarPreguntas` (URL `/bonita/portal/resource/app/preventa/frm33ElaborarPreguntas/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Preguntas aclaratorias | Text area | `preguntasAclaratorias` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `preguntasAclaratorias`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_37_radicarPreguntas` — Radicar o enviar preguntas a la entidad

- **Tarea / contrato / actor**: `37_radicarPreguntas` / `ctr_37_radicarPreguntas` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm37RadicarPreguntas` (URL `/bonita/portal/resource/app/preventa/frm37RadicarPreguntas/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.preguntasAclaratorias` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| PreguntasAclaratorias | Text (solo lectura) | — | `Preventa.preguntasAclaratorias` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_34_esperarRespuestas` — Esperar y registrar las respuestas de la entidad

- **Tarea / contrato / actor**: `34_esperarRespuestas` / `ctr_34_esperarRespuestas` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm34EsperarRespuestas` (URL `/bonita/portal/resource/app/preventa/frm34EsperarRespuestas/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.preguntasAclaratorias` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| PreguntasAclaratorias | Text (solo lectura) | — | `Preventa.preguntasAclaratorias` | — | — | — | — | — |
| ¿Las respuestas son completas? | Radio buttons (sí / no) | `respuestasCompletas` | — | sí | propia de UI: una opción elegida | — | — | — |
| Respuestas de la entidad | Text area | `respuestasEntidad` | — | no | — | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `respuestasCompletas`, `respuestasEntidad`, `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_35_definirSupuestos` — Definir supuestos para la propuesta

- **Tarea / contrato / actor**: `35_definirSupuestos` / `ctr_35_definirSupuestos` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm35DefinirSupuestos` (URL `/bonita/portal/resource/app/preventa/frm35DefinirSupuestos/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.preguntasAclaratorias`, `Preventa.respuestasEntidad` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| PreguntasAclaratorias | Text (solo lectura) | — | `Preventa.preguntasAclaratorias` | — | — | — | — | — |
| RespuestasEntidad | Text (solo lectura) | — | `Preventa.respuestasEntidad` | — | — | — | — | — |
| Supuestos de la propuesta | Text area | `supuestos` | — | sí | propia de UI: no vacío | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `supuestos`, `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_14_realizarLevantamiento` — Realizar sesión de levantamiento y solicitar documentación de referencia

- **Tarea / contrato / actor**: `14_realizarLevantamiento` / `ctr_14_realizarLevantamiento` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm14RealizarLevantamiento` (URL `/bonita/portal/resource/app/preventa/frm14RealizarLevantamiento/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| ¿El cliente entrega documentos de referencia? | Radio buttons (sí / no) | `entregaDocumentos` | — | sí | propia de UI: una opción elegida | — | — | — |
| Enlace a la grabación y transcripción | Input (texto) | `enlaceGrabacion` | — | no | — | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `entregaDocumentos`, `enlaceGrabacion`, `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_42_analizarDocumentos` — Analizar documentos e insumos de referencia del cliente

- **Tarea / contrato / actor**: `42_analizarDocumentos` / `ctr_42_analizarDocumentos` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm42AnalizarDocumentos` (URL `/bonita/portal/resource/app/preventa/frm42AnalizarDocumentos/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| ¿Requiere validar la viabilidad técnica? | Radio buttons (sí / no) | `requiereViabilidad` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `requiereViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_38_validarViabilidad` — Validar viabilidad técnica

- **Tarea / contrato / actor**: `38_validarViabilidad` / `ctr_38_validarViabilidad` / LiderTecnico.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm38ValidarViabilidad` (URL `/bonita/portal/resource/app/preventa/frm38ValidarViabilidad/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.descripcion`, `Preventa.medpicc` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Descripcion | Text (solo lectura) | — | `Preventa.descripcion` | — | — | — | — | — |
| Medpicc | Text (solo lectura) | — | `Preventa.medpicc` | — | — | — | — | — |
| ¿El requerimiento es viable? | Radio buttons (sí / no) | `esViable` | — | sí | propia de UI: una opción elegida | — | — | — |
| Concepto de viabilidad técnica | Text area | `conceptoViabilidad` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `esViable`, `conceptoViabilidad`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_39_notificarNoViabilidad` — Notificar y socializar no viabilidad con Comercial

- **Tarea / contrato / actor**: `39_notificarNoViabilidad` / `ctr_39_notificarNoViabilidad` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm39NotificarNoViabilidad` (URL `/bonita/portal/resource/app/preventa/frm39NotificarNoViabilidad/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.conceptoViabilidad` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| ConceptoViabilidad | Text (solo lectura) | — | `Preventa.conceptoViabilidad` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_31_prepararAnalisis` — Preparar análisis de documentos para el agente IA

- **Tarea / contrato / actor**: `31_prepararAnalisis` / `ctr_31_prepararAnalisis` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm31PrepararAnalisis` (URL `/bonita/portal/resource/app/preventa/frm31PrepararAnalisis/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Enlace al paquete de insumos estructurado | Input (texto) | `enlaceInsumos` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `enlaceInsumos`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_15_cargarInsumos` — Cargar insumos al agente IA

- **Tarea / contrato / actor**: `15_cargarInsumos` / `ctr_15_cargarInsumos` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm15CargarInsumos` (URL `/bonita/portal/resource/app/preventa/frm15CargarInsumos/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlaceInsumos` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlaceInsumos | Text (solo lectura) | — | `Preventa.enlaceInsumos` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_17_revisarArtefactos` — Revisar y ajustar artefactos

- **Tarea / contrato / actor**: `17_revisarArtefactos` / `ctr_17_revisarArtefactos` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm17RevisarArtefactos` (URL `/bonita/portal/resource/app/preventa/frm17RevisarArtefactos/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlaceEstimacion | Text (solo lectura) | — | `Preventa.enlaceEstimacion` | — | — | — | — | — |
| EnlacePresentacion | Text (solo lectura) | — | `Preventa.enlacePresentacion` | — | — | — | — | — |
| Enlace a la propuesta | Input (texto) | `enlacePropuesta` | — | sí | propia de UI: no vacío | — | — | — |
| Enlace a la presentación | Input (texto) | `enlacePresentacion` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `enlacePropuesta`, `enlacePresentacion`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_36_revisarEstimacion` — Revisar y generar estimación con Líder Técnico

- **Tarea / contrato / actor**: `36_revisarEstimacion` / `ctr_36_revisarEstimacion` / LiderTecnico.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm36RevisarEstimacion` (URL `/bonita/portal/resource/app/preventa/frm36RevisarEstimacion/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlaceEstimacion | Text (solo lectura) | — | `Preventa.enlaceEstimacion` | — | — | — | — | — |
| Enlace a la estimación validada | Input (texto) | `enlaceEstimacion` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `enlaceEstimacion`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_18_cargarArtefactos` — Cargar artefactos en el lead de HubSpot (etapa «Preventa / Solución GH»)

- **Tarea / contrato / actor**: `18_cargarArtefactos` / `ctr_18_cargarArtefactos` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm18CargarArtefactos` (URL `/bonita/portal/resource/app/preventa/frm18CargarArtefactos/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlaceEstimacion | Text (solo lectura) | — | `Preventa.enlaceEstimacion` | — | — | — | — | — |
| EnlacePresentacion | Text (solo lectura) | — | `Preventa.enlacePresentacion` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_19_socializarPropuesta` — Socializar propuesta con Comercial

- **Tarea / contrato / actor**: `19_socializarPropuesta` / `ctr_19_socializarPropuesta` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm19SocializarPropuesta` (URL `/bonita/portal/resource/app/preventa/frm19SocializarPropuesta/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlaceEstimacion | Text (solo lectura) | — | `Preventa.enlaceEstimacion` | — | — | — | — | — |
| EnlacePresentacion | Text (solo lectura) | — | `Preventa.enlacePresentacion` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_41_presentarPropuestaTecnica` — Presentar propuesta técnica: alcance, solución y cronograma

- **Tarea / contrato / actor**: `41_presentarPropuestaTecnica` / `ctr_41_presentarPropuestaTecnica` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm41PresentarPropuestaTecnica` (URL `/bonita/portal/resource/app/preventa/frm41PresentarPropuestaTecnica/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlacePresentacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlacePresentacion | Text (solo lectura) | — | `Preventa.enlacePresentacion` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_20_presentarPropuestaEconomica` — Presentar propuesta económica (presupuesto)

- **Tarea / contrato / actor**: `20_presentarPropuestaEconomica` / `ctr_20_presentarPropuestaEconomica` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm20PresentarPropuestaEconomica` (URL `/bonita/portal/resource/app/preventa/frm20PresentarPropuestaEconomica/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlaceEstimacion | Text (solo lectura) | — | `Preventa.enlaceEstimacion` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_21_validarAlcance` — Validar alcance de la propuesta

- **Tarea / contrato / actor**: `21_validarAlcance` / `ctr_21_validarAlcance` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm21ValidarAlcance` (URL `/bonita/portal/resource/app/preventa/frm21ValidarAlcance/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| ¿El cliente valida el alcance? | Radio buttons (sí / no) | `alcanceCorrecto` | — | sí | propia de UI: una opción elegida | — | — | — |
| Ajustes solicitados por el cliente | Text area | `observacionAlcance` | — | no | — | — | — | — |

**Acciones**: Enviar (fija `alcanceCorrecto`, `observacionAlcance`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_22_ajustarPropuesta` — Ajustar propuesta

- **Tarea / contrato / actor**: `22_ajustarPropuesta` / `ctr_22_ajustarPropuesta` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm22AjustarPropuesta` (URL `/bonita/portal/resource/app/preventa/frm22AjustarPropuesta/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.observacionAlcance`, `Preventa.enlacePropuesta` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| ObservacionAlcance | Text (solo lectura) | — | `Preventa.observacionAlcance` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| Ajustes realizados | Text area | `ajustesPropuesta` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `ajustesPropuesta`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_23_validarAjustes` — Validar ajustes («Negociación / Ajustes»)

- **Tarea / contrato / actor**: `23_validarAjustes` / `ctr_23_validarAjustes` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm23ValidarAjustes` (URL `/bonita/portal/resource/app/preventa/frm23ValidarAjustes/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.ajustesPropuesta`, `Preventa.enlacePropuesta` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| AjustesPropuesta | Text (solo lectura) | — | `Preventa.ajustesPropuesta` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_24_enviarPropuestaFormal` — Enviar propuesta formal y mover lead a «Propuesta enviada»

- **Tarea / contrato / actor**: `24_enviarPropuestaFormal` / `ctr_24_enviarPropuestaFormal` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm24EnviarPropuestaFormal` (URL `/bonita/portal/resource/app/preventa/frm24EnviarPropuestaFormal/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_25_confirmarPropuesta` — Confirmar propuesta

- **Tarea / contrato / actor**: `25_confirmarPropuesta` / `ctr_25_confirmarPropuesta` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm25ConfirmarPropuesta` (URL `/bonita/portal/resource/app/preventa/frm25ConfirmarPropuesta/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| ¿El cliente aprueba la propuesta? | Radio buttons (sí / no) | `propuestaAprobada` | — | sí | propia de UI: una opción elegida | — | — | — |

**Acciones**: Enviar (fija `propuestaAprobada`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_26_registrarRechazo` — Registrar rechazo y motivo en HubSpot

- **Tarea / contrato / actor**: `26_registrarRechazo` / `ctr_26_registrarRechazo` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm26RegistrarRechazo` (URL `/bonita/portal/resource/app/preventa/frm26RegistrarRechazo/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Motivo del rechazo | Text area | `motivoRechazo` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `motivoRechazo`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_27_cerrarGanado` — Pasar a «Cerrado ganado» y convocar traspaso

- **Tarea / contrato / actor**: `27_cerrarGanado` / `ctr_27_cerrarGanado` / Comercial.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm27CerrarGanado` (URL `/bonita/portal/resource/app/preventa/frm27CerrarGanado/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_28_presentarAlcanceTraspaso` — Presentar alcance en sesión interna de traspaso

- **Tarea / contrato / actor**: `28_presentarAlcanceTraspaso` / `ctr_28_presentarAlcanceTraspaso` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm28PresentarAlcanceTraspaso` (URL `/bonita/portal/resource/app/preventa/frm28PresentarAlcanceTraspaso/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlacePropuesta | Text (solo lectura) | — | `Preventa.enlacePropuesta` | — | — | — | — | — |
| EnlaceEstimacion | Text (solo lectura) | — | `Preventa.enlaceEstimacion` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_29_entregarCarpeta` — Entregar carpeta de documentación a Procesos

- **Tarea / contrato / actor**: `29_entregarCarpeta` / `ctr_29_entregarCarpeta` / ConsultorPreventa.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm29EntregarCarpeta` (URL `/bonita/portal/resource/app/preventa/frm29EntregarCarpeta/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| Enlace a la carpeta «Prospectos de Preventa» del cliente | Input (texto) | `enlaceCarpeta` | — | sí | propia de UI: no vacío | — | — | — |

**Acciones**: Enviar (fija `enlaceCarpeta`).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

### `frm_30_iniciarEjecucion` — Recibir carpeta e iniciar ejecución del proyecto

- **Tarea / contrato / actor**: `30_iniciarEjecucion` / `ctr_30_iniciarEjecucion` / EquipoInterno.
- **Form mapping**: Svelte. Aplicación `preventa`, página `frm30IniciarEjecucion` (URL `/bonita/portal/resource/app/preventa/frm30IniciarEjecucion/content/`).
- **Datos que carga al abrir** (solo lectura): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlaceCarpeta` (business variable `preventa` del caso, por la REST API extension `consultas/caso`).
- **Familia visible** (si `visibilidad-por-familia.md` aplica): no aplica (sin restricciones por familia).

| Campo | Control / widget | Input del contrato (escribe) | Objeto.atributo o consulta (lee) | Obligatorio | Validación (espeja constraint / propia de UI) | Depende de | Catálogo `param_*` | Visibilidad restringida |
|---|---|---|---|---|---|---|---|---|
| Ticket | Text (solo lectura) | — | `Preventa.ticketId` | — | — | — | — | — |
| Asunto | Text (solo lectura) | — | `Preventa.asunto` | — | — | — | — | — |
| Estado | Text (solo lectura) | — | `Preventa.estado` | — | — | — | — | — |
| EnlaceCarpeta | Text (solo lectura) | — | `Preventa.enlaceCarpeta` | — | — | — | — | — |

**Acciones**: Marcar como hecha (envía el contrato vacío).
**Conector síncrono invocado desde el formulario** (si aplica, `catalogo-conectores.md`): ninguno.

`frm_instanciacion` y `frm_overview` no tienen detalle: son `No form`.

## Familias y unidades de trabajo

| Familia | Formularios | Rol | Campos (cada uno) | Unidad de trabajo propuesta | Justificación |
|---|---|---|---|---|---|
| FAM-consultor-decision | `frm_7_analizarRequerimiento`, `frm_8_identificarProducto`, `frm_12_ejecutarDemo`, `frm_32_analizarLicitacion`, `frm_34_esperarRespuestas`, `frm_14_realizarLevantamiento` | `consultor` | 5–11 | una épica | formularios que capturan la decisión de una compuerta; ninguno supera el umbral |
| FAM-consultor-confirmacion | `frm_9_prepararDemoCliente`, `frm_10_prepararDemoGuia`, `frm_11_construirDocumentosEjemplo`, `frm_39_notificarNoViabilidad`, `frm_15_cargarInsumos`, `frm_18_cargarArtefactos`, `frm_19_socializarPropuesta`, `frm_41_presentarPropuestaTecnica`, `frm_28_presentarAlcanceTraspaso` | `consultor` | 3–6 | una épica | formularios sin inputs: muestran el caso y dan la tarea por hecha; ninguno supera el umbral |
| FAM-comercial-captura | `frm_13_registrarNoContinua`, `frm_26_registrarRechazo` | `comercial` | 4 | una épica | formularios que capturan texto o enlaces de un entregable; ninguno supera el umbral |
| FAM-consultor-captura | `frm_33_elaborarPreguntas`, `frm_35_definirSupuestos`, `frm_42_analizarDocumentos`, `frm_31_prepararAnalisis`, `frm_17_revisarArtefactos`, `frm_22_ajustarPropuesta`, `frm_29_entregarCarpeta` | `consultor` | 4–8 | una épica | formularios que capturan texto o enlaces de un entregable; ninguno supera el umbral |
| FAM-comercial-confirmacion | `frm_37_radicarPreguntas`, `frm_20_presentarPropuestaEconomica`, `frm_23_validarAjustes`, `frm_24_enviarPropuestaFormal`, `frm_27_cerrarGanado` | `comercial` | 3–5 | una épica | formularios sin inputs: muestran el caso y dan la tarea por hecha; ninguno supera el umbral |
| FAM-lider | `frm_38_validarViabilidad`, `frm_36_revisarEstimacion` | `liderTecnico` | 6–7 | una épica | los dos formularios del Líder Técnico; ninguno supera el umbral |
| FAM-comercial-decision | `frm_21_validarAlcance`, `frm_25_confirmarPropuesta` | `comercial` | 5–6 | una épica | formularios que capturan la decisión de una compuerta; ninguno supera el umbral |
| FAM-interno | `frm_30_iniciarEjecucion` | `procesos` | 4 | una épica | único formulario del Equipo interno; ninguno supera el umbral |

## Aplicación (Living Application)

| Elemento | Valor |
|---|---|
| Application descriptor | `preventa` (las páginas Svelte de los formularios; la bandeja es la de la Bonita User Application) |
| Perfiles con acceso | `User` (todos los usuarios de la organización) |
| Página de inicio | `frm7AnalizarRequerimiento` |
| Layout / tema | los de la plantilla |

| Página | Tipo | Perfil | Objetos / consultas que muestra | Formularios que lanza | Menú |
|---|---|---|---|---|---|
| `frm7AnalizarRequerimiento`, `frm8IdentificarProducto`, `frm9PrepararDemoCliente`, `frm10PrepararDemoGuia`, `frm11ConstruirDocumentosEjemplo`, `frm12EjecutarDemo`, `frm13RegistrarNoContinua`, `frm32AnalizarLicitacion`, `frm33ElaborarPreguntas`, `frm37RadicarPreguntas`, `frm34EsperarRespuestas`, `frm35DefinirSupuestos`, `frm14RealizarLevantamiento`, `frm42AnalizarDocumentos`, `frm38ValidarViabilidad`, `frm39NotificarNoViabilidad`, `frm31PrepararAnalisis`, `frm15CargarInsumos`, `frm17RevisarArtefactos`, `frm36RevisarEstimacion`, `frm18CargarArtefactos`, `frm19SocializarPropuesta`, `frm41PresentarPropuestaTecnica`, `frm20PresentarPropuestaEconomica`, `frm21ValidarAlcance`, `frm22AjustarPropuesta`, `frm23ValidarAjustes`, `frm24EnviarPropuestaFormal`, `frm25ConfirmarPropuesta`, `frm26RegistrarRechazo`, `frm27CerrarGanado`, `frm28PresentarAlcanceTraspaso`, `frm29EntregarCarpeta`, `frm30IniciarEjecucion` | formulario Svelte | `User` | `Preventa` (por `consultas/caso`) | — (las abre el portal por el form mapping) | — |

## Acceso al BDM y permisos (decisión tomada en la capa 0, detallada aquí)

Todo lo que un formulario lee se expone con una **REST API extension** (permiso por perfil, solo los atributos necesarios); el acceso directo a `/API/bdm` está desaconsejado.

| Recurso | Mecanismo (BDM access control / REST API extension / consulta directa) | Perfiles o actores con acceso | Objetos y atributos expuestos | Fuente (visibilidad-por-familia.md) |
|---|---|---|---|---|
| `Preventa` | REST API extension `consultas/caso` (`GET …/API/extension/consultas/caso?caseId=`) | `User`; actores `Comercial`, `ConsultorPreventa`, `LiderTecnico`, `EquipoInterno` | `Preventa` (el objeto raíz del caso) | — (no hay restricciones por familia) |

## Verificaciones de diseño (las revisa el gate)

- [x] Un registro por instanciación, por tarea humana y para el overview (o `No form` explícito).
- [x] Todo formulario con form mapping fijado y familia asignada.
- [x] Todo campo con origen o destino, obligatoriedad, validación, dependencia y catálogo fijados.
- [x] Toda constraint del contrato espejada o declarada como solo de servidor.
- [x] Toda restricción de visibilidad por familia aplicada (no hay ninguna).
- [x] Acceso al BDM decidido antes de construir el primer formulario.

## Pendientes de definición

- No hay prototipo ni referencia visual (`docs/05-prototipo/` vacío): el gate `fidelity` de las unidades de formularios no tiene contra qué comparar hasta que exista. Confirmación humana pendiente.
- Datos de contacto del lead en pantalla (`Preventa.descripcion`, `Preventa.medpicc`): son datos personales del ticket; falta decidir si algún rol no debe verlos (hoy no hay restricción por familia).
