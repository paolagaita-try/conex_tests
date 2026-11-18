#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/slice-ops.sh
# slice-ops.sh — operaciones de UNIDAD que conducen las skills del arnés Bonita contra el IA
# Hub. NO es un hook registrado (mismo estatus que context-sync.sh): lo invocan las skills
# `bonita-construir-*`, los comandos /bonita:* y los agentes, UNA invocación por transición.
# Una unidad (U0…U4, E-<familia>, S-<subproceso>, SUB) es una épica del hub; el hub reparte,
# guarda fases y gates; aquí solo se valida lo barato y se encola lo que no pudo entregarse.
#
#   uso: slice-ops.sh <subcomando> [opciones]   (ver `usage` abajo)
#
# Contrato con la prosa: cada subcomando devuelve un código de salida tipado
# (0 ok · 2 uso · 4 sin unidad · 5 offline · 6 rechazado · 7 sin trabajo · 9 identidad
# heredada) y escribe en stdout lo que la skill debe mostrar. Modo servidor SIEMPRE (U16): no
# hay fuente de verdad local; sin hub, fail-open — caché + cola, nunca un modo local.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-ops.sh"
# [#74] `register` manda el mismo harness_version/asset_types que el arranque de sesión.
source "$HERE/lib/harness-meta.sh"

# URL del hub cuando no la dan ni --url, ni las credenciales, ni runtime.url de la config.
SO_HUB_URL_POR_DEFECTO="https://desarrollo.trycore.co:8444/api/orchestrator"
# Tope de longitud de un código de unidad: el del hub (`preferred_epic`, `code` de la épica).
SO_MAX_CODIGO=50

usage() {
  cat >&2 <<'USAGE'
uso: slice-ops.sh <subcomando> [opciones]

  register [--token-stdin] [--url U] [--force]  da de alta ESTE árbol como agente con un token
                                                que el ADMIN emitió para él. El token entra por
                                                STDIN o por TRYCORE_REGISTER_TOKEN, nunca por
                                                argumento. Obligatorio en un worktree antes de
                                                escribir (si no, rc 9).
  claim [--unidad <código>]                     reclama trabajo del hub; con --unidad pide esa
                                                unidad como PREFERENCIA (el hub la honra si está
                                                lista y si no reparte la siguiente y dice por qué)
  next-step                                     deriva la siguiente acción desde la caché
  status [--no-refresh]                         informe local del agente (unidad, cola, rechazados)
  mode                                          imprime runtime (siempre)
  phase <to>                                    reporta la fase (emite la cadena phase_advanced
                                                que falte; idempotente)
  gate <nombre> <pass|fail|na> [--evidence «texto» | --evidence-file F] [--causa «texto»]
                                                reporta un veredicto de la unidad (hecho medido);
                                                un fail manda la causa (--causa o la evidencia):
                                                el hub la exige para reabrir un gate ya pasado
  submit [--pr-url U] [--openspec-change C]     entrega la unidad
  archive [--pr-url U] [--openspec-change C]    archiva la unidad (siempre por la cola)
  wiring seed --file items.json                 siembra el checklist de cableado (failing)
  wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]
  progress «nota» | --file F                    nota de progreso (bitácora = event stream)
  checkpoint [--note «t» | --note-file F]        continuidad tras una caída
  escalate «razón» | --file F [--gate G]        registra un bloqueo (la decisión es humana)
  micro-fase <in_progress|pr|done>              avanza el micro-work reclamado (orden estricto)
  micro-checkpoint [--branch B] [--commit SHA] [--resumen T]
                                                punto de retorno del micro-work (rama y commit de
                                                git si no se pasan)
  micro-escalar --motivo «…» [--limite L]       el micro-work desborda su carril: pasa a propuesta
                                                de unidad (L: sin_dependencia_nueva |
                                                sin_endpoint_publico_nuevo | sin_cambio_de_dominio)
  fact <project-kind|foundation|harness-phase> …
                                                reporta un hecho de proyecto confirmado
  propose-asset --type-key K --path P --content-file F
  propose-epic --file borrador.json            propone una unidad nueva al hub (el código lo
                                                asigna el hub al aprobar)
  epic-status [--id P]                         estado de las propuestas (QUEUED|PROPOSED|
                                                APPROVED|REJECTED|FAILED)
  graph-sync --file bundle.json [--dry-run]     propone al hub el re-sync del grafo con el bundle
                                                de `trycore-bonita grafo` (lo aprueba el ADMIN;
                                                con --dry-run solo enseña la proyección)
  graph-sync-status [--id P]                    veredicto del re-sync (QUEUED|PROPOSED|
                                                APPROVED|REJECTED con el motivo del ADMIN)

