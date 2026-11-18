#!/usr/bin/env bash
# context-sync.sh — sincronización de contexto content-addressed [EP-OR-08-B]
# (protocolo-cliente-runtime §4). NO es un hook registrado: lo invoca session-start.sh y,
# desde el sub-slice C, las skills antes de reclamar.
#   uso: context-sync.sh [manifest_hash_esperado]
# Fail-open: sin runtime, sin python3 o con manifiesto ilegible sale 0 y deja el lock
# anterior intacto — se sigue trabajando con el último contexto sincronizado.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"

MODE="$(runtime_mode)"
[ "$MODE" = "legacy" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

EXPECTED="${1:-}"
[ -n "$EXPECTED" ] || EXPECTED="$(runtime_field manifest_hash)"
CURRENT="$(runtime_lock_manifest_hash)"
[ -n "$EXPECTED" ] && [ "$EXPECTED" = "$CURRENT" ] && exit 0

PID="$(runtime_field project_id)"
[ -n "$PID" ] || exit 0

MANIFEST="$(runtime_get "/projects/$PID/context/manifest")"
[ "$(runtime_http_status)" = "200" ] || exit 0   # offline: se sigue con el lock viejo

ROOT="$(config_root)"
WORK="$(mktemp -d)" || exit 0
trap 'rm -rf "$WORK"' EXIT
printf '%s' "$MANIFEST" > "$WORK/manifest.json"

# Validación temprana: el manifiesto debe parsear como objeto JSON con un 'manifest_hash'
# no vacío. Un body no-JSON, un array, o una página de error de proxy servida con status
# 200 se descartan AQUÍ, antes de planificar/descargar/sellar nada — el lock existente
# queda intacto y no se emite context/synced con un hash falso.
NEWHASH="$(python3 -c '
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print(d.get("manifest_hash","") if isinstance(d,dict) else "")
except Exception:
    print("")
' "$WORK/manifest.json" 2>/dev/null)"
[ -n "$NEWHASH" ] || exit 0

# Plan de descarga: una línea "path<TAB>sha256" por archivo GOBERNADO que cambió.
# Las rutas se validan AQUÍ (antes de tocar disco): solo config/, rules/ y docs-cache/,
# nunca absolutas, nunca con "..". Un manifiesto hostil o con una entrada de destino no
# gobernado (CLAUDE.md, que necesita markers.ts — sub-slice D) no escribe nada: se lista
# como "no aplicado" y NO impide converger el hash.
python3 - "$WORK/manifest.json" "$(runtime_lock_path)" "$WORK/skipped.txt" > "$WORK/plan.tsv" <<'PY' 2>/dev/null
import json,sys,posixpath
ALLOWED_PREFIXES=("config/","rules/","docs-cache/")
try:
    man=json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
try:
    lock=json.load(open(sys.argv[2]))
except Exception:
    lock={}
have={}
for f in (lock.get("files") or []):
    if isinstance(f,dict) and f.get("path"):
        have[f["path"]]=f.get("sha256")
skipped=[]
for f in (man.get("files") or []):
    if not isinstance(f,dict):
        continue
    path=f.get("path") or ""
    sha=f.get("sha256") or ""
    if (not path or not sha or path.startswith("/") or ".." in path.split("/")
            or path != posixpath.normpath(path)
            or not path.startswith(ALLOWED_PREFIXES)):
        skipped.append(path or "(sin ruta)")
        continue
    if have.get(path) == sha:
        continue
    sys.stdout.write(path+"\t"+sha+"\n")
sys.stdout.flush()
try:
    with open(sys.argv[3],"w") as out:
        for s in skipped:
            out.write(s+"\n")
except Exception:
    pass
PY

# Si el plan no se generó (python falló), se trata como plan vacío: nada que descargar,
# nada que sellar. La redirección nunca debe fallar por fichero ausente.
[ -f "$WORK/plan.tsv" ] || : > "$WORK/plan.tsv"
plan=()
while IFS= read -r line; do
  [ -n "$line" ] && plan+=("$line")
done < "$WORK/plan.tsv"

applied=0
planned=${#plan[@]}
if [ "$planned" -gt 0 ]; then
  for line in "${plan[@]}"; do
    # Campos separados por TAB. Se parten con `cut` (delimitador por defecto = tabulador)
    # en vez de expansión de parámetros: un tabulador literal dentro de ${…%%…} es
    # invisible y cualquier editor que lo convierta en espacios rompería el parseo en
    # silencio, dejando rutas con el sha256 pegado.
    rel="$(printf '%s' "$line" | cut -f1)"
    sha="$(printf '%s' "$line" | cut -f2)"
    enc="$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$rel" 2>/dev/null)"
    [ -n "$enc" ] || continue
    body="$(runtime_get "/projects/$PID/context/files?path=$enc&sha256=$sha")"
    [ "$(runtime_http_status)" = "200" ] || continue
    printf '%s' "$body" > "$WORK/blob.json"
    if python3 - "$WORK/blob.json" "$ROOT/.claude/$rel" <<'PY' 2>/dev/null
import json,sys,os,tempfile
blob_path,dest=sys.argv[1],sys.argv[2]
raw=open(blob_path,encoding="utf-8",errors="replace").read()
try:
    d=json.loads(raw)
    content=d["content"] if isinstance(d,dict) and "content" in d else raw
except Exception:
    content=raw
if not isinstance(content,str):
    content=json.dumps(content,indent=2,ensure_ascii=False)
dirn=os.path.dirname(dest) or "."
os.makedirs(dirn,exist_ok=True)
fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".ctx-sync.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        out.write(content); out.flush(); os.fsync(out.fileno())
    os.replace(tmp,dest)   # sustitución atómica, patrón v0.8.1
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    sys.exit(1)
PY
    then
      applied=$((applied + 1))
    fi
  done
fi

if [ "$applied" -lt "$planned" ]; then
  # Convergencia parcial: NO se sella el hash nuevo (el lock mentiría sobre lo que hay en
  # disco). El próximo SessionStart reintenta solo lo que falta.
  echo "⚠ contexto: $applied/$planned archivo(s) sincronizados; el lock sigue en '${CURRENT:-vacío}'. Se reintenta en la próxima sesión." >&2
  exit 0
fi

FILES_JSON="$(python3 - "$WORK/manifest.json" <<'PY' 2>/dev/null
import json,sys
try:
    man=json.load(open(sys.argv[1]))
except Exception:
    man={}
out=[]
for f in (man.get("files") or []):
    if isinstance(f,dict) and f.get("path"):
        out.append({"path":f.get("path"),"sha256":f.get("sha256"),
                    "type_key":f.get("type_key"),"version":f.get("version")})
print(json.dumps(out,ensure_ascii=False))
PY
)"
[ -n "$FILES_JSON" ] || FILES_JSON='[]'
runtime_lock_write "$NEWHASH" "$FILES_JSON"

