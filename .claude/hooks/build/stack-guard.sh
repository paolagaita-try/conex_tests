#!/usr/bin/env bash
# stack-guard.sh — PreToolUse · Write/Edit en package.json
# AUTO-ARME: si aún no existe package.json en disco (primer scaffold), no hay
# qué comparar -> exit 0. Una vez existe, bloquea (exit 2) la introducción de
# dependencias fuera de .claude/config/stack-allowlist.json (el contrato de stack del PRD).
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
# [EP-OR-08-B] El allowlist deja de ser un fichero que edita un humano: en dual/runtime lo
# escribe context-sync.sh desde el asset gobernado del runtime. El guard sigue leyéndolo de
# disco (cero red en PreToolUse); solo avisa si el contexto local está sin sincronizar.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"
ALLOW="$ROOT/.claude/config/stack-allowlist.json"
[ -f "$ALLOW" ] || exit 0

INPUT="$(cat)"

# Guarda python3 [H4]: si falta, no podemos verificar las deps. Fail-closed DIRIGIDO:
# solo bloqueamos (exit 2) si la edición toca package.json; si no, exit 0.
if ! command -v python3 >/dev/null 2>&1; then
  if printf '%s' "$INPUT" | grep -q 'package\.json'; then
    echo "⛔ stack-guard: python3 no disponible; no puedo verificar las dependencias de package.json. Instala python3 (trycore-build doctor)." >&2
    exit 2
  fi
  exit 0
fi

# El script va por heredoc (= stdin), así que el JSON del hook se pasa por la
# variable de entorno INPUT, no por stdin.
VIOL="$(ALLOW="$ALLOW" INPUT="$INPUT" python3 <<'PY' 2>/dev/null
import os,sys,json,re,fnmatch
try:
    data=json.loads(os.environ.get("INPUT") or "{}")
except Exception:
    sys.exit(0)
ti=data.get("tool_input",{})
fp=ti.get("file_path") or ti.get("path") or ""
if not fp.endswith("package.json"):
    sys.exit(0)
content=ti.get("content")
new=ti.get("new_string")
old=ti.get("old_string")
# Nada que verificar si la edición no aporta texto.
if not (content and content.strip()) and not (new and new.strip()):
    sys.exit(0)
allow=json.load(open(os.environ["ALLOW"])).get("allow",[])
def ok(name):
    return any(fnmatch.fnmatch(name, pat) for pat in allow)
def extract(pkg):
    deps=set()
    for sec in ("dependencies","devDependencies","peerDependencies","optionalDependencies"):
        deps.update((pkg.get(sec) or {}).keys())
    return deps
# Extracción por clave (version-agnóstica) en tres ramas de prioridad decreciente.
# Las ramas 1 y 2 parsean el documento COMPLETO, así que capturan specs no-semver
# (github:, file:, git+https:, npm:alias) que la regex de la rama 3 dejaba pasar.
deps=set(); extracted=False
# (1) Write con package.json completo en `content`.
if content and content.strip():
    try:
        deps=extract(json.loads(content)); extracted=True
    except Exception:
        pass
# (2) Edit: reconstruir el documento POST-edición leyendo el package.json de disco.
if not extracted and new is not None:
    try:
        with open(fp) as fh: disk=fh.read()
        post = disk.replace(old, new) if old else (new + disk)
        deps=extract(json.loads(post)); extracted=True
    except Exception:
        pass
# (3) Fallback (solo si 1 y 2 fallan): regex semver ACTUAL, sin ampliar.
if not extracted:
    frag = content or new or ""
    for m in re.finditer(r'"((?:@[\w.-]+/)?[\w.-]+)"\s*:\s*"[\^~>=<*\d][^"]*"', frag):
        deps.add(m.group(1))
bad=sorted(d for d in deps if d and not ok(d))
if bad:
    print(" ".join(bad))
PY
)"

if [ -n "$VIOL" ]; then
  echo "⛔ stack-guard: dependencias fuera del stack declarado del PRD (allowlist): $VIOL" >&2
  echo "   Si es intencional, actualiza .claude/config/stack-allowlist.json y deja nota en GOVERNANCE.md," >&2
  echo "   o consulta al agente stack-guardian. Allowlist: .claude/config/stack-allowlist.json" >&2
  if [ "$(runtime_mode)" != "legacy" ] && projection_is_stale; then
    echo "   ⚠ Contexto local sin sincronizar (stale): el allowlist puede estar desactualizado respecto al runtime." >&2
  fi
  exit 2
fi
exit 0
