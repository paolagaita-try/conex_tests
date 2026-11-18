#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/session-start.sh
# session-start.sh — SessionStart (startup|clear|compact).
# La parte de RED del arranque de sesión: registro idempotente del agente (con el catálogo
# de asset types del paquete), hidratación de la caché de proyección desde /agent/context,
# sincronización de contexto por hash y aseguramiento del daemon de heartbeat.
# El RENDER del estado a `additionalContext` lo hace load-build-state.sh, que corre después.
# Fail-open absoluto: cualquier fallo imprime un aviso por stderr y sale 0 — un hub caído
# jamás impide arrancar una sesión. Modo servidor siempre (U16): sin hub se sigue con la caché.
# Cambios sobre el original: sin la salida temprana del modo sin hub; sin credenciales se AVISA
# (antes callaba); un worktree que heredó la identidad del clon principal NO se registra con el
# token ajeno (lee el hub, pero el alta es `slice-ops.sh register`).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"
source "$HERE/lib/agent-context.sh"
# [#74] La versión del arnés y el catálogo de asset types viven en lib/harness-meta.sh:
# `slice-ops.sh register` los necesita exactamente iguales para dar de alta un worktree.
source "$HERE/lib/harness-meta.sh"

cat >/dev/null 2>&1   # consumir el payload del hook (protocolo); no se usa aquí

command -v python3 >/dev/null 2>&1 || exit 0
if [ -z "$(runtime_url)" ] || [ -z "$(runtime_field project_token)" ]; then
  echo "⚠ arnés Bonita sin credenciales del hub: este proyecto no reporta al IA Hub todavía." >&2
  echo "   Regístralo con un token de agente del ADMIN (por stdin, nunca por argumento):" >&2
  echo "     trycore-bonita init --token-stdin   ·   o   bash .claude/hooks/bonita/slice-ops.sh register" >&2
  exit 0
fi

HEREDADA=0
if config_is_inherited_root; then
  # [#74] Solo LECTURA con la identidad heredada: ni registro, ni sincronización de contexto
  # (su POST /context/synced iría firmado por el agente del principal), ni heartbeat (renovaría
  # el lease del otro agente). Se refresca la caché de proyección, que es local.
  HEREDADA=1
  echo "⚠ este árbol no tiene identidad propia: se lee el hub con las credenciales del clon principal" >&2
  echo "   ($(config_main_clone_root)), pero no se registra, ni sincroniza, ni renueva leases con su token." >&2
  echo "   Para reclamar y reportar desde aquí: bash .claude/hooks/bonita/slice-ops.sh register" >&2
else
  HV="$(harness_version)"
  AT="$(harness_asset_types)"
  runtime_register "$HV" "$AT"
  RC=$?
  if [ "$RC" -eq 2 ]; then
    echo "⛔ El hub rechaza esta versión del arnés ($HV): incompatible_version." >&2
    echo "   Actualiza el arnés (trycore-bonita update) y reabre la sesión." >&2
    echo "   Mientras tanto se trabaja con la caché local: los guards siguen operando." >&2
    exit 0
  fi
fi

if ! agent_context_fetch_and_cache; then
  echo "⚠ El hub no respondió: se trabaja con la caché de proyección local." >&2
fi

[ "$HEREDADA" = 1 ] && exit 0

EXPECTED="$(projection_get context.manifest_hash "")"
[ -n "$EXPECTED" ] || EXPECTED="$(runtime_field manifest_hash)"
bash "$HERE/context-sync.sh" "$EXPECTED"

bash "$HERE/heartbeat.sh" --ensure "$PPID" >/dev/null 2>&1

exit 0