códigos de salida: 0 ok · 2 uso · 4 sin unidad · 5 offline (encolado) · 6 rechazado
                   · 7 sin trabajo · 9 sin identidad propia (worktree que la hereda o árbol sin
                     credenciales: \`register\` con un token del ADMIN)
USAGE
}

# ── claim ────────────────────────────────────────────────────────────────────────────
# Protocolo §3: siempre POST (el GET no acepta el reporte de hashes); regla 1: no se abre
# trabajo con contexto viejo, así que se sincroniza ANTES; los 409 se distinguen por su
# CUERPO (spec §3.1 rev. 2), no por el status.

# _claim_field <json> <clave> — lee una clave de primer nivel de una respuesta JSON.
_claim_field() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    v=d.get(sys.argv[1]) if isinstance(d,dict) else None
    print(v if isinstance(v,str) else "")
except Exception:
    print("")
' "$2" 2>/dev/null
}

# [EP-OR-17] Los motivos del 409 del claim, como los emite el hub DE VERDAD.
#
# Este `case` esperaba `drift`/`contention`/`context_unresolvable`/`cross_project` como valor de
# `reason` en la RAÍZ de la respuesta. Ninguno de esos literales existe en el backend del hub:
# un HTTPException de FastAPI anida SIEMPRE bajo `detail`, y los cuatro casos llegan como
#   • drift de contexto  → detail dict con `manifest_hash` (el hash al que sincronizar)
#   • contención         → detail str «contención con otra escritura del contexto: reintenta…»
#   • contexto irresoluble → detail str «…no hay trabajo sin contexto declarado»
#   • lease ajeno/expirado → detail str «El lease está expirado, es de otro agente o no existe…»
# Todos caían en el `*)` y salían como rechazo duro: un drift —que se resuelve sincronizando y
# reintentando— dejaba al agente sin claim y sin saber por qué. La clasificación por FORMA (el
# dict con manifest_hash) manda sobre la clasificación por texto, que solo se usa donde el hub
# construye el mensaje en un único sitio. Se conserva la lectura plana por compatibilidad.

# _claim_409_kind <json> — clasifica el 409: drift|contention|context_unresolvable|
# cross_project|"" (desconocido).
_claim_409_kind() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
if not isinstance(d,dict):
    print(""); raise SystemExit(0)
det=d.get("detail")
# Compatibilidad: una instancia que sí nombrara el motivo en un campo manda sobre el texto.
for fuente in (det if isinstance(det,dict) else {}, d):
    marca=fuente.get("reason") or fuente.get("error")
    if isinstance(marca,str) and marca:
        print(marca); raise SystemExit(0)
# El drift se reconoce por FORMA, no por texto: el borde del hub garantiza el `manifest_hash`
# en el cuerpo precisamente para que el cliente sepa a qué contexto sincronizar.
if isinstance(det,dict) and det.get("manifest_hash"):
    print("drift"); raise SystemExit(0)
texto=det if isinstance(det,str) else (det.get("message","") if isinstance(det,dict) else "")
t=str(texto).lower()
if "contenci" in t:
    print("contention")
elif "no hay trabajo sin contexto" in t:
    print("context_unresolvable")
elif "otro agente" in t or "otro proyecto" in t:
    print("cross_project")
else:
    print("")
' 2>/dev/null
}

# _claim_409_text <json> — el motivo del hub en prosa, para enseñárselo al humano sin volcarle
# el JSON crudo encima. Cae al cuerpo entero si no hay nada mejor.
_claim_409_text() {
  command -v python3 >/dev/null 2>&1 || { printf '%s' "$1"; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
crudo=sys.stdin.read()
try:
    d=json.loads(crudo)
except Exception:
    print(crudo.strip()); raise SystemExit(0)
if not isinstance(d,dict):
    print(crudo.strip()); raise SystemExit(0)
det=d.get("detail")
if isinstance(det,str) and det:
    print(det)
elif isinstance(det,dict):
    print(det.get("message") or json.dumps(det,ensure_ascii=False))
else:
    print(crudo.strip())
' 2>/dev/null
}

# _claim_render <json> — resumen compacto de la unidad reclamada (lo lee el humano y el modelo).
# Entiende la forma REAL de `TaskClaimOut` (stories como objetos {code, acceptance_ref};
# `lease_expires_at`/`ttl_s` planos; `preference` si se pidió una unidad) y la del original
# (stories como cadenas, `lease` anidado).
# [Arreglo sobre el original] El original hacía `printf … | python3 - <<'PY'`: el heredoc ocupa
# el stdin de python3, el JSON del pipe nunca se leía y el render caía SIEMPRE al volcado crudo.
# El JSON va ahora por fichero temporal.
_claim_render() {
  local tmp
  command -v python3 >/dev/null 2>&1 || { echo "$1"; return; }
  tmp="$(mktemp)" || { echo "$1"; return; }
  printf '%s' "$1" > "$tmp"
  python3 - "$tmp" "$OPS_LIB_DIR" "$(config_integration_branch)" <<'PY' 2>/dev/null || echo "$1"
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
if not isinstance(d,dict):
    sys.exit(1)
if d.get("work_type")=="micro_work":
    # `ClaimOut = TaskClaimOut | MicroWorkClaimOut` (task_router.py): el hub puede repartir un
    # micro-work (carril ligero EP-OR-25) en vez de una unidad. Se rinde con SUS campos y se
    # remite a su carril: micro-fase, micro-checkpoint y micro-escalar (el lease lo renueva el
    # heartbeat por /micro-works/{id}/lease/renew).
    lim=d.get("limits") or {}
    cp=d.get("checkpoint") or {}
    print("micro-work:   %s %s" % (d.get("micro_work_id"), d.get("title") or ""))
    print("tipo:         %s · prioridad %s" % (d.get("kind") or "?", d.get("priority") if d.get("priority") is not None else "?"))
    print("fase:         %s" % d.get("phase"))
    print("rama:         %s" % d.get("branch"))
    print("ficheros:     %s" % ", ".join(str(x) for x in (d.get("files_scope") or [])))
    if lim:
        print("límites:      %s" % ", ".join(k for k,v in sorted(lim.items()) if v is True))
    print("lease:        expira %s (ttl %ss)" % (d.get("lease_expires_at"), d.get("ttl_s")))
    if cp.get("branch") or cp.get("commit_sha"):
        print("CHECKPOINT:   rama %s commit %s — CONTINÚA desde aquí" % (cp.get("branch"), cp.get("commit_sha")))
    if d.get("description"):
        print("descripción:  %s" % d.get("description"))
    print("carril:       es un micro-work, no una unidad: phase/gate/archive no aplican. Usa")
    print("              slice-ops.sh micro-fase in_progress|pr|done · micro-checkpoint --branch B --commit SHA")
    print("              · micro-escalar --motivo «…» si desborda sus límites (el heartbeat renueva su lease).")
    sys.exit(0)
g=d.get("gates") or {}
abiertos=[k for k,v in g.items() if v is not True]
lease=d.get("lease") if isinstance(d.get("lease"),dict) else {}
expira=lease.get("expires_at") or d.get("lease_expires_at")
ttl=lease.get("ttl_s") or d.get("ttl_s")
historias=[]
for h in d.get("stories") or []:
    if isinstance(h,dict):
        historias.append(str(h.get("code") or "?"))
    elif isinstance(h,str):
        historias.append(h)
cp=d.get("checkpoint")
print("unidad:       %s %s (slice %s)" % (d.get("epic_code"), d.get("epic_title") or "", d.get("slice_id")))
pref=d.get("preference")
if isinstance(pref,dict):
    if pref.get("honored"):
        print("preferencia:  %s honrada por el hub" % pref.get("requested"))
    else:
        print("preferencia:  %s NO honrada (%s): el hub entregó la siguiente de su cola"
              % (pref.get("requested"), pref.get("reason") or "sin motivo"))
print("fase:         %s" % d.get("phase"))
print("gates abiertos: %s" % (", ".join(abiertos) if abiertos else "ninguno"))
# [Hub real] `branch_base` es la RAMA DE TRABAJO de la unidad (`derive_branch_base`), no la de partida: se
# parte de la de integración (la primera protegida de la política) y el PR va contra ella. El change viene
# null si el ADMIN importó el grafo (`EpicIn` no lo tiene): se deriva con la misma función que la caché.
rama,change,origen=d.get("branch_base"),d.get("openspec_change"),None
try:
    sys.dont_write_bytecode=True
    sys.path.insert(0,sys.argv[2])
    import grafo_unidades
    rama=grafo_unidades.rama_de_trabajo(d)
    change,origen=grafo_unidades.resolver_change(d)
except Exception:
    pass
print("rama:         %s" % rama)
print("integración:  %s" % sys.argv[3])
print("change:       %s%s" % (change, " (derivado: el hub no lo trae)" if origen=="derivado" else ""))
print("docs:         %s" % d.get("docs_ref"))
print("ficheros:     %s" % ", ".join(str(x) for x in (d.get("files_scope") or [])))
print("tareas:       %s" % ", ".join(historias))
print("lease:        expira %s (ttl %ss)" % (expira, ttl))
if cp:
    print("CHECKPOINT:   rama %s commit %s — CONTINÚA desde aquí, jamás reinicies (protocolo §3 regla 2)"
          % (cp.get("branch"), cp.get("commit_sha")))
# [I3] La resolución humana de la última escalada (`TaskClaimOut.resolution`, {decision, note}: ACEPTADA,
# REPLANTEADA o NEGADA). El hub omite la clave si el slice nunca se resolvió.
res=d.get("resolution")
if isinstance(res,dict) and (res.get("decision") or res.get("note")):
    print("resolución:   %s — %s" % (res.get("decision") or "?", res.get("note") or "sin nota"))
    print("              es la decisión del ADMIN sobre tu escalada: síguela antes que nada.")
PY
  rm -f "$tmp"
}

# _claim_once [unidad] — una llamada. rc 20 = reintentable (drift|contention), resto = final.
# [#39] `epic_code` NUNCA viaja: `TasksNextIn` no lo declara (pydantic lo ignoraba en silencio y
# la cola repartía OTRA épica con claim "exitoso"). La unidad pedida viaja como
# `preferred_epic` (EP-OR-18, HU-OR-79): un hint que el hub honra si la épica está en el
# ready-set sin lease; si no, reparte la siguiente y lo dice en `preference`. Sin
# `preferred_epic_strict`: el claim estricto deja al agente sin trabajo ante cualquier
# dependencia pendiente, y aquí el hub decide.
_claim_once() {
  local unidad="${1:-}" hashes body resp status reason gv extra=""
  hashes="$(ops_context_hashes)"
  # [#63] La versión de grafo viaja SOLO si la conocemos: un hub que no versiona (instancia
  # antigua) debe seguir viendo el mismo cuerpo de siempre — compatibilidad hacia atrás.
  gv="$(_runtime_graph_version)"
  [ -n "$gv" ] && extra=",\"graph_version\":$gv"
  [ -n "$unidad" ] && extra="$extra,\"preferred_epic\":$(ops_json_str "$unidad")"
  body="{\"context_hashes\":$hashes$extra}"
  resp="$(runtime_post "$OPS_PATH_CLAIM" "$body")"
  status="$(runtime_http_status)"
  case "$status" in
    200)
      # La respuesta del claim se guarda: /agent/context no trae el título de la unidad ni el
      # micro-work reclamado, y sin su id ni los subcomandos micro-* ni el heartbeat lo operan.
      ops_claim_cache_write "$resp" || echo "⚠ no se pudo guardar la caché del claim (.claude/state/claim.json)" >&2
      agent_context_fetch_and_cache || \
        echo "⚠ claim aceptado, pero /agent/context no respondió: se sigue con la caché anterior" >&2
      _claim_render "$resp"
      return $OPS_RC_OK ;;
    204)
      echo "NO_WORK: el runtime no tiene trabajo disponible para este agente"
      return $OPS_RC_NO_WORK ;;
    409)
      # [EP-OR-17] El grafo rancio se comprueba ANTES del `case`, con el helper del cliente:
      # conoce la forma REAL del hub (`detail.error = graph_version_stale`) además de la plana
      # que este sitio leía a mano y que el hub no emite en ninguna parte.
      local server_gv
      if server_gv="$(runtime_stale_graph_version "$resp")"; then
        # [#63] No es un error: es la señal de que operamos contra una foto vieja del
        # backlog. Se anota el desfase (lo muestra `status`) y se pide UN reintento con la
        # proyección refrescada. Mismo patrón que el 409 del lease en hb_renew.
        runtime_graph_note_stale "$gv" "$server_gv"
        echo "⚠ 409 (graph_version_stale): el grafo local (v${gv:-?}) va por detrás del hub (v${server_gv:-?})" >&2
        return 21
      fi
      reason="$(_claim_409_kind "$resp")"
      case "$reason" in
        drift|contention)
          echo "⚠ 409 ($reason): reintentable — $(_claim_409_text "$resp")" >&2
          return 20 ;;
        context_unresolvable)
          echo "⛔ 409 contexto irresoluble — NO reintentar: $(_claim_409_text "$resp")" >&2
          echo "  Resuélvelo en el hub (propuesta → publicación) y vuelve a reclamar." >&2
          return $OPS_RC_REJECTED ;;
        cross_project)
          echo "⛔ 409 cruce de proyecto (queda auditado en el servidor): $(_claim_409_text "$resp")" >&2
          echo "  Este clon está registrado contra otro proyecto: revisa runtime.credentials." >&2
          return $OPS_RC_REJECTED ;;
        *)
          echo "⛔ 409 del hub: $(_claim_409_text "$resp")" >&2
          return $OPS_RC_REJECTED ;;
      esac ;;
    401|403)
      echo "⛔ token inválido o revocado ($status): pide un token nuevo al ADMIN del proyecto." >&2
      echo "  Los guards siguen operando con el último lock; el trabajo local no se detiene." >&2
      return $OPS_RC_REJECTED ;;
    422)
      echo "⛔ 422 el servidor rechazó el claim: $resp — no reintentar." >&2
      return $OPS_RC_REJECTED ;;
    000)
      echo "OFFLINE: runtime inalcanzable; se sigue con la caché local (RNF-6)" >&2
      return $OPS_RC_OFFLINE ;;
    *)
      echo "⚠ respuesta inesperada del claim ($status): $resp" >&2
      return $OPS_RC_OFFLINE ;;
  esac
}

cmd_claim() {
  local epic="" unidad="" pedida=0 expected rc
  while [ $# -gt 0 ]; do
    case "$1" in
      --epic) epic="${2:-x}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --unidad) pedida=1; unidad="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  # [#39] `--epic` era el claim dirigido que el hub ignoraba en silencio (repartía otra épica
  # dejando un lease huérfano). Sigue fallando EXPLÍCITO, antes de tocar la red, y remite a la
  # vía buena: `--unidad`, que viaja como `preferred_epic` (EP-OR-18).
  if [ -n "$epic" ]; then
    echo "⛔ claim --epic no existe: POST /tasks/next no acepta epic_code y el hub repartiría la" >&2
    echo "  primera épica de su cola como si fuera la pedida." >&2
    echo "  Usa \`claim --unidad <código>\`: viaja como preferencia (preferred_epic) — el hub la" >&2
    echo "  honra si la unidad está lista y, si no, entrega la siguiente de su cola y dice por qué." >&2
    return $OPS_RC_USAGE
  fi
  if [ "$pedida" = 1 ]; then
    if [ -z "$unidad" ]; then
      echo "⛔ claim --unidad necesita un código (U0…U4, E-<familia>, S-<subproceso>, SUB)" >&2
      return $OPS_RC_USAGE
    fi
    # El cliente solo exige lo del hub (`preferred_epic`: max_length=50); el patrón fino de
    # los códigos de unidad lo aplican las skills.
    if [ "${#unidad}" -gt "$SO_MAX_CODIGO" ]; then
      echo "⛔ código de unidad de ${#unidad} caracteres: el hub admite $SO_MAX_CODIGO como máximo" >&2
      return $OPS_RC_USAGE
    fi
  fi
  # Contexto primero (protocolo §3 regla 1). context-sync.sh es fail-open: si no puede,
  # sale 0 y deja el lock anterior — el claim seguirá y el servidor detectará el drift.
  expected="$(projection_get context.manifest_hash "")"
  [ -n "$expected" ] || expected="$(runtime_field manifest_hash)"
  _claim_context_sync "$expected"
  _claim_once "$unidad"
  rc=$?
  if [ $rc -eq 20 ] || [ $rc -eq 21 ]; then
    # Drift, contención o grafo rancio: refrescar el estado REAL y reintentar EXACTAMENTE una
    # vez (protocolo §7). Pasar "" a context-sync.sh no fuerza nada — su fallback recae en la
    # caché de credenciales, que en el escenario de drift YA coincide con el lock local —, así
    # que se refresca antes con GET /agent/context y se usa SU manifest_hash como EXPECTED.
    # Para `stale_graph` ese mismo refresco es justamente lo que trae la versión nueva.
    agent_context_fetch_and_cache >/dev/null 2>&1
    expected="$(projection_get context.manifest_hash "")"
    _claim_context_sync "$expected"
    local prev_rc=$rc
    _claim_once "$unidad"
    rc=$?
    if [ $rc -eq 21 ]; then
      # Segundo 409 con el grafo ya refrescado: no es una carrera, es un desfase que el
      # cliente no puede resolver solo. El mensaje NOMBRA el desfase y la acción.
      local gs
      gs="$(runtime_graph_status_read)"
      echo "⛔ el hub rechaza el claim por versión de grafo obsoleta, incluso tras refrescar." >&2
      echo "  desfase: $gs" >&2
      echo "  El grafo del hub cambió mientras reclamabas (una unidad propuesta, aprobada o" >&2
      echo "  rechazada). Vuelve a intentarlo en unos segundos; si persiste, revisa en la consola" >&2
      echo "  del hub que este proyecto no esté a mitad de un import de grafo." >&2
      return $OPS_RC_REJECTED
    fi
    if [ $rc -eq 20 ]; then
      echo "otro agente tomó la tarea; pide la siguiente"
      return $OPS_RC_NO_WORK
    fi
    # Un claim correcto tras un stale_graph deja el marcador de desfase sin sentido.
    [ $rc -eq 0 ] && [ "$prev_rc" -eq 21 ] && runtime_graph_clear_stale
  fi
  return $rc
}

# _claim_context_sync <manifest_hash> — sincroniza el contexto gobernado antes de reclamar
# (context-sync.sh, invocado y no registrado). Fail-open: si el script falta o falla, el
# claim sigue y el hub detectará el drift por los hashes.
_claim_context_sync() {
  [ -f "$HERE/context-sync.sh" ] || return 0
  bash "$HERE/context-sync.sh" "$1" >/dev/null 2>&1
  return 0
}

# ── next-step ────────────────────────────────────────────────────────────────────────
# El servidor entrega hechos; el PASO lo deriva el cliente (spec §2, invierte el plan §1.3).
# Prioridad determinista, la primera que aplique.
cmd_next_step() {
  local sid proj tmp_script
  sid="$(ops_slice_id)"
  if [ -z "$sid" ]; then
    echo "sin slice activo: reclama trabajo (\`slice-ops.sh claim\`) o abre uno por DoR"
    return $OPS_RC_NO_SLICE
  fi
  command -v python3 >/dev/null 2>&1 || { echo "continúa el pipeline por la fase del slice"; return $OPS_RC_OK; }
  proj="$(runtime_projection_read)"
  tmp_script="$(mktemp)"
  cat > "$tmp_script" <<'PY'
import json,sys
orden=sys.argv[1].split()
try:
    d=json.load(sys.stdin)
except Exception:
    d={}
sl=d.get("active_slice") or {}
hint=sl.get("resume_hint")
failing=sl.get("wiring_failing") or []
subs=sl.get("sub_slices_pending") or []
gates=sl.get("gates") or {}
if hint:
    print("resume_hint: %s" % hint)
elif failing:
    it=failing[0]
    print("cablear el item de wiring «%s» (%s) con prueba REAL ejecutada; no lo marques passing por inspección"
          % (it.get("item_id"), it.get("kind")))
elif subs:
    print("construir el siguiente sub-slice: %s (journey_smoke verde antes de pasar al siguiente)" % subs[0])
else:
    abierto=next((g for g in orden if gates.get(g) is False), None)
    if abierto:
        print("cerrar el gate «%s» (fase %s)" % (abierto, sl.get("phase")))
    else:
        print("todos los gates conocidos están cerrados: abre el PR, archiva el change y reporta submit")
PY
  echo "$proj" | python3 "$tmp_script" "$OPS_SLICE_GATES" 2>/dev/null || echo "continúa el pipeline por la fase del slice"
  rm -f "$tmp_script"
}

# ── fact ─────────────────────────────────────────────────────────────────────────────
# Hechos de PROYECTO, contrato del catálogo v2 del hub [#38] (project_facts_domain):
# - Hechos MÁQUINA (`project_kind`, `harness_phase`, `foundation`): UN solo tipo,
#   `project_fact_updated`, con el payload EXACTO {fact, value, source:"AGENT"}
#   (extra="forbid": ninguna otra clave viaja). Ámbito proyecto: sin `slice_id`.
# - Los hechos HUMANOS del vertical original (`scaffold_confirmed`, `design_source_*`, de un
#   front web) no existen en el arnés Bonita: nombrarlos es un error de uso (rc 2).
cmd_fact() {
  local hecho="${1:-}"
  [ -n "$hecho" ] && shift
  case "$hecho" in
    project-kind) _fact_project_kind "$@" ;;
    foundation) _fact_foundation "$@" ;;
    harness-phase) _fact_harness_phase "$@" ;;
    *) echo "uso: slice-ops.sh fact <project-kind|foundation|harness-phase> [opciones]" >&2
       return $OPS_RC_USAGE ;;
  esac
}

# _ops_emit_event <tipo> <payload_json> [slice_id] — evento genérico de dominio, siempre por
# la cola (spec §3.1). El slice_id es opcional
# (los hechos de PROYECTO se encolan sin él, spec §3.1 rev. 3; una escalada de slice sí lo
# lleva). Devuelve $OPS_RC_OFFLINE si el runtime no pudo aceptar el evento (outbox no
# escribible, python3 ausente u otro fallo local) — el caller decide qué avisar y nunca debe
# reportar éxito en ese caso (fail-open sobre el trabajo local, nunca sobre el reporte).
_ops_emit_event() {
  local tipo="$1" payload="$2" sid="${3:-}" pfile
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OFFLINE
  if ! ops_enqueue_from_file "$tipo" "$pfile" "$sid"; then
    rm -f "$pfile"
    return $OPS_RC_OFFLINE
  fi
  rm -f "$pfile"
  return $OPS_RC_OK
}

# _fact_machine_emit <fact> <value_json> — [#38] hecho MÁQUINA del catálogo v2: payload
# EXACTO {fact, value, source:"AGENT"} (extra="forbid" en el hub: nada más viaja) y SIN
# slice_id (ámbito proyecto).
_fact_machine_emit() {
  local fact="$1" value_json="$2" payload pfile
  payload="{\"fact\":$(ops_json_str "$fact"),\"value\":$value_json,\"source\":\"AGENT\"}"
  pfile="$(ops_tmpjson "$payload")" || {
    echo "⚠ hecho \"$fact\" no se pudo encolar (fallo local)" >&2
    return $OPS_RC_OFFLINE
  }
  if ! ops_enqueue_from_file project_fact_updated "$pfile" ""; then
    rm -f "$pfile"
    echo "⚠ hecho \"$fact\" no se pudo encolar (outbox no escribible u otro fallo local)" >&2
    return $OPS_RC_OFFLINE
  fi
  rm -f "$pfile"
  echo "hecho de proyecto \"$fact\" encolado (project_fact_updated)"
  return $OPS_RC_OK
}

_fact_project_kind() {
  local kind="${1:-}" src="human"
  [ -n "$kind" ] && shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --source) src="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$kind" in greenfield|brownfield) : ;; *) echo "⛔ project-kind debe ser greenfield|brownfield" >&2; return $OPS_RC_REJECTED ;; esac
  # --source auto|human se sigue aceptando (compat con la prosa de las skills), pero NO
  # viaja: en la superficie de agente el hub solo admite source="AGENT" (progress_service).
  case "$src" in auto|human) : ;; *) echo "⛔ --source debe ser auto|human" >&2; return $OPS_RC_REJECTED ;; esac
  _fact_machine_emit project_kind "$(ops_json_str "$kind")"
}

_fact_foundation() {
  local required="" epic="" cfile=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --required) required="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --epic) epic="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --checklist-file) cfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$required" in true|false) : ;; *) echo "⛔ --required debe ser true|false" >&2; return $OPS_RC_REJECTED ;; esac
  # El hub proyecta `foundation` a un Boolean (`foundation_confirmed`): el value es el
  # booleano de --required. --epic y --checklist-file se aceptan por compat con
  # /bonita:onboard pero NO viajan (extra="forbid"): la checklist queda en los docs locales.
  _fact_machine_emit foundation "$required"
}

_fact_harness_phase() {
  local fase="${1:-}"
  case "$fase" in authoring|building) : ;; *) echo "⛔ harness-phase debe ser authoring|building" >&2; return $OPS_RC_REJECTED ;; esac
  _fact_machine_emit harness_phase "$(ops_json_str "$fase")"
}

# ── propose-asset ────────────────────────────────────────────────────────────────────
# Un agente JAMÁS publica contexto (protocolo §6): propone contra la superficie de agente
# `…/context/agent-proposals` (no la humana `…/context/proposals`) y un ADMIN publica.
cmd_propose_asset() {
  local type_key="" path="" cfile="" pid body resp status
  while [ $# -gt 0 ]; do
    case "$1" in
      --type-key) type_key="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --path) path="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --content-file) cfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$type_key" ] || [ -z "$path" ] || [ -z "$cfile" ]; then
    echo "uso: slice-ops.sh propose-asset --type-key K --path P --content-file F" >&2
    return $OPS_RC_USAGE
  fi
  [ -f "$cfile" ] || { echo "⛔ no existe el fichero de contenido: $cfile" >&2; return $OPS_RC_USAGE; }
  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || { echo "⛔ sin project_id en runtime.credentials: registra el agente (\`slice-ops.sh register\`)" >&2; return $OPS_RC_REJECTED; }
  # El contenido puede ser largo: se serializa por fichero (nunca por argv) y el body sale
  # por `curl --data-binary @fichero` dentro de runtime_post.
  body="{\"path\":$(ops_json_str "$path"),\"type_key\":$(ops_json_str "$type_key"),\"content\":$(ops_json_str_file "$cfile" 200000)}"
  resp="$(runtime_post "$(ops_path_proposals "$pid")" "$body")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202)
      echo "propuesta creada: $resp"
      echo "El agente NO publica contexto: la revisa y publica un ADMIN en la consola del hub."
      return $OPS_RC_OK ;;
    422)
      echo "⛔ 422 la propuesta no valida contra el schema del tipo \"$type_key\": $resp" >&2
      return $OPS_RC_REJECTED ;;
    401|403)
      echo "⛔ token inválido o sin permiso para proponer ($status): habla con el ADMIN." >&2
      return $OPS_RC_REJECTED ;;
    *)
      echo "OFFLINE: no se pudo proponer el asset (status $status). El documento queda en git; reintenta al reconectar." >&2
      return $OPS_RC_OFFLINE ;;
  esac
}

# ── propose-epic ─────────────────────────────────────────────────────────────────────
# [#62] La terminal PROPONE, el hub decide la identidad, un humano aprueba. El agente pierde
# a propósito la potestad de inventar el código: elegirlo a mano es lo que hizo que dos
# terminales crearan dos épicas con códigos consecutivos el mismo día y sus historias
# colisionaran (incidente del arnés original).
# Va por el carril directo de la outbox (endpoint propio, hub#113) para sobrevivir a estar
# offline, y se intenta despachar en el acto para poder devolver el identificador del hub.

# _epic_draft_normalize <fichero> — imprime el cuerpo de la propuesta ya normalizado, o "" con
# rc 2 si el borrador no vale. `epic_code`/`code`/`id` se DESCARTAN (no se rechaza la
# propuesta: la decisión de hub#113 es ignorar el campo, no fallar por él).
_epic_draft_normalize() {
  local f="$1"
  # [Importante 4] sin python3 no es "borrador inválido" (rc 2 de uso): es una degradación de
  # infraestructura — se anuncia con esas palabras y con OFFLINE, para que no se confunda con
  # un borrador mal escrito.
  command -v python3 >/dev/null 2>&1 || {
    echo "⛔ sin python3: no se puede validar el borrador en local" >&2
    return $OPS_RC_OFFLINE
  }
  # OJO: sin `2>/dev/null` aquí — el llamador captura este stderr en `$errf` para mostrar
  # el motivo del rc 2 (validación) o el aviso de `epic_code` ignorado; silenciarlo aquí
  # los perdería a los dos.
  python3 - "$f" <<'PY'
import json,re,sys
# [#70] El vocabulario del BORRADOR (lo que escribe el agente) y el del CONTRATO del hub
# (`EpicProposalIn`) no son el mismo: el borrador habla en minúsculas y conoce `technical`;
# el hub solo acepta el literal FOUNDATIONAL|BUSINESS. La traducción vive aquí, en el borde,
# porque rechazar `technical` sería castigar al agente por una distinción que el grafo no
# hace: para el hub una épica técnica es de negocio.
CAPAS={"foundational":"FOUNDATIONAL","business":"BUSINESS","technical":"BUSINESS"}

def escenarios(txt):
    """Criterios en prosa -> `acceptance[]` del contrato: un escenario Dado/Cuando/Entonces
    por entrada. Se parte por líneas y, dentro de cada una, por el `. Dado ` que separa dos
    escenarios seguidos en un mismo párrafo."""
    out=[]
    for linea in str(txt).splitlines():
        linea=linea.strip().lstrip("-*•").strip()
        if not linea:
            continue
        for trozo in re.split(r"\.\s+(?=Dado\s)", linea):
            trozo=trozo.strip()
            if trozo:
                out.append(trozo[:2000])
    return out[:20]

try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print("⛔ el borrador no es un JSON legible", file=sys.stderr); raise SystemExit(2)
if not isinstance(d,dict):
    print("⛔ el borrador debe ser un objeto JSON", file=sys.stderr); raise SystemExit(2)
title=(d.get("title") or "").strip()
objective=(d.get("objective") or "").strip()
if not title:
    print("⛔ el borrador no trae `title` (título de la épica)", file=sys.stderr); raise SystemExit(2)
if not objective:
    print("⛔ el borrador no trae `objective` (objetivo de la épica)", file=sys.stderr); raise SystemExit(2)
layer=str(d.get("layer") or "business").strip().lower()
if layer not in CAPAS:
    print("⛔ `layer` debe ser uno de: %s" % ", ".join(sorted(CAPAS)), file=sys.stderr); raise SystemExit(2)
ignorados=[k for k in ("epic_code","code","id") if d.get(k)]
stories=[]
for s in d.get("stories") or []:
    if isinstance(s,str):
        stories.append({"title":s[:300]})
    elif isinstance(s,dict) and (s.get("title") or "").strip():
        st={"title":s["title"].strip()[:300]}
        if s.get("description"):
            st["description"]=str(s["description"])[:2000]
        # La `acceptance` explícita del borrador manda; si no, se derivan de los criterios en
        # prosa. `acceptance_criteria` NO viaja: el hub descarta el campo en el borde
        # (`extra="ignore"`) y la consola enseñaba las historias sin un solo criterio.
        acc=s.get("acceptance")
        if isinstance(acc,list):
            acc=[str(x).strip()[:2000] for x in acc if str(x).strip()][:20]
        elif s.get("acceptance_criteria"):
            acc=escenarios(s["acceptance_criteria"])
        else:
            acc=[]
        if acc:
            st["acceptance"]=acc
        stories.append(st)
out={"title":title[:300],"objective":objective[:2000],"layer":CAPAS[layer],
     "files_scope":[str(x) for x in (d.get("files_scope") or []) if isinstance(x,(str,int))],
     "depends_on":[str(x) for x in (d.get("depends_on") or []) if isinstance(x,(str,int))],
     "stories":stories}
if ignorados:
    print("IGNORADOS %s" % ",".join(ignorados), file=sys.stderr)
print(json.dumps(out,ensure_ascii=False))
PY
}

# [#70] `EpicProposalOut` del contrato nombra `id` al identificador de la propuesta (el
# borrador de hub#113 lo llamaba `proposal_id`). Sin esto la terminal decía «sin identificador
# en la respuesta» y el ledger guardaba "" — `epic-status` se quedaba sin a quién preguntar.
# Se acepta el nombre viejo como respaldo: un hub anterior al contrato sigue funcionando.
_epic_proposal_id() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    r=(d.get("response") if isinstance(d.get("response"),dict) else d) or {}
    print(r.get("id") or r.get("proposal_id") or "")
except Exception:
    print("")
' 2>/dev/null
}

# _epic_from_response <respuesta> — la épica aprobada como objeto para el ledger. El contrato
# la devuelve en la RAÍZ de `EpicProposalOut`; el borrador viejo la anidaba en `epic`.
_epic_from_response() {
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("{}"); raise SystemExit(0)
if not isinstance(d,dict):
    print("{}"); raise SystemExit(0)
e=d.get("epic")
if not isinstance(e,dict):
    e={k:d[k] for k in ("title","objective","layer","stories","files_scope","depends_on") if k in d}
print(json.dumps(e,ensure_ascii=False))
' 2>/dev/null || echo "{}"
}

cmd_propose_epic() {
  local file="" pid norm errf rc cid pfile ack proposal_id reason
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$file" ]; then
    echo "uso: slice-ops.sh propose-epic --file borrador.json" >&2
    echo "  borrador: {title, objective, layer, files_scope[], depends_on[], stories[]}" >&2
    echo "  SIN código: lo asigna el hub al aprobar." >&2
    return $OPS_RC_USAGE
  fi
  [ -f "$file" ] || { echo "⛔ no existe el borrador: $file" >&2; return $OPS_RC_USAGE; }
  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || { echo "⛔ sin project_id en runtime.credentials: registra el agente (\`slice-ops.sh register\`)" >&2; return $OPS_RC_REJECTED; }

  errf="$(mktemp)" || return $OPS_RC_OFFLINE
  norm="$(_epic_draft_normalize "$file" 2>"$errf")"
  rc=$?
  # [Importante 4] rc OFFLINE (sin python3) no es lo mismo que rc USAGE (borrador inválido):
  # el primero es fallo de infraestructura, reintentable; el segundo es del agente.
  if [ "$rc" -eq "$OPS_RC_OFFLINE" ]; then
    cat "$errf" >&2
    rm -f "$errf"
    return $OPS_RC_OFFLINE
  fi
  if [ $rc -ne 0 ] || [ -z "$norm" ]; then
    cat "$errf" >&2
    rm -f "$errf"
    return $OPS_RC_USAGE
  fi
  if grep -q '^IGNORADOS ' "$errf"; then
    echo "⚠ código de épica ignorado ($(sed -n 's/^IGNORADOS //p' "$errf")): la identidad la asigna el hub al aprobar." >&2
  fi
  rm -f "$errf"

  pfile="$(ops_tmpjson "$norm")" || return $OPS_RC_OFFLINE
  # El `1` final pide el estampado de la versión de grafo AL DESPACHAR [#63]: una propuesta
  # encolada offline debe salir con la versión vigente en ese momento, no con la de ayer.
  cid="$(runtime_enqueue_direct epic_proposed POST "$(ops_path_epic_proposals "$pid")" "$pfile" 1)"
  rm -f "$pfile"
  if [ -z "$cid" ]; then
    echo "⛔ no se pudo encolar la propuesta (outbox no escribible): guárdala y reintenta." >&2
    return $OPS_RC_OFFLINE
  fi
  ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"QUEUED\",\"proposal_id\":null,\"epic_code\":null,\"written_back_at\":null,\"draft\":$norm}"

  # Intento de despacho inmediato: si hay red, la skill puede enseñar YA el identificador.
  runtime_dispatch_outbox >/dev/null 2>&1
  ack="$(ops_epic_ack_read "$cid")"
  if [ -n "$ack" ]; then
    proposal_id="$(_epic_proposal_id "$ack")"
    ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"PROPOSED\",\"proposal_id\":$(ops_json_str "$proposal_id")}"
    echo "propuesta enviada: ${proposal_id:-sin identificador en la respuesta}"
    echo "Queda en PROPOSED: NO es reclamable hasta que un humano la apruebe en la consola del hub."
    echo "El código lo asigna el hub AL APROBAR. Consulta con \`slice-ops.sh epic-status\`."
    return $OPS_RC_OK
  fi
  reason="$(ops_epic_rejected_reason "$cid")"
  if [ -n "$reason" ]; then
    ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"FAILED\",\"reason\":$(ops_json_str "$reason")}"
    echo "⛔ la propuesta no se pudo entregar: $reason" >&2
    return $OPS_RC_REJECTED
  fi
  echo "propuesta encolada: $cid"
  # [Ronda final] El texto ya no afirma «sin conexión»: desde que el despacho lleva mutex
  # (A1), este camino también se toma cuando el daemon estaba despachando la cola en ese
  # mismo instante y el intento en primer plano cedió el turno. La propuesta está encolada y
  # el daemon la lleva en los dos casos —el rc 5 y la conducta no cambian—, pero nombrar una
  # causa que puede ser falsa manda al usuario a revisar una red que funciona.
  echo "PENDIENTE: se despachará sola (el daemon de heartbeat la lleva). Sin conexión aún, o"
  echo "el daemon estaba drenando la cola en este instante. \`slice-ops.sh epic-status\` la sigue."
  echo "NO escribas la unidad en docs/08-construccion/plan.md con un código inventado: lo asigna el hub al aprobar."
  return $OPS_RC_OFFLINE
}

# ── epic-status ──────────────────────────────────────────────────────────────────────
# [#62] Resuelve el ciclo de vida de cada propuesta del ledger. Dos fuentes por estado:
#   QUEUED   → mira el ack del carril directo (¿ya se despachó?) o el rechazo local.
#   PROPOSED → pregunta al hub por su estado (APPROVED con `epic_code`, o REJECTED con razón).
# Es INFORMATIVO: rc 0 siempre en runtime, pase lo que pase.
cmd_epic_status() {
  local only="" pid entries n i cid pidv st ack resp status tmp
  while [ $# -gt 0 ]; do
    case "$1" in
      --id) only="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  command -v python3 >/dev/null 2>&1 || { echo "sin python3: no se puede leer el ledger"; return $OPS_RC_OK; }
  pid="$(runtime_field project_id)"

  # Primero, la parte que NO toca la red: acks y rechazos del carril directo.
  tmp="$(mktemp)" || return $OPS_RC_OK
  ops_epic_ledger_read > "$tmp"
  n="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["proposals"]))' "$tmp" 2>/dev/null)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  if [ "$n" -eq 0 ]; then
    rm -f "$tmp"
    echo "sin propuestas de épica registradas en esta copia del proyecto"
    return $OPS_RC_OK
  fi
  i=0
  while [ "$i" -lt "$n" ]; do
    cid="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposals"][int(sys.argv[2])].get("client_event_id") or "")' "$tmp" "$i" 2>/dev/null)"
    pidv="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposals"][int(sys.argv[2])].get("proposal_id") or "")' "$tmp" "$i" 2>/dev/null)"
    st="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposals"][int(sys.argv[2])].get("status") or "")' "$tmp" "$i" 2>/dev/null)"
    i=$((i + 1))
    [ -n "$only" ] && [ "$only" != "$pidv" ] && continue

    if [ "$st" = "QUEUED" ] && [ -n "$cid" ]; then
      ack="$(ops_epic_ack_read "$cid")"
      if [ -n "$ack" ]; then
        pidv="$(_epic_proposal_id "$ack")"
        st=PROPOSED
        ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"PROPOSED\",\"proposal_id\":$(ops_json_str "$pidv")}"
      else
        local rej; rej="$(ops_epic_rejected_reason "$cid")"
        if [ -n "$rej" ]; then
          ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"FAILED\",\"reason\":$(ops_json_str "$rej")}"
          echo "$cid  FAILED       $rej"
          continue
        fi
        echo "$cid  QUEUED       aún en la cola: se despachará al recuperar conexión"
        continue
      fi
    fi

    if [ "$st" = "PROPOSED" ] && [ -n "$pidv" ] && [ -n "$pid" ]; then
      resp="$(runtime_get "$(ops_path_epic_proposal "$pid" "$(ops_urlenc "$pidv")")")"
      status="$(runtime_http_status)"
      case "$status" in
        200)
          st="$(_claim_field "$resp" status)"
          case "$st" in
            APPROVED)
              local code epic
              # [#70] El código lo asigna el hub en `assigned_code` (EP-OR-15); `epic_code` era
              # el nombre del borrador y se conserva como respaldo.
              code="$(_claim_field "$resp" assigned_code)"
              [ -n "$code" ] || code="$(_claim_field "$resp" epic_code)"
              epic="$(_epic_from_response "$resp")"
              [ -n "$epic" ] || epic="{}"
              ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"APPROVED\",\"epic_code\":$(ops_json_str "$code"),\"epic\":$epic}"
              echo "$pidv  APPROVED     $code — llévala a docs/08-construccion/plan.md con ese código" ;;
            REJECTED)
              # [#70] El motivo del rechazo humano viaja en `reject_reason` (EP-OR-15).
              local why; why="$(_claim_field "$resp" reject_reason)"
              [ -n "$why" ] || why="$(_claim_field "$resp" reason)"
              ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"REJECTED\",\"reason\":$(ops_json_str "$why")}"
              echo "$pidv  REJECTED     ${why:-sin motivo registrado}" ;;
            *)
              echo "$pidv  PROPOSED     pendiente de aprobación humana en la consola del hub" ;;
          esac ;;
        404)
          echo "$pidv  ?            el hub no expone la consulta de propuestas: instancia sin soporte (hub#113 pendiente)" ;;
        401|403)
          echo "$pidv  ?            token inválido o sin permiso ($status): habla con el ADMIN" ;;
        *)
          echo "$pidv  ?            OFFLINE: no se pudo consultar (status $status); se conserva el estado local" ;;
      esac
      continue
    fi
    echo "${pidv:-$cid}  $st"
  done
  rm -f "$tmp"
  return $OPS_RC_OK
}

# ── graph-sync ───────────────────────────────────────────────────────────────────────
# [EP-OR-17] Hasta ahora el grafo del hub dejaba de evolucionar tras el import inicial de
# ADMIN: las unidades que el plan añadía después no tenían por dónde entrar, y TODOS los
# eventos de un slice cuya épica no está en el grafo rebotan con «la épica no existe en el
# grafo del proyecto». Este carril lo cierra sin regalarle al agente la potestad de mutar el
# grafo: el arnés PROPONE el bundle, el hub calcula el delta y un humano aprueba en la consola.

# _graph_sync_bundle <fichero-bundle> — imprime `{"epics":[…]}` proyectado al contrato del
# carril (`GraphSyncBundle` del hub, event_catalog.py: `extra="forbid"` y techos de tamaño), o ""
# con rc 2 (no cumple el contrato, un motivo por línea en stderr) / rc 5 (sin python3).
# El bundle lo construye `trycore-bonita grafo` desde docs/08-construccion/plan.md (tarea 9):
# aquí solo se descartan las claves de preparación (bundle_version, warnings…), se normaliza
# `layer` a MAYÚSCULA y se valida — lo que en el import de admin revisa un humano, aquí viaja
# solo, y el hub rechaza el grafo ENTERO ante una sola épica mal formada.
_graph_sync_bundle() {
  local f="$1"
  command -v python3 >/dev/null 2>&1 || {
    echo "⛔ sin python3: no se puede proyectar el bundle en local" >&2
    return $OPS_RC_OFFLINE
  }
  python3 - "$f" <<'PY'
import json,sys
LARGO={"code":50,"title":300,"files_scope":500,"depends_on":50,"release_line":100,
       "docs_ref":500,"openspec_change":200,"branch_base":200,"acceptance_ref":500}
MAX={"epics":200,"files_scope":200,"depends_on":50,"stories":100}
CAPAS={"FOUNDATIONAL","BUSINESS"}
try:
    raw=json.load(open(sys.argv[1]))
except Exception as e:
    print("⛔ el bundle no es un JSON legible: %s" % e, file=sys.stderr); raise SystemExit(2)
if not isinstance(raw,dict) or not isinstance(raw.get("epics"),list):
    print("⛔ el bundle debe ser un objeto con la lista `epics`", file=sys.stderr); raise SystemExit(2)
err=[]
def texto(v):
    return v if isinstance(v,str) else ""
def lista(v):
    return [x for x in v if isinstance(x,str)] if isinstance(v,list) else []
epicas={}
for e in raw["epics"]:
    if not isinstance(e,dict):
        err.append("una entrada de `epics` no es un objeto"); continue
    code=texto(e.get("code")).strip()
    if not code:
        err.append("una épica no tiene `code`"); continue
    if code in epicas:
        err.append("%s: código duplicado" % code); continue
    if len(code)>LARGO["code"]:
        err.append("%s: el `code` excede %d caracteres" % (code,LARGO["code"]))
    title=texto(e.get("title")).strip()
    if not title:
        err.append("%s: sin `title`" % code)
    elif len(title)>LARGO["title"]:
        err.append("%s: el `title` excede %d caracteres" % (code,LARGO["title"]))
    layer=texto(e.get("layer")).strip().upper()
    if layer not in CAPAS:
        err.append("%s: `layer` es %r y el contrato exige FOUNDATIONAL o BUSINESS" % (code,e.get("layer")))
    out={"code":code,"title":title,"layer":layer}
    for k in ("files_scope","depends_on"):
        xs=lista(e.get(k))
        if len(xs)>MAX[k]:
            err.append("%s: %d entradas en `%s` y el contrato admite %d" % (code,len(xs),k,MAX[k]))
        if any(not x or len(x)>LARGO[k] for x in xs):
            err.append("%s: una entrada de `%s` está vacía o excede %d caracteres" % (code,k,LARGO[k]))
        out[k]=sorted(set(xs))
    for k in ("release_line","docs_ref","openspec_change","branch_base"):
        v=texto(e.get(k))
        if v:
            if len(v)>LARGO[k]:
                err.append("%s: `%s` excede %d caracteres" % (code,k,LARGO[k]))
            out[k]=v
    if isinstance(e.get("priority"),int) and not isinstance(e.get("priority"),bool):
        out["priority"]=e["priority"]
    if isinstance(e.get("parallelizable"),bool):
        out["parallelizable"]=e["parallelizable"]
    hs=[]
    for h in e.get("stories") or []:
        if not isinstance(h,dict):
            err.append("%s: una historia no es un objeto" % code); continue
        hcode=texto(h.get("code") or h.get("id")).strip()
        htitle=texto(h.get("title")).strip()
        if not hcode or len(hcode)>LARGO["code"]:
            err.append("%s: una historia no tiene `code` o excede %d caracteres" % (code,LARGO["code"])); continue
        if not htitle or len(htitle)>LARGO["title"]:
            err.append("%s: la historia %s no tiene `title` o excede %d caracteres" % (code,hcode,LARGO["title"])); continue
        st={"code":hcode,"title":htitle}
        ref=texto(h.get("acceptance_ref"))
        if ref:
            if len(ref)>LARGO["acceptance_ref"]:
                err.append("%s: `acceptance_ref` de %s excede %d caracteres" % (code,hcode,LARGO["acceptance_ref"]))
            st["acceptance_ref"]=ref
        hs.append(st)
    if len(hs)>MAX["stories"]:
        err.append("%s: %d historias y el contrato admite %d por épica" % (code,len(hs),MAX["stories"]))
    out["stories"]=sorted(hs,key=lambda h:h["code"])
    epicas[code]=out
if not epicas and not err:
    err.append("el bundle no tiene ni una épica: no hay nada que proponer")
if len(epicas)>MAX["epics"]:
    err.append("%d épicas: el contrato admite %d como máximo" % (len(epicas),MAX["epics"]))
for code,e in sorted(epicas.items()):
    for dep in e["depends_on"]:
        if dep not in epicas:
            print("aviso: %s depende de %s, que no está en el bundle (el hub lo validará contra su grafo)" % (code,dep), file=sys.stderr)
if err:
    print("⛔ el bundle NO cumple el contrato del hub (no se envía nada):", file=sys.stderr)
    for x in err:
        print("  ⛔ %s" % x, file=sys.stderr)
    raise SystemExit(2)
json.dump({"epics":[epicas[c] for c in sorted(epicas)]}, sys.stdout, indent=2, ensure_ascii=False)
sys.stdout.write("\n")
PY
}

# _graph_sync_out <respuesta> <clave> — escalar de la respuesta del hub ("" si falta). Acepta
# tanto el cuerpo desnudo como el sobre `{"response": …}` con el que el carril directo guarda
# los acks, que es de donde lo lee este comando.
_graph_sync_out() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    r=(d.get("response") if isinstance(d.get("response"),dict) else d) or {}
    v=r.get(sys.argv[1])
    print("" if v is None else (v if isinstance(v,str) else json.dumps(v,ensure_ascii=False)))
except Exception:
    print("")
' "$2" 2>/dev/null
}

# _graph_sync_delta_render <delta-json> — resumen legible del delta que devuelve el hub. Es lo
# que el humano va a aprobar: enseñarlo aquí evita que el agente proponga a ciegas.
_graph_sync_delta_render() {
  command -v python3 >/dev/null 2>&1 || return 0
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not isinstance(d,dict):
    raise SystemExit(0)
print("delta propuesto: %d épicas nuevas · %d épicas con cambios · %d historias nuevas · %d historias con cambios"
      % (len(d.get("epics_added") or []), len(d.get("epics_changed") or []),
         len(d.get("stories_added") or []), len(d.get("stories_changed") or [])))
for e in (d.get("epics_added") or [])[:10]:
    print("  + %s %s" % (e.get("code",""), e.get("title","")))
for e in (d.get("epics_changed") or [])[:10]:
    print("  ~ %s (%s)" % (e.get("code",""), ", ".join(sorted((e.get("fields") or {}).keys()))))
' 2>/dev/null
}

cmd_graph_sync() {
  local file="" dry=0 pid bundle rc cid pfile n_epicas
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --dry-run) dry=1; shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$file" ]; then
    echo "uso: slice-ops.sh graph-sync --file bundle.json [--dry-run]" >&2
    echo "  bundle.json: la salida de \`trycore-bonita grafo\` (docs/08-construccion/plan.md)," >&2
    echo "  {\"epics\":[{code,title,layer,files_scope[],depends_on[],stories[]}]}." >&2
    return $OPS_RC_USAGE
  fi
  [ -f "$file" ] || { echo "⛔ no existe el bundle: $file" >&2; return $OPS_RC_USAGE; }

  # El bundle se proyecta ANTES de tocar nada: `--dry-run` sirve para revisarlo sin hub.
  bundle="$(_graph_sync_bundle "$file")"
  rc=$?
  if [ $rc -ne 0 ] || [ -z "$bundle" ]; then
    [ $rc -eq $OPS_RC_OFFLINE ] && return $OPS_RC_OFFLINE
    echo "⛔ el bundle no se envía: corrige docs/08-construccion/plan.md y vuelve a generarlo." >&2
    return $OPS_RC_USAGE
  fi
  if [ "$dry" = 1 ]; then
    printf '%s\n' "$bundle"
    echo "--dry-run: nada se ha enviado. Quita la opción para proponer el re-sync al hub." >&2
    return $OPS_RC_OK
  fi

  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || { echo "⛔ sin project_id en runtime.credentials: registra el agente (\`slice-ops.sh register\`)" >&2; return $OPS_RC_REJECTED; }

  cid="$(ops_graph_sync_cid)"
  # El cid es determinista, luego REUTILIZABLE: si el ledger se pierde o se limpia, el
  # contador vuelve atrás y el rastro local de un envío anterior con ese mismo cid (su ack o
  # su apartado) seguiría en disco. Leerlo haría que este comando reportara el resultado de
  # una propuesta que NO acaba de enviar. Se retira antes de encolar: el hub sigue
  # deduplicando por cid igualmente, así que borrar el rastro local no duplica nada.
  rm -f "$(runtime_outbox_dir)/acks/${cid}.json" 2>/dev/null
  rm -f "$(runtime_outbox_dir)/rejected/"*"${cid}.json" 2>/dev/null
  pfile="$(ops_tmpjson "{\"bundle\":$bundle}")" || return $OPS_RC_OFFLINE
  # El `1` pide el estampado de `graph_version` AL DESPACHAR: un re-sync que espera en la cola
  # offline debe salir con la versión vigente en ese momento, no con la de ayer. El `$cid` fija
  # la identidad: el reintento tras un 409 la reusa y el hub deduplica.
  cid="$(runtime_enqueue_direct graph_sync_proposed POST "$(ops_path_graph_sync_proposals "$pid")" "$pfile" 1 "$cid")"
  rm -f "$pfile"
  if [ -z "$cid" ]; then
    echo "⛔ no se pudo encolar el re-sync (outbox no escribible): reintenta." >&2
    return $OPS_RC_OFFLINE
  fi
  n_epicas="$(printf '%s' "$bundle" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["epics"]))' 2>/dev/null || echo 0)"
  ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"QUEUED\",\"proposal_id\":null,\"epics\":$n_epicas}"

  _graph_sync_despachar "$cid"
}

# _graph_sync_despachar <cid> — despacha, interpreta el resultado y, ante un grafo rancio,
# refresca la proyección y reintenta UNA vez.
#
# El reintento vive AQUÍ y no en el despachador porque `runtime-client.sh` es agnóstico al
# dominio: no sabe qué es un bundle ni cuándo vale la pena volver a intentarlo. Y re-estampar
# con la versión nueva ES «recalcular el bundle contra la versión que devuelve el hub»: el
# bundle no depende de la versión del grafo, solo el sello que lo acompaña.
_graph_sync_despachar() {
  local cid="$1" intento=1 ack reason id_prop delta
  while :; do
    runtime_dispatch_outbox >/dev/null 2>&1
    ack="$(ops_epic_ack_read "$cid")"
    if [ -n "$ack" ]; then
      if [ "$(_graph_sync_out "$ack" empty_delta)" = "true" ]; then
        # HU-OR-72 E2: no es un error ni una propuesta — el bundle coincide con el grafo
        # vigente. Se cierra la entrada del ledger para que `graph-sync-status` no vaya a
        # preguntar por una propuesta que el hub nunca creó.
        ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"EMPTY_DELTA\"}"
        echo "el grafo del hub ya está al día: no hay cambios que proponer."
        return $OPS_RC_OK
      fi
      id_prop="$(_graph_sync_out "$ack" id)"
      delta="$(_graph_sync_out "$ack" delta)"
      ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"PROPOSED\",\"proposal_id\":$(ops_json_str "$id_prop")}"
      echo "re-sync propuesto: ${id_prop:-sin identificador en la respuesta}"
      [ -n "$delta" ] && _graph_sync_delta_render "$delta"
      echo "Queda en PROPOSED: NADA se ha aplicado al grafo hasta que un humano lo apruebe en"
      echo "la consola del hub. Sigue el veredicto con \`slice-ops.sh graph-sync-status\`."
      return $OPS_RC_OK
    fi
    reason="$(ops_epic_rejected_reason "$cid")"
    if [ -n "$reason" ]; then
      ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"FAILED\",\"reason\":$(ops_json_str "$reason")}"
      case "$reason" in
        *"HTTP 404"*|*404*)
          # Anti-oráculo (HU-OR-72 E4): el hub responde lo MISMO para «no existe» y «no es
          # tuyo». Afirmar una de las dos causas mandaría a buscar el problema equivocado.
          echo "⛔ el hub respondió 404. Son dos causas indistinguibles POR DISEÑO: o el proyecto" >&2
          echo "  no existe, o no es el tuyo (el hub no confirma cuál para no filtrar proyectos" >&2
          echo "  ajenos). Verifica el project_id de runtime.credentials y que el hub tenga" >&2
          echo "  la superficie de re-sync (EP-OR-17)." >&2 ;;
        *) echo "⛔ el hub rechazó el re-sync: $reason" >&2 ;;
      esac
      return $OPS_RC_REJECTED
    fi
    # Sigue en la cola. Si fue por grafo rancio, el despachador dejó el marcador de desfase: se
    # refresca la proyección y se reintenta UNA vez con la versión nueva.
    if [ "$intento" = 1 ] && [ -n "$(runtime_graph_status_read)" ] && [ "$(runtime_graph_status_read)" != "{}" ]; then
      intento=2
      echo "⚠ el hub dice que nuestro grafo va rancio: se refresca el contexto y se reintenta una vez." >&2
      agent_context_fetch_and_cache >/dev/null 2>&1 || \
        echo "⚠ no se pudo refrescar /agent/context: el reintento sale con la versión que haya" >&2
      # El despacho lleva mutex y estado de backoff: sin limpiarlo, el segundo intento cedería
      # el turno y el reintento no ocurriría en este proceso.
      rm -f "$(runtime_outbox_dir)/.dispatch-state.json" 2>/dev/null
      continue
    fi
    echo "re-sync encolado: $cid"
    echo "PENDIENTE: se despachará solo (el daemon de heartbeat lo lleva). Sin conexión aún, o el"
    echo "daemon estaba drenando la cola en este instante. \`slice-ops.sh graph-sync-status\` lo sigue."
    return $OPS_RC_OFFLINE
  done
}

# ── graph-sync-status ────────────────────────────────────────────────────────────────
# [EP-OR-17] El motivo del rechazo lo escribe el ADMIN precisamente para que lo lea la terminal
# que propuso: sin este subcomando el veredicto humano se queda en la consola del hub y el
# agente vuelve a proponer exactamente lo mismo. Informativo: rc 0 siempre en runtime, pase lo
# que pase — es una consulta, y fallar aquí no arregla nada.
cmd_graph_sync_status() {
  local only="" pid entries n i cid pidv st resp status reason ack
  while [ $# -gt 0 ]; do
    case "$1" in
      --id) only="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  pid="$(runtime_field project_id)"
  entries="$(ops_graph_sync_ledger_read)"
  n="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("proposals") or []))' 2>/dev/null || echo 0)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  if [ "$n" = 0 ]; then
    echo "no hay ninguna propuesta de re-sync registrada en esta terminal."
    echo "Propón una con \`slice-ops.sh graph-sync --file epics.json\`."
    return $OPS_RC_OK
  fi
  i=0
  while [ "$i" -lt "$n" ]; do
    cid="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(json.load(sys.stdin)["proposals"][int(sys.argv[1])].get("client_event_id") or "")' "$i" 2>/dev/null)"
    pidv="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(json.load(sys.stdin)["proposals"][int(sys.argv[1])].get("proposal_id") or "")' "$i" 2>/dev/null)"
    st="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(json.load(sys.stdin)["proposals"][int(sys.argv[1])].get("status") or "")' "$i" 2>/dev/null)"
    i=$((i + 1))
    [ -z "$only" ] || [ "$only" = "$pidv" ] || [ "$only" = "$cid" ] || continue
    if [ -z "$pidv" ]; then
      # Todavía sin identificador del hub: el estado lo dicta el carril directo local, no la red.
      ack="$(ops_epic_ack_read "$cid")"
      reason="$(ops_epic_rejected_reason "$cid")"
      if [ "$st" = "EMPTY_DELTA" ]; then
        echo "$cid  EMPTY_DELTA  (el grafo ya estaba al día: el hub no creó ninguna propuesta)"
      elif [ -n "$reason" ]; then
        echo "$cid  FAILED  $reason"
      elif [ -n "$ack" ]; then
        echo "$cid  PROPOSED (ack recibido, sin identificador legible en la respuesta)"
      else
        echo "$cid  ${st:-QUEUED}  (pendiente de despacho: el daemon de heartbeat la lleva)"
      fi
      continue
    fi
    resp="$(runtime_get "$(ops_path_graph_sync_proposal "$pid" "$pidv")")"
    status="$(runtime_http_status)"
    case "$status" in
      200) _graph_sync_status_render "$cid" "$pidv" "$resp" ;;
      404)
        # HU-OR-73 E5: «no existe» y «es de otro proyecto» son el MISMO cuerpo, bit a bit.
        echo "$pidv  DESCONOCIDA para el hub (o es de otro proyecto: son indistinguibles)" ;;
      *)
        echo "$pidv  ${st:-?}  (el hub no respondió, HTTP $status: se muestra el último estado conocido)" ;;
    esac
  done
  return $OPS_RC_OK
}

# _graph_sync_status_render <cid> <proposal_id> <respuesta> — pinta el veredicto y lo persiste
# en el ledger. La persistencia va aquí y no en el llamador porque el estado del hub SOLO se
# conoce al leer la respuesta: guardarlo fuera obligaría a re-parsearla.
_graph_sync_status_render() {
  local cid="$1" pidv="$2" resp="$3" st reason applied
  st="$(_graph_sync_out "$resp" status)"
  reason="$(_graph_sync_out "$resp" reject_reason)"
  applied="$(_graph_sync_out "$resp" graph_version_applied)"
  case "$st" in
    APPROVED)
      echo "$pidv  APPROVED  (grafo del hub en v${applied:-?})"
      echo "         nada más que hacer: las historias nuevas entran solas al reparto del claim." ;;
    REJECTED)
      echo "$pidv  REJECTED  ${reason:-sin motivo registrado}"
      echo "         corrige docs/08-construccion/plan.md y vuelve a proponer con \`graph-sync\`." ;;
    PROPOSED)
      echo "$pidv  PROPOSED  (esperando aprobación humana en la consola del hub)" ;;
    *)
      echo "$pidv  ${st:-?}" ;;
  esac
  ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":$(ops_json_str "${st:-PROPOSED}"),\"reject_reason\":$(ops_json_str "$reason"),\"graph_version_applied\":$(ops_json_str "$applied")}"
}

# ── status ───────────────────────────────────────────────────────────────────────────
# Informe local del agente: proyecto (con sus hechos), unidad, gates, wiring, contexto,
# lease, cola y rechazados. Es INFORMATIVO: rc 0 siempre, pase lo que pase.
cmd_status() {
  local refresh=1 mode sid pend lock age
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-refresh) refresh=0; shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  # [#74] `status` conserva el fallback a propósito — es la herramienta de diagnóstico de un
  # worktree que todavía no se dio de alta, y negarle la lectura lo dejaría a ciegas. Pero se
  # dice en la primera línea de quién es el estado que está mirando: sin el banner, un informe
  # heredado es indistinguible de uno propio, y es exactamente así como se llega a creer que
  # se tiene un lease que en realidad es de otro agente.
  if config_is_inherited_root; then
    echo "identidad:    ⚠ HEREDADA del clon principal ($(config_main_clone_root)) — solo lectura"
    echo "              lo de abajo es el estado de ESE agente, no del tuyo. Antes de reclamar"
    echo "              o reportar: \`slice-ops.sh register\` con un token propio del ADMIN."
  fi
  echo "modo:         $mode (el estado de la unidad vive en el hub)"
  [ "$refresh" = 1 ] && { agent_context_fetch_and_cache >/dev/null 2>&1 || echo "aviso:        no se pudo refrescar /agent/context (se muestra la caché)"; }
  echo "proyecto:     $(runtime_field project_id)  ·  agente: $(runtime_field agent_key)"
  # [I4] El hub rechazó el token al despachar la cola: los eventos se conservan hasta re-registrar.
  if [ -f "$(runtime_auth_status_path)" ]; then
    echo "credenciales: ⛔ token no válido: register --force (HTTP $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status") or "?")' "$(runtime_auth_status_path)" 2>/dev/null || echo "?") al despachar)"
    echo "              la cola se conserva y drena en cuanto el árbol tenga un token válido"
  fi
  echo "hechos:       project_kind=$(projection_get project.project_kind "?")  ·  harness_phase=$(projection_get project.harness_phase "?")  ·  foundation_done=$(projection_get project.foundation_done false)"
  local mw
  mw="$(ops_micro_work_id)"
  [ -n "$mw" ] && echo "micro-work:   $mw  ·  fase $(claim_cache_get phase "?")  ·  rama $(claim_cache_get branch "?")"
  sid="$(ops_slice_id)"
  if [ -z "$sid" ]; then
    echo "unidad:       ninguna reclamada"
  else
    echo "unidad:       $(projection_get active_slice.epic_code "?")  ·  slice $sid  ·  fase $(projection_get active_slice.phase "?")"
    echo "gates:        $(projection_get active_slice.gates '{}')"
    echo "wiring:       $(projection_get active_slice.wiring_failing '[]')"
    # [Hub real] /agent/context no trae la rama: la de trabajo es el `branch_base` del claim del MISMO slice; la de
    # integración, la primera protegida de la política (de ella se parte y contra ella va el PR).
    local rama
    rama="$(projection_get active_slice.branch "")"
    [ -z "$rama" ] && [ "$(claim_cache_get slice_id "")" = "$sid" ] && rama="$(claim_cache_get branch_base "")"
    echo "rama:         ${rama:-?}  ·  integración: $(config_integration_branch)  ·  change: $(projection_get active_slice.openspec_change "?")"
  fi
  lock="$(runtime_lock_manifest_hash)"
  age="$(projection_age_seconds)"
  if projection_is_stale; then
    echo "contexto:     $lock  ⚠ proyección sin refrescar (${age}s)"
  else
    echo "contexto:     $lock  ✓ v$(projection_get context.version "?") (${age}s)"
  fi
  # [#63] La versión de grafo es la foto del BACKLOG. Solo se menciona si el hub versiona:
  # inventarla en una instancia antigua sería ruido sin significado.
  local gv gs gserver
  gv="$(projection_get context.graph_version "")"
  if [ -n "$gv" ]; then
    gs="$(runtime_graph_status_read)"
    gserver="$(printf '%s' "$gs" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("server") or "")' 2>/dev/null)"
    # [Ronda de arreglo 1, Important 3] La comparación es «servidor MAYOR que local», no
    # «distinto»: un marcador de desfase que se quedó pegado con un `server` viejo (porque el
    # carril directo no lo limpiaba al despachar con éxito — ya corregido) podía apuntar a una
    # versión POR DEBAJO de la local, y `!=` mentía diciendo «por detrás» con el local por
    # delante. `2>/dev/null` deja la comparación fail-open si algún valor no es entero.
    if [ -n "$gserver" ] && [ "$gserver" -gt "$gv" ] 2>/dev/null; then
      echo "grafo:        v$gv  ⚠ por detrás del hub (v$gserver): refresca antes de reclamar o proponer"
    else
      echo "grafo:        v$gv"
    fi
  fi
  echo "lease:        expira $(projection_get lease.expires_at "?")"
  local hbf hbstatus
  hbf="$(config_root)/.claude/state/heartbeat-status.json"
  if [ -f "$hbf" ]; then
    grep -q '"lease_lost": *true' "$hbf" 2>/dev/null \
      && echo "              ⚠ lease perdido: haz checkpoint y vuelve a reclamar"
    # [#61] Una caché vieja porque la red está caída NO es lo mismo que una caché vieja
    # porque nadie la pidió: la primera exige no cerrar gates a ciegas.
    if grep -q '"context_stale": *true' "$hbf" 2>/dev/null; then
      hbstatus="$(command -v python3 >/dev/null 2>&1 && python3 - "$hbf" <<'PY' 2>/dev/null
import json,sys
try:
    print(json.load(open(sys.argv[1])).get("last_context_status"))
except Exception:
    print("?")
PY
)"
      echo "              ⚠ el heartbeat no pudo refrescar /agent/context (último intento: ${hbstatus:-?})"
      echo "                se opera con la última proyección buena; no cierres gates a ciegas"
    fi
  fi
  pend="$(find "$(runtime_outbox_dir)" -maxdepth 1 -name '*.json' ! -name '.dispatch-state.json' 2>/dev/null | wc -l | tr -d ' ')"
  echo "cola:         $pend evento(s) pendiente(s) de despacho"
  # [issue #52] outbox/rejected/ era invisible: la cola mostraba 0 pendientes y parecía
  # éxito mientras el hub había descartado eventos (p.ej. un slice_archived sin la cadena
  # de fases). Se reporta el conteo y la razón del rechazo más reciente.
  local rej rejinfo
  rej="$(find "$(runtime_outbox_dir)/rejected" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${rej:-0}" -gt 0 ] 2>/dev/null; then
    echo "rechazados:   ⚠ $rej evento(s) en outbox/rejected/ — el hub los descartó, NO se reenvían"
    rejinfo="$(command -v python3 >/dev/null 2>&1 && python3 - "$(runtime_outbox_dir)/rejected" <<'PY' 2>/dev/null
import json,glob,os,sys
files=sorted(glob.glob(os.path.join(sys.argv[1],"*.json")))
if files:
    try:
        d=json.load(open(files[-1]))
    except Exception:
        d={}
    print("%s — %s" % (d.get("type") or d.get("event_type") or "?",
                       d.get("rejected_reason") or "razón no registrada (apartado por un cliente anterior)"))
PY
)"
    [ -n "$rejinfo" ] && echo "              último: $rejinfo"
    echo "              revisa la causa y re-emite el hecho corregido (un rechazo no se reintenta solo)"
  else
    echo "rechazados:   ninguno"
  fi
  echo "nudges:       $(projection_get nudges '[]')"
  return $OPS_RC_OK
}

# ── helpers para escalate ────────────────────────────────────────────────────────────

# _ops_evidence_json <texto> <fichero> — evidencia para escalate (texto preferentemente,
# fichero si es grande).
# _ops_evidence_file_ok <fichero> <etiqueta> — rc 0 si el fichero de evidencia existe y tiene texto;
# si no, mensaje y OPS_RC_USAGE, ANTES de la red. Una evidencia vacía es un rechazo seguro del hub
# («passing ⇒ evidence obligatoria», domain.py) que además no llega a verse: por la cola acaba en
# outbox/rejected/ minutos después. P. ej. un log de `mvn -q` en verde puede estar vacío.
_ops_evidence_file_ok() {
  local f="$1" etiqueta="$2"
  if [ ! -f "$f" ]; then
    echo "⛔ ${etiqueta}: no existe el fichero de evidencia «${f}»" >&2
    return $OPS_RC_USAGE
  fi
  if ! grep -q '[^[:space:]]' "$f" 2>/dev/null; then
    echo "⛔ ${etiqueta}: el fichero de evidencia «${f}» está vacío. Una evidencia vacía la rechaza el hub:" >&2
    echo "  escribe en él la salida del comando que lo prueba (comando, código de salida, resumen)." >&2
    return $OPS_RC_USAGE
  fi
  return $OPS_RC_OK
}

_ops_evidence_json() {
  local txt="$1" file="$2"
  if [ -n "$file" ]; then
    ops_json_str_file "$file"
  else
    ops_json_str "$txt"
  fi
}

# ── escalate ─────────────────────────────────────────────────────────────────────────
# Reportar un bloqueo es acto de agente; DECIDIR qué hacer con él es humano (spec §2).
# El evento deja el rastro en el runtime; la resolución se pide por el canal humano.
# La nota de gobierno SOLO se imprime si el evento de verdad quedó registrado (mismo patrón
# de fallo que _fact_machine_emit): un agente jamás debe creer que escaló algo que se perdió.
cmd_escalate() {
  local razon="" file="" gate="" sid payload
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --gate) gate="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) [ -z "$razon" ] && razon="$1"; shift ;;
    esac
  done
  if [ -z "$razon" ] && [ -z "$file" ]; then
    echo "uso: slice-ops.sh escalate «razón» | --file F [--gate G]" >&2
    return $OPS_RC_USAGE
  fi
  # [#44] El catálogo v2 la llama `slice_escalated` y su payload es EXACTAMENTE {cause}
  # (extra="forbid"): gate y fase viajan DENTRO del texto de la causa, no como claves.
  local prefix="" phase tmptxt
  phase="$(projection_get active_slice.phase "")"
  [ -n "$gate" ] && prefix="[gate: ${gate}] "
  [ -n "$phase" ] && prefix="${prefix}[fase: ${phase}] "
  tmptxt="$(mktemp)" || return $OPS_RC_OFFLINE
  { printf '%s' "$prefix"; if [ -n "$file" ] && [ -f "$file" ]; then cat "$file"; else printf '%s' "$razon"; fi; } > "$tmptxt"
  payload="{\"cause\":$(ops_json_str_file "$tmptxt" "$OPS_MAX_TEXT")}"
  rm -f "$tmptxt"
  sid="$(ops_slice_id)"
  # slice_escalated es de ámbito slice (slice_id obligatorio): sin slice el hub lo
  # rechazaría elemento a elemento — mejor un fallo local accionable que ruido en rejected/.
  if [ -z "$sid" ]; then
    echo "⛔ sin slice activo: slice_escalated exige slice_id (catálogo v2) y el hub rechazaría el evento." >&2
    echo "  Reclama trabajo primero o reporta el bloqueo por el PR / la consola del hub." >&2
    return $OPS_RC_NO_SLICE
  fi
  if ! _ops_emit_event slice_escalated "$payload" "$sid"; then
    echo "⚠ la escalada no se pudo registrar (outbox no escribible u otro fallo local): repórtala por el PR mientras tanto" >&2
    return $OPS_RC_OFFLINE
  fi
  echo "escalada registrada (evento encolado)"
  echo "La DECISIÓN es humana (gobierno, spec §2): recortar, diferir o desbloquear lo acuerda el equipo"
  echo "en la consola del hub o en el PR. El arnés no decide por ti ni degrada el alcance."
  return $OPS_RC_OK
}

# ── Helpers comunes de los subcomandos que transicionan ──────────────────────────────
# _ops_require_slice — id del slice activo o rc 4 con mensaje accionable.
_ops_require_slice() {
  local sid
  sid="$(ops_slice_id)"
  if [ -z "$sid" ]; then
    echo "⛔ no hay unidad activa en la caché de proyección: reclama primero (\`slice-ops.sh claim [--unidad <código>]\`)" >&2
    return $OPS_RC_NO_SLICE
  fi
  echo "$sid"
  return $OPS_RC_OK
}

# _ops_post_or_queue <path> <payload> <tipo_evento> <slice_id> <etiqueta> [queue_payload]
# Camino común de los actos primarios: POST y, si el servidor no está, encolar el hecho.
# Rechazo del servidor (409/422/401/403) => NUNCA se encola (no se reintenta lo rechazado).
# [#44] `queue_payload` (opcional, default = payload): el cuerpo del endpoint síncrono y
# el payload del catálogo pueden diferir (p.ej. el checkpoint lleva slice_id en el body
# de POST /checkpoints, pero el catálogo lo prohíbe dentro del payload del evento).
# [I1] El POST y su reencolado son UN acto: el `client_event_id` se crea ANTES del POST, viaja en el
# cuerpo síncrono (VerdictIn, CheckpointIn y SubmitIn lo declaran) y el evento encolado lleva el MISMO.
# Un hub lento que aplica y responde después del timeout ve el drenaje como duplicado y no cuenta el
# acto dos veces (un FAIL doble gastaba dos reintentos y escalaba la unidad tras un único fallo real).
# [I2] Orden FIFO tras una caída: si la cola tiene pendientes, se drena una vez ANTES del POST; si siguen
# quedando pendientes de ESTE slice, el acto se encola detrás en vez de adelantarlos (un `dod` síncrono
# que llega antes que el `wiring_verified` encolado es un 409 seguro del hub).
_ops_post_or_queue() {
  local path="$1" payload="$2" tipo="$3" sid="$4" etiqueta="$5" queue_payload="${6:-$2}" resp status cid pend
  cid="$(ops_new_cid)"
  if [ "$(ops_outbox_pending)" -gt 0 ] 2>/dev/null; then
    RUNTIME_DISPATCH_FORCE=1 runtime_dispatch_outbox >/dev/null 2>&1
    # [Residual I2+I4] Si el drenaje chocó con un 401/403, la cola se conserva (I4) pero el token no sirve: encolar
    # detrás con rc 5 («se entrega al drenar») haría seguir al agente con un token revocado. Es un rechazo: rc 6.
    if [ -f "$(runtime_auth_status_path)" ]; then
      echo "⛔ token no válido: register --force — el hub rechazó el token al drenar la cola (HTTP $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status") or "?")' "$(runtime_auth_status_path)" 2>/dev/null || echo "?"))." >&2
      echo "  $etiqueta NO se envió ni se encoló. Pide un token nuevo al ADMIN y corre \`slice-ops.sh register --force\`;" >&2
      echo "  la cola pendiente se conserva y drena después. Vuelve a emitir este hecho tras registrarte." >&2
      return $OPS_RC_REJECTED
    fi
    pend="$(ops_outbox_pending "$sid")"
    if [ "$pend" -gt 0 ] 2>/dev/null; then
      if _ops_queue_fact "$tipo" "$queue_payload" "$sid" "$cid"; then
        echo "PENDIENTE: $etiqueta encolado detrás de $pend hecho(s) de esta unidad que el hub aún no recibió"
        echo "  (orden FIFO: adelantarlos daría un rechazo falso). Se entrega al drenar la cola."
      else
        echo "⚠ $etiqueta NO se pudo encolar (outbox no escribible u otro fallo local) — se perderá" >&2
      fi
      return $OPS_RC_OFFLINE
    fi
  fi
  resp="$(runtime_post "$path" "$(ops_json_set_cid "$payload" "$cid")")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202)
      agent_context_fetch_and_cache >/dev/null 2>&1
      echo "$etiqueta registrado en el runtime"
      return $OPS_RC_OK ;;
    422)
      echo "⛔ 422 el servidor rechazó $etiqueta: $resp" >&2
      echo "  Compuerta mecánica funcionando: NO reintentes; corrige la causa y vuelve a medir." >&2
      return $OPS_RC_REJECTED ;;
    409)
      # [I2] El 409 no es siempre el lease: el hub dice por qué en `detail` (orden de gates, ratchet,
      # titularidad…), y eso es lo que el agente necesita para decidir.
      echo "⛔ 409 el hub rechazó $etiqueta: $(_claim_409_text "$resp")" >&2
      echo "  Si el motivo es el lease (expirado o de otro agente): haz checkpoint y vuelve a reclamar." >&2
      echo "  Si es una precondición del hub: corrige la causa y vuelve a medir; no reintentes a ciegas." >&2
      return $OPS_RC_REJECTED ;;
    401|403)
      echo "⛔ token inválido o revocado ($status): pide un token nuevo al ADMIN." >&2
      return $OPS_RC_REJECTED ;;
    *)
      if _ops_queue_fact "$tipo" "$queue_payload" "$sid" "$cid"; then
        echo "OFFLINE: $etiqueta encolado (tipo protegido, se entrega al reconectar)"
      else
        echo "⚠ OFFLINE: $etiqueta NO se pudo encolar (outbox no escribible u otro fallo local) — se perderá" >&2
      fi
      return $OPS_RC_OFFLINE ;;
  esac
}

# _ops_queue_fact <tipo> <payload> <slice_id> <client_event_id> — encola el hecho con ESE id. rc 0/1.
_ops_queue_fact() {
  local pfile rc
  pfile="$(ops_tmpjson "$2")" || return 1
  ops_enqueue_from_file "$1" "$pfile" "$3" "$4"
  rc=$?
  rm -f "$pfile"
  return $rc
}

# ── phase ────────────────────────────────────────────────────────────────────────────
# [issue #52] El hub modela la fase con `phase_advanced {to}` de ORDEN ESTRICTO
# (domain.py:400-407: solo la fase siguiente exacta) y `slice_archived` exige phase == pr
# (domain.py:499-500). Este subcomando emite la cadena que falte DESDE la fase conocida
# (proyección ∪ cola pendiente, ops_known_phase) HASTA <to>: nada si ya está (idempotente),
# la cadena completa si hay huecos. Va SIEMPRE por la cola (no hay endpoint síncrono de fase).

# _phase_chain_enqueue <sid> <desde_idx> <hasta_idx> — encola phase_advanced por paso.
# rc 0 si toda la cadena quedó encolada; rc 5 si algún eslabón no se pudo encolar (y se
# corta ahí: encolar eslabones posteriores con un hueco delante era rechazo garantizado).
_phase_chain_enqueue() {
  local sid="$1" i="$2" hasta="$3" step pfile
  i=$((i + 1))
  while [ "$i" -le "$hasta" ]; do
    step="$(ops_phase_at "$i")"
    pfile="$(ops_tmpjson "{\"to\":\"$step\"}")" || return $OPS_RC_OFFLINE
    if ! ops_enqueue_from_file phase_advanced "$pfile" "$sid"; then
      rm -f "$pfile"
      echo "⚠ phase_advanced → «${step}» NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
      return $OPS_RC_OFFLINE
    fi
    rm -f "$pfile"
    i=$((i + 1))
  done
  return $OPS_RC_OK
}

cmd_phase() {
  local to="${1:-}" sid base bidx tidx rc
  if [ -z "$to" ]; then
    echo "uso: slice-ops.sh phase <to>   (fases: $OPS_SLICE_PHASES)" >&2
    return $OPS_RC_USAGE
  fi
  tidx="$(ops_phase_idx "$to")"
  if [ "$tidx" -lt 0 ]; then
    echo "⛔ fase desconocida «${to}». Canónicas: $OPS_SLICE_PHASES" >&2
    echo "  (la fase terminal archived no se reporta por aquí: la produce \`slice-ops.sh archive\`)" >&2
    return $OPS_RC_REJECTED
  fi
  # La base es la fase que el SERVIDOR conoce: refresco de la proyección a mejor esfuerzo
  # (fail-open: sin red se sigue con la caché y con los pendientes de la cola).
  agent_context_fetch_and_cache >/dev/null 2>&1
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  base="$(ops_known_phase "$sid")"
  bidx="$(ops_phase_idx "$base")"; [ "$bidx" -ge 0 ] || bidx=0
  if [ "$bidx" -ge "$tidx" ]; then
    echo "fase «${to}» ya reportada (server-side o pendiente en la cola: ${base}) — nada que emitir"
    return $OPS_RC_OK
  fi
  [ $((tidx - bidx)) -gt 1 ] && echo "⚠ el slice estaba en «${base}» server-side: se emite la cadena completa hasta «${to}» (orden estricto del hub, sin saltos)"
  _phase_chain_enqueue "$sid" "$bidx" "$tidx"
  rc=$?
  [ "$rc" = "$OPS_RC_OK" ] || return $rc
  echo "fase reportada: ${base} → ${to} ($((tidx - bidx)) evento(s) phase_advanced encolados; se entregan al reconectar)"
  return $OPS_RC_OK
}

# ── gate ─────────────────────────────────────────────────────────────────────────────
# Un veredicto es un HECHO MEDIDO: acto de agente (spec §2). El nombre del gate y el
# estado se validan en el cliente (compuerta barata, sin round-trip); la compuerta real,
# que conoce el orden y las precondiciones, es el servidor.
cmd_gate() {
  local gate="${1:-}" estado="${2:-}" evfile="" ev="" causa="" sid evjson payload
  if [ -z "$gate" ] || [ -z "$estado" ]; then
    echo "uso: slice-ops.sh gate <nombre> <pass|fail|na> [--evidence «texto» | --evidence-file F] [--causa «texto»]" >&2
    return $OPS_RC_USAGE
  fi
  shift 2
  while [ $# -gt 0 ]; do
    case "$1" in
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --causa|--cause) causa="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case " $OPS_SLICE_GATES " in
    *" $gate "*) : ;;
    *) echo "⛔ gate desconocido «${gate}». Canónicos: $OPS_SLICE_GATES" >&2; return $OPS_RC_REJECTED ;;
  esac
  case "$estado" in
    pass|fail|na) : ;;
    *) echo "⛔ estado inválido «${estado}» (pass|fail|na)" >&2; return $OPS_RC_REJECTED ;;
  esac
  # [#44] El hub no tiene veredicto «na»: cualquier verdict ≠ PASS/FAIL es bloqueo
  # (domain.py, invariante 5) — emitirlo era rechazo garantizado. El gate no aplicable
  # simplemente no se reporta; queda documentado en el PR.
  if [ "$estado" = "na" ]; then
    echo "veredicto «na» de «${gate}»: el catálogo del hub no lo admite (solo PASS/FAIL) — no se reporta."
    echo "Documenta la no-aplicabilidad del gate en el PR; en el hub el gate queda sin evaluar."
    return $OPS_RC_OK
  fi
  # [#44] Contrato real del hub: la clave es `verdict` (VerdictIn y el catálogo
  # GateVerdict) y el reducer solo promueve con "PASS"/"FAIL" en MAYÚSCULA
  # (domain.py:423-431) — `status:"pass"` era rechazo en el sync Y en la cola.
  local verdict
  case "$estado" in
    pass) verdict="PASS" ;;
    fail) verdict="FAIL" ;;
  esac
  if [ -n "$evfile" ]; then
    _ops_evidence_file_ok "$evfile" "gate «${gate}»" || return $OPS_RC_USAGE
  fi
  evjson="$(_ops_evidence_json "$ev" "$evfile")"
  payload="{\"gate\":$(ops_json_str "$gate"),\"verdict\":$(ops_json_str "$verdict"),\"evidence\":$evjson"
  # [M4] Tumbar un gate que YA pasó exige `cause` en el hub (ratchet, domain.py:526-528): sin ella el FAIL
  # de una regresión hallada tras el PASS era un 409. La causa es `--causa` o, si no se da, la propia
  # evidencia (lo que el verificador midió). VerdictIn y el catálogo GateVerdict la admiten (≤ 2000).
  if [ "$verdict" = FAIL ]; then
    if [ -n "$causa" ]; then
      local tcausa
      tcausa="$(mktemp)" || return $OPS_RC_OFFLINE
      printf '%s' "$causa" > "$tcausa"
      payload="$payload,\"cause\":$(ops_json_str_file "$tcausa")"
      rm -f "$tcausa"
    elif [ "$evjson" != '""' ]; then
      payload="$payload,\"cause\":$evjson"
    fi
  fi
  payload="$payload}"
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  _ops_post_or_queue "$(ops_path_verdicts "$sid")" "$payload" gate_verdict "$sid" "el veredicto de «${gate}»"
}

# ── submit ───────────────────────────────────────────────────────────────────────────
cmd_submit() {
  local pr="" change="" sid payload
  while [ $# -gt 0 ]; do
    case "$1" in
      --pr-url) pr="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --openspec-change) change="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  # [#44] El catálogo v2 no admite ningún campo en slice_submitted (extra="forbid") y [I6] `SubmitIn` solo declara
  # `client_event_id`: ni el POST síncrono ni el evento encolado llevan pr_url/openspec_change (el hub los
  # descartaba). Se aceptan como opciones por la prosa de las skills; viven en el PR.
  payload="{}"
  _ops_post_or_queue "$(ops_path_submit "$sid")" "$payload" slice_submitted "$sid" "el submit del slice" "{}"
}

# ── archive ──────────────────────────────────────────────────────────────────────────
# SIEMPRE por la cola, también con el runtime vivo: `opsx:archive` corre dentro del PR,
# en el momento menos oportuno para una llamada síncrona, y el evento es idempotente por
# `client_event_id`. El tipo está protegido de la cota (Task 1): un archivado no se evicta.
cmd_archive() {
  # --pr-url y --openspec-change se aceptan por la prosa de las skills, pero NO viajan (el
  # catálogo no admite campos en slice_archived; ver abajo). Cualquier otra opción se ignora.
  local sid pfile
  while [ $# -gt 0 ]; do
    case "$1" in
      --pr-url|--openspec-change) [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  # [issue #52] Catch-up de fase: `slice_archived` exige phase == pr en el hub
  # (domain.py:499-500) y el orden de fases es estricto — un pipeline que no reportó
  # `phase` dejaba el slice en dor server-side y el archivado caía a rejected/ EN SILENCIO
  # (piloto 2026-08-28: slices «en construcción» con el PR ya mergeado). Antes de emitir el
  # archivado se completa la cadena phase_advanced que falte hasta pr — el workaround del
  # piloto, hecho sistema. Sin refresco de red: la base sale de la caché ∪ cola pendiente
  # (sobre-emitir desde atrás es seguro: el hub aplica el lote en orden y rechaza solo los
  # eslabones ya aplicados, elemento a elemento).
  local base bidx pridx
  pridx="$(ops_phase_idx pr)"
  # [#44] El catálogo v2 no admite ningún campo en slice_archived (extra="forbid") y el
  # tipo es de ámbito slice (slice_id de primer nivel OBLIGATORIO): con --epic/--pr-url
  # en el payload o sin slice el hub rechazaba TODO archivado — payload {} y slice exigido.
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  base="$(ops_known_phase "$sid")"
  bidx="$(ops_phase_idx "$base")"; [ "$bidx" -ge 0 ] || bidx=0
  if [ "$bidx" -lt "$pridx" ]; then
    echo "⚠ el slice estaba en «${base}» server-side: se encola la cadena phase_advanced hasta pr antes del archivado"
    _phase_chain_enqueue "$sid" "$bidx" "$pridx" || return $OPS_RC_OFFLINE
  fi
  pfile="$(ops_tmpjson "{}")" || return $OPS_RC_OFFLINE
  if ops_enqueue_from_file slice_archived "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "slice_archived encolado (se entrega al reconectar; tipo protegido de la cota)"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ slice_archived NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# ── wiring ───────────────────────────────────────────────────────────────────────────
# El checklist de cableado es el corazón del refresh de contexto: nace `failing` y solo
# pasa a `passing` tras prueba REAL ejecutada. Se emite como eventos del agregado slice
# (spec §4.1-C: el reducer proyecta status + kind/ref/evidence, no solo el status).
cmd_wiring() {
  local accion="${1:-}"
  [ -n "$accion" ] && shift
  case "$accion" in
    seed) _wiring_seed "$@" ;;
    update) _wiring_update "$@" ;;
    *) echo "uso: slice-ops.sh wiring seed --file items.json | wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]" >&2
       return $OPS_RC_USAGE ;;
  esac
}

# _wiring_seed --file <json array de {item_id, kind, ref}>
_wiring_seed() {
  local file="" sid pfile
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  [ -n "$file" ] && [ -f "$file" ] || { echo "uso: slice-ops.sh wiring seed --file items.json" >&2; return $OPS_RC_USAGE; }
  # [I5] Ámbito slice: sin slice_id el hub rechaza el evento elemento a elemento (rc 4, como escalate).
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  command -v python3 >/dev/null 2>&1 || { echo "⚠ sin python3: no se puede sembrar el checklist" >&2; return $OPS_RC_OFFLINE; }
  pfile="$(mktemp)" || return $OPS_RC_OFFLINE
  # El payload se construye leyendo el fichero DENTRO de python3 (nunca por argv) y se
  # normaliza al schema del catálogo v2 [#44]: WiringChecklistItem es {item_id, kind, ref}
  # EXACTO (extra="forbid") — `status` no viaja (cada ítem nace `failing` en el fold del
  # hub; el estado inicial no es negociable) y kind/ref nunca son null (son obligatorios).
  python3 - "$file" > "$pfile" <<'PY' 2>/dev/null
import json,sys
try:
    raw=json.load(open(sys.argv[1]))
except Exception:
    raw=[]
if isinstance(raw,dict):
    raw=raw.get("items") or []
items=[]
for it in raw if isinstance(raw,list) else []:
    if not isinstance(it,dict):
        continue
    iid=it.get("item_id") or it.get("id")
    if not iid:
        continue
    items.append({"item_id":iid,"kind":it.get("kind") or "","ref":it.get("ref") or ""})
print(json.dumps({"items":items},ensure_ascii=False))
PY
  # El hub exige al menos un ítem (WiringChecklistSeeded.items min_length=1): un checklist
  # vacío es rechazo garantizado — se corta aquí, sin encolar.
  local n_items
  n_items="$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1])).get("items") or []))' "$pfile" 2>/dev/null || echo 0)"
  if [ "$n_items" = 0 ]; then
    rm -f "$pfile"
    echo "⛔ el checklist no tiene items válidos (item_id obligatorio): el hub exige al menos uno" >&2
    return $OPS_RC_REJECTED
  fi
  if ops_enqueue_from_file wiring_checklist_seeded "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "checklist de wiring sembrado (evento encolado)"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ checklist de wiring NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# _wiring_update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence T|--evidence-file F]
_wiring_update() {
  local item="${1:-}" estado="${2:-}" kind="" ref="" ev="" evfile="" sid payload pfile
  if [ -z "$item" ] || [ -z "$estado" ]; then
    echo "uso: slice-ops.sh wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]" >&2
    return $OPS_RC_USAGE
  fi
  shift 2
  while [ $# -gt 0 ]; do
    case "$1" in
      --kind) kind="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --ref) ref="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$estado" in
    passing|failing) : ;;
    *) echo "⛔ estado inválido «${estado}» (passing|failing)" >&2; return $OPS_RC_REJECTED ;;
  esac
  if [ -n "$evfile" ]; then
    _ops_evidence_file_ok "$evfile" "wiring «${item}»" || return $OPS_RC_USAGE
  fi
  if [ "$estado" = "passing" ] && [ -z "$ev" ] && [ -z "$evfile" ]; then
    echo "⚠ marcando «${item}» como passing SIN evidencia: la regla dura exige prueba real ejecutada" >&2
  fi
  # [I5] Ámbito slice: rc 4 sin unidad reclamada (el hub lo rechazaría).
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  payload="{\"item_id\":$(ops_json_str "$item"),\"status\":$(ops_json_str "$estado"),\"kind\":$(ops_json_str "$kind"),\"ref\":$(ops_json_str "$ref"),\"evidence\":$(_ops_evidence_json "$ev" "$evfile")}"
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OFFLINE
  if ops_enqueue_from_file wiring_item_updated "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "wiring «${item}» → $estado (evento encolado)"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ wiring «${item}» NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# ── progress ─────────────────────────────────────────────────────────────────────────
# Sustituye a progress_log[]: el event stream ES la bitácora (spec §5.6, el comparador NO
# compara progress_log). Tipo EVICTABLE a propósito: es volumen, no hecho de dominio.
cmd_progress() {
  local nota="" file="" sid payload pfile
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) [ -z "$nota" ] && nota="$1"; shift ;;
    esac
  done
  if [ -z "$nota" ] && [ -z "$file" ]; then
    echo "uso: slice-ops.sh progress «nota» | --file F" >&2
    return $OPS_RC_USAGE
  fi
  # [#44] Nombre del catálogo v2: `progress_noted` (payload {note}, sin cambio de claves).
  # [I5] Ámbito slice: rc 4 sin unidad reclamada (el hub lo rechazaría).
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  payload="{\"note\":$(_ops_evidence_json "$nota" "$file")}"
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OFFLINE
  if ops_enqueue_from_file progress_noted "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "nota de progreso encolada"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ nota de progreso NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# ── checkpoint ───────────────────────────────────────────────────────────────────────
# El checkpoint es lo que permite que OTRO agente continúe tras una caída (protocolo §3
# regla 2). La rama y el commit se leen del repo del PROYECTO, no del cwd de la sesión.
cmd_checkpoint() {
  local nota="" file="" sid branch commit payload root
  while [ $# -gt 0 ]; do
    case "$1" in
      --note) nota="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --note-file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  root="$(config_root)"
  branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  commit="$(git -C "$root" rev-parse HEAD 2>/dev/null || echo "")"
  # [#44] Contrato real del hub: la nota se llama `summary` (CheckpointIn, max 1000; el
  # catálogo CheckpointRecorded también). `note` se descartaba en silencio en el sync y
  # era rechazo por extra="forbid" en la cola. Tope 970 + marcador < 1000.
  local sumjson
  if [ -n "$file" ]; then sumjson="$(ops_json_str_file "$file" 970)"; else sumjson="$(ops_json_str "$nota")"; fi
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  # El body síncrono lleva slice_id (POST /checkpoints, CheckpointIn); el payload del
  # EVENTO no lo admite (extra="forbid"): el slice_id va de primer nivel en la cola.
  payload="{\"slice_id\":$(ops_json_str "$sid"),\"branch\":$(ops_json_str "$branch"),\"commit_sha\":$(ops_json_str "$commit"),\"summary\":$sumjson}"
  local queue_payload
  queue_payload="{\"branch\":$(ops_json_str "$branch"),\"commit_sha\":$(ops_json_str "$commit"),\"summary\":$sumjson}"
  _ops_post_or_queue "$OPS_PATH_CHECKPOINTS" "$payload" checkpoint_recorded "$sid" "el checkpoint" "$queue_payload"
}

# ── carril de micro-works (EP-OR-25) ─────────────────────────────────────────────────
# El hub puede repartir un MICRO-WORK en vez de una unidad (`ClaimOut = TaskClaimOut |
# MicroWorkClaimOut`): un fix/chore/docs acotado, con máquina de fases reducida y sin gates. El
# cliente original no tenía este carril. Rutas y cuerpos: task_router.py de trycore-ia-hub
# (origin/develop) — `POST /micro-works/{id}/phase {to}`, `POST …/checkpoint {branch,
# commit_sha, summary?}` (204), `POST …/escalate {reason, limit?}` y `PUT …/lease/renew` (este
# último lo hace heartbeat.sh). Solo el TITULAR opera su micro-work (403 si no). El id sale de la
# caché del claim (.claude/state/claim.json). Mismo contrato de rc que el resto: 0 ok · 2 uso
# (validado en local, sin red) · 4 sin micro-work reclamado · 5 hub caído (encolado por el carril
# directo, drena al volver) · 6 rechazado por el hub (no se reintenta) · 9 identidad heredada.

