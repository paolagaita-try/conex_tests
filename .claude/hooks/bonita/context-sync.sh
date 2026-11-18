#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/context-sync.sh
# context-sync.sh — sincronización de contexto content-addressed (protocolo-cliente-runtime §4).
# NO es un hook registrado: lo invocan session-start.sh y `slice-ops.sh claim` (antes de
# reclamar y tras un 409 por drift).
#   uso: context-sync.sh [manifest_hash_esperado]
# Fail-open: sin hub, sin python3 o con manifiesto ilegible sale 0 y deja el lock anterior
# intacto — se sigue trabajando con el último contexto sincronizado.
#
# Cambios sobre el original (contrato REAL del hub, trycore-ia-hub origin/develop
# backend/app/modules/orchestrator/context_agent_router.py):
#   - el manifiesto trae las entradas en `asset_versions` (se acepta también `files`, la forma
#     del original);
#   - el contenido se pide a `GET /context/files?path=…&sha256=…` (sin /projects/{id});
#   - la señal es `POST /projects/{id}/context/synced` {from_hash|null, to_hash, files_changed,
#     local_hashes} — con `local_hashes` el hub puede apagar el aviso de drift;
#   - el lock registra SOLO las entradas gobernadas: una entrada rechazada (absoluta, con `..`
#     o fuera de los destinos) no debe acabar en `context_hashes` del claim, que la hashearía
#     desde disco siguiendo esa misma ruta;
#   - el hub gobierna `context/` y `docs/` (context_domain.GOVERNED_PREFIXES), rutas relativas
#     «al directorio de contexto» del agente: se materializan en `.claude/hub-context/<ruta>`
#     (RUNTIME_CONTEXT_DIR), nunca en el `docs/` del proyecto. Se rechaza además `~`, `\` y NUL,
#     y una ruta que, resuelta (symlinks), saliera del directorio de contexto.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"

# Prefijos gobernados por el hub y directorio donde se materializan (lib/runtime-client.sh).
CS_PREFIJOS="$RUNTIME_CONTEXT_PREFIXES"

command -v python3 >/dev/null 2>&1 || exit 0
# [#74] Con identidad heredada no se sincroniza: escribiría en el directorio de contexto del clon
# principal y el POST /context/synced iría firmado por su agente.
if config_is_inherited_root; then
  echo "⚠ context-sync: este árbol no tiene identidad propia; no se sincroniza con el token del clon principal (slice-ops.sh register)." >&2
  exit 0
fi

EXPECTED="${1:-}"
[ -n "$EXPECTED" ] || EXPECTED="$(runtime_field manifest_hash)"
CURRENT="$(runtime_lock_manifest_hash)"
[ -n "$EXPECTED" ] && [ "$EXPECTED" = "$CURRENT" ] && exit 0

PID="$(runtime_field project_id)"
[ -n "$PID" ] || exit 0

MANIFEST="$(runtime_get "/projects/$PID/context/manifest")"
[ "$(runtime_http_status)" = "200" ] || exit 0   # offline: se sigue con el lock viejo

CTXDIR="$(runtime_context_dir)"
WORK="$(mktemp -d)" || exit 0
trap 'rm -rf "$WORK"' EXIT
printf '%s' "$MANIFEST" > "$WORK/manifest.json"

# Validación temprana: el manifiesto debe ser un objeto JSON con `manifest_hash` no vacío. Un
# body no-JSON, un array o una página de error servida con 200 se descartan AQUÍ, antes de
# planificar, descargar o sellar nada.
NEWHASH="$(python3 -c '
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print((d.get("manifest_hash") or "") if isinstance(d,dict) else "")
except Exception:
    print("")
' "$WORK/manifest.json" 2>/dev/null)"
[ -n "$NEWHASH" ] || exit 0

# Plan: gobernadas.json (todas las entradas válidas, para el lock), plan.tsv (las que cambiaron:
# "path<TAB>sha256") y skipped.txt (lo rechazado). Las rutas se validan ANTES de tocar disco.
python3 -c "$_RUNTIME_CONTEXT_PATH_OK_PY"'
import json,sys,os
man_p,lock_p,work,prefijos=sys.argv[1],sys.argv[2],sys.argv[3],tuple(sys.argv[4].split())
try:
    man=json.load(open(man_p))
except Exception:
    sys.exit(0)
try:
    lock=json.load(open(lock_p))
except Exception:
    lock={}
have={}
for f in (lock.get("files") or []):
    if isinstance(f,dict) and f.get("path"):
        have[f["path"]]=f.get("sha256")
entradas=man.get("asset_versions")
if not isinstance(entradas,list):
    entradas=man.get("files") if isinstance(man.get("files"),list) else []
