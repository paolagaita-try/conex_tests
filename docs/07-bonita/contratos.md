---
actualizado: 2026-11-24
capa: 2
motor: Bonita
deriva_de: docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/07-bonita/insumo-preventa/reunion-socializacion.md, docs/08-construccion/plan-v2-bonita-first.md
total_contratos: 3
---

# Capa 2 — Contratos y operaciones — Gestión de Preventa

> Fuente: `bpmn.md`, la reunión de socialización y la decisión «Bonita-first» del 2026-11-24. Tres contratos: el de instanciación (lo cumple el middleware por la API al crearse un ticket) y los de las dos tareas humanas de la consultora asignada (`10_validarSolicitud` y `20_disenarPropuesta`), que se cumplen desde formularios de Bonita.

## Convenciones

- **ID de contrato**: `ctr_instanciacion` y `ctr_<id-tarea>` (reservados en `bpmn.md`).
- **Tipo de input**: `TEXT` o `FILE` (tipos de contrato de Bonita 2026.2).
- **Destino**: el atributo del objeto de negocio (`Objeto.atributo`), la process variable (`pv <variable>`) o el documento (`doc. <documento>`) que la operación escribe con ese input.
- **Constraint**: expresión sobre los inputs, con nombre y mensaje; su Groovy va en `docs/08-construccion/expresiones.md` (`ctr_<contrato>.<constraint>`).
- **Operación**: igual a la plantilla de persistencia `asignacion-directa` de `bdm.md` salvo los literales indicados. Un destino escrito por un script lleva su marca (`op_<tarea>.<atributo>`).
- **Datos de solo lectura de los formularios**: no son inputs. Lo del caso sale de `Preventa`; lo del CRM (ticket, Negocio, empresa, contactos, owner) de la REST API extension `preventaContexto` (`matriz-formularios.md`).

## Contrato de instanciación — `ctr_instanciacion`

### `GestionPreventa` 1.2

Formulario asociado (capa 3): `frm_instanciacion` (`No form`). Fuente: el middleware instancia el caso por la API REST al recibir el webhook `ticket.creation` de HubSpot.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (Tarea de Proceso → Entradas) |
|---|---|---|---|---|---|---|
| `ticketId` | TEXT | no | sí | — | `Preventa.ticketId` | webhook `ticket.creation` → identificador del ticket |

| Constraint | Expresión (lenguaje natural o Groovy) | Mensaje de error | AC que la origina |
|---|---|---|---|
| `ticketId_presente` | ticketId no está vacío | El identificador del ticket es obligatorio | insumo `A02` (ticket de preventa creado) |

Operaciones al instanciar: según plantilla `asignacion-directa` con literales: `Preventa.estado` = `recibida`; por script, `Preventa.fechaRecepcion` ← `la fecha y hora actuales` (`op_instanciacion.fechaRecepcion`); crea `Preventa` con el `ticketId` del input. La idempotencia por ticket se apoya en la unique constraint de `Preventa.ticketId`: se espera que un segundo caso del mismo ticket falle al instanciar. `[no verificado]` en ejecución; el middleware recibiría un error genérico, así que además debe evitar reenviar un ticket ya instanciado.

## Contratos de tarea humana

### `ctr_10_validarSolicitud` — Validar la solicitud