# _ops_micro_require — id del micro-work reclamado y vivo, o rc 4 con mensaje accionable.
_ops_micro_require() {
  local mw
  mw="$(ops_micro_work_id)"
  if [ -z "$mw" ]; then
    echo "⛔ no hay micro-work reclamado y vivo en la caché del claim: reclama primero" >&2
    echo "  (\`slice-ops.sh claim\`); si el hub reparte un micro-work, su id queda guardado." >&2
    return $OPS_RC_NO_SLICE
  fi
  echo "$mw"
}

# _ops_micro_send <tipo> <path> <payload> <etiqueta> <fichero-respuesta> — POST síncrono y, si el
# hub no está (000, 408, 429, 5xx), encolado por el carril directo. Un rechazo (4xx) NUNCA se
# encola. Deja el cuerpo de la respuesta en <fichero-respuesta>.
# Si el tipo deduplica por `Idempotency-Key` (RUNTIME_DIRECT_IDEMPOTENCY_KEY_TYPES), la clave se
# genera ANTES del primer intento y la petición se encola con ese mismo `client_event_id`: un
# timeout tras aplicarse en el hub (000) se reenvía con la misma clave y el hub devuelve el
# resultado original en vez de un 409.
_ops_micro_send() {
  local tipo="$1" path="$2" payload="$3" etiqueta="$4" rfile="$5" resp status pfile cid="" extra=""
  case " $RUNTIME_DIRECT_IDEMPOTENCY_KEY_TYPES " in
    *" $tipo "*)
      cid="$(python3 -c 'import uuid;print(uuid.uuid4())' 2>/dev/null)"
      [ -n "$cid" ] && extra="Idempotency-Key: $cid" ;;
  esac
  resp="$(runtime_post_headers "$path" "$payload" "$extra")"
  status="$(runtime_http_status)"
  printf '%s' "$resp" > "$rfile"
  case "$status" in
    200|201|202|204)
      return $OPS_RC_OK ;;
    401)
      echo "⛔ token inválido o revocado (401): pide un token nuevo al ADMIN." >&2
      return $OPS_RC_REJECTED ;;
    000|408|429|5*)
      pfile="$(ops_tmpjson "$payload")" || { echo "⚠ OFFLINE: $etiqueta NO se pudo encolar" >&2; return $OPS_RC_OFFLINE; }
      if runtime_enqueue_direct "$tipo" POST "$path" "$pfile" 0 "$cid" >/dev/null; then
        echo "OFFLINE: $etiqueta encolado (tipo protegido, se entrega al reconectar)"
      else
        echo "⚠ OFFLINE: $etiqueta NO se pudo encolar (outbox no escribible u otro fallo local) — se perderá" >&2
      fi
      rm -f "$pfile"
      return $OPS_RC_OFFLINE ;;
    *)
      echo "⛔ $status el hub rechazó $etiqueta: $(_claim_409_text "$resp")" >&2
      echo "  No se reintenta: corrige la causa (fase siguiente, titularidad, límite) y vuelve a pedirlo." >&2
      return $OPS_RC_REJECTED ;;
  esac
}

