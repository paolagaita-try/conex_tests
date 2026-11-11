"""Validaciones del hilo `contratos-documentos` (R-06 y R-09) sobre la spec.

- Input «— (solo lectura)» (o un hijo suyo): su raíz debe aparecer en el Groovy de alguna constraint del contrato o
  de alguna operación del mismo contexto (veredicto R-06); si no, error.
- Documentos del pool (`procesos[].documentos`): nombres únicos; «Atributo del BDM» existe y es `LONG`; «Tarea que lo
  aporta» es exactamente el conjunto de contextos cuyos inputs FILE llevan «doc. `<documento>`».
- Operaciones de documento (`procesos[].operaciones_documento`): el contexto tiene contrato; el documento existe; el
  input es FILE; un FILE que da varios archivos (múltiple, o hijo de un COMPLEX múltiple) va a un documento múltiple
  y uno simple a uno simple; un documento recibe como mucho un input por contexto.
- D-57 (integración): una operación de instanciación no puede leer un documento que inicializa el contrato de
  instanciación (el motor crea los documentos después de los datos: la operación no lo ve). Se detecta cuando su
  Groovy nombra el documento como identificador o como cadena; lo que lea un helper no se ve desde aquí.
"""
from __future__ import annotations

import re

from generadores.escribir.proc.datos import simbolos_usados
from generadores.escribir.proc.documentos import es_lista
from generadores.leer import donde

FP, FC = "bpmn.md", "contratos.md"
INSTANCIACION = "(instanciacion)"


def _ubic_contrato(p: dict, clave: str) -> str:
    if clave == INSTANCIACION:
        return donde(FC, "Contrato de instanciación", p.get("nombre"))
    return donde(FC, "Contratos de tarea humana", f"ctr_{clave}")


def _con_solo_lectura(nodo: dict) -> bool:
    return bool(nodo.get("solo_lectura")) or any(_con_solo_lectura(h) for h in nodo.get("hijos", []))


def _camino(entradas: list[dict], ruta: str) -> list[dict] | None:
    camino, nivel = [], entradas
    for parte in (ruta or "").split("."):
        n = next((x for x in nivel if x.get("nombre") == parte), None)
        if n is None:
            return None
        camino.append(n)
        nivel = n.get("hijos", [])
    return camino


def _solo_lectura(p: dict, err: list[str]) -> None:
    for clave, c in p.get("contratos", {}).items():
        groovys = [r.get("groovy") or "" for r in c.get("restricciones", [])]
        groovys += [(o.get("expresion") or {}).get("valor") or "" for o in p.get("operaciones", {}).get(clave, [])
                    if (o.get("expresion") or {}).get("tipo") == "groovy"]
        for i in c.get("inputs", []):
            if _con_solo_lectura(i) and not any(simbolos_usados(g, [i.get("nombre")]) for g in groovys):
                err.append(f"{donde(_ubic_contrato(p, clave), i.get('nombre'))}: input de solo lectura que no lee "
                           "ninguna constraint ni operación; o lo usa una constraint u operación de este contrato, "
                           "o sobra (un «—» a secas sigue siendo error)")


def _documentos(p: dict, atributos: dict, err: list[str]) -> None:
    nombre = p.get("nombre")
    docs = p.get("documentos", [])
    por_nombre = {}
    for d in docs:
        u = donde(FP, "Documentos del proceso", nombre, d.get("nombre"))
        if d.get("nombre") in por_nombre:
            err.append(f"{u}: documento repetido")
        por_nombre[d.get("nombre")] = d
        if d.get("atributo"):
            objeto, _, atributo = d["atributo"].partition(".")
            a = atributos.get(objeto, {}).get(atributo)
            if a is None:
                err.append(f"{u}: el Atributo del BDM «{d['atributo']}» no está en bdm.md")
            elif a.get("tipo") != "LONG":
                err.append(f"{u}: el Atributo del BDM «{d['atributo']}» es {a.get('tipo')}; el que guarda el ID de un "
                           "documento es LONG")
    aportan: dict[str, set[str]] = {}
    for clave, ods in p.get("operaciones_documento", {}).items():
        u = _ubic_contrato(p, clave)
        contrato = p.get("contratos", {}).get(clave)
        if contrato is None:
            err.append(f"{u}: hay inputs FILE hacia documentos pero «{clave}» no tiene contrato")
            continue
        vistos = set()
        for od in ods:
            uo = donde(u, od.get("input"))
            d = por_nombre.get(od.get("documento"))
            if d is None:
                err.append(f"{uo}: «doc. `{od.get('documento')}`» no está en {FP} › Documentos del proceso › "
                           f"{nombre}")
                continue
            aportan.setdefault(d["nombre"], set()).add(clave)
            camino = _camino(contrato.get("inputs", []), od.get("input"))
            if camino is None or camino[-1].get("tipo") != "FILE":
                tipo = camino[-1].get("tipo") if camino else "inexistente"
                err.append(f"{uo}: «doc. `{d['nombre']}`» solo vale para un input FILE (este es {tipo})")
                continue
            if es_lista(camino) and not d.get("multiple"):
                err.append(f"{uo}: el input da varios archivos (FILE múltiple o hijo de un COMPLEX múltiple); el "
                           f"documento «{d['nombre']}» debe ser Múltiple «sí»")
            elif not es_lista(camino) and d.get("multiple"):
                err.append(f"{uo}: el input da un archivo; el documento «{d['nombre']}» debe ser Múltiple «no»")
            if d["nombre"] in vistos:
                err.append(f"{uo}: dos inputs del mismo contrato escriben el documento «{d['nombre']}» (uno por "
                           "documento)")
            vistos.add(d["nombre"])
    for d in docs:
        declarado, real = set(d.get("aportan", [])), aportan.get(d.get("nombre"), set())
        if declarado != real:
            err.append(f"{donde(FP, 'Documentos del proceso', nombre, d.get('nombre'))}: «Tarea que lo aporta» "
                       f"{sorted(declarado) or '—'} no son los contextos cuyos inputs FILE van a «doc. "
                       f"`{d.get('nombre')}`» en {FC} ({sorted(real) or 'ninguno'})")


def _lee_documento(groovy: str, nombre: str) -> bool:
    return bool(simbolos_usados(groovy, [nombre])) or bool(re.search(rf"([\"']){re.escape(nombre)}\1", groovy))


def _documento_en_instanciacion(p: dict, err: list[str]) -> None:
    del_contrato = [od.get("documento") for od in p.get("operaciones_documento", {}).get(INSTANCIACION, [])]
    for o in p.get("operaciones", {}).get(INSTANCIACION, []):
        e = o.get("expresion") or {}
        if e.get("tipo") != "groovy":
            continue
        for d in dict.fromkeys(del_contrato):
            if _lee_documento(e.get("valor") or "", d):
                err.append(f"{donde(_ubic_contrato(p, INSTANCIACION), o.get('destino'))}: la operación de "
                           f"instanciación lee el documento «{d}», que inicializa el contrato de instanciación; el "
                           "motor crea los documentos después de los datos y la operación no lo ve (D-57). Guarda su "
                           "ID en una operación de la primera tarea, o de una tarea script posterior a la instanciación")


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    for p in spec.get("procesos", []):
        _solo_lectura(p, err)
        _documentos(p, atributos, err)
        _documento_en_instanciacion(p, err)
