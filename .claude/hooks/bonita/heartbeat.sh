#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/heartbeat.sh
# heartbeat.sh — daemon singleton por repo [EP-OR-08-B, spec §4.3].
#   uso: heartbeat.sh [--ensure <ppid>] | --daemon | --stop     (default: --ensure $PPID)
#
# Por qué un daemon y no un hook: no existe evento Timer, los hooks son efímeros y un
# PostToolUse throttled NO late durante una tool call larga (suites de >5 min contra un
# TTL de 300 s). Ciclo de vida explícito:
#   - Singleton por repo: pidfile + fichero de sesiones interesadas en .claude/state/.
#   - Cada SessionStart registra su ppid y RELANZA el daemon si el pidfile está muerto;
#     cada PostToolUse hace la misma comprobación barata (stat + kill -0, SIN red).
#   - Muere cuando no queda NINGÚN ppid registrado vivo (no cuando muere el primero):
#     dos sesiones sobre el mismo repo comparten daemon.
#   - Deberes por tick: consumir el sentinela de flush y despachar la cola; cada
#     lease_ttl_s/3, renovar el lease. Sin lease NO se apaga (los eventos de ámbito
#     proyecto, pre-claim, necesitan despachador).
#   - Nunca se cuelga de Stop (dispara cada turno) ni de SessionEnd (no existe).
# Cambios sobre el original: modo servidor siempre (sin las salidas de los modos sin hub) y,
# si el último claim fue un MICRO-WORK vivo (.claude/state/claim.json), se renueva SU lease
# (`PUT /micro-works/{id}/lease/renew`, task_router.py del hub) en vez del de la unidad: el
# original solo conocía `/leases/renew` y el lease de un micro-work vencía a los 300 s con el
# agente trabajándolo.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"
source "$HERE/lib/agent-context.sh"

HB_TICK_S="${TRYCORE_HEARTBEAT_TICK_S:-5}"
case "$HB_TICK_S" in ''|*[!0-9]*) HB_TICK_S=5 ;; esac

# Cadencia del refresco de contexto [#61]. NO es el tick: renovar un lease es barato, pero
# `GET /agent/context` es una proyección entera del proyecto — a 5 s castigaría al hub sin
# ganar nada. 45 s es del orden de la latencia con la que un humano aprueba una épica.
# `0` lo desactiva (vuelta al comportamiento previo a #61).
HB_CONTEXT_S="${TRYCORE_CONTEXT_REFRESH_S:-}"
[ -n "$HB_CONTEXT_S" ] || HB_CONTEXT_S="$(config_get runtime.context_refresh_s 45)"
case "$HB_CONTEXT_S" in ''|*[!0-9]*) HB_CONTEXT_S=45 ;; esac

hb_pidfile()   { echo "$(config_root)/.claude/state/heartbeat.pid"; }
hb_sessions()  { echo "$(config_root)/.claude/state/heartbeat-sessions.json"; }
hb_statusfile() { echo "$(config_root)/.claude/state/heartbeat-status.json"; }
hb_flushfile() { echo "$(runtime_outbox_dir)/.flush-request"; }
hb_spawnlock() { echo "$(config_root)/.claude/state/.heartbeat.spawn.lock"; }

# hb_alive — rc 0 si hay un daemon vivo según el pidfile.
hb_alive() {
  local f pid
  f="$(hb_pidfile)"
  [ -f "$f" ] || return 1
  pid="$(cat "$f" 2>/dev/null)"
  case "$pid" in ''|*[!0-9]*) return 1 ;; esac
  kill -0 "$pid" 2>/dev/null
}

# hb_register_session <ppid> — upsert idempotente del ppid en el registro de sesiones.
hb_register_session() {
  local ppid="${1:-}" f
  case "$ppid" in ''|*[!0-9]*) return 0 ;; esac
  f="$(hb_sessions)"
  mkdir -p "$(dirname "$f")"
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$f" "$ppid" <<'PY' 2>/dev/null
import json,sys,os,tempfile
path,ppid=sys.argv[1],int(sys.argv[2])
try:
    d=json.load(open(path))
except Exception:
    d={}
if not isinstance(d,dict):
    d={}
