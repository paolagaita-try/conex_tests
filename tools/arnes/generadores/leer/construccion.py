"""Lectores de `docs/08-construccion/`: `expresiones.md`, `consultas.md` y `caminos.md`.

Huella (formato de `expresiones.md`): los 12 primeros hexadecimales del sha1 (UTF-8) del texto de origen con los
espacios colapsados a uno y sin espacios en los extremos.
"""
from __future__ import annotations

import hashlib
import json
import re

from generadores.leer import donde, filas, seccion, sin_parentesis, tabla, vacio
from generadores.md import Documento, codigo, lista

FE, FQ, FC = "expresiones.md", "consultas.md", "caminos.md"


def huella(texto: str) -> str:
    return hashlib.sha1(" ".join(texto.split()).encode("utf-8")).hexdigest()[:12]


def leer_expresiones(doc: Documento) -> tuple[dict[str, dict], list[str]]:
    errores: list[str] = []
    out: dict[str, dict] = {}
    sec = seccion(doc, "Expresiones", FE, errores)
    for f in filas(tabla(sec, "ID", ("Origen", "Huella", "Groovy"), donde(FE, "Expresiones"), errores)):
        id_ = codigo(f["ID"]).strip()
        u = donde(FE, "Expresiones", id_)
        groovy = codigo(f["Groovy"]).strip()
        if getattr(f, "sobrantes", None):
            errores.append(f"{u}: la fila tiene más celdas que columnas: un «|» del Groovy sin escapar la parte "
                           "(D-59); escríbelo «\\|» (p. ej. «a \\|\\| b»)")
        elif not groovy:
            errores.append(f"{u}: Groovy vacío")
        if id_ in out:
            errores.append(f"{u}: ID repetido")
        out[id_] = {"origen": f["Origen"].strip(), "huella": codigo(f["Huella"]).strip(), "groovy": groovy}
    return out, errores


def leer_consultas(doc: Documento) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """Las filas de `consultas.md` por (Objeto, Consulta): Bonita acota el nombre de una consulta a su objeto, así que
    `findBySolicitud` puede estar en varios objetos, una fila por objeto (contrato §2.6.1). Repetida solo si se repite
    el par."""
    errores: list[str] = []
    out: dict[tuple[str, str], dict] = {}
    sec = seccion(doc, "Consultas", FQ, errores)
    for f in filas(tabla(sec, "Consulta", ("Objeto", "Parámetros", "Devuelve", "JPQL"), donde(FQ, "Consultas"), errores)):
        nombre, objeto = codigo(f["Consulta"]).strip(), codigo(f["Objeto"]).strip()
        u = donde(FQ, "Consultas", f"{objeto}.{nombre}")
        if (objeto, nombre) in out:
            errores.append(f"{u}: consulta repetida (la misma consulta en el mismo objeto)")
        jpql = codigo(f["JPQL"]).strip()
        if not jpql:
            errores.append(f"{u}: JPQL vacía")
        out[(objeto, nombre)] = {"objeto": objeto,
                                 "parametros": [{"nombre": n, "tipo": t}
                                                for n, t in re.findall(r"`(\w+)`\s*\((\w+)\)", f["Parámetros"])],
                                 "devuelve": f["Devuelve"].strip(), "jpql": jpql}
    return out, errores


_NO_VE = re.compile(r"\(no ve `(\w+)`\)")
_DENEGADO = re.compile(r"\(denegado `([A-Z]+) ([^`]+)`\)(\s*\[subscription\])?")


def _paso_negativo(t: str, f: dict[str, str], up: str, errores: list[str]) -> dict | None:
    """Pasos negativos de un camino (contrato §2.14): «(no ve `<tarea>`)» y «(denegado `MÉTODO ruta`)» con la marca
    opcional « [subscription]»; `None` si la celda Tarea no es ninguno de los dos y `{}` si lo parece pero está mal
    escrito (con su error)."""
    usuario = f["Usuario"].strip()
    if m := _NO_VE.fullmatch(t):
        if not vacio(f["Payload"]):
            errores.append(f"{up}: el paso «(no ve …)» no lleva payload (escribe «—»)")
        return {"tarea": "(no ve)", "usuario": usuario, "objetivo": m.group(1), "evento": None, "payload": None}
    if m := _DENEGADO.fullmatch(t):
        try:
            codigos = json.loads(codigo(f["Payload"]))
        except json.JSONDecodeError:
            codigos = None
        if not (isinstance(codigos, list) and codigos and all(type(c) is int for c in codigos)):
            errores.append(f"{up}: el payload de «(denegado …)» es la lista JSON de códigos aceptados "
                           f"(«{f['Payload'].strip()}» debe ser «`[403, 404]`»)")
            codigos = []
        return {"tarea": "(denegado)", "usuario": usuario,
                "peticion": {"metodo": m.group(1), "ruta": m.group(2).strip()}, "codigos": codigos,
                "edicion": "subscription" if m.group(3) else None, "payload": None}
    if t.startswith("(no ve") or t.startswith("(denegado"):
        errores.append(f"{up}: «{t}» debe ser «(no ve `<tarea>`)» o «(denegado `MÉTODO ruta`)» "
                       "(con « [subscription]» opcional detrás)")
        return {}  # mal escrito: el error ya está; el paso no entra en la spec
    return None


