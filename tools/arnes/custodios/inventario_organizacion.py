"""Inventario del hilo `organizacion` (Plan 5, R-01 y R-02): la documentación y lo generado dicen lo mismo en

- `bpmn.md` ↔ cada `.proc`: lanes y el actor de cada una (Actor Bonita, o ninguno si la lane va sin actor), los
  actores del pool y, por tarea humana, el actor de tarea (`overrideActorsOfTheLane="true"` + `actor`);
- `bdm.md` ↔ `app/organizations/*.xml`: grupos (ruta completa, de `name` + `parentPath`) y *manager* de cada usuario
  de la tabla de usuarios.

Los dos lados se leen por separado: el XML escrito y la documentación con los lectores (como `check_inventario`).
En modo existente la organización es la del proyecto (`generar` no la escribe): solo se exige lo que pide `bdm.md`, y
los pools existentes no se contrastan.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from custodios import leer_doc, pools_existentes
from generadores.existente.linea_base import modo_existente
from generadores.escribir.organizacion import actor_bonita
from generadores.leer.bdm import leer_bdm
from generadores.leer.bpmn import leer_bpmn

XMI = "{http://www.omg.org/XMI}"
MAIN = "{http://www.bonitasoft.org/ns/bpm/process}MainProcess"


def _pools(proyecto: Path) -> dict[str, tuple[Path, ET.Element]]:
    out = {}
    existentes = pools_existentes(proyecto)
    for f in sorted((proyecto / "bonita-project" / "app" / "diagrams").glob("*.proc")):
        main = ET.parse(f).getroot().find(MAIN)
        for pool in main.findall("elements"):
            if pool.get("name") not in existentes:
                out[pool.get("name")] = (f, pool)
    return out


def _comprobar_pool(u: str, p: dict, pool: ET.Element) -> list[str]:
    hallazgos = []
    actores_x = {a.get(f"{XMI}id"): a.get("name") for a in pool.findall("actors")}
    lanes_x = {l.get("name"): actores_x.get(l.get("actor")) for l in pool.findall("elements")
               if l.get(f"{XMI}type") == "process:Lane"}
    lanes_d = {l["nombre"]: actor_bonita(l) for l in p["lanes"]}
    for n in sorted(lanes_d.keys() - lanes_x.keys()):
        hallazgos.append(f"{u}: falta en el .proc la lane «{n}» de bpmn.md")
    for n in sorted(lanes_x.keys() - lanes_d.keys()):
        hallazgos.append(f"{u}: la lane «{n}» del .proc no está en bpmn.md")
    for n in sorted(lanes_d.keys() & lanes_x.keys()):
        if lanes_d[n] != lanes_x[n]:
            doc = f"«{lanes_d[n]}»" if lanes_d[n] else "sin actor"
            xml = f"«{lanes_x[n]}»" if lanes_x[n] else "sin actor"
            hallazgos.append(f"{u} › {n}: la lane tiene el actor {xml} en el .proc y {doc} en bpmn.md")
    tarea_d = {t: a["nombre"] for a in p.get("actores_tarea", []) for t in a.get("tareas", [])}
    nombres_d = {a for a in lanes_d.values() if a} | set(tarea_d.values())
    for a in sorted(nombres_d - set(actores_x.values())):
        hallazgos.append(f"{u}: falta en el .proc el actor «{a}» de bpmn.md")
    for a in sorted(set(actores_x.values()) - nombres_d):
        hallazgos.append(f"{u}: el actor «{a}» del .proc no está en bpmn.md")
    por_nombre = {e.get("name"): e for e in pool.iter() if e.get(f"{XMI}type") == "process:Task"}
    for n in p["nodos"]:
        if n["tipo"] != "humana" or n["nombre"] not in por_nombre:
            continue  # una tarea que falta ya la señala check_inventario
        e = por_nombre[n["nombre"]]
        propio = actores_x.get(e.get("actor")) if e.get("overrideActorsOfTheLane") == "true" else None
        esperado = tarea_d.get(n["id"])
        if propio != esperado:
            hallazgos.append(f"{u} › {n['id']}: actor de tarea «{propio or '—'}» en el .proc y "
                             f"«{esperado or '—'}» en bpmn.md")
    return hallazgos


def _organizacion_xml(proyecto: Path) -> ET.Element | None:
    ficheros = sorted((proyecto / "bonita-project" / "app" / "organizations").glob("*.xml"))
    return ET.parse(ficheros[0]).getroot() if len(ficheros) == 1 else None


def _comprobar_organizacion(proyecto: Path) -> list[str]:
    bdm, _ = leer_bdm(leer_doc(proyecto, "07-bonita/bdm.md"))  # sus errores ya los da check_inventario
    hallazgos: list[str] = []
    raiz = _organizacion_xml(proyecto)
    if raiz is None:
        return hallazgos + ["app/organizations: debe haber exactamente un XML de organización"]
    org = bdm["organizacion"]
    grupos_x = set()
    for g in raiz.iter("group"):  # hijos sin espacio de nombres (como los escribe `generar_organizacion`)
        madre = (g.get("parentPath") or "").strip("/")
        grupos_x.add(f"{madre}/{g.get('name')}" if madre else g.get("name"))
    grupos_d = set(org["grupos"])
    for g in sorted(grupos_d - grupos_x):
        hallazgos.append(f"organización: falta el grupo «/{g}» que declara bdm.md")
    for g in sorted(grupos_x - grupos_d) if not modo_existente(proyecto) else []:
        hallazgos.append(f"organización: el grupo «/{g}» no está en bdm.md")
    manager_x = {}
    for u in raiz.iter("user"):
        m = u.find("manager")
        manager_x[u.get("userName")] = m.text if m is not None else None
    for u in org["usuarios"]:
        if u["nombre"] in manager_x and manager_x[u["nombre"]] != u.get("manager"):
            hallazgos.append(f"organización › {u['nombre']}: *manager* «{manager_x[u['nombre']] or '—'}» en el XML y "
                             f"«{u.get('manager') or '—'}» en bdm.md")
    return hallazgos


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    bpmn, _ = leer_bpmn(leer_doc(proyecto, "07-bonita/bpmn.md"))  # sus errores ya los da check_inventario
    hallazgos: list[str] = []
    xml = _pools(proyecto)
    for p in bpmn["procesos"]:
        if p["nombre"] in xml:  # un pool que falta ya lo señala check_inventario
            fichero, pool = xml[p["nombre"]]
            hallazgos += _comprobar_pool(f"{fichero.name} › {p['nombre']}", p, pool)
    return hallazgos + _comprobar_organizacion(proyecto)
