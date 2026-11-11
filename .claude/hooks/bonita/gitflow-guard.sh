#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/gitflow-guard.sh
# gitflow-guard.sh — PreToolUse · Bash
# Enforce GitHub Flow estricto:
#   - Prohíbe `git commit` directo en las ramas protegidas.
#   - Prohíbe `git push` que apunte a una rama protegida (la integración va por PR).
#   - Exige trabajar en una rama con prefijo declarado para commitear.
# [EP-OR-08-B] Correcciones:
#   1. La rama se resuelve en el repo del COMANDO (`git -C <dir>`, `cd <dir> && git …`),
#      no en el de la sesión: en sesiones multi-repo el guard evaluaba el repo equivocado
#      (spec §9). Sin pistas en el comando, se cae al repo de la sesión, como antes.
#      El comando se tokeniza en segmentos (por &&, ||, ; y |) y se aplica el efecto
#      ACUMULATIVO de los `cd`: si hay varios `cd` antes del segmento que ejecuta el git,
#      gana el ÚLTIMO (el directorio real en el que corre el commit), no el primero.
#   2. La política (prefijos y ramas protegidas) sale de
#      .claude/config/policy.json (configuración local del proyecto). Sin fichero,
#      los defaults son los del original: feature|fix|chore y main|master.
#   3. Los prefijos/ramas de la política se escapan (re.escape) antes de entrar al patrón
#      grep -E: son texto de un asset editable, no regex de confianza, y un metacaracter
#      (p.ej. un punto) no debe interpretarse como comodín.
#   4. `-C <dir>` solo cuenta como cambio de repo cuando es el flag GLOBAL de git (aparece
#      antes del primer subcomando, p.ej. `git -C <dir> commit`). `git commit -C <ref>`
#      es un flag del subcomando commit (reusa mensaje/autoría de otro commit) y NO cambia
#      de directorio: tratarlo como tal dejaba el commit sin veredicto (bypass).
#   5. [Ronda de arreglo — hermano de destructive-guard.sh] `git` invocado por RUTA ABSOLUTA
#      (`/usr/bin/git commit`) desarmaba el guard ENTERO: las tres detecciones rápidas
#      (línea "sólo nos interesan…", `is_commit`, `is_push`) exigían "git" pegado a un
#      separador de shell o al inicio de la cadena — "/usr/bin/git" tiene "/" delante, no
#      un separador, así que ni entraban al bloque. Se añade `([^[:space:]]*/)?` delante de `git` en
#      los tres patrones: equivalente, a nivel de regex, a comparar por NOMBRE BASE en vez
#      de por igualdad literal. El mismo tratamiento va en `find_git_token` (más abajo):
#      compara por nombre base y el conjunto `WRAPPER_CMDS` suma `command`/`timeout`/
#      `xargs`, igual que en destructive-guard.sh.
# Cero red (PreToolUse). `set -uo pipefail` — nunca `-e`: este hook no puede abortar a
# mitad y dejar pasar un commit sin veredicto.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/config.sh"

INPUT="$(cat)"

# Guarda python3 [H4]: si falta, no podemos parsear el JSON del hook. Fail-closed DIRIGIDO:
# solo bloqueamos (exit 2) si el comando crudo parece un git commit/push; si no, exit 0.
if ! command -v python3 >/dev/null 2>&1; then
  if printf '%s' "$INPUT" | grep -Eq 'git[^"]*(commit|push)'; then
    echo "⛔ gitflow-guard: python3 no disponible; no puedo analizar el comando git. Instala python3 (trycore-bonita doctor)." >&2
    exit 2
  fi
  exit 0
fi

CMD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception:
    print("")')"

# Sólo nos interesan comandos git de escritura. `([^[:space:]]*/)?` delante de `git` = nombre base:
# `/usr/bin/git` cuenta igual que `git` a secas (ver punto 5 arriba).
if ! printf '%s' "$CMD" | grep -Eq '(^|[;&| ])([^[:space:]]*/)?git[ ]'; then
  exit 0
fi

is_commit=false
is_push=false
printf '%s' "$CMD" | grep -Eq '(^|[;&| ])([^[:space:]]*/)?git[ ]+(.*[ ])?commit([ ]|$)' && is_commit=true
printf '%s' "$CMD" | grep -Eq '(^|[;&| ])([^[:space:]]*/)?git[ ]+(.*[ ])?push([ ]|$)'   && is_push=true

