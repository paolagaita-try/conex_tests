#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/lib/projection.sh
# projection.sh — lectores de la caché de proyección local [EP-OR-08-B].
# La caché la ESCRIBE session-start.sh (vía lib/agent-context.sh) desde GET /agent/context;
# aquí solo se LEE: ninguna función de este fichero toca la red, y de esa garantía dependen
# los cuatro guards de PreToolUse (spec §4.2-B: «PreToolUse: prohibida la red»).
# Diseño fail-open, igual que config.sh: sin caché, sin python3 o con JSON
# corrupto se devuelve el default y jamás se lanza.

source "$(dirname "${BASH_SOURCE[0]}")/runtime-client.sh"

# projection_get <clave.punteada> <default>
# Escalares tal cual; booleanos en minúsculas (true/false, comparables desde bash);
# dict/list como JSON compacto para encadenar con python3 en el llamador.
projection_get() {
  local key="$1" def="$2" file
  file="$(runtime_projection_path)"
  [ -f "$file" ] || { echo "$def"; return; }
  command -v python3 >/dev/null 2>&1 || { echo "$def"; return; }
  python3 - "$file" "$key" "$def" <<'PY' 2>/dev/null || echo "$def"
import json,sys
path,key,default=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(path))
    for part in key.split("."):
        if isinstance(d,dict) and part in d:
            d=d[part]
        else:
            raise KeyError(part)
    if d is None:
        print(default)
    elif isinstance(d,bool):
        print(str(d).lower())
    elif isinstance(d,(dict,list)):
        print(json.dumps(d,ensure_ascii=False))
    else:
        print(d)
except Exception:
    print(default)
PY
}

# projection_age_seconds — segundos desde `fetched_at`. 999999 si no hay caché, no hay
# python3 o la fecha es ilegible (equivale a «infinitamente vieja»: el llamador avisará
# de stale en vez de fingir frescura).
projection_age_seconds() {
  local file; file="$(runtime_projection_path)"
  [ -f "$file" ] || { echo 999999; return; }
  command -v python3 >/dev/null 2>&1 || { echo 999999; return; }
  python3 - "$file" <<'PY' 2>/dev/null || echo 999999
import json,sys,datetime
try:
    d=json.load(open(sys.argv[1]))
    t=datetime.datetime.strptime(d.get("fetched_at") or "","%Y-%m-%dT%H:%M:%SZ")
    t=t.replace(tzinfo=datetime.timezone.utc)
    now=datetime.datetime.now(datetime.timezone.utc)
    print(max(0,int((now-t).total_seconds())))
except Exception:
    print(999999)
PY
}

# projection_is_stale — rc 0 si la caché supera runtime.stale_seconds (default 900 s).
# rc, no stdout: se usa como condición (`if projection_is_stale; then …`).
projection_is_stale() {
  local age max
  age="$(projection_age_seconds)"
  max="$(config_get runtime.stale_seconds 900)"
  case "$max" in ''|*[!0-9]*) max=900 ;; esac
  case "$age" in ''|*[!0-9]*) age=999999 ;; esac
  [ "$age" -gt "$max" ]
}

# ── Caché del último claim (.claude/state/claim.json) ────────────────────────────────
# La escribe `slice-ops.sh claim` con la respuesta del hub (ClaimOut = TaskClaimOut |
# MicroWorkClaimOut). Guarda lo que /agent/context NO trae: el título de la unidad y, sobre
# todo, el micro-work reclamado (su id es lo único que liga los subcomandos micro-* y el
# heartbeat con su carril). Solo lectura aquí, sin red, como el resto de este fichero.

claim_cache_path() { echo "$(config_root)/.claude/state/claim.json"; }

# claim_cache_get <clave> <default> — escalar de primer nivel de la caché del claim.
claim_cache_get() {
  local key="$1" def="$2" file
  file="$(claim_cache_path)"
  [ -f "$file" ] || { echo "$def"; return; }
  command -v python3 >/dev/null 2>&1 || { echo "$def"; return; }
  python3 - "$file" "$key" "$def" <<'PY' 2>/dev/null || echo "$def"
import json,sys
try:
    v=json.load(open(sys.argv[1])).get(sys.argv[2])
except Exception:
    v=None
print(sys.argv[3] if v is None or isinstance(v,(dict,list)) else v)
PY
}

# claim_micro_work_id — id del micro-work reclamado y VIVO ("" si el último claim fue una unidad,
# si no hay caché o si el micro-work llegó a un terminal: `done` o `escalated`).
claim_micro_work_id() {
  local wt ph
  wt="$(claim_cache_get work_type "")"
  [ "$wt" = "micro_work" ] || { echo ""; return; }
  ph="$(claim_cache_get phase "")"
  case "$ph" in done|escalated) echo ""; return ;; esac
  claim_cache_get micro_work_id ""
}
