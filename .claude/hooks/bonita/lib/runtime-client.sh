#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/lib/runtime-client.sh
# runtime-client.sh — cliente bash del IA Hub (Agent Orchestrator Runtime) [EP-OR-08-A].
# Diseño: fail-open, igual que config.sh. Ninguna función bloquea ni lanza; ante red caída,
# curl/python3 ausentes, JSON corrupto o timeout, degrada a un valor vacío/código
# distinguible y jamás corrompe el estado local.
# Contrato de red: protocolo-cliente-runtime.md del arnés original (trycore-spec-build-harness)
# y el hub `trycore-ia-hub` (backend/app/modules/orchestrator/).
# Modo servidor SIEMPRE (U16): el estado de la unidad vive en el hub; lo local es caché
# (proyección, lock de contexto) y cola (outbox/). Sin hub se trabaja con la caché y se encola.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# runtime_mode — SIEMPRE "runtime" (U16). En el original elegía entre legacy|dual|runtime por
# TRYCORE_RUNTIME_MODE o runtime.mode; aquí no existe un modo con fuente de verdad local, así que
# se ignoran los dos a propósito: un entorno heredado del arnés original no puede apagar el hub.
# Se conserva la función porque los hooks copiados del original la consultan.
runtime_mode() {
  echo runtime
}

runtime_credentials_path() {
  echo "$(config_root)/.claude/state/runtime.credentials"
}

# runtime_field <clave> — lee un campo del fichero de credenciales. Vacío si falta.
runtime_field() {
  local key="$1" file
  file="$(runtime_credentials_path)"
  [ -f "$file" ] || { echo ""; return; }
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$file" "$key" <<'PY' 2>/dev/null
import json,sys
file,key=sys.argv[1],sys.argv[2]
try:
    d=json.load(open(file))
    v=d.get(key)
    print(v if v is not None else "")
except Exception:
    print("")
PY
}

# runtime_credentials_field_at <fichero> <clave> — lee un campo de un fichero de credenciales
# CONCRETO, sin pasar por config_root(). [#74] Es la única forma de mirar la identidad del clon
# principal desde un worktree: `runtime_field` resuelve por config_root(), que es justo lo que
# puede estar heredado — preguntarle «¿cuál es el agent_key del principal?» devolvía el propio.
runtime_credentials_field_at() {
  local file="$1" key="$2"
  [ -f "$file" ] || { echo ""; return; }
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$file" "$key" <<'PY' 2>/dev/null
import json,sys
file,key=sys.argv[1],sys.argv[2]
try:
    d=json.load(open(file))
    v=d.get(key)
    print(v if v is not None else "")
except Exception:
    print("")
PY
}

# runtime_credentials_merge <json> — hace upsert de las claves del fragmento sobre el
# fichero existente (o uno nuevo). Escritura atómica + chmod 0600. Nunca imprime el token.
runtime_credentials_merge() {
  runtime_credentials_merge_at "$(runtime_credentials_path)" "$1"
}

# runtime_credentials_merge_at <fichero> <json> — el mismo upsert sobre una RUTA EXPLÍCITA.
# [#74] `register` tiene que sembrar el fichero del worktree ANTES de que exista, y por tanto
# antes de que config_root() pueda anclar en local: pasando por runtime_credentials_path()
# habría hecho merge del token nuevo sobre el fichero del clon principal, pisándole la
# identidad al agente que está construyendo ahí.
runtime_credentials_merge_at() {
  local file="$1" fragment="$2" dir
  dir="$(dirname "$file")"
  mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$file" "$fragment" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile
path,frag=sys.argv[1],sys.argv[2]
try:
    d=json.load(open(path)) if os.path.exists(path) else {}
except Exception:
    d={}
if not isinstance(d,dict):
    d={}
d.update(json.loads(frag))
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".runtime-credentials.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.chmod(tmp,0o600)
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

# runtime_credentials_seed_at <fichero> <runtime_url> — siembra credenciales en una RUTA
# EXPLÍCITA con el token tomado de `TRYCORE_REGISTER_TOKEN`. [#74] El token viaja por ENTORNO
# y no por argv a propósito: `runtime_credentials_merge_at` recibe el fragmento como argumento
# y en una máquina compartida un `ps` lo vería. Es el único camino por el que un secreto entra
# de nuevo al fichero, así que es el único que necesita esta precaución.
# Escribe un documento NUEVO, no un upsert: dar de alta un árbol es estrenar identidad, y
# conservar el `agent_key` anterior haría que una respuesta 200 sin `agent_key` pareciera un alta
# buena (`register --force` para rotar el token es justo el caso). Lo que el hub devuelva vuelve a
# entrar por `runtime_register`. Escritura atómica + chmod 0600.
runtime_credentials_seed_at() {
  local file="$1" url="$2" dir
  dir="$(dirname "$file")"
  mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$file" "$url" <<'PY' 2>/dev/null || return 1
import json,os,sys,tempfile
path,url=sys.argv[1],sys.argv[2]
tok=os.environ.get("TRYCORE_REGISTER_TOKEN","")
if not tok:
    raise SystemExit(1)
d={"runtime_url":url,"project_token":tok}
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".runtime-credentials.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.chmod(tmp,0o600)
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

runtime_url() {
  runtime_field runtime_url
}

# runtime_status_file — fichero de estado para el código HTTP de la última llamada.
# NO se usa una variable global: toda función de este cliente se invoca vía sustitución
# de comandos (`body="$(runtime_get ...)"`), que bash ejecuta en una subshell — cualquier
# asignación de variable dentro de esa subshell se pierde al volver al shell padre. Un
# fichero en disco sí sobrevive ese límite (mismo principio que context.lock/credentials).
runtime_status_file() {
  echo "$(config_root)/.claude/state/.runtime-http-status"
}

# runtime_http_status — código HTTP de la última llamada a runtime_get/runtime_post.
runtime_http_status() {
  local sfile; sfile="$(runtime_status_file)"
  [ -f "$sfile" ] && cat "$sfile" || echo "000"
}

# _runtime_http <METHOD> <path> [body] — primitivo interno. Nunca lanza; ante fallo de
# red/curl/python3 deja runtime_http_status()=000 y stdout vacío. El body SIEMPRE se
# manda vía `--data-binary @fichero` (nunca `-d "$body"` directo): un body en argv está
# limitado por ARG_MAX del sistema (~1 MB típico) — con la cota del outbox en 5 MB
# (Task 8) un lote grande superaría ese límite y curl fallaría en silencio, fail-open,
# sin drenar nunca la cola. Un fichero no tiene ese límite.
# [Arnés Bonita] El token tampoco va en argv: el original pasaba `-H "Authorization: Bearer …"`
# y `ps` lo enseñaba durante cada register/claim/heartbeat/despacho. La cabecera se escribe con
# `printf` (builtin: sin proceso, sin argv) en un fichero 0600 que curl lee con `-H @fichero`
# (curl ≥ 7.55). El fichero vive dentro de la subshell de la llamada y su trap lo borra al
# salir, también ante INT/TERM/HUP.
# [Arnés Bonita] 4º argumento opcional: cabeceras EXTRA, una por línea («Nombre: valor»). Van al
# MISMO fichero 0600 que el bearer, nunca al argv. Una línea que no sea `Nombre: valor` limpio
# (sin CR/LF ni caracteres de control) se descarta: una cabecera inyectada no debe llegar a curl.
# `TRYCORE_HUB_TIMEOUT_S` (entero, por defecto 10) acota la petición.
_runtime_http() {
  local method="$1" path="$2" body="${3:-}" extra="${4:-}" url token tmp bodyfile="" status rc sfile tmo
  tmo="${TRYCORE_HUB_TIMEOUT_S:-10}"
  case "$tmo" in ''|*[!0-9]*|0) tmo=10 ;; esac
  url="$(runtime_url)${path}"
  token="$(runtime_field project_token)"
  sfile="$(runtime_status_file)"
  mkdir -p "$(dirname "$sfile")"
  if [ -z "$(runtime_url)" ] || ! command -v curl >/dev/null 2>&1; then
    printf '000' > "$sfile"
    return 1
  fi
  tmp="$(mktemp)" || { printf '000' > "$sfile"; return 1; }
  if [ -n "$body" ]; then
    bodyfile="$(mktemp)" || { printf '000' > "$sfile"; rm -f "$tmp"; return 1; }
    printf '%s' "$body" > "$bodyfile"
  fi
  status="$(
    hdr="$(umask 077 && mktemp)" || exit 97
    trap 'rm -f "$hdr"' EXIT
    trap 'exit 98' INT TERM HUP
    chmod 600 "$hdr" 2>/dev/null
    printf 'Authorization: Bearer %s\n' "$token" > "$hdr" || exit 97
    if [ -n "$extra" ]; then
      printf '%s\n' "$extra" | LC_ALL=C grep -E '^[A-Za-z0-9-]+: [ -~]+$' >> "$hdr"
    fi
    if [ -n "$bodyfile" ]; then
      curl -sS -m "$tmo" -o "$tmp" -w '%{http_code}' -X "$method" "$url" \
        -H "@$hdr" -H 'Content-Type: application/json' --data-binary "@$bodyfile" 2>/dev/null
    else
      curl -sS -m "$tmo" -o "$tmp" -w '%{http_code}' -X "$method" "$url" -H "@$hdr" 2>/dev/null
    fi
  )"
  rc=$?
  token=""
  [ -n "$bodyfile" ] && rm -f "$bodyfile"
  if [ $rc -ne 0 ] || [ -z "$status" ]; then
    printf '000' > "$sfile"
    rm -f "$tmp"
    return 1
  fi
  printf '%s' "$status" > "$sfile"
  cat "$tmp"
  rm -f "$tmp"
  return 0
}

