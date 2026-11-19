# Integración HubSpot ↔ Bonita

Automatiza el **carril del Orquestador** del proceso de preventa: cuando se crea un ticket en HubSpot, se instancia un caso en Bonita que asigna una consultora por **balance de carga**, mueve el ticket por sus estados y, cuando la consultora carga los artefactos en el Negocio, lo pasa a **«Entregado a ventas»**. El resto del proceso es manual en HubSpot.

> Alcance (reunión de socialización): Bonita automatiza **solo** el carril Orquestador. Sin formularios, sin agente IA, sin Fase 2.

## Flujo de punta a punta

```
HubSpot: ticket creado (pipeline «Mesa de preventa»)
        │  webhook de app ticket.creation
        ▼
Middleware  ──► Bonita: instancia el caso GestionPreventa
        ▼
Bonita:  3_consultarTicket → 4_verificarDisponibilidad → 5_asignarConsultor → 6_actualizarTicket
         (ticket → «En validación», propietario = consultora elegida por carga)
        ▼
Middleware: ~5 min después → ticket a «Asignado/En diseño»
        ▼
Consultora llena las 4 fuentes en el NEGOCIO (Deal, sección «Definición Preventa»)
        │  webhook deal.propertyChange  (+ detector propio como red de seguridad)
        ▼
Middleware: detecta las 4 fuentes → completa la espera (18_esperarArtefactos)
        ▼
Bonita: 40_entregarAVentas → ticket a «Entregado a ventas»   (el Negocio NO se mueve)
```

**Las 4 fuentes del Negocio:** `concepto_viabilidad`, `valoracion_operaciones`, `url_ppta_preventa`, `link_repo_preventa` (las 4 con valor = artefactos cargados).

**Estados del ticket** (pipeline «Mesa de preventa», id `0`): Solicitud recibida `1` → En validación `2` → Asignado/En diseño `3` → Entregado a ventas `1425810258` (Closed `4`).

## Componentes

| Componente | Qué es | Dónde |
|---|---|---|
| **Proceso Bonita `GestionPreventa`** | Orquestación BPMN (1 lane: Orquestador) | `bonita-project/` |
| **3 conectores REST propios** | `hubspot-ticket-leer`, `hubspot-consultores-menor-carga`, `hubspot-ticket-actualizar` (REST nativo a HubSpot) | `bonita-project/extensions/preventa-conectores/` |
| **Middleware** | Puente externo HubSpot↔Bonita (entrada, avance a diseño, detección de artefactos, entrega) | `middleware/` — ver [middleware/README.md](middleware/README.md) |
| **Documentación de diseño** | Fuente del proceso (BPMN, BDM, contratos, parámetros) | `docs/07-bonita/`, `docs/08-construccion/`, `docs/00-parametros/` |
| **Journey + mock** | Pruebas del proceso con colección Postman contra un doble de HubSpot | `journey/`, `mock.json` |

> Regla dura: `docs/07-bonita/` es la **fuente**. Un fichero generado no se edita a mano: se cambia la fuente y se regenera con `tools/arnes.sh generar`.

## Conectores (resumen)

| Conector | Tarea | HTTP a HubSpot | Entradas | Salida |
|---|---|---|---|---|
| `hubspot-ticket-leer` | `3_consultarTicket` | `GET /crm/v3/objects/tickets/{id}?properties=subject` | urlBase, rutaTickets, ticketId | `asunto` → `Preventa.asunto` |
| `hubspot-consultores-menor-carga` | `4_verificarDisponibilidad` | `POST /crm/v3/objects/tickets/search` | urlBase, rutaTickets, pipelineId, ownerIds, stages, ultimoOwnerId | `ownerElegido` |
| `hubspot-ticket-actualizar` | `6_actualizarTicket` y `40_entregarAVentas` | `PATCH /crm/v3/objects/tickets/{id}` | urlBase, rutaTickets, ticketId, stageId, ownerId | — |

El **token de Private App** no es una entrada: el conector lo lee de la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN` (header `Authorization: Bearer`).

## Requisitos

- JDK 17, Maven, Node 18+, `trycore-bonita` (arnés). Verifica con `trycore-bonita doctor`.
- Bonita 2026.2 Community.

## Construir y probar

```bash
# Generar artefactos del proceso desde docs/07-bonita/ y construir el bundle
tools/arnes.sh generar
tools/arnes.sh verificar            # custodios/inventario

# Journey (proceso contra el bundle + mock de HubSpot)
tools/arnes.sh journey

# Middleware
cd middleware && npm test           # node --test (11/11)
```

## Configuración (parámetros del proceso, por entorno)

`param_hubspotUrlBase` (Local → mock `localhost:8099`; Prod → `https://api.hubapi.com`), `param_hubspotRutaTickets` (`/crm/v3/objects/tickets`), `param_stageEnValidacion` (`2`), `param_stageEnDiseno` (`3`), `param_stageEntregado` (`1425810258`), `param_pipelineTickets` (`0`), `param_consultores` (`ownerId:nombre;...`).

Variables de entorno del **middleware**: ver [`middleware/.env.example`](middleware/.env.example).

## Despliegue (producción)

1. **HubSpot:** token de Private App con scopes `tickets`, `crm.objects.deals.read`, `crm.objects.owners.read`; app con 2 webhooks → middleware: `ticket.creation` y `deal.propertyChange` (sobre las 4 fuentes). Guardar `HUBSPOT_APP_SECRET`.
2. **Middleware:** host con HTTPS público (Node 18+), variables de entorno rellenas, gestor de procesos.
3. **Bonita:** desplegar el bundle con entorno **Production** (`param_hubspotUrlBase=https://api.hubapi.com`), `HUBSPOT_PRIVATE_APP_TOKEN` en la JVM, `ofelia.bot` con perfil/permisos REST, actor `orquestador` mapeado; subir la versión del pool al desplegar.

## Estado

- ✅ Proceso + 3 conectores construidos; journey verde; middleware con 11/11 tests.
- ✅ Verificado **en vivo contra HubSpot real**: entrada, round robin, «En validación», avance a «Diseño», detección de las 4 fuentes y PATCH final a «Entregado a ventas» por el conector.
- ⏳ Pendiente: corrida encadenada 100% automática con ticket+Negocio frescos; despliegue (middleware público, Bonita prod, registro de webhooks); rotar el token de pruebas.

## Seguridad

- Secretos solo por variable de entorno (nunca en el repo ni en argumentos). El `.env` del middleware está gitignored.
- Pruebas de escritura solo contra tickets de prueba desechables; nunca tickets de producción reales sin autorización.
- El middleware solo actúa sobre el pipeline de Preventa (blindaje); ignora otros pipelines (p. ej. «Comercio»). El Negocio nunca se escribe.
