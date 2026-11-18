#!/usr/bin/env bash
# context-monitor.sh — PostToolUse|PreCompact|Stop. Lee el puente, aplica umbrales,
# inyecta additionalContext y en `critical` registra el handoff. Fail-open.
# [EP-OR-08-B] Comportamiento por modo:
#   - legacy: v0.8.5 exacto (handoff escrito en build-state.json).
#   - dual:   igual + el mismo handoff se emite como evento handoff_recorded (espejo).
#   - runtime: NO se escribe el fichero; el handoff es SOLO el evento, y el guard
#     once-per-sesión vive en una marca local (.claude/state/.handoff-<session_id>).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"
payload="$(cat)"; command -v python3 >/dev/null 2>&1 || exit 0

MODE="$(runtime_mode)"
[ "$MODE" != "runtime" ] && source "$HERE/lib/state-io.sh"

read -r SID EVT <<<"$(printf '%s' "$payload" | python3 -c '
import json,sys
try: p=json.load(sys.stdin)
except Exception: p={}
print(p.get("session_id","default"), p.get("hook_event_name","PostToolUse"))
' 2>/dev/null)"
SID="${SID:-default}"; EVT="${EVT:-PostToolUse}"

sanitized_sid="$(printf '%s' "$SID" | tr -c 'A-Za-z0-9_-' '_')"
BRIDGE="${TMPDIR:-/tmp}/claude-ctx-$sanitized_sid.json"
[ -f "$BRIDGE" ] || BRIDGE="$(command ls "${TMPDIR:-/tmp}"/claude-ctx-*.json 2>/dev/null | head -1)"
[ -n "${BRIDGE:-}" ] && [ -f "$BRIDGE" ] || exit 0

WARN="$(config_get context.warning_pct 35)"; CRIT="$(config_get context.critical_pct 25)"
STALE="$(config_get context.stale_seconds 60)"; AUTO="$(config_get context.auto_checkpoint false)"

if [ "$MODE" = "runtime" ]; then
  STATE=""
  MARK="$(config_root)/.claude/state/.handoff-$sanitized_sid"
  HINT="$(projection_get active_slice.wiring_failing '[]' | python3 -c 'import json,sys
try: w=json.load(sys.stdin)
except Exception: w=[]
ids=[str(i.get("item_id")) for i in w[:6] if i.get("item_id")]
print("cablear: "+", ".join(ids) if ids else "")' 2>/dev/null)"
  [ -n "$HINT" ] || HINT="$(projection_get active_slice.resume_hint "")"
else
  STATE="$(state_path)"
  MARK=""
  HINT=""
fi
mkdir -p "$(config_root)/.claude/state"
EVENT_OUT="$(mktemp)" || exit 0

# [#79] Rama real del árbol de trabajo. Si es de mantenimiento (fix/*|chore/*) y difiere de la
# del slice, el handoff que se graba es el del bugfix, no el del slice: el resume_hint lo dice
# para que una sesión fresca no los confunda. `symbolic-ref` también resuelve el repo recién
# inicializado (HEAD sin commits); `rev-parse` queda de reserva para HEAD desacoplado.
GIT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
BRANCH="$(git -C "$GIT_ROOT" symbolic-ref --short HEAD 2>/dev/null || git -C "$GIT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"

python3 - "$BRIDGE" "$WARN" "$CRIT" "$STALE" "$EVT" "$STATE" "$AUTO" "$MODE" "$EVENT_OUT" "$MARK" "$HINT" "$BRANCH" <<'PY' 2>/dev/null || true
import json,sys,os,time,tempfile
bridge,warn,crit,stale,evt,state,auto,mode,event_out,mark,hint,rama=sys.argv[1:13]
warn,crit,stale=int(warn),int(crit),int(stale)
try: b=json.load(open(bridge))
except Exception: sys.exit(0)
if time.time()-b.get("ts",0) > stale: sys.exit(0)   # métrica vieja
rem=b.get("remaining_pct",100)
sev = "critical" if rem<=crit else ("warning" if rem<=warn else None)
if not sev: sys.exit(0)

iso=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
recorded=False      # handoff persistido en el fichero (legacy|dual)
emit=False          # handoff que hay que encolar como evento (dual|runtime)
resume=hint or "revisar progreso y continuar"

