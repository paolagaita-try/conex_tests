"""Custodio de caminos: los caminos del journey cubren todas las salidas de compuerta y todos los fines.

Desde la documentación: cada salida de una compuerta exclusiva del pool principal (`bpmn.md`) aparece en las
`Salidas cubiertas` de algún camino de `caminos.md`, y cada evento de fin en el `Fin esperado` de alguno.

En modo existente el arnés no corre el journey (spec 6.8): sin `caminos.md` no hay nada que verificar.
"""
from __future__ import annotations

import sys
from pathlib import Path

from custodios import docs_de_procesos_nuevos, ejecutar, leer_doc
from generadores.existente.linea_base import modo_existente
from generadores.leer.bpmn import leer_bpmn
from generadores.leer.construccion import leer_caminos


def comprobar(proyecto: Path) -> list[str]:
    if not docs_de_procesos_nuevos(proyecto):
        return []  # unidad 0 (o modo existente sin procesos nuevos): no hay documentación que contrastar
    if modo_existente(proyecto) and not (Path(proyecto) / "docs" / "08-construccion" / "caminos.md").is_file():
        return []  # sin journey en modo existente
    bpmn, errores = leer_bpmn(leer_doc(proyecto, "07-bonita/bpmn.md"))
    caminos, err_c = leer_caminos(leer_doc(proyecto, "08-construccion/caminos.md"))
    hallazgos = [f"bpmn.md: {e}" for e in errores] + [f"caminos.md: {e}" for e in err_c]
    principal = next((p for p in bpmn["procesos"] if p["nombre"] == bpmn["principal"]["nombre"]), None)
    if principal is None:
        return hallazgos + ["bpmn.md: no hay pool principal"]
    xor = {n["id"] for n in principal["nodos"] if n["tipo"] == "xor"}
    fines = {n["id"] for n in principal["nodos"] if n["tipo"] == "fin"}
    salidas = [f"{t['desde']}→{t['hacia']}" for t in principal["transiciones"] if t["desde"] in xor]
    cubiertas = {s for c in caminos for s in c["salidas"]}
    for s in salidas:
        if s not in cubiertas:
            hallazgos.append(f"caminos.md: la salida de compuerta «{s}» de «{principal['nombre']}» no está en "
                             "las «Salidas cubiertas» de ningún camino")
    for s in sorted(cubiertas - set(salidas)):
        hallazgos.append(f"caminos.md: la salida cubierta «{s}» no es una salida de compuerta exclusiva de "
                         f"«{principal['nombre']}» en bpmn.md")
    alcanzados = {c["fin"] for c in caminos}
    for f in sorted(fines):
        if f not in alcanzados:
            hallazgos.append(f"caminos.md: el fin «{f}» de «{principal['nombre']}» no es el «Fin esperado» de "
                             "ningún camino")
    for f in sorted(alcanzados - fines):
        hallazgos.append(f"caminos.md: el «Fin esperado» «{f}» no es un evento de fin de «{principal['nombre']}»")
    return hallazgos


def main() -> int:
    return ejecutar("check_caminos", comprobar)


if __name__ == "__main__":
    sys.exit(main())
