"""Custodios: comprobaciones que mantienen honesto un proyecto Bonita generado.

Cada módulo expone `comprobar(proyecto) -> list[str]` (vacía = verde) y `main()`. Se ejecutan con
`python3 -m custodios.<nombre> <proyecto>` o todos juntos con `python3 -m generadores verificar <proyecto>`.

Códigos de salida: 0 verde; 1 hallazgos (lo versionado no cuadra con la documentación, o la documentación tiene
errores); 2 «no se puede verificar»: falta un documento que el custodio necesita (p. ej. un proyecto recién creado
con `nuevo`, sin `docs/`), o el generador o un lector fallan con esta documentación. En ese caso `comprobar` lanza
`NoVerificable` (o la excepción del lector). Excepción: un proyecto sin documentación de Bonita (recién creado,
unidad 0) sale 0: no hay nada que verificar (ver `sin_documentacion_bonita`) y no devuelve hallazgos: un custodio que no pudo mirar no está en verde.
Los hallazgos van por stdout; el «no se puede verificar», por stderr.

En modo «proyecto existente» (spec 6.8), solo `docs/07-bonita/bpmn.md` (procesos nuevos) es documentación que
contrastar con los artefactos (`docs_de_procesos_nuevos`); lo existente lo vigila `check_cambios` contra la línea base.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Callable

from generadores.existente.linea_base import BONITA, leer_linea_base, modo_existente, original
from generadores.md import Documento, leer_markdown


class NoVerificable(Exception):
    """El custodio no puede comprobar el proyecto (falta un documento, el generador falla): código 2."""


# Lo que impide comprobar (además de NoVerificable): un lector o el generador que fallan con la documentación.
NO_VERIFICABLE = (NoVerificable, ValueError, NotImplementedError, KeyError, OSError)


def sin_documentacion_bonita(proyecto: Path) -> bool:
    """Un proyecto de unidad 0 recién creado con `nuevo`: `docs/07-bonita/` no existe o no tiene ningún fichero
    (se ignoran los ocultos, como `.gitkeep`). No hay documentación de negocio que contrastar, así que los
    custodios que la comparan no tienen nada que verificar (verde) y `check_generados` vigila solo `hola`. En cuanto
    hay un solo fichero ahí, el proyecto «tiene documentación» y lo que falte sigue siendo `NoVerificable`."""
    carpeta = Path(proyecto) / "docs" / "07-bonita"
    return not carpeta.is_dir() or not any(f.is_file() and not f.name.startswith(".") for f in carpeta.rglob("*"))


def docs_de_procesos_nuevos(proyecto: Path) -> bool:
    """¿Hay documentación de negocio que contrastar con los artefactos? En modo existente, solo si hay procesos nuevos
    documentados (`docs/07-bonita/bpmn.md`): el mapa (`existente/`), `cambios.md`, el `handoff.md` del modo existente
    e `historial/` describen lo existente y sus cambios, no procesos nuevos. Fuera del modo existente, como siempre:
    en cuanto hay documentación de Bonita (ver `sin_documentacion_bonita`)."""
    if modo_existente(proyecto):
        return (Path(proyecto) / "docs" / "07-bonita" / "bpmn.md").is_file()
    return not sin_documentacion_bonita(proyecto)


def pools_existentes(proyecto: Path) -> set[str]:
    """Nombres de los pools de la línea base en modo existente (vacío fuera de él). Sus `.proc`, en cualquier versión
    (también la superior que crea la cirugía), son de lo existente: no se contrastan con `bpmn.md`."""
    datos = leer_linea_base(proyecto) if modo_existente(proyecto) else None
    return {clave.rpartition("@")[0] for clave in datos["pools"]} if datos else set()


def ruta_doc(proyecto: Path, rel: str) -> Path:
    """`proyecto/docs/<rel>`; NoVerificable si no existe."""
    ruta = Path(proyecto) / "docs" / rel
    if not ruta.is_file():
        raise NoVerificable(f"falta docs/{rel}")
    return ruta


def leer_doc(proyecto: Path, rel: str) -> Documento:
    return leer_markdown(ruta_doc(proyecto, rel).read_text(encoding="utf-8"))


def mensaje(e: BaseException) -> str:
    return e.args[0] if isinstance(e, KeyError) and e.args else str(e)


def ejecutar(nombre: str, comprobar: Callable[[Path], list[str]], argv: list[str] | None = None) -> int:
    """Corre un custodio sobre el proyecto de `argv[0]`, imprime los hallazgos y devuelve 0, 1 o 2."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(f"uso: python3 -m custodios.{nombre} <proyecto>", file=sys.stderr)
        return 2
    try:
        hallazgos = comprobar(Path(argv[0]))
    except NO_VERIFICABLE as e:
        print(f"[{nombre}] no se puede verificar: {mensaje(e)}", file=sys.stderr)
        return 2
    for h in hallazgos:
        print(f"[{nombre}] {h}")
    if not hallazgos:
        print(f"[{nombre}] verde")
    return 1 if hallazgos else 0


