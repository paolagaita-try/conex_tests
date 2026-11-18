"""Adopción de un proyecto del Studio y línea base de lo que ya existía.

La línea base (`.trycore-bonita-linea-base.json`) registra, con su SHA-256, cada fichero del Studio que el modo
«proyecto existente» no debe cambiar sin confirmación, y los pools que contienen los `.proc`. Junto a ella se guarda
una copia byte a byte de cada fichero registrado (`.trycore-bonita-linea-base/<ruta relativa>`, versionada): `generar`
aplica la cirugía siempre sobre esa copia, así que repetirlo da lo mismo. Adoptar nunca escribe bajo
`bonita-project/`."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from generadores.existente.leer_xml import leer_existente
from generadores.existente.mapa import DIRECTORIO, escribir_mapa
from generadores.nombres import GRUPO, MENSAJE, NOMBRE_PROYECTO, es
from generadores.version import cargar_version, versiones_admitidas

LINEA_BASE = Path(".trycore-bonita-linea-base.json")
COPIA = Path(".trycore-bonita-linea-base")  # copia de cada fichero de la línea base, con su ruta relativa
CONFIG = ".trycore-bonita.json"
BONITA = "bonita-project"
# Patrones de la línea base (spec 6.2), relativos a la raíz del proyecto.
PATRONES = (f"{BONITA}/app/diagrams/*.proc", f"{BONITA}/app/process_configurations/*.conf", f"{BONITA}/bdm/bom.xml",
            f"{BONITA}/app/organizations/*.xml", f"{BONITA}/app/profiles/*.xml", f"{BONITA}/app/environements/*.xml")
_POM = "{http://maven.apache.org/POM/4.0.0}"
_XMI_ID = "{http://www.omg.org/XMI}id"
_XMI_TIPO = "{http://www.omg.org/XMI}type"
_SUFIJO_PARENT = re.compile(r"-parent$")


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _ficheros(proyecto: Path) -> list[str]:
    rutas = {p.relative_to(proyecto).as_posix() for patron in PATRONES for p in proyecto.glob(patron) if p.is_file()}
    return sorted(rutas)


def _pools(proyecto: Path, rel: str) -> dict[str, dict]:
    try:
        raiz = ET.parse(proyecto / rel).getroot()
    except ET.ParseError as e:
        raise ValueError(f"{rel}: no es un XML válido ({e})") from e
    pools = {}
    for e in raiz.iter("elements"):
        if e.get(_XMI_TIPO) != "process:Pool":
            continue
        nombre, version, xmi_id = e.get("name"), e.get("version"), e.get(_XMI_ID)
        if not (nombre and version and xmi_id):
            raise ValueError(f"{rel}: un pool sin nombre, versión o xmi:id")
        conf = f"{BONITA}/app/process_configurations/{xmi_id}.conf"
        pools[f"{nombre}@{version}"] = {"fichero": rel, "xmi_id": xmi_id,
                                        "conf": conf if (proyecto / conf).is_file() else None}
    return pools


def crear_linea_base(proyecto: Path) -> dict:
    """La línea base de `proyecto` tal como está ahora en disco (no escribe nada)."""
    proyecto = Path(proyecto)
    ficheros = _ficheros(proyecto)
    pools: dict[str, dict] = {}
    for rel in ficheros:
        if rel.endswith(".proc"):
            for clave, datos in _pools(proyecto, rel).items():
                if clave in pools:
                    raise ValueError(f"El pool {clave} está en {pools[clave]['fichero']} y en {rel}")
                pools[clave] = datos
    return {"version": 1, "ficheros": {rel: _sha256(proyecto / rel) for rel in ficheros}, "pools": pools}


def leer_linea_base(proyecto: Path) -> dict | None:
    ruta = Path(proyecto) / LINEA_BASE
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_linea_base(proyecto: Path, datos: dict) -> None:
    """Escribe la línea base y rehace su copia (`COPIA`) con los ficheros que registra, tal como están en disco.
    `ValueError` si un fichero falta o no tiene el hash registrado; en ese caso no se escribe nada."""
    proyecto = Path(proyecto)
    contenidos = {}
    for rel, sha in datos["ficheros"].items():
        ruta = proyecto / rel
        if not ruta.is_file():
            raise ValueError(f"{rel}: falta; no se puede copiar a la línea base")
        contenidos[rel] = ruta.read_bytes()
        if hashlib.sha256(contenidos[rel]).hexdigest() != sha:
            raise ValueError(f"{rel}: su contenido no coincide con el hash de la línea base")
    shutil.rmtree(proyecto / COPIA, ignore_errors=True)
    for rel, contenido in contenidos.items():
        destino = proyecto / COPIA / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
    (proyecto / LINEA_BASE).write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def original(proyecto: Path, rel: str) -> bytes:
    """El contenido de `rel` tal como lo registra la línea base, leído de su copia (no del fichero de trabajo).
    `ValueError` si `rel` no está en la línea base, si falta su copia o si la copia no tiene el hash registrado."""
    proyecto = Path(proyecto)
    rel = Path(rel).as_posix()
    datos = leer_linea_base(proyecto)
    if datos is None or rel not in datos["ficheros"]:
        raise ValueError(f"{rel}: no está en la línea base")
    copia = proyecto / COPIA / rel
    if not copia.is_file():
        raise ValueError(f"{rel}: falta su copia en {COPIA.as_posix()}/; vuelve a crear la línea base")
    contenido = copia.read_bytes()
    if hashlib.sha256(contenido).hexdigest() != datos["ficheros"][rel]:
        raise ValueError(f"{COPIA.as_posix()}/{rel}: no coincide con el hash de la línea base")
    return contenido


def es_existente(proyecto: Path, rel: str) -> bool:
    """¿`rel` (ruta relativa al proyecto, con `/`) es un fichero de la línea base?"""
    datos = leer_linea_base(proyecto)
    return datos is not None and Path(rel).as_posix() in datos["ficheros"]


def _config(proyecto: Path) -> dict | None:
    ruta = Path(proyecto) / CONFIG
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{CONFIG}: no es un JSON válido ({e})") from e
    if not isinstance(datos, dict):
        raise ValueError(f"{CONFIG}: debe ser un objeto JSON")
    return datos


def modo_existente(proyecto: Path) -> bool:
    try:
        datos = _config(proyecto)
    except ValueError:
        return False
    return bool(datos) and datos.get("modo") == "existente"


def _leer_pom(proyecto: Path) -> tuple[str, str, str]:
    """(artifactId, groupId, versión del parent) del `pom.xml` de `bonita-project/`."""
    ruta = proyecto / BONITA / "pom.xml"
    try:
        raiz = ET.parse(ruta).getroot()
    except ET.ParseError as e:
        raise ValueError(f"{BONITA}/pom.xml: no es un XML válido ({e})") from e

    def texto(padre: ET.Element, etiqueta: str) -> str:
        e = padre.find(_POM + etiqueta)
        return (e.text or "").strip() if e is not None else ""

    parent = raiz.find(_POM + "parent")
    return (texto(raiz, "artifactId"), texto(raiz, "groupId") or (texto(parent, "groupId") if parent is not None else ""),
            texto(parent, "version") if parent is not None else "")


def _version_del_parent(parent: str) -> str:
    """La versión de Bonita de `versiones/` cuyo parent Maven es `parent`."""
    for v in versiones_admitidas():
        if cargar_version(v)["maven_parent"]["version"] == parent:
            return v
    raise ValueError(f"{BONITA}/pom.xml: el parent bonita-project {parent or '(sin versión)'} no corresponde a ninguna "
                     f"versión de Bonita admitida ({', '.join(versiones_admitidas())})")


def adoptar(proyecto: Path, nombre: str | None, grupo: str | None) -> Path:
    """Adopta `proyecto` (una carpeta con `bonita-project/` hecho en el Studio): escribe `.trycore-bonita.json` con
    `modo: "existente"`, la línea base (con su copia) y el mapa de lo existente (`docs/07-bonita/existente/`). No
    escribe bajo `bonita-project/`. ValueError si no se puede adoptar (ya adoptado, sin `bonita-project/`, versión de
    Bonita no admitida, nombre o grupo no válidos); en ese caso no se escribe nada."""
    proyecto = Path(proyecto)
    if not (proyecto / BONITA / "pom.xml").is_file():
        raise ValueError(f"{proyecto} no tiene {BONITA}/pom.xml: no hay nada que adoptar")
    config = _config(proyecto)
    if config is not None and config.get("modo") == "existente":
        raise ValueError(f"{proyecto} ya adoptado (modo existente en {CONFIG})")
    artefacto, grupo_pom, parent = _leer_pom(proyecto)
    config = dict(config) if config is not None else {}
    if "version_bonita" not in config:
        config["version_bonita"] = _version_del_parent(parent)
    cargar_version(str(config["version_bonita"]))  # ValueError si no está en versiones/
    config["nombre"] = nombre or config.get("nombre") or _SUFIJO_PARENT.sub("", artefacto)
    config["grupo"] = grupo or config.get("grupo") or grupo_pom
    if not es(NOMBRE_PROYECTO, config["nombre"]):
        raise ValueError(f"nombre «{config['nombre']}»: {MENSAJE['nombre']}")
    if not es(GRUPO, config["grupo"]):
        raise ValueError(f"grupo «{config['grupo']}»: {MENSAJE['grupo']}")
    for clave, valor in (("edicion_desarrollo", "community"), ("edicion_destino", "community"),
                         ("formularios", "svelte")):
        config.setdefault(clave, valor)
    config["modo"] = "existente"
    datos = crear_linea_base(proyecto)  # todo se calcula antes de escribir
    leer_existente(proyecto)  # un XML ilegible falla aquí, antes de escribir nada
    original = (proyecto / CONFIG).read_bytes() if (proyecto / CONFIG).is_file() else None
    existia_mapa = (proyecto / DIRECTORIO).is_dir()
    try:
        escribir_linea_base(proyecto, datos)
        (proyecto / CONFIG).write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        escribir_mapa(proyecto)
    except BaseException:
        (proyecto / LINEA_BASE).unlink(missing_ok=True)
        shutil.rmtree(proyecto / COPIA, ignore_errors=True)
        if original is None:
            (proyecto / CONFIG).unlink(missing_ok=True)
        else:
            (proyecto / CONFIG).write_bytes(original)
        if not existia_mapa:
            shutil.rmtree(proyecto / DIRECTORIO, ignore_errors=True)
        raise
    return proyecto
