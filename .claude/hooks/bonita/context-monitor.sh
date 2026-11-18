#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/context-monitor.sh
# context-monitor.sh — PostToolUse|PreCompact|Stop. Lee el puente de la statusline, aplica los
# umbrales de contexto, inyecta additionalContext y, al pasar a crítico, registra el handoff en
# el hub como evento `handoff_recorded`. Fail-open.
# Modo servidor siempre (U16): NO se escribe ningún fichero de estado; el handoff es SOLO el
# evento, y el guard once-per-sesión vive en una marca local (.claude/state/.handoff-<sid>).
# Cambios sobre el original: sin los caminos con fichero de estado local; el aviso de rama de
# mantenimiento (fix/*|chore/*) se aplica también aquí.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"
payload="$(cat)"; command -v python3 >/dev/null 2>&1 || exit 0

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

MARK="$(config_root)/.claude/state/.handoff-$sanitized_sid"
HINT="$(projection_get active_slice.wiring_failing '[]' | python3 -c 'import json,sys
try: w=json.load(sys.stdin)
except Exception: w=[]
ids=[str(i.get("item_id")) for i in w[:6] if isinstance(i,dict) and i.get("item_id")]
print("cablear: "+", ".join(ids) if ids else "")' 2>/dev/null)"
[ -n "$HINT" ] || HINT="$(projection_get active_slice.resume_hint "")"
mkdir -p "$(config_root)/.claude/state"
EVENT_OUT="$(mktemp)" || exit 0

# [#79] Rama real del árbol de trabajo. Si es de mantenimiento (fix/*|chore/*) y difiere de la
# de la unidad, el handoff que se graba es el del bugfix: el resume_hint lo dice para que una
# sesión fresca no los confunda. `symbolic-ref` también resuelve el repo recién inicializado.
GIT_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
BRANCH="$(git -C "$GIT_ROOT" symbolic-ref --short HEAD 2>/dev/null || git -C "$GIT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
SLICE_BRANCH="$(projection_get active_slice.branch "")"
# handoff_recorded es de ámbito slice: sin slice_id conocido no hay handoff que registrar (el hub
# lo rechazaría elemento a elemento) y tampoco se consume la marca once-per-sesión.
SLICE_ID_HANDOFF="$(projection_get active_slice.slice_id "")"
# [#74] Con identidad HEREDADA (worktree sin credenciales propias) config_root es el clon
# principal: el handoff caería en SU cola, para SU unidad, y su daemon lo enviaría con SU token.
# Se avisa igual, pero sin encolar ni consumir la marca.
if config_is_inherited_root; then
  if [ -n "$SLICE_ID_HANDOFF" ]; then
    echo "⚠ context-monitor: este árbol no tiene identidad propia; el handoff no se registra en el hub (iría firmado por el agente del clon principal). Alta: bash .claude/hooks/bonita/slice-ops.sh register" >&2
  fi
  SLICE_ID_HANDOFF=""
fi

python3 - "$BRIDGE" "$WARN" "$CRIT" "$STALE" "$EVT" "$AUTO" "$EVENT_OUT" "$MARK" "$HINT" "$BRANCH" "$SLICE_BRANCH" "$SLICE_ID_HANDOFF" <<'PY' 2>/dev/null || true
import json,sys,os,time
bridge,warn,crit,stale,evt,auto,event_out,mark,hint,rama,rama_unidad,slice_id=sys.argv[1:13]
warn,crit,stale=int(warn),int(crit),int(stale)
try: b=json.load(open(bridge))
except Exception: sys.exit(0)
if time.time()-b.get("ts",0) > stale: sys.exit(0)   # métrica vieja
rem=b.get("remaining_pct",100)
sev = "critical" if rem<=crit else ("warning" if rem<=warn else None)
if not sev: sys.exit(0)

iso=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
emit=False
resume=hint or "revisar progreso y continuar"
if rama.startswith(("fix/","chore/")) and rama != rama_unidad:
    resume=f"[rama {rama}: carril de mantenimiento; unidad en pausa] "+resume

if sev=="critical" and slice_id:
    # El guard once-per-sesión no puede vivir en un fichero de estado (no lo hay): marca local.
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

if sev=="warning":
    msg=(f"⚠️ Contexto al {rem}% restante. Acércate a un punto natural de corte "
         "(fin de fase/gate). No inicies trabajo complejo nuevo.")
else:
    tail=(" Handoff registrado en el hub (handoff_recorded)." if emit else "")
    cont=(" auto_checkpoint=ON: continúa en sesión fresca." if auto=="true" else
          " Avisa al usuario para reiniciar en un punto natural.")
    msg=(f"🛑 Contexto CRÍTICO al {rem}% restante.{tail} El estado de la unidad vive en el hub;"
         f" no reescribas handoff manual.{cont}")
# En 'Stop', inyectar additionalContext RE-LANZA el turno (re-prompt): repetirlo en cada intento
# de cierre entra en bucle hasta el tope CLAUDE_CODE_STOP_HOOK_BLOCK_CAP. Por eso en 'Stop' se
# re-lanza como MUCHO una vez por sesión y solo en la TRANSICIÓN a crítico. 'warning' nunca
# inyecta en 'Stop'.
if evt=="Stop" and not (sev=="critical" and emit): sys.exit(0)
print(json.dumps({"hookSpecificOutput":{"hookEventName":evt,"additionalContext":msg}}))
PY

# El evento se encola FUERA del bloque python (encolar es competencia del cliente bash) y así el
# stdout del hook queda limpio pase lo que pase. Sin slice_id NO se encola: al ser un tipo
# protegido de la evicción, un handoff rechazado quedaría como poison pill en la cola.
if [ -s "$EVENT_OUT" ] && [ -n "$SLICE_ID_HANDOFF" ]; then
  runtime_enqueue_event "handoff_recorded" "$(cat "$EVENT_OUT")" "$SLICE_ID_HANDOFF" >/dev/null 2>&1
fi
rm -f "$EVENT_OUT"
exit 0
