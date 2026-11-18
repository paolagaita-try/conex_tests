#!/usr/bin/env bash
# runtime-ops.sh — base común de las OPERACIONES DE DOMINIO que conducen las skills
# [EP-OR-08-C]. Los hooks (sub-slice B) observan; esto transiciona: claim, veredictos,
# checkpoints, submit, archive y hechos de proyecto. Lo usan hooks/build/slice-ops.sh y
# hooks/build/release-ops.sh, que son INVOCADOS por las skills (no hooks registrados).
#
# Aquí vive el ÚNICO sitio del cliente bash donde se escriben rutas del runtime: si el
# re-volcado de OpenAPI (EP-OR-13) mueve un endpoint, se toca este fichero y nada más.
#
# Diseño fail-open, igual que runtime-client.sh: ninguna función lanza; ante red caída,
# python3 ausente o JSON corrupto se degrada a un valor seguro o a un rc distinguible.

source "$(dirname "${BASH_SOURCE[0]}")/projection.sh"
source "$(dirname "${BASH_SOURCE[0]}")/agent-context.sh"

# ── Códigos de salida (contrato con las skills; la prosa ramifica sobre estos números) ──
OPS_RC_OK=0
OPS_RC_USAGE=2
OPS_RC_LEGACY=3
OPS_RC_NO_SLICE=4
OPS_RC_OFFLINE=5
OPS_RC_REJECTED=6
OPS_RC_NO_WORK=7
OPS_RC_NOT_MIRRORABLE=8
OPS_RC_NO_IDENTITY=9

# ── Guard de identidad heredada [#74] ────────────────────────────────────────────────
# Un worktree sin `.claude/state/runtime.credentials` propio hereda el del clon principal por
# el fallback de `config_root()`: lee bien, pero al ESCRIBIR suplanta — reclama con el
# `agent_key` ajeno, reporta al hub los hashes del árbol equivocado y comparte su heartbeat.
# El hub reparte dos épicas a dos agentes sin objeción; el bloqueo del multi-agente en una
# misma máquina siempre estuvo aquí, en el cliente. Por eso el guard es fail-FAST y no
# fail-open: la regla general de este cliente («ante la duda, no bloquees el trabajo local»)
# protege del runtime caído, no de mandar actos firmados con la identidad de otro.
#
# ops_guard_own_identity <subcomando> — rc 0 si este árbol tiene identidad propia;
# OPS_RC_NO_IDENTITY (9) con mensaje accionable si la heredó.
ops_guard_own_identity() {
  local sub="${1:-esta operación}" main
  config_is_inherited_root || return 0
  main="$(config_main_clone_root)"
  echo "⛔ este worktree no tiene identidad propia: «${sub}» operaría como el agente del clon" >&2
  echo "   principal (${main:-?}) — su agent_key, su lease, sus hashes de contexto." >&2
  echo "   Da de alta este árbol con un token de agente NUEVO emitido por el ADMIN:" >&2
  echo "     bash .claude/hooks/build/slice-ops.sh register" >&2
  echo "   (el token se pide por stdin, nunca por argumento). Las lecturas — \`status\`," >&2
  echo "   \`next-step\`, \`mode\` — siguen funcionando con el contexto heredado." >&2
  return $OPS_RC_NO_IDENTITY
}

# Tope de texto libre que el cliente manda al servidor (evidencias, notas): el protocolo §8
# dice que el servidor rechaza payloads sobredimensionados; se trunca aquí, marcándolo.
# [#44] El límite real del hub es 2000 (event_catalog._MAX_NOTE y VerdictIn.evidence):
# 1970 + los 27 caracteres del marcador de truncado de ops_json_str_file queda por debajo.
# El 4000 anterior producía rechazos en evidencias largas.
OPS_MAX_TEXT=1970

