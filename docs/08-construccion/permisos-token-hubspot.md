# Permisos (scopes) del token de la Private App de HubSpot — para Laura

Consultado el 2026-11-24 en la documentación oficial. Fuente general de la lista de scopes:
<https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/scopes> (en adelante, **[S]**).
Todos los de la tabla figuran allí como «disponibles en todas las cuentas».

## Scopes que hay que marcar en la Private App

| # | Scope | Para qué lo usa el proyecto | Fuente |
|---|---|---|---|
| 1 | `crm.objects.tickets.read` | leer el ticket (asunto, stage, owner, prioridad), buscar tickets para el reparto | [S] |
| 2 | `crm.objects.tickets.write` | fijar `hs_pipeline_stage` y `hubspot_owner_id` del ticket | [S] |
| 3 | `crm.objects.deals.read` | leer el Negocio para precargar los formularios | [S] |
| 4 | `crm.objects.deals.write` | escribir propiedades del Negocio (`hubspot-negocio-actualizar`) | [S]; guía de deals <https://developers.hubspot.com/docs/api-reference/crm-deals-v3/guide> |
| 5 | `crm.objects.companies.read` | leer la empresa asociada | [S] |
| 6 | `crm.objects.contacts.read` | leer los contactos asociados | [S] |
| 7 | `crm.objects.owners.read` | leer owners (nombre/correo de la consultora) | [S] (ya verificado en vivo en Fase 0) |
| 8 | `crm.schemas.deals.read` | listar las propiedades del Negocio para los formularios (`GET /crm/v3/properties/deals`) | [S] |
| 9 | `files` **o** `files.write` | subir adjuntos (`POST /files/v3/files`) | [S]; la referencia del endpoint acepta cualquiera de `files`, `files.write`, `files.ui_hidden.write`: <https://developers.hubspot.com/docs/api-reference/legacy/files/files/upload-file>. Recomendado `files.write` (granular; `files` es legacy) |
| 10 | Notas: **`crm.objects.contacts.write`** y, si la pantalla lo ofrece, `crm.objects.notes.write` | crear notas asociadas a ticket y Negocio | ver «Notas» abajo — **[no verificado]** |

Alternativa equivalente a 1 + 2: el scope legacy `tickets` («Retrieves and manages ticket data») [S]. Es el que tiene hoy
el token (Fase 0); HubSpot recomienda migrar a los granulares. Cualquiera de las dos opciones sirve.

## Qué usa cada pieza en ejecución

- API REST `preventaContexto` (precarga de formularios, solo lectura): `tickets` (o 1), `crm.objects.deals.read`,
  `crm.objects.companies.read`, `crm.objects.contacts.read`, `crm.objects.owners.read`.
- Conectores de escritura: 2 (o `tickets`), 4, 9 y el scope de notas (10).
- `crm.schemas.deals.read` (y el esquema de tickets, ver abajo) solo hace falta para leer el esquema de propiedades
  (listar los campos de los formularios), no en la ejecución del caso.

## Notas

- La lista de scopes [S] **no tiene ningún scope con «notes»**.
- La referencia 2026-09 de *Create note* incluye `crm.objects.notes.write` entre los scopes de su bloque de seguridad
  (<https://developers.hubspot.com/docs/api-reference/latest/crm/activities/notes/create-note>), sin decir si basta solo.
- La referencia legacy (`POST /crm/v3/objects/notes`) deja vacía la sección de scopes
  (<https://developers.hubspot.com/docs/api-reference/legacy/crm/activities/notes/create-note>); varias fuentes y
  hilos de la comunidad indican `crm.objects.contacts.write` como el scope histórico de las actividades (notas).
- **[no verificado]** cuál exige exactamente HubSpot hoy para una Private App. Recomendación: marcar
  `crm.objects.contacts.write` y, si aparece en la pantalla de la Private App, `crm.objects.notes.write`; después
  crear una nota de prueba sobre un ticket de prueba desechable y, si da `403 MISSING_SCOPES`, el cuerpo del error dice
  el scope que falta.
- Asociar la nota al ticket y al Negocio en el mismo create: **[no verificado]** si además exige escritura sobre el
  objeto asociado; con 2 y 4 ya marcados queda cubierto.

## Lecturas de asociaciones

No existe un scope propio de asociaciones en [S]. Leer `GET /crm/v4/objects/tickets/{id}/associations/{objeto}` o
`?associations=deals,companies,contacts` usa los scopes de lectura de los objetos implicados (1, 3, 5, 6).
**[no verificado]** en la referencia de asociaciones v4 (su sección de scopes no se pudo leer); el token actual ya leyó
asociaciones v4 en vivo con `tickets`.

## Esquema de propiedades de tickets

**No existe `crm.schemas.tickets.read`** en [S] (sí existen los de deals, companies, contacts…); si la pantalla de la
Private App lo ofrece, marcarlo, pero no aparece en la lista oficial consultada. `GET /crm/v3/properties/tickets`
ya respondió 200 en Fase 0 con el scope `tickets` (`fase-0-descubrimiento-hubspot.md`). **[no verificado]** que siga
funcionando si se sustituye `tickets` por los granulares 1 + 2; si falla, mantener `tickets`.

## Lo que NO va en este token

- El webhook `ticket.creation` que dispara el caso es una **suscripción de una app de desarrollador** (la usa el
  middleware de entrada), no un scope de la Private App. La app de webhooks pide sus propios scopes (lectura de tickets)
  en su configuración. **[no verificado]** el detalle actual de suscripciones de webhooks para Private Apps.
- Ningún scope de borrado (`files.delete`, etc.): el proyecto nunca borra en HubSpot.

## Mensaje sugerido para Laura

Agregar a la Private App: `crm.objects.tickets.read`, `crm.objects.tickets.write` (o mantener `tickets`),
`crm.objects.deals.read`, `crm.objects.deals.write`, `crm.objects.companies.read`, `crm.objects.contacts.read`,
`crm.objects.owners.read`, `crm.schemas.deals.read`, `files.write`, `crm.objects.contacts.write` y, si aparece,
`crm.objects.notes.write`. Al guardar, HubSpot puede rotar el token: el nuevo va solo a la variable de entorno
`HUBSPOT_PRIVATE_APP_TOKEN`, nunca por chat ni al repo.
