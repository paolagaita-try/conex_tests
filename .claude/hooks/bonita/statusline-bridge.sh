#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/statusline-bridge.sh
# statusline-bridge.sh — statusLine command (canal CLI). Imprime la línea de estado y escribe
# el puente de contexto que lee context-monitor.sh. Fail-open siempre.
# Plano de contexto: versión sincronizada (✓ vN), proyección sin refrescar (⚠ stale) y lease
# perdido (⚠ lease). Cero red: todo sale de ficheros locales (caché de proyección y estado del
# daemon). Cambios sobre el original: modo servidor siempre y etiqueta «bonita».
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
payload="$(cat)"
command -v python3 >/dev/null 2>&1 || { echo "🏗️ bonita"; exit 0; }

source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"

CTXTAG=""
if projection_is_stale; then
  CTXTAG=" · ⚠ stale"
else
  ver="$(projection_get context.version "")"
  [ -n "$ver" ] && CTXTAG=" · ✓ v$ver"
fi
if grep -q '"lease_lost": *true' "$(config_root)/.claude/state/heartbeat-status.json" 2>/dev/null; then
  CTXTAG="$CTXTAG · ⚠ lease"
fi

echo "$payload" | CTXTAG="$CTXTAG" python3 -c '
import json,sys,os,time,re,tempfile
try:
    p=json.load(sys.stdin)
except Exception:
    print("🏗️ bonita"+os.environ.get("CTXTAG","")); sys.exit(0)
sid=str(p.get("session_id","default"))
if re.search(r"[\\/]|\.\.", sid): sid=re.sub(r"[^A-Za-z0-9_-]","_",sid)  # sanitiza path traversal
rem=None
try: rem=int(p.get("context_window",{}).get("remaining_percentage"))
except Exception: rem=None
if rem is not None:
    d={"remaining_pct":rem,"used_pct":100-rem,"ts":int(time.time())}
    path=os.path.join(tempfile.gettempdir(), f"claude-ctx-{sid}.json")
    try:
        fd,tmp=tempfile.mkstemp(dir=tempfile.gettempdir(),prefix=".ctx-",suffix=".tmp")
        try:
            with os.fdopen(fd,"w") as f: json.dump(d,f)
            os.replace(tmp,path)
        except Exception:
            try: os.unlink(tmp)
            except OSError: pass
    except Exception: pass
tag = f"🏗️ bonita · ctx {rem}%" if rem is not None else "🏗️ bonita"
print(tag+os.environ.get("CTXTAG",""))
' 2>/dev/null || echo "🏗️ bonita"