# Gates canónicos (se validan en el cliente: un nombre inventado por el modelo no llega
# a la red — compuerta mecánica barata, sin round-trip).
OPS_SLICE_GATES="dor coherence_link tdd journey_smoke fidelity api data wiring_verified dod"
OPS_RELEASE_GATES="security smell ux coherence stack_arch integration"

# Fases canónicas del slice en el hub (domain.py PHASES, issue #52), SIN `archived`:
# esa fase terminal se alcanza con el evento `slice_archived`, nunca con `phase_advanced`.
# El orden es NORMATIVO: el reducer del hub solo acepta la fase siguiente exacta
# (orden estricto, domain.py:400-407) — de aquí salen las cadenas que emite `phase`.
OPS_SLICE_PHASES="dor change red green refactor smoke api data dod pr"

# Enumeración NORMATIVA de la ingesta espejo (`TIPOS_DE_ESPEJO` del hub, derivada allí de los
# schemas que heredan de `_TransicionDeEspejo`). Se replica aquí para no gastar una llamada en
# algo que el hub va a rechazar por elemento — y el test la compara contra esta misma lista, así
# que ampliarla en el hub obliga a ampliarla aquí (lección de #44: dos listas del mismo hecho
# divergen tarde o temprano, y la que calla es la que miente).
# `release_verdict_reported` y `front_integration_reported` NO están, y no es un olvido: no
# existen en el catálogo del hub. Sus canales de espejo son trabajo hub-side (tipo nuevo con su
# base `_TransicionDeEspejo` y su rama de reducer), no algo que este cliente pueda arreglar.
OPS_MIRROR_TYPES="slice_opened phase_advanced phase_reverted gate_verdict wiring_item_updated wiring_checklist_seeded checkpoint_recorded progress_noted handoff_recorded"

# ops_phase_idx <fase> — índice de la fase en OPS_SLICE_PHASES; -1 si no es fase del hub.
ops_phase_idx() {
  local i=0 p
  for p in $OPS_SLICE_PHASES; do
    [ "$p" = "$1" ] && { echo "$i"; return; }
    i=$((i + 1))
  done
  echo -1
}

# ops_phase_at <idx> — nombre de la fase en esa posición ("" fuera de rango).
ops_phase_at() {
  local i=0 p
  for p in $OPS_SLICE_PHASES; do
    [ "$i" = "$1" ] && { echo "$p"; return; }
    i=$((i + 1))
  done
  echo ""
}

# ops_known_phase [slice_id] — la fase del slice que el SERVIDOR conoce (o va a conocer):
# la de la caché de proyección, avanzada por los `phase_advanced` PENDIENTES de la outbox
# para ese slice (el daemon aún no drenó, pero el cliente ya los emitió — sin esto, dos
# llamadas seguidas a `phase` duplicarían la cadena y el hub las rechazaría una a una).
# Una fase desconocida o ausente cae a `dor` (fase de nacimiento del slice): sobre-emitir
# desde atrás es seguro — el lote se aplica en orden y el hub rechaza los eslabones ya
# aplicados elemento a elemento mientras el sufijo válido entra.
ops_known_phase() {
  local sid="${1:-}" base idx pidx
  base="$(projection_get active_slice.phase "")"
  idx="$(ops_phase_idx "$base")"
  [ "$idx" -ge 0 ] || idx=0
  if [ -n "$sid" ] && command -v python3 >/dev/null 2>&1; then
    pidx="$(python3 - "$(runtime_outbox_dir)" "$sid" "$OPS_SLICE_PHASES" <<'PY' 2>/dev/null
import json,sys,glob,os
d,sid,phases=sys.argv[1],sys.argv[2],sys.argv[3].split()
best=-1
for p in glob.glob(os.path.join(d,"*.json")):
    if os.path.basename(p).startswith("."):
        continue
    try:
        e=json.load(open(p))
    except Exception:
        continue
    if e.get("type")!="phase_advanced" or e.get("slice_id")!=sid:
        continue
    to=(e.get("payload") or {}).get("to")
    if to in phases:
        best=max(best,phases.index(to))
print(best)
PY
)"
    case "$pidx" in ''|*[!0-9]*) pidx=-1 ;; esac
    [ "$pidx" -gt "$idx" ] && idx="$pidx"
  fi
  ops_phase_at "$idx"
}