def _tokens(celda: str) -> list[str]:
    return [] if vacio(celda) else re.findall(r"`([^`]+)`", sin_parentesis(celda))


def _correos(s, u: str, errores: list[str]) -> list[dict] | None:
    """«**Correos esperados**»: «—» o ausente (no se comprueba: `None`), «ninguno» (`[]`) o una tabla
    «| Asunto contiene | Para | CC |»."""
    campo = s.campo("Correos esperados")
    t = tabla(s, "Asunto contiene", ("Para", "CC"), u, errores)
    if t is None:
        if campo is None or vacio(campo):
            return None
        if campo.strip().lower().rstrip(".") == "ninguno":
            return []
        errores.append(f"{u}: «**Correos esperados**: {campo}» debe ser «—», «ninguno» o la línea vacía seguida de "
                       "la tabla «| Asunto contiene | Para | CC |»")
        return None
    if campo:
        errores.append(f"{u}: «**Correos esperados**: {campo}» contradice la tabla de correos (deja la línea vacía)")
    out = []
    for f in filas(t):
        asunto = codigo(f["Asunto contiene"]).strip()
        uf = donde(u, "Correos esperados", asunto)
        para, cc = _tokens(f["Para"]), _tokens(f["CC"])
        if not para:
            errores.append(f"{uf}: falta «Para» (`usuario@dominio`, separados por «, »)")
        out.append({"asunto": asunto, "para": para, "cc": cc})
    return out


def _consultas(s, u: str, errores: list[str]) -> list[dict]:
    """Tabla «| Consulta | Parámetros | Filas | Valores (en orden) |» (lectura de filas múltiples)."""
    out = []
    for f in filas(tabla(s, "Consulta", ("Parámetros", "Filas"), u, errores)):
        nombre = codigo(f["Consulta"]).strip()
        uf = donde(u, "Consultas esperadas", nombre)
        m = re.fullmatch(r"([A-Z]\w*)\.(\w+)", nombre)
        if not m:
            errores.append(f"{uf}: «{nombre}» debe ser «`Objeto.consulta`»")
            continue
        parametros: dict[str, str] = {}
        if not vacio(f["Parámetros"]):
            for parte in lista(f["Parámetros"]):
                mp = re.fullmatch(r"`(\w+)`\s*=\s*`([^`]*)`", sin_parentesis(parte))
                if not mp:
                    errores.append(f"{uf}: el parámetro «{parte}» debe ser «`nombre` = `valor`»")
                    continue
                parametros[mp.group(1)] = mp.group(2)
        try:
            n = int(codigo(f["Filas"]).strip())
        except ValueError:
            errores.append(f"{uf}: «Filas» debe ser un número entero («{f['Filas'].strip()}»)")
            n = 0
        valores: dict[str, list[str]] = {}
        celda = next((v for k, v in f.items() if k.startswith("Valores")), "")
        if not vacio(celda):
            for parte in lista(celda):
                mv = re.fullmatch(r"`(\w+)`\s*:\s*(.+)", parte.strip())
                if not mv:
                    errores.append(f"{uf}: «{parte}» debe ser «`atributo`: `v1`, `v2`…»")
                    continue
                valores[mv.group(1)] = re.findall(r"`([^`]*)`", mv.group(2))
        out.append({"objeto": m.group(1), "consulta": m.group(2), "parametros": parametros, "filas": n,
                    "valores": valores})
    return out


