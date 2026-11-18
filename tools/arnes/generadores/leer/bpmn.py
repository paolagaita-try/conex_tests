"""Lector de `docs/07-bonita/bpmn.md`: pools, lanes, nodos, transiciones, conectores y process variables.

Reglas de la lane de compuertas y eventos (no tienen columna de lane): el borde va en la lane de su anfitriona; el
inicio, en la del iniciador (si no hay iniciador, en la de su primer sucesor); el resto, en la de su primer
predecesor según el orden de la tabla de transiciones. Los nodos `fin_*` salen de `## Eventos` y de los destinos de
transición o de compuerta.
"""
from __future__ import annotations

import re

from generadores.leer import (columna, donde, filas, plano, pools, ref_doc, requerir, seccion, si_no,
                              sin_parentesis, tabla, vacio)
from generadores.leer.documentos import leer_documentos
from generadores.leer.extensiones import entradas_con_marca
from generadores.md import Documento, Seccion, codigo, lista

F = "bpmn.md"
TIPOS_TAREA = {"human": "humana", "service": "servicio", "script": "script", "call activity": "llamada"}
# Tipo de conector en la celda «`conn_x` (TIPO)»; «(propio `<definitionId>`)» es un conector del proyecto (R-10).
TIPOS_CONECTOR = {"REST GET": "rest-get"}
PROPIO = "propio"
_BACKTICKS = re.compile(r"`([^`]+)`")
COL_TAREAS = ("Nombre", "Tipo Bonita", "Lane / actor", "Contrato", "Conector", "Operaciones previstas",
              "Notas")
COL_COMPUERTAS = ("Tipo", "Después de", "Variable o atributo que decide", "Salidas", "Salida por defecto")
COL_EVENTOS = ("Tipo", "Posición", "Disparador", "Destino")
COL_CONECTORES = ("Conector", "Modo", "Momento", "Entrada", "Salida")


def _nodo(id_: str, nombre: str, tipo: str, lane: str | None = None, documentacion: str = "") -> dict:
    return {"id": id_, "nombre": nombre, "tipo": tipo, "lane": lane, "documentacion": documentacion,
            "anfitrion": None, "interruptor": None, "duracion": None, "llamado": None, "conector": None}


def _sub(doc: Documento, nombre_sec: str, pool: str, errores: list[str]) -> Seccion | None:
    sec = seccion(doc, nombre_sec, F, errores)
    if sec is None:
        return None
    try:
        return sec.seccion(f"`{pool}`")
    except KeyError:
        errores.append(f"{donde(F, nombre_sec)}: falta la subsección del pool «`{pool}`»")
        return None


def _tareas(sec: Seccion | None, ubic: str, errores: list[str]) -> list[dict]:
    out = []
    for f in filas(tabla(sec, "ID", COL_TAREAS, ubic, errores)):
        id_ = codigo(f["ID"]).strip()
        u = donde(ubic, id_)
        tipo_doc = f["Tipo Bonita"].strip()
        tipo = TIPOS_TAREA.get(tipo_doc)
        if tipo is None:
            errores.append(f"{u}: tipo de tarea «{tipo_doc}» no soportado (solo {', '.join(TIPOS_TAREA)})")
            continue
        notas = f["Notas"]
        n = _nodo(id_, f["Nombre"].strip(), tipo, codigo(f["Lane / actor"]).strip(),
                  "" if vacio(notas) else plano(notas))
        n["_contrato"] = None if vacio(columna(f, "Contrato")) else codigo(columna(f, "Contrato")).strip()
        cc = columna(f, "Conector")
        # El conjunto de conectores `conn_*` de la tarea (sin tokens `conn_*`, el primer token, como antes).
        tokens = _BACKTICKS.findall(cc) if not vacio(cc) else []
        n["_conectores"] = [] if vacio(cc) else sorted({t for t in tokens if t.startswith("conn_")}
                                                       or {(tokens or [cc.strip()])[0]})
        if tipo == "llamada":
            m = re.search(r"Llama a `(\w+)` (\d+(?:\.\d+)*)", notas)
            if not m:
                errores.append(f"{u}: la call activity debe decir en Notas «Llama a `<Pool>` <versión>»")
            else:
                entradas = []
                for o, i in re.findall(r"`([^`]+)`\s*→\s*`([^`]+)`", f["Operaciones previstas"]):
                    if ref_doc(o) is None:
                        errores.append(f"{u}: el origen «{o}» de la entrada «{i}» debe ser «Objeto.atributo» o "
                                       "«pv variable»")
                        continue
                    entradas.append({"origen": ref_doc(o), "input": i.strip()})
                n["llamado"] = {"proceso": m.group(1), "version": m.group(2), "entradas": entradas}
        out.append(n)
    return out


