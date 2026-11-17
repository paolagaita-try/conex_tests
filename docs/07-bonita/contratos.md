---
actualizado: 2026-11-12
capa: 2
motor: Bonita
deriva_de: docs/07-bonita/bpmn.md, docs/07-bonita/bdm.md, docs/07-bonita/insumo-preventa/reunion-socializacion.md
total_contratos: 2
---

# Capa 2 — Contratos y operaciones — Gestión de Preventa

> Fuente: `bpmn.md` y la reunión de socialización. Solo hay dos contratos, y los dos los cumple el middleware por la API (ninguna persona): el de instanciación (se creó un ticket) y el de la tarea de espera (se cargaron los artefactos, o el ticket se cerró sin entregar).

## Convenciones

- **ID de contrato**: `ctr_instanciacion` y `ctr_<id-tarea>` (reservados en `bpmn.md`).
- **Tipo de input**: `TEXT` (tipo de contrato de Bonita 2026.2).
- **Destino**: el atributo del objeto de negocio (`Objeto.atributo`) o la process variable (`pv <variable>`) que la operación escribe con ese input.
- **Constraint**: expresión sobre los inputs, con nombre y mensaje; su Groovy va en `docs/08-construccion/expresiones.md` (`ctr_<contrato>.<constraint>`).
- **Operación**: igual a la plantilla de persistencia `asignacion-directa` de `bdm.md` salvo los literales indicados. Un destino escrito por un script lleva su marca (`op_<tarea>.<atributo>`).

## Contrato de instanciación — `ctr_instanciacion`

### `GestionPreventa` 1.0

Formulario asociado (capa 3): `frm_instanciacion` (`No form`). Fuente: el middleware instancia el caso por la API REST al recibir el webhook `ticket.creation` de HubSpot.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (Tarea de Proceso → Entradas) |
|---|---|---|---|---|---|---|
| `ticketId` | TEXT | no | sí | — | `Preventa.ticketId` | webhook `ticket.creation` → identificador del ticket |

| Constraint | Expresión (lenguaje natural o Groovy) | Mensaje de error | AC que la origina |
|---|---|---|---|
| `ticketId_presente` | ticketId no está vacío | El identificador del ticket es obligatorio | insumo `A02` (ticket de preventa creado) |

Operaciones al instanciar: según plantilla `asignacion-directa` con literales: `Preventa.estado` = `recibida`; crea `Preventa` con el `ticketId` del input. La idempotencia por ticket se apoya en la unique constraint de `Preventa.ticketId`: se espera que un segundo caso del mismo ticket falle al instanciar. `[no verificado]` en ejecución; el middleware recibiría un error genérico, así que además debe evitar reenviar un ticket ya instanciado.

## Contratos de tarea humana

### `ctr_18_esperarArtefactos` — Esperar la carga de artefactos en el negocio

- **Tarea** (`bpmn.md`): `18_esperarArtefactos`, actor Orquestador (la completa el middleware por la API).
- **Formulario asociado** (capa 3): `frm_18_esperarArtefactos` (`No form`).
- **Tarea de Proceso**: reunión de socialización, 28:22 y 39:22; insumo `A18` y `A40`.
- **Δestado**: `asignada` → `artefactosCargados` o `cerrada`.

| Input | Tipo | Múltiple | Obligatorio | Hijos (si COMPLEX) | Destino | Fuente (T-… → Entradas / Salidas) |
|---|---|---|---|---|---|---|
| `resultado` | TEXT | no | sí | — | `pv resultadoPreventa` | middleware → `entregado` si el negocio ya tiene los artefactos; `cerrado` si el ticket se cerró sin entregar |

| Constraint | Expresión | Mensaje de error | AC que la origina |
|---|---|---|---|
| `resultado_valido` | resultado es entregado o cerrado | El resultado debe ser entregado o cerrado | reunión 28:22 (entrega) e insumo `EE1`, `EE4` (cierre sin entrega) |

**Datos de solo lectura que el formulario consulta** (no son inputs): ninguno (no hay formulario).

**Operaciones**: plantilla `asignacion-directa`; literales: ninguno; por script, `Preventa.estado` ← `artefactosCargados si resultado es entregado, si no cerrada` (`op_18_esperarArtefactos.estado`); process variables actualizadas: `resultadoPreventa` (para `gwXor_1`). Desviación de la plantilla: ninguna.

## Operaciones de tareas de servicio y script

| Tarea | Conector | Operaciones (plantilla / literales) | Escribe | Process variables |
|---|---|---|---|---|
| `3_consultarTicket` | `conn_hubspotLeer` | `asignacion-directa` / ninguno; las salidas del conector escriben los datos del ticket (`bpmn.md` → Conectores por tarea) | `Preventa.asunto` | — |
| `4_verificarDisponibilidad` | `conn_hubspotCarga` | `asignacion-directa` / ninguno; la salida del conector escribe la process variable (`bpmn.md` → Conectores por tarea) | — | `ownerElegido` |
| `5_asignarConsultor` | — | `asignacion-directa` / `Preventa.estado` = `asignada`; script `Preventa.consultorOwnerId` ← `el valor de la process variable ownerElegido` (`op_5_asignarConsultor.consultorOwnerId`); script `Preventa.consultor` ← `el nombre que param_consultores da al owner de la process variable ownerElegido` (`op_5_asignarConsultor.consultor`) | `Preventa.estado`, `Preventa.consultorOwnerId`, `Preventa.consultor` | — |
| `6_actualizarTicket` | `conn_hubspotActualizar` | — (sin escritura) | — | — |
| `40_entregarAVentas` | `conn_hubspotActualizar` | `asignacion-directa` / `Preventa.estado` = `entregadaAVentas` | `Preventa.estado` | — |

Los dos scripts de `5_asignarConsultor` leen solo la process variable `ownerElegido`, que dejó la tarea anterior: ninguno depende de lo que escribe otro.

## Matriz tarea ↔ contrato ↔ formulario (la revisa el gate)

| Tarea humana | Contrato | Formulario (capa 3) | Inputs | Constraints |
|---|---|---|---|---|
| (instanciación) | `ctr_instanciacion` | `frm_instanciacion` | 1 | 1 |
| `18_esperarArtefactos` | `ctr_18_esperarArtefactos` | `frm_18_esperarArtefactos` | 1 | 1 |

## Cobertura de las reglas de validación de los AC

| Tarea de Proceso | Regla del AC | Cubierta por | Tipo |
|---|---|---|---|
| `A02` | Un ticket genera un solo caso | unique constraint `Preventa.ticketId` (rechazo del duplicado `[no verificado]` en ejecución) | BDM |
| `A04`, `A05` | El ticket se asigna a quien tiene menos tickets en «En validación» y «Asignado/En diseño» | `conn_hubspotCarga` (regla completa en `bpmn.md` → Conectores por tarea) | tarea de servicio |
| `A06` | Al asignar, el ticket queda con propietario y en «En validación» | `conn_hubspotActualizar` en `6_actualizarTicket` | tarea de servicio |
| `A40` | Con los artefactos cargados, el ticket pasa a «Entregado a ventas» | `gwXor_1` y `conn_hubspotActualizar` en `40_entregarAVentas` | flujo y tarea de servicio |
| `A18` | El resultado de la espera solo puede ser entrega o cierre | `resultado_valido` | constraint de contrato |

## Pendientes de definición

- El contrato de `18_esperarArtefactos` es un diseño de este documento: la reunión dice que el paso a «Entregado a ventas» es automático al cargar los artefactos, pero no cómo se entera Bonita. Depende del middleware (ver `bpmn.md` → Pendientes).