runtime_get() { _runtime_http GET "$1" ""; }
runtime_post() { _runtime_http POST "$1" "$2"; }
runtime_put() { _runtime_http PUT "$1" "$2"; }
# runtime_post_headers <path> <body> <cabeceras> — POST con cabeceras extra (fichero 0600, no argv).
runtime_post_headers() { _runtime_http POST "$1" "$2" "$3"; }

# Tipos del carril directo cuyo endpoint deduplica por la cabecera `Idempotency-Key` (y no por un
# campo del cuerpo): la escalada del micro-work (task_router.py:763 → client_event_id). La clave es
# el `client_event_id` de la petición, el mismo en el primer intento y en cada reenvío: así una
# escalada que el hub aplicó pero cuya respuesta se perdió se reconoce y no rebota con 409.
RUNTIME_DIRECT_IDEMPOTENCY_KEY_TYPES="micro_work_escalated"

# runtime_register <harness_version> [asset_types_json="[]"]
# 0 = registrado (credenciales actualizadas) · 1 = fallo de red/parseo (fail-open, reintentable)
# 2 = 409 incompatible_version (no reintentar sin actualizar el arnés)
runtime_register() {
  local hv="$1" asset_types="${2:-[]}" resp status frag
  resp="$(runtime_post "/agents/register" "{\"harness_version\":\"$hv\",\"asset_types\":$asset_types}")"
  status="$(runtime_http_status)"
  case "$status" in
    200)
      command -v python3 >/dev/null 2>&1 || return 1
      frag="$(python3 - "$resp" <<'PY'
import json,sys
try:
    d=json.loads(sys.argv[1])
    out={k:d.get(k) for k in ("agent_key","project_id","poll_interval_s","lease_ttl_s","manifest_hash") if k in d}
    print(json.dumps(out))
except Exception:
    print("{}")
PY
)"
      runtime_credentials_merge "$frag" || return 1
      return 0
      ;;
    409)
      echo "⛔ runtime_register: versión del arnés incompatible con el runtime — $resp" >&2
      return 2
      ;;
    *)
      return 1
      ;;
  esac
}

runtime_lock_path() {
  echo "$(config_root)/.claude/state/context.lock"
}

# Directorio de contexto del agente: los assets del hub se materializan en
# `<raíz>/.claude/hub-context/<ruta del hub>` — nunca en el `docs/` del proyecto ni en ningún otro
# sitio. El hub solo gobierna rutas bajo `context/` y `docs/` (context_domain.GOVERNED_PREFIXES,
# trycore-ia-hub origin/develop); el lock y los `context_hashes` del claim usan la ruta del hub
# como clave y hashean el fichero en este directorio. Es caché (está en el .gitignore del bloque).
RUNTIME_CONTEXT_DIR=".claude/hub-context"
RUNTIME_CONTEXT_PREFIXES="context/ docs/"

# _RUNTIME_CONTEXT_PATH_OK_PY — predicado python `ruta_gobernada(path, prefijos)` compartido por
# context-sync.sh (antes de escribir) y ops_context_hashes (antes de leer): relativa, POSIX,
# normalizada, sin `..`, `~`, `\` ni NUL, y bajo uno de los prefijos del hub.
_RUNTIME_CONTEXT_PATH_OK_PY='
import posixpath
def ruta_gobernada(path, prefijos):
    if not isinstance(path, str) or not path or path != path.strip():
        return False
    if path.startswith(("/", "~")) or "\\" in path or "\x00" in path:
        return False
    if len(path) > 1 and path[1] == ":":
        return False
    if any(p in ("", ".", "..") for p in path.split("/")) or path != posixpath.normpath(path):
        return False
    return path.startswith(tuple(prefijos))
'

# runtime_context_dir — ruta absoluta del directorio de contexto del agente.
runtime_context_dir() { echo "$(config_root)/$RUNTIME_CONTEXT_DIR"; }

runtime_lock_manifest_hash() {
  local file; file="$(runtime_lock_path)"
  [ -f "$file" ] || { echo ""; return; }
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$file" <<'PY' 2>/dev/null
import json,sys
try:
    print(json.load(open(sys.argv[1])).get("manifest_hash",""))
except Exception:
    print("")
PY
}

