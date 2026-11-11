"""Lector de la tabla de `bpmn.md › Documentos del proceso › `Pool` versión` (R-09, hilo `contratos-documentos`).

| Documento | Múltiple | Atributo del BDM (opcional) | Tarea que lo aporta | Tareas que lo leen | Fuente en §12 |

- Documento: token, nombre del `process:Document` del pool.
- Múltiple: `sí` (lista de documentos) o `no`, con paréntesis opcional.
- Atributo del BDM: opcional e informativa (`Objeto.atributo` que guarda el ID); `generadores.validar` comprueba que
  existe y es `LONG`.
- Tarea que lo aporta: tokens de tareas o «(instanciación)». `generadores.validar.contratos_documentos` lo compara con
  los contextos cuyos inputs FILE llevan «doc. `<documento>`».
- Tareas que lo leen, Fuente: informativas.
"""
from __future__ import annotations

import re

from generadores.leer import columna, donde, filas, si_no, tabla, vacio
from generadores.md import Seccion, codigo

INSTANCIACION = "(instanciacion)"
COLUMNAS = ("Múltiple", "Tarea que lo aporta")
_BACKTICKS = re.compile(r"`([^`]+)`")
_INSTANCIACION = re.compile(r"\(instanciaci[oó]n\)", re.I)


def _aportan(celda: str) -> list[str]:
    if vacio(celda):
        return []
    out = [INSTANCIACION] if _INSTANCIACION.search(celda) else []
    return out + [t for t in _BACKTICKS.findall(celda) if t not in out]


def leer_documentos(sec: Seccion | None, ubic: str, errores: list[str]) -> list[dict]:
    """Documentos del pool: `[{nombre, multiple, aportan, atributo}]` en el orden de la tabla."""
    out = []
    for f in filas(tabla(sec, "Documento", COLUMNAS, ubic, errores)):
        nombre = codigo(f["Documento"]).strip()
        u = donde(ubic, nombre)
        if not re.fullmatch(r"[A-Za-z_]\w*", nombre):
            errores.append(f"{u}: «{nombre}» no vale como nombre de documento (letras, dígitos y «_»)")
        atributo = None
        try:
            celda = columna(f, "Atributo")
        except KeyError:
            celda = None
        if celda is not None and not vacio(celda):
            atributo = codigo(celda).strip()
            if not re.fullmatch(r"[A-Z]\w*\.\w+", atributo):
                errores.append(f"{u}: Atributo del BDM «{celda}» debe ser «`Objeto.atributo`»")
        out.append({"nombre": nombre, "multiple": si_no(f["Múltiple"], u, errores),
                    "aportan": _aportan(columna(f, "Tarea que lo aporta")), "atributo": atributo})
    return out