# micro-fase <in_progress|pr|done> — avanza el micro-work por su máquina reducida.
cmd_micro_fase() {
  local to="${1:-}" mw rf rc
  case " $OPS_MICRO_WORK_PHASES " in
    *" $to "*) : ;;
    *)
      if [ "$to" = escalated ]; then
        echo "⛔ «escalated» no se pide por micro-fase: usa \`micro-escalar --motivo «…»\` (crea la propuesta de unidad)" >&2
      else
        echo "uso: slice-ops.sh micro-fase <$(printf '%s' "$OPS_MICRO_WORK_PHASES" | tr ' ' '|')> (orden estricto)" >&2
      fi
      return $OPS_RC_USAGE ;;
  esac
  mw="$(_ops_micro_require)" || return $?
  rf="$(mktemp)" || return $OPS_RC_OFFLINE
  _ops_micro_send micro_work_phase_advanced "$(ops_path_micro_work_phase "$(ops_urlenc "$mw")")" \
    "{\"to\":$(ops_json_str "$to")}" "la fase «${to}» del micro-work" "$rf"
  rc=$?
  rm -f "$rf"
  if [ $rc -eq $OPS_RC_OK ]; then
    ops_claim_cache_set phase "$to"
    echo "micro-work $mw en fase $to"
    [ "$to" = done ] && echo "micro-work terminado: el heartbeat deja de renovar su lease."
  fi
  return $rc
}