# runtime_lock_write <manifest_hash> [files_json="[]"]
runtime_lock_write() {
  local hash="$1" files="${2:-[]}" file dir
  file="$(runtime_lock_path)"; dir="$(dirname "$file")"
  mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$file" "$hash" "$files" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile,datetime
path,h,files=sys.argv[1],sys.argv[2],sys.argv[3]
d={"manifest_hash":h,
   "synced_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
   "files":json.loads(files)}
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".context.lock.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

runtime_projection_path() {
  echo "$(config_root)/.claude/state/runtime-projection.json"
}

# runtime_disconnected — 0 si este agente NO puede ver el estado del hub; 1 si sí (o si el
# proyecto aún no está registrado).
#
# Existe para separar dos situaciones que hasta ahora colapsaban en el mismo
# `exit 0` de los guards y que significan lo contrario:
#
#   auto-arme     el proyecto todavía no usa el arnés (no hay credenciales) →
#                 no hay nada que vigilar y hay que dejar trabajar.
#   desconectado  el proyecto SÍ está registrado (hay credenciales) pero falta la
#                 proyección → el agente no sabe qué le manda el hub. Aquí callar
#                 es peor que estorbar: es exactamente el estado en el que dos
#                 workers reclaman el mismo trabajo o pisan los mismos ficheros.
runtime_disconnected() {
  [ -f "$(runtime_credentials_path)" ] || return 1   # auto-arme legítimo
  [ -f "$(runtime_projection_path)" ] && return 1
  return 0
}

runtime_projection_read() {
  local file; file="$(runtime_projection_path)"
  [ -f "$file" ] || { echo "{}"; return; }
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  python3 - "$file" <<'PY' 2>/dev/null
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(json.dumps(d))
except Exception:
    print("{}")
PY
}

runtime_projection_write() {
  local body="$1" file dir
  file="$(runtime_projection_path)"; dir="$(dirname "$file")"
  mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$file" "$body" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile
path,body=sys.argv[1],sys.argv[2]
d=json.loads(body)
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".runtime-projection.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

# _runtime_graph_version — versión de grafo conocida por la proyección local ("" si el hub no
# versiona o no hay caché). Vive aquí, y no en projection.sh, porque el despacho de la outbox
# la necesita y projection.sh depende de este fichero (invertirlo sería un ciclo de sourcing).
_runtime_graph_version() {
  local f; f="$(runtime_projection_path)"
  [ -f "$f" ] || { echo ""; return; }
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$f" <<'PY' 2>/dev/null || echo ""
import json,sys
try:
    v=(json.load(open(sys.argv[1])).get("context") or {}).get("graph_version")
except Exception:
    v=None
print("" if v is None else v)
PY
}

runtime_graph_status_path() { echo "$(config_root)/.claude/state/graph-status.json"; }

# runtime_graph_note_stale <local> <servidor> — deja constancia de que el hub rechazó una
# acción por grafo rancio [#63]. Es lo que hace VISIBLE el desfase en `status`: sin este
# rastro, el 409 se resolvería solo y el usuario nunca sabría que ocurrió.
# Una versión ausente (cadena vacía) se graba como `null`, NUNCA como 0: «no sé qué versión
# tenía» y «tenía la versión cero» son cosas distintas, y la segunda mentiría en `status`.
# [Ronda final] El fallo de escritura ya NO se traga: se avisa y se devuelve rc 1. Tragarlo
# borraba en silencio justo el rastro que esta función existe para dejar — el desfase habría
# ocurrido y nadie podría verlo.
runtime_graph_note_stale() {
  local local_v="$1" server_v="$2" f
  f="$(runtime_graph_status_path)"
  mkdir -p "$(dirname "$f")"
  command -v python3 >/dev/null 2>&1 || { echo "⚠ sin python3: no se pudo anotar el desfase de grafo (local v${local_v:-?}, hub v${server_v:-?})" >&2; return 1; }
  python3 - "$f" "$local_v" "$server_v" <<'PY' 2>/dev/null || { echo "⚠ no se pudo anotar el desfase de grafo en $f (local v${local_v:-?}, hub v${server_v:-?}): no será visible en \`status\`" >&2; return 1; }
import json,sys,os,tempfile,datetime
path,lv,sv=sys.argv[1],sys.argv[2],sys.argv[3]
def num(x):
    try: return int(x)
    except Exception: return None
d={"local":num(lv),"server":num(sv),
   "seen_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".graph-status.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
  return 0
}

runtime_graph_status_read() {
  local f; f="$(runtime_graph_status_path)"
  [ -f "$f" ] || { echo "{}"; return; }
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  python3 - "$f" <<'PY' 2>/dev/null || echo "{}"
import json,sys
try:
    print(json.dumps(json.load(open(sys.argv[1]))))
except Exception:
    print("{}")
PY
}

# runtime_graph_clear_stale — el desfase dejó de existir (la proyección alcanzó al servidor).
runtime_graph_clear_stale() { rm -f "$(runtime_graph_status_path)" 2>/dev/null; return 0; }

# runtime_stale_graph_version <respuesta-json> — ¿este 409 dice que nuestro grafo va rancio?
# rc 0 = sí (imprime la versión vigente del servidor, o vacío si no la manda) · rc 1 = no.
#
# [EP-OR-17] Existe porque el cliente leía `{"reason":"stale_graph"}` en la RAÍZ y el hub emite
# `{"detail":{"error":"graph_version_stale","graph_version":N}}` — un HTTPException de FastAPI
# anida SIEMPRE bajo `detail`, y el literal `stale_graph` no aparece en ninguna parte de su
# backend. Con la lectura vieja, un claim con grafo rancio NO se reintentaba y una propuesta se
# apartaba como rechazo definitivo: dos caminos que existían para tolerar el desfase y que en
# realidad nunca se tomaban. Se aceptan las dos formas — si una instancia anterior al contrato
# emitiera la plana, seguiría entendiéndose.
# Fail-CLOSED a propósito, al revés que el resto del cliente: ante JSON ilegible o sin python3
# devuelve rc 1 («no es un stale»). Tratar un rechazo cualquiera como grafo rancio lo dejaría
# reintentando en bucle contra un hub que nunca va a aceptarlo.
runtime_stale_graph_version() {
  command -v python3 >/dev/null 2>&1 || return 1
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    raise SystemExit(1)
if not isinstance(d,dict):
    raise SystemExit(1)
det=d.get("detail")
fuente=det if isinstance(det,dict) else d
marca=fuente.get("error") or fuente.get("reason") or ""
if marca not in ("graph_version_stale","stale_graph"):
    raise SystemExit(1)
v=fuente.get("graph_version")
if v is None:
    v=d.get("graph_version")
sys.stdout.write("" if v is None else str(v))
' 2>/dev/null
}

RUNTIME_OUTBOX_MAX_BYTES=5242880
RUNTIME_OUTBOX_MAX_AGE_S=259200
# [EP-OR-08-C] Los hechos de dominio que emiten las skills (slice-ops.sh) tampoco se evictan:
# perder un `slice_archived` o un `wiring_item_updated` dejaría la proyección del servidor
# mintiendo. El volumen evictable es `progress_noted`.
# [#38] Los hechos máquina de proyecto viajan como UN solo tipo del catálogo v2
# (`project_fact_updated`); los cinco alias legados (`scaffold_confirmed`,
# `design_source_declared`, `project_kind_declared`, `foundation_declared`,
# `harness_phase_changed`) ya no se encolan y salieron de la lista.
# [#44] La lista lleva los NOMBRES DEL CATÁLOGO v2 del hub (event_catalog.SCHEMAS):
# proteger de la evicción un tipo que el hub va a rechazar era absurdo.
# [U16] Sin los alias 0.10.x (`checkpoint_created`, `verdict_reported`, `escalation_raised`):
# el arnés Bonita nunca tuvo consumidores 0.10.x y la lista debe coincidir con los nombres de
# `event_catalog.SCHEMAS` del hub (lo comprueba check-contrato-hub.py, tarea 10).
# [#52] `phase_advanced` es protegido: el orden de fases del hub es ESTRICTO — evictar un
# eslabón de la cadena haría ilegales todos los eventos posteriores del slice (incluido el
# slice_archived, que exige phase == pr).
# [#62] `epic_proposed` viaja por el CARRIL DIRECTO (su propio endpoint, no el lote de
# /events) pero comparte cola y cota: evictar una propuesta de épica perdería trabajo humano
# ya redactado y aprobado en la terminal, sin rastro en el hub.
# [Arnés Bonita] Los tres del carril de micro-works (carril directo, /micro-works/{id}/…) son
# protegidos por el mismo motivo que `phase_advanced`: el orden de fases del micro-work es
# estricto, y perder un checkpoint o una escalada es perder el punto de retorno o la salida del
# carril sin rastro en el hub.
RUNTIME_OUTBOX_PROTECTED="checkpoint_recorded gate_verdict slice_escalated slice_submitted slice_archived handoff_recorded telemetry_gap wiring_checklist_seeded wiring_item_updated project_fact_updated phase_advanced epic_proposed micro_work_phase_advanced micro_work_checkpointed micro_work_escalated"

runtime_outbox_dir() {
  echo "$(config_root)/.claude/state/outbox"
}

# runtime_phase_acks_path — última fase que el hub CONFIRMÓ por slice al drenar la cola
# ({slice_id: {"phase": …, "acked_at": epoch}}). Cubre el hueco entre «la cola drenó» y «la
# proyección se refrescó»: sin él, un `phase` con el hub caído justo después de drenar
# recalculaba la cadena desde la proyección vieja y re-emitía eslabones ya aplicados, que el hub
# rechaza uno a uno y acaban en outbox/rejected/ (ruido visible en status/doctor). Solo cuenta si
# es posterior al `fetched_at` de la proyección (ops_known_phase).
runtime_phase_acks_path() {
  echo "$(config_root)/.claude/state/phase-acks.json"
}

# [I4] Marca de credenciales rechazadas al DESPACHAR la cola: {"status": "401"|"403", "lane": "lote"|"directo",
# "at": ISO}. Un 401/403 no es «el contrato rechazó este evento» sino «el token no sirve ahora» (expirado o rotado
# por el ADMIN): la cola se conserva y la marca la enseñan `slice-ops.sh status`, `trycore-bonita status/doctor`
# y el bloque runtime; `register --force` la borra y el siguiente ciclo drena. Nunca lleva el token.
runtime_auth_status_path() { echo "$(config_root)/.claude/state/auth-status.json"; }

# runtime_auth_mark <status> <carril> — escribe la marca (atómica). Nunca lanza.
runtime_auth_mark() {
  local f; f="$(runtime_auth_status_path)"
  mkdir -p "$(dirname "$f")"
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$f" "$1" "$2" <<'PY' 2>/dev/null
import json,sys,os,tempfile,datetime
path,st,lane=sys.argv[1],sys.argv[2],sys.argv[3]
d={"status":st,"lane":lane,"at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
fd,tmp=tempfile.mkstemp(dir=os.path.dirname(path) or ".",prefix=".auth-status.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2)
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
PY
  return 0
}

# runtime_auth_clear [fichero] — borra la marca (tras un despacho aceptado o un `register --force`).
runtime_auth_clear() { rm -f "${1:-$(runtime_auth_status_path)}" 2>/dev/null; return 0; }

# runtime_enqueue_event <type> <payload_json> [slice_id] — encola un evento con
# client_event_id propio (idempotencia server-side) y aplica la cota tras encolar.
# [EP-OR-08-B] `slice_id` es OPCIONAL y se escribe como clave de PRIMER NIVEL del evento
# (no dentro de payload): `POST /events` lo exige por elemento para los tipos de ámbito
# slice. Sin él, el evento se manda sin la clave — el ámbito proyecto la omite a propósito.
runtime_enqueue_event() {
  local type="$1" payload="$2" slice_id="${3:-}" dir
  dir="$(runtime_outbox_dir)"; mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$dir" "$type" "$payload" "$slice_id" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile,uuid,datetime
dir_,typ,payload,slice_id=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
cid=str(uuid.uuid4())
ts=datetime.datetime.now(datetime.timezone.utc)
d={"client_event_id":cid,"type":typ,"payload":json.loads(payload),
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

# runtime_enqueue_direct <type> <method> <path> <payload_file> [stamp_graph_version]
#                        [client_event_id] — encola
# una petición del CARRIL DIRECTO [#62]: un hecho que NO viaja en el lote de `POST /events`
# sino a su propio endpoint (hoy: la propuesta de épica, hub#113). Comparte con la cola de
# eventos el directorio, el formato en disco, la cota y el sentinela de flush; lo único
# distinto es a dónde se despacha. Imprime el `client_event_id` (referencia local mientras el
# hub no ha asignado el suyo). El payload va por FICHERO, nunca por argv.
# La RUTA llega ya resuelta: runtime-client.sh no conoce la tabla de endpoints — la escribe
# quien sí la conoce (lib/runtime-ops.sh), que es el único sitio del cliente con rutas.
# [#63] Con `1` en el 5º argumento, el fichero se marca para que el DESPACHO le estampe la
# versión de grafo vigente. Sellarla al encolar sería un error: una propuesta que espera dos
# días en la cola offline saldría con la versión de hace dos días y nacería condenada al 409.
# [EP-OR-17] El 6º argumento fija el `client_event_id` en vez de generarlo: lo usa el re-sync
# del grafo, donde el reintento tiene que llevar la MISMA identidad para que el hub deduplique
# en vez de crear una segunda propuesta. Vacío (o ausente) = uuid4, como siempre.
runtime_enqueue_direct() {
  local type="$1" method="$2" path="$3" pfile="$4" stamp="${5:-0}" cid_fijo="${6:-}" dir
  dir="$(runtime_outbox_dir)"; mkdir -p "$dir"
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$dir" "$type" "$method" "$path" "$pfile" "$stamp" "$cid_fijo" <<'PY' 2>/dev/null || return 1
import json,sys,os,tempfile,uuid,datetime
dir_,typ,method,path,pfile,stamp,cid_fijo=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],sys.argv[6],sys.argv[7]
try:
    payload=json.load(open(pfile))
except Exception:
    payload={}
# [EP-OR-17] Un cid FIJADO por el productor es lo que hace idempotente el reintento: el hub
# deduplica por `client_event_id`, así que re-encolar el mismo re-sync tras un 409 de grafo
# rancio no crea una segunda propuesta del mismo grafo. Sin él se conserva el uuid4 de siempre,
# que es lo que quiere el carril de propuesta de épica (cada propuesta es una épica distinta).
cid=cid_fijo or str(uuid.uuid4())
ts=datetime.datetime.now(datetime.timezone.utc)
d={"client_event_id":cid,"type":typ,"channel":"direct","method":method,"path":path,
   "payload":payload,"enqueued_at":ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
if stamp=="1":
    d["stamp_graph_version"]=True
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
print(cid)
PY
  runtime_outbox_enforce_cap >/dev/null
}

# _runtime_direct_field <fichero> <clave> — escalar de primer nivel de una petición encolada
# ("" si falta o el fichero es ilegible).
_runtime_direct_field() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$1" "$2" <<'PY' 2>/dev/null
import json,sys
try:
    v=json.load(open(sys.argv[1])).get(sys.argv[2])
except Exception:
    v=None
print("" if v is None else v)
PY
}

# _runtime_direct_payload <fichero> — imprime el cuerpo que viaja al endpoint del carril
# directo: el payload guardado MÁS el `client_event_id` como CLAVE DE IDEMPOTENCIA ("{}" si
# falla). [#62 · ronda final] Sin esa clave el hub no podía deduplicar el carril directo: el
# lote de `/events` la lleva desde siempre (protocolo §5), pero aquí el `client_event_id`
# vivía solo como clave de primer nivel del FICHERO y no salía en la petición. Con dos
# despachadores posibles (el daemon y el proceso de la skill), un doble envío de la misma
# propuesta creaba DOS propuestas y, al aprobarlas, dos `EP-XXX` — la colisión que motiva #62,
# reintroducida por el otro extremo. Se estampa al armar el cuerpo, no al encolar: el formato
# en disco no cambia y los ficheros ya encolados drenan sin migración.
_runtime_direct_payload() {
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  python3 - "$1" <<'PY' 2>/dev/null || echo "{}"
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    p=d.get("payload")
    if p is None:
        p={}
    # [I6] Los cuerpos del micro-work (MicroWorkPhaseIn, MicroWorkCheckpointIn, MicroWorkEscalateAgentIn) no
    # declaran `client_event_id`: el hub lo descartaba y la escalada deduplica por la cabecera Idempotency-Key.
    if isinstance(p,dict) and not str(d.get("type") or "").startswith("micro_work_"):
        cid=d.get("client_event_id")
        # Un `client_event_id` ya presente en el payload manda: lo puso quien encoló y
        # sobrescribirlo cambiaría la identidad de la petición a espaldas del productor.
        if cid and "client_event_id" not in p:
            p["client_event_id"]=cid
    print(json.dumps(p,ensure_ascii=False))
except Exception:
    print("{}")
PY
}

# _runtime_reject_file <fichero> <razón> — aparta una petición a rejected/ con su razón
# PERSISTIDA (la muestran `slice-ops.sh status` y `trycore-bonita status/doctor`: el stderr de
# un daemon no lo lee nadie). Nunca lanza.
_runtime_reject_file() {
  local f="$1" reason="$2" rdir
  rdir="$(runtime_outbox_dir)/rejected"
  mkdir -p "$rdir"
  echo "⚠ $reason" >&2
  command -v python3 >/dev/null 2>&1 || { mv "$f" "$rdir/" 2>/dev/null; return 0; }
  # [#62] Escritura ATÓMICA del apartado: `tempfile.mkstemp` en el mismo directorio destino
  # + `os.replace` (restricción dura de la spec). Un `json.dump` directo a `dest` deja un
  # fichero truncado legible a medio escribir si el proceso muere entre el open y el flush —
  # inaceptable para algo que `slice-ops.sh status`/`trycore-bonita doctor` leen en caliente.
  python3 - "$f" "$rdir" "$reason" <<'PY' 2>/dev/null || mv "$f" "$rdir/" 2>/dev/null
import json,sys,os,tempfile
f,rdir,reason=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(f))
except Exception:
    d=None
dest=os.path.join(rdir,os.path.basename(f))
if isinstance(d,dict):
    d["rejected_reason"]=reason
    fd,tmp=tempfile.mkstemp(dir=rdir,prefix=".rejected.",suffix=".tmp")
    try:
        with os.fdopen(fd,"w") as out:
            json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
        os.replace(tmp,dest)
        os.unlink(f)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
else:
    os.replace(f,dest)
PY
  return 0
}

# _runtime_ack_direct <fichero> <respuesta-cruda> — deja el acuse en acks/<client_event_id>.json.
# El ledger de dominio (qué propuesta es, en qué estado está) NO vive aquí: runtime-client.sh
# es agnóstico al dominio. Quien correlaciona es lib/runtime-ops.sh.
_runtime_ack_direct() {
  local f="$1" resp="$2" adir
  adir="$(runtime_outbox_dir)/acks"
  mkdir -p "$adir"
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$f" "$adir" "$resp" <<'PY' 2>/dev/null
import json,sys,os,tempfile,datetime
f,adir,resp=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(f))
except Exception:
    d={}
try:
    body=json.loads(resp)
except Exception:
    body={}
cid=d.get("client_event_id") or "sin-id"
out={"client_event_id":cid,"type":d.get("type"),"status":"acked","response":body,
     "acked_at":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
path=os.path.join(adir,cid+".json")
fd,tmp=tempfile.mkstemp(dir=adir,prefix=".ack.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as fh:
        json.dump(out,fh,indent=2,ensure_ascii=False); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
PY
  return 0
}

# runtime_outbox_enforce_cap — cota 5MB/72h. Descarta primero los eventos NO protegidos
# (más viejos primero); jamás descarta un tipo de RUNTIME_OUTBOX_PROTECTED. Si hubo
# descartes, encola un telemetry_gap con el payload EXACTO del catálogo v2 [#44]
# (TelemetryGap: {dropped>=1, window_h>0, reason<=2000}; extra="forbid" — el
# {dropped_count, dropped_types} de 0.10.x era rechazo garantizado): `dropped` es el
# conteo, `window_h` la ventana de la cota en horas y `reason` el motivo con los tipos
# descartados. Imprime en stdout el conteo de descartados (última línea).
runtime_outbox_enforce_cap() {
  local dir; dir="$(runtime_outbox_dir)"
  [ -d "$dir" ] || { echo 0; return 0; }
  command -v python3 >/dev/null 2>&1 || { echo 0; return 0; }
  python3 - "$dir" "$RUNTIME_OUTBOX_MAX_BYTES" "$RUNTIME_OUTBOX_MAX_AGE_S" "$RUNTIME_OUTBOX_PROTECTED" <<'PY' 2>/dev/null
import json,os,sys,time,tempfile,uuid,datetime
dir_,max_bytes,max_age,protected=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),set(sys.argv[4].split())
files=[]
total=0
now=time.time()
for name in os.listdir(dir_):
    if not name.endswith(".json") or name.startswith("."):
        continue
    p=os.path.join(dir_,name)
    try:
        st=os.stat(p)
        d=json.load(open(p))
    except Exception:
        continue
    files.append((st.st_mtime,p,d.get("type","")))
    total+=st.st_size
files.sort()
dropped=[]
over_size=total>max_bytes
for mtime,p,typ in files:
    over_age=(now-mtime)>max_age
    if not (over_size or over_age):
        break
    if typ in protected:
        continue
    try:
        sz=os.path.getsize(p)
        os.unlink(p)
        total-=sz
        dropped.append(typ)
    except OSError:
        pass
    over_size=total>max_bytes
if dropped:
    # Coalescer en un telemetry_gap YA en cola (no despachado) en vez de acumular uno
    # por descarte: telemetry_gap es protegido (nunca se evicta), así que sin coalescer
    # crece sin límite mientras la cola siga sobre la cota.
    existing_gap_path=None
    existing_gap=None
    for name in os.listdir(dir_):
        if not name.endswith(".json") or name.startswith("."):
            continue
        p=os.path.join(dir_,name)
        try:
            d=json.load(open(p))
        except Exception:
            continue
        if d.get("type")=="telemetry_gap":
            existing_gap_path=p
            existing_gap=d
            break
    window_h=max_age/3600.0
    def resumen(tipos):
        counts={}
        for t in tipos:
            k=t or "desconocido"
            counts[k]=counts.get(k,0)+1
        return ", ".join("%s x%d" % kv for kv in sorted(counts.items()))
    encabezado="evicción por cota de la outbox (%d bytes / %.0f h)" % (max_bytes, window_h)
    if existing_gap_path:
        payload=existing_gap.get("payload") or {}
        prev_n=payload.get("dropped",0) or 0
        base=payload.get("reason") if isinstance(payload.get("reason"),str) else ""
        texto=("%s; %s" % (base, resumen(dropped))) if base else ("%s: %s" % (encabezado, resumen(dropped)))
        gap=existing_gap
        gap["payload"]={"dropped": prev_n+len(dropped), "window_h": window_h, "reason": texto[:2000]}
        fname=existing_gap_path
        fd,tmp=tempfile.mkstemp(dir=dir_,prefix=".outbox.",suffix=".tmp")
    else:
        cid=str(uuid.uuid4())
        ts=datetime.datetime.now(datetime.timezone.utc)
        gap={"client_event_id":cid,"type":"telemetry_gap",
             "payload":{"dropped":len(dropped),"window_h":window_h,
                        "reason":("%s: %s" % (encabezado, resumen(dropped)))[:2000]},
             "enqueued_at":ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
        fname=os.path.join(dir_, ts.strftime("%Y%m%d%H%M%S%f")+"-"+cid+".json")
        fd,tmp=tempfile.mkstemp(dir=dir_,prefix=".outbox.",suffix=".tmp")
    try:
        with os.fdopen(fd,"w") as out:
            json.dump(gap,out,indent=2,ensure_ascii=False)
        os.replace(tmp,fname)
    except Exception:
        # No re-lanzar: la evicción YA tuvo éxito: fallar aquí no debe ocultar ese
        # resultado ni romper el contrato de stdout (print(len(dropped)) siempre corre).
        try: os.unlink(tmp)
        except OSError: pass
print(len(dropped))
PY
}

RUNTIME_OUTBOX_BACKOFF_SCHEDULE="1 5 30 300"

# _runtime_partition_outbox <fichero…> — imprime "direct <ruta>", "batch <ruta>" o
# "bad <ruta>" por línea. Una sola invocación de python3 para todos los ficheros: el despacho
# corre en el hilo del daemon cada pocos segundos y no puede pagar un proceso por fichero.
# [#62 · ronda final] La tercera clase existe porque un fichero ILEGIBLE (JSON corrupto, o un
# JSON que no es un objeto) no se puede afirmar que sea del lote: clasificarlo como `batch`
# lo condenaba a saltarse en silencio al armar el cuerpo y a quedarse atascado PARA SIEMPRE
# —una pérdida muda sobre un tipo que además está protegido de la evicción por cota—. El
# llamador lo aparta a rejected/ nombrando la causa.
_runtime_partition_outbox() {
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$@" <<'PY' 2>/dev/null
import json,sys
for p in sys.argv[1:]:
    try:
        d=json.load(open(p))
    except Exception:
        d=None
    if not isinstance(d,dict):
        print("bad "+p)
        continue
    print(("direct " if d.get("channel")=="direct" else "batch ")+p)
PY
}

# _runtime_bump_field <fichero> <clave> <valor-entero> — persiste un contador dentro de la
# petición encolada (escritura atómica, con `fsync` — mismo patrón que el resto del fichero).
# Sin esto, el conteo de 409 viviría en memoria y se perdería entre ciclos del daemon: el
# reintento sería infinito por construcción. [Ronda de arreglo 1, Important 2] El fallo YA NO
# se traga: se propaga (rc distinguible) para que el llamador aparte el fichero en vez de
# reintentar para siempre sin poder nunca completar el conteo.
_runtime_bump_field() {
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$1" "$2" "$3" <<'PY' 2>/dev/null
import json,sys,os,tempfile
path,key,val=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(path))
except Exception:
    raise SystemExit(1)   # fichero ilegible: rc distinguible, el llamador decide (no reintento ciego)
d[key]=int(val)
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".outbox.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

# _runtime_mark_graph_409 <fichero> <n> <version-local> — persiste el conteo de rechazos por
# grafo rancio Y la versión local con la que se produjeron. Los dos campos van juntos porque la
# racha es «tres rechazos contra la MISMA versión local», no «tres rechazos a secas» (ver
# _runtime_dispatch_direct). Escritura atómica con fsync y fallo propagado (rc distinguible),
# igual que _runtime_bump_field: si el conteo no se puede persistir, el llamador aparta el
# fichero en vez de reintentar sin fin.
_runtime_mark_graph_409() {
  command -v python3 >/dev/null 2>&1 || return 1
  python3 - "$1" "$2" "$3" <<'PY' 2>/dev/null
import json,sys,os,tempfile
path,n,gv=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(path))
except Exception:
    raise SystemExit(1)   # fichero ilegible: rc distinguible, el llamador decide
d["graph_409"]=int(n)
# Ausencia de versión = None, nunca 0: «salió sin estampar» y «salió con la versión 0» son
# cosas distintas, y confundirlas haría que la racha se reiniciara sola sin motivo.
d["graph_409_at_version"]=gv if gv else None
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".outbox.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
PY
}

# _runtime_dispatch_direct <fichero…> — despacha el carril directo UNO a uno (cada petición
# tiene su endpoint; no hay lote que armar). Contrato de resultado por fichero:
#   200|201|202|204        → ack en acks/, se borra el fichero y se limpia el desfase de grafo
#                            si había uno anotado (la petición llegó, luego ya no vamos rancios).
#   404                    → el hub NO implementa esa ruta (instancia sin soporte, hub#113
#                            pendiente): se aparta diciéndolo con esas palabras.
#   409 reason=stale_graph → grafo rancio [#63]: se anota el desfase y se CONSERVA (no es un
#                            rechazo de contrato); a los 3 seguidos se aparta. Cualquier OTRO
#                            409 (propuesta duplicada, conflicto de estado…) sigue el camino
#                            normal de rechazo de contrato — el `reason` es lo único que decide.
#   401 · 403              → token no utilizable [I4]: se CONSERVA, se marca auth-status.json y se corta
#                            (salvo el 403 de las rutas del micro-work: titularidad, se aparta).
#   4xx (salvo 401/403/404/408/409-stale_graph/429) → rechazo de contrato: se aparta a rejected/.
#   000 · 5xx · 408 · 429  → transitorio: se CONSERVA y se reintenta en el próximo ciclo.
# rc 1 si algo quedó pendiente por causa transitoria, 0 si no queda nada del carril.
# No agenda backoff propio a propósito: el carril directo es de volumen bajísimo (una
# propuesta de épica) y compartir el backoff del lote dejaría los hechos de dominio del slice
# esperando detrás de una propuesta. El ritmo real de reintento lo marca el ciclo del daemon.
_runtime_dispatch_direct() {
  local f rc=0 resp status type path method payload gv server_gv n409 prev_gv stamped extra
  for f in "$@"; do
    [ -f "$f" ] || continue
    # [Ronda final] `gv` se reinicia POR ITERACIÓN: es `local` a la función y solo se asigna
    # dentro del `if stamp_graph_version`, así que un fichero sin estampar que recibiera un 409
    # heredaba la versión del fichero anterior y la usaba en el mensaje, en el marcador de
    # desfase y en la racha — un dato inventado con apariencia de medida.
    gv=""
    type="$(_runtime_direct_field "$f" type)"
    method="$(_runtime_direct_field "$f" method)"
    path="$(_runtime_direct_field "$f" path)"
    [ -n "$method" ] || method=POST
    if [ -z "$path" ]; then
      _runtime_reject_file "$f" "petición directa sin ruta de despacho (fichero corrupto): no se envió"
      continue
    fi
    payload="$(_runtime_direct_payload "$f")"
    # [#63] Estampado AL DESPACHAR, con la versión que la proyección tenga en ESTE instante.
    if [ "$(_runtime_direct_field "$f" stamp_graph_version)" = "True" ]; then
      gv="$(_runtime_graph_version)"
      if [ -n "$gv" ]; then
        # [Ronda de arreglo 1, Important 1] Si `$gv` no es un entero válido (hub#115 aún no
        # existe: nada coacciona el tipo en `agent-context.sh`), `int()` lanza y python no
        # imprime nada — NUNCA se sobrescribe `payload` con esa cadena vacía, o la petición
        # saldría sin cuerpo y el 4xx del hub se reportaría como "rechazo del hub" en vez de
        # como el fallo de estampado que de verdad es.
        stamped="$(printf '%s' "$payload" | python3 -c 'import json,sys; d=json.load(sys.stdin); d["graph_version"]=int(sys.argv[1]); print(json.dumps(d,ensure_ascii=False))' "$gv" 2>/dev/null)"
        [ -n "$stamped" ] && payload="$stamped"
      fi
    fi
    extra=""
    case " $RUNTIME_DIRECT_IDEMPOTENCY_KEY_TYPES " in
      *" $type "*) extra="Idempotency-Key: $(_runtime_direct_field "$f" client_event_id)" ;;
    esac
    resp="$(_runtime_http "$method" "$path" "$payload" "$extra")"
    status="$(runtime_http_status)"
    case "$status" in
      # 204: respuesta sin cuerpo del checkpoint del micro-work (task_router.py del hub).
      200|201|202|204)
        _runtime_ack_direct "$f" "$resp"
        rm -f "$f"
        runtime_auth_clear
        runtime_graph_clear_stale ;;
      403)
        # [I4] En las rutas del micro-work el 403 NO es el token: es «solo el titular opera su micro-work»
        # (task_router.py), un rechazo de dominio que reintentar no arregla. El resto, como el 401.
        case "$type" in
          micro_work_*)
            _runtime_reject_file "$f" "el hub rechazó «${type}» (HTTP 403): $resp — no se reintentará"
            continue ;;
        esac
        runtime_auth_mark "$status" directo
        echo "⛔ el hub no acepta el token (HTTP $status) al despachar «${type}»: la cola se conserva; renueva el token con \`slice-ops.sh register --force\`" >&2
        rc=1
        break ;;
      401)
        # [I4] Credenciales no utilizables AHORA, no un rechazo del contrato: la petición se CONSERVA y se
        # deja la marca del token. Seguir con el resto del carril solo repetiría el mismo 401.
        runtime_auth_mark "$status" directo
        echo "⛔ el hub no acepta el token (HTTP $status) al despachar «${type}»: la cola se conserva; renueva el token con \`slice-ops.sh register --force\`" >&2
        rc=1
        break ;;
      404)
        # [bash 3.2] un carácter multibyte pegado a `$var` sin llaves («$type») rompe el
        # escaneo del nombre bajo `set -u` en esta bash — `${type}` lo aísla.
        _runtime_reject_file "$f" "el hub no expone $path (HTTP 404): esta instancia está sin soporte para «${type}» — actualiza el hub y vuelve a proponer" ;;
      409)
        # [Ronda de arreglo 1, Important 4] El cuerpo decide, igual que en `_claim_once`:
        # un 409 por OTRA causa (client_event_id de otro agregado, conflicto de estado…) no es
        # un grafo rancio y tratarlo como tal apartaría la propuesta con un diagnóstico falso.
        # [EP-OR-17] La lectura vive en `runtime_stale_graph_version`, que conoce la forma real
        # del hub (`detail.error`) además de la plana legacy que este sitio leía a mano.
        if server_gv="$(runtime_stale_graph_version "$resp")"; then
          # No es un error de contrato: el grafo del hub cambió. Se anota el desfase (lo
          # muestra `status`) y la petición se CONSERVA — el refresco del heartbeat (#61)
          # traerá la versión nueva y el próximo ciclo la re-estampa. Con 3 rechazos seguidos
          # se deja de insistir: a esas alturas no es una carrera, y un bucle silencioso es
          # peor que un rechazo visible.
          runtime_graph_note_stale "$gv" "$server_gv"
          n409="$(_runtime_direct_field "$f" graph_409)"
          case "$n409" in ''|*[!0-9]*) n409=0 ;; esac
          # [Ronda final] La racha cuenta rechazos contra la MISMA versión local estampada. Las
          # dos cadencias son independientes y nada las acopla: el despacho corre en cada tick
          # que encuentre `outbox/.flush-request` —y `session-stop.sh` lo deja en CADA turno—,
          # mientras el refresco de contexto va a `runtime.context_refresh_s` (45 s por defecto,
          # y `0` lo DESACTIVA, valor soportado). Contando rechazos a secas, tres turnos en
          # menos de 45 s gastaban las tres vidas de la propuesta contra la misma foto del
          # grafo y la apartaban pidiendo un refresco que el cliente nunca se permitió hacer.
          # Si la versión local cambió, hubo refresco de verdad: la racha empieza de cero.
          prev_gv="$(_runtime_direct_field "$f" graph_409_at_version)"
          [ "$prev_gv" = "$gv" ] || n409=0
          n409=$((n409 + 1))
          if [ "$n409" -ge 3 ]; then
            _runtime_reject_file "$f" "el hub rechazó «${type}» tres veces por el MISMO grafo obsoleto (local v${gv:-?}, hub v${server_gv:-?}): refresca el proyecto y vuelve a proponer"
          elif _runtime_mark_graph_409 "$f" "$n409" "$gv"; then
            rc=1
          else
            # [Ronda de arreglo 1, Important 2] El conteo no se pudo persistir: reintentar a
            # ciegas sería un bucle infinito (el contador jamás llegaría a 3). Se aparta.
            _runtime_reject_file "$f" "no se pudo persistir el conteo de rechazos por grafo obsoleto de «${type}»: se aparta para evitar un reintento sin fin"
          fi
        else
          _runtime_reject_file "$f" "el hub rechazó «${type}» (HTTP $status): $resp — no se reintentará"
        fi ;;
      408|429|5*|000)
        # [Ronda de arreglo 1, Minor 6] «3 rechazos CONSECUTIVOS» debe ser literal: un
        # transitorio intercalado (timeout, 5xx…) no es un stale_graph y no debe sumar a esa
        # racha — se reinicia el contador si había uno. Best-effort: si la escritura falla,
        # el `rc=1` de abajo igual reintenta el próximo ciclo (no hay riesgo de bucle, ya que
        # solo la rama `409 stale_graph` puede volver a incrementarlo).
        n409="$(_runtime_direct_field "$f" graph_409)"
        case "$n409" in ''|*[!0-9]*) n409=0 ;; esac
        [ "$n409" -gt 0 ] && _runtime_bump_field "$f" graph_409 0
        rc=1 ;;
      4*)
        _runtime_reject_file "$f" "el hub rechazó «${type}» (HTTP $status): $resp — no se reintentará" ;;
      *)
        rc=1 ;;
    esac
  done
  return $rc
}

