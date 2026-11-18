#!/usr/bin/env bash
# dual-compare.sh — comparador dual (hook Stop) [EP-OR-08-E].
# En modo dual el fichero es primario y cada transición se espeja al runtime
# (protocolo-cliente-runtime §10: POST …/mirror/transitions). Este comparador detecta
# cuando el REDUCER del servidor llegó a una proyección distinta de lo que dice el
# fichero local — señal de un espejo rechazado o perdido. Discrepancia = issue
# bloqueante DEL CORTE (spec riesgos §4: "Divergencia dual… comparador automático en el
# hook Stop; discrepancia = issue bloqueante del corte") — nunca bloquea el trabajo
# local, se escala para revisión humana vía el mismo canal que /build:escalate.
# Fail-open en TODO: sin dual, sin python3, sin build-state.json o con JSON corrupto,
# sale 0 sin escalar nada.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/agent-context.sh"

MODE="$(runtime_mode)"
[ "$MODE" = "dual" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

ROOT="$(config_root)"
STATE_FILE="$ROOT/.claude/state/build-state.json"
[ -f "$STATE_FILE" ] || exit 0

# Refresco best-effort ANTES de comparar: Stop no es sensible a latencia como
# PreToolUse (protocolo §4.2-B), y sin refresco fresco una discrepancia real podría
# quedar enmascarada por una caché vieja de esta misma sesión.
agent_context_fetch_and_cache >/dev/null 2>&1 || true

FILE_SLICE="$(python3 - "$STATE_FILE" <<'PY' 2>/dev/null
import json,sys
try:
    st = json.load(open(sys.argv[1]))
except Exception:
    print("null")
    sys.exit(0)
sl = st.get("active_slice")
if not isinstance(sl, dict):
    print("null")
else:
    print(json.dumps({
        "epica": sl.get("epica"),
        "phase": sl.get("phase"),
        "gates": sl.get("gates") if isinstance(sl.get("gates"), dict) else {},
    }))
PY
)"
[ -n "$FILE_SLICE" ] || exit 0

PROJ="$(runtime_projection_read)"

REASONS_JSON="$(python3 - "$FILE_SLICE" "$PROJ" <<'PY' 2>/dev/null
import json,sys
try:
    file_slice = json.loads(sys.argv[1])
    proj = json.loads(sys.argv[2]) if sys.argv[2] else {}
except Exception:
    print("[]")
    sys.exit(0)
proj_slice = proj.get("active_slice") if isinstance(proj, dict) else None

reasons = []
if file_slice and not proj_slice:
    reasons.append("el fichero tiene un slice activo (%s) pero el runtime no reporta ninguno" % file_slice.get("epica"))
elif proj_slice and not file_slice:
    reasons.append("el runtime reporta un slice activo (%s) pero el fichero no tiene ninguno" % proj_slice.get("epic_code"))
elif file_slice and proj_slice:
    if file_slice.get("epica") != proj_slice.get("epic_code"):
        reasons.append("épica distinta: fichero=%s runtime=%s" % (file_slice.get("epica"), proj_slice.get("epic_code")))
    if file_slice.get("phase") != proj_slice.get("phase"):
        reasons.append("fase distinta: fichero=%s runtime=%s" % (file_slice.get("phase"), proj_slice.get("phase")))
    fg = file_slice.get("gates") or {}
    pg = proj_slice.get("gates") or {}
    for k in sorted(set(fg) & set(pg)):
        fv, pv = fg.get(k), pg.get(k)
        # Solo gates YA resueltos en ambos lados (True/False); null=pendiente no cuenta.
        if fv is not None and pv is not None and fv != pv:
            reasons.append("gate %s distinto: fichero=%s runtime=%s" % (k, fv, pv))

print(json.dumps(reasons, ensure_ascii=False))
PY
)"
[ -n "$REASONS_JSON" ] && [ "$REASONS_JSON" != "[]" ] || exit 0

REASON_TEXT="$(python3 -c "import json,sys; print('; '.join(json.loads(sys.argv[1])))" "$REASONS_JSON" 2>/dev/null)"
[ -n "$REASON_TEXT" ] || exit 0

echo "⚠ dual: discrepancia entre el fichero local y la proyección del runtime — ${REASON_TEXT}" >&2
echo "   Se escala para revisión humana (el corte a modo runtime queda bloqueado mientras haya discrepancias sin resolver)." >&2

"$HERE/slice-ops.sh" escalate "Discrepancia dual: ${REASON_TEXT}" >/dev/null 2>&1 || true
exit 0
