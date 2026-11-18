#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/event-emitter.sh
# event-emitter.sh — PostToolUse (Bash|Edit|Write|MultiEdit|Task).
# La telemetría es propiedad del arnés, no del modelo: este hook NO puede omitirse desde el
# prompt. Nunca abre socket (protocolo §2/§5): el despacho lo hace el daemon.
# Contenido permitido si algún día se emite: SOLO metadatos (herramienta, ruta relativa, argv0).
# Jamás código fuente ni el comando completo (protocolo §8: un comando puede llevar credenciales).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"

# El stdin del hook se consume y se descarta (higiene del pipe; no se usa).
cat >/dev/null 2>&1 || true

# [#44] `tool_use_recorded` NO existe en el catálogo v2 del hub (event_catalog.SCHEMAS):
# encolarlo era ruido garantizado en outbox/rejected/. No se emite telemetría de uso de
# herramienta hasta que el hub añada el tipo al catálogo; entonces se reactiva aquí.

# Comprobación barata del daemon (stat del pidfile + kill -0, SIN red): un daemon caído a
# mitad de sesión no debe quedar muerto durante horas hasta el próximo SessionStart.
bash "$HERE/heartbeat.sh" --ensure "$PPID" >/dev/null 2>&1

exit 0
