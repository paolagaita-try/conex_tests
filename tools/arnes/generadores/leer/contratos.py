"""Lector de `docs/07-bonita/contratos.md`: contratos (inputs y constraints) y operaciones.

Las referencias de destino se dejan como en la documentación (`Objeto.atributo`, `pv variable`); `generadores.spec`
las traduce a la business variable o process variable del pool.
"""
from __future__ import annotations

import re

from generadores.leer import columna, donde, filas, pools, ref_doc, requerir, seccion, si_no, tabla, vacio
from generadores.md import Documento, Seccion, codigo, lista

F = "contratos.md"
_BACKTICKS = re.compile(r"`([^`]+)`")
_LITERAL = re.compile(r"`([^`]+)`\s*=\s*`([^`]*)`")
_FLECHA = re.compile(r"`([^`]+)`\s*←\s*`([^`]*)`(\s*\(`(op_[^`]+)`\))?")


def _op(ref: str, tipo: str, valor, u: str, errores: list[str]) -> dict | None:
    destino = ref_doc(ref)
    if destino is None:
        errores.append(f"{u}: destino «{ref}» debe ser «Objeto.atributo» o «pv variable» (o «bv variable» como "
                       "destino de un script)")
        return None
    if destino.startswith("bv ") and tipo != "groovy":
        # R-07: la business variable entera solo la escribe un script de `expresiones.md` (devuelve el objeto o la
        # lista); un literal o un input no tienen forma de objeto.
        errores.append(f"{u}: «{destino}» (la business variable entera) solo admite un script: "
                       f"«`{destino}` ← `texto` (`op_<tarea>.{destino[3:]}`)»")
        return None
    return {"destino": destino, "expresion": {"tipo": tipo, "valor": valor}}


# ------------------------------------------------------------------ inputs (hilo contratos-documentos, R-06 y R-09)
# HIJOS := HIJO («; » HIJO)*;  HIJO := nombre «(» TIPO [«, » sí|no [«, múltiple»]] «)» [«[» HIJOS «]»]
_HIJO = re.compile(r"`?(\w+)`?\s*\(\s*(\w+)\s*(?:,\s*([^,()]*?)\s*(?:,\s*([^,()]*?)\s*)?)?\)")
_ANIDADO = re.compile(r"(.*?)\s*\[(.*)\]", re.S)
_SOLO_LECTURA = re.compile(r"—\s*\(\s*solo lectura", re.I)
_DOC = re.compile(r"doc\.\s*`([^`]+)`")
_OPS = re.compile(r"op\.\s*(`op_\w+\.\w+`(?:\s*,\s*`op_\w+\.\w+`)*)")
_POR_HIJO = re.compile(r"`?(\w+)`?\s*→\s*(.+)", re.S)
FORMA_HIJO = "«nombre (TIPO)» o «nombre (TIPO, sí|no[, múltiple])», con «[…]» tras un COMPLEX"
FORMA_DESTINO = ("«`Objeto.atributo`», «`pv variable`», «doc. `documento`», «op. `op_<contexto>.<bv>`» o "
                 "«— (solo lectura…)»")


def _partir(texto: str) -> list[str]:
    """Separa por «;» de primer nivel: respeta corchetes y paréntesis."""
    partes, nivel, actual = [], 0, ""
    for ch in texto:
        if ch in "[(":
            nivel += 1
        elif ch in "])":
            nivel -= 1
        if ch == ";" and nivel == 0:
            partes.append(actual)
            actual = ""
        else:
            actual += ch
    partes.append(actual)
    return [p.strip() for p in partes if p.strip()]


