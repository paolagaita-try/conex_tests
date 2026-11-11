#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/build-gate-check.sh
# build-gate-check.sh — Stop.
# AUTO-ARME: inerte mientras no exista bonita-project/pom.xml (proyecto Bonita aún sin construir).
# No bloquea: al cerrar el turno, avisa si hay una unidad activa con gates abiertos. La aritmética
# de gates vive en el hub: aquí solo se RENDERIZA lo que dice la proyección. Exit 0 siempre.
# Cambios sobre el original: el arme es el pom del proyecto Bonita, no un manifiesto de Node, y
# sin el camino con fichero de estado local (modo servidor siempre, U16).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"

ROOT="$(config_root)"
[ -f "$ROOT/bonita-project/pom.xml" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
[ -n "$(projection_get active_slice.slice_id "")" ] || exit 0

# [#79] Rama de mantenimiento (fix/*|chore/*) = carril de bugfix que coexiste con una unidad en
# pausa: no es drift, así que el aviso cambia de tono y NO desaconseja abrir el PR del bugfix.
BRANCH="$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null || git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"

abiertos="$(projection_get active_slice.gates '{}' | python3 -c 'import json,sys
try: g=json.load(sys.stdin)
except Exception: g={}
print(", ".join(k for k,v in (g.items() if isinstance(g,dict) else []) if v is not True))' 2>/dev/null)"
[ -n "$abiertos" ] || exit 0
unidad="$(projection_get active_slice.epic_code '?')"
fase="$(projection_get active_slice.phase '?')"
rama_unidad="$(projection_get active_slice.branch '')"
case "$BRANCH" in
  fix/*|chore/*)
    if [ "$BRANCH" != "$rama_unidad" ]; then
      echo "build-gate-check: carril de mantenimiento en '$BRANCH'; la unidad $unidad sigue en pausa (gates abiertos: $abiertos)." >&2
      exit 0
    fi ;;
esac
echo "build-gate-check: unidad $unidad en fase '$fase' con gates abiertos: $abiertos." >&2
echo "   No archives ni abras PR hasta cerrarlos (cada gate con su evidencia: slice-ops.sh gate <gate> pass|fail|na)." >&2
exit 0
