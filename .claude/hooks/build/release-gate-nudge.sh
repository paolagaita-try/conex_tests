#!/usr/bin/env bash
# release-gate-nudge.sh — Stop
# Sugiere correr el Release Gate (releasing-a-version) cuando hay ≥2 épicas archivadas sin
# auditar desde el último release. NUNCA bloquea el cierre, NUNCA ejecuta trabajo pesado,
# NUNCA llama al modelo ni escribe estado. Determinista y barato: aritmética de conjuntos
# sobre epicas[] (archivadas − cubiertas), independiente de timestamps.
# El criterio "cierra una línea de release" vive en docs/02-user-story-map/ y NO se intenta aquí
# (lo computa la skill building-a-slice en la fase 8).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"

# [EP-OR-08-B] Igual que reflect-nudge: la aritmética de conjuntos (archivadas − cubiertas)
# es del servidor; este hook renderiza el nudge tipado y jamás bloquea el cierre.
if [ "$(runtime_mode)" = "runtime" ]; then
  projection_get nudges '[]' | python3 -c 'import json,sys
try: ns=json.load(sys.stdin)
except Exception: ns=[]
for n in ns:
    if isinstance(n,dict) and n.get("kind")=="release_gate" and n.get("message"):
        print("💡 Release Gate sugerido: "+n["message"])
        print("   Ejecuta /build:release (o la skill releasing-a-version): corre los gates pesados UNA vez sobre el diff acumulado.")' 2>/dev/null
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE="$ROOT/.claude/state/build-state.json"
[ -f "$STATE" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0   # fail-open: jamás impide cerrar sesión

# Mensaje a STDOUT (no stderr): un Stop hook con exit 0 no bloquea el cierre; el 2>/dev/null
# suprime SOLO trazas de python, nunca el nudge.
python3 - "$STATE" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
hist = d.get("history") or []
rels = d.get("releases") or []
# Épicas ya archivadas (slices cerrados).
archived = {h.get("epica") for h in hist if isinstance(h, dict) and isinstance(h.get("epica"), str)}
# Épicas ya cubiertas por ALGÚN release (pending/passed/failed por igual).
covered = set()
for r in rels:
    if isinstance(r, dict):
        for e in (r.get("epicas") or []):
            if isinstance(e, str):
                covered.add(e)
pend = sorted(archived - covered)
if len(pend) >= 2:
    print(f"💡 Release Gate sugerido: {len(pend)} épicas archivadas sin auditar desde el último release ({', '.join(pend)}).")
    print("   Ejecuta /build:release (o la skill releasing-a-version): corre los gates pesados UNA vez sobre el diff acumulado.")
PY
exit 0
