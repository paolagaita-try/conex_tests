#!/usr/bin/env python3
"""guard_generados — decide si una escritura toca algo generado o instalado por el arnés.

Entrada: JSON del hook de Claude Code por stdin. Salida: si deniega, el JSON de PreToolUse con
`permissionDecision: deny` por stdout (exit 0); si permite, nada. Una entrada ilegible deja pasar con aviso por stderr.
Protegido: (a) los ficheros de `build/generados.json`; (b) lo que hay bajo `tools/arnes/`, `tools/arnes.sh`, el
manifiesto `.claude/.bonita-harness.json` y cada ruta que el manifiesto lista. (c) En modo «proyecto existente»
(`.trycore-bonita.json` con `modo: "existente"`): los ficheros de la línea base y su copia, la propia línea base, el
mapa (`docs/07-bonita/existente/`) y el registro de confirmación, con un mensaje que dice la vía correcta; y los
`.proc`/`.conf` de versiones superiores, que son generados. Por Bash, además, ningún comando invoca `cambios confirmar`
ni toca `cambios-confirmados.md` salvo para leerlo (la confirmación es de una persona en su propia terminal; protección
de buena fe, no infalible). Las aplicaciones y semillas del proyecto que `generar` no escribió no son generadas. Si la
configuración existe pero no se puede leer, no se desprotege: con línea base legible se siguen vigilando sus ficheros. Las rutas se normalizan contra CLAUDE_PROJECT_DIR;
lo que cae fuera del proyecto no se juzga.
"""
import json
import os
import posixpath
import re
import sys
from pathlib import Path

MSG_GENERADO = ("es generado: cambia `docs/07-bonita/` o `docs/08-construccion/` y corre "
                "`tools/arnes.sh generar`")
MSG_ARNES = "lo instala el arnés: usa `/bonita:reflect` o cambia el arnés"
MSG_EXISTENTE = ("es de lo existente (línea base): no se edita a mano; documenta el cambio en "
                 "`docs/07-bonita/cambios.md`, pide a una persona que lo confirme con `tools/arnes.sh cambios confirmar` "
                 "y corre `tools/arnes.sh generar`")
MSG_LINEA_BASE = ("lo mantiene el arnés: la línea base se crea al adoptar y se actualiza con "
                  "`tools/arnes.sh linea-base actualizar --micro-work <id>`")
MSG_MAPA = "es el mapa de lo existente, de solo lectura: se regenera con `tools/arnes.sh mapa`"
MSG_CONFIRMADOS = ("el registro de confirmación solo lo escribe una persona: que ejecute `tools/arnes.sh cambios "
                   "confirmar` en su propia terminal")
MSG_HITL = ("la confirmación la responde una persona en su propia terminal, fuera de esta sesión: el agente no ejecuta "
            "`cambios confirmar` ni toca `cambios-confirmados.md` (solo lo lee); pídeselo a la persona")
CONFIG = ".trycore-bonita.json"
LINEA_BASE = ".trycore-bonita-linea-base.json"
COPIA = ".trycore-bonita-linea-base"
MAPA = "docs/07-bonita/existente"
CONFIRMADOS = "docs/08-construccion/cambios-confirmados.md"
MANIFIESTO = ".claude/.bonita-harness.json"
PASAN = ("tools/arnes.sh", "trycore-bonita", "git")
OPS_ESCRITURA = {"tee", "cp", "mv", "rm", "truncate", "install", "ln"}
# Lo único que puede mencionar `cambios-confirmados.md` en modo existente: leerlo.
SOLO_LECTURA = {"cat", "head", "tail", "less", "grep", "rg", "wc"}
GIT_SOLO_LECTURA = {"diff", "log", "show", "status"}
_CONFIRMAR = re.compile(r"\bcambios\s+confirmar\b")
HERE = os.path.dirname(os.path.abspath(__file__))


def _cargar_es_generado(raiz):
    """`generadores.generados.es_generado` del arnés del proyecto (tools/arnes) o, en el repo del paquete, del propio
    paquete; None si no se encuentra (entonces solo valen las rutas de generados.json)."""
    for base in (os.path.join(raiz, "tools", "arnes"), os.path.normpath(os.path.join(HERE, "..", ".."))):
        if os.path.isfile(os.path.join(base, "generadores", "generados.py")):
            sys.path.insert(0, base)
            try:
                from generadores.generados import es_generado
                return es_generado
            except Exception:
                pass
            finally:
                sys.path.remove(base)
    return None


def _json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


