# Evidencia — Proceso v2 «Bonita-first» (agente A, 2026-11-24)

Hub desconectado: trabajo en modo local, sin claims de `slice-ops.sh`. Sin escrituras en HubSpot real ni peticiones de red.

## Qué se hizo

- **Fuente** (`docs/07-bonita/`): `bpmn.md` (pool `GestionPreventa` 1.0 → **1.1**; carril Consultoras; tareas
  `10_validarSolicitud`, `11_pasarADiseno`, `12_pasarAEnEspera`, `13_registrarNoViable`, `20_disenarPropuesta`,
  `21_subirAdjuntos`; compuertas `gwXor_1` y `gwXor_2`; se retira `18_esperarArtefactos` y `resultadoPreventa`),
  `bdm.md` (Preventa ampliado: `dealId`, `resultadoValidacion`, `conceptoViabilidad`, `notaValidacion`, `supuestos`,
  `valoracionOperaciones`, `urlPptaPreventa`, `linkRepoPreventa`, `notaPropuesta`, `cantidadAdjuntos` y fechas
  `fechaRecepcion`…`fechaEntrega`; `ticketId` sigue único; organización con `/trycore/preventa`, rol `consultora`,
  `linda.lozano`, `viviana.velasquez`, actor filter `filtroConsultoraDelCaso`), `contratos.md` (`ctr_10_*`, `ctr_20_*`),
  `matriz-formularios.md` (`frm_10_validarSolicitud`, `frm_20_disenarPropuesta`, `frm_overview`, familia
  FAM-consultoras, precarga por `preventaContexto`), `handoff.md` (decisión del 2026-11-24 que reemplaza la del 12-nov).
- **Parámetros**: `param_stageEnEspera` (`1425810257`) nuevo; `param_consultores` pasa a tríos
  `owner:nombre:usuarioBonita` (`89450376:Linda:linda.lozano;89450377:Viviana:viviana.velasquez`).
- **Construcción**: `expresiones.md` (48 expresiones nuevas o reubicadas), `caminos.md` (3 caminos: `entregada` con
  adjunto y paso negativo «viviana no ve la tarea», `bloqueada` → vuelve a validar → entrega sin adjuntos, `noViable`).
- **Actor filter propio** `usuario-por-nombre` en `bonita-project/extensions/preventa-filtros/` (registrado con
  `registrar_extension.py`; Spock 7/7).
- **App**: dependencia zip de `hubspot-bonita-preventa-contexto-api-extension` en `bonita-project/app/pom.xml` y
  permiso `preventa_contexto_lectura` en el perfil `User`.

## Decisiones de diseño tomadas aquí

- Cambios de stage y `concepto_viabilidad` en **tareas de servicio por rama** (11/12/13), no como conectores de salida de
  la tarea 10: `hubspot-negocio-actualizar` exige propiedades no vacías y con «bloqueado» puede no haber concepto; un
  conector de Bonita no se salta por condición.
- Adjuntos en `21_subirAdjuntos` solo si `cantidadAdjuntos > 0` (`gwXor_2`): `hubspot-archivo-subir` exige lista no vacía.
- «No viable» (decisión de la usuaria, 2026-11-24): cerrado por viabilidad. Nota «Cerrado por viabilidad: …» en ticket y Negocio, `concepto_viabilidad`
  y ticket a «Closed» (`param_stageCerrado` = `4`) en `13_registrarNoViable`; fin `fin_noViable`.
- `gwXor_1` decide por `Preventa.resultadoValidacion` (no process variable).

## Verificado (salidas reales, última corrida tras la decisión «no viable → Closed»)

- `dealId`: `hubspot-ticket-leer` ya expone la salida `dealId` (agente B); `3_consultarTicket` escribe `Preventa.dealId`.
- `tools/arnes.sh generar` → código 0.
- `tools/arnes.sh verificar` → **código 0**: `check_inventario`, `check_expresiones`, `check_caminos`,
  `check_generados`, `check_formularios`, `check_cambios` en verde. Los huérfanos de la 1.0
  (`GestionPreventa-1.0.proc`, `_h155681b40002.conf`) aparecen como borrados en el índice de git; no los borró este
  agente.
- `mvn -B clean install -Pbundle` (desde `bonita-project/`) → BUILD SUCCESS; conectores 54 tests, filtros 7 tests;
  `app/target/processes/GestionPreventa--1.1.bar` (ya sin la 1.0).

## Journey (2026-11-24, tercera tanda: verde, contra el mock local)

Corrido con las copias parcheadas del arnés (P-1 arranque en Windows, P-2 mock con `--registro`), bundle nuevo
construido por el runner (`mvn clean install -Pbundle` BUILD SUCCESS, 7 min) y token ficticio. RAM libre antes de
arrancar: 3,9 GB. Nada contra HubSpot real.

