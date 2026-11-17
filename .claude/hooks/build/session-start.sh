#!/usr/bin/env bash
# session-start.sh — SessionStart (startup|clear|compact) [EP-OR-08-B].
# La parte de RED del arranque de sesión: registro idempotente del agente (con el catálogo
# de asset types del paquete), hidratación de la caché de proyección desde /agent/context,
# sincronización de contexto por hash y aseguramiento del daemon de heartbeat.
# El RENDER del estado a `additionalContext` lo hace load-build-state.sh, que corre después.
# Fail-open absoluto: cualquier fallo imprime un aviso por stderr y sale 0 — un runtime
# caído jamás impide arrancar una sesión (RNF-6).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"
source "$HERE/lib/agent-context.sh"
# [#74] La versión del arnés y el catálogo de asset types viven en lib/harness-meta.sh:
# `slice-ops.sh register` los necesita exactamente iguales para dar de alta un worktree.
source "$HERE/lib/harness-meta.sh"

cat >/dev/null 2>&1   # consumir el payload del hook (protocolo); no se usa aquí

MODE="$(runtime_mode)"
[ "$MODE" = "legacy" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0
[ -n "$(runtime_url)" ] || exit 0   # sin `trycore-build init` (sub-slice D) no hay runtime

HV="$(harness_version)"
AT="$(harness_asset_types)"

runtime_register "$HV" "$AT"
RC=$?
if [ "$RC" -eq 2 ]; then
  echo "⛔ El runtime rechaza esta versión del arnés ($HV): incompatible_version." >&2
  echo "   Actualiza el paquete (npm i -g @trycore-co/spec-build-harness@latest) y reabre la sesión." >&2
  echo "   Mientras tanto se trabaja con la caché local: los guards siguen operando." >&2
  exit 0
elif [ "$RC" -ne 0 ]; then
  # El registro RE-PUBLICA el catálogo de asset types (los tipos `arch.*` del paquete) en CADA
  # arranque; si falla por red, token o un 4xx del endpoint, el catálogo NO se actualiza en el
  # hub. Antes esto era SILENCIOSO (solo se avisaba del 409 de versión), así que el síntoma
  # «los tipos del arnés no aparecen en la consola» quedaba sin pista. Fail-open: se sigue con
  # la caché local, pero se avisa para que el fallo sea diagnosticable.
  echo "⚠ No se pudo registrar el agente en el runtime: el catálogo de asset types no se re-publicó." >&2
  echo "   Se sigue con la caché local. Si faltan tipos en la consola, reintenta el alta:" >&2
  echo "   bash .claude/hooks/build/slice-ops.sh register --force" >&2
fi

if ! agent_context_fetch_and_cache; then
  echo "⚠ El runtime no respondió: se trabaja con la caché de proyección local." >&2
fi

EXPECTED="$(projection_get context.manifest_hash "")"
[ -n "$EXPECTED" ] || EXPECTED="$(runtime_field manifest_hash)"
bash "$HERE/context-sync.sh" "$EXPECTED"

bash "$HERE/heartbeat.sh" --ensure "$PPID" >/dev/null 2>&1

exit 0
