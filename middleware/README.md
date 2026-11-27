# preventa-middleware (Rust)

Puente entre HubSpot y Bonita para la integración de preventa. Servicio **Rust** (axum + tokio + reqwest), **dockerizado**. Reemplaza al middleware Node anterior (queda en el historial de git).

## Qué hace

1. **Entrada** — `POST /webhooks/ticket-created`: webhook de app `ticket.creation` → instancia el caso en Bonita (`POST /API/bpm/process/{id}/instantiation`). **Idempotente** por `ticketId` (store en `data/store.json`). **Blindaje de pipeline:** solo actúa sobre el pipeline de Preventa (`HUBSPOT_PIPELINE`); ignora otros (p. ej. «Comercio»).
2. **Reconciliación** — barrido periódico (`RECONCILE_MS`) que compara casos activos de Bonita con tickets del pipeline y lo deja en el log; no actúa. `GET /health` → `{ok:true}`.

La entrada es lo **único** que el middleware hace sobre el caso: con la premisa v2 «Bonita-first» (`docs/08-construccion/plan-v2-bonita-first.md`) el caso avanza dentro de Bonita. La consultora valida la solicitud y diseña la propuesta en **formularios de Bonita**, y son los conectores de Bonita los que mueven el ticket de stage y escriben en el Negocio. Por eso no hay en el middleware avance a diseño, webhook de artefactos (`/webhooks/artifacts-loaded`), suscripción `deal.propertyChange` ni detector periódico: se retiraron.

El middleware **no escribe** en HubSpot: solo lee el ticket (blindaje de pipeline y reconciliación). Tampoco envía correos: el aviso a la consultora de cada tarea nueva (desde la versión 1.5 del proceso) lo envía Bonita con su conector `correo-tarea-asignada`.

## Correr

```bash
# con Docker (recomendado; no requiere toolchain Rust en el host)
docker build -t preventa-middleware middleware/
docker compose up          # usa middleware/.env

# o con Cargo (si hay Rust instalado)
cd middleware
cargo run
cargo test                 # tests de integración (wiremock) + unit (firma)
```

Variables de entorno: ver [`.env.example`](.env.example). El caso se instancia en `GestionPreventa` versión `PROCESS_VERSION` (por defecto **1.5**, la del pool vigente; súbela con cada versión nueva del pool). Secretos (`HUBSPOT_PRIVATE_APP_TOKEN`, `HUBSPOT_APP_SECRET`) solo por entorno, nunca en el repo.

## Configurar en HubSpot (Free/Starter — sin costo)

Una sola **suscripción de webhook** de la app → al host del middleware:
- `ticket.creation` → `/webhooks/ticket-created`

Si la app tenía la suscripción `deal.propertyChange` (versión anterior), hay que **quitarla** en HubSpot: el endpoint ya no existe.

## Despliegue

Imagen a GHCR por CI (`.github/workflows/ci.yml`); el middleware va detrás de un reverse proxy TLS; Bonita/PostgreSQL son externos (`BONITA_URL` apunta fuera). Ver el README raíz y `docs/arquitectura-eventos.md`.

## Seguridad

- Blindaje de pipeline (solo Preventa). Firma de webhook `X-HubSpot-Signature-v3` validada con `HUBSPOT_APP_SECRET`.
- Pruebas de escritura solo contra tickets de prueba desechables; nunca tickets reales sin autorización.
