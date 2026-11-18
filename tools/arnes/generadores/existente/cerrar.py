"""Cierre de un micro-cambio en modo «proyecto existente» (spec 6.2 y 6.8.1).

Con todos los custodios en verde, `cerrar` archiva la documentación del cambio (`cambios.md` y
`cambios-confirmados.md`) en `docs/07-bonita/historial/<micro_work>/` y convierte el resultado en la nueva línea base:
los ficheros existentes que cambiaron (hash y copia nuevos) y los `.proc`/`.conf` de las versiones superiores que
generó la cirugía. Los procesos nuevos (generados desde la documentación) no entran: siguen siendo generados. Al final
regenera el mapa, cuya huella cambia, y una fase nueva parte sin `cambios.md`."""
from __future__ import annotations

import io
import re
import shutil
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from generadores.existente.confirmar import CAMBIOS, CONFIRMADOS, leer_confirmados
from generadores.existente.leer_xml import leer_existente
from generadores.existente.linea_base import (BONITA, COPIA, LINEA_BASE, _pools, _sha256, escribir_linea_base,
                                              leer_linea_base, modo_existente)
from generadores.existente.mapa import escribir_mapa

HISTORIAL = Path("docs") / "07-bonita" / "historial"
_SEGURO = re.compile(r"[A-Za-z0-9._-]+")


def _verificar(proyecto: Path) -> None:
    """`ValueError` con los hallazgos si `verificar` no sale 0. Diferido: `__main__` importa este módulo."""
    from generadores.__main__ import main
    salida, errores = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(errores):
        codigo = main(["verificar", str(proyecto)])
    if codigo:
        detalle = "\n".join(linea for linea in (salida.getvalue() + errores.getvalue()).splitlines()
                            if "verde" not in linea)
        raise ValueError(f"`verificar` sale {codigo}: no se puede cerrar el micro-cambio hasta que salga 0:\n{detalle}")


def _nueva_linea_base(proyecto: Path, linea_base: dict, confirmados: dict) -> dict:
    """La línea base tras el cambio: los ficheros de la actual con su contenido de hoy, más los `.proc`/`.conf` de las
    versiones superiores confirmadas. `ValueError` si falta un fichero o una versión superior confirmada."""
    ficheros = {}
    for rel in linea_base["ficheros"]:
        if not (proyecto / rel).is_file():
            raise ValueError(f"{rel}: es de la línea base y ya no está en el proyecto")
        ficheros[rel] = _sha256(proyecto / rel)
    pools = {clave: dict(datos) for clave, datos in linea_base["pools"].items()}
    superiores = {f"{clave.rpartition('@')[0]}@{datos['version_resultante']}": clave
                  for clave, datos in confirmados["procesos"].items()
                  if datos["version_resultante"] != clave.rpartition("@")[2]}
    for rel in sorted(p.relative_to(proyecto).as_posix() for p in (proyecto / BONITA / "app" / "diagrams").glob("*.proc")):
        if rel in ficheros:
            continue
        for clave, pool in _pools(proyecto, rel).items():
            if clave in superiores:
                pools[clave] = pool
                superiores.pop(clave)
                ficheros[rel] = _sha256(proyecto / rel)
                if pool["conf"]:
                    ficheros[pool["conf"]] = _sha256(proyecto / pool["conf"])
    if superiores:
        raise ValueError("falta en el proyecto la versión superior de: " + ", ".join(sorted(superiores))
                         + "; corre `tools/arnes.sh generar`")
    # Los pools de los `.proc` que cambiaron conservan su clave; se refrescan por si cambió su conf.
    for clave, pool in list(pools.items()):
        if pool["fichero"] in ficheros:
            pools[clave] = _pools(proyecto, pool["fichero"])[clave]
    return {"version": linea_base["version"], "ficheros": ficheros, "pools": pools}


def cerrar(proyecto: Path, micro_work: str) -> list[Path]:
    """Cierra el micro-cambio `micro_work` y devuelve las rutas escritas (documentación archivada, línea base y mapa).
    `ValueError` sin tocar nada si el nombre no es seguro, si el proyecto no está en modo existente, si `verificar` no
    sale 0, si falta la documentación del cambio o si el historial de ese micro-cambio ya existe."""
    proyecto = Path(proyecto)
    if not _SEGURO.fullmatch(micro_work or "") or micro_work in (".", ".."):
        raise ValueError(f"micro-work «{micro_work}»: usa solo letras, números, `.`, `_` y `-`")
    if not modo_existente(proyecto):
        raise ValueError(f"{proyecto} no está en modo existente; no hay micro-cambio que cerrar")
    linea_base = leer_linea_base(proyecto)
    if linea_base is None:
        raise ValueError(f"falta la línea base ({LINEA_BASE.as_posix()}); adopta el proyecto")
    faltan = [r.as_posix() for r in (CAMBIOS, CONFIRMADOS) if not (proyecto / r).is_file()]
    if faltan:
        raise ValueError("no hay un micro-cambio que cerrar: faltan " + ", ".join(faltan))
    destino = proyecto / HISTORIAL / micro_work
    if destino.exists():
        raise ValueError(f"{(HISTORIAL / micro_work).as_posix()} ya existe; elige otro nombre de micro-work")
    _verificar(proyecto)
    nueva = _nueva_linea_base(proyecto, linea_base, leer_confirmados(proyecto))
    leer_existente(proyecto)  # un XML ilegible falla aquí, antes de escribir nada
    respaldo = Path(tempfile.mkdtemp(prefix="cerrar-"))
    try:
        shutil.copy2(proyecto / LINEA_BASE, respaldo / LINEA_BASE.name)
        shutil.copytree(proyecto / COPIA, respaldo / COPIA.name)
        escrito = [proyecto / LINEA_BASE]
        try:
            escribir_linea_base(proyecto, nueva)
            escrito += escribir_mapa(proyecto)
            destino.mkdir(parents=True)
            archivados = []
            for origen in (CAMBIOS, CONFIRMADOS):
                shutil.move(proyecto / origen, destino / origen.name)
                archivados.append(destino / origen.name)
        except BaseException:
            shutil.rmtree(proyecto / COPIA, ignore_errors=True)
            shutil.copytree(respaldo / COPIA.name, proyecto / COPIA)
            shutil.copy2(respaldo / LINEA_BASE.name, proyecto / LINEA_BASE)
            for origen in (CAMBIOS, CONFIRMADOS):
                if (destino / origen.name).exists():
                    shutil.move(destino / origen.name, proyecto / origen)
            shutil.rmtree(destino, ignore_errors=True)
            raise
    finally:
        shutil.rmtree(respaldo, ignore_errors=True)
    return archivados + escrito