def _compuertas(sec: Seccion | None, ubic: str, errores: list[str]) -> list[dict]:
    out = []
    for f in filas(tabla(sec, "ID", COL_COMPUERTAS, ubic, errores)):
        id_ = codigo(f["ID"]).strip()
        u = donde(ubic, id_)
        tipo_doc = f["Tipo"].strip()
        if tipo_doc.startswith("exclusive"):
            tipo = "xor"
        elif tipo_doc.startswith("parallel"):
            tipo = "and"
        else:
            errores.append(f"{u}: compuerta «{tipo_doc}» no soportada (solo exclusive (XOR) y parallel (AND))")
            continue
        decide = f["Variable o atributo que decide"]
        n = _nodo(id_, id_, tipo, None, "" if vacio(decide) else plano(f"Decide: {decide}"))
        salidas = []
        for s in lista(columna(f, "Salidas")):
            if " → " not in s:
                errores.append(f"{u}: salida «{s}» debe ser «condición → `destino`»")
                continue
            cond, dest = s.rsplit(" → ", 1)
            salidas.append((cond.strip(), codigo(dest).strip()))
        n["_salidas"] = salidas
        n["_defecto"] = None if vacio(f["Salida por defecto"]) else codigo(f["Salida por defecto"]).strip()
        n["_despues"] = _BACKTICKS.findall(f["Después de"])
        out.append(n)
    return out


def _eventos(sec: Seccion | None, ubic: str, errores: list[str]) -> list[dict]:
    out = []
    for f in filas(tabla(sec, "ID", COL_EVENTOS, ubic, errores)):
        id_ = codigo(f["ID"]).strip()
        u = donde(ubic, id_)
        tipo_doc = f["Tipo"].strip()
        pos = columna(f, "Posición").strip()
        disparador = columna(f, "Disparador")
        doc_ = "" if vacio(disparador) else plano(disparador)
        if pos == "inicio" and tipo_doc == "none":
            n = _nodo(id_, id_, "inicio", None, doc_)
        elif pos == "fin" and tipo_doc in ("none", "terminate"):
            n = _nodo(id_, id_, "fin", None, doc_)
            if tipo_doc == "terminate":  # R-12: `process:EndTerminatedEvent`; para el resto del arnés, un fin
                n["terminar"] = True
        elif pos.startswith("borde de") and tipo_doc == "timer":
            m = re.fullmatch(r"borde de `(\w+)` \((no )?interruptor\)", pos)
            if not m:
                errores.append(f"{u}: posición «{pos}» debe ser «borde de `<tarea>` (interruptor)» "
                               "o «… (no interruptor)»")
                continue
            n = _nodo(id_, id_, "timer_borde", None, doc_)
            n["anfitrion"], n["interruptor"] = m.group(1), m.group(2) is None
            n["duracion"] = None if vacio(disparador) else codigo(disparador).strip()
        else:
            errores.append(f"{u}: evento «{tipo_doc}» en posición «{pos}» no soportado "
                           "(solo inicio none, fin none o terminate, y timer de borde)")
            continue
        n["_destino"] = _BACKTICKS.findall(f["Destino"])
        out.append(n)
    return out


def _transiciones(sec: Seccion | None, ubic: str, errores: list[str]) -> list[dict]:
    out = []
    for f in filas(tabla(sec, "Desde", ("Hacia", "Condición"), ubic, errores)):
        d, h = codigo(f["Desde"]).strip(), codigo(f["Hacia"]).strip()
        cond = columna(f, "Condición")
        t = {"desde": d, "hacia": h, "expresion": None, "defecto": False, "_condicion": cond.strip()}
        if cond.strip() == "(por defecto)":
            t["defecto"] = True
        elif not vacio(cond):
            t["expresion"] = requerir(f"{d}→{h}", codigo(cond), donde(ubic, f"{d}→{h}"))
        out.append(t)
    return out