# micro-checkpoint [--branch B] [--commit SHA] [--resumen T] — punto de retorno del micro-work
# (referencia git, nunca código). Rama y commit salen de git si no se pasan.
cmd_micro_checkpoint() {
  local branch="" commit="" resumen="" con_resumen=0 mw root payload tmp rf rc
  while [ $# -gt 0 ]; do
    case "$1" in
      --branch) branch="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --commit) commit="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --resumen) resumen="${2:-}"; con_resumen=1; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  root="$(config_candidate_root)"
  [ -n "$branch" ] || branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  [ -n "$commit" ] || commit="$(git -C "$root" rev-parse HEAD 2>/dev/null || echo "")"
  if [ -z "$branch" ] || [ -z "$commit" ] || [ "${#branch}" -gt 200 ] || [ "${#commit}" -gt 64 ]; then
    echo "uso: slice-ops.sh micro-checkpoint --branch <rama ≤200> --commit <sha ≤64> [--resumen «texto»]" >&2
    echo "  (sin --branch/--commit se toman de git; aquí no se pudieron leer)" >&2
    return $OPS_RC_USAGE
  fi
  mw="$(_ops_micro_require)" || return $?
  payload="{\"branch\":$(ops_json_str "$branch"),\"commit_sha\":$(ops_json_str "$commit")"
  if [ "$con_resumen" = 1 ] && [ -n "$resumen" ]; then
    tmp="$(mktemp)" || return $OPS_RC_OFFLINE
    printf '%s' "$resumen" > "$tmp"
    payload="$payload,\"summary\":$(ops_json_str_file "$tmp")"
    rm -f "$tmp"
  fi
  payload="$payload}"
  rf="$(mktemp)" || return $OPS_RC_OFFLINE
  _ops_micro_send micro_work_checkpointed "$(ops_path_micro_work_checkpoint "$(ops_urlenc "$mw")")" \
    "$payload" "el checkpoint del micro-work" "$rf"
  rc=$?
  rm -f "$rf"
  [ $rc -eq $OPS_RC_OK ] && echo "checkpoint del micro-work $mw registrado ($branch @ $commit)"
  return $rc
}