def leer_caminos(doc: Documento) -> tuple[list[dict], list[str]]:
    """Una sección «Camino `id`» por camino: **Fin esperado**, **Salidas cubiertas**, tabla de pasos y tabla de
    atributos esperados; opcionales (contrato §2.14) la línea o tabla de **Correos esperados** (clave `correos`, solo
    si se comprueba) y la tabla de consultas esperadas (clave `consultas`, solo si la hay). Los valores esperados
    quedan como texto; `generadores.spec` los tipa con el BDM."""
    errores: list[str] = []
    out = []
    for s in doc.raiz._recorrer():
        m = re.fullmatch(r"Camino `(\w+)`", s.titulo)
        if not m:
            continue
        u = donde(FC, s.titulo)
        fin = s.campo("Fin esperado")
        salidas = s.campo("Salidas cubiertas")
        if fin is None or vacio(fin):
            errores.append(f"{u}: falta «**Fin esperado**: `fin_…`»")
        if salidas is None:
            errores.append(f"{u}: falta «**Salidas cubiertas**: …» (o «—»)")
        pasos = []
        for f in filas(tabla(s, "Paso", ("Tarea", "Usuario", "Payload"), u, errores)):
            up = donde(u, f["Paso"])
            t = f["Tarea"].strip()
            espera = re.fullmatch(r"\(esperar `(\w+)`\)", t)
            if espera:
                pasos.append({"tarea": "(esperar)", "usuario": None, "evento": espera.group(1), "payload": None})
                continue
            negativo = _paso_negativo(t, f, up, errores)
            if negativo is not None:
                if negativo:
                    pasos.append(negativo)
                continue
            tarea = "(instanciacion)" if t in ("(instanciación)", "(instanciacion)") else codigo(t).strip()
            try:
                payload = json.loads(codigo(f["Payload"]))
            except json.JSONDecodeError as e:
                errores.append(f"{up}: payload no es JSON ({e})")
                payload = None
            if payload is not None and not isinstance(payload, dict):
                errores.append(f"{up}: payload debe ser un objeto JSON")
            pasos.append({"tarea": tarea, "usuario": f["Usuario"].strip(), "evento": None, "payload": payload})
        if not pasos:
            errores.append(f"{u}: falta la tabla «| Paso | Tarea | Usuario | Payload |»")
        esperado = {codigo(f["Atributo"]).strip(): codigo(f["Valor esperado"]).strip()
                    for f in filas(tabla(s, "Atributo", ("Valor esperado",), u, errores))}
        camino = {"id": m.group(1), "fin": codigo(fin or "").strip(),
                  "salidas": [codigo(x).strip() for x in lista(salidas or "") if not vacio(x)],
                  "pasos": pasos, "esperado": esperado}
        # Claves opcionales (G-5): solo cuando no son el valor por defecto.
        correos = _correos(s, u, errores)
        if correos is not None:
            camino["correos"] = correos
        consultas = _consultas(s, u, errores)
        if consultas:
            camino["consultas"] = consultas
        out.append(camino)
    if not out:
        errores.append(f"{FC}: no hay ninguna sección «Camino `<id>`»")
    return out, errores


def _clave_fila(fila: dict[str, str]) -> set[str]:
    v = list(fila.values())
    claves = {codigo(v[0])}
    if len(v) > 1:
        claves.add(f"{codigo(v[0])}→{codigo(v[1])}")
    return claves


def texto_de_origen(origen: str, id_: str, docs: dict[str, Documento]) -> str:
    """Resuelve una celda `Origen` de `expresiones.md` al texto de origen (formato descrito en su cabecera).

    `fichero › sección [› subsección…] › fila › columna` (la fila se busca por su primera celda o por
    `primera→segunda`; si varias filas casan, la única cuya celda contiene la marca del ID) o
    `fichero › sección [› subsección…] › Etiqueta:`. Si el texto contiene la marca
    (`<ID>`), el origen es el fragmento entre backticks inmediatamente anterior a la marca; si no, la celda sin backticks
    exteriores. Lanza `ValueError` si no resuelve.
    """
    partes = origen.split(" › ")
    if partes[0] not in docs:
        raise ValueError(f"fichero «{partes[0]}» desconocido")
    doc = docs[partes[0]]
    etiqueta = partes[-1].endswith(":")
    rutas = partes[1:-1] if etiqueta else partes[1:-2]
    if not rutas:
        raise ValueError("faltan sección y fila o etiqueta")
    try:
        sec = doc.seccion(rutas[0])
        for r in rutas[1:]:
            sec = sec.seccion(r)
    except KeyError as e:
        raise ValueError(str(e)) from None
    if etiqueta:
        lineas = [l.strip().removeprefix("- ") for l in sec.texto.splitlines()]
        coincidencias = [l for l in lineas if l.startswith(partes[-1])]
        if len(coincidencias) != 1:
            raise ValueError(f"{len(coincidencias)} líneas empiezan por «{partes[-1]}»")
        texto = coincidencias[0]
    else:
        fila_buscada, col = partes[-2:]
        encontradas = [f for t in sec.tablas for f in t if fila_buscada in _clave_fila(f)]
        if len(encontradas) > 1:
            # Varias filas con la misma clave (el mismo conector invocado varias veces en una tarea, Plan 5 R-10):
            # vale la única cuya celda lleva la marca del ID.
            marcadas = [f for f in encontradas if f"(`{id_}`)" in f.get(col, "")]
            if len(marcadas) == 1:
                encontradas = marcadas
        if len(encontradas) != 1:
            raise ValueError(f"{len(encontradas)} filas con clave «{fila_buscada}»")
        if col not in encontradas[0]:
            raise ValueError(f"no hay columna «{col}»")
        texto = encontradas[0][col]
    marca = f"(`{id_}`)"
    if marca in texto:
        m = re.search(r"`([^`]*)`\s*" + re.escape(marca), texto)
        if not m:
            raise ValueError(f"la marca {marca} no va precedida de un fragmento entre backticks")
        return m.group(1)
    return codigo(texto)