RUNTIME_DISPATCH_LOCK_MAX_AGE_MIN=2

runtime_dispatch_lock_path() { echo "$(config_root)/.claude/state/.outbox-dispatch.lock"; }

# runtime_dispatch_outbox — envoltura con MUTEX de `_runtime_dispatch_outbox_once`.
#
# [#62 · ronda final] Hasta esta rama el único despachador era el daemon (proceso único) y no
# hacía falta serializar nada. `slice-ops.sh propose-epic` despacha ahora en PRIMER PLANO, así
# que el proceso de la skill y el daemon pueden recorrer la MISMA cola a la vez. Para el lote
# no sería grave (su seguridad viene de la idempotencia server-side por `client_event_id`),
# pero `runtime_http_status` es un FICHERO compartido: entre el `_runtime_http` de un proceso y
# su lectura del status puede colarse el curl del otro, y un `409` leído como `2xx` borraría la
# petición dándola por entregada sin que el hub la haya visto jamás.
#
# `mkdir` es atómico (mismo patrón que `hb_spawnlock` en heartbeat.sh); un lock huérfano
# —proceso muerto entre el mkdir y el rmdir— se libera por edad. El umbral (2 min) queda muy
# por encima de un ciclo real: el lote es una petición y el carril directo es de volumen
# bajísimo, ambos con `curl -m 10`.
runtime_dispatch_outbox() {
  local lock rc
  lock="$(runtime_dispatch_lock_path)"
  mkdir -p "$(dirname "$lock")"
  if [ -d "$lock" ] && [ -n "$(find "$lock" -maxdepth 0 -mmin "+$RUNTIME_DISPATCH_LOCK_MAX_AGE_MIN" 2>/dev/null)" ]; then
    rmdir "$lock" 2>/dev/null
  fi
  # Otro proceso está despachando ESTA cola: no se toca nada y se reporta que quedó trabajo
  # (rc 1). Devolver 0 sería afirmar que la cola quedó drenada sin haberlo comprobado.
  mkdir "$lock" 2>/dev/null || return 1
  _runtime_dispatch_outbox_once
  rc=$?
  rmdir "$lock" 2>/dev/null
  return $rc
}