# micro-escalar --motivo «…» [--limite L] — el micro-work desborda su carril: sale a una propuesta
# de unidad que decide un humano. Deja el micro-work TERMINAL (escalated).
cmd_micro_escalar() {
  local motivo="" limite="" mw payload tmp rf rc prop
  while [ $# -gt 0 ]; do
    case "$1" in
      --motivo) motivo="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --limite) limite="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$motivo" ]; then
    echo "uso: slice-ops.sh micro-escalar --motivo «por qué desborda el carril» [--limite <$(printf '%s' "$OPS_MICRO_WORK_LIMITS" | tr ' ' '|')>]" >&2
    return $OPS_RC_USAGE
  fi
  if [ -n "$limite" ]; then
    case " $OPS_MICRO_WORK_LIMITS " in
      *" $limite "*) : ;;
      *) echo "⛔ límite «${limite}» fuera del vocabulario del carril: $OPS_MICRO_WORK_LIMITS" >&2
         return $OPS_RC_USAGE ;;
    esac
  fi
  mw="$(_ops_micro_require)" || return $?
  tmp="$(mktemp)" || return $OPS_RC_OFFLINE
  printf '%s' "$motivo" > "$tmp"
  payload="{\"reason\":$(ops_json_str_file "$tmp")"
  rm -f "$tmp"
  [ -n "$limite" ] && payload="$payload,\"limit\":$(ops_json_str "$limite")"
  payload="$payload}"
  rf="$(mktemp)" || return $OPS_RC_OFFLINE
  _ops_micro_send micro_work_escalated "$(ops_path_micro_work_escalate "$(ops_urlenc "$mw")")" \
    "$payload" "la escalada del micro-work" "$rf"
  rc=$?
  if [ $rc -eq $OPS_RC_OK ]; then
    prop="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("epic_proposal_id") or "")
