# Fase 0 — Descubrimiento de IDs en HubSpot

> **Alcance:** inventario de IDs reales de HubSpot para la integración HubSpot↔Bonita (ver `HANDOFF-SCAFFOLD.md` §7). Solo lectura contra la API de HubSpot.
> **Fecha:** 2026-11-11 · **Fuente:** HubSpot CRM API v3 (`api.hubapi.com`).
> **Secreto:** el token de Private App NO está en este repo; se usó solo por variable de entorno en la sesión.

---

## 1. Pipeline de tickets y stages

Hay **1 pipeline** de tickets: **Mesa de preventa** · `pipelineId = 0`.

| # | Stage (label real) | `stageId` | ¿Cerrado? |
|---|---|---|---|
| 0 | Solicitud recibida | `1` | false |
| 1 | En validación | `2` | false |
| 2 | Asignado/En diseño | `3` | false |
| 3 | En espera información del lead | `1425810257` | false |
| 4 | Entregado a ventas | `1425810258` | false |
| 5 | Closed | `4` | true |

> **Nota técnica:** el stage se fija en la propiedad `hs_pipeline_stage` del ticket con el `stageId` (no con la etiqueta). El pipeline se fija en `hs_pipeline` con el `pipelineId`.

### ⚠️ Discrepancia a resolver (NO la decide el agente)

El `HANDOFF-SCAFFOLD.md` §1 asumía 5 estados (`en diseño`, `en validación`, `en espera de información del lead`, `entregado a ventas`, `caso cerrado`). El pipeline real (**Mesa de preventa**) tiene 6 stages y algunos nombres difieren (p. ej. `Solicitud recibida` no estaba en el handoff; `Asignado/En diseño` combina asignación y diseño). El mapa de estados Bonita→HubSpot debe reconciliarse contra estos `stageId` reales. Esto es diseño del proceso: pertenece al **flujo de preventa** (U1 / `docs/07-bonita/`), lo confirma el líder técnico. Aquí solo se documentan los IDs reales.

---

## 2. Owners (candidatos del reparto)

Se descubrieron **18 owners** (sin paginación pendiente). Los IDs sirven para `hubspot_owner_id`. **Qué owners entran en el reparto es una decisión de negocio** (hoy: Linda `89450376` y Viviana `89450377`, en `param_consultores`) (no todos los owners tienen por qué ser elegibles); esta lista es el universo disponible, no la rotación final.

| `hubspot_owner_id` | Nombre | Archivado |
|---|---|---|
| `103351240` | Rodrigo Gutiérrez Caro | False |
| `87325521` | Carlos Segura | False |
| `87693293` | Jesus Antonio Segura | False |
| `88098140` | Evelyn Agudelo | False |
| `88449388` | Trynion | False |
| `89450376` | Linda Katherine Lozano Rodríguez | False |
| `89450377` | Viviana Paola Velásquez Peña | False |
| `90145590` | Duvan David Vega Vanegas | False |
| `90704681` | Emy Rincón Pérez | False |
| `90848444` | Jonathan Segura | False |
| `92377372` | Karen Bernal | False |
| `92940683` | Luz Aide Murte Orjuela | False |
| `94346095` | Laura Camila Bustamante García | False |
| `94394067` | Natalia Segura | False |
| `96211525` | Danna Chujmanova | False |
| `96972849` | Karen Andrea Durán Barrera | False |
| `99507401` | John German Velásquez Torres | False |
| `99578291` | Santiago Romero Herrera | False |

> Los correos de cada owner están disponibles en la API (`GET /crm/v3/owners`) si se necesitan; se omiten aquí para no fijar datos personales en el repo.

> **Verificado en vivo 2026-11-11** contra `api.hubapi.com` (token de pruebas, luego rotado): pipeline y los 6 `stageId` coinciden exactamente con §1; `GET /crm/v3/owners` devuelve **18 owners**.
> ⚠️ **Reparto:** el owner `88449388` ("Trynion") es un **bot de HubSpot** (correo `...@aichatbot.na1.hubspot.com`) — **excluido** de los candidatos del reparto por carga. Definir también si se incluyen/excluyen owners inactivos (`archived=true`).

---

## 3. Propiedades del ticket

### 3.1 Propiedades estándar clave

| Propiedad | Tipo | Uso en la integración |
|---|---|---|
| `hs_pipeline` | enumeration/select | pipeline del ticket (`pipelineId`) |
| `hs_pipeline_stage` | enumeration/select | **stage del ticket** — lo escribe Bonita en cada transición |
| `hubspot_owner_id` | enumeration/select | **responsable** — lo escribe Bonita al asignar por carga ponderada por prioridad |
| `subject` | string/text | asunto del ticket |
| `content` | string/textarea | descripción del ticket |

### 3.2 Propiedades de negocio personalizadas (21)

Candidatas a entrar en el BDM / contrato de instanciación cuando llegue el flujo de preventa (U1). **No se modela el BDM aquí** (§8 del handoff).