_IGNORE = re.compile(r"\bIGNORE\b")
_THROW = re.compile(r"\bTHROW ERROR\b")


def _tipo_conector(celda: str, u: str, errores: list[str]) -> tuple[str | None, str | None, str | None]:
    """«`conn_x` (REST GET)» o «`conn_x` (propio `<definitionId>`)» → (id, tipo, definición)."""
    ids = _BACKTICKS.findall(celda.split("(")[0])
    m = re.search(r"\(([^)]*)\)", celda)
    if not ids or not m:
        errores.append(f"{u}: el conector «{celda}» debe ser «`conn_x` (REST GET)» o «`conn_x` (propio `<definición>`)»")
        return None, None, None
    marca = m.group(1).strip()
    if marca.startswith(PROPIO):
        defs = _BACKTICKS.findall(marca) or marca[len(PROPIO):].split()
        if not defs:
            errores.append(f"{u}: el conector propio «{celda}» debe nombrar su definición: «(propio `<definitionId>`)»")
            return ids[0], None, None
        return ids[0], "propio", defs[0].strip()
    tipo = TIPOS_CONECTOR.get(marca)
    if tipo is None:
        errores.append(f"{u}: tipo de conector «{marca}» no soportado (solo {', '.join(TIPOS_CONECTOR)} o "
                       "«propio `<definitionId>`», un conector del proyecto en bonita-project/extensions)")
    return ids[0], tipo, None


def _conectores(sec: Seccion | None, ubic: str, nodos: dict[str, dict], errores: list[str]) -> list[dict]:
    """Una entrada por invocación (fila), en el orden de la tabla. `orden` = posición dentro de (tarea, momento).
    El mismo conector puede ir en varias tareas y varias veces en una tarea (R-10)."""
    out: list[dict] = []
    tipo_de: dict[str, tuple] = {}
    for f in filas(tabla(sec, "Tarea", COL_CONECTORES, ubic, errores)):
        tarea = codigo(f["Tarea"]).strip()
        u = donde(ubic, tarea)
        id_, tipo, definicion = _tipo_conector(columna(f, "Conector"), u, errores)
        if id_ is None:
            continue
        if id_ in tipo_de and tipo_de[id_] != (tipo, definicion):
            errores.append(f"{u}: el conector «{id_}» tiene otro tipo o definición en otra fila; un mismo ID lleva "
                           "siempre el mismo")
        tipo_de.setdefault(id_, (tipo, definicion))
        modo = f["Modo"].strip()
        if modo == "asíncrono":
            errores.append(f"{u}: modo «asíncrono» no soportado: el modo técnico es «síncrono»; para que el caso "
                           "siga aunque el conector falle, escribe `IGNORE` en «Manejo de fallo» (reintentos y "
                           "activación por código son lógica del conector del proyecto)")
        elif modo != "síncrono":
            errores.append(f"{u}: modo «{f['Modo']}» no soportado (solo síncrono)")
        momento = columna(f, "Momento").strip()
        if momento not in ("entrada", "salida"):
            errores.append(f"{u}: momento «{momento}» debe ser «entrada» o «salida»")
        salidas = []
        for s in lista(columna(f, "Salida")):
            if vacio(s):
                continue
            par = re.fullmatch(r"`([^`]+)`\s*←\s*`([^`]+)`", s.strip())
            clave = "salida" if tipo == "propio" else "json"
            if par and ref_doc(par.group(1)) is None:
                errores.append(f"{u}: el destino «{par.group(1)}» de la salida debe ser «Objeto.atributo» o "
                               "«pv variable»")
            elif par:
                salidas.append({"destino": ref_doc(par.group(1)), clave: par.group(2).strip()})
            else:
                errores.append(f"{u}: salida «{s}» debe ser «`destino` ← `{clave}`»")
        entrada = columna(f, "Entrada")
        if "←" in entrada:
            entradas = entradas_con_marca(entrada, f"{id_}.", donde(u, "Entrada"), errores)
            if tipo == "rest-get" and set(entradas) - {"url"}:
                errores.append(f"{u}: el REST GET solo admite la entrada `url` ({', '.join(sorted(entradas))})")
        elif tipo == "propio":
            errores.append(f"{u}: un conector propio necesita sus entradas como «`entrada` ← `texto` "
                           f"(`{id_}.{tarea}.<entrada>`)», separadas por «; »")
            entradas = {}
        else:
            entradas = {"url": requerir(f"{id_}.url", codigo(entrada), u)}
        try:
            fallo = columna(f, "Manejo")
        except KeyError:
            fallo = ""
        if _THROW.search(fallo):
            errores.append(f"{u}: manejo de fallo «THROW ERROR» no soportado (solo `IGNORE`, o el fallo por defecto)")
        elif re.search(r"ignor", fallo, re.IGNORECASE) and not _IGNORE.search(fallo):
            # «ignore», «ignorar»…: el autor quiere que el caso siga, y sin el token sería FAIL (revisión final, M-3).
            errores.append(f"{u}: manejo de fallo «{fallo.strip()}»: para que el caso siga aunque el conector falle "
                           "escribe el token `IGNORE` (en mayúsculas); sin él el fallo es `FAIL`")
        orden = 1 + sum(1 for c in out if c["tarea"] == tarea and c["momento"] == momento)
        out.append({"id": id_, "tarea": tarea, "orden": orden, "tipo": tipo, "definicion": definicion,
                    "momento": momento, "entradas": entradas, "salidas": salidas,
                    "ignorar_errores": bool(_IGNORE.search(fallo))})
        if tarea not in nodos:
            errores.append(f"{u}: la tarea no está en el inventario")
    for n in nodos.values():
        n.pop("conector", None)  # se deriva de `conectores` (contrato §3.6)
        if "_conectores" not in n:
            continue
        tabla_ = sorted({c["id"] for c in out if c["tarea"] == n["id"]})
        if tabla_ != n["_conectores"]:
            errores.append(f"{donde(F, 'Inventario de tareas', ubic.split(' › ')[-1], n['id'])}: el inventario dice "
                           f"conectores {n['_conectores'] or '—'} y Conectores por tarea {tabla_ or '—'}")
    return out


