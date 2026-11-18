#!/usr/bin/env python3
"""grafo_unidades.py — plan de unidades (docs/08-construccion/plan.md) -> bundle de grafo del hub.

Origen: trycore-spec-build-harness@062c6fd scripts/lib/graph-bundle.py
(adaptado: la entrada ya no es un JSON de discovery con épicas EP-NNN sino la tabla del plan de unidades Bonita;
el resto del contrato del hub se conserva).

Uso:
    python3 grafo_unidades.py [dir] [--salida fichero]

Salida: `{"epics":[…]}` y nada más. Es la forma que aceptan a la vez el import de admin (`EpicIn`, graph_router.py) y
el carril `slice-ops.sh graph-sync` (`GraphSyncBundle`, event_catalog.py: `extra="forbid"`). El import ignora
`openspec_change`/`branch_base` (no están en `EpicIn`); el carril de sync sí los guarda. Determinista: orden por código,
sin marcas de tiempo.

Códigos de salida: 0 = bundle generado · 1 = el plan no cumple las reglas del hub (un motivo por línea en stderr) ·
2 = no hay plan legible o uso incorrecto.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

CABECERA = ["Unidad", "Tipo", "Título", "Depende de", "Ficheros", "Entrada", "Tareas", "Estado"]
PLAN = Path("docs/08-construccion/plan.md")
TAREAS = Path("docs/04-tareas-proceso")

# Límites de EpicIn/StoryIn (graph_router.py) y GraphSyncBundle (event_catalog.py).
LARGO = {"code": 50, "title": 300, "files_scope": 500, "docs_ref": 500, "openspec_change": 200, "acceptance_ref": 500}
MAX = {"epics": 200, "files_scope": 200, "depends_on": 50, "stories": 100}
TIPOS = {"cimiento", "etapa", "subproceso", "subscription"}
RE_CODIGO = re.compile(r"^(?:U[0-4]|SUB|E-[A-Za-z0-9][A-Za-z0-9-]*|S-[A-Za-z0-9][A-Za-z0-9-]*)$")
RE_FOUNDATIONAL = re.compile(r"^U[0-4]$")
RE_TAREA = re.compile(r"\bT-[A-Za-z0-9][A-Za-z0-9_-]*?(?=\.md\b|[\s,;]|$)")


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def _lista(celda: str) -> list[str]:
    limpia = celda.replace("`", "")
    items = [x.strip() for x in re.split(r"[,;]", limpia)]
    return [x for x in items if x and x not in ("—", "-", "–")]


def leer_filas(texto: str) -> tuple[list[dict], list[str]]:
    errores: list[str] = []
    lineas = texto.splitlines()
    inicio = next((i for i, l in enumerate(lineas) if l.lstrip().startswith("|") and _celdas(l) == CABECERA), None)
    if inicio is None:
        return [], ["no hay tabla de unidades con la cabecera `| " + " | ".join(CABECERA) + " |`"]
    filas = []
    for l in lineas[inicio + 2:]:
        if not l.lstrip().startswith("|"):
            break
        c = _celdas(l)
        if len(c) != len(CABECERA):
            errores.append("fila con %d celdas en vez de %d: %s" % (len(c), len(CABECERA), l.strip()))
            continue
        filas.append(dict(zip(CABECERA, c)))
    return filas, errores


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


# ── Change y rama de una unidad (lo que el claim del hub trae o deja en null) ──────────────────────────────────
# Única derivación del arnés: la usan el bundle de abajo, el render y la caché del claim (`slice-ops.sh claim`,
# `runtime-ops.sh`). El hub real devuelve `openspec_change: null` cuando el ADMIN importa el grafo por
# `POST /graph/import` (`EpicIn` no tiene el campo; solo el carril graph-sync lo guarda) y su `branch_base` es la RAMA
# DE TRABAJO de la unidad, no la de partida: `epic.branch_base or derive_branch_base(code, title)` (task_service.py),
# con `derive_branch_base = f"feature/{code.lower()}-{slug(title)}"` (graph_domain.py). Lo vigila
# scripts/check-contrato-hub.py.
PREFIJO_RAMA = "feature/"


def change_de_unidad(code: str, titulo: str) -> str:
    """`<código en minúsculas>-<slug del título>`, recortado al límite de `openspec_change` del hub."""
    return ("%s-%s" % ((code or "").lower(), _slug(titulo or "")))[:LARGO["openspec_change"]].strip("-")


def _texto(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def resolver_change(claim: dict) -> tuple:
    """(change, origen) de un claim: `"hub"` si lo trae; si no, `"derivado"` de `branch_base` sin `feature/` o, sin
    `branch_base`, de código + título. (None, None) si no hay con qué derivarlo."""
    claim = claim if isinstance(claim, dict) else {}
    change = _texto(claim.get("openspec_change"))
    if change:
        return change, "hub"
    rama = _texto(claim.get("branch_base"))
    if rama and rama != PREFIJO_RAMA:
        return (rama[len(PREFIJO_RAMA):] if rama.startswith(PREFIJO_RAMA) else rama), "derivado"
    code = _texto(claim.get("epic_code"))
    if code:
        return change_de_unidad(code, _texto(claim.get("epic_title"))), "derivado"
    return None, None


def rama_de_trabajo(claim: dict):
    """Rama de trabajo de la unidad: `branch_base` del claim o, si no viene, la que derivaría el hub."""
    claim = claim if isinstance(claim, dict) else {}
    rama = _texto(claim.get("branch_base"))
    if rama:
        return rama
    code = _texto(claim.get("epic_code"))
    if code:
        return PREFIJO_RAMA + change_de_unidad(code, _texto(claim.get("epic_title")))
    return None


def _historias(celda: str, raiz: Path) -> list[dict]:
    historias = {}
    for m in RE_TAREA.finditer(celda.replace("`", "")):
        codigo = m.group(0)
        ref = (TAREAS / (codigo + ".md")).as_posix()
        titulo = codigo
        fichero = raiz / ref
        if fichero.is_file():
            for l in fichero.read_text(encoding="utf-8").splitlines():
                if l.startswith("# "):
                    t = re.sub(r"^%s\s*[—:–-]*\s*" % re.escape(codigo), "", l[2:].strip()).strip()
                    titulo = t or codigo
                    break
        historias[codigo] = {"code": codigo, "title": titulo[:LARGO["title"]], "acceptance_ref": ref}
    return [historias[k] for k in sorted(historias)]


def _ciclos(deps: dict[str, list[str]]) -> list[str]:
    errores, estado = [], {}
    for raiz in sorted(deps):
        if estado.get(raiz):
            continue
        pila = [(raiz, iter(deps[raiz]))]
        estado[raiz] = 1
        while pila:
            nodo, it = pila[-1]
            for dep in it:
                if dep not in deps:
                    continue
                if estado.get(dep) == 1:
                    errores.append("ciclo de dependencias: %s -> %s" % (nodo, dep))
                elif not estado.get(dep):
                    estado[dep] = 1
                    pila.append((dep, iter(deps[dep])))
                    break
            else:
                estado[nodo] = 2
                pila.pop()
    return errores


def construir_bundle(raiz: Path) -> tuple[dict, list[str]]:
    raiz = Path(raiz)
    filas, errores = leer_filas((raiz / PLAN).read_text(encoding="utf-8"))
    epicas: dict[str, dict] = {}
    tipos: dict[str, str] = {}
    for f in filas:
        code = f["Unidad"].replace("`", "").strip()
        if not code:
            errores.append("una fila no tiene código de unidad")
            continue
        if code in epicas:
            errores.append("%s: código duplicado" % code)
            continue
        if len(code) > LARGO["code"]:
            errores.append("%s: el código excede %d caracteres" % (code[:20] + "…", LARGO["code"]))
        if not RE_CODIGO.match(code):
            errores.append("%s: código fuera del patrón (U0..U4, E-<familia>, S-<subproceso> o SUB)" % code)
        tipo = f["Tipo"].replace("`", "").strip().lower()
        if tipo not in TIPOS:
            errores.append("%s: tipo %r desconocido (cimiento|etapa|subproceso|subscription)" % (code, tipo))
        else:
            esperado = {"S": {"subproceso"}, "E": {"etapa"}, "U": {"cimiento", "etapa"}}.get(code[:1], set())
            if code == "SUB":
                esperado = {"subscription"}
            if RE_CODIGO.match(code) and tipo not in esperado:
                errores.append("%s: el tipo %r no corresponde a ese código" % (code, tipo))
        titulo = f["Título"].strip()
        if not titulo:
            errores.append("%s: sin título" % code)
        elif len(titulo) > LARGO["title"]:
            errores.append("%s: el título excede %d caracteres" % (code, LARGO["title"]))
        ficheros = sorted(set(_lista(f["Ficheros"])))
        if not ficheros:
            errores.append("%s: la unidad no declara ficheros (el hub serializaría la cola con `**`)" % code)
        if len(ficheros) > MAX["files_scope"] or any(len(x) > LARGO["files_scope"] for x in ficheros):
            errores.append("%s: ficheros fuera de límite (máx. %d entradas de %d caracteres)"
                           % (code, MAX["files_scope"], LARGO["files_scope"]))
        depende = sorted(set(_lista(f["Depende de"])))
        if len(depende) > MAX["depends_on"]:
            errores.append("%s: más de %d dependencias" % (code, MAX["depends_on"]))
        entrada = _lista(f["Entrada"])
        docs_ref = ", ".join(entrada)
        if len(docs_ref) > LARGO["docs_ref"]:
            errores.append("%s: `docs_ref` excede %d caracteres" % (code, LARGO["docs_ref"]))
        historias = _historias(f["Tareas"], raiz)
        if len(historias) > MAX["stories"]:
            errores.append("%s: %d tareas y el hub admite %d por épica" % (code, len(historias), MAX["stories"]))
        tipos[code] = tipo
        epica = {
            "code": code,
            "title": titulo,
            "layer": "FOUNDATIONAL" if tipo == "cimiento" or RE_FOUNDATIONAL.match(code) else "BUSINESS",
            "files_scope": ficheros,
            "depends_on": depende,
            "openspec_change": change_de_unidad(code, titulo),
            "stories": historias,
        }
        if docs_ref:
            epica["docs_ref"] = docs_ref
        epicas[code] = epica
    if len(epicas) > MAX["epics"]:
        errores.append("%d unidades: el hub admite %d" % (len(epicas), MAX["epics"]))
    if not epicas and not errores:
        errores.append("el plan no tiene ninguna unidad")
    for code, e in sorted(epicas.items()):
        for dep in e["depends_on"]:
            if dep not in epicas:
                errores.append("%s: depende de %s, que no está en el plan" % (code, dep))
            elif dep == code:
                errores.append("%s: depende de sí misma" % code)
    if "U1" in epicas and "U0" not in epicas["U1"]["depends_on"]:
        errores.append("U1: debe depender de U0 (el cimiento va primero)")
    errores.extend(_ciclos({c: e["depends_on"] for c, e in epicas.items()}))
    return {"epics": [epicas[c] for c in sorted(epicas)]}, errores


def main(argv: list[str]) -> int:
    dir_, salida, i = ".", None, 0
    posicionales = []
    while i < len(argv):
        if argv[i] == "--salida":
            if i + 1 >= len(argv):
                print("grafo: --salida exige una ruta", file=sys.stderr)
                return 2
            salida, i = argv[i + 1], i + 2
        elif argv[i].startswith("--"):
            print("grafo: opción desconocida: %s" % argv[i], file=sys.stderr)
            return 2
        else:
            posicionales.append(argv[i])
            i += 1
    if len(posicionales) > 1:
        print("grafo: demasiados argumentos", file=sys.stderr)
        return 2
    if posicionales:
        dir_ = posicionales[0]
    raiz = Path(dir_)
    try:
        bundle, errores = construir_bundle(raiz)
    except OSError as e:
        print("grafo: no se puede leer %s: %s" % (raiz / PLAN, e), file=sys.stderr)
        return 2
    if errores:
        print("grafo: el plan NO cumple las reglas del hub (no se genera nada):", file=sys.stderr)
        for x in errores:
            print("  - %s" % x, file=sys.stderr)
        return 1
    texto = json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    if salida:
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_text(texto, encoding="utf-8")
    else:
        sys.stdout.write(texto)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
