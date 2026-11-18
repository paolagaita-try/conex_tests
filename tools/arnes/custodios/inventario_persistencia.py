"""Inventario del hilo `persistencia` (Plan 5, R-08): las business variables del pool contra el `.proc`, 1:1.

- `bdm.md › Decisión de persistencia › Business variables del pool` (lector `leer_bdm`) son las del pool principal
  (frontmatter `pool` de `bpmn.md`); los demás pools no tienen business variables.
- En el `.proc`, cada `data` de tipo `process:BusinessObjectData` del pool: nombre, objeto (`className` sin el
  paquete) y multiplicidad (`multiple="true"`).

Lo llama `custodios/check_inventario.py` (módulos `inventario_*`). Como el resto del inventario, lee los dos lados
por su cuenta: la documentación con los lectores, los artefactos del XML escrito.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from custodios import docs_de_procesos_nuevos, leer_doc, pools_existentes
from generadores.leer.bdm import leer_bdm
from generadores.leer.bpmn import leer_bpmn

XMI = "{http://www.omg.org/XMI}"
MAIN = "{http://www.bonitasoft.org/ns/bpm/process}MainProcess"
BV = "bdm.md › Decisión de persistencia › Business variables del pool"


def _xml(proyecto: Path) -> dict[str, tuple[str, dict[str, tuple[str, bool]]]]:
    """pool -> (fichero, {bv: (objeto, múltiple)})."""
    out = {}
    for f in sorted((proyecto / "bonita-project" / "app" / "diagrams").glob("*.proc")):
        main = ET.parse(f).getroot().find(MAIN)
        for pool in main.findall("elements"):
            datos = {d.get("name"): ((d.get("className") or "").rsplit(".", 1)[-1], d.get("multiple") == "true")
                     for d in pool.findall("data") if d.get(f"{XMI}type") == "process:BusinessObjectData"}
            out[pool.get("name")] = (f.name, datos)
    return out


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    if not docs_de_procesos_nuevos(proyecto):
        return []
    bdm, err_b = leer_bdm(leer_doc(proyecto, "07-bonita/bdm.md"))
    bpmn, err_p = leer_bpmn(leer_doc(proyecto, "07-bonita/bpmn.md"))
    hallazgos = [f"bdm.md: {e}" for e in err_b] + [f"bpmn.md: {e}" for e in err_p]
    principal = bpmn["principal"]["nombre"]
    doc = {b["nombre"]: (b["objeto"], bool(b.get("multiple"))) for b in bdm["persistencia"]["business_variables"]}
    existentes = pools_existentes(proyecto)  # modo existente: lo existente no se contrasta con bdm.md
    for pool, (fichero, xml) in sorted(_xml(proyecto).items()):
        if pool in existentes:
            continue
        u = f"{fichero} › {pool}"
        esperadas = doc if pool == principal else {}
        for n in sorted(esperadas.keys() - xml.keys()):
            hallazgos.append(f"{u}: falta en el .proc la business variable «{n}» que pide {BV}")
        for n in sorted(xml.keys() - esperadas.keys()):
            donde = BV if pool == principal else "bdm.md (solo el pool principal tiene business variables)"
            hallazgos.append(f"{u}: la business variable «{n}» del .proc no está en {donde}")
        for n in sorted(esperadas.keys() & xml.keys()):
            (o_d, m_d), (o_x, m_x) = esperadas[n], xml[n]
            if o_d != o_x:
                hallazgos.append(f"{u}: la business variable «{n}» es de «{o_x}» en el .proc y de «{o_d}» en bdm.md")
            if m_d != m_x:
                hallazgos.append(f"{u}: la business variable «{n}» es {'múltiple' if m_x else 'simple'} en el .proc "
                                 f"y {'múltiple' if m_d else 'simple'} en bdm.md («(múltiple)» tras el token)")
    return hallazgos
