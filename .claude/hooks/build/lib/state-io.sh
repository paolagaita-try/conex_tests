#!/usr/bin/env bash
# state-io.sh — helpers compartidos: rutas y patch atómico del estado.
# config_get vive en lib/config.sh [EP-OR-08-A] — se re-exporta sourceándolo aquí para
# que los llamadores existentes sigan funcionando sin cambios.
# Diseño: fail-open. Nunca lanza; ante fallo deja el archivo intacto.

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

state_path() {
  # CLAUDE_PROJECT_DIR es la señal autoritativa que Claude Code fija en los hooks;
  # git rev-parse solo aplica como fallback para invocación manual/dev (sin ese env).
  local root; root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  echo "$root/.claude/state/build-state.json"
}

# state_atomic_patch <state-file> <expr-python-que-muta-`d`>
# Ejecuta la expresión con `d` = dict del estado; escribe atómico solo si válido.
state_atomic_patch() {
  local file="$1" expr="$2"
  [ -f "$file" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  python3 - "$file" "$expr" <<'PY' 2>/dev/null || true
import json,sys,os,tempfile
path,expr=sys.argv[1],sys.argv[2]
try:
    d=json.load(open(path))
    if not isinstance(d,dict): sys.exit(0)
    exec(expr, {}, {"d":d})
    dirn=os.path.dirname(path) or "."
    fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".build-state.",suffix=".tmp")
    try:
        with os.fdopen(fd,"w") as out:
            json.dump(d,out,indent=2,ensure_ascii=False); out.flush(); os.fsync(out.fileno())
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
except Exception:
    pass
PY
}
