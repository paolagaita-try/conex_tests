"""Validaciones de R-15 (journey; contrato §2.14) sobre `spec["caminos"]`.

- Paso «(no ve `<tarea>`)»: usuario de la organización, tarea humana de algún pool, un paso posterior del camino la
  ejecuta (o la interrumpe un timer de borde que el camino espera: si no, no hay caso en el que comprobarlo) y el
  usuario no es candidato del actor de la tarea, salvo que la tarea tenga actor filter (el filtro decide en el motor).
- Paso «(denegado `MÉTODO ruta`)»: usuario de la organización, método HTTP conocido, ruta relativa a `baseUrl` cuyos
  huecos son `{caso}` o `{<business variable simple del pool principal>}`, códigos HTTP válidos.
- Archivos (`{"$archivo": "<nombre.ext>"}`): solo en inputs FILE (o en sus elementos si es múltiple), y todo input FILE
  del payload se envía así.
- Correos esperados: asunto y «Para» con direcciones `usuario@dominio`.
- Consultas esperadas: `Objeto.consulta` de `bdm.md` que devuelve una lista, los mismos parámetros, valores literales o
  `{<business variable simple>}`, atributos del objeto y tantos valores como filas.
"""
from __future__ import annotations

import re

from generadores.escribir.journey import nodo_de_paso
from generadores.escribir.organizacion import candidato
from generadores.leer import donde

FCAM = "caminos.md"
METODOS = ("GET", "POST", "PUT", "PATCH", "DELETE")
NO_VE, DENEGADO, ESPERAR, INSTANCIACION = "(no ve)", "(denegado)", "(esperar)", "(instanciacion)"
ARCHIVO = "$archivo"
_CORREO = re.compile(r"[^@\s`,;]+@[^@\s`,;]+\.[^@\s`,;]+")
_NOMBRE_ARCHIVO = re.compile(r"[^/\\\s][^/\\]*")
_HUECO = re.compile(r"\{([^{}]*)\}")


def filtro_de(proceso: dict, tarea: str) -> str | None:
    """Actor filter efectivo de una tarea humana (§2.5): el de su actor de tarea si lo tiene; si no, el de su lane.
    Lee las claves de §3.2 (`actores_tarea`, `lanes[].filtro`), ausentes = sin filtro."""
    for a in proceso.get("actores_tarea", []):
        if tarea in a.get("tareas", []):
            return a.get("filtro")
    lane = next((n.get("lane") for n in proceso.get("nodos", []) if n.get("id") == tarea), None)
    return next((l.get("filtro") for l in proceso.get("lanes", []) if l.get("nombre") == lane), None)


def es_archivo(v) -> bool:
    return isinstance(v, dict) and ARCHIVO in v


def _contiene_archivo(v) -> bool:
    if es_archivo(v):
        return True
    if isinstance(v, dict):
        return any(_contiene_archivo(x) for x in v.values())
    if isinstance(v, list):
        return any(_contiene_archivo(x) for x in v)
    return False


def _archivo_valido(v) -> bool:
    return (isinstance(v, dict) and set(v) == {ARCHIVO} and isinstance(v[ARCHIVO], str)
            and bool(_NOMBRE_ARCHIVO.fullmatch(v[ARCHIVO])))


def _revisar_valor(valor, inp: dict, ruta: str, up: str, err: list[str]) -> None:
    if valor is None:
        return
    tipo, multiple = inp.get("tipo"), inp.get("multiple")
    if tipo == "FILE":
        if multiple and not isinstance(valor, list):
            err.append(f"{up}: «{ruta}» es un FILE múltiple: va una lista de «{{\"$archivo\": \"<nombre.ext>\"}}»")
            return
        for e in (valor if multiple else [valor]):
            if e is not None and not _archivo_valido(e):
                err.append(f"{up}: «{ruta}» es un input FILE: se envía como «{{\"$archivo\": \"<nombre.ext>\"}}» "
                           "(un nombre de fichero sin carpetas)")
        return
    if tipo == "COMPLEX":
        hijos = {h.get("nombre"): h for h in inp.get("hijos", [])}
        for e in (valor if multiple and isinstance(valor, list) else [valor]):
            if not isinstance(e, dict):
                if _contiene_archivo(e):
                    err.append(f"{up}: «{ruta}»: «$archivo» solo vale en un input FILE")
                continue
            for k, v in e.items():
                if k in hijos:
                    _revisar_valor(v, hijos[k], f"{ruta}.{k}", up, err)
                elif _contiene_archivo(v):
                    err.append(f"{up}: «{ruta}.{k}»: «$archivo» solo vale en un input FILE")
        return
    if _contiene_archivo(valor):
        err.append(f"{up}: «{ruta}» es {tipo}: «$archivo» solo vale en un input FILE")


