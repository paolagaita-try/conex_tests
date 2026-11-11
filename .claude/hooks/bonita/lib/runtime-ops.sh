#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/lib/runtime-ops.sh
# runtime-ops.sh — base común de las OPERACIONES DE UNIDAD que conducen las skills
# [EP-OR-08-C]. Los hooks observan; esto transiciona: claim, veredictos, checkpoints, submit,
# archive y hechos de proyecto. Lo usa .claude/hooks/bonita/slice-ops.sh, que INVOCAN las
# skills (no es un hook registrado).
#
# Aquí viven, en un solo sitio, las rutas del hub y las LISTAS DEL CONTRATO que el cliente
# valida en local (fases, gates, tipos de evento; `RUNTIME_OUTBOX_PROTECTED` vive en
# runtime-client.sh, que este fichero sourcea). Las compara con trycore-ia-hub
# `scripts/check-contrato-hub.py` (tarea 10): si el hub mueve algo, se toca este fichero.
# [I6] Las CLAVES que el cliente manda en cada payload y cuerpo síncrono, y los campos que lee de las
# respuestas, viven en UNA tabla: scripts/contrato-cliente.json (la lee el check contra los modelos del hub
# y la leen las pruebas dinámicas contra lo que los productores mandan de verdad). Un payload nuevo o una
# clave nueva se declara allí.
#
# Diseño fail-open, igual que runtime-client.sh: ninguna función lanza; ante red caída,
# python3 ausente o JSON corrupto se degrada a un valor seguro o a un rc distinguible.

source "$(dirname "${BASH_SOURCE[0]}")/projection.sh"
source "$(dirname "${BASH_SOURCE[0]}")/agent-context.sh"

