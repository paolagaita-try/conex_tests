# preventa-middleware

Puente entre HubSpot y Bonita para la integración de preventa. **Sin dependencias externas** (Node 18+, módulos nativos).

## Qué hace

1. **Entrada** — `POST /webhooks/ticket-created`: al crearse un ticket en HubSpot (Workflow nativo → webhook), instancia el caso en Bonita (`POST /API/bpm/process/{id}/instantiation` con `{ticketId}`). **Idempotente** por `ticketId` (store en `data/store.json`).
2. **Espera** — `POST /webhooks/artifacts-loaded`: cuando cambian las propiedades del ticket, si los **4 campos de artefactos** (`concepto_viabilidad`, `estimacion_costos`, `url_ppta_preventa`, `link_repo_preventa`) tienen valor → completa la tarea `18_esperarArtefactos` con `resultado=entregado`; si el ticket está cerrado sin entregar → `cerrado`. Bonita entonces pasa el ticket a «Entregado a ventas».
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

## Configurar en HubSpot (Sales Hub Pro)

Dos **Workflows nativos** con acción *webhook*:
- Trigger «ticket creado» en el pipeline «Mesa de preventa» → `POST https://<host>/webhooks/ticket-created`.
- Trigger «cambió alguna de las 4 propiedades de artefactos» (o «ticket cerrado») → `POST https://<host>/webhooks/artifacts-loaded`.

El token de Private App y el app-secret van por entorno, nunca en el repo.

## Seguridad

- Todo secreto por variable de entorno (`.env` en `.gitignore`).
- Firma de webhook validada con `HUBSPOT_APP_SECRET`.
- Pruebas de escritura solo contra tickets de prueba desechables; nunca tickets de producción reales sin autorización.

## Pendiente (próxima sesión)

- `test/*.test.js` (node --test) con Bonita/HubSpot simulados: idempotencia, instanciación, completar espera, firma inválida.
- Prueba de integración end-to-end contra el bundle Bonita `:8080` (verificar que el caso llega a `fin_entregada`).