- **Tarea** (`bpmn.md`): `10_validarSolicitud`, actor Consultora (solo la consultora asignada, actor filter `filtroConsultoraDelCaso`).
- **Formulario asociado** (capa 3): `frm_10_validarSolicitud` (Svelte).
- **Tarea de Proceso**: plan v2 paso 3; insumo `A07` (analizar requerimiento) y `A38` (validar viabilidad).
- **Δestado**: `asignada` o `bloqueada` → `validada`, `bloqueada` o `noViable`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `resultado` | TEXT | no | sí | — | `Preventa.resultadoValidacion` | consultora → `viable`, `bloqueado` (falta información del lead) o `no_viable` |
| `conceptoViabilidad` | TEXT | no | no | — | `Preventa.conceptoViabilidad` | consultora → concepto que va a la propiedad `concepto_viabilidad` del Negocio |
| `notaValidacion` | TEXT | no | sí | — | `Preventa.notaValidacion` | consultora → nota (texto largo) que queda en el ticket y el Negocio |
| `supuestos` | TEXT | no | no | — | `Preventa.supuestos` | consultora → supuestos de la validación |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| `resultado_valido` | resultado es viable, bloqueado o no_viable | El resultado debe ser viable, bloqueado o no viable | plan v2 paso 3 (compuerta de validación) |
| `notaValidacion_presente` | notaValidacion no está vacía | La nota de validación es obligatoria | plan v2 paso 3 (nota de validación en ticket y Negocio) |
| `conceptoViabilidad_si_concluye` | si resultado es viable o no_viable, conceptoViabilidad no está vacío | El concepto de viabilidad es obligatorio si la solicitud es viable o no viable | plan v2 paso 3 (`concepto_viabilidad`) |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa` (ticket, asunto, consultor, validación anterior si hubo bloqueo) y, por `preventaContexto`, el ticket, el Negocio, la empresa, los contactos y el owner.

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; escribe `Preventa.resultadoValidacion`, `Preventa.conceptoViabilidad`, `Preventa.notaValidacion`, `Preventa.supuestos`; por script, `Preventa.estado` ← `validada si resultado es viable, bloqueada si es bloqueado, si no noViable` (`op_10_validarSolicitud.estado`); por script, `Preventa.fechaValidacion` ← `la fecha y hora actuales` (`op_10_validarSolicitud.fechaValidacion`); no actualiza process variables (`gwXor_1` lee `Preventa.resultadoValidacion`). Desviación de la plantilla: ninguna.

**Conectores a la salida** (`bpmn.md`): `conn_hubspotNota` (nota en ticket y Negocio). El `concepto_viabilidad` y el cambio de stage los hacen `11_pasarADiseno`, `12_pasarAEnEspera` o `13_registrarNoViable` según la compuerta.

### `ctr_20_disenarPropuesta` — Diseñar la propuesta

- **Tarea** (`bpmn.md`): `20_disenarPropuesta`, actor Consultora (solo la consultora asignada, actor filter `filtroConsultoraDelCaso`).
- **Formulario asociado** (capa 3): `frm_20_disenarPropuesta` (Svelte).
- **Tarea de Proceso**: plan v2 paso 4; insumo `A15`–`A18` (artefactos de la propuesta).
- **Δestado**: `validada` → `propuestaDisenada`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `valoracionOperaciones` | TEXT | no | sí | — | `Preventa.valoracionOperaciones` | consultora → propiedad `valoracion_operaciones` del Negocio |
| `urlPptaPreventa` | TEXT | no | sí | — | `Preventa.urlPptaPreventa` | consultora → propiedad `url_ppta_preventa` del Negocio (URL de la presentación) |
| `linkRepoPreventa` | TEXT | no | sí | — | `Preventa.linkRepoPreventa` | consultora → propiedad `link_repo_preventa` del Negocio (URL del repositorio) |
| `notaPropuesta` | TEXT | no | no | — | `Preventa.notaPropuesta` | consultora → nota de la propuesta |
| `adjuntos` | FILE | sí | no | — | doc. `adjuntosPropuesta` | consultora → documentos de la propuesta (varios) que se suben al Negocio |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| `valoracionOperaciones_presente` | valoracionOperaciones no está vacía | La valoración de operaciones es obligatoria | plan v2 paso 4 (cuatro artefactos del Negocio) |
| `urlPptaPreventa_valida` | urlPptaPreventa empieza por http:// o https:// | La URL de la propuesta debe empezar por http:// o https:// | plan v2 paso 4 |
| `linkRepoPreventa_valido` | linkRepoPreventa empieza por http:// o https:// | El enlace al repositorio debe empezar por http:// o https:// | plan v2 paso 4 |

**Datos de solo lectura que el formulario consulta** (no son inputs): `Preventa` (incluida la validación: resultado, concepto, nota y supuestos) y, por `preventaContexto`, el ticket, el Negocio, la empresa, los contactos y el owner.

**Operaciones**: plantilla `asignacion-directa`; literales: `Preventa.estado` = `propuestaDisenada`; escribe `Preventa.valoracionOperaciones`, `Preventa.urlPptaPreventa`, `Preventa.linkRepoPreventa`, `Preventa.notaPropuesta` y el documento `adjuntosPropuesta`; por script, `Preventa.fechaPropuesta` ← `la fecha y hora actuales` (`op_20_disenarPropuesta.fechaPropuesta`); por script, `Preventa.cantidadAdjuntos` ← `el número de adjuntos del input adjuntos, 0 si no hay` (`op_20_disenarPropuesta.cantidadAdjuntos`); no actualiza process variables. Desviación de la plantilla: ninguna.

**Conectores a la salida** (`bpmn.md`): `conn_hubspotNegocio` (las cuatro propiedades: `concepto_viabilidad`, `valoracion_operaciones`, `url_ppta_preventa`, `link_repo_preventa`) y `conn_hubspotNota`. Los adjuntos los sube `21_subirAdjuntos` si los hay (`gwXor_2`); el stage «Entregado a ventas» lo pone `40_entregarAVentas`.

## Operaciones de tareas de servicio y script

| Tarea | Conector | Operaciones (plantilla / literales) | Escribe | Process variables |
|---|---|---|---|---|
| `3_consultarTicket` | `conn_hubspotLeer` | `asignacion-directa` / ninguno; las salidas del conector escriben los datos del ticket (`bpmn.md` → Conectores por tarea) | `Preventa.asunto`, `Preventa.dealId` | — |
| `4_verificarDisponibilidad` | `conn_hubspotCarga` | `asignacion-directa` / ninguno; la salida del conector escribe la process variable (`bpmn.md` → Conectores por tarea) | — | `ownerElegido` |
| `5_asignarConsultor` | — | `asignacion-directa` / `Preventa.estado` = `asignada`; script `Preventa.consultorOwnerId` ← `el valor de la process variable ownerElegido` (`op_5_asignarConsultor.consultorOwnerId`); script `Preventa.consultor` ← `el nombre que param_consultores da al owner de la process variable ownerElegido` (`op_5_asignarConsultor.consultor`); script `Preventa.fechaAsignacion` ← `la fecha y hora actuales` (`op_5_asignarConsultor.fechaAsignacion`) | `Preventa.estado`, `Preventa.consultorOwnerId`, `Preventa.consultor`, `Preventa.fechaAsignacion` | — |
| `6_actualizarTicket` | `conn_hubspotActualizar` | — (sin escritura) | — | — |
| `11_pasarADiseno` | `conn_hubspotActualizar`, `conn_hubspotNegocio` | — (sin escritura) | — | — |
| `12_pasarAEnEspera` | `conn_hubspotActualizar` | — (sin escritura) | — | — |
| `13_registrarNoViable` | `conn_hubspotNegocio`, `conn_hubspotActualizar` | — (sin escritura) | — | — |
| `21_subirAdjuntos` | `conn_hubspotArchivos` | — (sin escritura) | — | — |
| `40_entregarAVentas` | `conn_hubspotActualizar` | `asignacion-directa` / `Preventa.estado` = `entregadaAVentas`; script `Preventa.fechaEntrega` ← `la fecha y hora actuales` (`op_40_entregarAVentas.fechaEntrega`) | `Preventa.estado`, `Preventa.fechaEntrega` | — |

Los scripts de `5_asignarConsultor` leen solo la process variable `ownerElegido` y el reloj: ninguno depende de lo que escribe otro.

## Matriz tarea ↔ contrato ↔ formulario (la revisa el gate)

| Tarea humana | Contrato | Formulario (capa 3) | Inputs | Constraints |
|---|---|---|---|---|
| (instanciación) | `ctr_instanciacion` | `frm_instanciacion` | 1 | 1 |
| `10_validarSolicitud` | `ctr_10_validarSolicitud` | `frm_10_validarSolicitud` | 4 | 3 |
| `20_disenarPropuesta` | `ctr_20_disenarPropuesta` | `frm_20_disenarPropuesta` | 5 | 3 |

## Cobertura de las reglas de validación de los AC

| Tarea de Proceso | Regla del AC | Cubierta por | Tipo |
|---|---|---|---|
| `A02` | Un ticket genera un solo caso | unique constraint `Preventa.ticketId` (rechazo del duplicado `[no verificado]` en ejecución) | BDM |
| `A04`, `A05` | El ticket se asigna a quien tiene menor carga ponderada en «En validación» y «Asignado/En diseño» | `conn_hubspotCarga` (regla completa en `bpmn.md` → Conectores por tarea) | tarea de servicio |
| `A06` | Al asignar, el ticket queda con propietario y en «En validación» | `conn_hubspotActualizar` en `6_actualizarTicket` | tarea de servicio |
| plan v2 paso 3 | La validación solo concluye viable, bloqueado o no viable, siempre con nota | `resultado_valido`, `notaValidacion_presente`, `conceptoViabilidad_si_concluye` | constraint de contrato |
| plan v2 paso 3 | Solo la consultora asignada ve y hace la validación y el diseño | actor filter `filtroConsultoraDelCaso` | asignación |
| plan v2 paso 3 | Viable → «Asignado/En diseño»; bloqueado → «En espera información del lead» y vuelve a validar | `gwXor_1`, `11_pasarADiseno`, `12_pasarAEnEspera` | flujo y tarea de servicio |
| plan v2 paso 3 (decisión de la usuaria, 2026-11-24) | No viable → nota «Cerrado por viabilidad: …» y ticket a «Closed» | `conn_hubspotNota` en `10_validarSolicitud` y `13_registrarNoViable` | tarea de servicio |
| plan v2 paso 4 | Las URLs de los artefactos son enlaces | `urlPptaPreventa_valida`, `linkRepoPreventa_valido` | constraint de contrato |
| `A40` | Con la propuesta diseñada, el ticket pasa a «Entregado a ventas» | `conn_hubspotActualizar` en `40_entregarAVentas` | tarea de servicio |

## Pendientes de definición

- **Tamaño y tipo de los adjuntos**: sin límite en el contrato; el límite de subida de Bonita y el de la API de archivos de HubSpot aplican `[no verificado]`.