# _runtime_dispatch_outbox_once — despacho best-effort de la cola. Respeta un backoff
# persistido (nunca bloquea reintentando en el hilo del hook). FIFO global.
_runtime_dispatch_outbox_once() {
  command -v python3 >/dev/null 2>&1 || return 1

  local dir; dir="$(runtime_outbox_dir)"
  [ -d "$dir" ] || return 0

  local state_file="$dir/.dispatch-state.json"
  local now next_ok=0 attempt=0
  now="$(date +%s)"
  if [ -f "$state_file" ]; then
    next_ok="$(python3 -c "import json;print(json.load(open('$state_file')).get('next_attempt_epoch',0))" 2>/dev/null || echo 0)"
    attempt="$(python3 -c "import json;print(json.load(open('$state_file')).get('attempt',0))" 2>/dev/null || echo 0)"
  fi
  # [I2] `RUNTIME_DISPATCH_FORCE=1` salta la espera del backoff (no el conteo): lo usa el POST síncrono
  # de slice-ops.sh, que va a tocar la red de todos modos y necesita la cola drenada ANTES (orden FIFO).
  [ "${RUNTIME_DISPATCH_FORCE:-0}" != 1 ] && [ "$now" -lt "$next_ok" ] && return 0

  # [#62] Dos carriles, un solo punto de despacho: los ficheros con `channel: "direct"` van a
  # su propio endpoint; el resto arma el lote de POST /events como siempre.
  local all=() files=() direct=() bad=() f line direct_rc=0 part prc
  while IFS= read -r f; do all+=("$f"); done < <(find "$dir" -maxdepth 1 -name '*.json' ! -name '.dispatch-state.json' | sort)
  [ ${#all[@]} -eq 0 ] && return 0
  # [Ronda final] El rc de la partición se COMPRUEBA. Si falla (E2BIG con una cola muy grande,
  # python3 caído a mitad), `direct` y `files` quedaban vacíos, se borraba el backoff agendado
  # y la función devolvía 0 con la cola llena: un fallo reportado como drenaje limpio. Ahora se
  # dice, no se toca el estado de backoff y se reintenta en el próximo ciclo.
  part="$(_runtime_partition_outbox "${all[@]}")"
  prc=$?
  if [ "$prc" -ne 0 ]; then
    echo "⚠ no se pudo clasificar la cola de la outbox (${#all[@]} fichero(s)): no se despacha en este ciclo, se reintentará" >&2
    return 1
  fi
  while IFS= read -r line; do
    case "$line" in
      "direct "*) direct+=("${line#direct }") ;;
      "batch "*)  files+=("${line#batch }") ;;
      "bad "*)    bad+=("${line#bad }") ;;
    esac
  done <<EOF
