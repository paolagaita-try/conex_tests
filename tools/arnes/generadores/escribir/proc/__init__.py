"""Generador del `.proc` (XMI de Bonita, `bonitaModelVersion="9"`) a partir de un proceso de la spec: un pool por
fichero, con su `notation:Diagram`, construible por el plugin Maven de Bonita sin pasar por el Studio.

Porta y amplía `tools/gen_proc.py` del lab del Plan 1 (77d212f): varias lanes y actores, tareas humanas, de script
y de servicio, compuertas XOR (condición Groovy, salida por defecto) y AND, varios fines, process variables,
business variables inicializadas desde la instanciación, contratos con COMPLEX y constraints, y operaciones.
Task 10 añade los parámetros del pool, los timers de borde y las call activities (con su mapeo hacia el contrato
del proceso llamado). Task 11, el conector REST GET en una tarea (`conectores.py`); otro tipo de conector se rechaza
con `NotImplementedError` nombrando el elemento.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.organizacion import actor_bonita, actor_iniciador
from generadores.escribir.proc import conectores, documentos, filtros, flujo
from generadores.escribir.proc.configuraciones import configuraciones
from generadores.escribir.proc.formularios import form_mapping, mapeos_del_proceso
from generadores.escribir.proc.contratos import contrato
from generadores.escribir.proc.datos import (INSTANCIACION, Contexto, business_variables, datos_del_pool,
                                             parametros, parametros_del_pool, tipos_de_dato, variables_de_proceso)
from generadores.escribir.proc.ids import NS, SOLO_EN_VALORES, XMI_ID, XMI_TYPE, elemento, q
from generadores.escribir.proc.notacion import dibujar
from generadores.xmlutil import Ids

MODEL_VERSION = "9"


def _no_soportado(proceso: dict, extensiones: dict | None = None) -> None:
    nombre = proceso["nombre"]
    for n in proceso["nodos"]:
        if n["tipo"] not in flujo.TIPOS:
            raise ValueError(f"proceso «{nombre}»: el nodo «{n['id']}» tiene tipo «{n['tipo']}» desconocido")
    conectores.validar(proceso, extensiones)
    filtros.validar(proceso, extensiones)


def generar_proc(proceso: dict, bdm: dict, procesos: list[dict] | None = None,
                 version_bonita: str = "2026.2", organizacion: dict | None = None,
                 formularios: dict | None = None, extensiones: dict | None = None) -> ET.ElementTree:
    """`.proc` del proceso `proceso` (un elemento de `spec["procesos"]`); `bdm` = `spec["bdm"]` (paquete y tipos de
    los atributos); `procesos` = `spec["procesos"]`, para comprobar las call activities contra el contrato del
    proceso llamado (sin él no se comprueba); `version_bonita`, la de `versiones/` con los ids de los conectores.
    IDs deterministas con la semilla `nombre@version`. Con `organizacion` (la de la spec) embebe las configuraciones
    de Qualification y Production (`configuraciones.py`); sin ella el `.proc` no las lleva. Con `formularios`
    (`spec["formularios"]`: la matriz y sus aplicaciones) el form mapping de tareas, instanciación y overview es
    `URL`; sin ella, o para «No form», `NONE`. `extensiones` (`conectores.de_la_spec(spec)`): definiciones propias
    y actor filters del proyecto, para los conectores propios y los filtros."""
    _no_soportado(proceso, extensiones)
    nombre, version = proceso["nombre"], proceso["version"]
    ids = Ids(f"{nombre}@{version}")
    raiz = ET.Element(q("xmi", "XMI"), {q("xmi", "version"): "2.0"})
    for prefijo in SOLO_EN_VALORES:
        raiz.set(f"xmlns:{prefijo}", NS[prefijo])
    main = ET.SubElement(raiz, q("process", "MainProcess"))
    main.set(XMI_ID, ids.siguiente())
    main.set("name", nombre)
    main.set("bonitaModelVersion", MODEL_VERSION)
    pool = elemento(main, "elements", "process:Pool", ids, {"name": nombre, "version": version})

    # Actores: el Actor Bonita de cada lane (una lane sin actor no lleva `actor`) y los de nivel tarea (R-02).
    actores: dict[str, str] = {}
    for lane in proceso["lanes"]:
        if actor_bonita(lane) and actor_bonita(lane) not in actores:
            actores[actor_bonita(lane)] = ids.siguiente()
    for a in proceso.get("actores_tarea", []):
        if a["nombre"] not in actores:
            actores[a["nombre"]] = ids.siguiente()
    lanes = {l["nombre"]: elemento(pool, "elements", "process:Lane", ids,
                                   {"name": l["nombre"], "actor": actores.get(actor_bonita(l) or "")})
             for l in proceso["lanes"]}
    tipos = tipos_de_dato(main, ids)
    ctx = Contexto(ids, tipos, business_variables(proceso, bdm), variables_de_proceso(proceso),
                   params=parametros(proceso))

    principal = not procesos or procesos[0]["nombre"] == nombre
    mapeos = mapeos_del_proceso(formularios, proceso, principal)
    nodos = flujo.nodos(lanes, proceso, ctx, procesos, version_bonita, mapeos, extensiones)
    instanciacion = proceso.get("contratos", {}).get(INSTANCIACION)
    datos_del_pool(pool, proceso, ctx.con_entradas((instanciacion or {}).get("inputs", [])))
    documentos.documentos_del_pool(pool, proceso, ids, (instanciacion or {}).get("inputs", []))  # R-09
    flujo.transiciones(pool, nodos, proceso, ctx)
    form_mapping(pool, "formMapping", mapeos["instanciacion"], ids)
    form_mapping(pool, "overviewFormMapping", mapeos["overview"], ids)
    # Una tarea con actor de tarea lo toma con `overrideActorsOfTheLane="true"` (`Task` de process.ecore 9.0.10).
    for a in proceso.get("actores_tarea", []):
        for t in a.get("tareas", []):
            if t in nodos:
                nodos[t].set("overrideActorsOfTheLane", "true")
                nodos[t].set("actor", actores[a["nombre"]])
    iniciador = actor_iniciador(proceso)
    for actor, id_actor in actores.items():
        a = ET.SubElement(pool, "actors")
        a.set(XMI_TYPE, "process:Actor")
        a.set(XMI_ID, id_actor)
        a.set("name", actor)
        if actor == iniciador:
            a.set("initiator", "true")
    if organizacion is not None:
        configuraciones(pool, proceso, organizacion, ids, version_bonita, extensiones)
    parametros_del_pool(pool, ctx)
    contrato(pool, instanciacion, ids, f"proceso «{nombre}» › {INSTANCIACION}")

    por_lane = [(lanes[l["nombre"]], [n["id"] for n in proceso["nodos"]
                                      if n["lane"] == l["nombre"] and n["tipo"] != "timer_borde"])
                for l in proceso["lanes"]]
    dibujar(raiz, main, pool, por_lane, nodos, proceso, ids)
    return ET.ElementTree(raiz)


def id_pool(arbol: ET.ElementTree) -> str:
    """`xmi:id` del pool: da nombre al `.conf` del proceso."""
    return next(e.get(XMI_ID) for e in arbol.getroot().iter() if e.get(XMI_TYPE) == "process:Pool")
