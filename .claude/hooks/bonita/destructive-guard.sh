#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/destructive-guard.sh
# destructive-guard.sh — PreToolUse · Bash
# Bloquea comandos irreversibles antes de ejecutarse:
#   1. `git push` forzado (--force, -f, --force-with-lease, o refspec con '+').
#   2. `git reset --hard`.
#   3. `git clean` con -f y además -d o -x.
#   4. `rm` con -r y -f combinados (en cualquier orden), salvo que TODAS las rutas
#      caigan bajo el directorio temporal del sistema. El temporal se resuelve como
#      TMPDIR con respaldo a /tmp, y se acepta también /var/folders: en macOS el
#      creador de temporales devuelve una ruta ahí, no bajo /tmp, y un temporal
#      legítimo quedaría bloqueado si solo mirásemos /tmp.
# La regla de confinamiento al directorio del proyecto queda retirada a propósito:
# producía contradicciones con los casos 4 y 10, y habría bloqueado la creación de
# árboles de trabajo hermanos, sobre la que se apoya la identidad por árbol [#74].
# Partimos el comando por subcomandos (separadores de shell y saltos de línea) antes
# de evaluar: basta que UN subcomando encaje con una regla para bloquear el conjunto.
# Cero red (PreToolUse). `set -uo pipefail` — nunca `-e`: este hook no puede abortar
# a mitad y dejar pasar un comando irreversible sin veredicto.
set -uo pipefail

INPUT="$(cat)"

# Guarda python3: si falta, no podemos parsear el JSON ni tokenizar el comando con
# precisión. Fail-closed DIRIGIDO (igual que gitflow-guard): aplicamos los patrones
# sobre la cadena cruda del payload y bloqueamos ante cualquier indicio, en vez de
# dejar pasar sin verificar.
if ! command -v python3 >/dev/null 2>&1; then
  if printf '%s' "$INPUT" | grep -Eq -- '(push[^"]*(--force(-with-lease)?|[ "]-f[ "]|\+[A-Za-z0-9])|reset[^"]*--hard|clean[^"]*-[a-zA-Z]*(fd|df|fx|xf)[a-zA-Z]*|rm[^"]*-[a-zA-Z]*(rf|fr)[a-zA-Z]*)'; then
    echo "⛔ destructive-guard: python3 no disponible; no puedo analizar el comando con precisión. Instala python3 (trycore-bonita doctor)." >&2
    exit 2
  fi
  exit 0
fi

CMD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception:
    print("")')"

[ -n "$CMD" ] || exit 0

TMPDIR_RESOLVED="${TMPDIR:-/tmp}"

REASON="$(CMD="$CMD" TMPDIR_RESOLVED="$TMPDIR_RESOLVED" python3 - <<'PY' 2>/dev/null
import os, posixpath, re, shlex

CMD = os.environ.get("CMD", "")
TMPDIR_RESOLVED = os.environ.get("TMPDIR_RESOLVED", "/tmp").rstrip("/")

# Candidatos de temporal: TMPDIR (con respaldo /tmp), y los físicos habituales en
# macOS/Linux. Un rm -rf bajo cualquiera de estos cuenta como excepción de la regla 4.
# Normalizados con normpath: los propios candidatos no deberían traer '..', pero es
# gratis mantenerlos en la misma forma que las rutas con las que se comparan.
TMP_CANDIDATES = [posixpath.normpath(c) for c in {TMPDIR_RESOLVED, "/tmp", "/private/tmp", "/var/folders", "/private/var/folders"} if c]


def is_under_tmp(path):
    if not path.startswith("/"):
        return False
    # [Ronda de arreglo — recorrido de directorio] Sin normalizar, una ruta que EMPIEZA
    # bajo el temporal pero sale con '..' hacia un directorio del sistema (uno o varios
    # saltos, p.ej. desde el temporal de macOS bajo /var/folders) pasaba el prefijo sin
    # bloquear. normpath resuelve los segmentos de subida ANTES de comparar — la
    # comparación de prefijo corre sobre la ruta ya resuelta, nunca sobre la cruda.
    resolved = posixpath.normpath(path)
    for c in TMP_CANDIDATES:
        if resolved == c or resolved.startswith(c + "/"):
            return True
    return False


# [Ronda de arreglo — CRÍTICO 1: tercera vía de escape] La ronda anterior cerró los
# envoltorios con un conjunto fijo (env, sudo, nice, ionice, time, nohup) exigiendo
# IGUALDAD LITERAL entre el token y el nombre del comando. Dos huecos quedaban abiertos:
# (a) faltaban envoltorios de uso real — `command` (fuerza el binario, ignora funciones o
# alias), `timeout` (el que se usa en la práctica para acotar un mandato; `time` solo
# mide) y `xargs`; y (b) una ruta absoluta (`/bin/rm`, `/usr/bin/git`) o las banderas y
# argumentos propios del envoltorio (`sudo -u root rm`, `timeout 5 rm`) desarmaban la
# detección: ni el token completo coincidía con el nombre pelado, ni el bucle sabía saltar
# nada que no fuera una asignación o un envoltorio EXACTO. find_cmd_token ahora compara
# por NOMBRE BASE (posixpath.basename) — no por igualdad literal — y, tras reconocer un
# envoltorio, avanza sobre lo que venga a continuación (banderas y argumentos posicionales
# del propio envoltorio) hasta el siguiente envoltorio conocido o el comando buscado. Las
# reglas 1-3 comprueban pertenencia sobre TODA la lista de tokens (no exigen que `git` sea
# el primero), así que les basta comparar por nombre base (vía `bnames`, más abajo) para
# cerrar también la invocación de `git` por ruta absoluta — no necesitan el salto de
# envoltorio.
WRAPPER_CMDS = {"env", "sudo", "nice", "ionice", "time", "nohup", "command", "timeout", "xargs"}
ENV_ASSIGNMENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')


