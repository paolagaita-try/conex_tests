"""Form mapping del `.proc`: `URL` hacia la página del formulario (Svelte) o hacia la URL externa de la matriz;
`NONE` si el formulario es «No form» o la matriz no lo trae."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.aplicaciones import mapeo
from generadores.escribir.proc.ids import elemento
from generadores.xmlutil import Ids

NONE = ("NONE", None)
INSTANCIACION_PRINCIPAL = "frm_instanciacion"
OVERVIEW = "frm_overview"


def mapeos_del_proceso(formularios: dict | None, proceso: dict, principal: bool) -> dict:
    """`{"tareas": {id de nodo: (tipo, url)}, "instanciacion": (tipo, url), "overview": (tipo, url)}` de un pool.
    Instanciación: `frm_instanciacion` en el pool principal, `frm_instanciacion_<Pool>` en los demás; el overview
    (`frm_overview`) es del pool principal. Lo que la matriz no trae es `NONE`."""
    out = {"tareas": {}, "instanciacion": NONE, "overview": NONE}
    if not formularios:
        return out
    apps = formularios.get("aplicaciones", [])
    por_id = {f["id"]: f for f in formularios.get("formularios", [])}
    id_inst = INSTANCIACION_PRINCIPAL if principal else f"frm_instanciacion_{proceso['nombre']}"
    if id_inst in por_id:
        out["instanciacion"] = mapeo(por_id[id_inst], apps)
    if principal and OVERVIEW in por_id:
        out["overview"] = mapeo(por_id[OVERVIEW], apps)
    humanas = {n["id"] for n in proceso["nodos"] if n["tipo"] == "humana"}
    for f in formularios.get("formularios", []):
        if f["tipo"] == "Task form" and f["tarea"] in humanas:
            out["tareas"][f["tarea"]] = mapeo(f, apps)
    return out


def form_mapping(padre: ET.Element, tag: str, destino: tuple[str, str | None], ids: Ids) -> ET.Element:
    tipo, url = destino
    fm = elemento(padre, tag, "process:FormMapping", ids, {"type": tipo, "url": url})
    if url:
        elemento(fm, "targetForm", "expression:Expression", ids,
                 {"name": url, "content": url, "type": "CONSTANT", "returnType": "java.lang.String",
                  "returnTypeFixed": "true"})
    return fm
