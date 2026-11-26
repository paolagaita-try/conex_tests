---
actualizado: 2026-11-26
track: proceso-bpms
total_parametros: 16
---

# Catálogo de Parámetros y Catálogos — Gestión de Preventa

> Transversal. Todo `param_*` citado en `docs/07-bonita/` tiene una fila aquí. Los dieciséis son **técnicos por entorno** (parámetros de proceso de `GestionPreventa`); no hay listas de negocio en el módulo de parámetros. El token de la Private App de HubSpot **no es un parámetro**: vive solo en la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN`.

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
| `param_stageEnDiseno` | `stageId` del stage «Asignado/En diseño» | valor | `3` | Equipo de operación (configuración del entorno) | no | El otro stage que mide la carga de cada consultor; Bonita lo escribe al validar «viable» (v2) | `4_verificarDisponibilidad`, `11_pasarADiseno` |
| `param_stageEntregado` | `stageId` del stage «Entregado a ventas» | valor | `1425810258` | Equipo de operación (configuración del entorno) | no | Stage que recibe el ticket al terminar la consultora el diseño de la propuesta | `40_entregarAVentas` |
| `param_stageEnEspera` | `stageId` del stage «En espera información del lead» | valor | `1425810257` | Equipo de operación (configuración del entorno) | no | Stage que recibe el ticket cuando la validación queda bloqueada por falta de información del lead (v2) | `12_pasarAEnEspera` |
| `param_stageCerrado` | `stageId` del stage «Closed» | valor | `4` | Equipo de operación (configuración del entorno) | no | Stage que recibe el ticket cuando la validación concluye «no viable»: cerrado por viabilidad (decisión de la usuaria, 2026-11-24) | `13_registrarNoViable` |
| `param_consultores` | Consultores que entran en el reparto de tickets | valor | `89450376:Linda:linda.lozano;89450377:Viviana:viviana.velasquez` (tríos «owner de HubSpot:nombre:usuario de Bonita», en orden, separados por «;») | Equipo de operación (configuración del entorno) | no | Reunión de socialización: todos los tickets se asignan a una de las dos consultoras; la lista cambia por vacaciones o ingresos | `4_verificarDisponibilidad`, `5_asignarConsultor`, actor filter `filtroConsultoraDelCaso` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_pipelineTickets` | Pipeline de tickets «Mesa de preventa» | valor | `0` | Equipo de operación (configuración del entorno) | no | La carga de cada consultora se mide solo sobre los tickets de este pipeline | `4_verificarDisponibilidad` |
| `param_smtpHost` | Servidor SMTP del aviso de tarea | valor | `localhost` (Local); `smtp.gmail.com` (Qualification, Production) | Equipo de operación (configuración del entorno) | no | Infraestructura de correo: cambia por entorno (en Local, el SMTP de prueba del journey) | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_smtpPuerto` | Puerto SMTP | valor | `2525` (Local); `587` (Qualification, Production) | Equipo de operación (configuración del entorno) | no | Infraestructura de correo: cambia por entorno | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_smtpStarttls` | Cifrar la conexión SMTP con STARTTLS | valor | `false` (Local); `true` (Qualification, Production) | Equipo de operación (configuración del entorno) | no | Gmail exige STARTTLS en el 587; el SMTP de prueba no cifra | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_smtpUsuario` | Cuenta remitente (y usuario SMTP) | valor | `preventa@trycore.com` (propuesta, por confirmar con infraestructura) | Equipo de operación (configuración del entorno) | no | Cuenta de Google Workspace que envía los avisos | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_smtpContrasena` | Contraseña de aplicación de la cuenta remitente | valor | `sin-configurar` (marcador; el valor real nunca va en el repositorio: el conector usa entonces la variable de entorno `PREVENTA_SMTP_CONTRASENA` del servidor) | Equipo de operación (configuración del entorno) | no | Secreto de la cuenta remitente: se configura en el servidor | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_smtpRemitenteNombre` | Nombre visible del remitente | valor | `Preventa Trycore` | Equipo de operación (configuración del entorno) | no | Decisión de la usuaria, 2026-11-26 | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |
| `param_bonitaUrlBase` | Dirección base de Bonita para el enlace de la tarea | valor | `http://localhost:8080/bonita` (pendiente la URL pública) | Equipo de operación (configuración del entorno) | no | El botón del correo abre la tarea en la aplicación `hubspotBonita` de este servidor | Conector `conn_correoTarea` (`10_validarSolicitud`, `20_disenarPropuesta`) |

## `[PARAM]` citados en otros artefactos sin fila aquí todavía

- (ninguno pendiente)

## Historial de cambios al catálogo

| Fecha | Qué cambió | Quién lo decidió |
|---|---|---|
| 2026-11-12 | Catálogo abierto con nueve parámetros para el proceso completo (borrador archivado en `docs/07-bonita/insumo-preventa/borrador-proceso-completo/`) | Equipo de construcción |
| 2026-11-12 | Reducido a cinco: la reunión de socialización fija que Bonita solo automatiza la asignación y dos cambios de estado del ticket | Reunión de socialización del proceso (Linda Lozano, Angie Gaita) |
| 2026-11-12 | Añadido `param_consultores` (sustituye al catálogo `ConsultorPreventa` del BDM, inalcanzable desde los scripts del pool según la auditoría de las capas) | Equipo de construcción (pendiente de confirmación) |
| 2026-11-24 | v2 «Bonita-first»: añadido `param_stageEnEspera`; `param_consultores` pasa a tríos con el usuario de Bonita de cada consultora (`linda.lozano`, `viviana.velasquez`) para el actor filter | Usuaria (aprobó el plan v2) |
| 2026-11-24 | Añadido `param_stageCerrado` (`4`): «no viable» cierra el ticket | Usuaria |
| 2026-11-26 | Versión 1.5: añadidos los seis `param_smtp*` y `param_bonitaUrlBase` del aviso por correo de cada tarea nueva (Gmail / Google Workspace); la contraseña de aplicación, fuera del repositorio | Usuaria |