- **Antes de la corrida verde** se corrigieron dos cosas:
  1. `frontend/forms.manifest.json`: restauradas las entradas técnicas (`parametros`, `_semilla`, `_muestra`); sin
     ellas la aplicación `parametros` no se instalaba. El bundle trae ya `custompage_formInternoParametros`,
     `custompage_frm10ValidarSolicitud`, `custompage_frm20DisenarPropuesta` y `custompage_frmOverview`.
  2. `docs/08-construccion/expresiones.md`: el `cuerpo` de `conn_hubspotNota` (10 y 20) usaba
     `.replace("\n","<br>")`; el generador convierte el `<br>` de la celda en un salto de línea real dentro del
     string Groovy y la tarea «Validar la solicitud» quedaba `failed` («Unexpected character: '"'»). Ahora:
     `.replace(String.valueOf((char) 10), "<" + "br>")`.
- **Resultado Newman**: salida 0 (`JOURNEY_EXIT=0`), sin assertions fallidas.
- **Reparto**: la consultora elegida por round robin fue `linda.lozano` (owner `89450376`) en los tres casos; el
  journey comprueba que «Validar la solicitud» **no** es tarea pendiente de `viviana.velasquez` y sí de `linda.lozano`.

Registro del mock (`método ruta cuerpo`, recortado):

| Camino | Líneas clave del registro | Resultado |
|---|---|---|
| `entregada` (viable + diseño **con** adjunto) | `PATCH tickets/T-001 {"hs_pipeline_stage": "2", "hubspot_owner_id": "89450376"}` · `POST notes` «Validación de preventa (Bonita): Viable … Concepto de viabilidad: Viable con DocFly» · `PATCH tickets/T-001 {"hs_pipeline_stage": "3"}` · `PATCH deals/D-001 {"concepto_viabilidad": …, "valoracion_operaciones": "40 h de fábrica", "url_ppta_preventa": …, "link_repo_preventa": …}` · `POST notes` «Propuesta de preventa (Bonita)» · `POST files/v3/files` (multipart `propuesta.pdf`) · `POST notes {"hs_note_body": "Adjuntos de preventa: 1 archivo(s).", "hs_attachment_ids": "F-001"}` · `PATCH tickets/T-001 {"hs_pipeline_stage": "1425810258"}` | pasó |
| `bloqueada` (bloqueado → En espera → vuelve → viable → diseño **sin** adjuntos) | `PATCH tickets/T-003 {"hs_pipeline_stage": "2", …}` · `POST notes` «Bloqueado (falta información del lead) … Falta el volumen de documentos.» · `PATCH tickets/T-003 {"hs_pipeline_stage": "1425810257"}` · `POST notes` «Viable … El lead completó la información.» · `PATCH tickets/T-003 {"hs_pipeline_stage": "3"}` · `PATCH deals/D-001 {… "valoracion_operaciones": "20 h" …}` · `POST notes` «Propuesta de preventa» · **sin** `POST files` · `PATCH tickets/T-003 {"hs_pipeline_stage": "1425810258"}` | pasó |
| `noViable` | `PATCH tickets/T-002 {"hs_pipeline_stage": "2", …}` · `POST notes {"hs_note_body": "<p><strong>Cerrado por viabilidad:</strong> Fuera del alcance de los productos</p>…"}` · `PATCH tickets/T-002 {"hs_pipeline_stage": "4"}` · `PATCH deals/D-002 {"concepto_viabilidad": "Fuera del alcance de los productos"}` | pasó |

- Limpieza: Bonita y el mock detenidos (puertos 8096 y 8099 libres, sin procesos `java`).

## Pendiente o no verificado

1. **`tools/arnes.sh verificar` = 1 solo por `check_generados`**: el manifiesto lleva el permiso
   `GET|extension/preventa` que el generador no escribe (opción B, `scripts/parche-manifest-preventa.py`). Se resuelve
   con P-3. Los demás custodios en verde.
2. **Versión del pool**: resuelto (2026-11-25, aprobado por la usuaria). El pool sube a **1.2** en `docs/07-bonita/`
   (`bpmn.md`, `contratos.md`, `handoff.md`) para que un runtime con la 1.1 desplegada tome la definición nueva
   (regla 6); regenerado (`GestionPreventa-1.2.proc`, se retiran el `.proc`/`.conf` de la 1.1) y middleware con
   `PROCESS_VERSION=1.2` por defecto.
3. Formularios en el navegador (precarga por `extension/preventa` con sesión real): no recorridos en esta corrida;
   el journey va por REST API.
4. Resto fuera del repo: `C:/Users/Administrador/AppData/Local/Temp/hubspot-bonita-bundle.Ldm3` (bundle de una
   corrida con `--mantener`, Bonita ya detenido). Borrarlo a mano.
5. Orden contrato → operaciones → conectores de salida y acceso a inputs en esos conectores: `[no verificado]` (sin MCP
   `bonita-doc-index` en la sesión).
6. Reintentar una tarea en fallo puede duplicar notas/adjuntos en HubSpot.
7. Tipo real de `concepto_viabilidad` y `valoracion_operaciones` en HubSpot (se guardan como `TEXT`).
