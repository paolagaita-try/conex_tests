#!/usr/bin/env bash
# scaffold-guard.sh — PreToolUse · Write/Edit/MultiEdit
# Backstop determinista del "Paso 1 fundamental": no se escribe código de slice sin
# scaffold confirmado. Enfoque A (por estado/fase): bloquea (exit 2) SOLO si hay un
# active_slice en fase de código (red/green/refactor/smoke/api/data) y scaffold.confirmed
# no es true. Permite crear el scaffold y planificar (sin slice, o fases dor/change).
# AUTO-ARME: si no existe build-state.json, no hay nada que vigilar -> exit 0.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

INPUT="$(cat)"

# [EP-OR-08-B] En modo runtime los hechos vienen de la caché de proyección (la escribe
# session-start.sh desde /agent/context), NUNCA de la red: este hook corre en PreToolUse y
# la red está prohibida aquí. En legacy|dual el fichero sigue siendo primario (spec §6.1).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"
if [ "$(runtime_mode)" = "runtime" ]; then
  CACHE="$(runtime_projection_path)"
  if [ ! -f "$CACHE" ]; then
    # Sin proyección hay dos casos opuestos y hay que separarlos: si el proyecto
    # no tiene credenciales es auto-arme (aún no usa el arnés) y se deja pasar;
    # si las tiene, este agente está DESCONECTADO del hub y seguir escribiendo
    # código es justo lo que produce trabajo duplicado y choques entre workers.
    if runtime_disconnected; then
      echo "⛔ sin conexión con el hub: hay credenciales del proyecto pero no hay proyección local." >&2
      echo "   Este agente no sabe qué trabajo tiene asignado, así que no puede escribir código." >&2
      echo "   Recupérala con \`slice-ops.sh status\` (refresca /agent/context) y reclama con \`/build:claim\`." >&2
      echo "   Si esto es un worktree: el estado del arnés vive en el clon principal y no viaja al worktree." >&2
      exit 2
    fi
    exit 0   # auto-arme: el proyecto aún no usa el arnés, nada que vigilar
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "⛔ scaffold-guard: python3 no disponible; no puedo verificar el gate de scaffold. Instala python3 (trycore-build doctor)." >&2
    exit 2
  fi
  PHASE="$(projection_get active_slice.phase "")"
  case "$PHASE" in
    red|green|refactor|smoke|api|data) ;;
    *) exit 0 ;;   # sin slice o en dor/change/pr/archived: permitido
  esac
  [ "$(projection_get project.scaffold_confirmed false)" = "true" ] && exit 0
  echo "⛔ scaffold-guard (Paso 1 fundamental): el slice está en fase de código pero el scaffold NO está confirmado." >&2
  echo "   Confirma primero que existe un scaffold runnable del proyecto (ver building-a-slice Fase 0 / DoR)." >&2
  echo "   El arnés NO genera el scaffold: créalo según tu stack (stack-allowlist.json) y confírmalo." >&2
  projection_is_stale && echo "   ⚠ Veredicto emitido con proyección stale (sin refrescar): el runtime no respondió en el último arranque." >&2
  exit 2
fi

# Camino legacy|dual: leer build-state.json
STATE="$ROOT/.claude/state/build-state.json"
[ -f "$STATE" ] || exit 0

# Guarda python3 [H4]: si falta, no podemos leer el estado de forma fiable. Fail-closed
# DIRIGIDO: solo bloqueamos si la edición NO es del propio scaffold/planificación obvia.
if ! command -v python3 >/dev/null 2>&1; then
  echo "⛔ scaffold-guard: python3 no disponible; no puedo verificar el gate de scaffold. Instala python3 (trycore-build doctor)." >&2
  exit 2
fi

VERDICT="$(STATE="$STATE" python3 <<'PY' 2>/dev/null
import os, sys, json
try:
    d = json.load(open(os.environ["STATE"]))
except Exception:
    sys.exit(0)  # estado ilegible -> no bloquear (auto-arme)
slice_ = d.get("active_slice")
if not slice_:
    sys.exit(0)  # sin slice: se permite crear el scaffold / planificar
code_phases = {"red", "green", "refactor", "smoke", "api", "data"}
if slice_.get("phase") not in code_phases:
    sys.exit(0)  # fases dor/change/pr/archived: permitido
if (d.get("scaffold") or {}).get("confirmed") is True:
    sys.exit(0)  # scaffold confirmado: permitido
print("BLOCK")
PY
)"

if [ "$VERDICT" = "BLOCK" ]; then
  echo "⛔ scaffold-guard (Paso 1 fundamental): el slice está en fase de código pero el scaffold NO está confirmado." >&2
  echo "   Confirma primero que existe un scaffold runnable del proyecto (ver building-a-slice Fase 0 / DoR)." >&2
  echo "   El arnés NO genera el scaffold: créalo según tu stack (stack-allowlist.json) y confírmalo." >&2
  exit 2
fi
exit 0