class Proyecto:
    def __init__(self, raiz):
        self.raiz = os.path.realpath(raiz)
        self._ruta_proyecto = Path(self.raiz)
        g = _json(os.path.join(self.raiz, "build", "generados.json"))
        lista = g.get("generados") if isinstance(g, dict) else None
        self.generados = {posixpath.normpath(r) for r in lista if isinstance(r, str)} if isinstance(lista, list) else set()
        # generados.json solo lista .proc y .conf; `generar` reescribe más (BDM, organización, perfiles, journey...):
        # la lista completa la da generadores.generados, y solo cuenta en un proyecto que ya generó.
        self.es_generado = _cargar_es_generado(self.raiz) if isinstance(g, dict) else None
        if isinstance(g, dict) and self.es_generado is None:
            print("guard-generados: no encuentro generadores/generados.py; solo vigilo lo de build/generados.json", file=sys.stderr)
        # Modo existente: la configuración dice `existente`, o existe pero no se lee (no desprotege) y hay línea base.
        ruta_config = os.path.join(self.raiz, CONFIG)
        linea = _json(os.path.join(self.raiz, LINEA_BASE))
        ficheros = linea.get("ficheros") if isinstance(linea, dict) else None
        self.linea_base = ({posixpath.normpath(r) for r in ficheros if isinstance(r, str)}
                           if isinstance(ficheros, dict) else set())
        config = _json(ruta_config)
        if isinstance(config, dict):
            self.existente = config.get("modo") == "existente"
        else:
            self.existente = os.path.exists(ruta_config) and isinstance(linea, dict)
        if self.existente and self.es_generado is None:
            self.es_generado = _cargar_es_generado(self.raiz)
        m = _json(os.path.join(self.raiz, MANIFIESTO))
        arch = m.get("archivos") if isinstance(m, dict) else None
        self.instalados = {posixpath.normpath(r) for r in arch if isinstance(r, str)} if isinstance(arch, dict) else set()

    def relativa(self, ruta, cwd):
        """Ruta relativa al proyecto (con /) o None si cae fuera."""
        if not ruta:
            return None
        ruta = os.path.expanduser(ruta)
        if not os.path.isabs(ruta):
            ruta = os.path.join(cwd, ruta)
        ruta = os.path.normpath(ruta)
        # realpath del padre existente: resuelve enlaces (/tmp -> /private/tmp) aunque el fichero aún no exista.
        resto, base = [], ruta
        while base and not os.path.exists(base) and base != os.path.dirname(base):
            resto.insert(0, os.path.basename(base))
            base = os.path.dirname(base)
        real = os.path.join(os.path.realpath(base), *resto)
        if real != self.raiz and not real.startswith(self.raiz + os.sep):
            return None
        return os.path.relpath(real, self.raiz).replace(os.sep, "/")

    def _generado(self, rel):
        """`es_generado(rel, proyecto)` (los de la línea base no lo son en modo existente); sin el parámetro
        `proyecto` en un arnés antiguo, solo por la ruta."""
        try:
            return self.es_generado(rel, self._ruta_proyecto)
        except TypeError:
            return self.es_generado(rel)

    def motivo(self, rel):
        if rel is None:
            return None
        if self.existente:
            if rel in self.linea_base or rel == COPIA or rel.startswith(COPIA + "/"):
                return MSG_EXISTENTE if rel in self.linea_base else MSG_LINEA_BASE
            if rel == LINEA_BASE:
                return MSG_LINEA_BASE
            if rel == MAPA or rel.startswith(MAPA + "/"):
                return MSG_MAPA
            if rel == CONFIRMADOS:
                return MSG_CONFIRMADOS
        if rel in self.generados or (self.es_generado is not None and self._generado(rel)):
            return MSG_GENERADO
        if rel == "tools/arnes.sh" or rel.startswith("tools/arnes/") or rel == MANIFIESTO or rel in self.instalados:
            return MSG_ARNES
        return None


def _analizar(cmd):
    """Trocea la línea de shell, con comillas, en segmentos (separados por ; & && | || y saltos de línea).
    Devuelve [(palabras, redirecciones)]: las redirecciones `>`/`>>` (con fd o `&` delante, pegadas o no) salen
    de las palabras y van aparte con su destino."""
    segmentos, palabras, redirs = [], [], []
    buf, hay, i, n = [], False, 0, len(cmd)
    pendiente = False  # la próxima palabra es destino de una redirección

    def palabra():
        nonlocal buf, hay, pendiente
        if hay:
            w = "".join(buf)
            if pendiente:
                redirs.append(w)
                pendiente = False
            else:
                palabras.append(w)
        buf, hay = [], False

    def segmento():
        nonlocal palabras, redirs, pendiente
        palabra()
        pendiente = False
        if palabras or redirs:
            segmentos.append((palabras, redirs))
        palabras, redirs = [], []

    while i < n:
        c = cmd[i]
        if c == "\\" and i + 1 < n:
            buf.append(cmd[i + 1]); hay = True; i += 2
        elif c in "'\"":
            j = cmd.find(c, i + 1)
            while c == '"' and j > 0 and cmd[j - 1] == "\\":
                j = cmd.find(c, j + 1)
            if j < 0:
                j = n
            buf.append(cmd[i + 1:j].replace('\\"', '"') if c == '"' else cmd[i + 1:j]); hay = True; i = j + 1
        elif c in " \t":
            palabra(); i += 1
        elif c in ";\n":
            segmento(); i += 1
        elif c == "|":
            if cmd.startswith("|&", i):
                i += 1
            segmento(); i += 2 if cmd.startswith("||", i) else 1
        elif c == "&":
            if cmd.startswith("&>", i):  # &> y &>>
                palabra(); pendiente = True; i += 3 if cmd.startswith("&>>", i) else 2
            else:
                segmento(); i += 2 if cmd.startswith("&&", i) else 1
        elif c == ">":
            if buf and all(ch.isdigit() for ch in buf) and hay:
                buf, hay = [], False  # el fd (2>)
            else:
                palabra()
            i += 2 if cmd.startswith(">>", i) else 1
            if i < n and cmd[i] == "|":
                i += 1
            if i < n and cmd[i] == "&":  # >&2, >&-: duplica un descriptor, no escribe un fichero
                j = i + 1
                while j < n and (cmd[j].isdigit() or cmd[j] == "-"):
                    j += 1
                i = j
            else:
                pendiente = True
        else:
            buf.append(c); hay = True; i += 1
    segmento()
    return segmentos


