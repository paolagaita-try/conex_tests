---
actualizado: 2026-11-12
capa: 2
motor: Bonita
deriva_de: docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/07-bonita/insumo-preventa/Documento Proceso Diseño de soluciones.docx
total_contratos: 35
---

# Capa 2 — Contratos y operaciones — Gestión de Preventa

> Fuente: el manual «Gestión de Preventa» (paso a paso por fase, columna «Entregables / Notas») y `bpmn.md`. Un contrato por tarea humana y uno de instanciación. Los inputs son los datos mínimos que la tarea debe dejar para que el flujo decida (compuertas) o para que el siguiente actor trabaje; una tarea que solo se «da por hecha» tiene contrato sin inputs.

## Convenciones

- **ID de contrato**: `ctr_instanciacion` y `ctr_<id-tarea>` (reservados en `bpmn.md`).
- **Tipo de input**: `TEXT`, `BOOLEAN` (tipos de contrato de Bonita 2026.2).
- **Destino**: el atributo del objeto de negocio (`Objeto.atributo`) o la process variable (`pv <variable>`) que la operación escribe con ese input.
- **Constraint**: expresión sobre los inputs, con nombre y mensaje; su Groovy va en `docs/08-construccion/expresiones.md` (`ctr_<contrato>.<constraint>`).
- **Operación**: igual a la plantilla de persistencia `asignacion-directa` de `bdm.md` salvo los literales indicados. Un destino escrito por un script lleva su marca (`op_<tarea>.<atributo>`).
- **`requiereViabilidad`**: la decisión de `gwXor_13` (`G13`) no tiene tarea propia en el insumo; la fija, como input opcional, la última tarea del consultor antes de la compuerta. Sin valor, vale `false`.

## Contrato de instanciación — `ctr_instanciacion`

### `GestionPreventa` 1.0

Formulario asociado (capa 3): `frm_instanciacion` (`No form`). Fuente: el middleware Ofelia instancia el caso por la API REST al recibir el webhook `ticket.creation` de HubSpot.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (Tarea de Proceso → Entradas) |
|---|---|---|---|---|---|---|
| `ticketId` | TEXT | no | sí | — | `Preventa.ticketId` | webhook `ticket.creation` → `objectId` del ticket |

| Constraint | Expresión (lenguaje natural o Groovy) | Mensaje de error | AC que la origina |
|---|---|---|---|
| `ticketId_presente` | ticketId no está vacío | El identificador del ticket es obligatorio | manual, Fase 1 (`A02`, ticket de preventa creado) |

Operaciones al instanciar: según plantilla `asignacion-directa` con literales: `Preventa.estado` = `recibida`; crea `Preventa` con el `ticketId` del input. La idempotencia por ticket la da la unique constraint de `Preventa.ticketId` (un segundo caso del mismo ticket no se crea).

## Contratos de tarea humana

### `ctr_7_analizarRequerimiento` — Analizar MEDDPICC y requerimiento

