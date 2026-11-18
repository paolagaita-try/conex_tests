"""Lector de `docs/07-bonita/bdm.md`: BDM, organización, perfiles, parámetros y decisión de persistencia."""
from __future__ import annotations

import re

from generadores.leer import columna, donde, filas, seccion, si_no, sin_parentesis, tabla, vacio
from generadores.leer.organizacion import leer_organizacion
from generadores.md import Documento, codigo

F = "bdm.md"
_OBJETO = re.compile(r"^`(\w+)`(?:\s*\(paquete `([\w.]+)`\))?$")
_PARAM_CONSULTA = re.compile(r"`(\w+)`\s*\((\w+)\)")
_BACKTICKS = re.compile(r"`([^`]+)`")
# «`Equipo Compras` (roles `a`, `b`)»: el nombre del perfil puede llevar espacios (R-16).
_PERFIL = re.compile(r"`([^`]+)`\s*\(rol(?:es)?\s+([^)]*)\)")


def _primer_codigo(texto: str | None) -> str | None:
    if not texto:
        return None
    m = _BACKTICKS.search(texto)
    return m.group(1) if m else None


def _grupos_de_atributos(texto: str | None) -> list[list[str]]:
    """«`a`; `b`, `c` (explicación).» → [["a"], ["b", "c"]]. «;» separa entradas; «,» o «+» combina atributos."""
    if texto is None:
        return []
    t = sin_parentesis(texto).rstrip(".").strip()
    if vacio(t):
        return []
    out = []
    for parte in t.split(";"):
        nombres = _BACKTICKS.findall(parte) or [n for n in re.split(r"[,+\s]+", parte) if n]
        nombres = [n.strip() for n in nombres if n.strip()]
        if nombres:
            out.append(nombres)
    return out


_NOMBRE_EXPLICITO = re.compile(r"\(\s*nombre\s+`([^`]*)`\s*[;)]")


def _entradas(texto: str) -> list[str]:
    """Las entradas de una celda separadas por «;» fuera de paréntesis."""
    partes, actual, nivel = [], [], 0
    for ch in texto:
        nivel += (ch == "(") - (ch == ")")
        if ch == ";" and nivel <= 0:
            partes.append("".join(actual))
            actual = []
        else:
            actual.append(ch)
    return partes + ["".join(actual)]


def _nombres_explicitos(texto: str | None) -> dict[str, str]:
    """«`a`, `b` (nombre `IX_X`); `c`» → {"a,b": "IX_X"}: el nombre que la documentación fija a un índice o a una
    unique constraint (contrato §2.6.2); la clave son sus atributos unidos por «,». Sin marcador, el generado."""
    out: dict[str, str] = {}
    for parte in _entradas(texto or ""):
        m = _NOMBRE_EXPLICITO.search(parte)
        grupos = _grupos_de_atributos(parte)
        if m and grupos:
            out[",".join(grupos[0])] = m.group(1).strip()
    return out


def _atributo(fila: dict[str, str], ubic: str, errores: list[str]) -> dict:
    nombre = codigo(fila["Atributo"]).strip()
    u = donde(ubic, nombre)
    obligatorio = si_no(fila["Obligatorio"], u, errores)
    multiple = si_no(fila["Múltiple"], u, errores)
    longitud = None
    if not vacio(fila["Longitud"]):
        try:
            longitud = int(codigo(fila["Longitud"]))
        except ValueError:
            errores.append(f"{u}: longitud «{fila['Longitud']}» no es un entero")
    relacion = None
    celda = fila["Relación"].strip()
    if not vacio(celda):
        if celda.lower().startswith("composición") or celda.lower().startswith("composicion"):
            relacion = "composicion"
        elif celda.lower().startswith("agregación") or celda.lower().startswith("agregacion"):
            relacion = "agregacion"
        else:
            errores.append(f"{u}: relación «{celda}» debe empezar por «composición» o «agregación»")
        m = re.search(r"([01])\.\.(\d+|n|\*)", celda)
        if m:
            if (m.group(2) in ("n", "*")) != multiple:
                errores.append(f"{u}: la cardinalidad {m.group(0)} no coincide con Múltiple «{fila['Múltiple']}»")
            if (m.group(1) == "1") != obligatorio:
                errores.append(f"{u}: la cardinalidad {m.group(0)} no coincide con Obligatorio «{fila['Obligatorio']}»")
    return {"nombre": nombre, "tipo": codigo(fila["Tipo"]).strip(), "obligatorio": obligatorio,
            "multiple": multiple, "longitud": longitud, "relacion": relacion}


