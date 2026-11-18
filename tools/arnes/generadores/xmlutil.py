"""Utilidades XML compartidas por los generadores: escritura determinista e IDs estables."""
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path


def xml_bytes(arbol: ET.ElementTree) -> bytes:
    """`arbol` serializado con sangría de 2 espacios, declaración con comillas dobles, LF y salto final."""
    ET.indent(arbol, space="  ")
    cuerpo = ET.tostring(arbol.getroot(), encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + cuerpo + "\n").encode("utf-8")


def escribir_xml(arbol: ET.ElementTree, ruta: Path) -> None:
    """Escribe `arbol` en `ruta` con el formato de `xml_bytes`."""
    Path(ruta).write_bytes(xml_bytes(arbol))


class Ids:
    """IDs deterministas: `_h<sha1(semilla)[:8]><NNNN>`. La semilla (p. ej. nombre y versión del pool) hace
    que dos procesos, o dos versiones, no compartan IDs ni nombre de `.conf`."""

    def __init__(self, semilla: str):
        self._prefijo = "h" + hashlib.sha1(semilla.encode("utf-8")).hexdigest()[:8]
        self._n = 0

    def siguiente(self) -> str:
        self._n += 1
        return f"_{self._prefijo}{self._n:04d}"