if sev=="critical" and mode!="runtime" and state and os.path.exists(state):
    try:
        d=json.load(open(state)); s=d.get("active_slice")
        if s:
            sc=s.setdefault("session_continuity",{})
            if not sc.get("critical_recorded"):
                sc["stopped_at"]=f"context exhaustion at {rem}% ({iso})"
                failing=[w["id"] for w in (s.get("wiring_checklist") or []) if w.get("status")=="failing"]
                resume=("cablear: "+", ".join(failing[:6])) if failing else "revisar progreso y continuar"
                # [#79] Carril de mantenimiento: el slice queda en pausa, el handoff es del bugfix.
                if rama.startswith(("fix/","chore/")) and rama != (s.get("branch") or ""):
                    resume=f"[rama {rama}: carril de mantenimiento; slice en pausa] "+resume
                sc["resume_hint"]=resume
                sc["critical_recorded"]=True
                sc["auto_continue"]=(auto=="true")
                s.setdefault("progress_log",[]).append(
                    {"at":iso,"by":"context-monitor","note":f"handoff auto a {rem}% de contexto restante"})
                dirn=os.path.dirname(state) or "."
                fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".build-state.",suffix=".tmp")
                try:
                    with os.fdopen(fd,"w") as o: json.dump(d,o,indent=2,ensure_ascii=False); o.flush(); os.fsync(o.fileno())
                    os.replace(tmp,state); recorded=True
                except Exception:
                    try: os.unlink(tmp)
                    except OSError: pass
                    raise
    except Exception: pass
    if recorded and mode=="dual":
        emit=True
elif sev=="critical" and mode=="runtime":
    # El guard once-per-sesión no puede vivir en el fichero (no lo hay): marca local.
    if mark and not os.path.exists(mark):
        try:
            with open(mark,"w") as m: m.write(iso)
            emit=True
        except Exception:
            emit=False

if emit:
    try:
        with open(event_out,"w") as out:
            json.dump({"note":f"handoff auto a {rem}% de contexto restante",
                       "resume_hint":resume,
                       "stopped_at":f"context exhaustion at {rem}% ({iso})"},out,ensure_ascii=False)
    except Exception:
        pass

transition = recorded or emit
if sev=="warning":
    msg=(f"⚠️ Contexto al {rem}% restante. Acércate a un punto natural de corte "
         "(fin de fase/gate). No inicies trabajo complejo nuevo.")
else:
    if mode=="runtime":
        tail=(" Handoff registrado en el runtime (handoff_recorded)." if emit else "")
        origen="El estado vive en el runtime;"
    else:
        tail=(" Handoff escrito en build-state.json (session_continuity)." if recorded else "")
        origen="El estado ya vive en build-state.json;"
    cont=(" auto_checkpoint=ON: continúa en sesión fresca." if auto=="true" else
          " Avisa al usuario para reiniciar en un punto natural.")
    msg=(f"🛑 Contexto CRÍTICO al {rem}% restante.{tail} {origen}"
         f" no reescribas handoff manual.{cont}")
# En 'Stop', inyectar additionalContext RE-LANZA el turno (re-prompt): repetirlo en cada
# intento de cierre entra en bucle hasta el tope CLAUDE_CODE_STOP_HOOK_BLOCK_CAP (=9→override).
# Por eso en 'Stop' re-lanzamos como MUCHO una vez por sesión y solo en la TRANSICIÓN a crítico
# (el instante en que se graba/emite el handoff). 'warning' nunca inyecta en 'Stop'.
if evt=="Stop" and not (sev=="critical" and transition): sys.exit(0)
print(json.dumps({"hookSpecificOutput":{"hookEventName":evt,"additionalContext":msg}}))
PY

# El evento se encola FUERA del bloque python: encolar es competencia del cliente bash
# (runtime_enqueue_event), y así el stdout del hook queda limpio pase lo que pase.
# handoff_recorded es de ámbito slice: los eventos de ámbito slice llevan slice_id, sin
# slice_id conocido NO se encolan (el servidor los rechazaría elemento a elemento) — misma
# guardia que event-emitter.sh. En `dual` es el caso NORMAL, no el borde: dual no reclama
# vía runtime, así que /agent/context no trae active_slice y sin esta guardia el evento se
# encolaba sin slice_id, quedando como poison pill en RUNTIME_OUTBOX_PROTECTED si el
# servidor rechazaba el lote entero.
SLICE_ID_HANDOFF="$(projection_get active_slice.slice_id "")"
if [ -s "$EVENT_OUT" ] && [ "$MODE" != "legacy" ] && [ -n "$SLICE_ID_HANDOFF" ]; then
  runtime_enqueue_event "handoff_recorded" "$(cat "$EVENT_OUT")" "$SLICE_ID_HANDOFF" >/dev/null 2>&1
fi
rm -f "$EVENT_OUT"
exit 0
