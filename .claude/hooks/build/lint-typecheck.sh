#!/usr/bin/env bash
# lint-typecheck.sh — PostToolUse · Write/Edit en *.ts/*.tsx
# AUTO-ARME: inerte mientras no exista package.json (fase authoring).
# No bloquea: reporta lint/format/typecheck del archivo editado para liberar
# capacidad de razonamiento del modelo (estilo delegado a herramientas).
# El typecheck es INCREMENTAL (--incremental + tsBuildInfoFile persistente): el primer
# run de la sesión paga O(repo) y cada edición posterior paga ~O(delta), para que el
# coste por edición no escale con el tamaño del repo.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
[ -f "$ROOT/package.json" ] || exit 0   # guard de auto-arme

# Guarda python3 [H4]: hook no-bloqueante; sin python3 no podemos extraer el archivo → omite.
command -v python3 >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
FILE="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    ti=json.load(sys.stdin).get("tool_input",{})
    print(ti.get("file_path") or ti.get("path") or "")
except Exception:
    print("")' 2>/dev/null)"

case "$FILE" in
  *.ts|*.tsx) : ;;
  *) exit 0 ;;
esac

cd "$ROOT" || exit 0
HAS() { [ -d node_modules ] && [ -x "node_modules/.bin/$1" ]; }

if HAS prettier; then node_modules/.bin/prettier --write "$FILE" >/dev/null 2>&1 || true; fi
if HAS eslint;   then node_modules/.bin/eslint --fix "$FILE" 2>&1 | sed -n '1,20p' >&2 || true; fi

# Typecheck INCREMENTAL del proyecto. `tsc` siempre recorre todo el grafo de tipos, pero con
# --incremental + un tsBuildInfoFile persistente, tras el primer run cada edición paga solo el delta.
# El .tsbuildinfo vive bajo node_modules/ (que el consumidor casi siempre tiene gitignored) → no
# contamina el repo. Filtramos la salida al archivo editado (grep -F) y la capamos a 20 líneas.
# timeout OPCIONAL: si coreutils está disponible acota un tsconfig patológico; si no, corre sin
# límite (el hook nunca bloquea, así que agotar el timeout solo omite el reporte de esta edición).
# Caveat: proyectos con `composite: true` deben usar `tsc -b`; aquí --noEmit prevalece como hoy
# y los errores se suprimen (|| true), igual que antes de v0.3.x.
if HAS tsc; then
  TSBI="node_modules/.cache/trycore-build/tsbuildinfo"
  mkdir -p "$(dirname "$TSBI")" 2>/dev/null || true
  TSC_TIMEOUT=""
  if   command -v timeout  >/dev/null 2>&1; then TSC_TIMEOUT="timeout 60"
  elif command -v gtimeout >/dev/null 2>&1; then TSC_TIMEOUT="gtimeout 60"; fi
  $TSC_TIMEOUT node_modules/.bin/tsc --noEmit --incremental --tsBuildInfoFile "$TSBI" 2>&1 \
    | grep -F "$FILE" | sed -n '1,20p' >&2 || true
fi
exit 0