def _variables(sec: Seccion | None, ubic: str, errores: list[str]) -> list[dict]:
    out = []
    for f in filas(tabla(sec, "Variable", ("Tipo", "Valor por defecto", "Transitoria"), ubic, errores)):
        nombre = codigo(f["Variable"]).strip()
        defecto = f["Valor por defecto"]
        out.append({"nombre": nombre, "tipo": f["Tipo"].strip(),
                    "defecto": None if vacio(defecto) else codigo(defecto).strip(),
                    "transitoria": si_no(f["Transitoria"], donde(ubic, nombre), errores)})
    return out


def _primer_token(celda: str) -> str | None:
    if vacio(celda) or celda.strip().lower().startswith("no aplica"):
        return None
    tokens = _BACKTICKS.findall(sin_parentesis(celda))
    return tokens[0].strip() if tokens else codigo(sin_parentesis(celda)).strip() or None


def _lane(f: dict[str, str], u: str, errores: list[str]) -> dict:
    """Una fila de la tabla de lanes (Plan 5, R-02). «Actor Bonita» (opcional, tras el actor de negocio): nombre del
    actor en el `.proc`/`.conf`; «—» = lane sin actor. «Actor filter»: el filtro de la lane, en crudo (lo valida y lo
    escribe el hilo `extensiones`). Solo se emiten las claves que no valen su defecto (G-5)."""
    lane = {"nombre": f["Lane"].strip(), "actor": codigo(columna(f, "Actor")).strip(),
            "_grupo_rol": [t.strip().strip("/") for t in _BACKTICKS.findall(columna(f, "Grupo/rol"))]}
    if any(k.startswith("Actor Bonita") for k in f):
        bonita = _primer_token(columna(f, "Actor Bonita"))
        if bonita is None:
            lane["sin_actor"] = True
        elif bonita != lane["actor"]:
            lane["actor_bonita"] = bonita
    filtro = _primer_token(columna(f, "Actor filter"))
    if filtro is not None:
        lane["filtro"] = filtro
    return lane


