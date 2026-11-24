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

## Journey (no ejecutado: tres intentos fallidos al arrancar el runtime)

- Intentos con un bundle nuevo extraído por `run-journey.sh` (en el scratchpad y en `C:/bjA\Temp`): «FALLA: la REST
  API no respondió en 300 s». Causa encontrada: en Git Bash, `cmd.exe /c "start-bonita.bat …"` pierde el `/c` por la
  conversión de rutas de MSYS (`/c` → `C:/`) y cmd abre un prompt sin arrancar Bonita (`stdout.log` solo muestra el
  prompt). Con `MSYS_NO_PATHCONV=1` el `/c` funciona, pero entonces el mock no arranca (ruta `/c/...` del script) y
  la corrida siguiente (mock arrancado aparte) la detuvo Claude Code por **falta de memoria del equipo**; no se
  reintentó.
- Queda sin probar en ejecución: los caminos `entregada` (con adjunto y «viviana no ve la tarea»), `bloqueada` y
  `noViable`.
- El mock (`mock_http.py`) **no registra peticiones**: aunque el journey corra, solo prueba que el PATCH del ticket
  responde y que el caso llega a `fin_noViable`; no puede comprobar que el cuerpo lleva `hs_pipeline_stage` = `4`.
- `mock.json`: se añadieron las rutas de `T-003` (copia de las de `T-001`) para el camino `bloqueada`.

## Pendiente o no verificado

1. **Journey de punta a punta** (ver arriba): corregir el arranque del bundle en Windows en `run-journey.sh` (arnés)
   o correrlo con memoria disponible; para ver el stage `4` hace falta un mock que registre las peticiones.
2. Restos fuera del repo: `C:/bjA\Temp\hubspot-bonita-bundle.xgc8` (bundle extraído del intento detenido; sin
   procesos vivos). Borrarlo a mano.
3. Orden contrato → operaciones → conectores de salida y acceso a inputs en esos conectores: `[no verificado]` (sin MCP
   `bonita-doc-index` en la sesión).
4. Reintentar una tarea en fallo puede duplicar notas/adjuntos en HubSpot.
5. Tipo real de `concepto_viabilidad` y `valoracion_operaciones` en HubSpot (se guardan como `TEXT`).