if [ "$is_commit" = false ] && [ "$is_push" = false ]; then
  exit 0
fi

# ── Repo del comando ──
# Tokeniza el comando en segmentos (por &&, ||, ; y |) y camina en orden: cada `cd`
# actualiza el directorio "vigente" (acumulativo — gana el ÚLTIMO visto); al llegar al
# segmento que invoca el git de escritura, ese directorio vigente es el candidato, salvo
# que el propio segmento traiga `-C <dir>` como flag GLOBAL de git (antes del subcomando),
# que gana por ser más explícito y local a esa invocación.
REPO_DIR="$(CMD="$CMD" python3 - <<'PY' 2>/dev/null
import os,posixpath,re,shlex

cmd = os.environ.get("CMD", "")
# Heurística de partición de shell (no un parser completo): &&, ||, ; y | en ese orden
# de prioridad para que "||" no se rompa en dos "|".
segments = re.split(r'&&|\|\||;|\|', cmd)


def cd_target(seg):
    m = re.match(r'^\s*cd\s+(.+?)\s*$', seg)
    if not m:
        return None
    try:
        toks = shlex.split(m.group(1).strip())
    except Exception:
        toks = [m.group(1).strip().strip("\"'")]
    return toks[0] if toks else None


ENV_ASSIGNMENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
# Envoltorios comunes que anteponen el nombre del binario real sin ser el subcomando de
# git: `env FOO=x git ...`, `sudo git ...`, `command git ...`, `timeout 5 git ...`,
# `xargs git ...`. [Ronda de arreglo — punto 5 arriba, hermano de destructive-guard.sh]
# Mismo conjunto y misma técnica que allí (find_cmd_token): comparación por NOMBRE BASE,
# no por igualdad literal, para que una ruta absoluta (`/usr/bin/git`, `/usr/bin/sudo`) no
# desarme la detección; y el walk salta también las banderas y los argumentos posicionales
# propios del envoltorio (`-u root` de sudo, la duración de `timeout`) hasta el siguiente
# envoltorio conocido o `git` mismo.
WRAPPER_CMDS = {"env", "sudo", "nice", "ionice", "time", "nohup", "command", "timeout", "xargs"}
# Flags GLOBALES de git que toman un argumento en un token SEPARADO: si no se saltan como
# par, el walk trata el valor (p.ej. "user.name=x" de `-c user.name=x`) como si fuera el
# subcomando y para ahí, sin llegar nunca al `-C` real que viene después (bypass).
GIT_GLOBAL_FLAGS_WITH_ARG = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}


def find_git_token(toks):
    """Busca el token `git` por NOMBRE BASE, saltando asignaciones de variables de entorno
    y una cadena de envoltorios conocidos por delante — junto con sus banderas y
    argumentos posicionales (mismo algoritmo que find_cmd_token en destructive-guard.sh).
    Sin esto, `toks[0] != "git"` descartaba el segmento entero y el -C real quedaba sin
    detectar (bypass: cae al repo de sesión)."""
    i, n = 0, len(toks)
    while i < n:
        tok = toks[i]
        if ENV_ASSIGNMENT_RE.match(tok):
            i += 1
            continue
        if posixpath.basename(tok) in WRAPPER_CMDS:
            i += 1
            while i < n and posixpath.basename(toks[i]) != "git" and posixpath.basename(toks[i]) not in WRAPPER_CMDS:
                i += 1
            continue
        break
    return i if i < n and posixpath.basename(toks[i]) == "git" else None


def git_global_dash_c(seg):
    # `-C <dir>` solo cuenta si aparece ANTES del primer subcomando (commit/push/…): ahí
    # es el flag GLOBAL de git. Tras el subcomando es un flag suyo (p.ej. `commit -C <ref>`
    # reusa mensaje/autoría de otro commit) y no debe leerse como cambio de directorio.
    try:
        toks = shlex.split(seg)
    except Exception:
        return None
    gi = find_git_token(toks)
    if gi is None:
        return None
    i = gi + 1
    while i < len(toks):
        t = toks[i]
        if t == "-C" and i + 1 < len(toks):
            return toks[i + 1]
        if t in GIT_GLOBAL_FLAGS_WITH_ARG and i + 1 < len(toks):
            i += 2  # flag GLOBAL con argumento en token separado (p.ej. -c user.name=x):
            continue  # se salta el PAR completo, nunca se lee el valor como subcomando.
        if t.startswith("-"):
            i += 1
            continue
        break  # primer token que no es flag => subcomando; -C posterior no cuenta.
    return None