def _hijos(celda: str, obligatorio_padre: bool, u: str, errores: list[str]) -> list[dict]:
    """Hijos de un COMPLEX. Forma vieja «nombre (TIPO)»: hereda la obligatoriedad del padre y no es múltiple. Forma
    nueva «nombre (TIPO, sí|no[, múltiple])»: obligatoriedad propia (`obligatorio_propio`)."""
    out = []
    for parte in _partir(celda):
        cabeza, sub = parte, None
        m = _ANIDADO.fullmatch(parte)
        if m:
            cabeza, sub = m.group(1), m.group(2)
        m = _HIJO.fullmatch(cabeza.strip())
        if not m:
            errores.append(f"{u}: hijo «{parte}» debe ser {FORMA_HIJO}")
            continue
        nombre, tipo, obl, mul = m.groups()
        h = {"nombre": nombre, "tipo": tipo, "multiple": False, "obligatorio": obligatorio_padre, "hijos": []}
        if obl is not None:
            h["obligatorio"] = si_no(obl, donde(u, nombre), errores)
            h["obligatorio_propio"] = True
        if mul is not None:
            if mul.strip().lower() != "múltiple":
                errores.append(f"{donde(u, nombre)}: «{mul}» debe ser «múltiple» (o nada)")
            else:
                h["multiple"] = True
        if sub is not None:
            if tipo != "COMPLEX":
                errores.append(f"{donde(u, nombre)}: «[…]» solo va tras COMPLEX (el hijo es {tipo})")
            else:
                h["hijos"] = _hijos(sub, h["obligatorio"], donde(u, nombre), errores)
        elif tipo == "COMPLEX":
            errores.append(f"{donde(u, nombre)}: el hijo COMPLEX necesita sus hijos entre corchetes: "
                           "«nombre (COMPLEX, sí) [a (TEXT, sí); b (INTEGER, no)]»")
        out.append(h)
    return out


def _destino(texto: str) -> tuple[str, object]:
    """Clase y valor de una celda DESTINO (contrato §2.0): `solo_lectura`, `vacio`, `doc`, `op`, `ref` o `malo`."""
    t = texto.strip()
    if _SOLO_LECTURA.match(t):
        return "solo_lectura", None
    if vacio(t):
        return "vacio", None
    m = _DOC.fullmatch(t)
    if m:
        return "doc", m.group(1)
    m = _OPS.fullmatch(t)
    if m:
        return "op", _BACKTICKS.findall(m.group(1))
    if ref_doc(t) is not None:
        return "ref", t
    return "malo", t


def _asignar(nodo: dict, ruta: str, texto: str, u: str, ops: list[dict], documentos: list[dict],
             errores: list[str]) -> None:
    """Aplica el DESTINO `texto` al input o hijo `nodo` (ruta `ruta`)."""
    clase, valor = _destino(texto)
    if clase == "solo_lectura":
        nodo["solo_lectura"] = True
    elif clase == "op":
        nodo["por_operacion"] = valor
    elif clase == "doc":
        documentos.append({"documento": valor, "input": ruta})
    elif clase == "ref":
        op = _op(codigo(valor), "input", ruta, u, errores)
        if op:
            ops.append(op)
    elif clase == "vacio":
        errores.append(f"{u}: input sin destino (todo input tiene destino; un dato que solo lee una constraint u "
                       "operación lleva «— (solo lectura)»)")
    else:
        errores.append(f"{u}: destino «{valor}» debe ser {FORMA_DESTINO}")