$part
EOF
  if [ ${#bad[@]} -gt 0 ]; then
    for f in "${bad[@]}"; do
      _runtime_reject_file "$f" "fichero de la outbox ilegible (no es un objeto JSON): no se puede saber por qué carril iba ni qué contiene — se aparta en vez de dejarlo atascado en la cola para siempre"
    done
  fi
  if [ ${#direct[@]} -gt 0 ]; then
    _runtime_dispatch_direct "${direct[@]}" || direct_rc=1
  fi
  if [ ${#files[@]} -eq 0 ]; then
    [ "$direct_rc" -eq 0 ] && rm -f "$state_file"
    return "$direct_rc"
  fi

  # [#37] El hub (`EventBatchIn`) exige el sobre {"events": [...]} — el array pelado era
  # 422 en cada intento y la cola no drenaba jamás. Cada elemento va con `event_type`
  # (`EventIn`); la clave interna de la outbox sigue siendo `type` y se traduce AQUÍ, al
  # armar el cuerpo (el formato en disco no cambia).
  # [#44] En el mismo punto de salida se ajustan los payloads que `extra="forbid"` rechazaría
  # (`slice_submitted`/`slice_archived` sin campos, items del wiring {item_id, kind, ref}).
  # [U16] Sin la capa de compat de nombres 0.10.x del original: el arnés Bonita nunca tuvo
  # consumidores 0.10.x. Los tipos SIN equivalente en el catálogo (`tool_use_recorded`,
  # `branch_drift`, `front_integration_reported`) se apartan localmente a rejected/ sin
  # gastar red: mandarlos era rechazo garantizado.
  local batch
  batch="$(python3 - "$dir/rejected" "${files[@]}" <<'PY'
import json,sys,os
rejected_dir=sys.argv[1]
SIN_EQUIVALENTE={"tool_use_recorded","branch_drift","front_integration_reported"}
def traducir(t,p,slice_id):
    p=dict(p)
    if t in ("slice_submitted","slice_archived"):
        p={}  # el catálogo no admite ningún campo (extra="forbid")
    elif t=="wiring_checklist_seeded":
        items=[]
        for it in p.get("items") or []:
            if isinstance(it,dict) and it.get("item_id"):
                items.append({"item_id":it["item_id"],"kind":it.get("kind") or "","ref":it.get("ref") or ""})
        p={"items":items}
    return t,p,slice_id
items=[]
for path in sys.argv[2:]:
    try:
        d=json.load(open(path))
    except Exception:
        continue
    t=d.get("event_type") or d.get("type") or ""
    if t in SIN_EQUIVALENTE:
        # [#52] La razón viaja DENTRO del fichero apartado (rejected_reason): es lo que
        # `slice-ops.sh status` y `trycore-bonita status/doctor` muestran después — sin
        # esto el rechazo era invisible (stderr de un daemon que nadie lee).
        try:
            os.makedirs(rejected_dir,exist_ok=True)
            d["rejected_reason"]="%r no existe en el catálogo v2 del hub (issue #44): no se envió" % t
            dest=os.path.join(rejected_dir,os.path.basename(path))
            json.dump(d,open(dest,"w"),indent=2,ensure_ascii=False)
            os.unlink(path)
            print("⚠ %r no existe en el catálogo v2 del hub: apartado a rejected/, no se enviará (issue #44)"
                  % t, file=sys.stderr)
        except OSError:
            pass
        continue
    t,p,slice_id=traducir(t,d.get("payload") or {},d.get("slice_id"))
    ev={"client_event_id": d.get("client_event_id") or "",
        "event_type": t,
        "payload": p}
    if slice_id:
        ev["slice_id"]=slice_id
    items.append(ev)
print(json.dumps({"events": items}, ensure_ascii=False))
PY
)"

  # Si todo lo pendiente eran tipos sin equivalente (ya apartados), no hay nada que enviar.
  local n_items
  n_items="$(printf '%s' "$batch" | python3 -c 'import json,sys;print(len(json.load(sys.stdin).get("events") or []))' 2>/dev/null || echo 0)"
  # [#62] El lote no tenía nada que enviar, pero el carril directo puede seguir con algo
  # pendiente por causa transitoria: el rc de la función tiene que reflejarlo (no solo el
  # rc del lote), porque quien lo consume (p. ej. slice-ops.sh) decide en base a ÉL si
  # queda trabajo por drenar.
  if [ "$n_items" = "0" ]; then
    rm -f "$state_file"
    return "$direct_rc"
  fi

  local resp status
  resp="$(runtime_post "/events" "$batch")"
  status="$(runtime_http_status)"

  if [ "$status" = "200" ]; then
    # [#37] Ack REAL del hub: {accepted:[cid], duplicates:[cid], rejected:[{client_event_id,
    # reason}]}. Se conserva la lectura de la forma antigua {"results":[…]} (stubs/beta).
    # Aceptado o duplicado => entregado, se borra. Rechazado POR ELEMENTO (fuera de catálogo
    # o payload inválido) => reenviarlo es inútil: se aparta a rejected/ con su razón en
    # stderr. Sin mención => se conserva para el próximo despacho (nunca se asume aceptado
    # en silencio: perder un checkpoint/verdict/submit sin confirmación real viola la cota).
    python3 - "$resp" "$dir/rejected" "$(runtime_phase_acks_path)" "${files[@]}" <<'PY'
import json,sys,os,tempfile,time
resp=json.loads(sys.argv[1])
rejected_dir=sys.argv[2]
acks_path=sys.argv[3]
paths=sys.argv[4:]
acks={}
status={}
reasons={}
if isinstance(resp,dict) and "results" in resp:
    for r in resp.get("results") or []:
        status[r.get("client_event_id")]=r.get("status")
elif isinstance(resp,dict):
    for cid in resp.get("accepted") or []:
        status[cid]="accepted"
    for cid in resp.get("duplicates") or []:
        status[cid]="accepted"
    for r in resp.get("rejected") or []:
        cid=r.get("client_event_id")
        status[cid]="rejected"
        reasons[cid]=r.get("reason") or "sin razón"
for p in paths:
    try:
        d=json.load(open(p))
        cid=d.get("client_event_id")
    except Exception:
        continue
    st=status.get(cid)
    if st=="accepted":
        # FIFO: la última phase_advanced aceptada de un slice es la fase que el hub conoce ahora.
        if d.get("type")=="phase_advanced" and d.get("slice_id"):
            to=(d.get("payload") or {}).get("to")
            if isinstance(to,str) and to:
                acks[d["slice_id"]]={"phase":to,"acked_at":time.time()}
        try: os.unlink(p)
        except OSError: pass
    elif st=="rejected":
        print("⚠ el hub rechazó el evento %s: %s — apartado a rejected/, no se reenviará"
              % (cid, reasons.get(cid,"sin razón")), file=sys.stderr)
        # [#52] La razón del hub se persiste en el fichero apartado (rejected_reason):
        # la muestran `slice-ops.sh status` y `trycore-bonita status/doctor`.
        try:
            os.makedirs(rejected_dir,exist_ok=True)
            d["rejected_reason"]=reasons.get(cid,"sin razón")
            dest=os.path.join(rejected_dir, os.path.basename(p))
            json.dump(d,open(dest,"w"),indent=2,ensure_ascii=False)
            os.unlink(p)
        except OSError:
            pass
if acks:
    try:
        try:
            prev=json.load(open(acks_path))
            if not isinstance(prev,dict):
                prev={}
        except Exception:
            prev={}
        prev.update(acks)
        dirn=os.path.dirname(acks_path) or "."
        os.makedirs(dirn,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".phase-acks.",suffix=".tmp")
        with os.fdopen(fd,"w") as out:
            json.dump(prev,out,indent=2)
        os.replace(tmp,acks_path)
    except Exception:
        pass
PY
    # [#62] Igual que arriba: el lote se resolvió (200), pero el rc global tiene que
    # reflejar también el carril directo si algo suyo quedó pendiente por causa
    # transitoria en este mismo ciclo.
    rm -f "$state_file"
    runtime_auth_clear
    return "$direct_rc"
  fi

  # [#37] Un 4xx del LOTE (salvo 401/403, 408 y 429) es un rechazo del contrato, no red caída:
  # reintentarlo para siempre solo repite el mismo error y el usuario cree que reportó.
  # Se loggea el cuerpo, el lote entero se aparta a rejected/ y NO se agenda backoff.
  # 408 (timeout) y 429 (rate-limit) siguen siendo transitorios, igual que 5xx y 000.
  case "$status" in
    408|429) : ;;
    401|403)
      # [I4] El token no sirve ahora (expirado o rotado): NO es un rechazo del contrato. El lote se conserva
      # entero, el backoff no crece (reintentar no arregla un token; `register --force` sí) y queda la marca.
      runtime_auth_mark "$status" lote
      echo "⛔ el hub no acepta el token (HTTP $status): ${#files[@]} evento(s) se CONSERVAN en la cola." >&2
      echo "  Pide un token nuevo al ADMIN y corre \`slice-ops.sh register --force\`: la cola drena en el siguiente ciclo." >&2
      return 1
      ;;
    4*)
      local rejected_dir
      rejected_dir="$dir/rejected"
      mkdir -p "$rejected_dir"
      echo "⛔ el hub rechazó el lote de eventos (HTTP $status): $resp" >&2
      echo "  ${#files[@]} evento(s) movidos a $rejected_dir/ — NO se reintentarán." >&2
      echo "  Revisa el contrato del cliente con el hub (\`trycore-bonita doctor\`) o actualiza" >&2
      echo "  el arnés; el trabajo local sigue (fail-open)." >&2
      # [#52] También aquí la razón (HTTP status) queda persistida en cada fichero apartado.
      python3 - "$rejected_dir" "$status" "${files[@]}" <<'PY' 2>/dev/null
import json,sys,os
rd,st=sys.argv[1],sys.argv[2]
for p in sys.argv[3:]:
    try:
        d=json.load(open(p))
    except Exception:
        d=None
    try:
        dest=os.path.join(rd,os.path.basename(p))
        if isinstance(d,dict):
            d["rejected_reason"]="el hub rechazó el lote entero (HTTP %s)" % st
            json.dump(d,open(dest,"w"),indent=2,ensure_ascii=False)
            os.unlink(p)
        else:
            os.replace(p,dest)
    except OSError:
        pass
PY
      # Fallback si python3 desapareció a mitad de camino: mover sin anotar (mejor apartado
      # sin razón que reintento eterno).
      for f in "${files[@]}"; do
        [ -f "$f" ] && mv "$f" "$rejected_dir/" 2>/dev/null
      done
      rm -f "$state_file"
      return 1
      ;;
  esac

  # [I2] El drenaje forzado del primer plano es un intento oportunista: el backoff es del daemon, y
  # agendarlo aquí retrasaría su próximo intento por un fallo que no fue suyo.
  [ "${RUNTIME_DISPATCH_FORCE:-0}" = 1 ] && return 1
  local schedule idx max_idx delay
  read -ra schedule <<< "$RUNTIME_OUTBOX_BACKOFF_SCHEDULE"
  idx=$attempt
  max_idx=$(( ${#schedule[@]} - 1 ))
  [ "$idx" -gt "$max_idx" ] && idx=$max_idx
  delay="${schedule[$idx]}"
  python3 -c "import json; json.dump({'next_attempt_epoch': $now + $delay, 'attempt': $((attempt + 1))}, open('$state_file','w'))"
  return 1
}
