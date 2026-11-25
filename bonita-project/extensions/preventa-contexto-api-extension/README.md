# preventa-contexto-api-extension

REST API extension de Bonita (Groovy) que lee de HubSpot, **del lado servidor**, todo lo que un formulario de
preventa necesita precargar: el ticket, su primer Negocio, la empresa, los contactos y el owner. El navegador nunca
ve el token.

## Endpoint

`GET /bonita/API/extension/preventa/contexto?ticketId=<id del ticket de HubSpot>`

Permiso: `preventa_contexto_lectura` (page.properties).

| Código | Cuándo | Cuerpo |
|---|---|---|
| 200 | ticket leído | `{ticket, deal, company, contacts, owner}` |
| 400 | falta `ticketId`, viene repetido o no es `[A-Za-z0-9-]{1,40}`, o llegan otros parámetros | `{motivo: "ticketId-requerido"}` |
| 404 | HubSpot no tiene ese ticket | `{motivo: "ticket-no-encontrado"}` |
| 500 | falta `HUBSPOT_PRIVATE_APP_TOKEN` en el servidor (o error inesperado) | `{motivo: "configuracion-incompleta"}` / `{motivo: "error-de-lectura"}` |
| 502 | HubSpot responde con otro código no 2xx, o no responde | `{motivo: "hubspot-no-disponible", estadoHubspot?}`; nunca el cuerpo de HubSpot ni el token |

## Respuesta 200

```json
{
  "ticket":   {"id": "...", "properties": {...}},
  "deal":     {"id": "...", "properties": {...}} | null,
  "company":  {"id": "...", "properties": {...}} | null,
  "contacts": [{"id": "...", "properties": {...}}],
  "owner":    {"id", "email", "firstName", "lastName", "userId"} | null
}
```

Cargas parciales: sin Negocio → `deal: null`; sin empresa → `company: null`; sin contactos → `[]`; owner vacío,
inexistente o bot (88449388, Trynion: no es consultor) → `owner: null`. La empresa y los contactos salen del Negocio si
lo hay; si no, de las asociaciones directas del ticket. Con varias asociaciones se toma la primaria (etiqueta no
`unlabeled`) y, si no, la primera.

## Configuración

- `HUBSPOT_PRIVATE_APP_TOKEN` (variable de entorno del servidor Bonita): obligatoria. Nunca en el repo ni en la respuesta.
- Raíz de HubSpot: `hubspot.urlBase` en `configuration.properties` (por defecto `https://api.hubapi.com`); la variable
  de entorno `HUBSPOT_BASE_URL`, si existe, gana. Para el journey se apunta al mock del arnés, que sirve bajo
  `/hubspot` (p. ej. `http://localhost:<puerto>/hubspot`).
- `hubspot.timeoutMs` (10000), `owners.excluidos` (`88449388`), `contactos.maximo` (20).

## Versión de la API de HubSpot

Se usa **`/crm/v3/...`** (objetos con `?associations=` y `/crm/v3/owners/{id}`), la misma convención que los conectores
del proyecto (`/crm/v3` y `/crm/v4` para asociaciones), que ya funcionaron en vivo. El 2026-11-24 se comprobó con GETs
de solo lectura que `/crm/v3/objects/tickets`, `/crm/v3/owners` y la ruta por fecha `/crm/objects/2026-09/tickets`
responden 200, sin cabeceras `Deprecation` ni `Sunset` en v3. La ruta base es configurable, pero las rutas `/crm/v3/...`
están en el código (`ContextoPreventa`): migrar a la versión por fecha es cambiar esas rutas. **[no verificado]**: el
calendario oficial de HubSpot de soporte/retirada de v3 frente a la versión por fecha (no se consultó la documentación
oficial en esta sesión).

## Propiedades pedidas (`Propiedades.groovy`) y por qué

Sin `properties=` HubSpot devuelve solo unas pocas por defecto; con todas (247 en tickets, 429 en deals, 251 en
companies, 439 en contacts en este portal) la respuesta se llena de propiedades internas. Se eligieron, a partir del
esquema real (`GET /crm/v3/properties/{objeto}`, 2026-11-24):

- **Ticket**: estándar (asunto, contenido, pipeline y etapa, prioridad, categoría, owner, origen, fechas) + todas las
  personalizadas de preventa (alcance, complejidad, entregable, línea de negocio, MEDPICC, SLA, tipo de requerimiento,
  etc.), salvo `aux_paso_por_validacion` (auxiliar del flujo).
- **Deal**: estándar (nombre, importe y moneda, etapa, pipeline, tipo, descripción, fechas, owner, prioridad, siguiente
  paso) + personalizadas de preventa (viabilidad, estimación de costos, dolor principal, documentación, URLs de
  propuesta/cotizador/repositorio, preventa asignado, sector, soluciones ofrecidas...). Fuera las `migrated_*`.
- **Company**: identificación, sector, contacto, ubicación, tamaño, ingresos, ciclo de vida, owner + las 4
  personalizadas de madurez/objetivo en automatización.
- **Contact**: nombre, correo, teléfonos, cargo, empresa, ubicación, ciclo de vida, estado del lead, owner + área,
  temperatura del lead y reto operativo. Fuera `migrated_*`, `zoom_*`, opt-ins de marketing y cumpleaños (dato
  personal sin uso en preventa).

## Scopes de HubSpot

`tickets`, `crm.objects.deals.read`, `crm.objects.companies.read`, `crm.objects.contacts.read`,
`crm.objects.owners.read`. (Los `crm.schemas.*.read` solo hicieron falta para leer el esquema al elegir propiedades.)

## Despliegue (pendiente)

El zip debe viajar en el application archive y el permiso fusionarse en el perfil User, como `consultas-api-extension`
(fuera del alcance de este módulo; ver informe).
