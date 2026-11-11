#!/usr/bin/env bash
# stack-guard.sh — PostToolUse · Write|Edit|MultiEdit
# Tras editar un pom.xml: el parent de Bonita es el de versiones/<v>.json, los bonita-connector-* llevan la versión
# de la matriz y (si hay lista) toda dependencia está en bonita-stack-allowlist.json. Exit 2 con el motivo en stderr.
# Lista: .claude/hub-context/context/bonita-stack-allowlist.json (hub) y, si no está, .claude/config/ (local);
# vacía o ausente = no se compara. Entrada ilegible o pom ilegible: deja pasar con aviso.
set -uo pipefail
if ! command -v python3 >/dev/null 2>&1; then
  echo "stack-guard: python3 no disponible; no se comprueba el pom (trycore-bonita doctor)" >&2
  exit 0
fi
HOOK_INPUT="$(cat)" HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" python3 - <<'PY'
import fnmatch, json, os, re, sys
import xml.etree.ElementTree as ET

try:
    datos = json.loads(os.environ.get("HOOK_INPUT", ""))
    ruta = str((datos.get("tool_input") or {}).get("file_path") or "")
except Exception as e:
    print(f"stack-guard: entrada ilegible ({e}); dejo pasar", file=sys.stderr)
    sys.exit(0)
if os.path.basename(ruta) != "pom.xml":
    sys.exit(0)
raiz = os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or os.getcwd()
if not os.path.isabs(ruta):
    ruta = os.path.join(datos.get("cwd") or raiz, ruta)


def leer(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


try:
    arbol = ET.parse(ruta).getroot()
except (OSError, ET.ParseError) as e:
    print(f"stack-guard: no pude leer {ruta} ({e}); dejo pasar", file=sys.stderr)
    sys.exit(0)


def local(t):
    return t.rsplit("}", 1)[-1]


def hijo(el, nombre):
    for c in el:
        if local(c.tag) == nombre:
            return c
    return None


def texto(el, nombre):
    c = hijo(el, nombre)
    return (c.text or "").strip() if c is not None else ""


props = {}
p = hijo(arbol, "properties")
if p is not None:
    props = {local(c.tag): (c.text or "").strip() for c in p}
_padre = hijo(arbol, "parent")
# ${project.*} sale del propio pom o, si no lo declara, de su <parent>.
for _k in ("groupId", "artifactId", "version"):
    _v = texto(arbol, _k) or (texto(_padre, _k) if _padre is not None else "")
    if _v:
        props.setdefault(f"project.{_k}", _v)
        props.setdefault(f"pom.{_k}", _v)
grupo_propio = props.get("project.groupId", "")


def resolver(v):
    for _ in range(5):
        n = re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m.group(1), m.group(0)), v)
        if n == v:
            break
        v = n
    return v


errores = []
cfg = leer(os.path.join(raiz, ".trycore-bonita.json")) or {}
vb = cfg.get("version_bonita")
matriz = None
if vb:
    for base in (os.path.join(raiz, "tools", "arnes", "versiones"), os.path.join(os.environ["HOOK_DIR"], "..", "..", "..", "tools", "arnes", "versiones"),
                 os.path.join(os.environ["HOOK_DIR"], "..", "versiones")):
        matriz = leer(os.path.join(base, f"{vb}.json"))
        if matriz:
            break
if vb and not matriz:
    print(f"stack-guard: sin matriz de versiones para Bonita {vb}; no se comprueban parent ni conectores", file=sys.stderr)

parent = hijo(arbol, "parent")
if matriz and parent is not None and texto(parent, "groupId") == "org.bonitasoft" and texto(parent, "artifactId") == "bonita-project":
    pedido = (matriz.get("maven_parent") or {}).get("version")
    real = resolver(texto(parent, "version"))
    if pedido and real != pedido:
        errores.append(f"el parent org.bonitasoft:bonita-project es {real} y la matriz de Bonita {vb} pide {pedido}")

conectores = {}
if matriz:
    for c in (matriz.get("conectores") or {}).values():
        if isinstance(c, dict) and c.get("artifactId"):
            conectores[c["artifactId"]] = c.get("version")
        elif isinstance(c, str) and c.count(":") == 2:
            g, a, v = c.split(":")
            conectores[a] = v

lista = None
for rel in ("hub-context/context", "config"):
    a = leer(os.path.join(raiz, ".claude", rel, "bonita-stack-allowlist.json"))
    if isinstance(a, dict):
        lista = a.get("allow")
        break
permitidos = []
for e in lista if isinstance(lista, list) else []:
    if isinstance(e, str):
        permitidos.append(e)
    elif isinstance(e, dict) and e.get("groupId") and e.get("artifactId"):
        permitidos.append(f"{e['groupId']}:{e['artifactId']}")

deps = hijo(arbol, "dependencies")
for d in list(deps) if deps is not None else []:
    if local(d.tag) != "dependency":
        continue
    g, a = resolver(texto(d, "groupId")), resolver(texto(d, "artifactId"))
    v = resolver(texto(d, "version"))
    if grupo_propio and g == grupo_propio:  # módulo del propio proyecto
        continue
    if a.startswith("bonita-connector-") and v and "${" not in v and a in conectores and conectores[a] and v != conectores[a]:
        errores.append(f"{g}:{a} es {v} y la matriz de Bonita {vb} pide {conectores[a]}")
    if permitidos:
        ga = f"{g}:{a}"
        if not any(fnmatch.fnmatchcase(ga, pat if ":" in pat else pat + ":*") for pat in permitidos):
            errores.append(f"la dependencia {ga} no está en .claude/config/bonita-stack-allowlist.json")

if errores:
    print(f"stack-guard: {os.path.relpath(ruta, raiz) if ruta.startswith(raiz) else ruta}", file=sys.stderr)
    for e in errores:
        print(f"  - {e}", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
PY
