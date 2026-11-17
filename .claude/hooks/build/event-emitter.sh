#!/usr/bin/env bash
# event-emitter.sh — PostToolUse (Bash|Edit|Write|MultiEdit|Task) [EP-OR-08-B].
# La telemetría es propiedad del arnés, no del modelo: este hook NO puede omitirse desde
# el prompt. Encola en .claude/state/outbox/ y devuelve el control de inmediato — el
# despacho a POST /events lo hace el daemon (protocolo §2/§5). Nunca abre socket.
# Contenido: SOLO metadatos (herramienta, ruta relativa, argv0). Jamás código fuente ni
# el comando completo (protocolo §8: el arnés no envía fuente al runtime, y un comando
# puede llevar credenciales).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"

MODE="$(runtime_mode)"
[ "$MODE" = "legacy" ] && exit 0

# El stdin del hook se consume y se descarta (higiene del pipe; no se usa).
cat >/dev/null 2>&1 || true

# [#44] `tool_use_recorded` NO existe en el catálogo v2 del hub (event_catalog.SCHEMAS):
# encolarlo era ruido garantizado en outbox/rejected/ al drenar, y este hook era justo su
# único productor. NO se emite telemetría de uso de herramienta hasta que el equipo del
# hub decida si añade el tipo al catálogo (decisión pendiente, issue #44); si eso ocurre,
# se reactiva aquí el armado de metadatos que vivía en este bloque hasta la v0.10.x
# (git history: solo herramienta, ruta relativa y argv0 — jamás el comando completo ni el
# fuente, protocolo §8). En legacy este hook ya salía arriba sin encolar: nada cambia.

# Comprobación barata del daemon (stat del pidfile + kill -0, SIN red): un daemon caído a
# mitad de sesión no debe quedar muerto durante horas hasta el próximo SessionStart.
bash "$HERE/heartbeat.sh" --ensure "$PPID" >/dev/null 2>&1

exit 0
