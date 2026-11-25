#!/usr/bin/env python3
"""Re-aplica el permiso GET|extension/preventa en frontend/forms.manifest.json.

Excepción temporal (opción B): el generador del arnés (tools/arnes.sh generar) escribe el
manifiesto y solo declara las REST API extensions del arnés (consultas, parametros). Los
formularios de negocio leen además la extensión propia `preventa` (preventaContexto), así que
después de cada `generar` hay que correr:

    PYTHONUTF8=1 python scripts/parche-manifest-preventa.py

Es idempotente: si el permiso ya está, no cambia nada. Excepción hasta que el arnés soporte
permisos de APIs propias en el manifiesto. Detalle en
docs/08-construccion/formularios-v2.md › «Excepción: permiso extension/preventa».
"""
import json
import sys
from pathlib import Path

PERMISO = "GET|extension/preventa"
FORMULARIOS = ("frm10ValidarSolicitud", "frm20DisenarPropuesta", "frmOverview")
MANIFIESTO = Path(__file__).resolve().parent.parent / "frontend" / "forms.manifest.json"


def main() -> int:
    datos = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    por_id = {f["id"]: f for f in datos.get("formularios", [])}
    faltan = [i for i in FORMULARIOS if i not in por_id]
    if faltan:
        print(f"ERROR: el manifiesto no tiene {faltan}", file=sys.stderr)
        return 1
    cambiados = []
    for i in FORMULARIOS:
        permisos = por_id[i].setdefault("permisos", [])
        if PERMISO not in permisos:
            permisos.append(PERMISO)
            cambiados.append(i)
    if cambiados:
        MANIFIESTO.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
        print(f"permiso {PERMISO} añadido a: {', '.join(cambiados)}")
    else:
        print(f"sin cambios: {PERMISO} ya estaba en {', '.join(FORMULARIOS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
