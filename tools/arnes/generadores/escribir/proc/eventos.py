"""Timers de borde del `.proc`: `process:BoundaryTimerEvent` (interruptor) o `NonInterruptingBoundaryTimerEvent`
dentro de `BoundaryIntermediateEvents` de su anfitrión, nunca en la lane.

- Anfitrión: solo una tarea humana o una call activity (doc `process/events`: «You can set a boundary timer on a
  human task or a call activity»).
- Duración: un parámetro Integer del pool, en milisegundos. La condición es un script `return <param> as Long` con
  `returnType` `java.lang.Long`: bonita2bar 9.0.10 (EngineFlowElementBuilder.getTimerType) toma DURATION cuando el
  `returnType` es un `Number`, y el `as Long` evita depender de que el motor acepte un Integer en la duración
  (minor de Task 5) [no verificado en runtime; lo confirma el journey de Task 13].
- El evento de borde es `SourceElement` pero no `TargetElement`: tiene salidas y nunca entradas.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc.datos import Contexto
from generadores.escribir.proc.ids import elemento

ANFITRIONES = ("humana", "llamada")
CLASE_BORDE = {True: "process:BoundaryTimerEvent", False: "process:NonInterruptingBoundaryTimerEvent"}


def es_borde(nodo: dict) -> bool:
    return nodo["tipo"] == "timer_borde"


def bordes(nodos_: dict[str, ET.Element], proceso: dict, ctx: Contexto, documentacion) -> None:
    """Crea cada timer de borde dentro de su anfitrión (ya creado en `nodos_`) y lo añade a `nodos_`.
    `documentacion(nodo, donde)` valida y devuelve la documentación del nodo."""
    nombre = proceso["nombre"]
    tipo_de = {n["id"]: n["tipo"] for n in proceso["nodos"]}
    for n in filter(es_borde, proceso["nodos"]):
        donde = f"proceso «{nombre}» › {n['id']}"
        anfitrion = n.get("anfitrion")
        if anfitrion not in nodos_ or tipo_de.get(anfitrion) not in ANFITRIONES:
            raise ValueError(f"{donde}: el timer de borde va sobre una tarea humana o una call activity del pool, no "
                             f"sobre «{anfitrion}» ({tipo_de.get(anfitrion, 'no está en el pool')})")
        if not isinstance(n.get("interruptor"), bool):
            raise ValueError(f"{donde}: falta si el timer de borde es interruptor")
        param = ctx.params.get(n.get("duracion"))
        if param is None or param["tipo"] != "Integer":
            raise ValueError(f"{donde}: la duración «{n.get('duracion')}» debe ser un parámetro Integer del pool "
                             f"(milisegundos); parámetros: {', '.join(ctx.params) or 'ninguno'}")
        e = elemento(nodos_[anfitrion], "BoundaryIntermediateEvents", CLASE_BORDE[n["interruptor"]], ctx.ids,
                     {"documentation": documentacion(n, donde) or None, "name": n["nombre"]})
        ctx.script(e, "condition", f"duracion_{n['id']}()", f"return {param['nombre']} as Long", "java.lang.Long",
                   fijo=True)
        nodos_[n["id"]] = e