# ── Tabla de rutas ──
OPS_PATH_CLAIM="/tasks/next"
OPS_PATH_CHECKPOINTS="/checkpoints"
ops_path_verdicts() { echo "/slices/$1/verdicts"; }
ops_path_submit() { echo "/slices/$1/submit"; }
ops_path_release_verdicts() { echo "/releases/$1/verdicts"; }
ops_path_front_integration() { echo "/fronts/$1/members/$2/integration"; }
ops_path_mirror() { echo "/projects/$1/mirror/transitions"; }
ops_path_proposals() { echo "/projects/$1/context/agent-proposals"; }

# [#62] Propuesta de épica (hub#113/#114). El agente PROPONE; el hub decide la identidad
# (`EP-XXX`) al aprobar y un humano aprueba: por eso hay una ruta de creación y otra de
# consulta, y ninguna de publicación. Mismo patrón que las propuestas de asset
# (`ops_path_proposals`), que es su precedente en este cliente.
# [#70] El carril del AGENTE lleva `/agent/`: `/projects/{id}/epic-proposals` (sin él) es la
# vista de CONSOLA — GET con JWT de usuario — y responde `405 Allow: GET` a un POST con token
# de proyecto. Las dos superficies no se comparten por diseño (hub CON-1).
ops_path_epic_proposals() { echo "/projects/$1/agent/epic-proposals"; }
ops_path_epic_proposal() { echo "/projects/$1/agent/epic-proposals/$2"; }

# [EP-OR-17] Re-sync del grafo (HU-OR-72/73). El arnés PROPONE el bundle construido desde los
# docs de discovery, el hub calcula el delta y un HUMANO aprueba en la consola: nada se aplica
# por esta ruta. Mismo carril `/agent/` que las propuestas de épica y por la misma razón — la
# ruta sin `/agent/` es la superficie humana (sesión + PDP) y a un bearer de agente le responde
# 403 auditado, no 405: las dos superficies no se comparten por diseño.
ops_path_graph_sync_proposals() { echo "/projects/$1/agent/graph-sync-proposals"; }
ops_path_graph_sync_proposal() { echo "/projects/$1/agent/graph-sync-proposals/$2"; }

ops_mode() { runtime_mode; }

# ops_slice_id — id del slice activo según la caché de proyección ("" si no hay).
ops_slice_id() { projection_get active_slice.slice_id ""; }

# ops_urlenc <texto> — percent-encoding para segmentos de ruta (una línea de release puede
# llevar espacios o barras). Sin python3 devuelve el texto tal cual: peor URL, nunca excepción.
ops_urlenc() {
  command -v python3 >/dev/null 2>&1 || { printf '%s' "$1"; return; }
  printf '%s' "$1" | python3 -c 'import sys,urllib.parse; sys.stdout.write(urllib.parse.quote(sys.stdin.read(), safe=""))' 2>/dev/null || printf '%s' "$1"
}

# ops_json_str <texto> — imprime el texto como cadena JSON (comillas incluidas). El texto
# viaja por STDIN, nunca por argv: así ni ARG_MAX ni el quoting de bash lo limitan.
ops_json_str() {
  command -v python3 >/dev/null 2>&1 || { printf '""'; return; }
  printf '%s' "$1" | python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read(), ensure_ascii=False))' 2>/dev/null || printf '""'
}

