#!/usr/bin/env python3
"""Despliega las reglas dinámicas del proyecto (R-14) en un bundle: copia `app/permisos/reglas/*.groovy` a
`<platform_conf/initial>/tenant_security_scripts` y `dynamic-permissions-checks-custom.properties` a
`<platform_conf/initial>/tenant_portal` (sitios de rest-api-authorization.adoc).

Son una función de las ediciones Subscription (Teamwork, Efficiency, Performance, Enterprise): con `edicion_destino`
`community` no se copia nada y se avisa, sin fallar. Sin reglas no se hace ni se avisa nada.

Uso: tools/reglas.py [--desarrollo] --bundle <platform_conf/initial> [--edicion community|subscription]
`--desarrollo` (lo pasa `run-journey.sh`): decide por `edicion_desarrollo`, la edición del bundle local, no por
`edicion_destino` (un proyecto Subscription se prueba en local en un bundle Community).
Salida estándar: `true` si se desplegaron reglas (el journey activa entonces
BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED), `false` si no. Avisos por la salida de errores.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

RAIZ = Path(os.environ.get("TRYCORE_PROYECTO") or Path(__file__).resolve().parent.parent).resolve()
PROPIEDADES = "dynamic-permissions-checks-custom.properties"


def edicion(proyecto: Path, clave: str = "edicion_destino") -> str:
    """`edicion_destino` (o `clave`, p. ej. `edicion_desarrollo`) de `.trycore-bonita.json` (community si falta)."""
    f = Path(proyecto) / ".trycore-bonita.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")).get(clave) or "community"
    except (OSError, ValueError):
        return "community"


def reglas(app: Path) -> list[Path]:
    carpeta = Path(app) / "permisos" / "reglas"
    return sorted(carpeta.glob("*.groovy")) if carpeta.is_dir() else []


def desplegar(app: Path, inicial: Path, ed: str) -> tuple[list[Path], list[str]]:
    """Copia las reglas bajo `inicial` (platform_conf/initial). Devuelve (copiados, avisos)."""
    grupo = reglas(app)
    if not grupo:
        return [], []
    if ed != "subscription":
        return [], [f"{len(grupo)} regla(s) dinámica(s) ({', '.join(g.stem for g in grupo)}) no se despliegan: son de "
                    "las ediciones Subscription y la edición es «community» (en Community la protección de "
                    "datos vive en las REST API extensions)"]
    copiados = []
    seg = Path(inicial) / "tenant_security_scripts"
    seg.mkdir(parents=True, exist_ok=True)
    for g in grupo:
        shutil.copyfile(g, seg / g.name)
        copiados.append(seg / g.name)
    props = Path(app) / "permisos" / PROPIEDADES
    if props.is_file():
        portal = Path(inicial) / "tenant_portal"
        portal.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(props, portal / PROPIEDADES)
        copiados.append(portal / PROPIEDADES)
    return copiados, []


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Despliega las reglas dinámicas en un bundle.")
    a.add_argument("--bundle", type=Path, required=True, help="carpeta setup/platform_conf/initial del bundle")
    a.add_argument("--edicion", choices=["community", "subscription"])
    a.add_argument("--desarrollo", action="store_true", help="la edición del bundle local (edicion_desarrollo)")
    args = a.parse_args(argv)
    ed = args.edicion or edicion(RAIZ, "edicion_desarrollo" if args.desarrollo else "edicion_destino")
    copiados, avisos = desplegar(RAIZ / "bonita-project/app", args.bundle, ed)
    for v in avisos:
        print(f"AVISO: {v}", file=sys.stderr)
    for c in copiados:
        print(f"reglas: {c}", file=sys.stderr)
    print("true" if copiados else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