def _inputs(t: list[dict] | None, ubic: str, errores: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """(inputs, operaciones por input, documentos por input) de la tabla de inputs de un contrato."""
    inputs, ops, documentos = [], [], []
    for f in filas(t):
        nombre = codigo(f["Input"]).strip()
        u = donde(ubic, nombre)
        multiple = si_no(f["Múltiple"], u, errores)
        obligatorio = si_no(f["Obligatorio"], u, errores)
        tipo = f["Tipo"].strip()
        celda_hijos = columna(f, "Hijos")
        # «Múltiple» es del input de la fila: sus hijos son campos de cada elemento, no listas (salvo «múltiple»).
        hijos = [] if vacio(celda_hijos) else _hijos(celda_hijos, obligatorio, u, errores)
        entrada = {"nombre": nombre, "tipo": tipo, "multiple": multiple, "obligatorio": obligatorio, "hijos": hijos}
        inputs.append(entrada)
        destino = f["Destino"]
        clase, _ = _destino(destino)
        if not hijos or clase in ("solo_lectura", "op"):
            _asignar(entrada, nombre, destino, u, ops, documentos, errores)
            continue
        if any(h["tipo"] == "COMPLEX" for h in hijos):
            errores.append(f"{u}: un COMPLEX con hijos COMPLEX solo admite el destino entero de su raíz "
                           "(«op. `op_<contexto>.<bv>`» o «— (solo lectura)»), no «hijo → destino»")
            continue
        asignados = {}
        for parte in _partir(destino):
            m = _POR_HIJO.fullmatch(parte.strip())
            if not m:
                errores.append(f"{u}: destino «{parte}» debe ser «hijo → destino», con destino {FORMA_DESTINO}")
                continue
            asignados[m.group(1)] = m.group(2)
        for h in hijos:
            if h["nombre"] not in asignados:
                errores.append(f"{u}: el hijo «{h['nombre']}» no tiene destino")
                continue
            _asignar(h, f"{nombre}.{h['nombre']}", asignados.pop(h["nombre"]), u, ops, documentos, errores)
        for sobra in asignados:
            errores.append(f"{u}: destino para «{sobra}», que no es un hijo del input")
    return inputs, ops, documentos


def _restricciones(t: list[dict] | None, ctx: str, ubic: str, errores: list[str]) -> list[dict]:
    out = []
    for f in filas(t):
        nombre = codigo(f["Constraint"]).strip()
        u = donde(ubic, nombre)
        expr = columna(f, "Expresión")
        mensaje = f["Mensaje de error"].strip()
        if vacio(expr):
            errores.append(f"{u}: constraint sin expresión")
        if vacio(mensaje):
            errores.append(f"{u}: constraint sin mensaje de error")
        out.append({"nombre": nombre, "groovy": requerir(f"ctr_{ctx}.{nombre}", codigo(expr), u),
                    "mensaje": mensaje})
    return out


def _tramo_de_literales(texto: str, u: str, errores: list[str]) -> None:
    """El tramo «literales: …» (hasta el «;» siguiente) es «ninguno…» o solo literales «`a` = `b`» separados por «,»
    o «y»: un literal mal escrito no genera operación y se perdería en silencio (revisión final, I-1)."""
    for m in re.finditer(r"literales\s*:\s*([^;]*)", texto):
        tramo = m.group(1).strip().rstrip(".").strip()
        if tramo.lower().startswith("ninguno"):
            continue
        resto = re.sub(r"\s*(?:,|\by\b|\be\b)\s*", "", _LITERAL.sub("", tramo)).strip()
        if resto or not _LITERAL.search(tramo):
            errores.append(f"{u}: el tramo «literales: {tramo}» tiene texto que no es un literal y no generaría "
                           "ninguna operación; cada literal se escribe «`Objeto.atributo` = `valor`» (p. ej. "
                           "`Solicitud.estado` = `pagada`), separados por «,»; sin literales, «literales: ninguno»")


def _operaciones_texto(texto: str, ctx: str, u: str, errores: list[str]) -> tuple[list[dict], str | None]:
    """Literales «`destino` = `valor`» y scripts «`destino` ← `texto` (`op_ctx.atributo`)», en orden de aparición.
    El destino de un script puede ser la business variable entera (`bv nombre`, marca `op_ctx.nombre`: R-07)."""
    m = re.search(r"plantilla `([\w-]+)`", texto) or re.match(r"\s*`([\w-]+)`\s*/", texto)
    plantilla = m.group(1) if m else None
    if plantilla is None:
        errores.append(f"{u}: las operaciones no nombran la plantilla de persistencia («plantilla `<nombre>`» o "
                       "«`<nombre>` / …», con un nombre de la fila «Plantilla de persistencia» de bdm.md, p. ej. "
                       "`asignacion-directa`)")
    _tramo_de_literales(texto, u, errores)
    encontradas = []
    for lit in _LITERAL.finditer(texto):
        op = _op(lit.group(1), "literal", lit.group(2), u, errores)
        if op:
            encontradas.append((lit.start(), op))
    for sc in _FLECHA.finditer(texto):
        destino, fuente, id_ = sc.group(1), sc.group(2), sc.group(4)
        if id_ is None:
            errores.append(f"{u}: el script «{destino} ← {fuente}» no lleva su marca (`op_{ctx}.<atributo>`)")
            continue
        atributo = re.split(r"[.\s]", destino.strip())[-1]
        if id_ != f"op_{ctx}.{atributo}":
            errores.append(f"{u}: la marca «{id_}» debe ser «op_{ctx}.{atributo}»")
        op = _op(destino, "groovy", requerir(id_, fuente, u), u, errores)
        if op:
            encontradas.append((sc.start(), op))
    return [op for _, op in sorted(encontradas, key=lambda x: x[0])], plantilla


def _contrato(sec: Seccion, ctx: str, ubic: str, errores: list[str]) -> tuple[dict, list[dict]]:
    t_inputs = tabla(sec, "Input", ("Tipo", "Múltiple", "Obligatorio", "Hijos", "Destino"), ubic, errores)
    t_constraints = tabla(sec, "Constraint", ("Expresión", "Mensaje de error"), ubic, errores)
    inputs, ops, documentos = _inputs(t_inputs, ubic, errores)
    contrato = {"inputs": inputs, "restricciones": _restricciones(t_constraints, ctx, ubic, errores)}
    if documentos:
        contrato["_documentos"] = documentos  # temporal: `spec._combinar_procesos` lo lleva a operaciones_documento
    return contrato, ops


def _instanciacion(doc: Documento, errores: list[str]) -> dict:
    out = {}
    sec = seccion(doc, "Contrato de instanciación", F, errores)
    if sec is None:
        return out
    base = donde(F, "Contrato de instanciación")
    for pool, _, s in pools(sec, base, errores):
        u = donde(base, pool)
        contrato, ops = _contrato(s, "instanciacion", u, errores)
        lineas = [l.strip() for l in s.texto.splitlines() if l.strip().startswith("Operaciones al instanciar:")]
        plantilla = None
        if len(lineas) != 1:
            errores.append(f"{u}: debe haber una línea «Operaciones al instanciar: …»")
        else:
            mas, plantilla = _operaciones_texto(lineas[0], "instanciacion", donde(u, "Operaciones al instanciar:"),
                                                errores)
            ops += mas
        out[pool] = {"contrato": contrato, "operaciones": ops, "plantilla": plantilla, "_ubic": u}
    return out


def _tareas_humanas(doc: Documento, errores: list[str]) -> dict:
    out = {}
    sec = seccion(doc, "Contratos de tarea humana", F, errores)
    base = donde(F, "Contratos de tarea humana")
    for s in sec.hijas if sec else []:
        ids = _BACKTICKS.findall(s.titulo)
        ctr = ids[0] if ids else s.titulo
        u = donde(base, ctr)
        celda = s.campo("Tarea")
        tareas = _BACKTICKS.findall(celda or "")
        if not tareas:
            errores.append(f"{u}: falta «**Tarea** (`bpmn.md`): `<id>`»")
            continue
        tarea = tareas[0]
        if ctr != f"ctr_{tarea}":
            errores.append(f"{u}: el contrato de la tarea «{tarea}» debe llamarse «ctr_{tarea}»")
        pool = re.search(r"\(pool `(\w+)`\)", celda)
        contrato, ops = _contrato(s, tarea, u, errores)
        if s.campo("Operaciones al entrar") is not None:  # R-11 no procede (veredicto): sigue siendo error
            errores.append(f"{donde(u, '**Operaciones al entrar**:')}: Bonita ejecuta las operaciones de una tarea "
                           "humana al completarla; usa una tarea script previa (las operaciones de esta tarea van en "
                           "«**Operaciones**:»)")
        texto_ops = s.campo("Operaciones")
        plantilla = None
        if texto_ops is None:
            errores.append(f"{u}: falta «**Operaciones**: …»")
        else:
            mas, plantilla = _operaciones_texto(texto_ops, tarea, donde(u, "**Operaciones**:"), errores)
            ops += mas
        if tarea in out:
            errores.append(f"{u}: la tarea «{tarea}» ya tiene contrato")
        out[tarea] = {"pool": pool.group(1) if pool else None, "contrato": contrato, "operaciones": ops,
                      "plantilla": plantilla, "_ubic": u}
    return out


def _servicio(doc: Documento, errores: list[str]) -> dict:
    out = {}
    sec = seccion(doc, "Operaciones de tareas de servicio y script", F, errores)
    base = donde(F, "Operaciones de tareas de servicio y script")
    for f in filas(tabla(sec, "Tarea", ("Conector", "Operaciones", "Escribe", "Process variables"), base, errores)):
        tarea = codigo(f["Tarea"]).strip()
        u = donde(base, tarea)
        celda = columna(f, "Operaciones")
        if vacio(celda):
            ops, plantilla = [], None  # «—» o «— (sin escritura)»: sin operaciones, no hace falta nombrar plantilla
        else:
            ops, plantilla = _operaciones_texto(celda, tarea, donde(u, "Operaciones"), errores)
        out[tarea] = {"pool": None, "operaciones": ops, "plantilla": plantilla, "_ubic": u,
                      "_conector": None if vacio(f["Conector"]) else codigo(f["Conector"]).strip(),
                      "_escribe": _BACKTICKS.findall(f["Escribe"]),
                      "_pv": [] if vacio(f["Process variables"]) else
                      [x.strip() for x in (_BACKTICKS.findall(f["Process variables"]) or
                                           f["Process variables"].split(","))]}
    return out


def leer_contratos(doc: Documento) -> tuple[dict, list[str]]:
    errores: list[str] = []
    return {"instanciacion": _instanciacion(doc, errores), "tareas": _tareas_humanas(doc, errores),
            "servicio": _servicio(doc, errores)}, errores
