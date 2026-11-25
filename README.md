# Integración HubSpot ↔ Bonita

Gestiona el proceso de preventa **en Bonita** («Bonita-first»): cuando se crea un ticket en HubSpot, se instancia un caso en Bonita que asigna una consultora por **carga ponderada por prioridad**; la consultora **valida la solicitud** y **diseña la propuesta** en formularios Bonita (Svelte), y Bonita escribe por detrás en HubSpot el stage y el propietario del ticket, las notas, las propiedades del Negocio y los adjuntos. El equipo de Preventa no trabaja en HubSpot; el cierre lo sigue haciendo el comercial en HubSpot.

> Alcance vigente: `docs/08-construccion/plan-v2-bonita-first.md` (decisión del 2026-11-24), que reemplaza el alcance anterior «solo carril del orquestador». Sin agente IA, sin Fase 2.

## Flujo de punta a punta

```
HubSpot: ticket creado (pipeline «Mesa de preventa»)
        │  webhook de app ticket.creation
        ▼
Middleware  ──► Bonita: instancia el caso GestionPreventa (idempotente por ticketId)
        ▼
Bonita:  3_consultarTicket → 4_verificarDisponibilidad → 5_asignarConsultor → 6_actualizarTicket
         (ticket → «En validación», propietario = consultora elegida por carga)
        ▼
Consultora: formulario «Validar solicitud» (10_validarSolicitud) — nota en ticket y Negocio
        ├─ viable    → 11_pasarADiseno: ticket → «Asignado/En diseño» + concepto_viabilidad en el Negocio
        ├─ bloqueado → 12_pasarAEnEspera: ticket → «En espera información del lead» → vuelve a validar
        └─ no viable → 13_registrarNoViable: concepto_viabilidad + ticket → «Closed» (fin)
        ▼
Consultora: formulario «Diseñar propuesta» (20_disenarPropuesta)
         — propiedades del Negocio y nota; 21_subirAdjuntos si hay adjuntos
        ▼
Bonita: 40_entregarAVentas → ticket a «Entregado a ventas»   (la etapa del Negocio NO se mueve)
```

**Propiedades del Negocio que escribe Bonita:** `concepto_viabilidad` (al validar), `valoracion_operaciones`, `url_ppta_preventa`, `link_repo_preventa` (al diseñar la propuesta).

**Estados del ticket** (pipeline «Mesa de preventa», id `0`): Solicitud recibida `1` → En validación `2` → Asignado/En diseño `3` (o En espera información del lead `1425810257`) → Entregado a ventas `1425810258`; Closed `4`. Todos los cambios de stage los hace Bonita, salvo el cierre del comercial.

## Componentes

| Componente | Qué es | Dónde |
|---|---|---|
| **Proceso Bonita `GestionPreventa`** | BPMN con 2 lanes: Orquestador (tareas automáticas; su actor es el usuario técnico del middleware) y Consultoras (tareas humanas, actor filter `filtroConsultoraDelCaso`) | `bonita-project/` |
| **Conectores REST propios** | `hubspot-ticket-leer`, `hubspot-consultores-menor-carga`, `hubspot-ticket-actualizar`, `hubspot-negocio-actualizar`, `hubspot-nota-crear`, `hubspot-archivo-subir` (REST nativo a HubSpot) | `bonita-project/extensions/preventa-conectores/` |
| **REST API extension `preventaContexto`** | Lectura del CRM (ticket, Negocio, empresa, contactos, owner) para precargar los formularios; el token solo vive en el servidor | `bonita-project/extensions/preventa-contexto-api-extension/` |
| **Formularios Svelte** | `frm10ValidarSolicitud`, `frm20DisenarPropuesta`, `frmOverview` | `frontend/` |
| **Middleware (Rust)** | Única entrada HubSpot→Bonita: `ticket.creation` → instancia el caso | `middleware/` — ver [middleware/README.md](middleware/README.md) |
| **Documentación de diseño** | Fuente del proceso (BPMN, BDM, contratos, formularios, parámetros) | `docs/07-bonita/`, `docs/08-construccion/`, `docs/00-parametros/` |
| **Journey + mock** | Pruebas del proceso con colección Postman contra un doble de HubSpot | `journey/`, `mock.json` |

> Regla dura: `docs/07-bonita/` es la **fuente**. Un fichero generado no se edita a mano: se cambia la fuente y se regenera con `tools/arnes.sh generar`.

## Conectores (resumen)

