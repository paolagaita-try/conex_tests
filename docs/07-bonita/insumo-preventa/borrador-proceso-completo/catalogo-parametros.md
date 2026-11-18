---
actualizado: 2026-11-12
track: proceso-bpms
total_parametros: 9
---

# Catálogo de Parámetros y Catálogos — Gestión de Preventa

> Transversal. Todo `param_*` citado en `docs/07-bonita/` tiene una fila aquí. Los nueve son **técnicos por entorno** (parámetros de proceso de `GestionPreventa`); no hay listas de negocio en el módulo de parámetros. El token de la Private App de HubSpot **no es un parámetro**: vive solo en la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN`.

## Convenciones

- **ID**: `param_<nombre_corto>`, sin acentos.
- **Tipo**: `valor` (un número o texto único), `lista`, `tramo`, `tramo-cascada`.
- **Quién administra**: quien puede cambiar el valor sin pasar por delivery.
- **Origen**: la regla o restricción que motiva que sea un parámetro y no un valor fijo.

## Catálogo

| ID | Nombre | Tipo | Valor(es) / rango conocido hoy | Quién administra | Doble control | Origen | Citado en |
|---|---|---|---|---|---|---|---|
| `param_hubspotUrlBase` | Dirección base de la API de HubSpot | valor | `https://api.hubapi.com` (Local: doble de pruebas `http://localhost:8099/hubspot`) | Equipo de operación (configuración del entorno) | no | Integración con HubSpot: cambia por entorno (en Local no se llama a HubSpot real) | `conn_hubspotLeer`, `conn_hubspotActualizar` |
| `param_hubspotRutaTickets` | Ruta de tickets de la API de HubSpot | valor | `/crm/v3/objects/tickets` (verificada en la Fase 0) | Equipo de operación (configuración del entorno) | no | HubSpot versiona su API por fecha (cambios en marzo y septiembre): la ruta debe poder cambiarse sin tocar el proceso | `conn_hubspotLeer`, `conn_hubspotActualizar` |
| `param_stageEnValidacion` | `stageId` del stage «En validación» | valor | `2` | Equipo de operación (configuración del entorno) | no | Mapa estado del caso → stage del ticket (pipeline «Mesa de preventa», id `0`) | `6_actualizarTicket` |
| `param_stageEnDiseno` | `stageId` del stage «Asignado/En diseño» | valor | `3` | Equipo de operación (configuración del entorno) | no | Mapa estado del caso → stage del ticket | `31_prepararAnalisis` |
| `param_stageEnEspera` | `stageId` del stage «En espera información del lead» | valor | `1425810257` | Equipo de operación (configuración del entorno) | no | Mapa estado del caso → stage del ticket | `14_realizarLevantamiento`, `37_radicarPreguntas` |
| `param_stageEntregado` | `stageId` del stage «Entregado a ventas» | valor | `1425810258` | Equipo de operación (configuración del entorno) | no | Mapa estado del caso → stage del ticket | `40_entregarAVentas` |
| `param_stageCerrado` | `stageId` del stage «Closed» | valor | `4` | Equipo de operación (configuración del entorno) | no | Mapa estado del caso → stage del ticket | `13_registrarNoContinua`, `39_notificarNoViabilidad`, `26_registrarRechazo`, `30_iniciarEjecucion` |
| `param_urlAgenteIA` | Dirección del servicio del Agente IA de Preventa | valor | `http://localhost:8099/agente-ia` (doble de pruebas; el servicio real no está definido) | Equipo de operación (configuración del entorno) | no | Integración con el Agente IA (Claude): cambia por entorno | `16_generarArtefactos` (`conn_agenteIA`) |
| `param_plazoRespuestasMs` | Plazo de espera de las respuestas de la entidad en una licitación, en milisegundos | valor | `20000` (Local); `432000000` = 5 días (provisional) | Equipo de operación (configuración del entorno) | no | Vencimiento del plazo de respuestas (`BE1` del insumo); corto en Local para probar el vencimiento | `evTimer_1` |

## `[PARAM]` citados en otros artefactos sin fila aquí todavía

- (ninguno pendiente)

## Historial de cambios al catálogo

| Fecha | Qué cambió | Quién lo decidió |
|---|---|---|
| 2026-11-12 | Catálogo abierto con los nueve parámetros técnicos del proceso, a partir del flujo de preventa y de los IDs reales de la Fase 0 | Equipo de construcción (pendiente de confirmación del mapa de stages) |
