# preventa-middleware

Puente entre HubSpot y Bonita para la integración de preventa. **Sin dependencias externas** (Node 18+, módulos nativos).

## Qué hace

1. **Entrada** — `POST /webhooks/ticket-created`: al crearse un ticket en HubSpot (webhook de app `ticket.creation`), instancia el caso en Bonita (`POST /API/bpm/process/{id}/instantiation` con `{ticketId}`). **Idempotente** por `ticketId` (store en `data/store.json`).
2. **Espera** — `POST /webhooks/artifacts-loaded`: los **4 campos de artefactos** viven en el **Negocio (Deal)** (sección «Definición Preventa»), no en el ticket; los llenan las consultoras manualmente. Al llegar un `deal.propertyChange`, si los 4 campos (`concepto_viabilidad` —selector—, `estimacion_costos`, `url_ppta_preventa`, `link_repo_preventa`) tienen valor, el middleware **busca el ticket asociado al Negocio** y completa la tarea de espera con `resultado=entregado`. Si llega un `ticket.propertyChange` con el ticket en stage cerrado → `cerrado`. Bonita entonces pasa el ticket a «Entregado a ventas».
3. **Reconciliación** — job cada 24 h: compara casos Bonita vs tickets del pipeline y logea huérfanos/desincronizados.
4. `GET /health` → `{ok:true}`.

## Correr

```bash
cp .env.example .env     # rellena HUBSPOT_PRIVATE_APP_TOKEN, HUBSPOT_APP_SECRET, BONITA_PASSWORD...
node src/index.js        # o: npm start
npm test                 # tests (node --test) — pendientes de escribir, ver abajo
```

Con el bundle de pruebas de Bonita arriba en `:8080` (`BONITA_URL=http://localhost:8080/bonita`, `BONITA_USER=ofelia.bot`, `BONITA_PASSWORD=bpm`), prueba local:

```bash
# simular creación de ticket (usa un ticketId real o de prueba de HubSpot)
curl -X POST localhost:3000/webhooks/ticket-created -H 'Content-Type: application/json' -d '{"objectId":"51191820137"}'
# simular artefactos cargados
curl -X POST localhost:3000/webhooks/artifacts-loaded -H 'Content-Type: application/json' -d '{"objectId":"51191820137"}'
```

> Con `HUBSPOT_APP_SECRET` vacío no se valida la firma (dev). En producción, configúralo para validar `X-HubSpot-Signature-v3`.

## Configurar en HubSpot (Free/Starter — sin costo)

Decisión 2026-11-11: sin costo → **webhooks de app** (no Workflows nativos; estos exigen un plan de pago). En la app privada/pública de HubSpot se configuran dos **suscripciones de webhook**:
- `ticket.creation` → `POST https://<host>/webhooks/ticket-created` (instancia el caso).
- `deal.propertyChange` sobre las 4 propiedades de artefactos del **Negocio** (`concepto_viabilidad`, `estimacion_costos`, `url_ppta_preventa`, `link_repo_preventa`) → `POST https://<host>/webhooks/artifacts-loaded` (dispara la entrega). Opcional: `ticket.propertyChange` sobre `hs_pipeline_stage` para el cierre sin entrega.

Las 4 propiedades **ya existen** en el objeto Negocio (grupo `dealinformation`); no hay que crearlas. El Negocio debe estar **asociado** al ticket (asociación Deal↔Ticket) para que el middleware resuelva el ticket. Las suscripciones se crean por la UI de la app o por API con el token. El token de Private App y el `HUBSPOT_APP_SECRET` van por variable de entorno, nunca en el repo.

## Seguridad

- Todo secreto por variable de entorno (`.env` en `.gitignore`).
- Firma de webhook validada con `HUBSPOT_APP_SECRET`.
- Pruebas de escritura solo contra tickets de prueba desechables; nunca tickets de producción reales sin autorización.

## Pendiente (próxima sesión)

- `test/*.test.js` (node --test) con Bonita/HubSpot simulados: idempotencia, instanciación, completar espera, firma inválida.
- Prueba de integración end-to-end contra el bundle Bonita `:8080` (verificar que el caso llega a `fin_entregada`).