gob,plan,skipped=[],[],[]
for f in entradas:
    if not isinstance(f,dict):
        continue
    path=f.get("path") or ""
    sha=f.get("sha256") or ""
    if not sha or not ruta_gobernada(path, prefijos):
        skipped.append((path if isinstance(path,str) else "") .replace("\x00","\\0") or "(sin ruta)")
        continue
    gob.append({"path":path,"sha256":sha,"type_key":f.get("type_key"),"version":f.get("version")})
    if have.get(path) != sha:
        plan.append(path+"\t"+sha)
json.dump(gob,open(os.path.join(work,"gobernadas.json"),"w"),ensure_ascii=False)
with open(os.path.join(work,"plan.tsv"),"w") as out:
    for l in plan: out.write(l+"\n")
with open(os.path.join(work,"skipped.txt"),"w") as out:
    for s in skipped: out.write(s+"\n")
' "$WORK/manifest.json" "$(runtime_lock_path)" "$WORK" "$CS_PREFIJOS" 2>/dev/null
# Si el plan no se generó (python falló), no se sella nada: el lock mentiría.
[ -f "$WORK/gobernadas.json" ] || exit 0
[ -f "$WORK/plan.tsv" ] || : > "$WORK/plan.tsv"

applied=0
planned=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  planned=$((planned + 1))
  # Campos separados por TAB, partidos con `cut` (tabulador por defecto): un tabulador literal
  # dentro de ${…%%…} es invisible y un editor que lo convierta en espacios rompería el parseo.
  rel="$(printf '%s' "$line" | cut -f1)"
  sha="$(printf '%s' "$line" | cut -f2)"
  qp="$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$rel" 2>/dev/null)"
  qs="$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$sha" 2>/dev/null)"
  [ -n "$qp" ] && [ -n "$qs" ] || continue
  body="$(runtime_get "/context/files?path=$qp&sha256=$qs")"
  [ "$(runtime_http_status)" = "200" ] || continue
  printf '%s' "$body" > "$WORK/blob.json"
  if python3 - "$WORK/blob.json" "$CTXDIR" "$rel" <<'PY' 2>/dev/null
import json,sys,os,tempfile
blob_path,base,rel=sys.argv[1],sys.argv[2],sys.argv[3]
os.makedirs(base,exist_ok=True)
dest=os.path.join(base,rel)
# Contención FÍSICA: un symlink dentro del directorio de contexto (p. ej. hub-context/docs -> el
# docs/ del proyecto) no debe dejar escribir fuera de él.
raiz=os.path.realpath(base)
if not os.path.realpath(dest).startswith(raiz+os.sep):
    sys.exit(1)
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
    os.replace(tmp,dest)   # sustitución atómica
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    sys.exit(1)
PY
  then
    applied=$((applied + 1))
  fi
done < "$WORK/plan.tsv"

if [ "$applied" -lt "$planned" ]; then
  # Convergencia parcial: NO se sella el hash nuevo (el lock mentiría sobre lo que hay en
  # disco). La próxima sesión, o el próximo claim, reintenta solo lo que falta.
  echo "⚠ contexto: $applied/$planned archivo(s) sincronizados; el lock sigue en '${CURRENT:-vacío}'. Se reintenta en la próxima sesión." >&2
  exit 0
fi

runtime_lock_write "$NEWHASH" "$(cat "$WORK/gobernadas.json")" || exit 0

# Señal de sincronización (la única sin slice_id: corre antes del claim). 422 = manifiesto
# desconocido para el hub -> no se reintenta ni se encola.
SYNCED="$(python3 - "$WORK/plan.tsv" "$WORK/gobernadas.json" "$CTXDIR" "$CURRENT" "$NEWHASH" <<'PY' 2>/dev/null
import json,sys,os,hashlib
plan_p,gob_p,base,cur,new=sys.argv[1:6]
cambiados=[l.split("\t")[0] for l in open(plan_p).read().splitlines() if l]
local={}
for f in json.load(open(gob_p)):
    try:
        with open(os.path.join(base,f["path"]),"rb") as fh:
            local[f["path"]]=hashlib.sha256(fh.read()).hexdigest()
    except Exception:
        pass
print(json.dumps({"from_hash":cur or None,"to_hash":new,"files_changed":cambiados,"local_hashes":local},ensure_ascii=False))
PY
)"
[ -n "$SYNCED" ] || SYNCED="{\"to_hash\":\"$NEWHASH\",\"files_changed\":[]}"
runtime_post "/projects/$PID/context/synced" "$SYNCED" >/dev/null
[ "$(runtime_http_status)" = "422" ] && echo "⚠ el hub no reconoce el manifiesto sincronizado (422): revisa 'trycore-bonita doctor'." >&2

if [ "$applied" -gt 0 ]; then
  echo "⬆ contexto: $applied archivo(s) actualizados (${CURRENT:-sin lock} → $NEWHASH)"
fi
if [ -s "$WORK/skipped.txt" ]; then
  echo "   No aplicados (fuera de context/ y docs/ o ruta inválida): $(tr '\n' ' ' < "$WORK/skipped.txt")"
fi
exit 0
