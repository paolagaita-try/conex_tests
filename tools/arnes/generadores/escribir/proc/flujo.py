"""Flujo del `.proc`: nodos dentro de sus lanes y `SequenceFlow` entre ellos.

Salidas de una XOR (doc `process/gateways`: gana la primera condición verdadera): se conserva el orden de la
documentación en `connections` y en `outgoing`; la de por defecto lleva `isDefault="true"` y ninguna condición; una
salida no por defecto sin expresión es un error, nunca un `true` silencioso (Review Focus 2).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc import conectores, documentos, eventos, filtros
from generadores.escribir.proc.contratos import contrato
from generadores.escribir.proc.datos import INSTANCIACION, Contexto, comprobar_groovy
from generadores.escribir.proc.formularios import NONE, form_mapping
from generadores.escribir.proc.ids import XMI_ID, elemento
from generadores.escribir.proc.llamada import llamada
from generadores.xmlutil import Ids

# Nodos que van en una lane; los timers de borde cuelgan de su anfitrión (eventos.py).
CLASES = {"inicio": "process:StartEvent", "fin": "process:EndEvent", "humana": "process:Task",
          "script": "process:ScriptTask", "servicio": "process:ServiceTask", "xor": "process:XORGateway",
          "and": "process:ANDGateway", "llamada": "process:CallActivity"}
TIPOS = (*CLASES, "timer_borde")
FIN_TERMINATE = "process:EndTerminatedEvent"  # R-12 (clase de process.ecore 9.0.10)


def clase(n: dict) -> str:
    """Clase `process:*` de un nodo de una lane: la de su tipo, o `EndTerminatedEvent` si es un fin terminate."""
    return FIN_TERMINATE if n["tipo"] == "fin" and n.get("terminar") else CLASES[n["tipo"]]
CON_OPERACIONES = ("humana", "script", "servicio")
MAX_DOC = 255  # documentación de elementos: VARCHAR(255) en el runtime


def _vacia(padre: ET.Element, tag: str, ctx: Contexto) -> None:
    elemento(padre, tag, "expression:Expression", ctx.ids, {"name": "", "content": "", "returnTypeFixed": "true"})


def documentacion(n: dict, donde: str) -> str:
    doc = n.get("documentacion") or ""
    if len(doc) > MAX_DOC:
        raise ValueError(f"{donde}: la documentación tiene {len(doc)} caracteres; el máximo es {MAX_DOC}")
    return doc


def nodos(lanes: dict[str, ET.Element], proceso: dict, ctx: Contexto,
          procesos: list[dict] | None = None, version_bonita: str = "2026.2",
          mapeos: dict | None = None, extensiones: dict | None = None) -> dict[str, ET.Element]:
    """Crea cada nodo en su lane (orden de la spec) y, después, cada timer de borde en su anfitrión; devuelve id de
    spec -> elemento. `procesos` (todos los de la spec) sirve para comprobar el mapeo de las call activities;
    `version_bonita`, para los ids de los conectores; `mapeos` (formularios.mapeos_del_proceso), el form mapping de
    cada tarea humana (sin él, `NONE`); `extensiones` (`conectores.de_la_spec`), las definiciones propias y los
    filtros del proyecto."""
    nombre = proceso["nombre"]
    contratos = proceso.get("contratos", {})
    operaciones = proceso.get("operaciones", {})
    por_id = {n["id"]: n for n in proceso["nodos"]}
    for clave, ops in operaciones.items():
        if clave == INSTANCIACION or not ops:
            continue
        if por_id.get(clave, {}).get("tipo") not in CON_OPERACIONES:
            raise ValueError(f"proceso «{nombre}»: hay operaciones para «{clave}», que no es una tarea del pool")
    out = {}
    for n in proceso["nodos"]:
        if eventos.es_borde(n):
            continue
        donde = f"proceso «{nombre}» › {n['id']}"
        if n["lane"] not in lanes:
            raise ValueError(f"{donde}: la lane «{n['lane']}» no está en el pool ({', '.join(lanes)})")
        doc = documentacion(n, donde)
        tipo = n["tipo"]
        e = elemento(lanes[n["lane"]], "elements", clase(n), ctx.ids,
                     {"documentation": doc or None, "name": n["nombre"]})
        if tipo == "humana":
            e.set("overrideActorsOfTheLane", "false")
            e.set("priority", "1")
        for tag in ("dynamicLabel", "dynamicDescription", "stepSummary"):
            _vacia(e, tag, ctx)
        suyos = conectores.de_la_tarea(proceso, n["id"])
        if suyos and tipo not in CON_OPERACIONES:
            raise ValueError(f"{donde}: un conector solo va en una tarea ({', '.join(CON_OPERACIONES)})")
        if tipo in CON_OPERACIONES:
            c = contratos.get(n["id"]) if tipo == "humana" else None
            entradas = (c or {}).get("inputs", [])
            paso = ctx.con_entradas(entradas)
            for nombre_c, cn in suyos:
                # Antes de las operaciones (orden de features de Activity). Al entrar no hay contrato todavía.
                ctx_conector = paso if cn.get("momento") == "salida" else ctx.con_entradas([])
                conectores.conector(e, nombre_c, cn, ctx_conector, donde, version_bonita, extensiones)
            if tipo == "humana":
                # Actor filter (Assignable.filters): corre al crear la tarea, sin contrato.
                filtros.filtro(e, proceso, n, ctx.con_entradas([]), donde, extensiones)
                form_mapping(e, "formMapping", ((mapeos or {}).get("tareas") or {}).get(n["id"], NONE), ctx.ids)
                contrato(e, c, ctx.ids, donde)
            if tipo == "humana":  # R-09: las operaciones de documento van antes que las demás
                documentos.operaciones(e, proceso, n["id"], paso, entradas, donde)
            for op in operaciones.get(n["id"], []):
                paso.operacion(e, op, donde)
        if tipo == "llamada":
            llamada(e, n, ctx, procesos, donde)
        out[n["id"]] = e
    eventos.bordes(out, proceso, ctx, documentacion)
    return out


def secuencia(pool: ET.Element, origen: str, destino: str, ids: Ids, defecto: bool = False) -> ET.Element:
    """`connections` (`SequenceFlow`) de `pool` entre los `xmi:id` `origen` y `destino`, con su `decisionTable` vacío
    y sin condición (ver `condicion_vacia`); `isDefault="true"` si es la salida por defecto de una compuerta."""
    f = elemento(pool, "connections", "process:SequenceFlow", ids,
                 {"target": destino, "source": origen, "isDefault": "true" if defecto else None})
    elemento(f, "decisionTable", "decision:DecisionTable", ids)
    return f


def condicion_vacia(f: ET.Element, ids: Ids) -> None:
    """Condición vacía de una transición que no sale de una compuerta exclusiva."""
    elemento(f, "condition", "expression:Expression", ids,
             {"name": "", "returnType": "java.lang.Boolean", "returnTypeFixed": "true"})


def transiciones(pool: ET.Element, nodos_: dict[str, ET.Element], proceso: dict, ctx: Contexto) -> None:
    nombre = proceso["nombre"]
    tipo_de = {n["id"]: n["tipo"] for n in proceso["nodos"]}
    salen: dict[str, list[str]] = {}
    entran: dict[str, list[str]] = {}
    sin_inputs = ctx.con_entradas([])
    for t in proceso["transiciones"]:
        d, h = t["desde"], t["hacia"]
        donde = f"proceso «{nombre}» › transición {d}→{h}"
        for x in (d, h):
            if x not in nodos_:
                raise ValueError(f"{donde}: «{x}» no es un nodo del pool")
        if tipo_de[h] == "timer_borde":
            raise ValueError(f"{donde}: «{h}» es un timer de borde; no tiene entradas")
        expr, defecto = t.get("expresion"), bool(t.get("defecto"))
        f = secuencia(pool, nodos_[d].get(XMI_ID), nodos_[h].get(XMI_ID), ctx.ids, defecto)
        if tipo_de[d] == "xor":
            if defecto and expr:
                raise ValueError(f"{donde}: la salida por defecto no lleva condición")
            if not defecto:
                if not (expr or "").strip():  # una condición en blanco no es una condición
                    raise ValueError(f"{donde}: salida de una compuerta exclusiva sin condición ni «(por defecto)»")
                comprobar_groovy(expr, donde)
                sin_inputs.script(f, "condition", f"condicion_{d}_{h}()", expr, "java.lang.Boolean", fijo=True)
        else:
            if expr or defecto:
                raise ValueError(f"{donde}: solo las salidas de una compuerta exclusiva llevan condición o defecto")
            condicion_vacia(f, ctx.ids)
        salen.setdefault(d, []).append(f.get(XMI_ID))
        entran.setdefault(h, []).append(f.get(XMI_ID))
    for nid, e in nodos_.items():
        if nid in entran:
            e.set("incoming", " ".join(entran[nid]))
        if nid in salen:
            e.set("outgoing", " ".join(salen[nid]))