ppids=[p for p in (d.get("ppids") or []) if isinstance(p,int)]
if ppid not in ppids:
    ppids.append(ppid)
d["ppids"]=ppids
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".heartbeat-sessions.",suffix=".tmp")
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

# hb_prune_sessions — deja en el registro solo los ppids vivos e imprime cuántos quedan.
# La lista se materializa en un fichero temporal y se itera con `while read` (bash 3.2:
# nada de mapfile) para poder aplicar `kill -0` a cada uno.
hb_prune_sessions() {
  local f tmp pid n
  f="$(hb_sessions)"
  [ -f "$f" ] || { echo 0; return 0; }
  command -v python3 >/dev/null 2>&1 || { echo 0; return 0; }
  tmp="$(mktemp)" || { echo 0; return 0; }
  python3 - "$f" > "$tmp" <<'PY' 2>/dev/null
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    d={}
for p in (d.get("ppids") or []):
    print(p)
PY
  local live=()
  while IFS= read -r pid; do
    case "$pid" in ''|*[!0-9]*) continue ;; esac
    kill -0 "$pid" 2>/dev/null && live+=("$pid")
  done < "$tmp"
  rm -f "$tmp"
  n=${#live[@]}
  if [ "$n" -gt 0 ]; then
    python3 - "$f" "${live[@]}" <<'PY' 2>/dev/null
import json,sys,os,tempfile
path=sys.argv[1]
ppids=[int(x) for x in sys.argv[2:]]
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".heartbeat-sessions.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump({"ppids":ppids},out,indent=2)
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
PY
  fi
  echo "$n"
}

# hb_write_status <fragmento-json> — UPSERT del fragmento sobre el estado observable del
# daemon (lo lee statusline-bridge.sh y `slice-ops.sh status`). Es merge y no reemplazo
# desde #61: el fichero lo escriben DOS deberes distintos del tick — la renovación del lease
# y el refresco de contexto — y con reemplazo el último en escribir borraba el diagnóstico
# del otro (un refresco correcto tapaba un `lease_lost: true` recién detectado).
hb_write_status() {
  local body f
  body="$1"
  f="$(hb_statusfile)"
  mkdir -p "$(dirname "$f")"
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$f" "$body" <<'PY' 2>/dev/null
import json,sys,os,tempfile
path,body=sys.argv[1],sys.argv[2]
try:
    d=json.load(open(path))
except Exception:
    d={}
if not isinstance(d,dict):
    d={}
try:
    frag=json.loads(body)
except Exception:
    frag={}
if isinstance(frag,dict):
    d.update(frag)
dirn=os.path.dirname(path) or "."
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".heartbeat-status.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump(d,out,indent=2); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,path)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
PY
  return 0
}

# hb_renew — renueva el lease del trabajo activo: el micro-work reclamado si lo hay, si no la
# unidad. El hub responde SIEMPRE 409 de cuerpo único cuando el lease ya no es nuestro
# (anti-oráculo HU-OR-41a): esa es la señal de «lease perdido». No se apaga el daemon; se
# marca el estado y se sigue despachando.
hb_renew() {
  local slice_id agent_key status mw
  mw="$(claim_micro_work_id)"
  if [ -n "$mw" ]; then
    hb_renew_micro_work "$mw"
    return $?
  fi
  slice_id="$(projection_get active_slice.slice_id "")"
  [ -n "$slice_id" ] || return 0
  agent_key="$(runtime_field agent_key)"
  runtime_put "/leases/renew" "{\"agent_key\":\"$agent_key\",\"slice_id\":\"$slice_id\"}" >/dev/null
  status="$(runtime_http_status)"
  case "$status" in
    200)
      hb_write_status "{\"lease_lost\": false, \"slice_id\": \"$slice_id\", \"last_renew_status\": 200}"
      return 0
      ;;
    409)
      hb_write_status "{\"lease_lost\": true, \"slice_id\": \"$slice_id\", \"last_renew_status\": 409}"
      return 1
      ;;
    *)
      # Red caída: no se toca el estado anterior (no es lo mismo «sin red» que «lease perdido»).
      return 1
      ;;
  esac
}

