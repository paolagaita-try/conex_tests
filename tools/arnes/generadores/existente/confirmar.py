"""Confirmación con una persona de los cambios sobre lo existente (spec 6.5) y su registro.

Antes de tocar nada existente, una persona confirma la clasificación de cada cambio, responde si cada proceso tocado
tiene instancias vivas en producción (y qué versión resulta) y acepta el aviso del BDM. Las respuestas solo llegan
por `preguntar`; el CLI usa siempre `preguntar_tty`, que lee de la terminal (`/dev/tty`) y no de la entrada estándar,
de modo que un agente no puede responder. Lo confirmado queda en `cambios-confirmados.md`: una tabla legible y, al
final, un bloque ```json con los datos. La confirmación caduca si cambia `cambios.md` o un elemento confirmado."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable

from generadores.existente.clasificar import clasificar
from generadores.existente.leer_xml import leer_existente
from generadores.existente.linea_base import BONITA, leer_linea_base
from generadores.leer.cambios import leer_cambios
from generadores.md import leer_markdown

CONFIRMADOS = Path("docs/08-construccion/cambios-confirmados.md")
CAMBIOS = Path("docs/07-bonita/cambios.md")
Preguntar = Callable[[str, list[str]], str]

SI, NO = "sí", "no"
CONFIRMO, NO_CONFIRMO = "confirmo", "no confirmo"
ACEPTO, NO_ACEPTO = "acepto", "no acepto"
SUBIR, MISMA = "subir la versión", "modificar la misma versión"
OTRA = "otra"
MENSAJE_SIN_TTY = ("La confirmación la responde una persona: ejecuta `tools/arnes.sh cambios confirmar` en tu "
                   "terminal")
_BLOQUE_JSON = re.compile(r"```json\n(.*?)\n```\s*\Z", re.S)


def siguiente_menor(version: str) -> str:
    """`"3.0"` -> `"3.1"`, `"1.9"` -> `"1.10"`; con un solo tramo, `"2"` -> `"2.1"`."""
    partes = version.split(".")
    if len(partes) == 1:
        return f"{version}.1"
    if not partes[-1].isdigit():
        raise ValueError(f"la versión «{version}» no termina en un número; no se puede subir")
    return ".".join([*partes[:-1], str(int(partes[-1]) + 1)])


def _componentes(version: str) -> tuple[int, ...] | None:
    """`"3.10"` -> `(3, 10)`; None si no es una versión numérica con tramos separados por puntos."""
    partes = version.strip().split(".")
    return tuple(int(p) for p in partes) if all(p.isdigit() for p in partes) else None


def _es_mayor(nueva: str, actual: str) -> bool:
    n, a = _componentes(nueva), _componentes(actual)
    if n is None or a is None:
        return False
    largo = max(len(n), len(a))
    return n + (0,) * (largo - len(n)) > a + (0,) * (largo - len(a))


def _elegir_version(preguntar: Preguntar, pool: str, actual: str) -> str:
    """Ofrece el siguiente menor u «otra» versión (texto libre, numéricamente mayor que la actual)."""
    siguiente = siguiente_menor(actual)
    pregunta = f"¿Qué versión resulta para el proceso {pool}? La actual es {actual}."
    if _elegir(preguntar, pregunta, [siguiente, OTRA]) == siguiente:
        return siguiente
    while True:
        escrita = preguntar(f"Escribe la versión de {pool}; debe ser mayor que {actual} (por ejemplo "
                            f"{siguiente}).", []).strip()
        if _es_mayor(escrita, actual):
            return escrita


def _huella_cambios(proyecto: Path) -> str:
    return hashlib.sha256((proyecto / CAMBIOS).read_bytes()).hexdigest()


def clasificacion(proyecto: Path) -> list[dict]:
    """Lee `cambios.md` y el proyecto y devuelve la clasificación de cada cambio. `ValueError` si no se puede leer."""
    ruta = proyecto / CAMBIOS
    if not ruta.is_file():
        raise ValueError(f"falta {CAMBIOS.as_posix()}")
    cambios, errores = leer_cambios(leer_markdown(ruta.read_text(encoding="utf-8")))
    if errores:
        raise ValueError("cambios.md no es válido:\n" + "\n".join(f"  {e}" for e in errores))
    return clasificar(cambios, leer_existente(proyecto), proyecto)


def _elemento(c: dict) -> str:
    d = c["datos"]
    if c["existente"]:
        return c["existente"]
    return " / ".join(str(v) for v in (c["pool"], *(x for x in d.values() if isinstance(x, (str, int))
                                                    and not isinstance(x, bool))) if v)


def _descripcion(c: dict) -> str:
    sobre = f" en el proceso {c['pool']}" if c["pool"] else ""
    return (f"{c['cambio']} {c['clase']} «{_elemento(c)}»{sobre}"
            + (f" (en el proyecto sería «{c['calculado']}»)" if c["calculado"] != c["cambio"] else ""))


def _pregunta_instancias(pool: str) -> str:
    return f"¿El proceso {pool} tiene instancias vivas en producción?"


def _pregunta_version(pool: str) -> str:
    return (f"El proceso {pool} no tiene instancias vivas. ¿Subes la versión o modificas la misma? Modificar la "
            f"misma versión obliga, al desplegar, a borrar el proceso con todos sus casos (también los terminados), "
            f"y un CI/CD que no reinstala un proceso con la misma versión lo rechaza.")


def _pregunta_bdm(c: dict) -> str:
    return (f"Se modifica el BDM ({_descripcion(c)}). En producción puede haber datos en esa tabla o columna. "
            f"¿Aceptas el aviso?")


def _elegir(preguntar: Preguntar, pregunta: str, opciones: list[str]) -> str:
    respuesta = preguntar(pregunta, opciones)
    if respuesta not in opciones:
        raise ValueError(f"respuesta no válida «{respuesta}»; las opciones eran: {', '.join(opciones)}")
    return respuesta


def _bloqueos(resultado: list[dict]) -> list[str]:
    bloqueos = [f"{c['ubic']}: {c['discrepancia']}" for c in resultado if c["discrepancia"]]
    bloqueos += [f"{c['ubic']}: no soportado: {c['motivo']}" for c in resultado if not c["soportado"]]
    return bloqueos


def confirmar(proyecto: Path, preguntar: Preguntar, quien: str, ahora: str) -> Path:
    """Corre la secuencia de la spec 6.5 y escribe `CONFIRMADOS`. `ValueError` si quedan discrepancias o cambios no
    soportados, si alguna respuesta no es válida o si la persona no confirma."""
    proyecto = Path(proyecto)
    resultado = clasificacion(proyecto)
    bloqueos = _bloqueos(resultado)
    if bloqueos:
        raise ValueError("hay discrepancias o cambios no soportados; corrige cambios.md antes de confirmar:\n"
                         + "\n".join(f"  {b}" for b in bloqueos))
    for i, c in enumerate(resultado, 1):
        pregunta = f"Cambio {i} de {len(resultado)}: {_descripcion(c)}. ¿Confirmas esta clasificación?"
        if _elegir(preguntar, pregunta, [CONFIRMO, NO_CONFIRMO]) != CONFIRMO:
            raise ValueError(f"no se confirmó el cambio {i} ({c['ubic']}); corrige cambios.md y repite")
    procesos: dict[str, dict] = {}
    for pool in dict.fromkeys(c["pool"] for c in resultado if c["clase"] in ("nodo", "contrato")):
        version = pool.rpartition("@")[2]
        if _elegir(preguntar, _pregunta_instancias(pool), [SI, NO]) == SI:
            procesos[pool] = {"instancias_vivas": True,
                              "version_resultante": _elegir_version(preguntar, pool, version)}
            continue
        sube = _elegir(preguntar, _pregunta_version(pool), [SUBIR, MISMA]) == SUBIR
        procesos[pool] = {"instancias_vivas": False,
                          "version_resultante": _elegir_version(preguntar, pool, version) if sube else version}
    for c in resultado:
        if c["clase"] in ("objeto", "atributo") and c["cambio"] == "modifica":
            if _elegir(preguntar, _pregunta_bdm(c), [ACEPTO, NO_ACEPTO]) != ACEPTO:
                raise ValueError(f"no se aceptó el aviso del BDM ({c['ubic']}); no se confirma")
    datos = {"version": 1, "respondido_por": quien, "fecha": ahora, "huella_cambios": _huella_cambios(proyecto),
             "cambios": [{**c, "confirmado": True} for c in resultado], "procesos": procesos}
    ruta = proyecto / CONFIRMADOS
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(_markdown(datos), encoding="utf-8")
    return ruta


def _celda(valor) -> str:
    return "—" if valor in (None, "") else str(valor).replace("|", "\\|").replace("\n", " ")


def _markdown(datos: dict) -> str:
    lineas = ["# Cambios confirmados", "",
              f"Confirmado por **{datos['respondido_por']}** el {datos['fecha']}.", "",
              f"Huella de `cambios.md`: `{datos['huella_cambios']}`. Si `cambios.md` o un elemento confirmado "
              f"cambian, la confirmación caduca y hay que repetirla.", "", "## Cambios", "",
              "| # | Cambio | Clase | Elemento | Proceso | Huella en el proyecto |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(datos["cambios"], 1):
        lineas.append("| " + " | ".join(_celda(x) for x in (i, c["cambio"], c["clase"], _elemento(c), c["pool"],
                                                              c["huella"])) + " |")
    lineas += ["", "## Procesos tocados", ""]
    if datos["procesos"]:
        lineas += ["| Proceso | Instancias vivas | Versión resultante | Qué implica |", "|---|---|---|---|"]
        for pool, p in sorted(datos["procesos"].items()):
            misma = pool.rpartition("@")[2] == p["version_resultante"]
            implica = ("se modifica la misma versión: al desplegar hay que borrar el proceso con todos sus casos"
                       if misma else "versión superior; la anterior queda intacta y sus casos terminan con ella")
            lineas.append("| " + " | ".join(_celda(x) for x in (pool, SI if p["instancias_vivas"] else NO,
                                                                  p["version_resultante"], implica)) + " |")
    else:
        lineas.append("Ningún proceso tocado.")
    lineas += ["", "## Datos", "", "```json", json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True),
               "```", ""]
    return "\n".join(lineas)


def leer_confirmados(proyecto: Path) -> dict | None:
    """Los datos del bloque ```json de `CONFIRMADOS`, o None si no hay confirmación."""
    ruta = Path(proyecto) / CONFIRMADOS
    if not ruta.is_file():
        return None
    m = _BLOQUE_JSON.search(ruta.read_text(encoding="utf-8"))
    if m is None:
        raise ValueError(f"{CONFIRMADOS.as_posix()}: no tiene el bloque ```json con los datos")
    return json.loads(m.group(1))


