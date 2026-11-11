"""Carga la matriz de versiones de Bonita (`versiones/<version>.json`)."""
import json
from pathlib import Path

from generadores.nombres import MENSAJE, VERSION_BONITA, es

RAIZ_REPO: Path = Path(__file__).resolve().parent.parent


def versiones_admitidas(raiz: Path | None = None) -> list[str]:
    """Las versiones de Bonita con matriz en `versiones/`, de menor a mayor."""
    return sorted(f.stem for f in ((raiz or RAIZ_REPO) / "versiones").glob("*.json"))


def cargar_version(version: str, raiz: Path | None = None) -> dict:
    """Devuelve la matriz de `version` tal cual está en `versiones/<version>.json`. Una versión que no tiene la forma
    `AAAA.N` falla sin buscar el fichero (nunca se resuelve una ruta fuera de `versiones/`)."""
    if not es(VERSION_BONITA, version):
        raise ValueError(f"«{version}»: {MENSAJE['version_bonita']}")
    ruta = (raiz or RAIZ_REPO) / "versiones" / f"{version}.json"
    if not ruta.is_file():
        admitidas = ", ".join(versiones_admitidas(raiz))
        raise ValueError(f"La versión {version} no está en versiones/ ({ruta}). Admitidas: {admitidas}")
    return json.loads(ruta.read_text(encoding="utf-8"))