DEVUELVE = {"lista": ("lista", False), "lista paginada": ("lista", True), "uno": ("uno", False),
            "conteo": ("conteo", False)}


def devuelve(celda: str) -> tuple[str, bool] | None:
    """«lista», «lista paginada», «uno» o «conteo», con paréntesis explicativo opcional → (devuelve, paginada).
    None si no es ninguno (R-05)."""
    return DEVUELVE.get(" ".join(sin_parentesis(celda).lower().split()))


def _consulta(fila: dict[str, str], ubic: str, errores: list[str]) -> dict:
    """Fila de la tabla «Consulta» de un objeto (R-05). «`nombre` (por defecto…)» la genera Bonita: sin JPQL y fuera
    de `bom.xml`. Devuelve `lista paginada` exige su `countFor…` (lo comprueba `validar/organizacion.py`). Las claves
    `paginada` y `por_defecto` solo se emiten cuando valen `True` (G-5)."""
    celda = fila["Consulta"]
    nombre = (_BACKTICKS.findall(celda) or [codigo(celda)])[0].strip()
    u = donde(ubic, nombre)
    parametros = [{"nombre": n, "tipo": t} for n, t in _PARAM_CONSULTA.findall(fila["Parámetros"])]
    if not parametros and not vacio(fila["Parámetros"]):
        errores.append(f"{u}: parámetros «{fila['Parámetros']}» deben ser «`nombre` (TIPO)»")
    leido = devuelve(fila["Devuelve"])
    if leido is None:
        errores.append(f"{u}: Devuelve «{fila['Devuelve'].strip()}» debe ser «lista», «lista paginada», «uno» o "
                       "«conteo»")
        leido = (fila["Devuelve"].strip(), False)
    q = {"nombre": nombre, "jpql": None, "parametros": parametros, "devuelve": leido[0]}
    if leido[1]:
        q["paginada"] = True
    if re.search(r"\(\s*por defecto", celda):
        q["por_defecto"] = True
    return q


def _objetos(doc: Documento, paquete: str | None, errores: list[str]) -> list[dict]:
    ubic = donde(F, "Objetos de negocio")
    sec = seccion(doc, "Objetos de negocio", F, errores)
    objetos = []
    for h in sec.hijas if sec else []:
        m = _OBJETO.match(h.titulo)
        if not m:
            errores.append(f"{donde(ubic, h.titulo)}: el título debe ser «`Objeto` (paquete `x.y`)»")
            continue
        nombre = m.group(1)
        u = donde(ubic, nombre)
        if m.group(2) and paquete and m.group(2) != paquete:
            errores.append(f"{u}: paquete «{m.group(2)}» distinto del de Convenciones «{paquete}»")
        t_atr = tabla(h, "Atributo", ("Tipo", "Obligatorio", "Múltiple", "Longitud", "Relación"), u, errores)
        if not any(t and list(t[0])[0] == "Atributo" for t in h.tablas):
            errores.append(f"{u}: falta la tabla de atributos")
        t_con = tabla(h, "Consulta", ("Parámetros", "Devuelve"), u, errores)
        objeto = {
            "nombre": nombre,
            "atributos": [_atributo(f, u, errores) for f in filas(t_atr)],
            "unicos": _grupos_de_atributos(h.campo("Unique constraints")),
            "consultas": [_consulta(f, u, errores) for f in filas(t_con)],
            "indices": _grupos_de_atributos(h.campo("Índices")),
        }
        # Nombres explícitos de índices y unique constraints (hilo `huecos-generador`); solo si los hay (G-5).
        for clave, campo in (("unicos", "Unique constraints"), ("indices", "Índices")):
            if explicitos := _nombres_explicitos(h.campo(campo)):
                objeto[f"nombres_{clave}"] = explicitos
        objetos.append(objeto)
    return objetos