def _archivos(paso: dict, procesos: list[dict], up: str, err: list[str]) -> None:
    payload = paso.get("payload")
    if not isinstance(payload, dict):
        return
    tarea = paso.get("tarea")
    if tarea == INSTANCIACION:
        proceso = procesos[0]
    else:
        try:
            proceso, _ = nodo_de_paso(procesos, tarea, {"humana"}, "una tarea humana")
        except ValueError:
            return  # ya lo dice _validar_caminos
    inputs = {i.get("nombre"): i for i in proceso.get("contratos", {}).get(tarea, {}).get("inputs", [])}
    for clave, valor in payload.items():
        if clave in inputs:
            _revisar_valor(valor, inputs[clave], clave, up, err)
        elif _contiene_archivo(valor):
            err.append(f"{up}: «{clave}»: «$archivo» solo vale en un input FILE")


def _ejecuta_despues(objetivo: str, posteriores: list[dict], procesos: list[dict]) -> bool:
    for p in posteriores:
        if p.get("tarea") == objetivo:
            return True
        if p.get("tarea") == ESPERAR:
            try:
                _, timer = nodo_de_paso(procesos, p.get("evento"), {"timer_borde"}, "un timer de borde")
            except ValueError:
                continue
            if timer.get("anfitrion") == objetivo:
                return True
    return False


def _no_ve(paso: dict, posteriores: list[dict], spec: dict, up: str, err: list[str]) -> None:
    procesos, org = spec.get("procesos", []), spec.get("organizacion", {})
    usuario, objetivo = paso.get("usuario"), paso.get("objetivo")
    if usuario not in {u.get("nombre") for u in org.get("usuarios", [])}:
        err.append(f"{up}: el usuario «{usuario}» no está en bdm.md › Organización")
        return
    try:
        proceso, _ = nodo_de_paso(procesos, objetivo, {"humana"}, "una tarea humana")
    except ValueError as e:
        err.append(f"{up}: (no ve …): {e}")
        return
    if not _ejecuta_despues(objetivo, posteriores, procesos):
        err.append(f"{up}: (no ve `{objetivo}`): ningún paso posterior del camino ejecuta «{objetivo}» (ni lo "
                   "interrumpe un timer que el camino espera): el journey no tendría la tarea lista para comprobarlo")
    if candidato(org, proceso, objetivo, usuario) and not filtro_de(proceso, objetivo):
        err.append(f"{up}: (no ve `{objetivo}`): «{usuario}» es candidato del actor de «{objetivo}» y la tarea no tiene "
                   "actor filter: la vería siempre (cambia el usuario o declara el filtro)")


def _denegado(paso: dict, spec: dict, up: str, err: list[str]) -> None:
    org = spec.get("organizacion", {})
    usuario = paso.get("usuario")
    if usuario not in {u.get("nombre") for u in org.get("usuarios", [])}:
        err.append(f"{up}: el usuario «{usuario}» no está en bdm.md › Organización")
    peticion = paso.get("peticion") or {}
    metodo, ruta = peticion.get("metodo"), peticion.get("ruta") or ""
    if metodo not in METODOS:
        err.append(f"{up}: (denegado …): el método «{metodo}» debe ser {', '.join(METODOS)}")
    if not ruta or ruta.startswith("/") or "://" in ruta:
        err.append(f"{up}: (denegado …): la ruta «{ruta}» es relativa a la raíz de Bonita («API/…», sin «/» inicial)")
    bvs = {b.get("nombre"): b for b in (spec.get("procesos") or [{}])[0].get("business_variables", [])}
    for hueco in _HUECO.findall(ruta):
        if hueco != "caso" and (hueco not in bvs or bvs[hueco].get("multiple")):
            err.append(f"{up}: (denegado …): el hueco «{{{hueco}}}» debe ser «{{caso}}» o «{{<business variable>}}» "
                       "(simple) del pool principal")
    codigos = paso.get("codigos")
    if not codigos or not all(type(c) is int and 100 <= c <= 599 for c in codigos):
        err.append(f"{up}: (denegado …): los códigos aceptados «{codigos}» deben ser una lista de códigos HTTP")
    if paso.get("edicion") not in (None, "subscription"):
        err.append(f"{up}: (denegado …): la marca de edición «{paso.get('edicion')}» solo puede ser «[subscription]»")