# hb_renew_micro_work <id> — `PUT /micro-works/{id}/lease/renew` (sin cuerpo: el agente sale del
# bearer). 409 = expirado, ajeno o inexistente; 404 = el micro-work no existe en el proyecto del
# token. Los dos son «lease perdido»: un renew jamás lo resucita, hay que volver a reclamar.
hb_renew_micro_work() {
  local mw="$1" status mwj mwp
  mwj="$(printf '%s' "$mw" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))' 2>/dev/null)"
  mwp="$(printf '%s' "$mw" | python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read(),safe=""))' 2>/dev/null)"
  [ -n "$mwj" ] && [ -n "$mwp" ] || return 1
  runtime_put "/micro-works/$mwp/lease/renew" "" >/dev/null
  status="$(runtime_http_status)"
  case "$status" in
    200)
      hb_write_status "{\"lease_lost\": false, \"micro_work_id\": $mwj, \"last_renew_status\": 200}"
      return 0 ;;
    404|409)
      hb_write_status "{\"lease_lost\": true, \"micro_work_id\": $mwj, \"last_renew_status\": $status}"
      return 1 ;;
    *)
      return 1 ;;
  esac
}

# hb_refresh_context — refresca la caché de proyección desde GET /agent/context. Es el ÚNICO
# camino por el que una terminal ABIERTA se entera de algo nuevo: `session-start.sh` hidrata
# una vez al arrancar y `slice-ops.sh` solo en claim/status — y el claim ocurre una vez por
# slice, así que sin esto una sesión larga trabaja horas contra una foto vieja (#61).
# `agent_context_fetch_and_cache` NUNCA pisa la caché anterior si falla (fail-open);
# aquí solo se anota el diagnóstico, para que `status` distinga «vieja» de «no se pudo».
#
# `last_context_status` es SIEMPRE una cadena. El diagnóstico no es solo un código HTTP
# (`"write_error"` no lo es) y `"000"` —el valor de «sin red» de `runtime_http_status`— no es
# un número JSON válido: emitirlo sin comillas rompía el parseo del fragmento entero y
# `hb_write_status` acababa no escribiendo NADA, ni siquiera el `context_stale: true`.
hb_refresh_context() {
  local status rc
  agent_context_fetch_and_cache >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    hb_write_status "{\"context_stale\": false, \"last_context_status\": \"200\", \"last_context_refresh_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
    return 0
  fi
  # [#61 · ronda final] Un 200 que no se pudo normalizar o escribir NO es un fallo de red:
  # anotarlo como «último intento: 200» mandaba a mirar el sitio equivocado.
  if [ "$rc" -eq 2 ]; then
    status="write_error"
  else
    status="$(runtime_http_status)"
  fi
  hb_write_status "{\"context_stale\": true, \"last_context_status\": \"$status\"}"
  return 1
}

hb_daemon() {
  local pidf interval ttl last last_ctx now n
  pidf="$(hb_pidfile)"
  mkdir -p "$(dirname "$pidf")"
  printf '%s' "$$" > "$pidf"
  # [I7] El trap mata también el `sleep` del tick (corre en segundo plano, ver el bucle) y solo borra
  # el pidfile si sigue siendo el SUYO: tras un --stop, un --ensure puede haber lanzado ya otro daemon.
  HB_SLEEP_PID=""
  trap '[ -n "$HB_SLEEP_PID" ] && kill "$HB_SLEEP_PID" 2>/dev/null; [ "$(cat "$(hb_pidfile)" 2>/dev/null)" = "$$" ] && rm -f "$(hb_pidfile)"; exit 0' TERM INT EXIT
  interval="${TRYCORE_HEARTBEAT_INTERVAL_S:-}"
  case "$interval" in
    ''|*[!0-9]*)
      ttl="$(runtime_field lease_ttl_s)"
      case "$ttl" in ''|*[!0-9]*) ttl=300 ;; esac
      interval=$(( ttl / 3 ))
      [ "$interval" -lt 10 ] && interval=10
      ;;
  esac
  last=0
  # `session-start.sh` acaba de hidratar la caché: arrancar el contador AHORA evita un
  # refresco redundante en el primer tick del daemon.
  last_ctx="$(date +%s)"
  while :; do
    # [I7] bash corre el trap de TERM solo cuando termina el comando en PRIMER plano: con `sleep` en
    # primer plano el daemon sobrevivía al --stop hasta un tick entero. `wait` sí lo interrumpe una
    # señal atrapada, así que el trap corre al instante (y mata este `sleep`).
    sleep "$HB_TICK_S" &
    HB_SLEEP_PID=$!
    wait "$HB_SLEEP_PID"
    HB_SLEEP_PID=""
    n="$(hb_prune_sessions)"
    case "$n" in ''|*[!0-9]*) n=0 ;; esac
    [ "$n" -eq 0 ] && break     # murió la última sesión interesada: el daemon se va con ella
    if [ -f "$(hb_flushfile)" ]; then
      rm -f "$(hb_flushfile)"
      runtime_dispatch_outbox >/dev/null 2>&1
    fi
    now="$(date +%s)"
    if [ "$HB_CONTEXT_S" -gt 0 ] && [ $(( now - last_ctx )) -ge "$HB_CONTEXT_S" ]; then
      hb_refresh_context
      last_ctx="$now"
    fi
    if [ $(( now - last )) -ge "$interval" ]; then
      hb_renew
      runtime_dispatch_outbox >/dev/null 2>&1
      last="$now"
    fi
  done
  rm -f "$pidf"
  exit 0
}

