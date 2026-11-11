"""Piezas comunes del `.proc`: espacios de nombres, creación de elementos con `xmi:type`/`xmi:id` y tipos de vista
del editor (`conocimiento/ids-visuales-<version>.json`, medidos del jar del Studio en Task 2)."""
import functools
import json
import xml.etree.ElementTree as ET

from generadores.version import RAIZ_REPO
from generadores.xmlutil import Ids

NS = {
    "xmi": "http://www.omg.org/XMI",
    "process": "http://www.bonitasoft.org/ns/bpm/process",
    "notation": "http://www.eclipse.org/gmf/runtime/1.0.3/notation",
    "expression": "http://www.bonitasoft.org/ns/bpm/expression",
    "decision": "http://www.bonitasoft.org/ns/bpm/process/decision",
    "parameter": "http://www.bonitasoft.org/ns/bpm/parameter",
    "connectorconfiguration": "http://www.bonitasoft.org/model/connector/configuration",
}
for _p, _u in NS.items():
    ET.register_namespace(_p, _u)
# Prefijos que solo aparecen dentro de valores (xmi:type="expression:Expression"): ElementTree no los declara por su
# cuenta y EMF falla con «Class 'Expression' is not found» (aprendizaje 2 del Plan 1). `parameter` es el de los
# parámetros del pool y de sus referencias en los scripts (`xmi:type="parameter:Parameter"`); `connectorconfiguration`
# el de la configuración de los conectores (`connectorconfiguration:ConnectorConfiguration`, como en el piloto).
SOLO_EN_VALORES = ("expression", "decision", "parameter", "connectorconfiguration")


def q(prefijo: str, nombre: str) -> str:
    return f"{{{NS[prefijo]}}}{nombre}"


XMI_ID = q("xmi", "id")
XMI_TYPE = q("xmi", "type")


def elemento(padre: ET.Element, tag: str, tipo: str | None, ids: Ids, attrs: dict | None = None) -> ET.Element:
    """Hijo `tag` con `xmi:type` (si lo hay), un `xmi:id` nuevo y los atributos dados, en ese orden. Los atributos
    con valor None no se escriben."""
    e = ET.SubElement(padre, tag)
    if tipo:
        e.set(XMI_TYPE, tipo)
    e.set(XMI_ID, ids.siguiente())
    for k, v in (attrs or {}).items():
        if v is not None:
            e.set(k, v)
    return e


@functools.cache
def ids_visuales(version: str = "2026.2") -> dict[str, int]:
    """Clase de edit part del editor -> VISUAL_ID (p. ej. `Task2` = tarea dentro de una lane)."""
    ruta = RAIZ_REPO / "conocimiento" / f"ids-visuales-{version}.json"
    return json.loads(ruta.read_text(encoding="utf-8"))["ids"]


def vista_en_lane(clase: str) -> tuple[str, str]:
    """(tipo del `notation:Shape` de un nodo `clase` dentro de una lane, tipo de su etiqueta)."""
    ids = ids_visuales()
    etiqueta = ids.get(f"{clase}Label2") or ids.get(f"{clase}Name2")
    if f"{clase}2" not in ids or etiqueta is None:
        raise KeyError(f"ids-visuales: no hay vista en lane para {clase} ({clase}2 y {clase}Label2/{clase}Name2)")
    return str(ids[f"{clase}2"]), str(etiqueta)


# Vista de un evento de borde según su anfitrión (ProcessVisualIDRegistry.getNodeVisualID del Studio 2026.2: dentro
# de Task2 (3005) un BoundaryTimerEvent es 3043 y un NonInterruptingBoundaryTimerEvent 3064; dentro de CallActivity2
# (3063), 3044 y 3065). Sufijo de la edit part por clase del anfitrión.
_SUFIJO_BORDE = {"Task": "", "CallActivity": "2"}


def vista_de_borde(clase: str, anfitrion: str) -> tuple[str, str]:
    """(tipo del `notation:Shape` de un evento de borde `clase` hijo de la vista de su `anfitrion`, tipo de su
    etiqueta)."""
    ids = ids_visuales()
    if anfitrion not in _SUFIJO_BORDE:
        raise KeyError(f"ids-visuales: no hay vista de borde sobre {anfitrion} ({', '.join(_SUFIJO_BORDE)})")
    s = _SUFIJO_BORDE[anfitrion]
    etiqueta = ids.get(f"{clase}Label{s}") or ids.get(f"{clase}Name{s}")
    if f"{clase}{s}" not in ids or etiqueta is None:
        raise KeyError(f"ids-visuales: no hay vista de {clase} sobre {anfitrion}")
    return str(ids[f"{clase}{s}"]), str(etiqueta)


def vista(clave: str) -> str:
    """VISUAL_ID de una edit part por su nombre exacto (`Pool`, `PoolName`, `LaneLaneCompartment`…)."""
    return str(ids_visuales()[clave])
