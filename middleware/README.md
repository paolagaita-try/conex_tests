# preventa-middleware (Rust)

Puente entre HubSpot y Bonita para la integración de preventa. Servicio **Rust** (axum + tokio + reqwest), **dockerizado**. Reemplaza al middleware Node anterior (queda en el historial de git).

## Qué hace

1. **Entrada** — `POST /webhooks/ticket-created`: webhook de app `ticket.creation` → instancia el caso en Bonita (`POST /API/bpm/process/{id}/instantiation`). **Idempotente** por `ticketId` (store en `data/store.json`). **Blindaje de pipeline:** solo actúa sobre el pipeline de Preventa (`HUBSPOT_PIPELINE`); ignora otros (p. ej. «Comercio»).
2. **Avance a diseño (manual)** — el paso «En validación» → «Asignado/En diseño» lo hace **la consultora** en el tablero de HubSpot. El middleware **no** lo automatiza (antes había un temporizador; se eliminó porque ensuciaba los tiempos por etapa y saturaba el trabajo en curso).
3. **Artefactos de preventa** — ya **no** pasan por el middleware: entran por **formularios de Bonita** (premisa v2 «Bonita first», ver `docs/08-construccion/plan-v2-bonita-first.md`). Se retiraron el webhook `/webhooks/artifacts-loaded`, la suscripción `deal.propertyChange` y el detector periódico de artefactos.
4. **Reconciliación** — barrido periódico (log). `GET /health` → `{ok:true}`.

El middleware **no escribe** en HubSpot: solo lee el ticket (blindaje de pipeline y reconciliación).

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

Variables de entorno: ver [`.env.example`](.env.example). Secretos (`HUBSPOT_PRIVATE_APP_TOKEN`, `HUBSPOT_APP_SECRET`) solo por entorno, nunca en el repo.

## Configurar en HubSpot (Free/Starter — sin costo)

Una sola **suscripción de webhook** de la app → al host del middleware:
- `ticket.creation` → `/webhooks/ticket-created`

Si la app tenía la suscripción `deal.propertyChange` (versión anterior), hay que **quitarla** en HubSpot: el endpoint ya no existe.

## Despliegue

Imagen a GHCR por CI (`.github/workflows/ci.yml`); el middleware va detrás de un reverse proxy TLS; Bonita/PostgreSQL son externos (`BONITA_URL` apunta fuera). Ver el README raíz y `docs/arquitectura-eventos.md`.

## Seguridad

- Blindaje de pipeline (solo Preventa). Firma de webhook `X-HubSpot-Signature-v3` validada con `HUBSPOT_APP_SECRET`.
- Pruebas de escritura solo contra tickets de prueba desechables; nunca tickets reales sin autorización.