def _fila_de_pool(f: dict[str, str], lane: dict, u: str, errores: list[str]) -> None:
    """Una fila de nivel pool repite lo que dice la tabla de lanes: Mapeo «—» o los roles de la lane, Filtro «—» o el
    Actor filter de la lane. Lo que difiere se perdería en silencio (el arnés escribe lo de la lane): es error
    (revisión final, I-3)."""
    filtro = _primer_token(f["Filtro"])
    if filtro is not None and filtro != lane.get("filtro"):
        errores.append(f"{u}: el Filtro «{filtro}» de la fila de nivel pool no es el Actor filter de la lane "
                       f"«{lane['nombre']}» ({lane.get('filtro') or '—'}); el filtro de una lane se declara en la "
                       "columna «Actor filter» de la tabla de lanes (o «—» aquí)")
    if vacio(f["Mapeo"]):
        return
    mapeo = [t.strip() for t in _BACKTICKS.findall(sin_parentesis(f["Mapeo"]))]
    roles = lane.get("_grupo_rol", [])[1:]
    if sorted(set(mapeo)) != sorted(set(roles)):
        errores.append(f"{u}: el Mapeo {', '.join(mapeo) or f['Mapeo'].strip()} de la fila de nivel pool no son los "
                       f"roles de la lane «{lane['nombre']}» ({', '.join(roles) or '—'}); el mapeo del actor de una "
                       "lane sale de su Grupo/rol (o «—» aquí). Otro mapeo para una tarea: un actor de tarea (Nivel "
                       "«tarea»)")


def _actores_bonita(sec_pool: Seccion, lanes: list[dict], ul: str, errores: list[str]) -> list[dict]:
    """Tabla «Actor Bonita | Nivel | Mapeo | Tareas | Filtro» del pool (opcional). Nivel `pool…`: informativa (el
    nombre debe ser el Actor Bonita de alguna lane). Nivel `tarea`: un actor de tarea con su Mapeo (roles, o
    membresías «`ruta` / `rol`», separados por «; »), sus tareas humanas y su filtro."""
    out = []
    nombres = {l.get("actor_bonita") or l["actor"] for l in lanes if not l.get("sin_actor")}
    for f in filas(tabla(sec_pool, "Actor Bonita", ("Nivel", "Mapeo", "Tareas", "Filtro"), ul, errores)):
        nombre = _primer_token(f["Actor Bonita"]) or f["Actor Bonita"].strip()
        u = donde(ul, "Actor Bonita", nombre)
        nivel = f["Nivel"].strip().lower()
        if nivel.startswith("pool"):
            if nombre not in nombres:
                errores.append(f"{u}: nivel pool, pero ninguna lane tiene el Actor Bonita «{nombre}» "
                               f"({', '.join(sorted(nombres)) or 'ninguna'})")
            else:
                _fila_de_pool(f, next(l for l in lanes if not l.get("sin_actor")
                                      and (l.get("actor_bonita") or l["actor"]) == nombre), u, errores)
            continue
        if nivel != "tarea":
            errores.append(f"{u}: Nivel «{f['Nivel']}» debe ser «pool…» o «tarea»")
            continue
        roles, membresias = [], []
        for parte in [x for x in f["Mapeo"].split(";") if x.strip()]:
            tokens = [t.strip() for t in _BACKTICKS.findall(sin_parentesis(parte))]
            if len(tokens) == 2 and "/" in _BACKTICKS.sub("", parte):
                membresias.append({"grupo": tokens[0].strip("/"), "rol": tokens[1]})
            else:
                roles += [t for t in tokens if t not in roles]
        out.append({"nombre": nombre, "roles": roles, "membresias": membresias,
                    "tareas": [t.strip() for t in _BACKTICKS.findall(sin_parentesis(f["Tareas"]))],
                    "filtro": _primer_token(f["Filtro"])})
    return out


