#!/usr/bin/env bash
# harness-meta.sh — metadatos del PAQUETE instalado (versión del arnés y catálogo de asset
# types). Extraído de session-start.sh [#74] para que `slice-ops.sh register` mande
# exactamente el mismo `harness_version` que el registro de arranque de sesión: dos lecturas
# distintas de la misma versión acabarían con un worktree rechazado por
# `incompatible_version` y el clon principal aceptado, o al revés.
# Fail-open, igual que config.sh: nunca lanza; sin fichero devuelve un valor neutro.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# harness_pkg_root — raíz del PAQUETE (no del proyecto). Los hooks se instalan como symlinks
# por fichero (linkChildren), así que hay que resolver la cadena de enlaces a mano:
# `readlink -f` no es portable al BSD readlink de macOS. Este fichero vive en
# `<pkg>/hooks/build/lib/`, de ahí los tres niveles.
harness_pkg_root() {
  local src="${BASH_SOURCE[0]}" target i=0
  while [ -L "$src" ] && [ "$i" -lt 10 ]; do
    target="$(readlink "$src" 2>/dev/null)" || break
    case "$target" in
      /*) src="$target" ;;
      *)  src="$(dirname "$src")/$target" ;;
    esac
    i=$((i + 1))
  done
  (cd "$(dirname "$src")/../../.." >/dev/null 2>&1 && pwd -P) 2>/dev/null
}

# harness_version — versión instalada en el consumidor; si no, la del paquete.
# [#74] El marcador `.claude/.build-harness-version` está en .gitignore en modo symlink: NO
# viaja a un `git worktree add`. Por eso se mira también el clon principal antes de caer al
# paquete — un worktree recién dado de alta no tiene por qué mentir sobre su versión.
# Se eliminan también los `\r`: un `VERSION`/marcador con finales de línea CRLF (consumidor
# Windows con `core.autocrlf=true`) dejaría un retorno de carro pegado a la versión, que al
# embeberse en el JSON de `POST /agents/register` es un carácter de control ilegal — el hub
# rechazaría el alta y el catálogo de asset types no se re-publicaría (fallo silencioso).
harness_version() {
  local f pkg root
  for root in "$(config_root)" "$(config_candidate_root)" "$(config_main_clone_root)"; do
    [ -n "$root" ] || continue
    f="$root/.claude/.build-harness-version"
    [ -f "$f" ] && { tr -d ' \r\n' < "$f"; return; }
  done
  pkg="$(harness_pkg_root)"
  if [ -n "$pkg" ] && [ -f "$pkg/VERSION" ]; then
    tr -d ' \r\n' < "$pkg/VERSION"
    return
  fi
  echo "0.0.0"
}

# harness_asset_types — el array `types` de asset-types.json del paquete (protocolo §6).
# Cadena de resolución: plugin > copia en .claude/ (la siembra es del sub-slice D) >
# paquete resuelto por symlink. Sin fichero: "[]" — el registro sigue funcionando.
harness_asset_types() {
  local pkg candidates f
  pkg="$(harness_pkg_root)"
  candidates="${CLAUDE_PLUGIN_ROOT:-}/asset-types.json
$(config_root)/.claude/asset-types.json
${pkg:-}/asset-types.json"
  while IFS= read -r f; do
    case "$f" in /asset-types.json|asset-types.json) continue ;; esac
    [ -f "$f" ] || continue
    python3 - "$f" <<'PY' 2>/dev/null && return
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    t=d.get("types")
    print(json.dumps(t if isinstance(t,list) else [],ensure_ascii=False))
except Exception:
    raise SystemExit(1)
PY
  done <<EOS
$candidates
EOS
  echo "[]"
}
