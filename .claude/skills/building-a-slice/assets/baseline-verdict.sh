#!/usr/bin/env bash
# baseline-verdict.sh — veredicto de baseline cacheado por sha (skill building-a-slice).
#
# Responde «¿rompí algo?» en proyectos con tests rojos «ambientales» heredados SIN pagar
# el ritual de worktree + suite ×2 en cada medición: cachea el conjunto de ficheros rojos
# del baseline (origin/<destino>) en un JSON versionable por sha, y la medición de
# regresión pasa a ser UNA corrida de la suite del working tree + comparación estilo comm.
#
# Uso:
#   baseline-verdict.sh capture <ref>   # captura el veredicto del baseline en un worktree temporal
#   baseline-verdict.sh compare <ref>   # corre la suite actual 1 vez y compara contra el cache
#
# <ref> DEBE ser un ref remoto (`origin/<rama>`) o un sha verificado como remoto
# (`git branch -r --contains <sha>` no vacío). Los refs locales se RECHAZAN: comparar
# contra un ref local obsoleto ya produjo una medición falsa (issue #30 del arnés).
#
# Parametrización (env), agnóstica del runner de tests:
#   BASELINE_SUITE_CMD   comando de la suite (default: `npm test`; con vitest, p.ej.
#                        `npx vitest run`). Puede salir ≠0 — los rojos son el dato, no un error.
#   BASELINE_RED_FILTER  pipeline shell que lee la salida de la suite por stdin y emite un
#                        fichero rojo por línea. Default (formato `FAIL <fichero> …`, como el
#                        reporter de vitest): grep '^\s*FAIL\s' | awk '{print $2}' | sort -u
#   BASELINE_DIR         dónde viven los JSON (default: `.baseline/` en la raíz del repo).
#   BASELINE_LINK_DIRS   dirs a symlinkear de la raíz al worktree temporal en `capture`
#                        (default: `node_modules`; separa con espacios; vacío = ninguno).
#   BASELINE_NO_FETCH=1  no hacer `git fetch origin` antes de resolver el ref.
#
# Salidas: 0 sin regresiones · 1 regresiones nuevas · 2 uso/guard de ref · 3 cache
# inválido o inexistente (re-captura) · 4 error de entorno (git/worktree/suite ilocalizable).
set -uo pipefail

SUITE_CMD="${BASELINE_SUITE_CMD:-npm test}"
RED_FILTER="${BASELINE_RED_FILTER:-grep -E '^[[:space:]]*FAIL([[:space:]]|\$)' | awk '{print \$2}' | sort -u}"
LINK_DIRS="${BASELINE_LINK_DIRS-node_modules}"

usage() {
  sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'
}

err() { echo "✗ $*" >&2; }
info() { echo "▶ $*"; }

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { err "no estamos dentro de un repo git"; exit 4; }
cd "$ROOT" || exit 4
BASE_DIR="${BASELINE_DIR:-$ROOT/.baseline}"

CMD="${1:-}"; REF="${2:-}"
case "$CMD" in
  capture|compare) : ;;
  -h|--help|help|"") usage; exit 2 ;;
  *) err "subcomando desconocido: $CMD"; usage; exit 2 ;;
esac
[ -n "$REF" ] || { err "falta <ref> (p.ej. origin/main)"; exit 2; }

# ── Guard de ref remoto ──────────────────────────────────────────────────────
# Acepta SOLO `origin/...` o un sha contenido en alguna rama remota. Nunca refs
# locales: `main` local puede estar detrás de `origin/main` y la medición sale falsa.
if [ "${BASELINE_NO_FETCH:-0}" != 1 ]; then
  git fetch --quiet origin 2>/dev/null || info "aviso: git fetch origin falló; sigo con los refs remotos ya conocidos"
fi