def _lanes_de_nodos(nodos: list[dict], trans: list[dict], lanes: list[dict], iniciador: str | None,
                    ubic: str, errores: list[str]) -> None:
    por_id = {n["id"]: n for n in nodos}
    for n in nodos:
        if n["tipo"] == "inicio" and iniciador is not None:
            candidatas = [l["nombre"] for l in lanes if iniciador in (l["actor"], l.get("actor_bonita"))
                          and not l.get("sin_actor")]
            if len(candidatas) > 1:
                candidatas = [c for c in candidatas if c == iniciador] or candidatas
            if len(candidatas) == 1:
                n["lane"] = candidatas[0]
            else:
                errores.append(f"{donde(ubic, n['id'])}: no hay una sola lane del iniciador «{iniciador}» "
                               f"({candidatas or 'ninguna'})")
    cambio = True
    while cambio:
        cambio = False
        for n in nodos:
            if n["lane"] is not None:
                continue
            if n["tipo"] == "timer_borde":
                fuente = por_id.get(n["anfitrion"])
            elif n["tipo"] == "inicio":
                fuente = next((por_id.get(t["hacia"]) for t in trans if t["desde"] == n["id"]), None)
            else:
                fuente = next((por_id.get(t["desde"]) for t in trans if t["hacia"] == n["id"]), None)
            if fuente is not None and fuente["lane"] is not None:
                n["lane"] = fuente["lane"]
                cambio = True


def _comprobar_compuertas(nodos: list[dict], trans: list[dict], ubic: str, errores: list[str]) -> None:
    for n in nodos:
        u = donde(ubic, n["id"])
        if "_salidas" in n:
            salientes = [t for t in trans if t["desde"] == n["id"]]
            doc_ = [d for _, d in n["_salidas"]]
            tr = [t["hacia"] for t in salientes]
            if sorted(doc_) != sorted(tr):
                errores.append(f"{u}: las salidas {doc_} no son las transiciones que salen de la compuerta {tr}")
            elif doc_ != tr:
                errores.append(f"{u}: las transiciones {tr} no siguen el orden de las salidas {doc_} "
                               "(en una XOR gana la primera condición verdadera)")
            else:
                for (cond, dest), t in zip(n["_salidas"], salientes):
                    if cond != t["_condicion"] and not (vacio(cond) and vacio(t["_condicion"])):
                        errores.append(f"{u}: la condición de la salida a «{dest}» («{cond}») no es la de la "
                                       f"transición («{t['_condicion']}»)")
            por_defecto = [d for c, d in n["_salidas"] if c == "(por defecto)"]
            if n["tipo"] == "xor" and por_defecto != ([n["_defecto"]] if n["_defecto"] else []):
                errores.append(f"{u}: la salida «(por defecto)» {por_defecto} no es la columna "
                               f"«Salida por defecto» ({n['_defecto'] or '—'})")
            previos = sorted(t["desde"] for t in trans if t["hacia"] == n["id"])
            if n["_despues"] and sorted(n["_despues"]) != previos:
                errores.append(f"{u}: «Después de» {n['_despues']} no son sus predecesores {previos}")
        if n.get("_destino"):
            siguientes = sorted(t["hacia"] for t in trans if t["desde"] == n["id"])
            if sorted(n["_destino"]) != siguientes:
                errores.append(f"{donde(F, 'Eventos', ubic.split(' › ')[-1], n['id'])}: «Destino» {n['_destino']} "
                               f"no son sus transiciones {siguientes}")


