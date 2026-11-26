# Conectores de escritura hacia HubSpot (plan v2, fase 4)

Módulo: `bonita-project/extensions/preventa-conectores/` (Groovy en `src/main/groovy/co/trycore/preventa/conectores/`,
`.def`/`.impl` en `src/main/resources-filtered/`). Mismo patrón que `hubspot-ticket-leer`, `hubspot-ticket-actualizar` y
`hubspot-consultores-menor-carga`:

- El token de la Private App se lee **solo** de la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN` (`Http.token()`) y
  viaja como `Authorization: Bearer …`. Nunca es entrada del conector, ni va al repo, ni a argumentos de línea de comandos.
- Un status no 2xx lanza `HubspotHttpException` (status + método + URL + cuerpo truncado a 500 caracteres, con el token
  enmascarado si el servidor lo reflejara); el conector la envuelve en `ConnectorException`. La URL no lleva el token.
- Las entradas obligatorias se comprueban en `validateInputParameters` (`ConnectorValidationException`).
- `Http` ganó `postMultipart` (Files API) y una fuente de token sustituible (`Http.fuenteToken`) solo para las pruebas.

## Versión de la API

**Convención elegida: rutas semánticas `v3` (`/crm/v3/objects/...`, `/files/v3/files`), con la ruta base configurable.**

- Coherente con los conectores existentes (`/crm/v3/...`), que ya funcionaron en vivo (lectura/PATCH de tickets,
  search, asociaciones v4).
- HubSpot publica además versiones por fecha (`/crm/objects/2026-09/...`; la ruta cambia solo en el prefijo y muchos
  contratos v3 son idénticos). Fuente: guía de migración
  <https://developers.hubspot.com/docs/api-reference/legacy/migration-guide> — «In September 2027, all legacy APIs using
  semantic versions (e.g., v4, v3, v2, and v1) will no longer be supported». Es decir: **v3 sigue soportado hasta
  septiembre de 2027** y hay que migrar antes.
- Notas: la referencia 2026-09 documenta `POST /crm/objects/2026-09/notes`
  (<https://developers.hubspot.com/docs/api-reference/latest/crm/activities/notes/create-note>) y la legacy
  `POST /crm/v3/objects/notes`.
- Archivos: la guía 2026-03 usa `POST /files/2026-03/files`
  (<https://developers.hubspot.com/docs/api-reference/2026-03/files/guide>); **[no verificado]** que exista
  `/files/2026-09/files`.
- Comprobado en vivo (otro agente, 2026-11-24, **solo GET**): `/crm/v3/objects/tickets` y
  `/crm/objects/2026-09/tickets` respondieron 200, sin cabeceras `Deprecation` ni `Sunset`. La API REST
  `preventaContexto` también usa v3. No se probó en vivo ninguna escritura (PATCH/POST) en ninguna de las dos rutas.
- Para migrar sin tocar código: entradas opcionales `rutaObjetos` (defecto `/crm/v3/objects`, p. ej.
  `/crm/objects/2026-09`) y `rutaArchivos` (defecto `/files/v3/files`). Una prueba (`HubspotNegocioActualizarSpec`)
  ya ejercita `rutaObjetos=/crm/objects/2026-09`. **[no verificado]** en vivo que el cuerpo 2026-09 sea idéntico para
  deals/notes/files.

## `hubspot-ticket-leer` (`HubspotTicketLeer`, existente) · salida nueva `dealId`

| | |
|---|---|
| Entradas | `urlBase`, `rutaTickets`, `ticketId` (oblig.); `rutaAsociaciones` (opc., por defecto `/crm/v4/objects/tickets`) |
| Salidas | `asunto` (sin cambios), `dealId` (`String`: id del **primer** Negocio asociado; `""` si no hay ninguno, sin fallar) |
| Endpoints | `GET {urlBase}{rutaTickets}/{ticketId}?properties=subject`, luego `GET {urlBase}{rutaAsociaciones}/{ticketId}/associations/deals` (API de asociaciones v4, la que ya usa el middleware) |
| Respuesta usada | `results[].toObjectId` del primer elemento (un id numérico sale como texto) |
| Fuente | <https://developers.hubspot.com/docs/api-reference/crm-associations-v4/guide> |
| Errores | HTTP no 2xx en cualquiera de las dos lecturas → `ConnectorException` «No se pudo leer el ticket en HubSpot: …» (sin el token) |

La definición sigue en `1.0.0`: la entrada nueva es opcional y la salida nueva no rompe el `.proc` que ya la referencia.
«Primer» Negocio = el primero que devuelve HubSpot; el orden no está documentado como estable **[no verificado]**.

## `hubspot-negocio-actualizar` (`HubspotNegocioActualizar`)

| | |
|---|---|
| Entradas | `urlBase` (oblig.), `rutaObjetos` (opc., `/crm/v3/objects`), `dealId` (oblig.), `propiedadesJson` (oblig.: objeto JSON no vacío, o un `Map`) |
| Salida | `ok` (`Boolean`, `true` si 2xx; un error lanza excepción, no devuelve `false`) |
| Endpoint | `PATCH {urlBase}{rutaObjetos}/deals/{dealId}` |
| Payload | `{"properties": { ...propiedadesJson... }}` |
| Fuente | <https://developers.hubspot.com/docs/api-reference/crm-deals-v3/guide> |
| Errores | entrada vacía, JSON inválido, no-objeto u objeto vacío → `ConnectorValidationException`; HTTP no 2xx → `ConnectorException` «HTTP {status} …» |

## `hubspot-nota-crear` (`HubspotNotaCrear`)

| | |
|---|---|
| Entradas | `urlBase` (oblig.), `rutaObjetos` (opc.), `cuerpo` (oblig., texto/HTML, ≤ 65 536 caracteres), `ticketId` (oblig.), `dealId` (opc.), `adjuntos` (opc., ids de archivo separados por `;`) |
| Salida | `noteId` (`String`) |
| Endpoint | `POST {urlBase}{rutaObjetos}/notes` |
| Payload | `{"properties":{"hs_note_body":…, "hs_timestamp":"<ISO-8601 UTC>", ["hs_attachment_ids":"F-1;F-2"]}, "associations":[{"to":{"id":ticketId},"types":[{"associationCategory":"HUBSPOT_DEFINED","associationTypeId":228}]}, {"to":{"id":dealId},"types":[{…,"associationTypeId":214}]}]}` |
| Fuentes | Notas: <https://developers.hubspot.com/docs/api-reference/crm-notes-v3/guide> (`hs_timestamp` obligatorio; `hs_attachment_ids` con `;`; asociaciones en el create). Ids de asociación: <https://developers.hubspot.com/docs/api-reference/crm-associations-v4/guide> (**note→ticket = 228, note→deal = 214**) |
| Errores | `urlBase`/`cuerpo`/`ticketId` vacíos o cuerpo > 65 536 → validación; HTTP no 2xx o respuesta sin `id` → `ConnectorException` |
| [no verificado] | HubSpot muestra `to.id` numérico; aquí se envía como texto (los ids reales son numéricos en texto). |

## `hubspot-archivo-subir` (`HubspotArchivoSubir`)

| | |
|---|---|
| Entradas | `urlBase` (oblig.), `rutaArchivos` (opc., `/files/v3/files`), `rutaObjetos` (opc.), `documentos` (oblig., `java.util.List` no vacía), `dealId` (oblig.), `ticketId` (oblig.), `carpeta` (opc., `/preventa`), `cuerpoNota` (opc.; por defecto «Adjuntos de preventa: N archivo(s).») |
| Elementos de `documentos` | `Map` `{nombre, mime, contenido}` (contenido `byte[]` o Base64); `org.bonitasoft.engine.bpm.document.Document` del caso (contenido vía `ProcessAPI.getDocumentContent`); o cualquier objeto con `getFileName()`/`getContent()` y `getContentType()`/`getMimeType()` (p. ej. `FileInputValue` de un contrato) |
| Salidas | `fileIds` (`String`, ids separados por `;`, listo para `hs_attachment_ids`), `noteId` (`String`) |
| Paso 1 | por documento, `POST {urlBase}{rutaArchivos}` `multipart/form-data` con `file` (binario, filename y Content-Type), `fileName`, `folderPath` y `options` = `{"access":"PRIVATE"}`; HubSpot responde 201 con `id` |
| Paso 2 | crea la nota como `hubspot-nota-crear` con `hs_attachment_ids` = `fileIds`, asociada a ticket (228) y Negocio (214) |
| Fuentes | <https://developers.hubspot.com/docs/api-reference/files-files-v3/guide>, <https://developers.hubspot.com/docs/api-reference/legacy/files/files/upload-file> (campos multipart, 201, `id`) |
| Errores | entradas vacías / `documentos` no lista o vacía → validación; documento sin contenido, HTTP no 2xx (subida o nota) o respuesta sin `id` → `ConnectorException`. Si falla una subida no se crea la nota (los archivos ya subidos quedan en el File Manager, sin borrar). |
| [no verificado] | Cómo entrega Bonita 2026.2 una lista de documentos del caso a una entrada `java.util.List` de un conector (no se consultó `bonita-doc-index`); por eso se aceptan las tres formas. |

## Pruebas (Spock, sin red real)

`src/test/groovy/co/trycore/preventa/conectores/`: `ServidorSimulado` (servidor `com.sun.net.httpserver` en un puerto
libre, guarda método, ruta, cabeceras y cuerpo) y una Spec por conector. El token se inyecta con
`Http.fuenteToken = { 'token-de-prueba' }` y se comprueba `Authorization: Bearer token-de-prueba`.

| Spec | Casos |
|---|---|
| `HubspotTicketLeerSpec` (7) | con Negocio (asunto + primer `dealId`, dos GET con Bearer); id numérico como texto; sin Negocio → `""`; ruta de asociaciones configurable; HTTP 404 en el ticket y 500 en asociaciones |
| `HubspotNegocioActualizarSpec` (13) | PATCH, ruta, Bearer, cuerpo JSON; ruta 2026-09 configurable; HTTP 400/404/500 con cuerpo truncado y sin token; 6 validaciones |
| `HubspotNotaCrearSpec` (10) | POST, cuerpo, `hs_timestamp` ISO, adjuntos normalizados, asociaciones 228/214; sin Negocio ni adjuntos; HTTP 403/500; 4 validaciones |
| `HubspotArchivoSubirSpec` (12) | multipart (file con filename y mime, fileName, folderPath, options PRIVATE) para Map y objeto tipo `FileInputValue`; Base64; nota con adjuntos y asociaciones; HTTP 413 en la subida (no crea nota); HTTP 500 en la nota; documento vacío; 6 validaciones |

Comando: `mvn -B -f bonita-project/extensions/preventa-conectores/pom.xml clean install` → 54 pruebas del módulo, 0 fallos (`Tests run: 54, Failures: 0, Errors: 0, Skipped: 0`).

## HubSpot simulado (journey)

`mock.json` (raíz del repo) lo sirve `tools/arnes/herramientas/mock_http.py`; el arnés lo levanta solo en el puerto
8099 (`tools/arnes.sh`). A mano:

```bash
python3 tools/arnes/herramientas/mock_http.py --puerto 8099 --rutas mock.json
# urlBase de los conectores en Local: http://127.0.0.1:8099/hubspot
```

Formato: clave `«MÉTODO /ruta»` exacta (sin comodines; la query string se ignora), valor `{status, json}`. Soporta
GET/POST/PUT/PATCH/DELETE; no lee el cuerpo, así que el multipart se acepta tal cual (no hizo falta cambiar el mock).
Límites: una respuesta fija por ruta (todas las subidas devuelven `F-001`, todas las notas `N-001`) y no valida payloads
(eso lo hacen las Spec).

| Endpoint simulado (prefijo `/hubspot`) | Datos |
|---|---|
| `GET /crm/v3/objects/tickets/T-001`, `T-002` | asunto, pipeline `0`, stage `2` (En validación), owner `89450376`, prioridad, y `associations` (deals/companies/contacts) para `?associations=deals,companies,contacts` |
| `PATCH /crm/v3/objects/tickets/T-001`, `T-002`, `POST /crm/v3/objects/tickets/search` | (ya existían) |
| `GET /crm/v4/objects/tickets/{T-001,T-002}/associations/{deals,companies,contacts}` | `toObjectId` D-00x / C-00x / P-00x con typeId 28 / 339 / 16 |
| `GET` y `PATCH /crm/v3/objects/deals/D-001`, `D-002` | Negocio de ejemplo (`dealname`, `amount`, `dealstage`, owner `89450377`, `concepto_viabilidad`) y `associations` companies/contacts en forma v3 (para `?associations=companies,contacts` de `preventaContexto`) |
| `GET /crm/v3/objects/companies/C-001`, `C-002`; `GET /crm/v3/objects/contacts/P-001`, `P-002` | empresa y contacto ficticios (dominios `example.com`) |
| `POST /crm/v3/objects/notes` | 201 `{"id":"N-001"}` |
| `POST /files/v3/files` | 201 `{"id":"F-001", "access":"PRIVATE"}` |
| `GET /crm/v3/owners/89450376`, `89450377` | Linda y Viviana: `id`, `email` (ficticio), `firstName`, `lastName`, `userId`; el bot `88449388` no aparece |
| `GET /crm/v3/properties/deals`, `/tickets` | unas pocas propiedades; `hs_pipeline_stage` con los 6 stageId reales de `fase-0-descubrimiento-hubspot.md` |

`concepto_viabilidad` existe en el Negocio (verificado por GET al esquema el 2026-11-25): enumeración de cuatro
opciones, valor interno = etiqueta (`docs/07-bonita/bdm.md`); qué opción vale con cada resultado lo fija el contrato
(versión 1.4). `dealstage`/`pipeline` del Negocio son
valores por defecto de HubSpot, de ejemplo.
