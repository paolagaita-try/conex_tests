"""Generador de la configuración de proceso (`.conf`): mapeo de actores y valores de los parámetros del entorno
(Local en esta etapa)."""
import xml.etree.ElementTree as ET

from generadores.escribir.organizacion import actor_bonita
from generadores.escribir.proc.conectores import mapeos as mapeos_de_conectores
from generadores.escribir.proc.filtros import mapeos as mapeos_de_filtros
from generadores.escribir.proc.datos import CLASE_PARAMETRO

NS_CONF = "http://www.bonitasoft.org/ns/bpm/configuration"


def _actores_del_proceso(proceso: dict, organizacion: dict) -> list[tuple[str, dict]]:
    """(nombre del actor Bonita, mapeo) de cada actor del proceso, en el orden del `.proc`: los de las lanes (su Actor
    Bonita, sin las lanes sin actor) y después los de nivel tarea. Mapeo = `{"grupo", "roles", "membresias"}`: el de
    una lane sale de su actor de negocio en `organizacion["actores"]` (una membresía por rol con su grupo); el de un
    actor de tarea, de su Mapeo (roles en cualquier grupo y membresías)."""
    vistos: dict[str, dict] = {}
    for lane in proceso["lanes"]:
        nombre = actor_bonita(lane)
        if nombre is None or nombre in vistos:
            continue
        destino = organizacion["actores"].get(lane["actor"])
        if destino is None:
            raise ValueError(f"el actor {lane['actor']} del proceso {proceso['nombre']} no está en organizacion.actores")
        grupo, roles = destino.get("grupo"), destino.get("roles") or [destino.get("rol")]
        roles = [r for r in roles if r]
        if not grupo and not roles:
            raise ValueError(f"el actor {lane['actor']} no tiene ni grupo ni rol en organizacion.actores")
        if grupo and roles:
            vistos[nombre] = {"grupo": None, "roles": [], "membresias": [{"grupo": grupo, "rol": r} for r in roles]}
        else:
            vistos[nombre] = {"grupo": grupo, "roles": roles, "membresias": []}
    for a in proceso.get("actores_tarea", []):
        if a["nombre"] not in vistos:
            vistos[a["nombre"]] = {"grupo": None, "roles": list(a.get("roles", [])),
                                   "membresias": list(a.get("membresias", []))}
    return list(vistos.items())


def generar_conf(proceso: dict, organizacion: dict, entorno: str = "Local",
                 version_bonita: str = "2026.2", extensiones: dict | None = None) -> ET.ElementTree:
    """`.conf` versión 9 con un `actorMapping` por actor del proceso (`_actores_del_proceso`: los de las lanes con
    actor y los de nivel tarea). Con grupo y roles, una `membership` por rol con `<group>/ruta</group><role>rol</role>`
    (la ruta completa del grupo); solo rol -> `role`; solo grupo -> `group` `/ruta`; un actor de tarea, sus `role` y
    sus `membership`.
    Cada definición de conector que usa el proceso lleva su `definitionMappings` hacia la implementación (ids de
    `versiones/<version_bonita>.json`), con `type="CONNECTOR"` en MAYÚSCULAS: bonita2bar compara ese literal y, con
    otro, el `.impl` no entra al `.bar` y el proceso queda «unresolved» (D-14 del piloto). Los conectores y filtros
    propios (`extensiones`, Plan 5) toman ids y versiones de su `.def`/`.impl`; los filtros van con
    `type="ACTOR_FILTER"`, el otro literal de bonita2bar.
    Cada parámetro del pool lleva su valor del entorno en `parameters` (`Configuration.parameters` de
    `configuration.ecore`; bonita2bar lo busca por nombre y lo convierte con la clase del parámetro)."""
    raiz = ET.Element("configuration:Configuration",
                      {"xmlns:configuration": NS_CONF, "name": entorno, "version": "9"})
    mapeos = ET.SubElement(raiz, "actorMappings")
    for actor, mapeo in _actores_del_proceso(proceso, organizacion):
        nodo = ET.SubElement(mapeos, "actorMapping", {"name": actor})
        grupos = ET.SubElement(nodo, "groups")
        membresias = ET.SubElement(nodo, "memberships")
        roles = ET.SubElement(nodo, "roles")
        ET.SubElement(nodo, "users")
        for m_ in mapeo["membresias"]:
            m = ET.SubElement(membresias, "membership")
            ET.SubElement(m, "group").text = f"/{m_['grupo']}"
            ET.SubElement(m, "role").text = m_["rol"]
        for r in mapeo["roles"]:
            ET.SubElement(roles, "role").text = r
        if mapeo["grupo"]:
            ET.SubElement(grupos, "group").text = f"/{mapeo['grupo']}"
    # Orden de features de Configuration: actorMappings, definitionMappings, processDependencies, parameters.
    for d in mapeos_de_conectores(proceso, version_bonita, extensiones):
        ET.SubElement(raiz, "definitionMappings", {"type": "CONNECTOR", **d})
    for d in mapeos_de_filtros(proceso, extensiones):
        ET.SubElement(raiz, "definitionMappings", {"type": "ACTOR_FILTER", **d})
    for id_ in ("CONNECTOR", "ACTOR_FILTER", "OTHER"):
        ET.SubElement(raiz, "processDependencies", {"id": id_})
    for p in proceso.get("parametros", []):
        valor = (p.get("valores") or {}).get(entorno)
        if valor is None or valor == "":
            raise ValueError(f"el parámetro {p['nombre']} del proceso {proceso['nombre']} no tiene valor en {entorno}")
        if p.get("tipo") not in CLASE_PARAMETRO:
            raise ValueError(f"el parámetro {p['nombre']} tiene tipo {p.get('tipo')} no soportado "
                             f"({', '.join(CLASE_PARAMETRO)})")
        ET.SubElement(raiz, "parameters", {"name": p["nombre"], "value": valor,
                                           "typeClassname": CLASE_PARAMETRO[p["tipo"]]})
    return ET.ElementTree(raiz)
