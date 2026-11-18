#!/usr/bin/env bash
# design-source-guard.sh — PreToolUse · Write/Edit/MultiEdit
# Backstop determinista del "seguro de fuente de diseño": no se escribe código de un slice
# CON UI sin que la fuente de diseño del proyecto esté confirmada. Espejo de scaffold-guard.sh.
# Bloquea (exit 2) SOLO si: hay active_slice en fase de código (red/green/refactor/smoke/api/data),
# el proyecto tiene UI (design_source.applies===true), el slice está marcado UI-pendiente
# (gates.fidelity===false) y design_source.confirmed!==true.
# AUTO-ARME: si no existe build-state.json, exit 0.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

INPUT="$(cat)"  # consumir stdin (protocolo de hook); la decisión es por estado.

# [EP-OR-08-B] Espejo del camino runtime de scaffold-guard: hechos desde la caché de
# proyección, cero red (PreToolUse).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"
if [ "$(runtime_mode)" = "runtime" ]; then
  CACHE="$(runtime_projection_path)"
  if [ ! -f "$CACHE" ]; then
    # auto-arme (sin credenciales) vs desconectado (con credenciales): ver
    # runtime_disconnected en lib/runtime-client.sh.
    if runtime_disconnected; then
      echo "⛔ sin conexión con el hub: hay credenciales del proyecto pero no hay proyección local." >&2
      echo "   Este agente no sabe qué trabajo tiene asignado, así que no puede escribir código." >&2
      echo "   Recupérala con \`slice-ops.sh status\` (refresca /agent/context) y reclama con \`/build:claim\`." >&2
      echo "   Si esto es un worktree: el estado del arnés vive en el clon principal y no viaja al worktree." >&2
      exit 2
    fi
    exit 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "⛔ design-source-guard: python3 no disponible; no puedo verificar el gate de fuente de diseño. Instala python3 (trycore-build doctor)." >&2
    exit 2
  fi
  PHASE="$(projection_get active_slice.phase "")"
  case "$PHASE" in
    red|green|refactor|smoke|api|data) ;;
    *) exit 0 ;;
  esac
  [ "$(projection_get project.design_source_applies false)" = "true" ] || exit 0   # proyecto sin UI: mecanismo apagado
  [ "$(projection_get active_slice.gates.fidelity none)" = "false" ] || exit 0     # solo UI-pendiente (false) cuenta
  [ "$(projection_get project.design_source_confirmed false)" = "true" ] && exit 0
  echo "⛔ design-source-guard: el slice con UI está en fase de código pero la fuente de diseño NO está confirmada." >&2
  echo "   Declara y confirma primero el DESIGN_SOURCE del proyecto (ver building-a-slice Fase 0-bis / DoR)." >&2
  echo "   Genera el prototipo con /build:prototype o declara una fuente existente (prototipo/export), y confírmala." >&2
  projection_is_stale && echo "   ⚠ Veredicto emitido con proyección stale (sin refrescar): el runtime no respondió en el último arranque." >&2
  exit 2
fi

# Camino legacy|dual: leer build-state.json
STATE="$ROOT/.claude/state/build-state.json"
[ -f "$STATE" ] || exit 0

# Guarda python3 [H4]: si falta, no podemos leer el estado de forma fiable. Fail-closed.
if ! command -v python3 >/dev/null 2>&1; then
  echo "⛔ design-source-guard: python3 no disponible; no puedo verificar el gate de fuente de diseño. Instala python3 (trycore-build doctor)." >&2
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
    sys.exit(0)  # sin slice: permitir declarar / planificar
code_phases = {"red", "green", "refactor", "smoke", "api", "data"}
if slice_.get("phase") not in code_phases:
    sys.exit(0)  # fases dor/change/pr/archived: permitido
ds = d.get("design_source") or {}
if ds.get("applies") is not True:
    sys.exit(0)  # proyecto sin UI (o indeterminado): mecanismo apagado
if (slice_.get("gates") or {}).get("fidelity") is not False:
    sys.exit(0)  # solo UI-pendiente (false) cuenta; null/ausente -> no bloquear
if ds.get("confirmed") is True:
    sys.exit(0)  # fuente de diseño confirmada: permitido
print("BLOCK")
PY
)"

if [ "$VERDICT" = "BLOCK" ]; then
  echo "⛔ design-source-guard: el slice con UI está en fase de código pero la fuente de diseño NO está confirmada." >&2
  echo "   Declara y confirma primero el DESIGN_SOURCE del proyecto (ver building-a-slice Fase 0-bis / DoR)." >&2
  echo "   Genera el prototipo con /build:prototype o declara una fuente existente (prototipo/export), y confírmala." >&2
  exit 2
fi
exit 0
