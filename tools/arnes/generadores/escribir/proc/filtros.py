"""Actor filters propios en las tareas humanas del `.proc` (Plan 5, R-03) y su mapeo en el `.conf`.

Un filtro es una extensión del proyecto (`.def`/`.impl` escritos a mano en `bonita-project/extensions/<modulo>/`,
leídos por `generadores.leer.extensiones`); el arnés no genera su código. Aquí se escribe, en cada tarea humana con
filtro, un `filters` de clase `process:ActorFilter` (que extiende `Connector`; `Assignable.filters` de process.ecore
9.0.10: lanes y tareas lo admiten) con su `ConnectorConfiguration` y un `ConnectorParameter` por entrada (el Groovy de
`expresiones.md`, `flt_<filtro>.<entrada>`, con el `type` de su `<input>` en el `.def` como tipo de retorno).

Por qué en la tarea y no en la lane: el filtro efectivo de una tarea es el de su actor de tarea si lo tiene y, si
no, el de su lane (`filtro_de_tarea`). bonita2bar 9.0.10 (`EngineFlowElementBuilder.caseTask`, leído con `javap`)
toma el primer filtro de la tarea y solo si la tarea no tiene ninguno el de su lane, con `overrideActorsOfTheLane`
o sin él; escribirlo siempre en la tarea da el mismo resultado sin depender de esa regla.

El `.conf` lleva un `definitionMappings type="ACTOR_FILTER"` por definición distinta: es el literal que compara
bonita2bar (`ConnectorImplementationArtifactProvider`, junto a `CONNECTOR`) para meter el `.impl` en el `.bar`.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc.conectores import definicion_propia, mapeo_propio
from generadores.escribir.proc.datos import Contexto, comprobar_groovy
from generadores.escribir.proc.ids import elemento


def filtro_de_tarea(proceso: dict, nodo: dict) -> str | None:
    """ID del filtro efectivo de una tarea humana: el de su actor de tarea (`actores_tarea`, aunque sea ninguno) y,
    si la tarea no tiene actor de tarea, el de su lane (`lanes[i].filtro`). `None` si no tiene."""
    if nodo.get("tipo") != "humana":
        return None
    for a in proceso.get("actores_tarea", []):
        if nodo.get("id") in (a.get("tareas") or []):
            return a.get("filtro") or None
    lane = next((l for l in proceso.get("lanes", []) if l.get("nombre") == nodo.get("lane")), None)
    return (lane or {}).get("filtro") or None


def filtros_del_proceso(proceso: dict) -> dict[str, list[str]]:
    """filtro -> tareas humanas del proceso a las que se aplica, en el orden de los nodos."""
    out: dict[str, list[str]] = {}
    for n in proceso.get("nodos", []):
        f = filtro_de_tarea(proceso, n)
        if f:
            out.setdefault(f, []).append(n["id"])
    return out


def _filtro(id_: str, extensiones: dict | None, donde: str) -> dict:
    f = ((extensiones or {}).get("filtros") or {}).get(id_)
    if f is None:
        raise ValueError(f"{donde}: el actor filter «{id_}» no está declarado en bdm.md › Organización (tabla "
                         "«Actor filter»)")
    return f


def validar(proceso: dict, extensiones: dict | None = None) -> None:
    """Cada filtro que usa el proceso está declarado y su definición está en el proyecto."""
    for id_, tareas in filtros_del_proceso(proceso).items():
        donde = f"proceso «{proceso['nombre']}» › {tareas[0]} › filtro «{id_}»"
        definicion_propia(_filtro(id_, extensiones, donde).get("definicion"), extensiones, donde)


def filtro(tarea: ET.Element, proceso: dict, nodo: dict, ctx: Contexto, donde: str,
           extensiones: dict | None = None) -> None:
    """`filters` de la tarea humana `nodo` si tiene filtro efectivo. `ctx` sin inputs de contrato: el filtro corre al
    crear la tarea, antes de que nadie la ejecute (ve business y process variables y parámetros)."""
    id_ = filtro_de_tarea(proceso, nodo)
    if id_ is None:
        return
    donde = f"{donde} › filtro «{id_}»"
    f = _filtro(id_, extensiones, donde)
    def_id = f.get("definicion")
    d = definicion_propia(def_id, extensiones, donde)
    tipos = {i["nombre"]: i["tipo"] for i in d["entradas"]}
    e = elemento(tarea, "filters", "process:ActorFilter", ctx.ids,
                 {"name": id_, "definitionId": def_id, "definitionVersion": d["version"]})
    conf = elemento(e, "configuration", "connectorconfiguration:ConnectorConfiguration", ctx.ids,
                    {"definitionId": def_id, "version": d["version"], "name": id_})
    for clave, groovy in (f.get("entradas") or {}).items():
        if clave not in tipos:
            raise ValueError(f"{donde}: «{clave}» no es una entrada de la definición «{def_id}» ({', '.join(tipos)})")
        if not groovy:
            raise ValueError(f"{donde}: falta el Groovy de la entrada «{clave}»")
        comprobar_groovy(groovy, f"{donde} › {clave}")
        p = elemento(conf, "parameters", "connectorconfiguration:ConnectorParameter", ctx.ids, {"key": clave})
        ctx.script(p, "expression", f"{clave}_{id_}()", groovy, tipos[clave], fijo=True)


def mapeos(proceso: dict, extensiones: dict | None = None) -> list[dict]:
    """Un mapeo definición → implementación por definición distinta de los filtros del proceso, en orden."""
    out: list[dict] = []
    for id_, tareas in filtros_del_proceso(proceso).items():
        donde = f"proceso «{proceso['nombre']}» › {tareas[0]} › filtro «{id_}»"
        def_id = _filtro(id_, extensiones, donde).get("definicion")
        m = mapeo_propio(def_id, definicion_propia(def_id, extensiones, donde))
        if m not in out:
            out.append(m)
    return out
