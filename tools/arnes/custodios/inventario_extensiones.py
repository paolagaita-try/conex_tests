"""Inventario del hilo `extensiones` (Plan 5, R-03 y R-10): conectores y actor filters de `bpmn.md` ↔ cada `.proc`.

- Conectores: **una fila por invocación**. Por tarea, el multiconjunto de (nombre en el `.proc`, definición, momento,
  `ignoreErrors`) de la tabla «Conectores por tarea» es el de los `connectors` de la tarea en el `.proc`. El nombre
  esperado sigue la regla del generador (`conectores.de_la_tarea`: el ID, o `<ID>_<n>` si la tarea lo invoca varias
  veces); la definición de un REST GET es `rest-get`, la de un propio la de su celda.
- Filtros: por tarea humana, el filtro efectivo de la documentación (actor de tarea o lane, `filtro_de_tarea`) es el
  `filters` de la tarea en el `.proc` (ninguno = ninguno).

Lee la documentación con los lectores y el `.proc` como XML; los errores de lectura de `bpmn.md` ya los informa
`check_inventario`, aquí no se repiten. Lo invoca `check_inventario.comprobar` (A0.3).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from custodios import leer_doc
from generadores.escribir.proc.conectores import MOMENTOS, de_la_tarea
from generadores.escribir.proc.filtros import filtro_de_tarea
from generadores.escribir.proc.flujo import CLASES
from generadores.leer.bpmn import leer_bpmn

XMI = "{http://www.omg.org/XMI}"
MAIN = "{http://www.bonitasoft.org/ns/bpm/process}MainProcess"


def _pools(proyecto: Path) -> dict[str, tuple[Path, ET.Element]]:
    out = {}
    for f in sorted((proyecto / "bonita-project" / "app" / "diagrams").glob("*.proc")):
        main = ET.parse(f).getroot().find(MAIN)
        for pool in main.findall("elements") if main is not None else []:
            out[pool.get("name")] = (f, pool)
    return out


def _tarea_xml(pool: ET.Element, n: dict) -> ET.Element | None:
    return next((e for e in pool.iter() if e.get(f"{XMI}type") == CLASES.get(n["tipo"])
                 and e.get("name") == n["nombre"]), None)


def _fila(nombre: str, definicion: str | None, evento: str | None, ignorar: bool) -> str:
    return f"«{nombre}» ({definicion}, {evento}, ignoreErrors={'true' if ignorar else 'false'})"


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    bpmn, _ = leer_bpmn(leer_doc(proyecto, "07-bonita/bpmn.md"))
    xml = _pools(proyecto)
    hallazgos: list[str] = []
    for p in bpmn["procesos"]:
        if p["nombre"] not in xml:
            continue  # ya lo dice check_inventario
        fichero, pool = xml[p["nombre"]]
        u = f"{fichero.name} › {p['nombre']}"
        for n in p["nodos"]:
            if n["tipo"] not in ("humana", "servicio", "script"):
                continue
            tarea = _tarea_xml(pool, n)
            if tarea is None:
                continue  # nodo que falta: ya lo dice check_inventario
            doc = Counter(_fila(nombre, c["definicion"] if c["tipo"] == "propio" else c["tipo"],
                                MOMENTOS.get(c["momento"]), c["ignorar_errores"])
                          for nombre, c in de_la_tarea(p, n["id"]))
            proc = Counter(_fila(e.get("name"), e.get("definitionId"), e.get("event"), e.get("ignoreErrors") == "true")
                           for e in tarea.findall("connectors"))
            for f in sorted((doc - proc).elements()):
                hallazgos.append(f"{u} › {n['id']}: la invocación de conector {f} de bpmn.md falta en el .proc")
            for f in sorted((proc - doc).elements()):
                hallazgos.append(f"{u} › {n['id']}: el conector {f} del .proc no es una fila de bpmn.md › Conectores "
                                 "por tarea")
            if n["tipo"] != "humana":
                continue
            esperado = filtro_de_tarea(p, n)
            filtros = [e.get("name") for e in tarea.findall("filters")]
            if filtros != ([esperado] if esperado else []):
                hallazgos.append(f"{u} › {n['id']}: el .proc tiene el actor filter {filtros or '—'} y bpmn.md "
                                 f"aplica {esperado or '—'} (lane o actor de tarea)")
    return hallazgos