def _ficheros_del_cambio(c: dict, linea_base: dict) -> list[str]:
    """Los ficheros de la línea base que contienen el elemento de un cambio."""
    if c["clase"] in ("objeto", "atributo"):
        return [f"{BONITA}/bdm/bom.xml"]
    if c["clase"] in ("nodo", "contrato"):
        pool = linea_base["pools"].get(c["pool"])
        return [pool["fichero"]] if pool else []
    return [f for f in linea_base["ficheros"] if f.startswith(f"{BONITA}/app/organizations/")]


def _intacto(proyecto: Path, rel: str, linea_base: dict) -> bool:
    """¿El fichero sigue igual a su hash de la línea base (estado previo a generar)?"""
    ruta = proyecto / rel
    esperado = linea_base["ficheros"].get(rel)
    return (esperado is not None and ruta.is_file()
            and hashlib.sha256(ruta.read_bytes()).hexdigest() == esperado)


def caducada(proyecto: Path) -> list[str]:
    """`[]` si la confirmación sigue vigente; si no, los motivos. Sin confirmación: `["no hay confirmación"]`.
    Un elemento confirmado solo cuenta si el fichero de la línea base que lo contiene sigue igual a su hash."""
    proyecto = Path(proyecto)
    try:
        datos = leer_confirmados(proyecto)
    except (ValueError, OSError) as e:
        return [f"la confirmación no se puede leer: {e}"]
    if datos is None:
        return ["no hay confirmación"]
    if not (proyecto / CAMBIOS).is_file():
        return [f"falta {CAMBIOS.as_posix()}"]
    if _huella_cambios(proyecto) != datos["huella_cambios"]:
        return ["cambios.md cambió después de confirmar"]
    try:
        ahora = clasificacion(proyecto)
    except (ValueError, OSError, KeyError) as e:
        return [f"el proyecto ya no se puede comparar con lo confirmado: {e}"]
    linea_base = leer_linea_base(proyecto)
    motivos = []
    for antes, c in zip(datos["cambios"], ahora):
        # Tras generar, el fichero de la línea base cambia a propósito (y con él la huella): ese elemento ya no
        # cuenta aquí; lo vigila la comprobación de la línea base.
        if linea_base is not None and not all(_intacto(proyecto, rel, linea_base)
                                              for rel in _ficheros_del_cambio(c, linea_base)):
            continue
        if antes["huella"] != c["huella"]:
            motivos.append(f"el elemento «{_elemento(c)}» cambió en el proyecto después de confirmar "
                           f"({c['ubic']})")
    return motivos


def preguntar_tty() -> Preguntar:
    """Un `Preguntar` que habla con la persona por la terminal (`/dev/tty`). `OSError` si no hay terminal."""
    try:
        tty = open("/dev/tty", "r+", encoding="utf-8")
    except OSError as e:
        raise OSError(MENSAJE_SIN_TTY) from e

    def preguntar(pregunta: str, opciones: list[str]) -> str:
        while True:
            print(f"\n{pregunta}", file=tty)
            for i, o in enumerate(opciones, 1):
                print(f"  {i}) {o}", file=tty)
            print("Respuesta (número o texto): ", end="", file=tty, flush=True)
            linea = tty.readline()
            if not linea:
                raise OSError(MENSAJE_SIN_TTY)
            r = linea.strip()
            if r in opciones:
                return r
            if r.isdigit() and 1 <= int(r) <= len(opciones):
                return opciones[int(r) - 1]
            print("Respuesta no válida.", file=tty)

    return preguntar
