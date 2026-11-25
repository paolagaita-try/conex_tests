# Prueba real v2 (1.2) contra HubSpot — 2026-11-25

Prueba de punta a punta de `GestionPreventa` 1.2 (main `d51306b`) operando **solo por Bonita**, contra el HubSpot real,
sobre el ticket de pruebas **51223233059 «PRUEBAS»** (pipeline 0) y su Negocio **68036155510 «Lead pruebas integración
ofelia Husbpot»**. Al final se restauró todo y la foto DESPUÉS coincide con la ANTES.

## Montaje

- Bundle nuevo desde main: `npm run build:all` (frontend) y `mvn -B clean install -Pbundle` (BUILD SUCCESS); sin
  regenerar (no hizo falta re-aplicar `parche-manifest-preventa.py`).
- Bonita Community 2026.2 local (H2 limpio en cada corrida), token en la variable de entorno de la JVM. El parámetro
  `param_hubspotUrlBase` de Local apunta a `http://localhost:8099/hubspot`; ahí corrió un **proxy con guarda** hacia
  `https://api.hubapi.com`: GET libres y escrituras **solo** sobre el ticket y el Negocio de prueba (PATCH de esos dos
  ids, notas asociadas solo a ellos, carga de archivo). Peticiones bloqueadas por la guarda: **0**.
- Entrada como en producción: imagen `preventa-middleware:v2` (`docker build middleware/`) en Docker contra ese Bonita y
  el HubSpot real (a través del mismo proxy); `POST /webhooks/ticket-created {"objectId":"51223233059"}` → `{"caseId":1,"ok":true}`.
- Navegador: Playwright (Chromium) sobre la Bonita User Application → Tareas → tarea → formulario Svelte → Enviar.
  RAM libre antes de arrancar: 2,97 GB.

## Resultado: dos defectos reales y una corrida completa en verde

| Corrida | Consultora (reparto) | Qué pasó |
|---|---|---|
| 1 | linda.lozano (89450376) | Validar → Viable con concepto en texto libre. Nota y stage 3 OK; `PATCH deals concepto_viabilidad` → **HTTP 400**: la tarea de servicio «Pasar el ticket a «Asignado/En diseño»» quedó `failed`. |
| 2 | viviana.velasquez (89450377) | Validar con concepto **«Aprobado (Viable)»** (valor exacto del enumerado) → OK. Diseñar con valoración en texto → `PATCH deals` → **HTTP 400 `INVALID_URL` en `valoracion_operaciones`**: la tarea «Diseñar la propuesta» quedó `failed` (sin nota ni archivo). |
| 3 | linda.lozano (89450376) | Validar con «Aprobado (Viable)» y Diseñar con valoración **en forma de URL** → todo en verde: stages 2 → 3 → 1425810258, 4 campos del Negocio, nota de propuesta, archivo y nota de adjuntos. |

### Defecto 1 — `concepto_viabilidad` es un enumerado en HubSpot

`GET /crm/v3/properties/deals/concepto_viabilidad` → `enumeration/select` con opciones
`Aprobado (Viable)`, `Aprobado con Condiciones`, `No Viable (Rechazado)`, `Requiere más información`. El formulario
`frm_10_validarSolicitud` lo pide como texto libre (`textarea`), y cualquier otro texto da 400 y deja el caso en fallo.

### Defecto 2 — `valoracion_operaciones` exige una URL en HubSpot

La propiedad es `string/text`, pero HubSpot la valida como URL («La URL debe empezar por http:// o https://»,
`INVALID_URL`); el valor original del Negocio es un enlace a una hoja de Google. El formulario `frm_20_disenarPropuesta`
la presenta como texto libre («Esfuerzo, equipo y riesgos operativos estimados»).

Ambos cierran el punto 7 de «Pendiente» de `evidencia-v2-proceso.md` (tipo real de esas propiedades). Corregirlos
toca `docs/07-bonita/` (contratos y matriz de formularios), que es fuente aprobada: queda a decisión de la usuaria.

## Escrituras en HubSpot (todas de los conectores de Bonita, vistas por el proxy)

