#!/usr/bin/env bash
# build-gate-check.sh — Stop
# AUTO-ARME: inerte mientras no exista package.json.
# No bloquea: al cerrar el turno, avisa si hay un slice activo con gates abiertos.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
# [#79] Rama de mantenimiento (fix/*|chore/*) = carril de bugfix que coexiste con un slice en
# pausa: no es drift, así que el aviso cambia de tono y NO desaconseja abrir el PR del bugfix.
# `symbolic-ref` va primero porque también resuelve el repo recién inicializado (HEAD aún sin
# commits, donde `rev-parse` falla); `rev-parse` queda de reserva para HEAD desacoplado.
BRANCH="$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null || git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
is_maintenance_branch() { case "${1:-}" in fix/*|chore/*) return 0;; *) return 1;; esac; }

# [EP-OR-08-B] En runtime la aritmética de gates vive en el servidor: este hook solo
# RENDERIZA lo que el claim/proyección ya dice. Nunca bloquea (Stop hook, exit 0 siempre).
if [ "$(runtime_mode)" = "runtime" ]; then
  if [ -n "$(projection_get active_slice.slice_id "")" ]; then
    abiertos="$(projection_get active_slice.gates '{}' | python3 -c 'import json,sys
try: g=json.load(sys.stdin)
except Exception: g={}
print(", ".join(k for k,v in g.items() if v is False))' 2>/dev/null)"
    if [ -n "$abiertos" ]; then
      epica="$(projection_get active_slice.epic_code '?')"
      hus="$(projection_get active_slice.hus '[]' | tr -d '[]"')"
      fase="$(projection_get active_slice.phase '?')"
      rama_slice="$(projection_get active_slice.branch '')"
      if is_maintenance_branch "$BRANCH" && [ "$BRANCH" != "$rama_slice" ]; then
        echo "build-gate-check: carril de mantenimiento en '$BRANCH'; el slice $epica sigue en pausa (gates abiertos: $abiertos)." >&2
      else
        echo "build-gate-check: slice $epica [${hus:-—}] en fase '$fase' con gates abiertos: $abiertos." >&2
        echo "   No archives ni abras PR hasta cerrarlos (ver building-a-slice / dod.md)." >&2
      fi
    fi
  fi
  exit 0
fi

[ -f "$ROOT/package.json" ] || exit 0
STATE="$ROOT/.claude/state/build-state.json"
[ -f "$STATE" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

python3 - "$STATE" "$BRANCH" <<'PY' || true
import json,sys
# Fail-open silencioso: este hook escribe sus avisos por el MISMO stderr que vería un
# traceback, así que cualquier estado inesperado (active_slice no-dict, gates lista…)
# sale por la puerta de atrás sin ruido [#79].
try:
    d=json.load(open(sys.argv[1]))
    rama=sys.argv[2] if len(sys.argv)>2 else ""
    s=d.get("active_slice") if isinstance(d,dict) else None
    if not isinstance(s,dict): sys.exit(0)
    g=s.get("gates") or {}
    if not isinstance(g,dict): sys.exit(0)
    abiertos=[k for k,v in g.items() if v is False]
    if abiertos:
        epica=s.get('epica') or '?'
        hus_raw=s.get('hus') or []
        hus=', '.join(str(h) for h in hus_raw) if isinstance(hus_raw,list) else '—'
        # [#79] Carril de mantenimiento: rama fix/*|chore/* distinta de la del slice.
        if rama.startswith(("fix/","chore/")) and rama != (s.get("branch") or ""):
            print(f"build-gate-check: carril de mantenimiento en '{rama}'; el slice {epica} sigue en pausa (gates abiertos: {', '.join(abiertos)}).", file=sys.stderr)
        else:
            print(f"build-gate-check: slice {epica} [{hus or '—'}] en fase '{s.get('phase')}' con gates abiertos: {', '.join(abiertos)}.", file=sys.stderr)
            print("   No archives ni abras PR hasta cerrarlos (ver building-a-slice / dod.md).", file=sys.stderr)
except Exception:
    sys.exit(0)
PY
exit 0