SHA=""
if [[ "$REF" == origin/* ]]; then
  SHA="$(git rev-parse --verify --quiet "refs/remotes/${REF}^{commit}")" \
    || { err "el ref remoto '$REF' no existe (¿git fetch origin?)"; exit 2; }
elif [[ "$REF" =~ ^[0-9a-f]{7,40}$ ]]; then
  SHA="$(git rev-parse --verify --quiet "${REF}^{commit}")" \
    || { err "el sha '$REF' no existe en este repo"; exit 2; }
  if [ -z "$(git branch -r --contains "$SHA" 2>/dev/null)" ]; then
    err "el sha '$REF' no está contenido en ninguna rama remota (git branch -r --contains vacío)."
    err "GUARD: la comparación es SIEMPRE contra origin/<destino>, nunca contra un ref local"
    err "(este error ya ocurrió y costó una medición falsa). Usa origin/<rama> o un sha ya pusheado."
    exit 2
  fi
else
  err "ref local rechazado: '$REF'."
  err "GUARD: la comparación es SIEMPRE contra origin/<destino>, nunca contra un ref local"
  err "(este error ya ocurrió y costó una medición falsa). Usa origin/<rama> o un sha remoto."
  exit 2
fi

CACHE_FILE="$BASE_DIR/baseline-verdict.${SHA}.json"

# ── Suite → conjunto ordenado de ficheros rojos ──────────────────────────────
# Corre BASELINE_SUITE_CMD en $1 (dir), deja los rojos (uno por línea, sort -u) en $2.
run_suite_red_files() {
  local dir="$1" out="$2" raw
  raw="$(mktemp)"
  info "corriendo suite en $dir: $SUITE_CMD"
  ( cd "$dir" && bash -c "$SUITE_CMD" ) >"$raw" 2>&1
  local rc=$?
  [ $rc -ne 0 ] && info "la suite salió con rc=$rc (esperable con rojos heredados)"
  bash -c "$RED_FILTER" <"$raw" | LC_ALL=C sort -u >"$out"
  rm -f "$raw"
}

# ─────────────────────────────────────────────────────────────────────────────
if [ "$CMD" = capture ]; then
  WT="$(mktemp -d)/baseline-wt"
  cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1; rm -rf "$(dirname "$WT")"; }
  trap cleanup EXIT
  git worktree add --quiet --detach "$WT" "$SHA" || { err "no pude crear el worktree temporal de $SHA"; exit 4; }
  for d in $LINK_DIRS; do
    [ -e "$ROOT/$d" ] && [ ! -e "$WT/$d" ] && ln -s "$ROOT/$d" "$WT/$d"
  done

  REDS="$(mktemp)"
  run_suite_red_files "$WT" "$REDS"

  mkdir -p "$BASE_DIR"
  CAPTURED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" SHA="$SHA" REF="$REF" \
  SUITE_CMD="$SUITE_CMD" RED_FILTER="$RED_FILTER" CACHE_FILE="$CACHE_FILE" \
  python3 - "$REDS" <<'PY'
import json, os, sys
red = [l.rstrip("\n") for l in open(sys.argv[1]) if l.strip()]
doc = {
    "sha": os.environ["SHA"],
    "ref": os.environ["REF"],
    "captured_at": os.environ["CAPTURED_AT"],
    "suite_cmd": os.environ["SUITE_CMD"],
    "red_filter": os.environ["RED_FILTER"],
    "red_files": sorted(red),
}
with open(os.environ["CACHE_FILE"], "w") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
  [ $? -eq 0 ] || { err "no pude escribir el JSON del veredicto"; exit 4; }
  N="$(grep -c . "$REDS" || true)"
  rm -f "$REDS"
  info "baseline capturado: $N fichero(s) rojo(s) en $REF @ $SHA"
  info "veredicto: $CACHE_FILE (versiónalo en git si quieres compartirlo)"
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# compare
if [ ! -f "$CACHE_FILE" ]; then
  err "no hay veredicto cacheado para $REF @ $SHA — el sha remoto cambió o nunca se capturó."
  OLD="$(ls "$BASE_DIR"/baseline-verdict.*.json 2>/dev/null | head -3)"
  [ -n "$OLD" ] && err "caches existentes (obsoletos para este sha): $(echo "$OLD" | tr '\n' ' ')"
  err "re-captura con: bash ${0##*/} capture $REF"
  exit 3
fi

BASE_REDS="$(mktemp)"; CUR_REDS="$(mktemp)"
trap 'rm -f "$BASE_REDS" "$CUR_REDS"' EXIT
python3 -c 'import json,sys; [print(f) for f in json.load(open(sys.argv[1]))["red_files"]]' \
  "$CACHE_FILE" | LC_ALL=C sort -u >"$BASE_REDS" \
  || { err "el cache $CACHE_FILE no es un veredicto válido; re-captura"; exit 3; }

run_suite_red_files "$ROOT" "$CUR_REDS"

NEW="$(LC_ALL=C comm -13 "$BASE_REDS" "$CUR_REDS")"   # rojo ahora, no estaba: REGRESIÓN
FIXED="$(LC_ALL=C comm -23 "$BASE_REDS" "$CUR_REDS")" # estaba rojo, ya no: arreglado
SAME="$(LC_ALL=C comm -12 "$BASE_REDS" "$CUR_REDS")"  # rojo en ambos: heredado sin cambio

count() { [ -n "$1" ] && printf '%s\n' "$1" | grep -c . || echo 0; }
echo ""
echo "── veredicto vs $REF @ $SHA (capturado $(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["captured_at"])' "$CACHE_FILE")) ──"
echo "  regresiones nuevas : $(count "$NEW")"
[ -n "$NEW" ] && printf '%s\n' "$NEW" | sed 's/^/    ✗ /'
echo "  arreglados         : $(count "$FIXED")"
[ -n "$FIXED" ] && printf '%s\n' "$FIXED" | sed 's/^/    ✓ /'
echo "  heredados sin cambio: $(count "$SAME")"

if [ -n "$NEW" ]; then
  err "hay regresiones nuevas respecto del baseline $REF"
  exit 1
fi
info "sin regresiones nuevas respecto del baseline $REF"
exit 0
