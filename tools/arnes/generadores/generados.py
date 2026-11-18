"""Qué rutas de un proyecto son generadas: las reescribe `generar` y no se editan a mano.

Fuente única para el hook guard-generados. Las rutas son relativas al proyecto, con `/`. La prueba
tests/test_generados.py comprueba contra un proyecto real que todo lo que escribe `escribir_proyecto` encaja aquí.
En modo «proyecto existente», los ficheros de la línea base (y su copia) son del proyecto, no generados.
"""
from __future__ import annotations

import fnmatch
import json
import posixpath
from pathlib import Path

# Patrones por nivel de carpeta (un `*` no cruza `/`).
PATRONES = (
    "bonita-project/bdm/bom.xml",
    "bonita-project/app/organizations/*.xml",
    "bonita-project/app/profiles/*.xml",
    "bonita-project/app/environements/*.xml",
    "bonita-project/app/diagrams/*.proc",
    "bonita-project/app/process_configurations/*.conf",
    "bonita-project/app/applications/*.xml",
    "bonita-project/parametros/semillas/*.json",
    "journey/*.postman_collection.json",
    "frontend/forms.manifest.json",
    "frontend/src/forms/*/generado/contrato.ts",
    "frontend/src/forms/*/generado/esquema.ts",
    "build/generados.json",
    "build/spec.json",
)
# El esqueleto de cada formulario (`frontend/src/forms/<id>/` fuera de `generado/`), de cada página propia y de cada
# tema (`tema.css`) NO está aquí: se escribe una vez y es del proyecto (`escribir/frontend.py`, `es_esqueleto`).
# `bonita-project/parametros/configuration.properties` NO está aquí: solo es generado su bloque entre marcadores
# (lo vigila check_generados); el resto del fichero se edita a mano.
# Ficheros de la plantilla que cumplen un patrón pero no los escribe el generador.
PLANTILLA = (
    "bonita-project/app/organizations/hola.xml",
    "bonita-project/app/environements/Qualification.xml",
    "bonita-project/app/environements/Production.xml",
    # La aplicación de administración de parámetros (módulo de parámetros, U21): de la plantilla, no del generador.
    "bonita-project/app/applications/parametros.xml",
)


APLICACIONES = "bonita-project/app/applications/*.xml"
SEMILLAS = "bonita-project/parametros/semillas/*.json"


def _encaja(rel: str, patron: str) -> bool:
    return len(rel.split("/")) == len(patron.split("/")) and fnmatch.fnmatchcase(rel, patron)


def _json(ruta: Path) -> dict:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _de_lo_nuevo(rel: str, proyecto: Path) -> bool:
    """En modo existente, una aplicación o una semilla solo es generada si la escribió `generar`: la aplicación, si
    está en `build/generados.json`; la semilla, si es la de `build/spec.json` con parámetros de negocio. Las demás son
    del proyecto (no están en la línea base, pero `generar` no las escribe)."""
    if _encaja(rel, APLICACIONES):
        lista = _json(Path(proyecto) / "build" / "generados.json").get("generados")
        return isinstance(lista, list) and rel in {posixpath.normpath(r) for r in lista if isinstance(r, str)}
    spec = _json(Path(proyecto) / "build" / "spec.json")
    if not spec.get("parametros_negocio"):
        return False
    nombre = (spec.get("proyecto") or {}).get("nombre") or Path(proyecto).name
    return rel == f"bonita-project/parametros/semillas/{nombre}.json"


def es_generado(rel: str, proyecto: Path | None = None) -> bool:
    """¿`rel` lo reescribe `generar`? Con `proyecto` en modo existente, un fichero de la línea base o su copia en
    `.trycore-bonita-linea-base/` no lo es: solo lo cambia la cirugía confirmada; una aplicación o una semilla de
    parámetros solo lo es si la escribió `generar` (`_de_lo_nuevo`). Sin `proyecto`, solo por la ruta."""
    rel = posixpath.normpath(rel)
    if rel in PLANTILLA:
        return False
    if proyecto is not None:
        # Diferido: el modo existente importa el generador entero.
        from generadores.existente.linea_base import COPIA, es_existente, modo_existente
        if modo_existente(proyecto):
            if rel.startswith(f"{COPIA.as_posix()}/") or es_existente(proyecto, rel):
                return False
            if _encaja(rel, APLICACIONES) or _encaja(rel, SEMILLAS):
                return _de_lo_nuevo(rel, proyecto)
    return any(_encaja(rel, p) for p in PATRONES)