| Corrida | Petición | Estado | Id creado |
|---|---|---|---|
| 1 | `PATCH tickets/51223233059 {stage 2, owner 89450376}` | 200 | |
| 1 | `POST notes` «Validación de preventa (Bonita): Viable … PRUEBA REAL v2 – validación» | 201 | nota 122069912466 |
| 1 | `PATCH tickets {stage 3}` | 200 | |
| 1 | `PATCH deals/68036155510 {concepto_viabilidad: "PRUEBA REAL v2 – concepto de viabilidad"}` | **400** | |
| 2 | `PATCH tickets {stage 2, owner 89450377}` | 200 | |
| 2 | `POST notes` (validación) | 201 | nota 122060685988 |
| 2 | `PATCH tickets {stage 3}` · `PATCH deals {concepto_viabilidad: "Aprobado (Viable)"}` | 200 · 200 | |
| 2 | `PATCH deals {4 campos, valoracion_operaciones en texto}` | **400** | |
| 3 | `PATCH tickets {stage 2, owner 89450376}` | 200 | |
| 3 | `POST notes` (validación) | 201 | nota 122089789491 |
| 3 | `PATCH tickets {stage 3}` · `PATCH deals {concepto_viabilidad}` | 200 · 200 | |
| 3 | `PATCH deals {concepto, valoracion (URL), url_ppta, link_repo}` | 200 | |
| 3 | `POST notes` «Propuesta de preventa (Bonita) … PRUEBA REAL v2 – propuesta» | 201 | nota 122099007131 |
| 3 | `POST files/v3/files` (`PRUEBA-v2-adjunto.pdf`, 560 bytes, privado) | 201 | archivo 228643295290 |
| 3 | `POST notes` «Adjuntos de preventa: 1 archivo(s).» con `hs_attachment_ids` | 201 | nota 122095672344 |
| 3 | `PATCH tickets {stage 1425810258}` | 200 | |

Verificado por GET tras la corrida 3: las 5 notas asociadas al ticket **y** al Negocio; el archivo existe.

## Fotos (GET) y comparación

| Campo | ANTES | DESPUÉS de la prueba | RESTAURADO |
|---|---|---|---|
| ticket `hs_pipeline` | 0 | 0 | 0 |
| ticket `hs_pipeline_stage` | 2 | 1425810258 | 2 |
| ticket `hubspot_owner_id` | 89450377 | 89450376 | 89450377 |
| ticket `hs_ticket_priority` | HIGH | HIGH | HIGH |
| ticket `subject` | PRUEBAS | PRUEBAS | PRUEBAS |
| Negocio `concepto_viabilidad` | Aprobado (Viable) | Aprobado (Viable) | Aprobado (Viable) |
| Negocio `valoracion_operaciones` | enlace a la hoja de Google (`…/1eQ1vf00…/edit?gid=1179127349`) | https://example.com/prueba-real-v2/valoracion | el mismo enlace de ANTES |
| Negocio `url_ppta_preventa` | (vacío) | https://example.com/prueba-real-v2/ppta | (vacío) |
| Negocio `link_repo_preventa` | (vacío) | https://example.com/prueba-real-v2/repo | (vacío) |
| Negocio `dealstage` | 1289529608 | 1289529608 | 1289529608 |
| Negocio asociado al ticket | sí | sí | sí |
| notas del ticket | ninguna | 5 (las de la prueba) | ninguna |
| notas del Negocio | ninguna | 5 (las mismas) | ninguna |
| archivo 228643295290 | — | existe | borrado (GET 404) |

Comparación automática de la foto ANTES y la RESTAURADA: **iguales** (sin diferencias).

Restauración (autorizada por la usuaria): `PATCH` del ticket (stage, owner, prioridad) y del Negocio (4 campos) con
los valores de ANTES; `DELETE` de las notas 122069912466, 122060685988, 122089789491, 122099007131, 122095672344 y
del archivo 228643295290 (todas 204). Nada más se borró ni se tocó.

Lo que **no** vuelve atrás: `hs_lastmodifieddate` y el historial de propiedades del ticket y del Negocio en HubSpot
registran los cambios de la prueba y su restauración.

## Capturas (`prueba-real/`)

- Corrida 3 (completa): `validar-1-bandeja`, `validar-2-formulario-precargado`, `validar-3-formulario-diligenciado`,
  `validar-4-confirmacion`, `disenar-1-bandeja`, `disenar-2-formulario-precargado`, `disenar-3-formulario-diligenciado`,
  `disenar-4-confirmacion` («Formulario enviado» y bandeja vacía).
- Corridas 1 y 2 (las de los defectos): mismos nombres con prefijo `corrida1-` y `corrida2-`.
- Precarga comprobada: el formulario muestra el ticket real (`PRUEBAS`, #51223233059, prioridad Alta, stage 2, owner
  asignado) y el Negocio real (nombre, importe, `concepto_viabilidad`, `valoracion_operaciones`, `dealstage`).
  La tarea ya llegó asignada a la consultora elegida (actor filter): no hizo falta «Tomar».

## Observaciones

- El reparto eligió consultoras distintas entre corridas (linda, viviana, linda) aunque cada corrida tenía H2 limpio:
  la causa (p. ej. que la carga ponderada se lea de los tickets en HubSpot) queda `[no verificado]`.
- Reintentar no fue posible por la interfaz en Community: cada defecto dejó el caso en `failed` y hubo que arrancar
  un runtime nuevo. Coincide con el riesgo 6 de `evidencia-v2-proceso.md` (reintentos pueden duplicar notas).
