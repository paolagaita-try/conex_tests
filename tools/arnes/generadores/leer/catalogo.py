"""Lector de `docs/00-parametros/catalogo-parametros.md`: el Catálogo de Parámetros y Catálogos.

Devuelve una fila por parámetro; `niveles` solo en una cascada de listas (contrato §2.18). La forma de «Valor(es)»
(claves, campos, caminos de la cascada) la valida `generadores/validar/parametros.py` al sembrar. Los de negocio (Representación «módulo de parámetros» en `bdm.md`) viajan a la spec
como `parametros_negocio`; los técnicos se quedan como parámetros de proceso en el `.conf`.
"""
from __future__ import annotations

import re

from generadores.leer import columna, donde, filas, tabla
from generadores.md import codigo, leer_markdown

F = "catalogo-parametros.md"
TIPOS = ("valor", "lista", "tramo", "tramo-cascada")
_COLUMNAS = ("Nombre", "Tipo", "Valor(es)", "Quién administra", "Doble control", "Origen", "Citado en")
_PARAM = re.compile(r"`(param_\w+)`")


def _padre(tipo_celda: str, valores: str) -> str | None:
    """El parámetro del que depende un `tramo-cascada`: «tramo-cascada (depende de `param_x`)»."""
    for texto in (tipo_celda, valores):
        m = re.search(r"depende de\s+`(param_\w+)`", texto)
        if m:
            return m.group(1)
    return None


_NIVELES = re.compile(r"niveles\s+((?:`[^`]+`(?:\s*,\s*)?)+)")


def _niveles(tipo: str, tipo_celda: str, padre: str | None, u: str, errores: list[str]) -> list[str] | None:
    """Los niveles de una cascada de listas (contrato §2.18): «tramo-cascada (depende de `param_x`; niveles `a`, `b`)».
    Cada nivel es una lista que depende de la anterior; la primera, de la lista padre."""
    m = _NIVELES.search(tipo_celda)
    if m is None:
        return None
    niveles = [n.strip() for n in re.findall(r"`([^`]+)`", m.group(1))]
    if tipo != "tramo-cascada":
        errores.append(f"{u}: «niveles» solo vale en un tramo-cascada (es una cascada de listas)")
    elif padre is None:
        errores.append(f"{u}: los niveles necesitan su lista padre («tramo-cascada (depende de `param_x`; niveles "
                       "`a`, `b`)»)")
    for i, n in enumerate(niveles):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", n):
            errores.append(f"{u}: nivel «{n}» debe ser un nombre sin espacios («`area`»)")
        elif n in niveles[:i]:
            errores.append(f"{u}: nivel «{n}» repetido")
    return niveles


def leer_catalogo(texto: str, errores: list[str]) -> list[dict]:
    doc = leer_markdown(texto)
    sec = next((x for x in doc.raiz._recorrer() if x.titulo.strip() == "Catálogo"), None)
    if sec is None:
        errores.append(f"{F}: falta la sección «Catálogo»")
    t = tabla(sec, "ID", _COLUMNAS, donde(F, "Catálogo"), errores)
    if t is None:
        if sec is not None and not any(tb and list(tb[0])[0] == "ID" for tb in sec.tablas):
            errores.append(f"{donde(F, 'Catálogo')}: falta la tabla «| ID | Nombre | Tipo | … |»")
        return []
    out: list[dict] = []
    for f in filas(t):
        id_ = codigo(f["ID"]).strip()
        u = donde(F, "Catálogo", id_)
        if not _PARAM.fullmatch(f"`{id_}`"):
            errores.append(f"{u}: el ID debe ser «`param_<nombre>`»")
        if any(o["id"] == id_ for o in out):
            errores.append(f"{u}: ID repetido")
        tipo_celda = f["Tipo"].strip()
        tipo = re.split(r"[\s(]", tipo_celda, maxsplit=1)[0]
        if tipo not in TIPOS:
            errores.append(f"{u}: tipo «{tipo_celda}» debe ser {' | '.join(TIPOS)}")
        valores = columna(f, "Valor(es)").strip()
        padre = _padre(tipo_celda, valores)
        dc = f["Doble control"].strip().lower()
        if dc not in ("sí", "si", "no"):
            errores.append(f"{u}: Doble control «{f['Doble control']}» debe ser «sí» o «no»")
        out.append({"id": id_, "nombre": f["Nombre"].strip(), "tipo": tipo, "valores": valores,
                    "administra": f["Quién administra"].strip(), "doble_control": dc in ("sí", "si"),
                    "origen": f["Origen"].strip(), "citado_en": f["Citado en"].strip(), "padre": padre})
        niveles = _niveles(tipo, tipo_celda, padre, u, errores)
        if niveles is not None:
            out[-1]["niveles"] = niveles
    ids = {o["id"] for o in out}
    for o in out:
        if o["padre"] and o["padre"] not in ids:
            errores.append(f"{donde(F, 'Catálogo', o['id'])}: su padre «{o['padre']}» no está en el catálogo")
    return out
