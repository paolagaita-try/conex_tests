# preventa-middleware (Rust)

Puente entre HubSpot y Bonita para la integración de preventa. Servicio **Rust** (axum + tokio + reqwest), **dockerizado**. Reemplaza al middleware Node anterior (queda en el historial de git).

## Qué hace

1. **Entrada** — `POST /webhooks/ticket-created`: webhook de app `ticket.creation` → instancia el caso en Bonita (`POST /API/bpm/process/{id}/instantiation`). **Idempotente** por `ticketId` (store en `data/store.json`). **Blindaje de pipeline:** solo actúa sobre el pipeline de Preventa (`HUBSPOT_PIPELINE`); ignora otros (p. ej. «Comercio»).
2. **Avance a diseño (manual)** — el paso «En validación» → «Asignado/En diseño» lo hace **la consultora** en el tablero de HubSpot. El middleware **no** lo automatiza (antes había un temporizador; se eliminó porque ensuciaba los tiempos por etapa y saturaba el trabajo en curso).
3. **Espera** — `POST /webhooks/artifacts-loaded`: las **4 fuentes** viven en el **Negocio (Deal)**. Con `deal.propertyChange`, si las 4 (`concepto_viabilidad`, `valoracion_operaciones`, `url_ppta_preventa`, `link_repo_preventa`) tienen valor, busca el ticket asociado (cardinalidad 1 Negocio→N tickets, elige el activo de Preventa) y completa la espera → «Entregado a ventas». `ticket.propertyChange` a stage cerrado → `cerrado`. **Detector propio** cada `ARTEFACTOS_CHECK_MS` como red de seguridad (entrega sin depender del webhook).
4. **Reconciliación** — barrido periódico (log). `GET /health` → `{ok:true}`.

El **Negocio nunca se mueve**; solo se escribe el **ticket**.

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

Dos **suscripciones de webhook** de la app → al host del middleware:
- `ticket.creation` → `/webhooks/ticket-created`
- `deal.propertyChange` sobre las 4 fuentes del Negocio → `/webhooks/artifacts-loaded`

Las 4 propiedades **ya existen** en el Negocio (grupo `dealinformation`); no hay que crearlas. El Negocio debe estar **asociado** al ticket.

## Despliegue

Imagen a GHCR por CI (`.github/workflows/ci.yml`); el middleware va detrás de un reverse proxy TLS; Bonita/PostgreSQL son externos (`BONITA_URL` apunta fuera). Ver el README raíz y `docs/arquitectura-eventos.md`.

## Seguridad

- Blindaje de pipeline (solo Preventa). Firma de webhook `X-HubSpot-Signature-v3` validada con `HUBSPOT_APP_SECRET`.
- Pruebas de escritura solo contra tickets de prueba desechables; nunca tickets reales sin autorización.