def _organizacion(doc: Documento, errores: list[str]) -> dict:
    """Organización (`leer.organizacion`, Plan 5 R-01), contraseña de prueba y perfiles previstos (R-16: el nombre del
    perfil admite espacios y acentos: «`Equipo Compras` (roles `a`, `b`)»)."""
    ubic = donde(F, "Organización")
    org = {"grupos": [], "roles": [], "usuarios": [], "actores": {}, "perfiles": [], "contrasena": None}
    sec = seccion(doc, "Organización", F, errores)
    if sec is None:
        return org
    leida = leer_organizacion(sec, ubic, errores)
    membresias = leida.pop("membresias", None)
    org.update(leida)
    org["contrasena"] = _primer_codigo(sec.campo("Contraseña de prueba"))
    if not org["contrasena"]:
        errores.append(f"{ubic}: falta «**Contraseña de prueba**: `…`»")
    acceso = seccion(doc, "Acceso al BDM", F, errores)
    perfiles = acceso.campo("Perfiles previstos") if acceso else None
    if perfiles is not None and not vacio(perfiles.rstrip(".")) and "ninguno" not in perfiles.lower():
        encontrados = _PERFIL.findall(perfiles)
        if not encontrados:
            errores.append(f"{donde(F, 'Acceso al BDM', 'Perfiles previstos')}: «{perfiles}» debe ser "
                           "«`Perfil` (rol `r`)» o «`Perfil` (roles `a`, `b`)», separados por «; »")
        for nombre, roles in encontrados:
            org["perfiles"].append({"nombre": nombre.strip(), "roles": _BACKTICKS.findall(roles)})
    if membresias:
        org["membresias"] = membresias
    return org


REPR_NEGOCIO = "módulo de parámetros"
REPR_ALIAS_NEGOCIO = "objeto de negocio de catálogo"  # compatibilidad con la v0.8.0
REPR_TECNICO = "parámetro de proceso"
# La plantilla de documentación (P, tarea 19) llama a la columna «Módulo / parámetro de proceso»; la v0.8.0 la llamaba
# «Objeto / parámetro de proceso». Se admiten las dos.
COLUMNAS_DESTINO = ("Módulo / parámetro de proceso", "Objeto / parámetro de proceso")


def _parametros(doc: Documento, errores: list[str]) -> tuple[dict[str, list[dict]], list[str], list[str]]:
    """(técnicos por pool con valores por entorno, nombres de los parámetros de negocio del módulo, todos los
    `param_*` que la tabla declara —con cualquier representación—)."""
    ubic = donde(F, "Parámetros")
    sec = seccion(doc, "Parámetros", F, errores)
    if sec is None:
        return {}, [], []
    definicion = valores = None
    for t in sec.tablas:
        if t and list(t[0])[0] == "`param_*`":
            if "Local" in t[0]:
                valores = t
            else:
                definicion = t
    destino = next((c for c in COLUMNAS_DESTINO if definicion and any(k.startswith(c) for k in definicion[0])),
                   COLUMNAS_DESTINO[0])
    for t, columnas in ((definicion, ("Tipo en el catálogo", "Representación", destino)),
                        (valores, ("Local", "Qualification", "Production"))):
        faltan = [c for c in columnas if t and not any(k.startswith(c) for k in t[0])]
        if faltan:
            errores.append(f"{ubic}: a la tabla «`param_*` | …» le faltan las columnas {faltan}")
            return {}, [], []
    tecnicos_def = [f for f in filas(definicion) if f["Representación"].strip() == REPR_TECNICO]
    if tecnicos_def and valores is None:
        errores.append(f"{ubic}: falta la tabla de valores por entorno «| `param_*` | Local | Qualification | "
                       "Production |»")
    por_nombre = {codigo(f["`param_*`"]).strip(): f for f in filas(valores)}
    out: dict[str, list[dict]] = {}
    negocio: list[str] = []
    for f in filas(definicion):
        nombre = codigo(f["`param_*`"]).strip()
        u = donde(ubic, nombre)
        representacion = f["Representación"].strip()
        if representacion in (REPR_NEGOCIO, REPR_ALIAS_NEGOCIO):
            if nombre in negocio:
                errores.append(f"{u}: parámetro repetido")
            if nombre in por_nombre:
                errores.append(f"{u}: es del módulo de parámetros (negocio) y tiene fila en la tabla de valores por "
                               "entorno: sus valores son los del catálogo, que se administran en la app de "
                               "parámetros; quita la fila o hazlo parámetro de proceso")
            negocio.append(nombre)
            continue
        if representacion != REPR_TECNICO:
            errores.append(f"{u}: representación «{representacion}» no soportada "
                           f"(solo «{REPR_NEGOCIO}» o «{REPR_TECNICO}»)")
            continue
        partes = _BACKTICKS.findall(columna(f, destino))
        if len(partes) != 2 or partes[1] != nombre:
            errores.append(f"{u}: «{destino}» debe ser «`<Pool>` › `{nombre}`»")
            continue
        fila_v = por_nombre.get(nombre)
        if fila_v is None:
            errores.append(f"{u}: falta su fila en la tabla de valores por entorno (Local, Qualification, Production)")
            continue
        out.setdefault(partes[0], []).append({
            "nombre": nombre, "tipo": f["Tipo en el catálogo"].strip(),
            "valores": {e: codigo(fila_v[e]).strip() for e in ("Local", "Qualification", "Production")}})
    declarados = list(dict.fromkeys(codigo(f["`param_*`"]).strip() for f in filas(definicion)))
    for nombre in por_nombre:
        if nombre not in declarados:
            errores.append(f"{donde(ubic, nombre)}: tiene valores por entorno pero no está en la tabla de parámetros")
    return out, negocio, declarados


