---
actualizado: 2026-11-12
track: proceso-bpms
total_parametros: 7
---

# Catálogo de Parámetros y Catálogos — Gestión de Preventa

> Transversal. Todo `param_*` citado en `docs/07-bonita/` tiene una fila aquí. Los siete son **técnicos por entorno** (parámetros de proceso de `GestionPreventa`); no hay listas de negocio en el módulo de parámetros. El token de la Private App de HubSpot **no es un parámetro**: vive solo en la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN`.

## Convenciones

- **ID**: `param_<nombre_corto>`, sin acentos.
- **Tipo**: `valor` (un número o texto único), `lista`, `tramo`, `tramo-cascada`.
- **Quién administra**: quien puede cambiar el valor sin pasar por delivery.
- **Origen**: la regla o restricción que motiva que sea un parámetro y no un valor fijo.

## Catálogo

| ID | Nombre | Tipo | Valor(es) / rango conocido hoy | Quién administra | Doble control | Origen | Citado en |
|---|---|---|---|---|---|---|---|
| `param_hubspotUrlBase` | Dirección base de la API de HubSpot | valor | `https://api.hubapi.com` (Local: doble de pruebas `http://localhost:8099/hubspot`) | Equipo de operación (configuración del entorno) | no | Integración con HubSpot: cambia por entorno (en Local no se llama a HubSpot real) | `conn_hubspotLeer`, `conn_hubspotCarga`, `conn_hubspotActualizar` |
| `param_hubspotRutaTickets` | Ruta de tickets de la API de HubSpot | valor | `/crm/v3/objects/tickets` (lectura y búsqueda verificadas en vivo el 2026-11-12; la escritura no) | Equipo de operación (configuración del entorno) | no | HubSpot versiona su API por fecha: la ruta debe poder cambiarse sin tocar el proceso | `conn_hubspotLeer`, `conn_hubspotCarga`, `conn_hubspotActualizar` |
| `param_stageEnValidacion` | `stageId` del stage «En validación» | valor | `2` | Equipo de operación (configuración del entorno) | no | Stage que recibe el ticket al asignarse, y uno de los dos que miden la carga de cada consultor | `6_actualizarTicket`, `4_verificarDisponibilidad` |
| `param_stageEnDiseno` | `stageId` del stage «Asignado/En diseño» | valor | `3` | Equipo de operación (configuración del entorno) | no | El otro stage que mide la carga de cada consultor (Bonita no lo escribe) | `4_verificarDisponibilidad` |
| `param_stageEntregado` | `stageId` del stage «Entregado a ventas» | valor | `1425810258` | Equipo de operación (configuración del entorno) | no | Stage que recibe el ticket al cargarse los artefactos en el negocio | `40_entregarAVentas` |
| `param_consultores` | Consultores que entran en el reparto de tickets | valor | `89450376:Linda;89450377:Viviana` (pares «owner de HubSpot:nombre», en orden, separados por «;») | Equipo de operación (configuración del entorno) | no | Reunión de socialización: todos los tickets se asignan a una de las dos consultoras; la lista cambia por vacaciones o ingresos | `4_verificarDisponibilidad`, `5_asignarConsultor` |
| `param_pipelineTickets` | Pipeline de tickets «Mesa de preventa» | valor | `0` | Equipo de operación (configuración del entorno) | no | La carga de cada consultora se mide solo sobre los tickets de este pipeline | `4_verificarDisponibilidad` |

## `[PARAM]` citados en otros artefactos sin fila aquí todavía

- (ninguno pendiente)

## Historial de cambios al catálogo

| Fecha | Qué cambió | Quién lo decidió |
|---|---|---|
| 2026-11-12 | Catálogo abierto con nueve parámetros para el proceso completo (borrador archivado en `docs/07-bonita/insumo-preventa/borrador-proceso-completo/`) | Equipo de construcción |
| 2026-11-12 | Reducido a cinco: la reunión de socialización fija que Bonita solo automatiza la asignación y dos cambios de estado del ticket | Reunión de socialización del proceso (Linda Lozano, Angie Gaita) |
| 2026-11-12 | Añadido `param_consultores` (sustituye al catálogo `ConsultorPreventa` del BDM, inalcanzable desde los scripts del pool según la auditoría de las capas) | Equipo de construcción (pendiente de confirmación) |