except Exception: print("")' "$rf" 2>/dev/null)"
    ops_claim_cache_set phase escalated
    echo "micro-work $mw escalado: sale del carril (terminal)."
    echo "propuesta de unidad: ${prop:-sin id en la respuesta}  ·  la DECISIÓN es humana (consola del hub)."
  elif [ $rc -eq $OPS_RC_OFFLINE ]; then
    echo "  Viaja con Idempotency-Key: si el hub ya la aplicó, el reenvío devuelve el mismo resultado."
    echo "  Al entregarse, la propuesta de unidad queda en .claude/state/outbox/acks/ (epic_proposal_id)."
  fi
  rm -f "$rf"
  return $rc
}

# ── register ─────────────────────────────────────────────────────────────────────────
# [#74] Alta EXPLÍCITA de este árbol de trabajo como agente propio.
#
# El caso que lo motiva: dos agentes construyendo dos épicas en la misma máquina, cada uno en
# su worktree. El hub reparte las dos sin objeción — el bloqueo estaba aquí: un worktree sin
# `.claude/state/runtime.credentials` propio hereda el del clon principal por el fallback de
# `config_root()` y trabaja con SU identidad sin decirlo.
#
# Tres decisiones de diseño que no son gratuitas:
#   1. El token entra por STDIN (prompt si hay TTY), jamás por argumento: un `--token` queda
#      en el historial del shell y en `ps`. Por eso `register` es un comando de terminal
#      humano y NO se invoca desde dentro de un claim — los hooks y las tool calls no tienen
#      TTY y un `read` ahí colgaría la llamada.
#   2. Se siembra PRIMERO el fichero local, para que `config_root()` ancle en este árbol antes
#      de cualquier merge. Al revés, `runtime_register` habría hecho upsert del token nuevo
#      sobre el fichero del clon principal, pisándole la identidad al agente que trabaja ahí.
#   3. Se valida que el `agent_key` obtenido DIFIERA del que tiene el principal. El hub no crea
#      identidades en `/agents/register`: el `agent_key` es el `agent_id` que el ADMIN grabó en
#      el token al emitirlo. Mismo token ⇒ mismo agente ⇒ el claim devolvería el trabajo del
#      otro worktree. Un token por agente, siempre.
#
# Ante cualquier fallo se revierte: o el árbol queda con identidad propia y verificada, o
# queda exactamente como estaba. Un fichero de credenciales a medias es peor que ninguno.

