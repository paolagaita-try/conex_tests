#!/usr/bin/env bash
# lint-bonita.sh — PostToolUse · Write|Edit|MultiEdit
# Tras editar un *.proc, *.bconf o un *.xml de bonita-project/: el XML tiene que estar bien formado.
# Exit 2 con línea y columna en stderr. Entrada ilegible: deja pasar con aviso.
set -uo pipefail
if ! command -v python3 >/dev/null 2>&1; then
  echo "lint-bonita: python3 no disponible; no se comprueba el XML (trycore-bonita doctor)" >&2
  exit 0
fi
HOOK_INPUT="$(cat)" python3 - <<'PY'
import json, os, re, sys
import xml.etree.ElementTree as ET

try:
    datos = json.loads(os.environ.get("HOOK_INPUT", ""))
    ruta = str((datos.get("tool_input") or {}).get("file_path") or "")
except Exception as e:
    print(f"lint-bonita: entrada ilegible ({e}); dejo pasar", file=sys.stderr)
    sys.exit(0)
if not ruta:
    sys.exit(0)
raiz = os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or os.getcwd()
if not os.path.isabs(ruta):
    ruta = os.path.join(datos.get("cwd") or raiz, ruta)
ruta = os.path.normpath(ruta)
norm = ruta.replace(os.sep, "/")
if not (norm.endswith(".proc") or norm.endswith(".bconf") or (norm.endswith(".xml") and "/bonita-project/" in norm)):
    sys.exit(0)
if not os.path.isfile(ruta):
    sys.exit(0)
try:
    ET.parse(ruta)
except ET.ParseError as e:
    linea, col = e.position
    print(f"lint-bonita: {ruta} no es XML bien formado: línea {linea}, columna {col + 1} ({e})", file=sys.stderr)
    sys.exit(2)
except OSError as e:
    print(f"lint-bonita: no pude leer {ruta} ({e}); dejo pasar", file=sys.stderr)
sys.exit(0)
PY
