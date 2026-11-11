"""Nombres que acaban en rutas, poms o XML: solo se admiten nombres simples.

Lo que llega de `.trycore-bonita.json`, de la línea de órdenes o de la documentación termina en nombres de fichero
(`<nombre>.xml`, `<pool>-<versión>.proc`, `versiones/<versión>.json`) o dentro de un pom. Un `../`, un `&` o un `<`
sacarían una escritura del proyecto o romperían el XML; por eso se validan antes de usarlos y `escribir_proyecto`
además rechaza cualquier destino que no resuelva dentro del proyecto.
"""
from __future__ import annotations

import re

# Nombre del proyecto: artifactId de Maven y nombre de fichero (organización, journey).
NOMBRE_PROYECTO = re.compile(r"[a-z][a-z0-9-]*")
# Grupo Maven: un paquete Java en minúsculas.
GRUPO = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*")
# Versión de un pool: números separados por puntos (1.0, 2.1.3).
VERSION_POOL = re.compile(r"\d+(\.\d+)*")
# Versión de Bonita de la matriz `versiones/` (2026.2).
VERSION_BONITA = re.compile(r"\d{4}\.\d+")
# Nombre de un pool: lo que admite Bonita, sin separadores de ruta ni caracteres de control, ni solo puntos.
_POOL_PROHIBIDO = re.compile(r"[/\\\x00-\x1f\x7f]")
# R-16 (Plan 5): nombres de la organización y de las lanes, tal como los admiten el XML y el journey.
USUARIO = re.compile(r"[A-Za-z0-9._-]+")                 # solicitante.prueba1
ROL = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")              # VPAdministrativo
SEGMENTO_GRUPO = re.compile(r"[A-Za-z0-9_-]+")           # un tramo de /a/b/c
PERFIL_PROHIBIDO = re.compile(r"[/\\`\x00-\x1f\x7f]")   # «Solicitante SyP» vale; barras, backticks y controles no
LANE_PROHIBIDO = re.compile(r"[`|\x00-\x1f\x7f]")         # «Analista / Líder de Proyectos SyP» vale


def nombre_pool_valido(nombre: object) -> bool:
    return (isinstance(nombre, str) and nombre.strip() == nombre and nombre.strip(".") != ""
            and not _POOL_PROHIBIDO.search(nombre))


def es(patron: re.Pattern, valor: object) -> bool:
    return isinstance(valor, str) and patron.fullmatch(valor) is not None


MENSAJE = {
    "nombre": "debe ser un nombre simple en minúsculas: letras, cifras y guiones, empezando por letra "
              "(p. ej. vacaciones)",
    "grupo": "debe ser un paquete Java en minúsculas (p. ej. com.empresa.vacaciones)",
    "version_pool": "la versión del pool debe ser números separados por puntos (p. ej. 1.0)",
    "version_bonita": "la versión de Bonita debe tener la forma AAAA.N (p. ej. 2026.2)",
    "pool": "el nombre del pool no puede tener separadores de ruta (/, \\), caracteres de control ni ser solo "
            "puntos",
}