def _persistencia(doc: Documento, errores: list[str]) -> dict:
    ubic = donde(F, "Decisión de persistencia")
    out = {"business_variables": [], "plantilla": None, "plantillas": []}
    sec = seccion(doc, "Decisión de persistencia", F, errores)
    if sec is None:
        return out
    por_decision = {f["Decisión"].strip(): f["Valor"] for f in filas(tabla(sec, "Decisión", ("Valor",), ubic, errores))}
    bv = por_decision.get("Business variables del pool")
    if bv is None:
        errores.append(f"{ubic}: falta la fila «Business variables del pool»")
    elif not vacio(bv):
        for token in _BACKTICKS.finditer(bv):
            trozo = token.group(1)
            m = re.fullmatch(r"\s*(\w+)\s*:\s*(\w+)\s*", trozo)
            if m:
                variable = {"nombre": m.group(1), "objeto": m.group(2)}
                # R-08: «(múltiple)», o un paréntesis que contenga la palabra, justo detrás del token. La clave solo
                # se emite cuando no es el defecto (G-5).
                detras = re.match(r"\s*\(([^()]*)\)", bv[token.end():])
                if detras and "múltiple" in detras.group(1).lower():
                    variable["multiple"] = True
                out["business_variables"].append(variable)
            else:
                errores.append(f"{donde(ubic, 'Business variables del pool')}: «{trozo}» debe ser «nombre: Objeto» "
                               "(p. ej. «`solicitud: Solicitud`; `eventos: Evento` (múltiple)»)")
    plantilla = por_decision.get("Plantilla de persistencia")
    # R-07: la familia de plantillas son los tokens de la celda, fuera de los paréntesis explicativos y antes de la
    # explicación tras « — ». `plantilla` sigue siendo la primera (lo que leía la 0.10.0).
    out["plantillas"] = _BACKTICKS.findall(sin_parentesis((plantilla or "").split(" — ")[0]))
    out["plantilla"] = out["plantillas"][0] if out["plantillas"] else _primer_codigo(plantilla)
    if not out["plantilla"]:
        errores.append(f"{ubic}: falta la fila «Plantilla de persistencia» con su valor entre backticks")
    elif not out["plantillas"]:
        out["plantillas"] = [out["plantilla"]]
    return out


def leer_bdm(doc: Documento) -> tuple[dict, list[str]]:
    errores: list[str] = []
    conv = seccion(doc, "Convenciones", F, errores)
    paquete = _primer_codigo(conv.campo("Paquete")) if conv else None
    if not paquete:
        errores.append(f"{donde(F, 'Convenciones')}: falta «**Paquete**: `x.y.z`»")
    tecnicos, negocio, declarados = _parametros(doc, errores)
    parcial = {
        "bdm": {"paquete": paquete, "objetos": _objetos(doc, paquete, errores)},
        "organizacion": _organizacion(doc, errores),
        "parametros": tecnicos,
        "parametros_negocio": negocio,
        "parametros_declarados": declarados,
        "persistencia": _persistencia(doc, errores),
    }
    return parcial, errores
