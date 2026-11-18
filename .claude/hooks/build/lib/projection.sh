#!/usr/bin/env bash
# projection.sh — lectores de la caché de proyección local [EP-OR-08-B].
# La caché la ESCRIBE session-start.sh (vía lib/agent-context.sh) desde GET /agent/context;
# aquí solo se LEE: ninguna función de este fichero toca la red, y de esa garantía dependen
# los cuatro guards de PreToolUse (spec §4.2-B: «PreToolUse: prohibida la red»).
# Diseño fail-open, igual que config.sh/state-io.sh: sin caché, sin python3 o con JSON
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
