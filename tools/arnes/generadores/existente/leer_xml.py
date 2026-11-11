"""Lectura de lo que ya existe en un proyecto del Studio: BDM, organización y pools de los `.proc`.

Solo lee (`xml.etree.ElementTree`); nunca escribe. El resultado es un diccionario estable (mismas claves ordenadas,
mismos valores) que usan el mapa, la documentación de cambios, la clasificación y la cirugía:

- `bdm`: `{"paquete" (el más común), "objetos": {Objeto: {"paquete", "atributos": {nombre: {tipo, obligatorio, multiple, longitud, relacion}}}}}`.
- `organizacion`: `{"grupos": [ruta], "roles": [str], "usuarios": {usuario: [[rol, grupo]]}}`.
- `pools`: `{"<Pool>@<v>": {fichero, xmi_id, nombre, version, lanes, nodos, transiciones, contratos,
  no_interpretados}}`.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from generadores.escribir.bom import PAQUETE_PARAMETROS
from generadores.escribir.proc.datos import INSTANCIACION
from generadores.escribir.proc.eventos import CLASE_BORDE
from generadores.escribir.proc.flujo import CLASES, FIN_TERMINATE

BONITA = "bonita-project"
_XMI_ID = "{http://www.omg.org/XMI}id"
_XMI_TIPO = "{http://www.omg.org/XMI}type"
# Tipos de flujo que el generador escribe: son los únicos que el arnés interpreta.
INTERPRETADOS = frozenset((*CLASES.values(), FIN_TERMINATE, *CLASE_BORDE.values()))
_RELACIONES = {"COMPOSITION": "composición", "AGGREGATION": "agregación"}


def _parsear(ruta: Path, rel: str) -> ET.Element:
    try:
        return ET.parse(ruta).getroot()
    except ET.ParseError as e:
        raise ValueError(f"{rel}: no es un XML válido ({e})") from e


def _local(e: ET.Element) -> str:
    return e.tag.rsplit("}", 1)[-1]


def _todos(raiz: ET.Element, etiqueta: str) -> list[ET.Element]:
    """Descendientes con esa etiqueta, con o sin espacio de nombres."""
    return [e for e in raiz.iter() if _local(e) == etiqueta]


def _corto(qualified: str) -> str:
    return qualified.rsplit(".", 1)[-1]


def _bdm(proyecto: Path) -> dict:
    ruta = proyecto / BONITA / "bdm" / "bom.xml"
    vacio = {"paquete": None, "objetos": {}}
    if not ruta.is_file():
        return vacio
    raiz = _parsear(ruta, f"{BONITA}/bdm/bom.xml")
    objetos: dict[str, dict] = {}
    for bo in _todos(raiz, "businessObject"):
        qualified = bo.get("qualifiedName") or ""
        nombre = _corto(qualified)
        if not nombre:
            raise ValueError(f"{BONITA}/bdm/bom.xml: un businessObject sin qualifiedName")
        if nombre in objetos:
            raise ValueError(f"{BONITA}/bdm/bom.xml: el objeto {nombre} está repetido (en otro paquete)")
        paquete = qualified.rsplit(".", 1)[0] if "." in qualified else None
        atributos = {}
        for campo in [c for f in bo if _local(f) == "fields" for c in f]:
            relacion = _local(campo) == "relationField"
            longitud = campo.get("length")
            atributos[campo.get("name")] = {
                "tipo": _corto(campo.get("reference") or "") if relacion else campo.get("type"),
                "obligatorio": campo.get("nullable") == "false",
                "multiple": campo.get("collection") == "true",
                "longitud": int(longitud) if longitud and longitud.isdigit() else None,
                "relacion": _RELACIONES.get(campo.get("type"), (campo.get("type") or "").lower()) if relacion else None}
        objetos[nombre] = {"paquete": paquete, "atributos": dict(sorted(atributos.items()))}
    # Paquete del BDM = el que comparten más objetos de negocio (sin contar los Kp* del módulo de parámetros, que
    # en el fixture son mayoría); en empate, el del primero en el fichero (Counter conserva el orden).
    cuentas = Counter(o["paquete"] for o in objetos.values() if o["paquete"] and o["paquete"] != PAQUETE_PARAMETROS)
    cuentas = cuentas or Counter(o["paquete"] for o in objetos.values() if o["paquete"])
    paquete = max(cuentas, key=cuentas.get) if cuentas else None
    return {"paquete": paquete, "objetos": dict(sorted(objetos.items()))}


def _ruta_grupo(nombre: str, padre: str | None) -> str:
    return "/".join(p for p in ((padre or "").strip("/"), nombre) if p)


def _organizacion(proyecto: Path) -> dict:
    grupos: set[str] = set()
    roles: set[str] = set()
    usuarios: dict[str, set[tuple[str, str]]] = {}
    for ruta in sorted((proyecto / BONITA / "app" / "organizations").glob("*.xml")):
        raiz = _parsear(ruta, ruta.relative_to(proyecto).as_posix())
        for g in _todos(raiz, "group"):
            grupos.add(_ruta_grupo(g.get("name") or "", g.get("parentPath")))
        roles.update(r.get("name") for r in _todos(raiz, "role") if r.get("name"))
        for u in _todos(raiz, "user"):
            usuarios.setdefault(u.get("userName"), set())
        for m in _todos(raiz, "membership"):
            def texto(etiqueta: str) -> str:
                e = next((h for h in m if _local(h) == etiqueta), None)
                return (e.text or "").strip() if e is not None else ""
            usuarios.setdefault(texto("userName"), set()).add(
                (texto("roleName"), _ruta_grupo(texto("groupName"), texto("groupParentPath"))))
    return {"grupos": sorted(grupos), "roles": sorted(roles),
            "usuarios": {u: [list(m) for m in sorted(ms)] for u, ms in sorted(usuarios.items())}}


def _entradas(padre: ET.Element, prefijo: str = "") -> dict[str, str]:
    """Inputs de un contrato, con los anidados como `padre.hijo`."""
    out = {}
    for i in padre.findall("inputs"):
        nombre = prefijo + (i.get("name") or "")
        out[nombre] = i.get("type") or ""
        out.update(_entradas(i, nombre + "."))
    return out


def leer_pool(raiz: ET.Element, e: ET.Element, rel: str) -> dict:
    nombre, version, xmi_id = e.get("name"), e.get("version"), e.get(_XMI_ID)
    actores = {a.get(_XMI_ID): a.get("name") for a in e.findall("actors")}
    lanes = {}
    elementos: list[tuple[ET.Element, str | None]] = []  # (elemento de flujo, lane)
    for hijo in e.findall("elements"):
        if hijo.get(_XMI_TIPO) == "process:Lane":
            lanes[hijo.get("name")] = {"id": hijo.get(_XMI_ID), "actor": actores.get(hijo.get("actor"))}
            elementos.extend((n, hijo.get("name")) for n in hijo.findall("elements"))
        else:
            elementos.append((hijo, None))
    todos = []  # (elemento, lane) incluidos los timers de borde de cada tarea
    for n, lane in elementos:
        todos.append((n, lane))
        todos.extend((b, lane) for b in n.findall("BoundaryIntermediateEvents"))
    veces = Counter(x.get("name") for x, _ in todos)
    repetidos = {n for n, v in veces.items() if v > 1}
    clave_de = {n.get(_XMI_ID): (n.get("name") if n.get("name") and n.get("name") not in repetidos
                                 else n.get(_XMI_ID)) for n, _ in todos}
    donde_base = f"{nombre}@{version}"
    nodos, contratos, no_interpretados = {}, {}, []
    for n, lane in todos:
        tipo = n.get(_XMI_TIPO)
        clave = clave_de[n.get(_XMI_ID)]
        nodos[clave] = {"id": n.get(_XMI_ID), "nombre": n.get("name"), "tipo": tipo, "lane": lane}
        if tipo not in INTERPRETADOS:
            no_interpretados.append(f"{tipo} en {donde_base} › {'lane ' + lane if lane else 'pool'} › {clave}")
        contrato = n.find("contract")
        if contrato is not None and _entradas(contrato):
            contratos[clave] = _entradas(contrato)
    contrato = e.find("contract")
    if contrato is not None and _entradas(contrato):
        contratos[INSTANCIACION] = _entradas(contrato)
    conexiones = e.findall("connections")
    pares = [(clave_de.get(c.get("source"), c.get("source")), clave_de.get(c.get("target"), c.get("target")))
             for c in conexiones]
    transiciones = {}
    for c, (desde, hacia) in zip(conexiones, pares):
        clave = f"{desde}->{hacia}" if pares.count((desde, hacia)) == 1 else c.get(_XMI_ID)
        condicion = c.find("condition")
        contenido = (condicion.get("content") or "").strip() if condicion is not None else ""
        transiciones[clave] = {"id": c.get(_XMI_ID), "desde": desde, "hacia": hacia,
                               "condicion": contenido or ("(por defecto)" if c.get("isDefault") == "true" else None)}
    return {"fichero": rel, "xmi_id": xmi_id, "nombre": nombre, "version": version,
            "lanes": dict(sorted(lanes.items())), "nodos": nodos, "transiciones": transiciones,
            "contratos": {t: dict(sorted(i.items())) for t, i in sorted(contratos.items())},
            "no_interpretados": no_interpretados}


def _pools(proyecto: Path) -> dict[str, dict]:
    pools: dict[str, dict] = {}
    for ruta in sorted((proyecto / BONITA / "app" / "diagrams").glob("*.proc")):
        rel = ruta.relative_to(proyecto).as_posix()
        raiz = _parsear(ruta, rel)
        for e in raiz.iter("elements"):
            if e.get(_XMI_TIPO) != "process:Pool":
                continue
            if not (e.get("name") and e.get("version") and e.get(_XMI_ID)):
                raise ValueError(f"{rel}: un pool sin nombre, versión o xmi:id")
            clave = f"{e.get('name')}@{e.get('version')}"
            if clave in pools:
                raise ValueError(f"El pool {clave} está en {pools[clave]['fichero']} y en {rel}")
            pools[clave] = leer_pool(raiz, e, rel)
    return dict(sorted(pools.items()))


def leer_existente(proyecto: Path) -> dict:
    """BDM, organización y pools de `proyecto` tal como están en disco. ValueError si un XML no es válido."""
    proyecto = Path(proyecto)
    return {"bdm": _bdm(proyecto), "organizacion": _organizacion(proyecto), "pools": _pools(proyecto)}