# ops_json_str_file <fichero> [max=OPS_MAX_TEXT] — igual, leyendo de un fichero y truncando
# al tope (marcado en el propio texto para que el servidor y el humano lo vean).
ops_json_str_file() {
  local f="$1" max="${2:-$OPS_MAX_TEXT}"
  [ -f "$f" ] || { printf '""'; return; }
  command -v python3 >/dev/null 2>&1 || { printf '""'; return; }
  python3 - "$f" "$max" <<'PY' 2>/dev/null || printf '""'
import json,sys
try:
    t=open(sys.argv[1], encoding="utf-8", errors="replace").read()
except Exception:
    t=""
m=int(sys.argv[2])
if len(t) > m:
    t = t[:m] + "\n…[truncado por el cliente]"
sys.stdout.write(json.dumps(t, ensure_ascii=False))
PY
}

# ops_tmpjson <json> — materializa un JSON en un fichero temporal e imprime su ruta.
# Los payloads viajan a python3 y a curl POR FICHERO (regla dura del repo: nunca por argv).
ops_tmpjson() {
  local f
  f="$(mktemp)" || return 1
  printf '%s' "$1" > "$f"
  echo "$f"
}

# ops_context_hashes — sha256 EFECTIVO local de cada archivo gobernado del lock
# (protocolo §3 regla 3: el servidor detecta drift/manipulación local comparándolos con los
# suyos). Se hashea el fichero real, NUNCA se repite el sha del lock: repetirlo convertiría
# el reporte en un espejo del servidor y el drift sería indetectable.
# Forma del reporte [#36]: el hub (`TasksNextIn.context_hashes: dict[str, str] | None`)
# exige un DICT {path: sha} — la lista [{"path":…,"sha256":…}] era 422 dict_type en TODO
# claim. Fallback {} (nunca []); fichero ilegible => "" (el dict no admite null en valores).
ops_context_hashes() {
  local lock root
  lock="$(runtime_lock_path)"
  root="$(config_root)"
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  python3 - "$lock" "$root" <<'PY' 2>/dev/null || echo "{}"
import json,sys,os,hashlib
lock,root=sys.argv[1],sys.argv[2]
try:
    files=json.load(open(lock)).get("files") or []
except Exception:
    files=[]
out={}
for f in files:
    if not isinstance(f,dict):
        continue
    p=f.get("path")
    if not isinstance(p,str) or not p:
        continue
    full=os.path.join(root,".claude",p)
    sha=""
    try:
        h=hashlib.sha256()
        with open(full,"rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        sha=h.hexdigest()
    except Exception:
        sha=""
    out[p]=sha
print(json.dumps(out,ensure_ascii=False))
PY
}

# ops_local_slice_ref — identidad del slice según el FICHERO local. Solo tiene sentido en
# modo `dual`, donde el fichero es primario y el runtime crea la identidad por el mismo
# camino que el import (spec §4.1-D). En `runtime` no se usa: allí manda la caché.
# Imprime {} si no hay fichero, no hay python3 o no hay slice activo — nunca lanza.
ops_local_slice_ref() {
  local p
  p="$(config_root)/.claude/state/build-state.json"
  [ -f "$p" ] || { echo "{}"; return; }
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  python3 - "$p" <<'PY' 2>/dev/null || echo "{}"
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    s=d.get("active_slice") or {}
except Exception:
    s={}
print(json.dumps({"epic_code": s.get("epica"),
                  "openspec_change": s.get("openspec_change"),
                  "branch": s.get("branch"),
                  "phase": s.get("phase")}, ensure_ascii=False))
PY
}

# ops_enqueue_from_file <type> <payload_file> [slice_id] — encola un evento cuyo payload
# puede ser grande (checklist de wiring, evidencia, contenido propuesto): el payload se lee
# del FICHERO dentro de python3, así que no pasa por argv (a diferencia de
# runtime_enqueue_event, que sigue sirviendo para payloads pequeños).
ops_enqueue_from_file() {
  local type="$1" pfile="$2" slice_id="${3:-}" dir
  dir="$(runtime_outbox_dir)"
  mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$dir" "$type" "$pfile" "$slice_id" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile,uuid,datetime
dir_,typ,pfile,slice_id=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
try:
    payload=json.load(open(pfile))
except Exception:
    payload={}
cid=str(uuid.uuid4())
ts=datetime.datetime.now(datetime.timezone.utc)
d={"client_event_id":cid,"type":typ,"payload":payload,
   "enqueued_at":ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
if slice_id:
    d["slice_id"]=slice_id
fname=os.path.join(dir_, ts.strftime("%Y%m%d%H%M%S%f")+"-"+cid+".json")
fd,tmp=tempfile.mkstemp(dir=dir_,prefix=".outbox.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,fname)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
  runtime_outbox_enforce_cap >/dev/null
}

# ops_mirror <event_type> <payload_file> [epic_code] — ingesta espejo del modo `dual`
# (spec §4.1-D). El fichero local sigue siendo primario: un rechazo del reducer NO bloquea el
# trabajo, queda como discrepancia del comparador.
# rc 0 aplicado o duplicado · 5 no se pudo (red, sin epic_code, sin python3) · 6 rechazado
# · 8 el tipo no es espejable.
#
# [EP-OR-17] El cuerpo es `MirrorTransitionsIn`: `{"transitions":[{client_event_id, epic_code,
# event_type, payload}]}`. El `{kind, payload, origin, occurred_at}` que se mandaba antes no
# existe en el contrato — el 100 % de lo que el modo dual espejaba era un 422. El `occurred_at`
# tampoco viaja, y no por descuido: los relojes de cliente entran SOLO por el import; aquí
# estampa el servidor. El `origin` tampoco: la marca de origen-espejo la pone el hub, y lo que
# el cliente dijera no elegiría el origen de todos modos.
ops_mirror() {
  local event_type="$1" pfile="$2" epic_code="${3:-}" pid body resp status tmp
  case " $OPS_MIRROR_TYPES " in
    *" $event_type "*) : ;;
    *)
      echo "⚠ «${event_type}» está fuera de la enumeración normativa del catálogo de espejo del hub:" >&2
      echo "  no se envía (viajaría solo para volver rechazado por elemento). Espejables:" >&2
      echo "  $OPS_MIRROR_TYPES" >&2
      return $OPS_RC_NOT_MIRRORABLE ;;
  esac
  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || return $OPS_RC_OFFLINE
  [ -n "$epic_code" ] || epic_code="$(ops_local_slice_ref | python3 -c 'import json,sys; print(json.load(sys.stdin).get("epic_code") or "")' 2>/dev/null)"
  if [ -z "$epic_code" ]; then
    echo "⚠ «${event_type}» no espejado: sin epic_code (el hub lo exige y el lote sería un 422)." >&2
    echo "  Sale de active_slice.epica del build-state local: abre un slice antes de espejar." >&2
    return $OPS_RC_OFFLINE
  fi
  command -v python3 >/dev/null 2>&1 || return $OPS_RC_OFFLINE
  tmp="$(mktemp)" || return $OPS_RC_OFFLINE
  python3 - "$event_type" "$pfile" "$epic_code" > "$tmp" <<'PY' 2>/dev/null
import json,sys,uuid
event_type,pfile,epic_code=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    payload=json.load(open(pfile))
except Exception:
    payload={}
if not isinstance(payload,dict):
    payload={}
print(json.dumps({"transitions":[{"client_event_id":str(uuid.uuid4()),
                                  "epic_code":epic_code,
                                  "event_type":event_type,
                                  "payload":payload}]},ensure_ascii=False))
PY
  body="$(cat "$tmp" 2>/dev/null)"
  rm -f "$tmp"
  [ -n "$body" ] || return $OPS_RC_OFFLINE
  resp="$(runtime_post "$(ops_path_mirror "$pid")" "$body")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202) _ops_mirror_report "$event_type" "$resp" ;;
    409|422)
      # 409 = el cutover apagó la ingesta espejo para este proyecto; 422 = el lote no cumple el
      # borde. Los dos son del LOTE entero, no de un elemento: no hay reporte que leer.
      echo "⚠ el espejo rechazó «${event_type}» (HTTP $status): $resp" >&2
      echo "  (queda como discrepancia del comparador dual; el trabajo local NO se bloquea)" >&2
      return $OPS_RC_REJECTED ;;
    *) return $OPS_RC_OFFLINE ;;
  esac
}