# Lo que no se copia al regenerar en una copia temporal.
IGNORAR = shutil.ignore_patterns(".git", "target", "node_modules", "runtime", "__pycache__")
# Carpetas de los `.proc` y `.conf`: los de la línea base, los de versión superior y los de los procesos nuevos.
PROCESOS = ((f"{BONITA}/app/diagrams", "*.proc"), (f"{BONITA}/app/process_configurations", "*.conf"))


def regenerar_existente(proyecto: Path, tmp: Path) -> tuple[Path, list[Path], set[str]]:
    """Genera en modo existente en una copia de `proyecto` dentro de `tmp` (el real no se toca) y devuelve
    `(copia, rutas escritas en la copia, rutas relativas de la cirugía)`; la cirugía son los ficheros de la línea base
    que cambia y los `.proc`/`.conf` de versión superior que crea. La copia parte de la línea base: sus ficheros
    vuelven a su original y se quitan los demás `.proc`/`.conf` (versiones superiores y procesos nuevos ya generados,
    que la generación vuelve a escribir), así que el resultado no depende de lo editado a mano en el proyecto.
    `NoVerificable` si no se puede generar (sin confirmación vigente mientras hay un `cambios.md` en curso,
    documentación o copia de la línea base que fallan). Con la fase cerrada (`fase_cerrada`) solo se regeneran los
    procesos nuevos, sin exigir handoff sobre el mapa actual ni confirmación."""
    proyecto = Path(proyecto)
    copia = Path(tmp) / (proyecto.resolve().name or "proyecto")
    shutil.copytree(proyecto, copia, ignore=IGNORAR)
    try:
        ficheros = leer_linea_base(copia)["ficheros"]
        for rel in ficheros:
            (copia / rel).parent.mkdir(parents=True, exist_ok=True)
            (copia / rel).write_bytes(original(copia, rel))
        for carpeta, patron in PROCESOS:
            for f in sorted((copia / carpeta).glob(patron)):
                if f.relative_to(copia).as_posix() not in ficheros:
                    f.unlink()
        from generadores.existente.generar import generar_existente  # diferido: importa el generador entero
        escritos = generar_existente(copia)
    except NO_VERIFICABLE as e:
        raise NoVerificable(f"no se puede regenerar en modo existente: {mensaje(e)}") from e
    generados = copia / "build" / "generados.json"
    nuevos = set(json.loads(generados.read_text(encoding="utf-8"))["generados"]) if generados.is_file() else set()
    cirugia = set()
    for ruta in escritos:
        rel = ruta.relative_to(copia).as_posix()
        de_procesos = any(ruta.parent == copia / carpeta and ruta.match(patron) for carpeta, patron in PROCESOS)
        if rel in ficheros or (de_procesos and rel not in nuevos):
            cirugia.add(rel)
    return copia, escritos, cirugia
