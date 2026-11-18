#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/coherence-flag.sh
# coherence-flag.sh — PostToolUse · Write/Edit en openspec/changes/**/proposal.md
# No bloquea (exit 0 siempre): comprueba que el change recién tocado declare su trazabilidad al
# método Bonita — una sección `## Trazabilidad` con al menos una ruta `docs/07-bonita/` — y
# recuerda que el gate `coherence_link` mide change ↔ docs/07-bonita/ ↔ docs_ref de la unidad.
# Cambios sobre el original: la trazabilidad es a docs/07-bonita/, no a épicas e historias del
# vertical, y se comprueba de verdad en vez de solo recordarla.
set -uo pipefail

INPUT="$(cat)"

# Hook informativo no-bloqueante: si falta python3, omite el recordatorio.
command -v python3 >/dev/null 2>&1 || exit 0

FILE="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    ti=json.load(sys.stdin).get("tool_input",{})
    print(ti.get("file_path") or ti.get("path") or "")
except Exception:
    print("")' 2>/dev/null)"

case "$FILE" in
  *openspec/changes/*/proposal.md) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

VEREDICTO="$(python3 - "$FILE" <<'PY' 2>/dev/null
import re,sys
try:
    txt=open(sys.argv[1],encoding="utf-8",errors="replace").read()
except Exception:
    print("ilegible"); sys.exit(0)
m=re.search(r"^##[ \t]+Trazabilidad[ \t]*$(.*?)(?=^##[ \t]|\Z)", txt, re.M|re.S)
if not m:
    print("sin_seccion")
elif not re.search(r"docs/07-bonita/\S", m.group(1)):
    print("sin_ruta")
else:
    print("ok")
PY
)"

case "$VEREDICTO" in
  sin_seccion)
    echo "⚠ $FILE no tiene sección '## Trazabilidad'. Añádela con al menos una ruta docs/07-bonita/ (p. ej. docs/07-bonita/bdm.md) que el change implementa: sin ella el gate coherence_link no puede pasar." >&2 ;;
  sin_ruta)
    echo "⚠ $FILE tiene '## Trazabilidad' pero ninguna ruta docs/07-bonita/: nombra el artefacto del perfil Bonita que el change implementa, o el gate coherence_link no puede pasar." >&2 ;;
  ok)
    echo "🔗 proposal.md con trazabilidad a docs/07-bonita/: corre 'openspec validate'; el gate coherence_link contrasta el change con docs/07-bonita/ y el docs_ref de la unidad." >&2 ;;
esac
exit 0