| Conector | Tareas | Llamada a HubSpot | Qué hace |
|---|---|---|---|
| `hubspot-ticket-leer` | `3_consultarTicket` | `GET` del ticket y de su Negocio asociado | lee el asunto y el Negocio del ticket |
| `hubspot-consultores-menor-carga` | `4_verificarDisponibilidad` | `POST /crm/v3/objects/tickets/search` | devuelve el owner con menor carga ponderada |
| `hubspot-ticket-actualizar` | `6`, `11`, `12`, `13`, `40` | `PATCH /crm/v3/objects/tickets/{id}` | stage del ticket (y owner en `6`) |
| `hubspot-negocio-actualizar` | `11`, `13`, `20` | `PATCH` del Negocio | propiedades del Negocio |
| `hubspot-nota-crear` | `10`, `20` | `POST` de una nota | nota asociada a ticket y Negocio |
| `hubspot-archivo-subir` | `21_subirAdjuntos` | carga de archivos (Files API) | sube los adjuntos y los asocia al Negocio |

Entradas y salidas exactas: `docs/07-bonita/bpmn.md` › Conectores por tarea y `docs/08-construccion/conectores-escritura-hubspot.md`. El **token de Private App** no es una entrada: el conector lo lee de la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN` (header `Authorization: Bearer`).

## Requisitos

- JDK 17, Maven, Node 18+ (formularios), `trycore-bonita` (arnés). Verifica con `trycore-bonita doctor`.
- Bonita 2026.2 Community.
- Middleware: Docker, o Rust estable si se compila con Cargo.

## Construir y probar

```bash
# Generar los ficheros del proceso desde docs/07-bonita/ y construir el bundle
tools/arnes.sh generar
tools/arnes.sh verificar            # custodios/inventario

# Journey (proceso contra el bundle + mock de HubSpot)
tools/arnes.sh journey

# Middleware
cd middleware && cargo test         # o con Docker: docker build -t preventa-middleware middleware/
```

## Configuración (parámetros del proceso, por entorno)

`param_hubspotUrlBase` (Local → mock `localhost:8099`; Prod → `https://api.hubapi.com`), `param_hubspotRutaTickets` (`/crm/v3/objects/tickets`), `param_stageEnValidacion` (`2`), `param_stageEnDiseno` (`3`), `param_stageEnEspera` (`1425810257`), `param_stageEntregado` (`1425810258`), `param_stageCerrado` (`4`), `param_pipelineTickets` (`0`), `param_consultores` (owner de HubSpot ↔ usuario Bonita de cada consultora). Detalle en `docs/07-bonita/bdm.md`.

Variables de entorno del **middleware**: ver [`middleware/.env.example`](middleware/.env.example).

## Despliegue (producción)

1. **HubSpot:** token de Private App con los scopes de `docs/08-construccion/permisos-token-hubspot.md` (tickets y Negocios en lectura y escritura; empresas, contactos y owners en lectura; archivos; notas); app con **un solo** webhook → middleware: `ticket.creation`. Guardar `HUBSPOT_APP_SECRET`.
2. **Middleware:** imagen Docker (`docker-compose.yml`) detrás de un reverse proxy con HTTPS público, variables de entorno rellenas.
3. **Bonita:** desplegar el bundle con entorno **Production** (`param_hubspotUrlBase=https://api.hubapi.com`), `HUBSPOT_PRIVATE_APP_TOKEN` en la JVM, el usuario técnico del middleware con perfil/permisos REST, actores `orquestador` y `consultora` mapeados, cada consultora enlazada a su owner de HubSpot en `param_consultores`; subir la versión del pool al desplegar.

## Estado

- Proceso v2 (validación y propuesta en formularios Bonita), conectores de escritura, `preventaContexto` y formularios construidos; journey verde contra el mock (caminos entregada, bloqueada y no viable): `docs/08-construccion/evidencia-v2-proceso.md`.
- Middleware Rust: solo la entrada `ticket.creation`; `cargo test` en CI.
- Pendiente: despliegue (middleware público, Bonita prod, registro del webhook); rotar el token de pruebas.

## Seguridad

- Secretos solo por variable de entorno (nunca en el repo ni en argumentos). El `.env` del middleware está gitignored.
- Pruebas de escritura solo contra tickets y Negocios de prueba desechables; nunca objetos de producción reales sin autorización.
- El middleware solo actúa sobre el pipeline de Preventa (blindaje) e ignora los demás; no escribe en HubSpot. Toda escritura la hacen los conectores de Bonita. Del Negocio se escriben propiedades, notas y adjuntos, nunca su etapa.