# _ops_mirror_report <event_type> <respuesta> — lee el reporte POR ELEMENTO (HU-OR-56 E3).
# rc 0 aplicado o duplicado · 6 rechazado, con el motivo del hub a la vista: volcar el cuerpo
# crudo escondía justo la frase que dice qué hay que arreglar.
_ops_mirror_report() {
  local event_type="$1" reason
  command -v python3 >/dev/null 2>&1 || return $OPS_RC_OK
  reason="$(printf '%s' "$2" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    rs=d.get("results") or []
    sys.stdout.write(next((r.get("reason") or "rechazado sin motivo registrado")
                          for r in rs if r.get("status")=="rejected"))
except Exception:
    pass
' 2>/dev/null)"
  [ -n "$reason" ] || return $OPS_RC_OK
  echo "⚠ el espejo rechazó «${event_type}»: $reason" >&2
  case "$reason" in
    *"no existe en el grafo"*)
      # Este es EL rechazo del piloto: el grafo del hub se quedó en la foto del import inicial
      # y toda transición de una épica posterior rebota. Ahora hay una salida que ofrecer.
      echo "  El grafo del hub no conoce esa épica. Propón el re-sync con" >&2
      echo "  \`slice-ops.sh graph-sync --file epics.json\` y pide su aprobación en la consola." >&2 ;;
  esac
  echo "  (queda como discrepancia del comparador dual; el trabajo local NO se bloquea)" >&2
  return $OPS_RC_REJECTED
}

