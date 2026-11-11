#!/usr/bin/env bash
# guard-generados.sh — PreToolUse · Write|Edit|MultiEdit|NotebookEdit y Bash
# Deniega escribir lo generado (build/generados.json) y lo que instala el arnés (tools/arnes/, manifiesto).
# Un hook que no entiende su entrada deja pasar con aviso; uno que reconoce un caso prohibido deniega.
# `set -uo pipefail`, nunca `-e`.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "guard-generados: python3 no disponible; dejo pasar sin comprobar (trycore-bonita doctor)" >&2
  exit 0
fi
# -B: importa generadores/ de tools/arnes/ y no debe dejar __pycache__ ahí (fuera del manifiesto: uninstall no lo quita).
python3 -B "$HERE/lib/guard_generados.py" || { echo "guard-generados: fallo interno; dejo pasar" >&2; exit 0; }
