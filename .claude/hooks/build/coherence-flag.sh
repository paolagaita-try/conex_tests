#!/usr/bin/env bash
# coherence-flag.sh — PostToolUse · Write/Edit en openspec/changes/**/proposal.md
# No bloquea: recuerda validar la trazabilidad del change recién tocado.
set -uo pipefail

INPUT="$(cat)"

# Guarda python3 [H4]: hook informativo no-bloqueante; si falta python3, omite el recordatorio.
command -v python3 >/dev/null 2>&1 || exit 0

FILE="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    ti=json.load(sys.stdin).get("tool_input",{})
    print(ti.get("file_path") or ti.get("path") or "")
except Exception:
    print("")' 2>/dev/null)"

case "$FILE" in
  *openspec/changes/*/proposal.md)
    echo "🔗 proposal.md modificado: corre el agente change-epic-coherence para validar el bloque '## Trazabilidad' (Épica EP-XXX / Historias HU-XXX) y 'openspec validate'." >&2
    ;;
esac
exit 0
