#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/lib/harness-meta.sh
# harness-meta.sh — metadatos del arnés instalado (versión y catálogo de asset types).
# Extraído de session-start.sh [#74] para que `slice-ops.sh register` mande
# exactamente el mismo `harness_version` que el registro de arranque de sesión: dos lecturas
# distintas de la misma versión acabarían con un worktree rechazado por
# `incompatible_version` y el clon principal aceptado, o al revés.
# Fail-open, igual que config.sh: nunca lanza; sin fichero devuelve un valor neutro.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# harness_pkg_root — raíz del PAQUETE cuando el cliente corre desde el propio paquete
# (`<pkg>/hooks/lib/`, dos niveles). Instalado en un proyecto (`.claude/hooks/bonita/lib/`) los
# hooks son COPIAS, no enlaces: ahí no hay paquete y la versión sale del manifiesto. Se resuelve
# la cadena de enlaces a mano por si alguien enlaza el fichero (`readlink -f` no es portable al
# BSD readlink de macOS).
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
  (cd "$(dirname "$src")/../.." >/dev/null 2>&1 && pwd -P) 2>/dev/null
}

# harness_version_number — versión instalada en el proyecto (campo `version` del manifiesto
# .claude/.bonita-harness.json); si no, la del paquete (VERSION); si no, "0.0.0".
# [#74] El manifiesto está versionado en el proyecto, pero se mira también el clon principal:
# un worktree recién dado de alta no tiene por qué mentir sobre su versión.
harness_version_number() {
  local f pkg root v
  for root in "$(config_root)" "$(config_candidate_root)" "$(config_main_clone_root)"; do
    [ -n "$root" ] || continue
    f="$root/.claude/.bonita-harness.json"
    [ -f "$f" ] || continue
    v="$(python3 - "$f" <<'PY2' 2>/dev/null
import json,sys
try:
    v=json.load(open(sys.argv[1])).get("version")
    print(v if isinstance(v,str) and v else "")
except Exception:
    print("")
PY2
)"
    [ -n "$v" ] && { echo "$v"; return; }
  done
  pkg="$(harness_pkg_root)"
  if [ -n "$pkg" ] && [ -f "$pkg/VERSION" ] && [ -f "$pkg/hooks/slice-ops.sh" ]; then
    tr -d ' \n' < "$pkg/VERSION"
    return
  fi
  echo "0.0.0"
}

# harness_version — lo que viaja en `POST /agents/register` (`harness_version`): el nombre del
# arnés y su versión, `trycore-bonita@<VERSION>`. El hub compara lo que va tras la `@` contra
# `harness_min_version` (0.9.0) y rechaza por debajo (`incompatible_version`). `register` y
# `session-start` usan esta MISMA función: dos lecturas distintas acabarían con un árbol
# aceptado y otro rechazado.
harness_version() {
  echo "trycore-bonita@$(harness_version_number)"
}

# harness_asset_types — el array `types` de asset-types.json (protocolo §6): la copia instalada
# en .claude/ primero y, si se corre desde el paquete, la del paquete. Sin fichero: "[]" — el
# registro sigue funcionando (el hub acepta la lista vacía).
harness_asset_types() {
  local pkg candidates f
  pkg="$(harness_pkg_root)"
  candidates="$(config_root)/.claude/asset-types.json
${pkg:-}/asset-types.json"
  while IFS= read -r f; do
    case "$f" in /asset-types.json|asset-types.json) continue ;; esac
    [ -f "$f" ] || continue
    python3 - "$f" <<'PY2' 2>/dev/null && return
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    t=d.get("types")
    print(json.dumps(t if isinstance(t,list) else [],ensure_ascii=False))
except Exception:
    raise SystemExit(1)
PY2
  done <<EOS
$candidates
EOS
  echo "[]"
}
