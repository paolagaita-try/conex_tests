"""Custodio de expresiones: lo que la documentación pide en lenguaje natural tiene su Groovy fijado y vigente.

Recorre los marcadores `$expresion` que dejan los lectores de `bdm.md` (también su tabla de actor filters),
`bpmn.md` y `contratos.md`: cada uno necesita
una fila en `expresiones.md` cuya huella coincida con el texto de origen y cuyo `Origen` resuelva a ese mismo texto.
Una fila que nadie pide también es un hallazgo (Groovy huérfano).
"""
from __future__ import annotations

import sys
from pathlib import Path

from custodios import docs_de_procesos_nuevos, ejecutar, leer_doc
from generadores.leer import EXPR
from generadores.leer.bdm import leer_bdm
from generadores.leer.bpmn import leer_bpmn
from generadores.leer.construccion import huella, leer_expresiones, texto_de_origen
from generadores.leer.contratos import leer_contratos
from generadores.leer.extensiones import leer_filtros

_DOCS = {"bdm.md": leer_bdm, "bpmn.md": leer_bpmn, "contratos.md": leer_contratos}


def _marcadores(x):
    if isinstance(x, dict):
        if EXPR in x:
            yield x
        else:
            for v in x.values():
                yield from _marcadores(v)
    elif isinstance(x, list):
        for v in x:
            yield from _marcadores(v)


def comprobar(proyecto: Path) -> list[str]:
    if not docs_de_procesos_nuevos(proyecto):
        return []  # unidad 0 (o modo existente sin procesos nuevos): no hay documentación que contrastar
    hallazgos: list[str] = []
    docs = {n: leer_doc(proyecto, f"07-bonita/{n}") for n in _DOCS}
    pedidas: list[dict] = []
    for n, lector in _DOCS.items():
        parcial, errores = lector(docs[n])
        hallazgos += [f"{n}: {e}" for e in errores]
        pedidas += list(_marcadores(parcial))
    # Entradas de los actor filters de bdm.md › Organización (`flt_<filtro>.<entrada>`), que lee otro lector.
    filtros, errores = leer_filtros(docs["bdm.md"])
    hallazgos += [f"bdm.md: {e}" for e in errores]
    pedidas += list(_marcadores(filtros))
    filas, errores = leer_expresiones(leer_doc(proyecto, "08-construccion/expresiones.md"))
    hallazgos += [f"expresiones.md: {e}" for e in errores]
    vistas: dict[str, str] = {}
    for m in pedidas:
        id_, fuente, donde = m[EXPR], m["fuente"], m["donde"]
        if id_ in vistas:
            hallazgos.append(f"{donde}: el ID «{id_}» ya lo usa {vistas[id_]}")
            continue
        vistas[id_] = donde
        fila = filas.get(id_)
        if fila is None:
            hallazgos.append(f"{donde}: falta la fila «{id_}» en expresiones.md (texto «{fuente}»)")
            continue
        if fila["huella"] != huella(fuente):
            hallazgos.append(f"expresiones.md › {id_}: la huella {fila['huella']} no coincide con el texto de "
                             f"origen «{fuente}» ({huella(fuente)}); la documentación cambió y la fila no")
        try:
            origen = texto_de_origen(fila["origen"], id_, docs)
            if " ".join(origen.split()) != " ".join(fuente.split()):
                hallazgos.append(f"expresiones.md › {id_}: el Origen «{fila['origen']}» apunta a «{origen}», no a "
                                 f"{donde}")
        except ValueError as e:
            hallazgos.append(f"expresiones.md › {id_}: el Origen «{fila['origen']}» no resuelve ({e})")
    for id_ in filas:
        if id_ not in vistas:
            hallazgos.append(f"expresiones.md › {id_}: ninguna parte de la documentación pide esta expresión "
                             "(fila sin uso)")
    return hallazgos


def main() -> int:
    return ejecutar("check_expresiones", comprobar)


if __name__ == "__main__":
    sys.exit(main())