def find_cmd_token(toks, name):
    """Busca `name` (p.ej. "rm") por NOMBRE BASE, saltando asignaciones de variables de
    entorno y una cadena de envoltorios conocidos por delante — junto con las banderas y
    los argumentos posicionales propios de esos envoltorios (`-u root` de sudo, la
    duración de `timeout`, ...). No distinguimos bandera de argumento posicional: basta
    con seguir avanzando hasta toparnos con OTRO envoltorio conocido o con `name` mismo;
    fail-safe hacia bloquear de más antes que dejar pasar un envoltorio no previsto."""
    i, n = 0, len(toks)
    while i < n:
        tok = toks[i]
        if ENV_ASSIGNMENT_RE.match(tok):
            i += 1
            continue
        if posixpath.basename(tok) in WRAPPER_CMDS:
            i += 1
            while i < n and posixpath.basename(toks[i]) != name and posixpath.basename(toks[i]) not in WRAPPER_CMDS:
                i += 1
            continue
        break
    return i if i < n and posixpath.basename(toks[i]) == name else None


def flags_of(tokens):
    """Concatena las flags cortas combinadas vistas en una lista de tokens (sin '-')."""
    combined = ""
    for t in tokens:
        if t.startswith("-") and not t.startswith("--"):
            combined += t[1:]
    return combined


segments = re.split(r'&&|\|\||;|\||\n', CMD)
reason = ""

# [Ronda de arreglo — IMPORTANTE 3] Fail-safe dirigido también ante lo imprevisto: antes
# solo el troceo por segmento (shlex.split) tenía su propio try/except; una excepción no
# prevista en cualquier otro punto de la evaluación se propagaba, `REASON` quedaba vacío
# y el guardia dejaba pasar — justo lo contrario de fail-closed. Envolvemos el bloque
# ENTERO: cualquier fallo inesperado bloquea con motivo, igual que la guarda de python3
# ausente.
try:
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        try:
            toks = shlex.split(seg)
        except Exception:
            toks = seg.split()
        if not toks:
            continue

        # Nombres base de todos los tokens del segmento: las reglas 1-3 comprueban
        # pertenencia sobre TODA la lista (no exigen que `git` sea el primer token), así
        # que comparar por nombre base basta para cerrar también `/usr/bin/git ...` sin
        # necesitar el salto de envoltorio de find_cmd_token.
        bnames = [posixpath.basename(t) for t in toks]

        # Regla 1: git push forzado.
        if "git" in bnames and "push" in bnames:
            rest = toks[bnames.index("push") + 1:]
            forced = False
            for t in rest:
                if t == "--force" or t.startswith("--force=") or t == "--force-with-lease" or t.startswith("--force-with-lease="):
                    forced = True
                    break
                if t == "-f":
                    forced = True
                    break
                if t.startswith("-") and not t.startswith("--") and "f" in t[1:]:
                    forced = True
                    break
                if t.startswith("+") and t != "+":
                    forced = True
                    break
            if forced:
                reason = "git push forzado (--force / -f / --force-with-lease / refspec '+') no permitido: reescribe historia remota. Abre un PR."
                break

        # Regla 2: git reset --hard.
        if "git" in bnames and "reset" in bnames and "--hard" in bnames:
            reason = "git reset --hard no permitido: descarta cambios locales de forma irreversible."
            break

        # Regla 3: git clean -f y además -d o -x.
        if "git" in bnames and "clean" in bnames:
            rest = toks[bnames.index("clean") + 1:]
            combined = flags_of(rest)
            has_f = "f" in combined or "--force" in rest
            has_d = "d" in combined
            has_x = "x" in combined
            if has_f and (has_d or has_x):
                reason = "git clean -f con -d o -x no permitido: borra ficheros y directorios no versionados sin posibilidad de deshacer."
                break

        # Regla 4: rm -r -f combinados, salvo que todas las rutas caigan bajo el temporal.
        rm_idx = find_cmd_token(toks, "rm")
        if rm_idx is not None:
            rest = toks[rm_idx + 1:]
            combined = flags_of(rest)
            has_r = "r" in combined or "R" in combined or "--recursive" in rest
            has_f = "f" in combined or "--force" in rest
            if has_r and has_f:
                paths = [t for t in rest if not t.startswith("-")]
                if not paths or not all(is_under_tmp(p) for p in paths):
                    reason = "rm -rf no permitido fuera del directorio temporal del sistema: borrado recursivo irreversible."
                    break
except Exception as e:
    reason = f"fallo inesperado analizando el comando ({e!r}); bloqueado por fail-safe."

print(reason)
PY
)"

if [ -n "$REASON" ]; then
  echo "⛔ destructive-guard: $REASON" >&2
  exit 2
fi

exit 0