# Señal de sincronización: endpoint propio (es la única señal SIN slice_id del protocolo).
# 422 = manifiesto desconocido para el servidor -> no se reintenta ni se encola.
CHANGED_JSON="$(python3 - "$WORK/plan.tsv" <<'PY' 2>/dev/null
import json,sys
paths=[]
try:
    for line in open(sys.argv[1]):
        line=line.rstrip("\n")
        if line:
            paths.append(line.split("\t")[0])
except Exception:
    pass
print(json.dumps(paths,ensure_ascii=False))
sys.stdout.flush()
PY
)"
[ -n "$CHANGED_JSON" ] || CHANGED_JSON='[]'
runtime_post "/context/synced" "{\"from_hash\":\"$CURRENT\",\"to_hash\":\"$NEWHASH\",\"files_changed\":$CHANGED_JSON}" >/dev/null
ST="$(runtime_http_status)"
[ "$ST" = "422" ] && echo "⚠ el runtime no reconoce el manifiesto sincronizado (422): revisa 'trycore-build doctor'." >&2

if [ "$applied" -gt 0 ]; then
  echo "⬆ contexto: $applied archivo(s) actualizados (${CURRENT:-sin lock} → $NEWHASH)"
fi
if [ -s "$WORK/skipped.txt" ]; then
  echo "   No aplicados (destino no gobernado por este canal): $(tr '\n' ' ' < "$WORK/skipped.txt")"
fi
exit 0
