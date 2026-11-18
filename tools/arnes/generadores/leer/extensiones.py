"""Extensiones propias del proyecto (Plan 5, R-03 y R-10): definiciones e implementaciones de actor filters y
conectores escritas a mano en `bonita-project/extensions/<modulo>/`, y la tabla de actor filters de `bdm.md`.

El arnés **no** genera el código de un filtro o de un conector propio: lee su `.def` para conocer id, versión,
entradas y salidas, y su `.impl` para el mapeo definición → implementación del `.conf`. Formato del arquetipo
(`actor-filter-archetype.adoc`, `connector-archetype.adoc`): los dos ficheros en `src/main/resources-filtered/`, con
`${…}` que Maven sustituye en el build con las `<properties>` del pom del módulo (y `project.artifactId`,
`project.version`, `project.groupId`). Aquí se sustituyen igual; un `${…}` sin valor en un campo que el arnés lee es
error.

Tabla de filtros (`bdm.md › Organización`, primera columna `Actor filter`): «Tarea que asigna» (tokens de tareas),
«Definición» (`definitionId` del `.def`), «Entradas» («`entrada` ← `texto` (`flt_<filtro>.<entrada>`)» separadas
por «; »). El Groovy de cada entrada va en `expresiones.md` con ese ID; queda como marcador hasta `construir_spec`.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from generadores.leer import columna, donde, filas, requerir, seccion, vacio
from generadores.md import Documento, codigo

F = "bdm.md"
RECURSOS = Path("src") / "main" / "resources-filtered"
NS_DEF = "{http://www.bonitasoft.org/ns/connector/definition/6.1}"
_PROP = re.compile(r"\$\{([^}]+)\}")
_BACKTICKS = re.compile(r"`([^`]+)`")
# «`entrada` ← `texto` (`ID`)»: el texto entre backticks puede llevar «;» (no se parte por «; » a ciegas).
_ENTRADA = re.compile(r"`([A-Za-z_][\w]*)`\s*←\s*`([^`]*)`\s*\(`([^`]+)`\)")
COL_FILTROS = ("Tarea que asigna", "Definición", "Entradas")


# ------------------------------------------------------------------------------------------- entradas con marca

def entradas_con_marca(celda: str, prefijo: str, ubic: str, errores: list[str]) -> dict[str, dict]:
    """«`entrada` ← `texto` (`<ID>`)» separadas por «; » → {entrada: marcador de expresión}. Cada ID empieza por
    `prefijo` (`conn_x.` o `flt_<filtro>.`). Un fragmento que no tiene esa forma es error (nada se descarta en
    silencio)."""
    out: dict[str, dict] = {}
    for m in _ENTRADA.finditer(celda):
        nombre, texto, id_ = m.group(1), m.group(2), m.group(3).strip()
        if nombre in out:
            errores.append(f"{ubic}: entrada «{nombre}» repetida")
            continue
        if not id_.startswith(prefijo) or id_ == prefijo:
            errores.append(f"{ubic}: el ID «{id_}» de la entrada «{nombre}» debe empezar por «{prefijo}»")
            continue
        out[nombre] = requerir(id_, texto, ubic)
    resto = _ENTRADA.sub("", celda).replace(";", " ").strip()
    if resto:
        errores.append(f"{ubic}: «{resto}» no tiene la forma «`entrada` ← `texto` (`ID`)» (varias, separadas por «; »)")
    return out


# ---------------------------------------------------------------------------------------------------- .def/.impl

def _propiedades(pom: Path) -> dict[str, str]:
    if not pom.is_file():
        return {}
    try:
        raiz = ET.parse(pom).getroot()
    except ET.ParseError:
        return {}
    ns = raiz.tag[: raiz.tag.index("}") + 1] if raiz.tag.startswith("{") else ""
    props = {}
    for clave, ruta in (("project.artifactId", "artifactId"), ("project.version", "version"),
                        ("project.groupId", "groupId")):
        valor = raiz.findtext(f"{ns}{ruta}") or raiz.findtext(f"{ns}parent/{ns}{ruta}")
        if valor:
            props[clave] = valor.strip()
    for p in raiz.find(f"{ns}properties") if raiz.find(f"{ns}properties") is not None else []:
        props[p.tag.removeprefix(ns)] = (p.text or "").strip()
    return props


def _sustituir(texto: str | None, props: dict[str, str], ubic: str, campo: str, errores: list[str]) -> str | None:
    if texto is None:
        errores.append(f"{ubic}: falta <{campo}>")
        return None
    valor = texto.strip()
    for _ in range(5):  # una propiedad puede nombrar otra (`impl-version` = `${project.version}`)
        nuevo = _PROP.sub(lambda m: props.get(m.group(1), m.group(0)), valor)
        if nuevo == valor:
            break
        valor = nuevo
    pendientes = _PROP.findall(valor)
    if pendientes:
        errores.append(f"{ubic}: <{campo}> usa ${{{pendientes[0]}}}, que no está en las <properties> del pom del "
                       "módulo")
        return None
    return valor


def _xml(ruta: Path, ubic: str, errores: list[str]) -> ET.Element | None:
    try:
        return ET.parse(ruta).getroot()
    except ET.ParseError as e:
        errores.append(f"{ubic}: XML mal formado ({e})")
        return None


def _definicion(ruta: Path, props: dict, ubic: str, errores: list[str]) -> dict | None:
    raiz = _xml(ruta, ubic, errores)
    if raiz is None:
        return None
    id_ = _sustituir(raiz.findtext("id"), props, ubic, "id", errores)
    version = _sustituir(raiz.findtext("version"), props, ubic, "version", errores)
    entradas, salidas = [], []
    for i in raiz.findall("input"):
        entradas.append({"nombre": i.get("name"), "tipo": i.get("type"),
                         "obligatoria": (i.get("mandatory") or "false").strip() == "true"})
    for o in raiz.findall("output"):
        salidas.append({"nombre": o.get("name"), "tipo": o.get("type")})
    if id_ is None or version is None:
        return None
    return {"id": id_, "version": version, "entradas": entradas, "salidas": salidas}


def _implementacion(ruta: Path, props: dict, ubic: str, errores: list[str]) -> dict | None:
    raiz = _xml(ruta, ubic, errores)
    if raiz is None:
        return None
    campos = {c: _sustituir(raiz.findtext(c), props, ubic, c, errores)
              for c in ("implementationId", "implementationVersion", "definitionId", "definitionVersion")}
    if None in campos.values():
        return None
    clase = raiz.findtext("implementationClassname")
    campos["_clase"] = _sustituir(clase, props, ubic, "implementationClassname", []) if clase else None
    return campos


def _tipo_de_clase(mod: Path, clase: str | None) -> str | None:
    """«filtro» si la clase de la implementación (en `src/main/groovy` o `src/main/java` del módulo) extiende
    `AbstractUserFilter`, «conector» si extiende `AbstractConnector`; None si no se sabe (revisión final, M-13)."""
    if not clase:
        return None
    rel = clase.replace(".", "/")
    for base in ("groovy", "java"):
        for ext in (".groovy", ".java"):
            f = mod / "src" / "main" / base / f"{rel}{ext}"
            if f.is_file():
                texto = f.read_text(encoding="utf-8", errors="replace")
                if re.search(r"\bextends\s+[\w.]*AbstractUserFilter\b", texto):
                    return "filtro"
                if re.search(r"\bextends\s+[\w.]*AbstractConnector\b", texto):
                    return "conector"
    return None


def _hijos(pom: Path, ruta: str) -> list[str]:
    """Textos de `ruta` (p. ej. `modules/module`) del pom, sin espacio de nombres; [] si no se puede leer."""
    try:
        raiz = ET.parse(pom).getroot()
    except (ET.ParseError, OSError):
        return []
    ns = raiz.tag[: raiz.tag.index("}") + 1] if raiz.tag.startswith("{") else ""
    return [(e.text or "").strip() for e in raiz.findall("/".join(f"{ns}{x}" for x in ruta.split("/")))]


def _no_registrados(extensiones: Path) -> set[str] | None:
    """Módulos de `extensions/` que no están en los `<modules>` de `extensions/pom.xml` o cuyo artifactId no es
    dependencia de `app/pom.xml` (revisión final, I-6). None si no hay `extensions/pom.xml` (no es un proyecto: p. ej.
    la carpeta de un ejemplo)."""
    pom = extensiones / "pom.xml"
    if not pom.is_file():
        return None
    modulos = set(_hijos(pom, "modules/module"))
    deps = set(_hijos(extensiones.parent / "app" / "pom.xml", "dependencies/dependency/artifactId"))
    out = set()
    for mod in (p for p in extensiones.iterdir() if p.is_dir()):
        artifact = (_propiedades(mod / "pom.xml").get("project.artifactId") or mod.name)
        if mod.name not in modulos or artifact not in deps:
            out.add(mod.name)
    return out


def leer_extensiones(extensiones: Path) -> tuple[dict | None, list[str]]:
    """`{definiciones: {defId: {version, entradas, salidas, implementacion: {id, version}, modulo}}}` de los
    `.def`/`.impl` de `extensiones/<modulo>/src/main/resources-filtered/`. Sin ninguna definición, `None` (la spec no
    lleva la clave). Cada definición necesita una sola implementación de su misma versión."""
    errores: list[str] = []
    definiciones: dict[str, dict] = {}
    if not extensiones.is_dir():
        return None, errores
    sin_registrar = _no_registrados(extensiones) or set()
    for mod in sorted(p for p in extensiones.iterdir() if p.is_dir()):
        recursos = mod / RECURSOS
        if not recursos.is_dir():
            continue
        props = _propiedades(mod / "pom.xml")
        base = f"bonita-project/extensions/{mod.name}/{RECURSOS.as_posix()}"
        defs = {}
        for f in sorted(recursos.glob("*.def")):
            d = _definicion(f, props, f"{base}/{f.name}", errores)
            if d is not None:
                defs[d["id"]] = (d, f"{base}/{f.name}")
        impls: dict[str, list[dict]] = {}
        for f in sorted(recursos.glob("*.impl")):
            i = _implementacion(f, props, f"{base}/{f.name}", errores)
            if i is None:
                continue
            i["_ubic"] = f"{base}/{f.name}"
            if i["definitionId"] not in defs:
                errores.append(f"{i['_ubic']}: implementa «{i['definitionId']}», y no hay .def con ese id en "
                               f"{base}")
                continue
            impls.setdefault(i["definitionId"], []).append(i)
        for id_, (d, ubic) in defs.items():
            suyas = impls.get(id_, [])
            if not suyas:
                errores.append(f"{ubic}: la definición «{id_}» no tiene .impl en {base}")
                continue
            if len(suyas) > 1:
                errores.append(f"{ubic}: la definición «{id_}» tiene {len(suyas)} .impl; el arnés mapea una sola")
                continue
            impl = suyas[0]
            if impl["definitionVersion"] != d["version"]:
                errores.append(f"{impl['_ubic']}: implementa «{id_}» {impl['definitionVersion']}, y el .def es la "
                               f"versión {d['version']}")
                continue
            if id_ in definiciones:
                errores.append(f"{ubic}: la definición «{id_}» ya está en el módulo «{definiciones[id_]['modulo']}»")
                continue
            definiciones[id_] = {"version": d["version"], "entradas": d["entradas"], "salidas": d["salidas"],
                                 "implementacion": {"id": impl["implementationId"],
                                                    "version": impl["implementationVersion"]},
                                 "modulo": mod.name}
            tipo = _tipo_de_clase(mod, impl.get("_clase"))
            if tipo is not None:
                definiciones[id_]["tipo"] = tipo
            if mod.name in sin_registrar:
                definiciones[id_]["registrado"] = False  # solo si no lo está (G-5)
    return ({"definiciones": definiciones} if definiciones else None), errores


# ---------------------------------------------------------------------------------------------- tabla de filtros

def leer_filtros(doc: Documento) -> tuple[dict, list[str]]:
    """Filtros declarados en `bdm.md › Organización` (tabla con primera columna `Actor filter`)."""
    errores: list[str] = []
    out: dict[str, dict] = {}
    ubic = donde(F, "Organización")
    sec = seccion(doc, "Organización", F, errores)
    tablas = [t for t in (sec.tablas if sec else []) if t and list(t[0])[0] == "Actor filter"]
    if not tablas:
        return out, errores
    if len(tablas) > 1:  # la segunda se perdería en silencio (revisión final, M-5)
        errores.append(f"{ubic}: hay {len(tablas)} tablas «Actor filter | …»; los filtros van en una sola tabla «Actor "
                       "filter» (una fila por filtro)")
    t = tablas[0]
    faltan = [c for c in COL_FILTROS if not any(k.startswith(c) for k in t[0])]
    if faltan:
        errores.append(f"{ubic}: a la tabla «Actor filter | …» le faltan las columnas {faltan} (formato de la "
                       "plantilla)")
        return out, errores
    for f in filas(t):
        ids = _BACKTICKS.findall(f["Actor filter"])
        id_ = ids[0].strip() if ids else codigo(f["Actor filter"]).strip()
        u = donde(ubic, id_)
        if id_ in out:
            errores.append(f"{u}: filtro repetido")
            continue
        tareas_celda = columna(f, "Tarea que asigna")
        tareas = [] if vacio(tareas_celda) else [x.strip() for x in _BACKTICKS.findall(tareas_celda)]
        if not tareas:
            errores.append(f"{u}: «Tarea que asigna» debe nombrar las tareas que asigna el filtro (`tarea`; …)")
        defs = _BACKTICKS.findall(columna(f, "Definición"))
        if vacio(columna(f, "Definición")) or not defs:
            errores.append(f"{u}: «Definición» debe ser el `definitionId` del .def del proyecto (`usuario-del-caso`)")
        celda = columna(f, "Entradas")
        entradas = {} if vacio(celda) else entradas_con_marca(celda, f"flt_{id_}.", donde(u, "Entradas"), errores)
        out[id_] = {"definicion": defs[0].strip() if defs else None, "entradas": entradas, "tareas_doc": tareas}
    return out, errores
