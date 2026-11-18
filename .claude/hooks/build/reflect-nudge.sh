#!/usr/bin/env bash
# reflect-nudge.sh — Stop
# Ciclo autocorrectivo (reflexión post-sesión): NUNCA bloquea el cierre de sesión.
# Sugiere /build:reflect SOLO si hay slice(s) archivado(s) sin reflexionar (reflected != true).
# Determinista y barato: el razonamiento (qué se aprendió) lo hace el MODELO en /build:reflect.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"

# [EP-OR-08-B] En runtime el cómputo («qué slices quedaron sin reflexionar») lo hace el
# servidor sobre TODO el proyecto, no este clon: aquí solo se renderiza su nudge.
if [ "$(runtime_mode)" = "runtime" ]; then
  projection_get nudges '[]' | python3 -c 'import json,sys
try: ns=json.load(sys.stdin)
except Exception: ns=[]
for n in ns:
    if isinstance(n,dict) and n.get("kind")=="reflect" and n.get("message"):
        print("💡 "+n["message"])
        print("   Ejecuta /build:reflect para proponer convenciones aprendidas a CLAUDE.md (se aplican tras tu aprobación).")' 2>/dev/null
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE="$ROOT/.claude/state/build-state.json"
[ -f "$STATE" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0   # fail-open: jamás impide cerrar sesión

# Mensaje a STDOUT (no stderr): un Stop hook con exit 0 no debe bloquear el cierre;
# el `2>/dev/null` suprime SOLO trazas de python, nunca el nudge.
python3 - "$STATE" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
hist = d.get("history") or []
pend = [h for h in hist if isinstance(h, dict) and h.get("reflected") is not True]
if pend:
    n = len(pend)
    plural = "s" if n != 1 else ""
    print(f"💡 Reflexión pendiente: {n} slice{plural} archivado{plural} sin capturar aprendizajes.")
    print("   Ejecuta /build:reflect para proponer convenciones aprendidas a CLAUDE.md (se aplican tras tu aprobación).")
PY
exit 0