def _proceso(doc: Documento, nombre: str, version: str, sec_pool: Seccion, errores: list[str]) -> dict:
    extra: dict = {}  # claves de proceso que añaden los hilos: `extra["…"] = …` dentro de su bloque
    ul = donde(F, "Pool y lanes", nombre)
    t_lanes = tabla(sec_pool, "Lane", ("Actor", "Grupo/rol", "Actor filter"), ul, errores)
    lanes = [_lane(f, donde(ul, f["Lane"]), errores) for f in filas(t_lanes)]
    ini = sec_pool.campo("Iniciador")
    iniciador = None if ini is None or vacio(ini.rstrip(".")) else codigo(ini.rstrip(".").strip()).strip()
    if ini is None:
        errores.append(f"{ul}: falta «**Iniciador**: `Actor`.» (o «—»)")
    actores_tarea = _actores_bonita(sec_pool, lanes, ul, errores)
    if actores_tarea:
        extra["actores_tarea"] = actores_tarea

    tareas = _tareas(_sub(doc, "Inventario de tareas", nombre, errores),
                     donde(F, "Inventario de tareas", nombre), errores)
    compuertas = _compuertas(_sub(doc, "Compuertas", nombre, errores), donde(F, "Compuertas", nombre), errores)
    eventos = _eventos(_sub(doc, "Eventos", nombre, errores), donde(F, "Eventos", nombre), errores)
    trans = _transiciones(_sub(doc, "Transiciones", nombre, errores), donde(F, "Transiciones", nombre), errores)

    nodos: list[dict] = []
    vistos: dict[str, dict] = {}
    inicio = [e for e in eventos if e["tipo"] == "inicio"]
    fines = [e for e in eventos if e["tipo"] == "fin"]
    bordes = [e for e in eventos if e["tipo"] == "timer_borde"]

    def agregar(n: dict, ubic: str):
        if n["id"] in vistos:
            errores.append(f"{donde(ubic, n['id'])}: el ID ya existe en el pool «{nombre}»")
            return
        vistos[n["id"]] = n
        nodos.append(n)

    for n in inicio:
        agregar(n, donde(F, "Eventos", nombre))
    for n in tareas:
        agregar(n, donde(F, "Inventario de tareas", nombre))
        for b in bordes:
            if b["anfitrion"] == n["id"]:
                agregar(b, donde(F, "Eventos", nombre))
    for b in bordes:
        if b["id"] not in vistos:
            agregar(b, donde(F, "Eventos", nombre))
    for n in compuertas:
        agregar(n, donde(F, "Compuertas", nombre))
    for n in fines:
        agregar(n, donde(F, "Eventos", nombre))
    destinos = [t["hacia"] for t in trans] + [d for g in compuertas for _, d in g["_salidas"]]
    for d in destinos:
        if d.startswith("fin_") and d not in vistos:
            agregar(_nodo(d, d, "fin"), donde(F, "Transiciones", nombre))

    _lanes_de_nodos(nodos, trans, lanes, iniciador, donde(F, "Eventos", nombre), errores)
    _comprobar_compuertas(nodos, trans, donde(F, "Compuertas", nombre), errores)
    conectores = _conectores(_sub(doc, "Conectores por tarea", nombre, errores),
                             donde(F, "Conectores por tarea", nombre), vistos, errores)
    variables = _variables(_sub(doc, "Process variables", nombre, errores),
                           donde(F, "Process variables", nombre), errores)
    # Documentos del proceso (hilo contratos-documentos, R-09): solo se emite la clave si hay alguno (G-5).
    documentos = leer_documentos(_sub(doc, "Documentos del proceso", nombre, errores),
                                 donde(F, "Documentos del proceso", nombre), errores)
    if documentos:
        extra["documentos"] = documentos
    return {"nombre": nombre, "version": version, "iniciador": iniciador, "lanes": lanes, "variables": variables,
            "nodos": nodos, "transiciones": trans, "conectores": conectores, **extra}


def leer_bpmn(doc: Documento) -> tuple[dict, list[str]]:
    errores: list[str] = []
    principal = {"nombre": doc.frontmatter.get("pool"), "version": doc.frontmatter.get("version")}
    if not principal["nombre"] or not principal["version"]:
        errores.append(f"{F}: el frontmatter debe tener «pool» y «version» del pool principal")
    sec = seccion(doc, "Pool y lanes", F, errores)
    procesos = [_proceso(doc, n, v, s, errores) for n, v, s in (pools(sec, donde(F, "Pool y lanes"), errores)
                                                                 if sec else [])]
    if principal["nombre"] and not any(p["nombre"] == principal["nombre"] and p["version"] == principal["version"]
                                       for p in procesos):
        errores.append(f"{donde(F, 'Pool y lanes')}: el pool principal «{principal['nombre']}» "
                       f"{principal['version']} del frontmatter no tiene subsección")
    return {"principal": principal, "procesos": procesos}, errores