# hb_spawn — lanza el daemon bajo un mutex de directorio (`mkdir` es atómico): dos
# SessionStart simultáneos sobre el mismo repo no crean dos daemons. Un lock huérfano
# (proceso muerto entre el mkdir y el rmdir) se libera por edad.
#
# El mutex cubre «daemon confirmado arriba», no solo «proceso bifurcado»: tras el nohup se
# hace poll acotado (~3s) de hb_alive antes de soltar el lock. Sin esto, la ventana entre
# el backgrounding y que el hijo escriba heartbeat.pid deja el lock libre con hb_alive aún
# en falso; un --ensure casi simultáneo puede colarse ahí y lanzar un SEGUNDO daemon (se
# autosana en el siguiente tick al ver 0 sesiones propias, pero produce renew/dispatch
# duplicados transitorios mientras tanto).
hb_spawn() {
  local lock waited
  lock="$(hb_spawnlock)"
  mkdir -p "$(dirname "$lock")"
  if [ -d "$lock" ] && [ -n "$(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
    rmdir "$lock" 2>/dev/null
  fi
  mkdir "$lock" 2>/dev/null || return 0     # otro proceso está lanzando: nada que hacer
  if ! hb_alive; then
    nohup bash "$HERE/heartbeat.sh" --daemon >/dev/null 2>&1 &
    waited=0
    while [ "$waited" -lt 30 ]; do
      hb_alive && break
      sleep 0.1
      waited=$((waited + 1))
    done
  fi
  rmdir "$lock" 2>/dev/null
  return 0
}

hb_ensure() {
  # [#74] Un worktree que heredó la identidad del clon principal no arranca ni comparte daemon:
  # renovaría el lease y despacharía la cola del OTRO agente. Su alta es `slice-ops.sh register`.
  config_is_inherited_root && return 0
  hb_register_session "${1:-}"
  hb_alive || hb_spawn
  return 0
}

# hb_stop — apaga el daemon y ESPERA (hasta ~2 s) a que muera antes de borrar el pidfile. [I7] Borrarlo
# con el daemon aún vivo (en mitad de un curl -m 10 o de un python3 del tick) abría una ventana en la que
# un --ensure lanzaba un SEGUNDO daemon: renovación y despacho dobles.
hb_stop() {
  local pid i=0
  pid="$(cat "$(hb_pidfile)" 2>/dev/null)"
  case "$pid" in
    ''|*[!0-9]*) ;;
    *)
      kill "$pid" 2>/dev/null
      while [ "$i" -lt 20 ] && kill -0 "$pid" 2>/dev/null; do
        sleep 0.1
        i=$((i + 1))
      done ;;
  esac
  rm -f "$(hb_pidfile)" "$(hb_sessions)"
  return 0
}

case "${1:-}" in
  --daemon) hb_daemon ;;
  --stop)   hb_stop ;;
  --ensure) hb_ensure "${2:-$PPID}" ;;
  *)        hb_ensure "$PPID" ;;
esac
exit 0