# ── Ledger local de propuestas de épica [#62] ────────────────────────────────────────
# Memoria del ciclo «propongo → un humano aprueba → escribo el fichero con el código del
# hub». Vive fuera de build-state.json a propósito: en modo `runtime` ese fichero no es la
# fuente de verdad, y el ledger no es estado del pipeline sino el rastro de una conversación
# con el hub. Clave estable: `client_event_id` (lo asigna el encolado, existe desde el primer
# instante); `proposal_id` llega después, con el ack, y puede no llegar nunca (offline).
ops_epic_ledger_path() { echo "$(config_root)/.claude/state/epic-proposals.json"; }

# _ops_ledger_read <fichero> — imprime {"proposals":[…]}; nunca lanza.
# [EP-OR-17] Base común del ledger de propuestas de épica y del de re-sync del grafo: son la
# misma estructura con otra ruta, y duplicar 60 líneas de python3 garantizaba que una de las
# dos copias se quedara atrás.
_ops_ledger_read() {
  command -v python3 >/dev/null 2>&1 || { echo '{"proposals":[]}'; return; }
  python3 - "$1" <<'PY' 2>/dev/null || echo '{"proposals":[]}'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    ps=d.get("proposals")
    print(json.dumps({"proposals": ps if isinstance(ps,list) else []},ensure_ascii=False))
except Exception:
    print('{"proposals":[]}')
PY
}

