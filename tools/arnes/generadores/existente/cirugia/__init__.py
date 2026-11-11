"""Cirugía: aplica los cambios confirmados sobre los ficheros hechos en el Studio editando el texto por rangos.

Lo que no se toca queda idéntico byte a byte (ver `generadores.existente.xmi`). Cada módulo recibe solo los cambios
confirmados de su clase y lanza `NotImplementedError` ante una operación fuera de la spec 6.7 y `ValueError` ante un
cambio que no cuadra con el fichero (todo o nada: el llamador no escribe nada si algo falla)."""
import xml.etree.ElementTree as ET

from generadores.existente.xmi import Nodo


def operacion(cambio: dict) -> str:
    """`agrega`, `modifica` o `quita`: lo confirmado si viene, y si no lo documentado."""
    return cambio.get("confirmado") or cambio["cambio"]


def hijos_de(nodos: list[Nodo], posicion: int, tag: str | None = None) -> list[tuple[int, Nodo]]:
    """`(posición, nodo)` de los hijos directos del nodo en `posicion`, en orden del documento."""
    return [(i, n) for i, n in enumerate(nodos) if n.padre == posicion and (tag is None or n.tag == tag)]


def salto_de(texto: str) -> str:
    return "\r\n" if "\r\n" in texto else "\n"


def local(elemento: ET.Element) -> str:
    return elemento.tag.rsplit("}", 1)[-1]