def _correos(c: dict, u: str, err: list[str]) -> None:
    for m in c.get("correos") or []:
        uc = donde(u, "Correos esperados", m.get("asunto") or "")
        if not m.get("asunto"):
            err.append(f"{uc}: falta «Asunto contiene»")
        if not m.get("para"):
            err.append(f"{uc}: falta «Para»")
        for d in [*m.get("para", []), *m.get("cc", [])]:
            if not _CORREO.fullmatch(d):
                err.append(f"{uc}: «{d}» no es una dirección de correo («usuario@dominio»)")


def _consultas(c: dict, spec: dict, atributos: dict, u: str, err: list[str]) -> None:
    objetos = {o.get("nombre"): o for o in spec.get("bdm", {}).get("objetos", [])}
    bvs = {b.get("nombre"): b for b in (spec.get("procesos") or [{}])[0].get("business_variables", [])}
    for q in c.get("consultas", []):
        objeto, nombre = q.get("objeto"), q.get("consulta")
        uq = donde(u, "Consultas esperadas", f"{objeto}.{nombre}")
        if objeto not in objetos:
            err.append(f"{uq}: «{objeto}» no es un objeto de bdm.md")
            continue
        definida = next((x for x in objetos[objeto].get("consultas", []) if x.get("nombre") == nombre), None)
        if definida is None:
            err.append(f"{uq}: «{nombre}» no es una consulta de «{objeto}» en bdm.md")
            continue
        if definida.get("devuelve") != "lista":
            err.append(f"{uq}: «{nombre}» devuelve «{definida.get('devuelve')}»: el journey solo cuenta filas de "
                       "consultas que devuelven una lista")
        esperados = {p.get("nombre") for p in definida.get("parametros", [])}
        dados = set(q.get("parametros", {}))
        if dados != esperados:
            err.append(f"{uq}: parámetros {sorted(dados)} distintos de los de bdm.md {sorted(esperados)}")
        for n, v in q.get("parametros", {}).items():
            for hueco in _HUECO.findall(v):
                if hueco not in bvs or bvs[hueco].get("multiple"):
                    err.append(f"{uq}: el valor «{v}» de «{n}»: «{{{hueco}}}» no es una business variable simple del "
                               "pool principal")
        filas = q.get("filas")
        if type(filas) is not int or filas < 0:
            err.append(f"{uq}: «Filas» debe ser un entero ≥ 0")
            continue
        for a, valores in q.get("valores", {}).items():
            if a not in atributos.get(objeto, {}) and a != "persistenceId":
                err.append(f"{uq}: «{a}» no es un atributo de «{objeto}»")
            if len(valores) != filas:
                err.append(f"{uq}: «{a}» trae {len(valores)} valores y la consulta espera {filas} filas")


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    procesos = spec.get("procesos", [])
    if not procesos:
        return
    for c in spec.get("caminos", []):
        u = donde(FCAM, f"Camino `{c.get('id')}`")
        pasos = c.get("pasos", [])
        for i, paso in enumerate(pasos, 1):
            up = donde(u, str(i))
            tarea = paso.get("tarea")
            if tarea == NO_VE:
                _no_ve(paso, pasos[i:], spec, up, err)
            elif tarea == DENEGADO:
                _denegado(paso, spec, up, err)
            elif tarea != ESPERAR:
                _archivos(paso, procesos, up, err)
        _correos(c, u, err)
        _consultas(c, spec, atributos, u, err)