# _ops_ledger_upsert <fichero> <entrada-json> — upsert por client_event_id: las claves que la
# entrada NO menciona se conservan (así un `epic-status` puede fijar el estado sin borrar el
# borrador que guardó `propose-epic`). Escritura atómica. rc 0/1.
_ops_ledger_upsert() {
  local f="$1" entry="$2"
  mkdir -p "$(dirname "$f")"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$f" "$entry" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile
path,entry=sys.argv[1],sys.argv[2]
try:
    d=json.load(open(path))
except Exception:
    d={}
ps=d.get("proposals")
if not isinstance(ps,list):
    ps=[]
e=json.loads(entry)
cid=e.get("client_event_id")
for i,p in enumerate(ps):
    if isinstance(p,dict) and p.get("client_event_id")==cid:
        p.update(e)
        ps[i]=p
        break
else:
    ps.append(e)
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".ledger.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump({"proposals":ps},out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

ops_epic_ledger_read() { _ops_ledger_read "$(ops_epic_ledger_path)"; }
ops_epic_ledger_upsert() { _ops_ledger_upsert "$(ops_epic_ledger_path)" "$1"; }

# ── Ledger local del re-sync del grafo [EP-OR-17] ────────────────────────────────────
# Fichero PROPIO, no una sección del de épicas: un re-sync no es una propuesta de épica, y
# mezclarlos haría que `epic-status` hablara de grafos y `graph-sync-status` de épicas.
ops_graph_sync_ledger_path() { echo "$(config_root)/.claude/state/graph-sync-proposals.json"; }
ops_graph_sync_ledger_read() { _ops_ledger_read "$(ops_graph_sync_ledger_path)"; }
ops_graph_sync_ledger_upsert() { _ops_ledger_upsert "$(ops_graph_sync_ledger_path)" "$1"; }

# ops_graph_sync_cid — `client_event_id` DETERMINISTA de la próxima propuesta de re-sync:
# `<agent_key>:graph-sync:<n>`, con n = entradas del ledger + 1.
#
# Determinista es el punto: el reintento tras un 409 de grafo rancio reusa exactamente este
# cid y el hub deduplica, en vez de acabar con dos propuestas del mismo grafo esperando
# aprobación humana. El contrato acota el campo a 64 caracteres, así que una `agent_key` larga
# se sustituye por su sha256 truncado — sigue siendo estable para el mismo agente, que es lo
# único que la idempotencia necesita.
ops_graph_sync_cid() {
  local ak n
  ak="$(runtime_field agent_key)"
  [ -n "$ak" ] || ak="agente"
  n="$(ops_graph_sync_ledger_read | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("proposals") or []) + 1)' 2>/dev/null)"
  case "$n" in ''|*[!0-9]*) n=1 ;; esac
  if [ "${#ak}" -gt 30 ]; then
    ak="$(printf '%s' "$ak" | python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest()[:16])' 2>/dev/null)"
    [ -n "$ak" ] || ak="agente"
  fi
  echo "${ak}:graph-sync:${n}"
}

# ops_epic_ack_read <client_event_id> — el ack que dejó el carril directo, o "".
ops_epic_ack_read() {
  local f; f="$(runtime_outbox_dir)/acks/$1.json"
  [ -f "$f" ] || { echo ""; return; }
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$f" <<'PY' 2>/dev/null || echo ""
import json,sys
try:
    print(json.dumps(json.load(open(sys.argv[1])),ensure_ascii=False))
except Exception:
    print("")
PY
}

# ops_epic_rejected_reason <client_event_id> — razón con la que el carril directo apartó la
# petición (o "" si no está apartada). Es lo que convierte «no pasa nada» en un diagnóstico.
ops_epic_rejected_reason() {
  local dir; dir="$(runtime_outbox_dir)/rejected"
  [ -d "$dir" ] || { echo ""; return; }
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$dir" "$1" <<'PY' 2>/dev/null || echo ""
import json,os,sys
d,cid=sys.argv[1],sys.argv[2]
for name in sorted(os.listdir(d)):
    if not name.endswith(".json"):
        continue
    try:
        e=json.load(open(os.path.join(d,name)))
    except Exception:
        continue
    if e.get("client_event_id")==cid:
        print(e.get("rejected_reason") or "apartada sin razón registrada")
        break
else:
    print("")
PY
}