def _destinos_comando(toks):
    """Rutas que el comando (sin sus redirecciones) escribiría."""
    toks = list(toks)
    while toks and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0]):
        toks.pop(0)
    if not toks:
        return []
    cmd = posixpath.basename(toks[0])
    while cmd in ("sudo", "command", "env", "nohup", "time") and len(toks) > 1:
        toks = toks[1:]
        while toks and (toks[0].startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[0])):
            toks = toks[1:]
        if not toks:
            return []
        cmd = posixpath.basename(toks[0])
    args = toks[1:]
    pos = [a for a in args if not a.startswith("-")]
    if cmd == "sed" and any(a == "-i" or a.startswith("-i") or (a.startswith("-") and not a.startswith("--") and "i" in a[1:]) or a.startswith("--in-place") for a in args):
        return pos
    if cmd in ("perl", "ruby") and any(a.startswith("-") and "i" in a.lstrip("-") and not a.startswith("--") for a in args):
        return pos
    if cmd in ("cp", "install", "ln") and pos:
        return [pos[-1]]
    if cmd in OPS_ESCRITURA:
        return pos
    return []


def _exento(toks):
    """Comandos del propio arnés o git: lo que ellos escriban es cosa suya (las redirecciones del shell no)."""
    sin_env = [t for t in toks if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t)]
    primero = sin_env[0] if sin_env else ""
    return primero in PASAN or posixpath.basename(primero) in ("trycore-bonita", "git") or primero.endswith("tools/arnes.sh")


def _solo_lectura(toks):
    """¿El segmento solo lee? (`cat`, `head`, `tail`, `less`, `grep`, `rg`, `wc` o `git diff|log|show|status`)."""
    toks = [t for t in toks if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t)]
    if not toks:
        return True
    cmd = posixpath.basename(toks[0])
    if cmd == "git":
        sub = next((t for t in toks[1:] if not t.startswith("-")), "")
        return sub in GIT_SOLO_LECTURA
    return cmd in SOLO_LECTURA


def _confirmacion(cmd, segmentos):
    """En modo existente, la confirmación es de una persona (HITL): se deniega todo comando que invoque `cambios
    confirmar` (por `tools/arnes.sh`, `trycore-bonita`, `python3 -m generadores` o envuelto en otro, p. ej. `script`)
    y todo el que mencione `cambios-confirmados.md` salvo si solo lo lee. Un comando de solo lectura que nombre
    «cambios confirmar» también se deniega (`rg --pre`, p. ej., ejecuta un programa). Es una protección de buena fe, no
    infalible."""
    if not (_CONFIRMAR.search(cmd) or posixpath.basename(CONFIRMADOS) in cmd):
        return None
    if all(_solo_lectura(p) and not _CONFIRMAR.search(" ".join(p)) for p, _ in segmentos):
        return None
    return MSG_HITL


def decidir_bash(proy, cmd, cwd):
    segmentos = _analizar(cmd)
    if proy.existente:
        motivo = _confirmacion(cmd, segmentos)
        if motivo:
            return motivo
    for palabras, redirs in segmentos:
        destinos = list(redirs)
        if not _exento(palabras):
            destinos += _destinos_comando(palabras)
        for d in destinos:
            if d.startswith("/dev/"):
                continue
            motivo = proy.motivo(proy.relativa(d, cwd))
            if motivo:
                return motivo
    return None


def main():
    try:
        datos = json.loads(sys.stdin.read())
        if not isinstance(datos, dict):
            raise ValueError("no es un objeto")
        herramienta = datos.get("tool_name", "")
        entrada = datos.get("tool_input") or {}
        if not isinstance(entrada, dict):
            raise ValueError("tool_input no es un objeto")
    except (ValueError, OSError) as e:
        print(f"guard-generados: entrada ilegible ({e}); dejo pasar", file=sys.stderr)
        return 0
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or os.getcwd()
    cwd = datos.get("cwd") or raiz
    proy = Proyecto(raiz)
    if herramienta == "Bash":
        motivo = decidir_bash(proy, str(entrada.get("command", "")), cwd)
    else:
        ruta = entrada.get("file_path") or entrada.get("notebook_path") or ""
        motivo = proy.motivo(proy.relativa(str(ruta), cwd))
    if motivo:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                  "permissionDecisionReason": motivo}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