cur_dir = ""
target = ""
for seg in segments:
    seg = seg.strip()
    if not seg:
        continue
    cdt = cd_target(seg)
    if cdt is not None:
        cur_dir = cdt
        continue
    if re.search(r'(^|\s)(\S*/)?git(\s|$)', seg) and re.search(r'\b(commit|push)\b', seg):
        dashc = git_global_dash_c(seg)
        target = dashc if dashc else cur_dir
        break

print(target)
PY
)"
if [ -n "$REPO_DIR" ]; then
  case "$REPO_DIR" in
    /*) ;;
    *)  REPO_DIR="$(config_root)/$REPO_DIR" ;;
  esac
else
  REPO_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
fi
[ -d "$REPO_DIR" ] || REPO_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

BRANCH="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"

# ── Política (la publicada por el hub, luego la local; defaults del original) ──
# context-sync deja los assets del hub en .claude/hub-context/context/; sin ellos vale .claude/config/
# (config_policy_path, la misma que da la rama de integración del claim).
POLICY="$(config_policy_path)"
POLICY_OUT="$(POLICY="$POLICY" python3 - <<'PY' 2>/dev/null
import json,os,re
try:
    d=json.load(open(os.environ["POLICY"]))
except Exception:
    d={}
if not isinstance(d,dict):
    d={}
pref=[p for p in (d.get("branch_prefixes") or []) if isinstance(p,str)] or ["feature","fix","chore"]
prot=[p for p in (d.get("protected_branches") or []) if isinstance(p,str)] or ["main","master"]
# [EP-OR-08-B] re.escape: los prefijos/ramas vienen de un asset editable (policy.json), no son
# regex de confianza. Sin escapar, un metacaracter (p.ej. un punto en "release.candidate")
# se interpreta como comodín y afloja o rompe el gate silenciosamente.
pref_re="|".join(re.escape(p) for p in pref)
prot_re="|".join(re.escape(p) for p in prot)
print("^(" + pref_re + ")/", "^(" + prot_re + ")$")
PY
)"
case "$POLICY_OUT" in
  *' '*) ;;
  *) POLICY_OUT='^(feature|fix|chore)/ ^(main|master)$' ;;
esac
PREFIX_RE="${POLICY_OUT%% *}"
PROT_RE="${POLICY_OUT##* }"

block() {
  echo "⛔ gitflow-guard (GitHub Flow estricto): $1" >&2
  echo "   Política: ramas protegidas ${PROT_RE} · trabajar en ${PREFIX_RE}* · integrar por PR." >&2
  echo "   Repo evaluado: $REPO_DIR (rama '$BRANCH')." >&2
  exit 2
}

# 1) Commit directo a una rama protegida.
if [ "$is_commit" = true ] && printf '%s' "$BRANCH" | grep -Eq "$PROT_RE"; then
  block "commit directo a '$BRANCH' no permitido. Crea una rama: git switch -c feature/<slug>"
fi

# 2) Commit desde una rama no tipada.
if [ "$is_commit" = true ] && [ -n "$BRANCH" ] && ! printf '%s' "$BRANCH" | grep -Eq "$PREFIX_RE"; then
  block "rama '$BRANCH' no sigue la convención. Usa un prefijo declarado en la política para commitear."
fi

# 3) Push apuntando a una rama protegida.
PROT_ALT="$(printf '%s' "$PROT_RE" | sed -e 's/^\^(//' -e 's/)\$$//')"
if [ "$is_push" = true ] && printf '%s' "$CMD" | grep -Eq "push[^|;&]*[ :]($PROT_ALT)([ ]|$|:)"; then
  block "push directo a una rama protegida no permitido. Abre un Pull Request desde tu rama de trabajo."
fi

exit 0