- **Tarea** (`bpmn.md`): `7_analizarRequerimiento`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_7_analizarRequerimiento`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 1 — Inicio, registro y asignación (`A07`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `tipoAtencion` | TEXT | no | sí | — | `Preventa.tipoAtencion` | insumo `A07` → Tipo de atención |
| `informacionSuficiente` | BOOLEAN | no | sí | — | `pv informacionSuficiente` | insumo `A07` → ¿La información es suficiente para la propuesta? |
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `A07` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| `tipoAtencion_valido` | tipoAtencion es demo, licitacion o propuesta | El tipo de atención debe ser demo, licitacion o propuesta | insumo `A07` |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.descripcion`, `Preventa.medpicc`, `Preventa.tipoRequerimiento`, `Preventa.comercialCreador`, `Preventa.linkRepositorio` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.tipoAtencion`; process variables actualizadas: `informacionSuficiente`, `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_8_identificarProducto` — Identificar producto del demo (DocFly / Oriuno)

- **Tarea** (`bpmn.md`): `8_identificarProducto`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_8_identificarProducto`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 2 — Demo (`A08`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `productoDemo` | TEXT | no | sí | — | `Preventa.productoDemo` | insumo `A08` → Producto del demo |
| `origenDocumentosDemo` | TEXT | no | sí | — | `Preventa.origenDocumentosDemo` | insumo `A08` → Documentos con los que se prepara la demo |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| `productoDemo_valido` | productoDemo es docfly u oriuno | El producto debe ser docfly u oriuno | insumo `A08` |
| `origenDocumentosDemo_valido` | origenDocumentosDemo es cliente, guia o ejemplo | El origen de los documentos debe ser cliente, guia o ejemplo | insumo `A08` |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.productoDemo`, `Preventa.origenDocumentosDemo`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_9_prepararDemoCliente` — Preparar demo con documentos del cliente

- **Tarea** (`bpmn.md`): `9_prepararDemoCliente`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_9_prepararDemoCliente`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 2 — Demo (`A09`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_10_prepararDemoGuia` — Preparar demo con documentos guía

- **Tarea** (`bpmn.md`): `10_prepararDemoGuia`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_10_prepararDemoGuia`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 2 — Demo (`A10`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_11_construirDocumentosEjemplo` — Construir documentos de ejemplo para el caso

- **Tarea** (`bpmn.md`): `11_construirDocumentosEjemplo`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_11_construirDocumentosEjemplo`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 2 — Demo (`A11`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_12_ejecutarDemo` — Ejecutar demo con el cliente

- **Tarea** (`bpmn.md`): `12_ejecutarDemo`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_12_ejecutarDemo`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 2 — Demo (`A12`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `clienteAvanza` | BOOLEAN | no | sí | — | `pv clienteAvanza` | insumo `A12` → ¿El cliente avanza? |
| `informacionSuficiente` | BOOLEAN | no | sí | — | `pv informacionSuficiente` | insumo `A12` → ¿La información es suficiente para la propuesta? |
| `observacionDemo` | TEXT | no | no | — | `Preventa.observacionDemo` | insumo `A12` → Observaciones de la demo |
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `A12` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.observacionDemo`; process variables actualizadas: `clienteAvanza`, `informacionSuficiente`, `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_13_registrarNoContinua` — Actualizar estado en HubSpot (no continúa)

- **Tarea** (`bpmn.md`): `13_registrarNoContinua`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_13_registrarNoContinua`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 2 — Demo (`A13`).
- **Δestado**: → `descartada`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `motivoDescarte` | TEXT | no | sí | — | `Preventa.motivoDescarte` | insumo `A13` → Motivo por el que no continúa |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `descartada`; escribe `Preventa.motivoDescarte`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_32_analizarLicitacion` — Analizar insumos de la licitación (pliegos / TDR)

- **Tarea** (`bpmn.md`): `32_analizarLicitacion`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_32_analizarLicitacion`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 3 — Licitación (`A32`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `requierePreguntas` | BOOLEAN | no | sí | — | `pv requierePreguntas` | insumo `A32` → ¿Requiere preguntas aclaratorias? |
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `A32` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; process variables actualizadas: `requierePreguntas`, `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_33_elaborarPreguntas` — Elaborar preguntas y cargarlas en el ticket

- **Tarea** (`bpmn.md`): `33_elaborarPreguntas`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_33_elaborarPreguntas`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 3 — Licitación (`A33`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `preguntasAclaratorias` | TEXT | no | sí | — | `Preventa.preguntasAclaratorias` | insumo `A33` → Preguntas aclaratorias |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.preguntasAclaratorias`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_37_radicarPreguntas` — Radicar o enviar preguntas a la entidad

- **Tarea** (`bpmn.md`): `37_radicarPreguntas`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_37_radicarPreguntas`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 3 — Licitación (`A37`).
- **Δestado**: → `enEsperaRespuestas`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.preguntasAclaratorias` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `enEsperaRespuestas`; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_34_esperarRespuestas` — Esperar y registrar las respuestas de la entidad

- **Tarea** (`bpmn.md`): `34_esperarRespuestas`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_34_esperarRespuestas`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 3 — Licitación (`RT1`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `respuestasCompletas` | BOOLEAN | no | sí | — | `pv respuestasCompletas` | insumo `RT1` → ¿Las respuestas son completas? |
| `respuestasEntidad` | TEXT | no | no | — | `Preventa.respuestasEntidad` | insumo `RT1` → Respuestas de la entidad |
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `RT1` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.preguntasAclaratorias` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.respuestasEntidad`; process variables actualizadas: `respuestasCompletas`, `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_35_definirSupuestos` — Definir supuestos para la propuesta

- **Tarea** (`bpmn.md`): `35_definirSupuestos`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_35_definirSupuestos`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 3 — Licitación (`A35`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `supuestos` | TEXT | no | sí | — | `Preventa.supuestos` | insumo `A35` → Supuestos de la propuesta |
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `A35` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.preguntasAclaratorias`, `Preventa.respuestasEntidad` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.supuestos`; process variables actualizadas: `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_14_realizarLevantamiento` — Realizar sesión de levantamiento y solicitar documentación de referencia

- **Tarea** (`bpmn.md`): `14_realizarLevantamiento`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_14_realizarLevantamiento`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 4 — Validación de información, viabilidad técnica y preparación de insumos (`A14`).
- **Δestado**: → `enLevantamiento`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `entregaDocumentos` | BOOLEAN | no | sí | — | `pv entregaDocumentos` | insumo `A14` → ¿El cliente entrega documentos de referencia? |
| `enlaceGrabacion` | TEXT | no | no | — | `Preventa.enlaceGrabacion` | insumo `A14` → Enlace a la grabación y transcripción |
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `A14` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `enLevantamiento`; escribe `Preventa.enlaceGrabacion`; process variables actualizadas: `entregaDocumentos`, `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_42_analizarDocumentos` — Analizar documentos e insumos de referencia del cliente

- **Tarea** (`bpmn.md`): `42_analizarDocumentos`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_42_analizarDocumentos`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 4 — Validación de información, viabilidad técnica y preparación de insumos (`A42`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `requiereViabilidad` | BOOLEAN | no | no | — | `pv requiereViabilidad` | insumo `A42` → ¿Requiere validar la viabilidad técnica? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; process variables actualizadas: `requiereViabilidad`. Desviación de la plantilla: ninguna.

### `ctr_38_validarViabilidad` — Validar viabilidad técnica

- **Tarea** (`bpmn.md`): `38_validarViabilidad`, actor Líder Técnico.
- **Formulario asociado** (capa 3): `frm_38_validarViabilidad`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 4 — Validación de información, viabilidad técnica y preparación de insumos (`A38`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `esViable` | BOOLEAN | no | sí | — | `pv esViable` | insumo `A38` → ¿El requerimiento es viable? |
| `conceptoViabilidad` | TEXT | no | sí | — | `Preventa.conceptoViabilidad` | insumo `A38` → Concepto de viabilidad técnica |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.descripcion`, `Preventa.medpicc` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.conceptoViabilidad`; process variables actualizadas: `esViable`. Desviación de la plantilla: ninguna.

### `ctr_39_notificarNoViabilidad` — Notificar y socializar no viabilidad con Comercial

- **Tarea** (`bpmn.md`): `39_notificarNoViabilidad`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_39_notificarNoViabilidad`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 4 — Validación de información, viabilidad técnica y preparación de insumos (`A39`).
- **Δestado**: → `noViable`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.conceptoViabilidad` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `noViable`; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_31_prepararAnalisis` — Preparar análisis de documentos para el agente IA

- **Tarea** (`bpmn.md`): `31_prepararAnalisis`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_31_prepararAnalisis`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 4 — Validación de información, viabilidad técnica y preparación de insumos (`A31`).
- **Δestado**: → `enDiseno`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `enlaceInsumos` | TEXT | no | sí | — | `Preventa.enlaceInsumos` | insumo `A31` → Enlace al paquete de insumos estructurado |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `enDiseno`; escribe `Preventa.enlaceInsumos`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_15_cargarInsumos` — Cargar insumos al agente IA

- **Tarea** (`bpmn.md`): `15_cargarInsumos`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_15_cargarInsumos`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 4 — Validación de información, viabilidad técnica y preparación de insumos (`A15`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlaceInsumos` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_17_revisarArtefactos` — Revisar y ajustar artefactos

- **Tarea** (`bpmn.md`): `17_revisarArtefactos`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_17_revisarArtefactos`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 5 — Construcción y estimación de la oferta (`A17`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `enlacePropuesta` | TEXT | no | sí | — | `Preventa.enlacePropuesta` | insumo `A17` → Enlace a la propuesta |
| `enlacePresentacion` | TEXT | no | sí | — | `Preventa.enlacePresentacion` | insumo `A17` → Enlace a la presentación |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.enlacePropuesta`, `Preventa.enlacePresentacion`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_36_revisarEstimacion` — Revisar y generar estimación con Líder Técnico

- **Tarea** (`bpmn.md`): `36_revisarEstimacion`, actor Líder Técnico.
- **Formulario asociado** (capa 3): `frm_36_revisarEstimacion`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 5 — Construcción y estimación de la oferta (`A36`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `enlaceEstimacion` | TEXT | no | sí | — | `Preventa.enlaceEstimacion` | insumo `A36` → Enlace a la estimación validada |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.enlaceEstimacion`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_18_cargarArtefactos` — Cargar artefactos en el lead de HubSpot (etapa «Preventa / Solución GH»)

- **Tarea** (`bpmn.md`): `18_cargarArtefactos`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_18_cargarArtefactos`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 5 — Construcción y estimación de la oferta (`A18`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_19_socializarPropuesta` — Socializar propuesta con Comercial

- **Tarea** (`bpmn.md`): `19_socializarPropuesta`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_19_socializarPropuesta`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A19`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_41_presentarPropuestaTecnica` — Presentar propuesta técnica: alcance, solución y cronograma

- **Tarea** (`bpmn.md`): `41_presentarPropuestaTecnica`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_41_presentarPropuestaTecnica`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A41`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlacePresentacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_20_presentarPropuestaEconomica` — Presentar propuesta económica (presupuesto)

- **Tarea** (`bpmn.md`): `20_presentarPropuestaEconomica`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_20_presentarPropuestaEconomica`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A20`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_21_validarAlcance` — Validar alcance de la propuesta

- **Tarea** (`bpmn.md`): `21_validarAlcance`, actor Comercial (en nombre del Cliente).
- **Formulario asociado** (capa 3): `frm_21_validarAlcance`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A21`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `alcanceCorrecto` | BOOLEAN | no | sí | — | `pv alcanceCorrecto` | insumo `A21` → ¿El cliente valida el alcance? |
| `observacionAlcance` | TEXT | no | no | — | `Preventa.observacionAlcance` | insumo `A21` → Ajustes solicitados por el cliente |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.observacionAlcance`; process variables actualizadas: `alcanceCorrecto`. Desviación de la plantilla: ninguna.

### `ctr_22_ajustarPropuesta` — Ajustar propuesta

- **Tarea** (`bpmn.md`): `22_ajustarPropuesta`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_22_ajustarPropuesta`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A22`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `ajustesPropuesta` | TEXT | no | sí | — | `Preventa.ajustesPropuesta` | insumo `A22` → Ajustes realizados |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.observacionAlcance`, `Preventa.enlacePropuesta` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.ajustesPropuesta`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_23_validarAjustes` — Validar ajustes («Negociación / Ajustes»)

- **Tarea** (`bpmn.md`): `23_validarAjustes`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_23_validarAjustes`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A23`).
- **Δestado**: → `enNegociacion`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.ajustesPropuesta`, `Preventa.enlacePropuesta` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `enNegociacion`; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_24_enviarPropuestaFormal` — Enviar propuesta formal y mover lead a «Propuesta enviada»

- **Tarea** (`bpmn.md`): `24_enviarPropuestaFormal`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_24_enviarPropuestaFormal`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 6 — Socialización, sustentación y ajustes (`A24`).
- **Δestado**: → `propuestaEnviada`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `propuestaEnviada`; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_25_confirmarPropuesta` — Confirmar propuesta

- **Tarea** (`bpmn.md`): `25_confirmarPropuesta`, actor Comercial (en nombre del Cliente).
- **Formulario asociado** (capa 3): `frm_25_confirmarPropuesta`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 7 — Confirmación, cierre y traspaso a ejecución (`A25`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `propuestaAprobada` | BOOLEAN | no | sí | — | `pv propuestaAprobada` | insumo `A25` → ¿El cliente aprueba la propuesta? |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; process variables actualizadas: `propuestaAprobada`. Desviación de la plantilla: ninguna.

### `ctr_26_registrarRechazo` — Registrar rechazo y motivo en HubSpot

- **Tarea** (`bpmn.md`): `26_registrarRechazo`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_26_registrarRechazo`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 7 — Confirmación, cierre y traspaso a ejecución (`A26`).
- **Δestado**: → `rechazada`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `motivoRechazo` | TEXT | no | sí | — | `Preventa.motivoRechazo` | insumo `A26` → Motivo del rechazo |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `rechazada`; escribe `Preventa.motivoRechazo`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_27_cerrarGanado` — Pasar a «Cerrado ganado» y convocar traspaso

- **Tarea** (`bpmn.md`): `27_cerrarGanado`, actor Comercial.
- **Formulario asociado** (capa 3): `frm_27_cerrarGanado`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 7 — Confirmación, cierre y traspaso a ejecución (`A27`).
- **Δestado**: → `ganada`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `ganada`; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_28_presentarAlcanceTraspaso` — Presentar alcance en sesión interna de traspaso

- **Tarea** (`bpmn.md`): `28_presentarAlcanceTraspaso`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_28_presentarAlcanceTraspaso`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 7 — Confirmación, cierre y traspaso a ejecución (`A28`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_29_entregarCarpeta` — Entregar carpeta de documentación a Procesos

- **Tarea** (`bpmn.md`): `29_entregarCarpeta`, actor Consultor Preventa.
- **Formulario asociado** (capa 3): `frm_29_entregarCarpeta`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 7 — Confirmación, cierre y traspaso a ejecución (`A29`).
- **Δestado**: — (no cambia `Preventa.estado`).

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `enlaceCarpeta` | TEXT | no | sí | — | `Preventa.enlaceCarpeta` | insumo `A29` → Enlace a la carpeta «Prospectos de Preventa» del cliente |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.enlaceCarpeta`; no actualiza process variables. Desviación de la plantilla: ninguna.

### `ctr_30_iniciarEjecucion` — Recibir carpeta e iniciar ejecución del proyecto

- **Tarea** (`bpmn.md`): `30_iniciarEjecucion`, actor Equipo interno.
- **Formulario asociado** (capa 3): `frm_30_iniciarEjecucion`.
- **Tarea de Proceso**: manual «Gestión de Preventa», Fase 7 — Confirmación, cierre y traspaso a ejecución (`A30`).
- **Δestado**: → `enEjecucion`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| — | — | — | — |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa.ticketId`, `Preventa.asunto`, `Preventa.estado`, `Preventa.enlaceCarpeta` (business variable `preventa` del caso).

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `enEjecucion`; no escribe atributos desde inputs; no actualiza process variables. Desviación de la plantilla: ninguna.

## Operaciones de tareas de servicio y script

| Tarea | Conector | Operaciones (plantilla / literales) | Escribe | Process variables |
|---|---|---|---|---|
| `3_consultarTicket` | `conn_hubspotLeer` | `asignacion-directa` / ninguno; las salidas del conector escriben los datos del ticket (`bpmn.md` → Conectores por tarea) | `Preventa.asunto`, `Preventa.descripcion`, `Preventa.comercialCreador`, `Preventa.tipoRequerimiento`, `Preventa.medpicc`, `Preventa.linkRepositorio` | — |
| `4_verificarDisponibilidad` | — | `asignacion-directa` / ninguno; script `pv totalDisponibles` ← `cantidad de consultores activos del catálogo ConsultorPreventa` (`op_4_verificarDisponibilidad.totalDisponibles`) | — | `totalDisponibles` |
| `5_asignarConsultor` | — | `asignacion-directa` / `Preventa.estado` = `asignada`; script `Preventa.consultor` ← `usuario del consultor activo que sigue en el turno: posición (ultimoIndice + 1) módulo totalDisponibles sobre los activos ordenados por usuario` (`op_5_asignarConsultor.consultor`); script `Preventa.consultorOwnerId` ← `owner de HubSpot del consultor elegido` (`op_5_asignarConsultor.consultorOwnerId`); script `TurnoAsignacion.ultimoIndice` ← `posición del consultor elegido` (`op_5_asignarConsultor.ultimoIndice`) | `Preventa.estado`, `Preventa.consultor`, `Preventa.consultorOwnerId`, `TurnoAsignacion.ultimoIndice` | — |
| `6_actualizarTicket` | `conn_hubspotActualizar` | — (sin escritura) | — | — |
| `16_generarArtefactos` | `conn_agenteIA` | `asignacion-directa` / ninguno; las salidas del conector escriben los enlaces de los borradores (`bpmn.md` → Conectores por tarea) | `Preventa.enlacePropuesta`, `Preventa.enlaceEstimacion`, `Preventa.enlacePresentacion` | — |
| `40_entregarAVentas` | `conn_hubspotActualizar` | `asignacion-directa` / `Preventa.estado` = `entregadaAVentas` | `Preventa.estado` | — |

## Matriz tarea ↔ contrato ↔ formulario (la revisa el gate)

| Tarea humana | Contrato | Formulario (capa 3) | Inputs | Constraints |
|---|---|---|---|---|
| (instanciación) | `ctr_instanciacion` | `frm_instanciacion` | 1 | 1 |
| `7_analizarRequerimiento` | `ctr_7_analizarRequerimiento` | `frm_7_analizarRequerimiento` | 3 | 1 |
| `8_identificarProducto` | `ctr_8_identificarProducto` | `frm_8_identificarProducto` | 2 | 2 |
| `9_prepararDemoCliente` | `ctr_9_prepararDemoCliente` | `frm_9_prepararDemoCliente` | 0 | 0 |
| `10_prepararDemoGuia` | `ctr_10_prepararDemoGuia` | `frm_10_prepararDemoGuia` | 0 | 0 |
| `11_construirDocumentosEjemplo` | `ctr_11_construirDocumentosEjemplo` | `frm_11_construirDocumentosEjemplo` | 0 | 0 |
| `12_ejecutarDemo` | `ctr_12_ejecutarDemo` | `frm_12_ejecutarDemo` | 4 | 0 |
| `13_registrarNoContinua` | `ctr_13_registrarNoContinua` | `frm_13_registrarNoContinua` | 1 | 0 |
| `32_analizarLicitacion` | `ctr_32_analizarLicitacion` | `frm_32_analizarLicitacion` | 2 | 0 |
| `33_elaborarPreguntas` | `ctr_33_elaborarPreguntas` | `frm_33_elaborarPreguntas` | 1 | 0 |
| `37_radicarPreguntas` | `ctr_37_radicarPreguntas` | `frm_37_radicarPreguntas` | 0 | 0 |
| `34_esperarRespuestas` | `ctr_34_esperarRespuestas` | `frm_34_esperarRespuestas` | 3 | 0 |
| `35_definirSupuestos` | `ctr_35_definirSupuestos` | `frm_35_definirSupuestos` | 2 | 0 |
| `14_realizarLevantamiento` | `ctr_14_realizarLevantamiento` | `frm_14_realizarLevantamiento` | 3 | 0 |
| `42_analizarDocumentos` | `ctr_42_analizarDocumentos` | `frm_42_analizarDocumentos` | 1 | 0 |
| `38_validarViabilidad` | `ctr_38_validarViabilidad` | `frm_38_validarViabilidad` | 2 | 0 |
| `39_notificarNoViabilidad` | `ctr_39_notificarNoViabilidad` | `frm_39_notificarNoViabilidad` | 0 | 0 |
| `31_prepararAnalisis` | `ctr_31_prepararAnalisis` | `frm_31_prepararAnalisis` | 1 | 0 |
| `15_cargarInsumos` | `ctr_15_cargarInsumos` | `frm_15_cargarInsumos` | 0 | 0 |
| `17_revisarArtefactos` | `ctr_17_revisarArtefactos` | `frm_17_revisarArtefactos` | 2 | 0 |
| `36_revisarEstimacion` | `ctr_36_revisarEstimacion` | `frm_36_revisarEstimacion` | 1 | 0 |
| `18_cargarArtefactos` | `ctr_18_cargarArtefactos` | `frm_18_cargarArtefactos` | 0 | 0 |
| `19_socializarPropuesta` | `ctr_19_socializarPropuesta` | `frm_19_socializarPropuesta` | 0 | 0 |
| `41_presentarPropuestaTecnica` | `ctr_41_presentarPropuestaTecnica` | `frm_41_presentarPropuestaTecnica` | 0 | 0 |
| `20_presentarPropuestaEconomica` | `ctr_20_presentarPropuestaEconomica` | `frm_20_presentarPropuestaEconomica` | 0 | 0 |
| `21_validarAlcance` | `ctr_21_validarAlcance` | `frm_21_validarAlcance` | 2 | 0 |
| `22_ajustarPropuesta` | `ctr_22_ajustarPropuesta` | `frm_22_ajustarPropuesta` | 1 | 0 |
| `23_validarAjustes` | `ctr_23_validarAjustes` | `frm_23_validarAjustes` | 0 | 0 |
| `24_enviarPropuestaFormal` | `ctr_24_enviarPropuestaFormal` | `frm_24_enviarPropuestaFormal` | 0 | 0 |
| `25_confirmarPropuesta` | `ctr_25_confirmarPropuesta` | `frm_25_confirmarPropuesta` | 1 | 0 |
| `26_registrarRechazo` | `ctr_26_registrarRechazo` | `frm_26_registrarRechazo` | 1 | 0 |
| `27_cerrarGanado` | `ctr_27_cerrarGanado` | `frm_27_cerrarGanado` | 0 | 0 |
| `28_presentarAlcanceTraspaso` | `ctr_28_presentarAlcanceTraspaso` | `frm_28_presentarAlcanceTraspaso` | 0 | 0 |
| `29_entregarCarpeta` | `ctr_29_entregarCarpeta` | `frm_29_entregarCarpeta` | 1 | 0 |
| `30_iniciarEjecucion` | `ctr_30_iniciarEjecucion` | `frm_30_iniciarEjecucion` | 0 | 0 |

## Cobertura de las reglas de validación de los AC

| Tarea de Proceso | Regla del AC | Cubierta por | Tipo |
|---|---|---|---|
| `A02` | Un ticket genera un solo caso | unique constraint `Preventa.ticketId` | BDM |
| `A07` | tipoAtencion es demo, licitacion o propuesta | `tipoAtencion_valido` | constraint de contrato |
| `A08` | productoDemo es docfly u oriuno | `productoDemo_valido` | constraint de contrato |
| `A08` | origenDocumentosDemo es cliente, guia o ejemplo | `origenDocumentosDemo_valido` | constraint de contrato |
| Punto de control 3 | Viabilidad validada por el Líder Técnico cuando el requerimiento lo amerita | `gwXor_13`, `38_validarViabilidad`, `gwXor_14` | flujo |
| Punto de control 5 | Revisión humana de los artefactos generados por el agente IA | `17_revisarArtefactos` | flujo |
| Punto de control 6 | Estimación validada con el Líder Técnico antes de socializar | `36_revisarEstimacion` antes de `19_socializarPropuesta` | flujo |
| Punto de control 7 | Propuesta socializada con Comercial antes de presentarla al cliente | `19_socializarPropuesta` antes de `41_presentarPropuestaTecnica` | flujo |

## Pendientes de definición

- Los inputs de cada tarea son los mínimos que el flujo necesita; el manual no trae criterios de aceptación por tarea (no hay `docs/04-tareas-proceso/`). Si negocio quiere capturar más datos por tarea, se reabre esta capa.
- `33_elaborarPreguntas`: el manual dice «cargarlas en el ticket»; aquí las preguntas quedan en el caso (`Preventa.preguntasAclaratorias`). Falta decidir si además Bonita debe escribirlas como nota del ticket en HubSpot. `[no verificado]`
