#!/usr/bin/env bash
# config.sh — helpers de lectura de config/build-config.json. Extraído de state-io.sh
# [EP-OR-08-A] para que sea infraestructura común a legacy/dual/runtime: retirar
# state-io.sh en modo runtime puro no debe romper context-monitor, que solo necesita
# config_get. Diseño: fail-open, igual que state-io.sh — nunca lanza.

# config_root — raíz del proyecto consumidor (misma señal que state_path en state-io.sh).
#
# Worktrees: el estado del arnés (runtime.credentials, runtime-projection.json,
# outbox/, build-state.json) está en .gitignore — es secreto y working state, no
# se versiona — así que NO viaja a un `git worktree add`. Resolviendo la raíz solo
# por el toplevel, todo agente que arranque en un worktree se queda sin
# credenciales y opera HUÉRFANO: sin identidad de proyecto, sin lease, sin
# reportar al hub, y con los guards inhibidos porque su fail-open de auto-arme no
# distingue "este proyecto no usa el arnés" de "no veo el estado desde aquí".
# Por eso, cuando el árbol actual no tiene estado, se cae al clon principal
# (--git-common-dir), que es donde vive de verdad. Idempotente para un clon
# normal: si el candidato ya tiene estado, se devuelve tal cual.
#
# [#74] Ese fallback vale para LEER, nunca para ESCRIBIR: quien vaya a transicionar algo
# tiene que preguntar antes por `config_is_inherited_root` (más abajo) y abortar, o estará
# operando con la identidad del clon principal sin saberlo.
config_root() {
  local candidate
  candidate="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  [ -f "$candidate/.claude/state/runtime.credentials" ] && { echo "$candidate"; return; }

  local main
  main="$(config_main_clone_root)"
  if [ -n "$main" ] && [ -f "$main/.claude/state/runtime.credentials" ]; then
    echo "$main"; return
  fi
  echo "$candidate"
}

# ── Identidad por árbol de trabajo [#74] ─────────────────────────────────────────────
# El fallback de config_root es deliberado para LEER (un worktree sin estado propio sigue
# viendo el contexto del proyecto), pero es veneno para ESCRIBIR: un worktree sin
# credenciales propias impersona en silencio al agente del clon principal — reclama con su
# `agent_key`, reporta los hashes de SU árbol (no del propio), comparte su heartbeat y, al
# registrarse, le pisaría el fichero de credenciales. Estos tres helpers son la señal que
# permite a las operaciones de escritura fallar rápido en vez de suplantar.

# _config_phys <ruta> — forma FÍSICA de una ruta (resuelve symlinks). En macOS /var es un
# symlink a /private/var: comparar rutas sin normalizar mide cómo se escribió el path, no a
# qué apunta. Ante una ruta inaccesible devuelve la entrada tal cual — nunca lanza.
_config_phys() {
  (cd "$1" 2>/dev/null && pwd -P) || printf '%s\n' "$1"
}

# config_candidate_root — la raíz que corresponde a ESTE árbol de trabajo, SIN fallback:
# `CLAUDE_PROJECT_DIR` o el toplevel del árbol actual. Es el otro extremo de la comparación
# de identidad (config_root es «de quién es el estado que voy a usar»; esto es «dónde estoy»).
config_candidate_root() {
  local candidate
  candidate="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  _config_phys "$candidate"
}

# config_main_clone_root — raíz del clon principal según `--git-common-dir` ("" si no hay
# git). En un clon normal coincide con el propio árbol; en un worktree apunta al clon que lo
# creó. Es la única forma de leer la identidad del principal sin depender de config_root
# (que es justo lo que puede estar heredado).
config_main_clone_root() {
  local candidate common main
  candidate="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  common="$(git -C "$candidate" rev-parse --git-common-dir 2>/dev/null)" || common=""
  [ -n "$common" ] || { echo ""; return; }
  case "$common" in /*) ;; *) common="$candidate/$common" ;; esac
  main="$(cd "$common/.." 2>/dev/null && pwd -P)" || main=""
  echo "$main"
}

# config_is_inherited_root — rc 0 si el estado que se va a usar NO es el de este árbol, es
# decir: config_root cayó al clon principal. rc 1 en un clon normal, en un worktree ya
# registrado y en un proyecto sin arnés (donde no hay identidad que heredar).
config_is_inherited_root() {
  local here there
  here="$(config_candidate_root)"
  there="$(_config_phys "$(config_root)")"
  [ -n "$here" ] && [ -n "$there" ] && [ "$here" != "$there" ]
}

# config_get <clave.punteada> <default>
config_get() {
  local key="$1" def="$2" file
  file="${BUILD_CONFIG_FILE:-$(config_root)/.claude/config/build-config.json}"
  command -v python3 >/dev/null 2>&1 || { echo "$def"; return; }
  python3 - "$file" "$key" "$def" <<'PY' 2>/dev/null || echo "$def"
import json,sys
file,key,default=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(file))
    for part in key.split("."): d=d[part]
    print(d if not isinstance(d,bool) else str(d).lower())
except Exception:
    print(default)
PY
}
