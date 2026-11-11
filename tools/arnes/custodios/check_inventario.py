"""Custodio de inventario: la documentación y los artefactos generados dicen lo mismo, 1:1.

- `bdm.md` ↔ `bom.xml`: objetos y atributos (sin los 8 `Kp*` fijos del módulo de parámetros, que se reconocen por
  su paquete y no están en `bdm.md`).
- `bpmn.md` ↔ cada `.proc`: nodos (por nombre) y transiciones.
- `contratos.md` ↔ cada `.proc`: inputs (con los hijos de los COMPLEX, por ruta y tipo, a cualquier profundidad) y
  constraints; las `mandatory_*` las genera el generador a partir de los inputs obligatorios (con la obligatoriedad
  propia de cada hijo) y no cuentan como sobrantes.
- `bpmn.md › Documentos del proceso` ↔ cada `.proc`: documentos del pool, su multiplicidad y, si los aporta la
  instanciación, `documentType="CONTRACT"`.

El lado de los artefactos se lee del XML escrito, no de la spec, y el de la documentación con los lectores: ninguno
de los dos lados sale del otro.

En modo existente (spec 6.8) se contrastan los procesos nuevos: lo que su documentación pide debe estar en los
artefactos, pero lo existente (los pools de la línea base en cualquier versión, y los objetos, atributos y grupos que
`generar` no escribe en ese modo) no se exige en la documentación: lo vigila `check_cambios` contra la línea base.
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import custodios
from custodios import docs_de_procesos_nuevos, ejecutar, leer_doc, pools_existentes
from generadores.existente.linea_base import modo_existente
from generadores.escribir.bom import PAQUETE_PARAMETROS
from generadores.leer.bdm import leer_bdm
from generadores.leer.bpmn import leer_bpmn
from generadores.escribir.proc.contratos import obligatorias
from generadores.escribir.proc.eventos import CLASE_BORDE
from generadores.escribir.proc.flujo import clase
from generadores.leer.contratos import leer_contratos

XMI = "{http://www.omg.org/XMI}"
MAIN = "{http://www.bonitasoft.org/ns/bpm/process}MainProcess"
BDM_NS = "{http://documentation.bonitasoft.com/bdm-xml-schema/1.0}"
INSTANCIACION = "(instanciacion)"


def _clase(n: dict) -> str:
    """Clase `process:*` que el generador da a un nodo de la documentación (su propia tabla)."""
    return CLASE_BORDE[bool(n.get("interruptor"))] if n["tipo"] == "timer_borde" else clase(n)


_FLUJO = ("Task", "Activity", "Event", "Gateway")


# ---------------------------------------------------------------------------------------------------- BDM

def _comprobar_bdm(proyecto: Path) -> list[str]:
    # En modo existente `generar` no escribe el bom.xml: lo que tenga de más es lo existente (o un cambio confirmado).
    existente = modo_existente(proyecto)
    bdm, errores = leer_bdm(leer_doc(proyecto, "07-bonita/bdm.md"))
    hallazgos = [f"bdm.md: {e}" for e in errores]
    doc = {o["nombre"]: {a["nombre"] for a in o["atributos"]} for o in bdm["bdm"]["objetos"]}
    ruta = proyecto / "bonita-project" / "bdm" / "bom.xml"
    if not ruta.is_file():
        return hallazgos + ["bom.xml: no existe"]
    xml: dict[str, set[str]] = {}
    for bo in ET.parse(ruta).getroot().iter(f"{BDM_NS}businessObject"):
        calificado = bo.get("qualifiedName", "")
        paquete, _, nombre = calificado.rpartition(".")
        if paquete == PAQUETE_PARAMETROS:
            continue  # objetos fijos del módulo de parámetros: no son del dominio ni están en bdm.md
        if paquete != bdm["bdm"]["paquete"] and not (existente and nombre not in doc):
            hallazgos.append(f"bom.xml › {nombre}: paquete «{paquete}»; bdm.md dice «{bdm['bdm']['paquete']}»")
        xml[nombre] = {c.get("name") for c in bo.find(f"{BDM_NS}fields")
                       if c.tag in (f"{BDM_NS}field", f"{BDM_NS}relationField")}
    for o in sorted(doc.keys() - xml.keys()):
        hallazgos.append(f"bom.xml: falta el objeto «{o}» que declara bdm.md")
    for o in sorted(xml.keys() - doc.keys()) if not existente else []:
        hallazgos.append(f"bom.xml: el objeto «{o}» no está en bdm.md")
    for o in sorted(doc.keys() & xml.keys()):
        for a in sorted(doc[o] - xml[o]):
            hallazgos.append(f"bom.xml › {o}: falta el atributo «{a}» que declara bdm.md")
        for a in sorted(xml[o] - doc[o]) if not existente else []:
            hallazgos.append(f"bom.xml › {o}: el atributo «{a}» no está en bdm.md")
    return hallazgos


# ---------------------------------------------------------------------------------------------------- .proc

def _pools(proyecto: Path) -> dict[str, tuple[Path, ET.Element]]:
    """Pools de los `.proc` por nombre, sin los existentes (modo existente)."""
    out = {}
    existentes = pools_existentes(proyecto)
    for f in sorted((proyecto / "bonita-project" / "app" / "diagrams").glob("*.proc")):
        main = ET.parse(f).getroot().find(MAIN)
        for pool in main.findall("elements"):
            if pool.get("name") not in existentes:
                out[pool.get("name")] = (f, pool)
    return out


def _es_flujo(e: ET.Element) -> bool:
    t = e.get(f"{XMI}type", "")
    return t.startswith("process:") and t.endswith(_FLUJO) and e.get("name") is not None


def _nodos_xml(pool: ET.Element) -> dict[str, tuple[str, str]]:
    return {e.get(f"{XMI}id"): (e.get("name"), e.get(f"{XMI}type")) for e in pool.iter() if _es_flujo(e)}


def _inputs_xml(contrato: ET.Element | None, prefijo: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for i in (contrato.findall("inputs") if contrato is not None else []):
        ruta = f"{prefijo}{i.get('name')}"
        out[ruta] = i.get("type")
        out.update(_inputs_xml(i, ruta + "."))
    return out


def _inputs_doc(inputs: list[dict], prefijo: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for i in inputs:
        ruta = f"{prefijo}{i['nombre']}"
        out[ruta] = i["tipo"]
        out.update(_inputs_doc(i.get("hijos", []), ruta + "."))
    return out


def _comprobar_contrato(u: str, doc: dict | None, xml: ET.Element | None) -> list[str]:
    hallazgos = []
    ins_d = _inputs_doc(doc["inputs"]) if doc else {}
    ins_x = _inputs_xml(xml)
    for i in sorted(ins_d.keys() - ins_x.keys()):
        hallazgos.append(f"{u}: falta el input «{i}» que pide contratos.md")
    for i in sorted(ins_x.keys() - ins_d.keys()):
        hallazgos.append(f"{u}: el input «{i}» no está en contratos.md")
    for i in sorted(ins_d.keys() & ins_x.keys()):
        if ins_d[i] != ins_x[i]:
            hallazgos.append(f"{u}: el input «{i}» es {ins_x[i]} en el .proc y {ins_d[i]} en contratos.md")
    # Las `mandatory_*` salen de la columna «Obligatorio» con la regla del generador (misma función).
    cons_d = ({r["nombre"] for r in doc["restricciones"]} | {o[0] for o in obligatorias(doc["inputs"])}) \
        if doc else set()
    cons_x = {c.get("name") for c in (xml.findall("constraints") if xml is not None else [])}
    for c in sorted(cons_d - cons_x):
        hallazgos.append(f"{u}: falta el constraint «{c}» que pide contratos.md")
    for c in sorted(cons_x - cons_d):
        hallazgos.append(f"{u}: el constraint «{c}» no está en contratos.md")
    return hallazgos


def _comprobar_documentos(u: str, doc: list[dict], pool: ET.Element) -> list[str]:
    hallazgos = []
    d = {x["nombre"]: x for x in doc}
    x = {e.get("name"): e for e in pool.findall("documents")}
    for n in sorted(d.keys() - x.keys()):
        hallazgos.append(f"{u}: falta el documento «{n}» que declara bpmn.md")
    for n in sorted(x.keys() - d.keys()):
        hallazgos.append(f"{u}: el documento «{n}» no está en bpmn.md")
    for n in sorted(d.keys() & x.keys()):
        if d[n]["multiple"] != (x[n].get("multiple") == "true"):
            hallazgos.append(f"{u}: el documento «{n}» es {'múltiple' if d[n]['multiple'] else 'simple'} en bpmn.md "
                             "y no en el .proc")
        if (INSTANCIACION in d[n]["aportan"]) != (x[n].get("documentType") == "CONTRACT"):
            hallazgos.append(f"{u}: el documento «{n}»: bpmn.md "
                             f"{'lo' if INSTANCIACION in d[n]['aportan'] else 'no lo'} inicializa desde la "
                             f"instanciación y el .proc dice documentType «{x[n].get('documentType') or 'NONE'}»")
    return hallazgos


def _comprobar_procesos(proyecto: Path) -> list[str]:
    bpmn, errores = leer_bpmn(leer_doc(proyecto, "07-bonita/bpmn.md"))
    contratos, err_c = leer_contratos(leer_doc(proyecto, "07-bonita/contratos.md"))
    hallazgos = [f"bpmn.md: {e}" for e in errores] + [f"contratos.md: {e}" for e in err_c]
    xml = _pools(proyecto)
    doc = {p["nombre"]: p for p in bpmn["procesos"]}
    for n in sorted(doc.keys() - xml.keys()):
        hallazgos.append(f"{n}: falta en el .proc el pool que describe bpmn.md")
    for n in sorted(xml.keys() - doc.keys()):
        hallazgos.append(f"{xml[n][0].name}: el pool «{n}» no está en bpmn.md")
    for nombre in sorted(doc.keys() & xml.keys()):
        fichero, pool = xml[nombre]
        p = doc[nombre]
        u = f"{fichero.name} › {nombre}"
        nombre_de = {n["id"]: n["nombre"] for n in p["nodos"]}
        nodos_x = _nodos_xml(pool)
        d = Counter((n["nombre"], _clase(n)) for n in p["nodos"])
        x = Counter(nodos_x.values())
        for n, c in sorted((d - x).elements()):
            hallazgos.append(f"{u}: el nodo «{n}» ({c}) de bpmn.md falta en el .proc o tiene otro tipo")
        for n, c in sorted((x - d).elements()):
            hallazgos.append(f"{u}: el nodo «{n}» ({c}) del .proc no está en bpmn.md o tiene otro tipo")
        for n, k in sorted(Counter(nom for nom, _ in nodos_x.values()).items()):
            if k > 1:
                hallazgos.append(f"{u}: el nombre de nodo «{n}» está repetido {k} veces en el .proc; debe ser único "
                                 "en el pool")
        trans_d = Counter((nombre_de[t["desde"]], nombre_de[t["hacia"]]) for t in p["transiciones"]
                          if t["desde"] in nombre_de and t["hacia"] in nombre_de)
        trans_x = Counter((nodos_x.get(e.get("source"), (None,))[0], nodos_x.get(e.get("target"), (None,))[0])
                          for e in pool.iter("connections") if e.get(f"{XMI}type") == "process:SequenceFlow")
        for a, b in sorted((trans_d - trans_x).elements(), key=str):
            hallazgos.append(f"{u}: la transición «{a}» → «{b}» de bpmn.md falta en el .proc")
        for a, b in sorted((trans_x - trans_d).elements(), key=str):
            hallazgos.append(f"{u}: la transición «{a}» → «{b}» del .proc no está en bpmn.md")
        hallazgos += _comprobar_documentos(u, p.get("documentos", []), pool)
        # Contratos: instanciación (en el pool) y uno por tarea humana (en la tarea, que se nombra por `nombre`).
        bloque = contratos["instanciacion"].get(nombre)
        hallazgos += _comprobar_contrato(f"{u} › {INSTANCIACION}", bloque["contrato"] if bloque else None,
                                         pool.find("contract"))
        for n in p["nodos"]:
            if n["tipo"] != "humana":
                continue
            bloque = contratos["tareas"].get(n["id"])
            tarea = next((e for e in pool.iter() if _es_flujo(e) and e.get("name") == n["nombre"]
                         and e.get(f"{XMI}type") == _clase(n)), None)
            if tarea is None:
                continue  # ya señalado como nodo que falta
            hallazgos += _comprobar_contrato(f"{u} › {n['id']}", bloque["contrato"] if bloque else None,
                                             tarea.find("contract"))
    return hallazgos


def _modulos_inventario() -> list:
    """Los módulos `custodios/inventario_*.py` (comparaciones de inventario de los hilos del Plan 5), en orden
    alfabético. Cada uno expone `comprobar(proyecto: Path) -> list[str]`."""
    return [importlib.import_module(f"custodios.{m.name}")
            for m in sorted(pkgutil.iter_modules(custodios.__path__), key=lambda m: m.name)
            if m.name.startswith("inventario_")]


def _comprobar_adaptador(proyecto: Path) -> list[str]:
    """D-113: `parametros-adaptador` en `app/pom.xml` lleva la semilla (`semillas/*.json`) al classpath del proceso;
    sin él, `usar` no la aplica y vuelve el fallo D-112 (`ParametroNoDisponible` hasta que alguien llama a la API)."""
    modulo = proyecto / "bonita-project" / "extensions" / "parametros-adaptador"
    pom = proyecto / "bonita-project" / "app" / "pom.xml"
    if not modulo.is_dir() or not pom.is_file():
        return []  # proyecto sin el módulo de parámetros: nada que llevar
    if "-parametros-adaptador</artifactId>" in pom.read_text(encoding="utf-8"):
        return []
    return ["bonita-project/app/pom.xml: falta la dependencia «parametros-adaptador»; es lo que lleva la semilla de "
            "parámetros al proceso (D-113) y sin ella vuelve el fallo D-112"]


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    if not docs_de_procesos_nuevos(proyecto):
        # Unidad 0 (o modo existente sin procesos nuevos): no hay documentación que contrastar.
        return _comprobar_adaptador(proyecto)
    hallazgos = _comprobar_adaptador(proyecto) + _comprobar_bdm(proyecto) + _comprobar_procesos(proyecto)
    for modulo in _modulos_inventario():
        hallazgos += modulo.comprobar(proyecto)
    return hallazgos


def main() -> int:
    return ejecutar("check_inventario", comprobar)


if __name__ == "__main__":
    sys.exit(main())