# _reg_rollback <fichero> <backup> — deja el fichero local como estaba antes de `register`.
# Desarma el trap de interrupción: una segunda pasada, ya sin copia, borraría el fichero recién restaurado.
_reg_rollback() {
  local file="$1" backup="$2"
  trap - INT TERM HUP
  if [ -n "$backup" ] && [ -f "$backup" ]; then
    cp "$backup" "$file" 2>/dev/null
    rm -f "$backup"
  else
    rm -f "$file"
  fi
}

cmd_register() {
  local url="" force=0 desde_stdin=0 wt main localfile mainfile mainkey newkey token backup="" hv at rc cfg_main cfg_wt
  while [ $# -gt 0 ]; do
    case "$1" in
      --url|--runtime-url|--hub-url) url="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --token-stdin) desde_stdin=1; shift ;;
      --force) force=1; shift ;;
      --token|--project-token|--runtime-token)
        echo "⛔ el token NO se pasa por argumento: quedaría en el historial del shell y en \`ps\`." >&2
        echo "   \`register\` lo lee por stdin (--token-stdin) o de TRYCORE_REGISTER_TOKEN." >&2
        return $OPS_RC_USAGE ;;
      *) shift ;;
    esac
  done
  command -v python3 >/dev/null 2>&1 || {
    echo "⛔ register necesita python3 para escribir las credenciales." >&2; return $OPS_RC_OFFLINE; }

  wt="$(config_candidate_root)"
  main="$(config_main_clone_root)"
  localfile="$wt/.claude/state/runtime.credentials"
  mainfile=""
  if [ -n "$main" ] && [ "$main" != "$wt" ]; then mainfile="$main/.claude/state/runtime.credentials"; fi

  if [ -f "$localfile" ] && [ "$force" != 1 ]; then
    echo "este árbol YA tiene identidad propia — no se toca nada:"
    echo "  raíz:      $wt"
    echo "  agente:    $(runtime_credentials_field_at "$localfile" agent_key)"
    echo "  proyecto:  $(runtime_credentials_field_at "$localfile" project_id)"
    echo "(para re-registrarlo con OTRO token: \`register --force\`)"
    return $OPS_RC_OK
  fi

  # La URL no es secreta y es la MISMA del proyecto: --url > credenciales (propias o del clon
  # principal) > runtime.url de bonita-build-config.json (de este árbol o del principal) > la
  # del hub de desarrollo de Trycore.
  cfg_wt="$wt/.claude/config/bonita-build-config.json"
  cfg_main=""
  [ -n "$main" ] && cfg_main="$main/.claude/config/bonita-build-config.json"
  if [ -z "$url" ]; then
    url="$(runtime_credentials_field_at "$localfile" runtime_url)"
    [ -n "$url" ] || url="$(runtime_credentials_field_at "$mainfile" runtime_url)"
    [ -n "$url" ] || [ ! -f "$cfg_wt" ] || url="$(BUILD_CONFIG_FILE="$cfg_wt" config_get runtime.url "")"
    [ -n "$url" ] || [ -z "$cfg_main" ] || [ ! -f "$cfg_main" ] || url="$(BUILD_CONFIG_FILE="$cfg_main" config_get runtime.url "")"
    [ -n "$url" ] || url="$SO_HUB_URL_POR_DEFECTO"
  fi
  url="${url%/}"
  case "$url" in
    http://*|https://*) : ;;
    *)
      echo "⛔ la URL del hub no es http(s): «${url}». Pásala explícita: \`register --url https://…\`" >&2
      return $OPS_RC_USAGE ;;
  esac

  mainkey="$(runtime_credentials_field_at "$mainfile" agent_key)"

  # El token, por stdin (--token-stdin, o prompt si hay TTY) o por TRYCORE_REGISTER_TOKEN.
  # Nunca por argumento. `init` lo pasa por stdin con la variable vaciada en el hijo.
  token=""
  if [ "$desde_stdin" = 1 ] && [ -t 0 ]; then
    printf 'Token de agente (no se muestra en pantalla): ' >&2
    IFS= read -rs token
    printf '\n' >&2
  elif [ "$desde_stdin" = 1 ]; then
    IFS= read -r token || [ -n "$token" ] || token=""
  elif [ -n "${TRYCORE_REGISTER_TOKEN:-}" ]; then
    token="$TRYCORE_REGISTER_TOKEN"
  elif [ -t 0 ]; then
    printf 'Token de agente para este árbol (no se muestra en pantalla): ' >&2
    IFS= read -rs token
    printf '\n' >&2
  else
    IFS= read -r token || [ -n "$token" ] || token=""
  fi
  token="$(printf '%s' "$token" | tr -d '[:space:]')"
  [ -n "$token" ] || { echo "⛔ token vacío: no se registró nada." >&2; return $OPS_RC_USAGE; }

  # Compuerta barata y decisiva, ANTES de la red: si el token es el del clon principal, el hub
  # devolverá su misma identidad — el `agent_key` va grabado en el token, no se crea al
  # registrar. Preguntarlo por HTTP solo añadiría una llamada al mismo veredicto.
  if [ -n "$mainfile" ] && [ "$token" = "$(runtime_credentials_field_at "$mainfile" project_token)" ]; then
    token=""
    echo "⛔ ese token es la identidad del clon principal: registrarlo aquí daría el MISMO" >&2
    echo "   agent_key y el claim te devolvería el trabajo que ya tiene reclamado el otro árbol." >&2
    echo "   Pide al ADMIN un token con \`agent_id\` distinto (uno por agente)." >&2
    echo "   El fichero del clon principal NO se ha tocado." >&2
    return $OPS_RC_REJECTED
  fi

  # [M3] La copia de las credenciales viejas (lleva el token) vive en .claude/state/, que se ignora entero, y no en
  # $TMPDIR: un kill a mitad del registro la dejaba fuera de todo .gitignore. Si el registro se interrumpe, el trap
  # restaura el fichero con ella y la borra; al salir, la copia nunca sobrevive.
  if [ -f "$localfile" ]; then
    backup="$(umask 077 && mktemp "$(dirname "$localfile")/.runtime-credentials.backup.XXXXXX")" \
      && cp "$localfile" "$backup" 2>/dev/null || { rm -f "$backup" 2>/dev/null; backup=""; }
  fi
  SO_REG_FILE="$localfile"
  SO_REG_BACKUP="$backup"
  trap '_reg_rollback "$SO_REG_FILE" "$SO_REG_BACKUP"; exit 130' INT TERM HUP
  trap 'rm -f "${SO_REG_BACKUP:-}"' EXIT

  if ! TRYCORE_REGISTER_TOKEN="$token" runtime_credentials_seed_at "$localfile" "$url"; then
    token=""
    _reg_rollback "$localfile" "$backup"
    echo "⛔ no se pudo escribir $localfile — revisa permisos." >&2
    return $OPS_RC_OFFLINE
  fi
  token=""   # el secreto ya está en el fichero 0600: fuera de las variables del shell

  hv="$(harness_version)"
  at="$(harness_asset_types)"
  runtime_register "$hv" "$at"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    _reg_rollback "$localfile" "$backup"
    if [ "$rc" -eq 2 ]; then
      echo "⛔ el hub rechaza esta versión del arnés ($hv): incompatible_version." >&2
      echo "   Actualiza el paquete (\`trycore-bonita update\`) y repite \`register\`." >&2
      return $OPS_RC_REJECTED
    fi
    case "$(runtime_http_status)" in
      401|403)
        echo "⛔ el hub no acepta ese token (HTTP $(runtime_http_status)): pide al ADMIN uno válido" >&2
        echo "   para este proyecto. Nada quedó escrito." >&2
        return $OPS_RC_REJECTED ;;
      *)
        echo "OFFLINE: no se pudo registrar contra $url (HTTP $(runtime_http_status))." >&2
        echo "  Nada quedó escrito: repite \`register\` cuando haya red." >&2
        return $OPS_RC_OFFLINE ;;
    esac
  fi

  newkey="$(runtime_credentials_field_at "$localfile" agent_key)"
  if [ -z "$newkey" ]; then
    _reg_rollback "$localfile" "$backup"
    echo "⛔ el hub respondió 200 pero sin \`agent_key\`: sin identidad verificable no se da" >&2
    echo "   de alta el árbol. Nada quedó escrito." >&2
    return $OPS_RC_REJECTED
  fi
  if [ -n "$mainkey" ] && [ "$newkey" = "$mainkey" ]; then
    _reg_rollback "$localfile" "$backup"
    echo "⛔ ese token resuelve al MISMO agent_key que el clon principal ($mainkey): no es una" >&2
    echo "   identidad nueva. El \`agent_key\` lo graba el ADMIN en el token al emitirlo —" >&2
    echo "   pide uno con \`agent_id\` distinto. El fichero del clon principal NO se ha tocado." >&2
    return $OPS_RC_REJECTED
  fi
  trap - INT TERM HUP
  rm -f "$backup"
  # [I4] Token nuevo y verificado: la marca de token rechazado deja de ser verdad (la cola drena sola).
  runtime_auth_clear "$wt/.claude/state/auth-status.json"

  # A partir de aquí `config_root()` ancla en este árbol, y con él TODA la resolución de
  # config: si bonita-build-config.json no viajó al worktree, los umbrales de contexto y
  # `runtime.url` caerían a sus valores por defecto. Se copia del principal solo si aquí no hay
  # ninguno: nunca se pisa una config local.
  if [ -n "$cfg_main" ] && [ "$main" != "$wt" ] && [ ! -f "$cfg_wt" ] && [ -f "$cfg_main" ]; then
    mkdir -p "$wt/.claude/config"
    cp "$cfg_main" "$cfg_wt" 2>/dev/null \
      && echo "  (bonita-build-config.json copiado del clon principal)"
  fi

  echo "árbol dado de alta con identidad propia:"
  echo "  raíz:      $wt"
  echo "  agente:    $newkey"
  echo "  proyecto:  $(runtime_credentials_field_at "$localfile" project_id)"
  echo "  hub:       $url  ·  arnés $hv"
  [ -n "$mainkey" ] && echo "  (distinto del clon principal: $mainkey — su fichero no se tocó)"
  echo "Desde aquí el claim, los gates y el heartbeat son de ESTE árbol. Siguiente paso:"
  echo "  bash .claude/hooks/bonita/slice-ops.sh claim [--unidad <código>]"
  return $OPS_RC_OK
}

SUB="${1:-}"
[ $# -gt 0 ] && shift

# [#74] Compuerta de identidad ANTES de despachar. Las operaciones de ESCRITURA — todo lo que
# firma un acto con el `agent_key` o toca la cola/los ledgers — abortan si este árbol heredó la
# identidad del clon principal o [I5] si no tiene credenciales (un clon sin registrar). Las LECTURAS (`mode`, `next-step`, `status`, los `*-status`)
# quedan fuera a propósito: son el diagnóstico de un worktree que aún no se dio de alta, y
# `status` avisa de quién es el estado que enseña. `register` tampoco entra: es la salida.
case " claim phase gate submit archive wiring progress checkpoint fact propose-asset propose-epic graph-sync escalate micro-fase micro-checkpoint micro-escalar " in
  *" $SUB "*) ops_guard_own_identity "$SUB" || exit $? ;;
esac

case "$SUB" in
  mode) ops_mode; exit 0 ;;
  register) cmd_register "$@"; exit $? ;;
  claim) cmd_claim "$@"; exit $? ;;
  next-step) cmd_next_step; exit $? ;;
  phase) cmd_phase "$@"; exit $? ;;
  gate) cmd_gate "$@"; exit $? ;;
  submit) cmd_submit "$@"; exit $? ;;
  archive) cmd_archive "$@"; exit $? ;;
  wiring) cmd_wiring "$@"; exit $? ;;
  progress) cmd_progress "$@"; exit $? ;;
  checkpoint) cmd_checkpoint "$@"; exit $? ;;
  fact) cmd_fact "$@"; exit $? ;;
  propose-asset) cmd_propose_asset "$@"; exit $? ;;
  propose-epic) cmd_propose_epic "$@"; exit $? ;;
  epic-status) cmd_epic_status "$@"; exit $? ;;
  graph-sync) cmd_graph_sync "$@"; exit $? ;;
  graph-sync-status) cmd_graph_sync_status "$@"; exit $? ;;
  status) cmd_status "$@"; exit $? ;;
  escalate) cmd_escalate "$@"; exit $? ;;
  micro-fase) cmd_micro_fase "$@"; exit $? ;;
  micro-checkpoint) cmd_micro_checkpoint "$@"; exit $? ;;
  micro-escalar) cmd_micro_escalar "$@"; exit $? ;;
  ""|-h|--help|help) usage; exit $OPS_RC_USAGE ;;
  *) echo "subcomando desconocido: $SUB" >&2; usage; exit $OPS_RC_USAGE ;;
esac