# ── Códigos de salida (contrato con las skills; la prosa ramifica sobre estos números) ──
# [U16] El 3 («legacy») y el 8 («fuera del catálogo de espejo») del original no existen:
# sin modos legacy/dual no hay nada que los produzca.
OPS_RC_OK=0
OPS_RC_USAGE=2
OPS_RC_NO_SLICE=4
OPS_RC_OFFLINE=5
OPS_RC_REJECTED=6
OPS_RC_NO_WORK=7
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
# OPS_RC_NO_IDENTITY (9) con mensaje accionable si la heredó o si no tiene credenciales.
# [I5] Un CLON sin registrar (segundo desarrollador) no hereda nada, pero tampoco tiene token: sin este
# segundo caso `claim` salía con 5 («sigue trabajando») y el agente construía sin claim ni lease, quizá sobre
# una unidad de otro; `wiring`/`progress` encolaban hechos que tras registrarse acababan en rejected/.
ops_guard_own_identity() {
  local sub="${1:-esta operación}" main
  if ! config_is_inherited_root; then
    [ -n "$(runtime_field project_token)" ] && return 0
    echo "⛔ este árbol no tiene credenciales propias: «${sub}» no puede firmar nada en el hub" >&2
    echo "   (no hay project_token en .claude/state/runtime.credentials). Pide al ADMIN un token de" >&2
    echo "   agente para ti y da de alta el árbol:" >&2
    echo "     bash .claude/hooks/bonita/slice-ops.sh register" >&2
    echo "   (el token se pide por stdin o TRYCORE_REGISTER_TOKEN, nunca por argumento). Las lecturas" >&2
    echo "   — \`status\`, \`next-step\`, \`mode\` — siguen funcionando. No construyas sin claim." >&2
    return $OPS_RC_NO_IDENTITY
  fi
  main="$(config_main_clone_root)"
  echo "⛔ este worktree no tiene identidad propia: «${sub}» operaría como el agente del clon" >&2
  echo "   principal (${main:-?}) — su agent_key, su lease, sus hashes de contexto." >&2
  echo "   Da de alta este árbol con un token de agente NUEVO emitido por el ADMIN:" >&2
  echo "     bash .claude/hooks/bonita/slice-ops.sh register" >&2
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
# Gates del Release Gate (`release_gate_domain.OUTER_GATES`). El arnés Bonita aún no trae
# release-ops.sh (crece en el piloto), pero la lista se conserva aquí para que el contrato
# con el hub se compruebe completo.
OPS_RELEASE_GATES="security smell ux coherence stack_arch integration"

# Fases canónicas del slice en el hub (domain.py PHASES, issue #52), SIN `archived`:
# esa fase terminal se alcanza con el evento `slice_archived`, nunca con `phase_advanced`.
# El orden es NORMATIVO: el reducer del hub solo acepta la fase siguiente exacta
# (orden estricto, domain.py:400-407) — de aquí salen las cadenas que emite `phase`.
OPS_SLICE_PHASES="dor change red green refactor smoke api data dod pr"

# Tipos de evento que el cliente ENCOLA por el lote de `POST /events` (todos deben existir en
# `event_catalog.SCHEMAS` del hub) y los del CARRIL DIRECTO (cada uno a su endpoint).
# `handoff_recorded` lo emite context-monitor.sh y `telemetry_gap` la cota de la outbox.
OPS_EVENT_TYPES="phase_advanced gate_verdict wiring_checklist_seeded wiring_item_updated checkpoint_recorded progress_noted handoff_recorded slice_submitted slice_archived slice_escalated project_fact_updated telemetry_gap"
# [Arnés Bonita] Carril de micro-works (EP-OR-25): sus tres actos van por el carril directo, cada
# uno a su ruta /micro-works/{id}/…; los nombres son los de los eventos que el hub registra
# (`event_catalog.SCHEMAS`), pero viajan a su endpoint, nunca al lote de /events.
OPS_DIRECT_TYPES="epic_proposed graph_sync_proposed micro_work_phase_advanced micro_work_checkpointed micro_work_escalated"

# Carril de micro-works (trycore-ia-hub origin/develop, micro_work_domain.py): máquina REDUCIDA
# backlog → claimed → in_progress → pr → done, orden estricto; `escalated` se alcanza desde
# cualquier fase no terminal, pero por POST /micro-works/{id}/escalate (crea la propuesta de
# unidad), no por /phase. El agente solo pide estas tres (backlog→claimed lo hace el claim).
OPS_MICRO_WORK_PHASES="in_progress pr done"
# LIMITES_DUROS del carril: el `limit` de una escalada debe ser uno de estos (o ninguno).
OPS_MICRO_WORK_LIMITS="sin_dependencia_nueva sin_endpoint_publico_nuevo sin_cambio_de_dominio"

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
# la de la caché de proyección, avanzada por la última fase que el hub CONFIRMÓ al drenar la cola
# (`runtime_phase_acks_path`, solo si es posterior a la proyección) y por los `phase_advanced` PENDIENTES de la outbox
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
    pidx="$(python3 - "$(runtime_outbox_dir)" "$sid" "$OPS_SLICE_PHASES" "$(runtime_phase_acks_path)" "$(runtime_projection_path)" <<'PY' 2>/dev/null
import json,sys,glob,os,calendar,time
d,sid,phases,acks_p,proj_p=sys.argv[1],sys.argv[2],sys.argv[3].split(),sys.argv[4],sys.argv[5]
best=-1
# Lo que el hub ya confirmó al drenar la cola, si es posterior a la foto de la proyección: una
# proyección vieja no puede hacer re-emitir eslabones ya aplicados (el hub los rechazaría).
try:
    ack=(json.load(open(acks_p)) or {}).get(sid) or {}
except Exception:
    ack={}
try:
    fa=json.load(open(proj_p)).get("fetched_at") or ""
    fetched=calendar.timegm(time.strptime(fa,"%Y-%m-%dT%H:%M:%SZ"))
except Exception:
    fetched=0
if isinstance(ack,dict) and ack.get("phase") in phases and float(ack.get("acked_at") or 0) >= fetched:
    best=phases.index(ack["phase"])
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

# Carril de micro-works (task_router.py): solo el TITULAR del micro-work opera estas rutas.
ops_path_micro_work_phase() { echo "/micro-works/$1/phase"; }
ops_path_micro_work_checkpoint() { echo "/micro-works/$1/checkpoint"; }
ops_path_micro_work_escalate() { echo "/micro-works/$1/escalate"; }
ops_path_micro_work_lease_renew() { echo "/micro-works/$1/lease/renew"; }

ops_mode() { runtime_mode; }

# ops_micro_work_id — id del micro-work reclamado y vivo según la caché del claim ("" si no hay).
ops_micro_work_id() { claim_micro_work_id; }

# Carpeta de esta biblioteca: de aquí se importa grafo_unidades.py (la derivación del change de una unidad).
OPS_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# _ops_claim_cache_py — escritura atómica 0600 de la caché del claim (.claude/state/claim.json).
# No lleva secretos, pero es working state de una sola máquina. Modo `write <lib>` (el JSON entra por
# stdin) o `set <clave> <valor>` (actualiza un escalar; sin caché no hace nada).
# [Hub real] En `write`, una unidad (no un micro-work) sale con su change RESUELTO: si el hub lo trae
# (`openspec_change`, carril graph-sync) se marca `openspec_change_origen: "hub"`; si viene null (grafo
# importado por el ADMIN: `EpicIn` no lo tiene) se guarda el derivado de `grafo_unidades.resolver_change`
# con origen "derivado". El resto de la respuesta se guarda tal cual. Sin la biblioteca, tal cual.
_OPS_CLAIM_CACHE_PY='
import json,sys,os,tempfile
path,modo=sys.argv[1],sys.argv[2]
if modo=="write":
    d=json.load(sys.stdin)
    if isinstance(d,dict) and d.get("work_type")!="micro_work" and len(sys.argv)>3:
        try:
            sys.dont_write_bytecode=True
            sys.path.insert(0,sys.argv[3])
            import grafo_unidades
            change,origen=grafo_unidades.resolver_change(d)
            if change:
                d["openspec_change"]=change
                d["openspec_change_origen"]=origen
        except Exception:
            pass
else:
    if not os.path.exists(path):
        raise SystemExit(0)
    d=json.load(open(path))
    d[sys.argv[3]]=sys.argv[4]
if not isinstance(d,dict):
    raise SystemExit(1)
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".claim.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.chmod(tmp,0o600)
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
'

# ops_claim_cache_write <json> — guarda la respuesta del claim (la escribe `slice-ops.sh claim`).
ops_claim_cache_write() {
  local file; file="$(claim_cache_path)"
  mkdir -p "$(dirname "$file")"
  command -v python3 >/dev/null 2>&1 || return 1
  printf '%s' "$1" | python3 -c "$_OPS_CLAIM_CACHE_PY" "$file" write "$OPS_LIB_DIR" 2>/dev/null
}

# ops_claim_cache_set <clave> <valor> — p. ej. la fase del micro-work tras un 200 del hub.
ops_claim_cache_set() {
  command -v python3 >/dev/null 2>&1 || return 1
  python3 -c "$_OPS_CLAIM_CACHE_PY" "$(claim_cache_path)" set "$1" "$2" </dev/null 2>/dev/null
}

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

# ops_context_hashes — sha256 EFECTIVO local de cada archivo gobernado del lock, leído en
# .claude/hub-context/<ruta del hub> (clave: la ruta del hub)
# (protocolo §3 regla 3: el servidor detecta drift/manipulación local comparándolos con los
# suyos). Se hashea el fichero real, NUNCA se repite el sha del lock: repetirlo convertiría
# el reporte en un espejo del servidor y el drift sería indetectable.
# Forma del reporte [#36]: el hub (`TasksNextIn.context_hashes: dict[str, str] | None`)
# exige un DICT {path: sha} — la lista [{"path":…,"sha256":…}] era 422 dict_type en TODO
# claim. Fallback {} (nunca []); fichero ilegible => "" (el dict no admite null en valores).
ops_context_hashes() {
  local lock base
  lock="$(runtime_lock_path)"
  base="$(runtime_context_dir)"
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  python3 -c "$_RUNTIME_CONTEXT_PATH_OK_PY"'
import json,sys,os,hashlib
lock,base,prefijos=sys.argv[1],sys.argv[2],sys.argv[3].split()
try:
    files=json.load(open(lock)).get("files") or []
except Exception:
    files=[]
out={}
for f in files:
    if not isinstance(f,dict):
        continue
    p=f.get("path")
    # Una ruta no gobernada (lock de un cliente anterior, lock manipulado) JAMÁS se sigue en
    # disco: se omite del reporte en vez de hashear lo que haya al otro lado de un `..`.
    if not ruta_gobernada(p, prefijos):
        continue
    sha=""
    try:
        h=hashlib.sha256()
        with open(os.path.join(base,p),"rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        sha=h.hexdigest()
    except Exception:
        sha=""
    out[p]=sha
print(json.dumps(out,ensure_ascii=False))
' "$lock" "$base" "$RUNTIME_CONTEXT_PREFIXES" 2>/dev/null || echo "{}"
}

# ops_enqueue_from_file <type> <payload_file> [slice_id] [client_event_id] — encola un evento cuyo
# payload puede ser grande (checklist de wiring, evidencia, contenido propuesto): el payload se lee
# del FICHERO dentro de python3, así que no pasa por argv (a diferencia de
# runtime_enqueue_event, que sigue sirviendo para payloads pequeños).
# [I1] El 4º argumento FIJA el `client_event_id` (vacío = uuid4 nuevo): el reencolado de un POST
# síncrono que falló lleva el MISMO id que ese POST, para que el hub deduplique si ya lo aplicó.
ops_enqueue_from_file() {
  local type="$1" pfile="$2" slice_id="${3:-}" cid_fijo="${4:-}" dir
  dir="$(runtime_outbox_dir)"
  mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$dir" "$type" "$pfile" "$slice_id" "$cid_fijo" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile,uuid,datetime
dir_,typ,pfile,slice_id,cid_fijo=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5]
try:
    payload=json.load(open(pfile))
except Exception:
    payload={}
cid=cid_fijo or str(uuid.uuid4())
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

# ops_new_cid — un `client_event_id` nuevo (uuid4); "" sin python3.
ops_new_cid() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 -c 'import uuid;print(uuid.uuid4())' 2>/dev/null
}

# ops_json_set_cid <json> <client_event_id> — el objeto JSON con `client_event_id` añadido (por stdin,
# nunca por argv). Con el id vacío o un JSON que no es objeto, imprime el JSON tal cual.
ops_json_set_cid() {
  [ -n "$2" ] || { printf '%s' "$1"; return; }
  command -v python3 >/dev/null 2>&1 || { printf '%s' "$1"; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
crudo=sys.stdin.read()
try:
    d=json.loads(crudo)
except Exception:
    sys.stdout.write(crudo); raise SystemExit(0)
if isinstance(d,dict):
    d["client_event_id"]=sys.argv[1]
    sys.stdout.write(json.dumps(d,ensure_ascii=False))
else:
    sys.stdout.write(crudo)
' "$2" 2>/dev/null || printf '%s' "$1"
}

# ops_outbox_pending [slice_id] — cuántos hechos esperan en la cola (outbox/*.json, sin los ficheros de
# control ni rejected/); con slice_id, solo los de ese slice. 0 si no hay cola o falta python3.
ops_outbox_pending() {
  local dir; dir="$(runtime_outbox_dir)"
  [ -d "$dir" ] || { echo 0; return; }
  command -v python3 >/dev/null 2>&1 || { echo 0; return; }
  python3 - "$dir" "${1:-}" <<'PY' 2>/dev/null || echo 0
import json,sys,glob,os
d,sid=sys.argv[1],sys.argv[2]
n=0
for p in glob.glob(os.path.join(d,"*.json")):
    if os.path.basename(p).startswith("."):
        continue
    if sid:
        try:
            if json.load(open(p)).get("slice_id")!=sid:
                continue
        except Exception:
            continue
    n+=1
print(n)
PY
}

# ── Ledger local de propuestas de épica [#62] ────────────────────────────────────────
# Memoria del ciclo «propongo → un humano aprueba → escribo el fichero con el código del
# hub». No es estado del pipeline (ese vive en el hub) sino el rastro de una conversación
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
