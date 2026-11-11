"""Lectores de la documentación (`docs/07-bonita/`, `docs/08-construccion/`) a fragmentos de la spec.

Cada módulo lee un fichero y devuelve `(parcial, errores)`. `generadores.spec` los combina. Los errores nombran
fichero › sección › fila. Una expresión Groovy que el documento pide se deja como marcador
`{"$expresion": id, "fuente": texto, "donde": ubicación}`; `construir_spec` la resuelve contra `expresiones.md`.
"""
from __future__ import annotations

import re

from generadores.md import Documento, Seccion, codigo

SEP = " › "
EXPR = "$expresion"
VACIOS = {"", "—", "-", "–"}


def donde(*partes: str) -> str:
    return SEP.join(p for p in partes if p)


def vacio(celda: str | None) -> bool:
    """Celda sin valor: vacía, «—» o «— (explicación)»."""
    if celda is None:
        return True
    c = codigo(celda).strip()
    return c in VACIOS or c.startswith("— ") or c.startswith("—(")


def plano(texto: str) -> str:
    """Texto sin backticks ni espacios repetidos (para la documentación de un elemento)."""
    return " ".join(texto.replace("`", "").split())


def sin_parentesis(texto: str) -> str:
    """Quita las explicaciones entre paréntesis (no anidadas), repetidamente."""
    anterior = None
    while anterior != texto:
        anterior, texto = texto, re.sub(r"\s*\([^()]*\)", "", texto)
    return texto.strip()


def requerir(id_: str, fuente: str, ubicacion: str) -> dict:
    return {EXPR: id_, "fuente": fuente, "donde": ubicacion}


_SI_NO = re.compile(r"(sí|si|no)\s*(\(.*\))?", re.DOTALL)


def si_no(celda: str, ubicacion: str, errores: list[str]) -> bool:
    """«sí» / «no», con un paréntesis explicativo opcional detrás: «sí (una por fila)»."""
    m = _SI_NO.fullmatch(celda.strip().lower())
    v = m.group(1) if m else celda.strip().lower()
    if v in ("sí", "si"):
        return True
    if v == "no":
        return False
    errores.append(f"{ubicacion}: «{celda}» debe ser «sí» o «no»")
    return False


def seccion(base: Documento | Seccion, prefijo: str, ubicacion: str, errores: list[str]) -> Seccion | None:
    try:
        return base.seccion(prefijo)
    except KeyError:
        errores.append(f"{ubicacion}: falta la sección «{prefijo}»")
        return None


def tabla(sec: Seccion | None, primera: str, columnas: tuple[str, ...] = (), ubicacion: str = "",
          errores: list[str] | None = None) -> list[dict[str, str]] | None:
    """La primera tabla de la sección cuya primera columna se llama `primera`.

    Si le falta alguna de `columnas` (por prefijo del título), lo anota en `errores` y devuelve None: un título de
    columna cambiado es un error del documento, no una tabla vacía.
    """
    for t in sec.tablas if sec else []:
        if t and list(t[0])[0] == primera:
            faltan = [c for c in columnas if not any(k.startswith(c) for k in t[0])]
            if faltan:
                if errores is not None:
                    errores.append(f"{ubicacion or sec.titulo}: a la tabla «{primera} | …» le faltan las columnas "
                                   f"{faltan} (formato de la plantilla)")
                return None
            return t
    return None


def filas(t: list[dict[str, str]] | None) -> list[dict[str, str]]:
    """Filas con valor (la fila de relleno «— | — | …» se descarta)."""
    return [f for f in (t or []) if not vacio(list(f.values())[0])]


def columna(fila: dict[str, str], prefijo: str) -> str:
    """Valor de la primera columna cuyo título empieza por `prefijo`."""
    for k, v in fila.items():
        if k.startswith(prefijo):
            return v
    raise KeyError(prefijo)


_POOL = re.compile(r"^`(\w+)`\s+(\S+)$")


def pools(sec: Seccion, ubicacion: str, errores: list[str]) -> list[tuple[str, str, Seccion]]:
    """Subsecciones de nivel 3 de un pool: «`Nombre` versión»."""
    out = []
    for h in sec.hijas:
        m = _POOL.match(h.titulo)
        if m:
            out.append((m.group(1), m.group(2), h))
        else:
            errores.append(f"{donde(ubicacion, h.titulo)}: el título debe ser «`<Pool>` <versión>»")
    return out


def ref_doc(texto: str) -> str | None:
    """Normaliza una referencia de la documentación: `Objeto.atributo`, `pv variable` o `bv variable` (la business
    variable entera, solo como destino de un script: R-07) → igual, sin backticks."""
    t = codigo(texto.strip()).strip()
    if re.fullmatch(r"[pb]v \w+", t) or re.fullmatch(r"[A-Z]\w*\.\w+", t):
        return t
    return None
