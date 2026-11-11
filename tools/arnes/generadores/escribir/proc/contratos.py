"""Contratos del `.proc`: `process:Contract` con sus `ContractInput` (COMPLEX con hijos) y `ContractConstraint`
(nombre, expresión Groovy, mensaje e `inputNames`, como en el `.proc` del piloto).

`ContractInput` no tiene atributo de obligatoriedad en el modelo EMF 2026.2: cada input (o hijo de COMPLEX) con
`obligatorio` lleva una constraint `mandatory_<ruta>` (ruta unida con `_`), como las que genera el Studio (doc
`data/contracts-and-contexts.adoc`: «generates constraints for each mandatory field»; nombre
`mandatory_invoiceInput_customer`). La expresión recorre el COMPLEX con `?.`; en un COMPLEX múltiple, el hijo se
exige en cada elemento.

Plan 5 (hilo `contratos-documentos`, R-06): hijos COMPLEX anidados a cualquier profundidad (`[no verificado]` en el
motor más allá de dos niveles) y obligatoriedad propia por hijo (`obligatorio_propio`, forma «nombre (TIPO, sí)»),
con la semántica «si llega el padre, el hijo no es nulo» (`padre == null || padre.hijo != null`, en cada elemento de
un padre múltiple). Un hijo de primer nivel con la forma vieja conserva la expresión de antes. Los documentos de
instanciación (`proc/documentos.py`) se enlazan aquí con el `ContractInput` de su ruta."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc.datos import TIPOS_INPUT, comprobar_groovy, simbolos_usados
from generadores.escribir.proc.documentos import enlazar_documentos
from generadores.escribir.proc.ids import XMI_ID, elemento
from generadores.xmlutil import Ids


def entrada(padre: ET.Element, i: dict, ids: Ids, donde: str, rutas: dict[str, str], prefijo: str = "") -> ET.Element:
    """`inputs` de `padre` para el input `i` de la spec (y sus hijos, si es COMPLEX); anota en `rutas` el `xmi:id` de
    cada ruta (`padre.hijo`)."""
    if i.get("tipo") not in TIPOS_INPUT:
        raise ValueError(f"{donde}: el input «{i.get('nombre')}» tiene tipo «{i.get('tipo')}» desconocido "
                         f"({', '.join(TIPOS_INPUT)})")
    if (i["tipo"] == "COMPLEX") != bool(i.get("hijos")):
        raise ValueError(f"{donde}: el input «{i['nombre']}»: solo un COMPLEX tiene hijos, y siempre los tiene")
    e = elemento(padre, "inputs", "process:ContractInput", ids,
                 {"name": i["nombre"], "type": i["tipo"], "multiple": "true" if i.get("multiple") else None})
    rutas[f"{prefijo}{i['nombre']}"] = e.get(XMI_ID)
    for h in i.get("hijos", []):
        entrada(e, h, ids, f"{donde} › {i['nombre']}", rutas, f"{prefijo}{i['nombre']}.")
    return e


def contrato(padre: ET.Element, c: dict | None, ids: Ids, donde: str) -> ET.Element:
    """`contract` de una tarea humana o del pool (instanciación). `c` = {inputs, restricciones} de la spec."""
    c = c or {}
    e = elemento(padre, "contract", "process:Contract", ids)
    entradas = c.get("inputs", [])
    rutas: dict[str, str] = {}
    for i in entradas:
        entrada(e, i, ids, donde, rutas)
    enlazar_documentos(padre, rutas, donde)
    raices = [i["nombre"] for i in entradas]
    generadas = obligatorias(entradas)
    for r in c.get("restricciones", []):
        if any(r["nombre"] == o[0] for o in generadas):
            raise ValueError(f"{donde}: la constraint «{r['nombre']}» choca con la que se genera para un input "
                             "obligatorio; cámbiale el nombre")
        comprobar_groovy(r["groovy"], f"{donde} › {r['nombre']}")
        restriccion(e, r["nombre"], r["groovy"], r["mensaje"], simbolos_usados(r["groovy"], raices), ids)
    for nombre, expresion, mensaje, raiz in generadas:
        restriccion(e, nombre, expresion, mensaje, [raiz], ids)
    return e


def restriccion(padre: ET.Element, nombre: str, expresion: str, mensaje: str, raices: list[str],
                ids: Ids) -> ET.Element:
    """`constraints` de `padre` con su expresión, su mensaje y un `inputNames` por input raíz que usa."""
    k = elemento(padre, "constraints", "process:ContractConstraint", ids,
                 {"name": nombre, "expression": expresion, "errorMessage": mensaje})
    for n in raices:
        ET.SubElement(k, "inputNames").text = n
    return k


def obligatorias(entradas: list[dict]) -> list[tuple[str, str, str, str]]:
    """(nombre, expresión, mensaje, input raíz) de cada input o hijo obligatorio, en el orden del contrato."""
    out = []
    for i in entradas:
        raiz = i["nombre"]
        if i.get("obligatorio"):
            out.append((f"mandatory_{raiz}", f"{raiz} != null", f"{raiz} es obligatorio", raiz))
        for h in i.get("hijos", []):
            if h.get("obligatorio") and not h.get("obligatorio_propio"):
                # Forma vieja (hereda del padre): la expresión de siempre.
                if i.get("multiple"):
                    expresion = f"({raiz} ?: []).every {{ e -> e?.{h['nombre']} != null }}"
                else:
                    expresion = f"{raiz}?.{h['nombre']} != null"
                out.append((f"mandatory_{raiz}_{h['nombre']}", expresion, f"{raiz}.{h['nombre']} es obligatorio",
                            raiz))
            elif h.get("obligatorio"):
                out.append(_propia([i], h, raiz))
            out += _anidadas([i, h], raiz)
    return out


def _instancias(camino: list[dict]) -> str:
    """Expresión Groovy con la lista de instancias no nulas del último nodo de `camino` (raíz primero): un nodo
    múltiple aporta cada elemento."""
    raiz = camino[0]
    expr = f"({raiz['nombre']} ?: [])" if raiz.get("multiple") else f"[{raiz['nombre']}]"
    for n in camino[1:]:
        acceso = f"x?.{n['nombre']}"
        expr += (f".findAll {{ x -> x != null }}.collectMany {{ x -> {acceso} ?: [] }}" if n.get("multiple")
                 else f".findAll {{ x -> x != null }}.collect {{ x -> {acceso} }}")
    return expr


def _propia(camino: list[dict], h: dict, raiz: str) -> tuple[str, str, str, str]:
    """Constraint de un hijo con obligatoriedad propia: «si llega el padre, el hijo no es nulo»."""
    padre = camino[-1]
    ruta = ".".join(n["nombre"] for n in camino) + f".{h['nombre']}"
    if len(camino) == 1 and not padre.get("multiple"):
        expresion = f"{raiz} == null || {raiz}.{h['nombre']} != null"
    else:
        expresion = f"{_instancias(camino)}.every {{ p -> p == null || p.{h['nombre']} != null }}"
    return (f"mandatory_{ruta.replace('.', '_')}", expresion, f"{ruta} es obligatorio", raiz)


def _anidadas(camino: list[dict], raiz: str) -> list[tuple[str, str, str, str]]:
    """Las constraints de los hijos de un hijo COMPLEX (segundo nivel y siguientes): siempre con la semántica «si
    llega el padre» (la forma vieja no existía a esa profundidad)."""
    out = []
    for h in camino[-1].get("hijos", []):
        if h.get("obligatorio"):
            out.append(_propia(camino, h, raiz))
        out += _anidadas([*camino, h], raiz)
    return out
