#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/session-stop.sh
# session-stop.sh — Stop.
# Flush de la cola al cerrar el turno, pero SIN red en el hilo del hook: deja un sentinela
# en outbox/.flush-request y se asegura de que el daemon esté vivo. El daemon lo consume en
# su siguiente tick y despacha (protocolo §5: «señal local al daemon»).
# Nunca bloquea el cierre: exit 0 siempre, sin stdout (en Stop, stdout inyecta contexto).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"

cat >/dev/null 2>&1   # consumir el payload del hook

# [#74] Con identidad heredada no se toca la cola del clon principal (su daemon despacharía con
# su token): ni sentinela de flush ni daemon. Silencio en stdout (Stop).
config_is_inherited_root && exit 0

DIR="$(runtime_outbox_dir)"
mkdir -p "$DIR" 2>/dev/null
: > "$DIR/.flush-request" 2>/dev/null

bash "$HERE/heartbeat.sh" --ensure "$PPID" >/dev/null 2>&1

exit 0
