"""Parte `notation:Diagram` del `.proc`: una vista por elemento (el build falla con «No Diagram found» sin ella y con
«No view found for Pool» si está vacía; aprendizaje 1 del Plan 1) y una disposición legible al abrirlo en el Studio.

Tipos de vista: los del editor 2026.2 (`conocimiento/ids-visuales-2026.2.json`); los nodos dentro de una lane usan
las edit parts `<Clase>2` y su etiqueta `<Clase>Label2`/`<Clase>Name2`. Un timer de borde es una `notation:Shape`
hija de la Shape de su anfitrión (como los border items del editor), con el tipo que el Studio usa para ese
anfitrión (`ids.vista_de_borde`: 3043 sobre una tarea humana, 3044 sobre una call activity).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc.ids import XMI_ID, XMI_TYPE, elemento, q, vista, vista_de_borde, vista_en_lane
from generadores.xmlutil import Ids

# Tamaños por tipo de nodo: `plantillas-xml-bonita.md` §5.4 del piloto.
TAMANOS = {"inicio": (30, 30), "fin": (30, 30), "timer_borde": (30, 30), "humana": (128, 64), "script": (128, 64),
           "servicio": (128, 64), "llamada": (128, 64), "xor": (43, 43), "and": (43, 43)}
COLUMNA = 180       # ancho de una columna (nodo más hueco hasta la siguiente)
CELDA = 128         # ancho útil de la columna: los nodos se centran en ella
FILA = 100          # alto de una fila dentro de una lane
MARGEN_X = 60       # deja libre la cabecera de la lane
MARGEN_Y = 20
ALTO_MIN_LANE = 140
_CON_ETIQUETA_EXTERNA = ("inicio", "fin", "timer_borde", "xor", "and")  # su etiqueta lleva Location (Studio)


def _columnas(proceso: dict) -> dict[str, int]:
    """Columna de cada nodo: el camino más largo desde el inicio en el grafo sin aristas de vuelta (las que cierran
    un ciclo en un recorrido en profundidad desde el inicio). Un nodo de borde va en la columna de su anfitrión."""
    nodos = [n["id"] for n in proceso["nodos"]]
    sucesores: dict[str, list[str]] = {n: [] for n in nodos}
    for t in proceso["transiciones"]:
        sucesores[t["desde"]].append(t["hacia"])
    anfitrion = {n["id"]: n["anfitrion"] for n in proceso["nodos"] if n.get("anfitrion")}
    for borde, host in anfitrion.items():
        sucesores[host].append(borde)
    raices = [n["id"] for n in proceso["nodos"] if n["tipo"] == "inicio"] + nodos
    vuelta: set[tuple[str, str]] = set()
    estado: dict[str, int] = {}  # 1 = en la pila, 2 = cerrado

    def dfs(n: str) -> None:
        estado[n] = 1
        for s in sucesores[n]:
            if estado.get(s) == 1:
                vuelta.add((n, s))
            elif s not in estado:
                dfs(s)
        estado[n] = 2

    for r in raices:
        if r not in estado:
            dfs(r)
    entradas = {n: 0 for n in nodos}
    for n in nodos:
        for s in sucesores[n]:
            if (n, s) not in vuelta:
                entradas[s] += 1
    columna = {n: 0 for n in nodos}
    pendientes = [n for n in nodos if entradas[n] == 0]
    while pendientes:
        n = pendientes.pop(0)
        for s in sucesores[n]:
            if (n, s) in vuelta:
                continue
            paso = 0 if anfitrion.get(s) == n else 1
            columna[s] = max(columna[s], columna[n] + paso)
            entradas[s] -= 1
            if entradas[s] == 0:
                pendientes.append(s)
    return columna


def disponer(proceso: dict) -> dict[str, tuple[int, int, int, int]]:
    """(x, y, ancho, alto) de cada nodo, relativos a su lane: columna = orden topológico desde el inicio, fila =
    lane; dos nodos de la misma lane en la misma columna se apilan. Un timer de borde va relativo a su anfitrión,
    montado sobre su borde inferior derecho, y no ocupa sitio en la lane."""
    columna = _columnas(proceso)
    ocupadas: dict[tuple[str, int], int] = {}
    out = {}
    tamano = {n["id"]: TAMANOS[n["tipo"]] for n in proceso["nodos"]}
    for n in proceso["nodos"]:
        ancho, alto = TAMANOS[n["tipo"]]
        if n["tipo"] == "timer_borde":
            w, h = tamano[n["anfitrion"]]
            out[n["id"]] = (w - ancho - 15, h - alto // 2, ancho, alto)
            continue
        clave = (n["lane"], columna[n["id"]])
        sub = ocupadas.get(clave, 0)
        ocupadas[clave] = sub + 1
        x = MARGEN_X + columna[n["id"]] * COLUMNA + (CELDA - ancho) // 2
        y = MARGEN_Y + sub * FILA + (FILA - alto) // 2
        out[n["id"]] = (x, y, ancho, alto)
    return out


def _nodo(padre: ET.Element, tag: str, tipo_xmi: str, tipo_vista: str, ids: Ids, elem: str | None = None,
          extra: dict | None = None) -> ET.Element:
    n = elemento(padre, tag, tipo_xmi, ids, {"type": tipo_vista, "element": elem})
    for k, v in (extra or {}).items():
        n.set(k, v)
    return n


def _estilos(n: ET.Element, ids: Ids) -> None:
    elemento(n, "styles", "notation:DescriptionStyle", ids)
    elemento(n, "styles", "notation:FontStyle", ids)
    elemento(n, "styles", "notation:LineStyle", ids, {"lineColor": "12632256"})
    elemento(n, "styles", "notation:FillStyle", ids)


def _borde(padre: ET.Element, e: ET.Element, anfitrion: ET.Element, pos: tuple[int, int, int, int],
           ids: Ids) -> str:
    """Shape del evento de borde `e` hija de la Shape `padre` de su `anfitrion`; devuelve su `xmi:id`."""
    tipo_vista, etiqueta = vista_de_borde(e.get(XMI_TYPE).split(":")[1], anfitrion.get(XMI_TYPE).split(":")[1])
    s = _nodo(padre, "children", "notation:Shape", tipo_vista, ids, e.get(XMI_ID))
    dn = _nodo(s, "children", "notation:DecorationNode", etiqueta, ids)
    elemento(dn, "layoutConstraint", "notation:Location", ids, {"y": "5"})
    x, y, w, h = pos
    elemento(s, "layoutConstraint", "notation:Bounds", ids, {"x": str(x), "y": str(y), "width": str(w), "height": str(h)})
    return s.get(XMI_ID)


def figura(comp: ET.Element, e: ET.Element, tipo: str, ids: Ids) -> ET.Element:
    """`notation:Shape` del nodo `e` (de tipo de spec `tipo`) dentro del compartimento `comp` de su lane, con su
    etiqueta. Sin `Bounds`: van al final, tras las figuras de los eventos de borde (ver `limites`)."""
    tipo_vista, etiqueta = vista_en_lane(e.get(XMI_TYPE).split(":")[1])
    colores = {} if tipo in _CON_ETIQUETA_EXTERNA else {"fillColor": "14334392", "lineColor": "10710316"}
    s = _nodo(comp, "children", "notation:Shape", tipo_vista, ids, e.get(XMI_ID), colores)
    dn = _nodo(s, "children", "notation:DecorationNode", etiqueta, ids)
    if tipo in _CON_ETIQUETA_EXTERNA:
        elemento(dn, "layoutConstraint", "notation:Location", ids, {"y": "5"})
    return s


def limites(s: ET.Element, pos: tuple[int, int, int, int], ids: Ids) -> None:
    """`Bounds` (x, y, ancho, alto) de la figura `s`, relativos a su lane."""
    x, y, w, h = pos
    elemento(s, "layoutConstraint", "notation:Bounds", ids,
             {"x": str(x), "y": str(y), "width": str(w), "height": str(h)})


def conector(d: ET.Element, flujo: str, origen: str, destino: str, ids: Ids) -> ET.Element:
    """`notation:Connector` del diagrama `d` para la transición `flujo`, entre las figuras `origen` y `destino`."""
    a = elemento(d, "edges", "notation:Connector", ids,
                 {"type": vista("SequenceFlow"), "element": flujo, "source": origen, "target": destino,
                  "roundedBendpointsRadius": "10", "routing": "Rectilinear", "lineColor": "12632256"})
    dn = _nodo(a, "children", "notation:DecorationNode", vista("SequenceFlowName"), ids)
    elemento(dn, "layoutConstraint", "notation:Location", ids, {"y": "-10"})
    elemento(a, "styles", "notation:FontStyle", ids)
    elemento(a, "bendpoints", "notation:RelativeBendpoints", ids, {"points": "[0, 0, 0, 0]$[0, 0, 0, 0]"})
    return a


def dibujar(raiz: ET.Element, main: ET.Element, pool: ET.Element, lanes: list[tuple[ET.Element, list[str]]],
            nodos: dict[str, ET.Element], proceso: dict, ids: Ids) -> None:
    """Añade a `raiz` el `notation:Diagram`. `lanes`: (elemento Lane, ids de spec de sus nodos); `nodos`: id de
    spec -> elemento del nodo."""
    pos = disponer(proceso)
    tipo_de = {n["id"]: n["tipo"] for n in proceso["nodos"]}
    bordes_de: dict[str, list[str]] = {}
    for n in proceso["nodos"]:
        if n["tipo"] == "timer_borde":
            bordes_de.setdefault(n["anfitrion"], []).append(n["id"])
    d = ET.SubElement(raiz, q("notation", "Diagram"))
    d.set(XMI_ID, ids.siguiente())
    for k, v in (("type", "Process"), ("element", main.get(XMI_ID)), ("name", main.get("name")),
                 ("measurementUnit", "Pixel")):
        d.set(k, v)
    ancho = max([MARGEN_X + COLUMNA] + [x + w for x, _, w, _ in pos.values()]) + MARGEN_X
    vp = _nodo(d, "children", "notation:Node", vista("Pool"), ids, pool.get(XMI_ID))
    _nodo(vp, "children", "notation:DecorationNode", vista("PoolName"), ids)
    comp_pool = _nodo(vp, "children", "notation:DecorationNode", vista("PoolPoolCompartment"), ids)
    forma: dict[str, str] = {}
    alto_total = 0
    for lane, ids_nodos in lanes:
        vl = _nodo(comp_pool, "children", "notation:Node", vista("Lane"), ids, lane.get(XMI_ID))
        _nodo(vl, "children", "notation:DecorationNode", vista("LaneName"), ids)
        comp = _nodo(vl, "children", "notation:DecorationNode", vista("LaneLaneCompartment"), ids)
        alto = ALTO_MIN_LANE
        for nid in ids_nodos:
            e = nodos[nid]
            s = figura(comp, e, tipo_de[nid], ids)
            for b in bordes_de.get(nid, []):
                forma[b] = _borde(s, nodos[b], e, pos[b], ids)
            limites(s, pos[nid], ids)
            forma[nid] = s.get(XMI_ID)
            x, y, w, h = pos[nid]
            alto = max(alto, y + h + MARGEN_Y + (FILA - h) // 2)
        _estilos(vl, ids)
        elemento(vl, "layoutConstraint", "notation:Bounds", ids, {"width": str(ancho - 30), "height": str(alto)})
        alto_total += alto
    _estilos(vp, ids)
    elemento(vp, "layoutConstraint", "notation:Bounds", ids, {"width": str(ancho), "height": str(alto_total)})
    elemento(d, "styles", "notation:DiagramStyle", ids)

    por_xmi = {e.get(XMI_ID): nid for nid, e in nodos.items()}
    for f in pool.findall("connections"):
        conector(d, f.get(XMI_ID), forma[por_xmi[f.get("source")]], forma[por_xmi[f.get("target")]], ids)