| `name` | Etiqueta | Tipo |
|---|---|---|
| `alcance_preliminar` | Alcance preliminar | string/textarea |
| `aux_paso_por_validacion` | Marca de validación previa | bool/booleancheckbox |
| `comercial_creador` | Comercial creador | enumeration/select |
| `complejidad_estimada` | Complejidad estimada | enumeration/select |
| `entregable_esperado` | Entregable esperado | enumeration/checkbox |
| `fecha_de_vencimiento` | Fecha de vencimiento | datetime/date |
| `fecha_probable_siguiente_reunion_con_prospecto` | Fecha probable siguiente reunión con prospecto | date/date |
| `linea_de_negocio` | Línea de negocio | enumeration/checkbox |
| `link_repositorio_preventa` | Link repositorio preventa | string/text |
| `medpicc` | MEDPICC | string/text |
| `motivo_de_cierre` | Motivo de cierre | enumeration/select |
| `numero_de_iteraciones_retrabajo` | Número de iteraciones (Retrabajo) | number/number |
| `pais_del_cliente` | País del cliente | enumeration/select |
| `restricciones_conocidas` | Restricciones conocidas | string/textarea |
| `satisfaccion_del_comercial` | Satisfacción del comercial | enumeration/select |
| `sistemas_involucrados` | Sistemas involucrados | string/text |
| `sla_cumplido` | SLA cumplido | enumeration/checkbox |
| `sla_vencido` | SLA vencido | bool/booleancheckbox |
| `tipo_de_requerimiento` | Tipo de requerimiento | enumeration/checkbox |
| `tuvo_reproceso` | ¿Tuvo reproceso? | enumeration/radio |
| `volumenmagnitud` | Volumen/magnitud | string/textarea |

> El tenant tiene **247 propiedades** de ticket en total (estándar + personalizadas). Las opciones de cada propiedad `enumeration` (p. ej. `motivo_de_cierre`, `linea_de_negocio`) se pueden volcar en un anexo cuando se modele el BDM.

---

## 4. Datos de la API (referencia)

- **Base:** `https://api.hubapi.com`
- **Auth:** token de Private App → header `Authorization: Bearer <token>`. Scopes requeridos: `tickets`, `crm.objects.owners.read` (verificados: pipelines, owners y properties respondieron `200`).
- **Endpoints usados:** `GET /crm/v3/pipelines/tickets`, `GET /crm/v3/owners`, `GET /crm/v3/properties/tickets`.
- **Escritura de salida (Bonita→HubSpot):** `PATCH /crm/v3/objects/tickets/{id}` fijando `hs_pipeline_stage` y `hubspot_owner_id`.
- **Límites:** 100 req / 10 s · 250 000 / día.

---

## 5. Pendiente / no verificado

- **Mapa de stages definitivo:** depende del flujo de preventa + confirmación del líder (ver §1).
- **Candidatos del reparto:** qué owners son elegibles — decisión de negocio (hoy en `param_consultores`).
- **Opciones de las propiedades `enumeration`:** no volcadas aún (se harán al modelar el BDM en U1).
- **Process ID de Bonita:** no existe todavía (sale tras construir el proceso en U1).
- **Escritura `PATCH` a HubSpot:** documentada, **no ejecutada** (Fase 0 es solo lectura).


---

## 6. Verificación en vivo del 2026-11-12 (solo lectura)

Ejecutada contra `api.hubapi.com` con el token de Private App entregado por el usuario (guardado fuera del repositorio).
No se escribió nada en HubSpot. No se imprimió ni se guardó contenido de tickets o negocios, solo conteos y nombres de
propiedades.

| Comprobación | Resultado |
|---|---|
| `GET /crm/v3/objects/tickets` | 200 |
| `GET /crm/objects/2026-09/tickets` (ruta con versión por fecha) | 200 |
| `POST /crm/v3/objects/tickets/search` filtrando `hs_pipeline` = `0`, `hubspot_owner_id` = owner y `hs_pipeline_stage` en (`2`, `3`) | 200; owner `89450376` → 0 tickets; owner `89450377` → 1 ticket (en stage `2`) |
| Tickets del pipeline `0` en stage `1` («Solicitud recibida») | 200; 0 en ese momento |
| Tickets con negocio asociado (`associations=deals`, muestra de 5) | 5 de 5 |

La búsqueda de la segunda fila es la que mide la carga de cada consultora para la asignación; su resultado coincide con
lo que se dijo en la reunión de socialización («Viviana tiene uno, Linda no tiene ninguno»).

### 6.1 Propiedades del negocio donde se cargan los artefactos

La reunión las llama «definición de preventa». Nombres internos reales (objeto negocio, grupo `dealinformation`,
creadas por el usuario):

| `name` | Etiqueta | Tipo | Artefacto |
|---|---|---|---|
| `concepto_viabilidad` | Concepto viabilidad por Preventa | enumeration/select | viable o no viable |
| `estimacion_costos` | Estimación fábrica | string/text | enlace de la calculadora (estimación) |
| `url_ppta_preventa` | URL propuesta Preventa - Slide | string/text | enlace de la presentación |
| `link_repo_preventa` | Link repositorio Preventa | string/text | enlace del repositorio |

Otras propiedades del negocio relacionadas, que hoy no se usan: `preventa_asignado` (Preventa asignado,
enumeration/select), `meddpicc` (MEDDPICC, string/text), `link_repositorio_comercial`.

### 6.2 Sigue sin verificar

- La escritura `PATCH /crm/v3/objects/tickets/{id}` (cambia datos reales).
- Qué evento de HubSpot avisa del cambio de las cuatro propiedades del negocio, y si el plan contratado lo permite.
- Los scopes exactos que la Private App necesita para leer negocios desde el middleware (esta lectura respondió 200).
