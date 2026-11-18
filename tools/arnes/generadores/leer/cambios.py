"""Lector de `docs/07-bonita/cambios.md`: lo que se agrega, modifica o quita sobre un proyecto Bonita existente.

`cambios.md` es el contrato con el arnés de documentación. Este lector solo comprueba la forma y la coherencia interna
de cada fila (`modifica` y `quita` exigen `Existente`; `agrega` no lo lleva); que lo existente exista de verdad lo
decide la clasificación, no el lector.

Secciones (todas opcionales, pero debe haber al menos una):

- `## Objetos de negocio`: `Cambio | Existente | Objeto | Atributo | Tipo | Obligatorio | Múltiple | Longitud`. Una fila
  sin `Atributo` es el objeto; con `Atributo`, es un atributo de ese objeto (nuevo o existente).
- `## Organización`: `Cambio | Existente | Tipo | Nombre | Detalle`, con `Tipo` en grupo, rol, usuario o membresía
  (`Detalle` de una membresía: `rol / grupo`).
- `## Proceso `<Pool>` <versión>` con `### Nodos` (`Cambio | Existente | Nombre | Tipo Bonita | Lane | Sobre la
  transición`, esta última «desde -> hacia», con o sin backticks en cada extremo) y `### Contratos` (`Cambio |
  Existente | Tarea | Input | Tipo | Múltiple | Obligatorio`).

Cada cambio: `{"cambio", "existente", "clase", "pool", "datos", "ubic"}`.
"""
from __future__ import annotations

import re

from generadores.leer import columna, donde, filas, si_no, tabla, vacio
from generadores.leer.organizacion import ruta_grupo
from generadores.md import Documento, Seccion, codigo

FC = "cambios.md"
CAMBIOS = ("agrega", "modifica", "quita")
_TIPOS_ORG = {"grupo": "grupo", "rol": "rol", "usuario": "usuario", "membresía": "membresia", "membresia": "membresia"}
_SECCION_PROCESO = re.compile(r"^Proceso\s+`([^`]+)`\s+(\S+)$")
_TRANSICION = re.compile(r"^(.+?)\s*->\s*(.+)$")
_MEMBRESIA = re.compile(r"^(.+?)\s*/\s*(.+)$")


def _texto(fila: dict, prefijo: str) -> str | None:
    """Valor de la columna sin backticks; None si está vacía."""
    v = columna(fila, prefijo)
    return None if vacio(v) else codigo(v).strip()


def _booleano(fila: dict, prefijo: str, ubic: str, errores: list[str]) -> bool | None:
    v = _texto(fila, prefijo)
    return None if v is None else si_no(v, f"{ubic} › {prefijo}", errores)


def _comun(fila: dict, ubic: str, errores: list[str]) -> tuple[str, str | None] | None:
    """`(cambio, existente)` de la fila, o None (con error) si la combinación es incoherente."""
    cambio = (_texto(fila, "Cambio") or "").lower()
    existente = _texto(fila, "Existente")
    if getattr(fila, "sobrantes", None):
        errores.append(f"{ubic}: la fila tiene más celdas que columnas (¿un «|» sin escapar dentro de una celda?)")
        return None
    if cambio not in CAMBIOS:
        errores.append(f"{ubic}: Cambio «{cambio or '—'}» debe ser «agrega», «modifica» o «quita»")
        return None
    if cambio == "agrega" and existente is not None:
        errores.append(f"{ubic}: «agrega» no lleva Existente (es nuevo); se encontró «{existente}»")
        return None
    if cambio != "agrega" and existente is None:
        errores.append(f"{ubic}: «{cambio}» exige el identificador de lo existente en la columna Existente")
        return None
    return cambio, existente


def _forma(existente: str | None, patron: str, ubic: str, errores: list[str]) -> bool:
    if existente is not None and not re.fullmatch(patron, existente):
        errores.append(f"{ubic}: Existente «{existente}» no tiene la forma de identificador esperada "
                       f"(«{patron}»)")
        return False
    return True


def _objetos(sec: Seccion, errores: list[str], out: list[dict]) -> None:
    cols = ("Cambio", "Existente", "Objeto", "Atributo", "Tipo", "Obligatorio", "Múltiple", "Longitud")
    u0 = donde(FC, sec.titulo)
    t = tabla(sec, "Cambio", cols, u0, errores)
    for n, f in enumerate(t or [], 1):
        if vacio(f["Cambio"]):
            continue
        ubic = donde(u0, f"fila {n}")
        c = _comun(f, ubic, errores)
        objeto = _texto(f, "Objeto")
        if c is None:
            continue
        if objeto is None:
            errores.append(f"{ubic}: falta el Objeto")
            continue
        cambio, existente = c
        atributo = _texto(f, "Atributo")
        if atributo is None:
            if not _forma(existente, r"bdm/[^/]+", ubic, errores):
                continue
            if existente is not None and existente != f"bdm/{objeto}":
                errores.append(f"{ubic}: Existente «{existente}» no corresponde al objeto «{objeto}»")
                continue
            out.append({"cambio": cambio, "existente": existente, "clase": "objeto", "pool": None,
                        "datos": {"objeto": objeto}, "ubic": ubic})
            continue
        if not _forma(existente, r"bdm/[^/]+/[^/]+", ubic, errores):
            continue
        if existente is not None and existente != f"bdm/{objeto}/{atributo}":
            errores.append(f"{ubic}: Existente «{existente}» no corresponde al atributo «{objeto}.{atributo}»")
            continue
        longitud = _texto(f, "Longitud")
        if longitud is not None and not longitud.isdigit():
            errores.append(f"{ubic}: Longitud «{longitud}» debe ser un entero")
            continue
        n_err = len(errores)
        datos = {"objeto": objeto, "atributo": atributo, "tipo": _texto(f, "Tipo"),
                 "obligatorio": _booleano(f, "Obligatorio", ubic, errores),
                 "multiple": _booleano(f, "Múltiple", ubic, errores),
                 "longitud": int(longitud) if longitud is not None else None}
        if cambio == "agrega" and datos["tipo"] is None:
            errores.append(f"{ubic}: un atributo nuevo necesita Tipo")
        if len(errores) == n_err:
            out.append({"cambio": cambio, "existente": existente, "clase": "atributo", "pool": None,
                        "datos": datos, "ubic": ubic})


def _organizacion(sec: Seccion, errores: list[str], out: list[dict]) -> None:
    cols = ("Cambio", "Existente", "Tipo", "Nombre", "Detalle")
    u0 = donde(FC, sec.titulo)
    t = tabla(sec, "Cambio", cols, u0, errores)
    for n, f in enumerate(t or [], 1):
        if vacio(f["Cambio"]):
            continue
        ubic = donde(u0, f"fila {n}")
        c = _comun(f, ubic, errores)
        if c is None:
            continue
        cambio, existente = c
        tipo_txt = (_texto(f, "Tipo") or "").lower()
        clase = _TIPOS_ORG.get(tipo_txt)
        if clase is None:
            errores.append(f"{ubic}: Tipo «{tipo_txt or '—'}» debe ser grupo, rol, usuario o membresía")
            continue
        nombre = _texto(f, "Nombre")
        detalle = None if vacio(columna(f, "Detalle")) else columna(f, "Detalle").strip()
        if nombre is None:
            errores.append(f"{ubic}: falta el Nombre")
            continue
        datos: dict
        if clase == "grupo":
            ruta = ruta_grupo(nombre)
            datos = {"ruta": ruta}
            patron, esperado = r"org/grupo/.+", f"org/grupo/{ruta}"
        elif clase == "rol":
            datos = {"rol": nombre}
            patron, esperado = r"org/rol/.+", f"org/rol/{nombre}"
        elif clase == "usuario":
            datos = {"usuario": nombre, "detalle": detalle}
            patron, esperado = r"org/usuario/.+", f"org/usuario/{nombre}"
        else:
            m = _MEMBRESIA.match(detalle or "")
            if m is None and cambio != "quita":
                errores.append(f"{ubic}: el Detalle de una membresía debe ser «rol / grupo»")
                continue
            datos = {"usuario": nombre, "rol": m.group(1).strip("` ") if m else None,
                     "grupo": ruta_grupo(m.group(2)) if m else None}
            patron, esperado = r"org/usuario/.+", f"org/usuario/{nombre}"
        if not _forma(existente, patron, ubic, errores):
            continue
        if existente is not None and existente != esperado:
            errores.append(f"{ubic}: Existente «{existente}» no corresponde a «{nombre}» (se esperaba «{esperado}»)")
            continue
        out.append({"cambio": cambio, "existente": existente, "clase": clase, "pool": None,
                    "datos": datos, "ubic": ubic})


def _id_pool(existente: str | None, pool: str, tramo: str, ubic: str, errores: list[str]) -> bool:
    if existente is None:
        return True
    if not re.fullmatch(rf"proc/{re.escape(pool)}/{tramo}/.+", existente):
        errores.append(f"{ubic}: Existente «{existente}» debe ser «proc/{pool}/{tramo}/…» (el pool de la sección)")
        return False
    return True


def _nodos(sec: Seccion, base: str, pool: str, errores: list[str], out: list[dict]) -> None:
    cols = ("Cambio", "Existente", "Nombre", "Tipo Bonita", "Lane", "Sobre la transición")
    u0 = donde(FC, base, sec.titulo)
    t = tabla(sec, "Cambio", cols, u0, errores)
    for n, f in enumerate(t or [], 1):
        if vacio(f["Cambio"]):
            continue
        ubic = donde(u0, f"fila {n}")
        c = _comun(f, ubic, errores)
        if c is None:
            continue
        cambio, existente = c
        if not _id_pool(existente, pool, "nodo", ubic, errores):
            continue
        nombre, tipo = _texto(f, "Nombre"), _texto(f, "Tipo Bonita")
        sobre = _texto(f, "Sobre la transición")
        if cambio != "quita" and nombre is None:
            errores.append(f"{ubic}: falta el Nombre del nodo")
            continue
        if cambio == "agrega" and tipo is None:
            errores.append(f"{ubic}: un nodo nuevo necesita Tipo Bonita")
            continue
        transicion = None
        if sobre is not None:
            m = _TRANSICION.match(sobre)
            if cambio != "agrega" or m is None:
                errores.append(f"{ubic}: «Sobre la transición» solo aplica a «agrega» y debe ser «desde -> hacia»")
                continue
            # Cada extremo puede ir entre backticks (la plantilla escribe «`desde` -> `hacia`»).
            transicion = {"desde": m.group(1).strip("` "), "hacia": m.group(2).strip("` ")}
        out.append({"cambio": cambio, "existente": existente, "clase": "nodo", "pool": pool,
                    "datos": {"nombre": nombre, "tipo": tipo, "lane": _texto(f, "Lane"), "transicion": transicion},
                    "ubic": ubic})


def _contratos(sec: Seccion, base: str, pool: str, errores: list[str], out: list[dict]) -> None:
    cols = ("Cambio", "Existente", "Tarea", "Input", "Tipo", "Múltiple", "Obligatorio")
    u0 = donde(FC, base, sec.titulo)
    t = tabla(sec, "Cambio", cols, u0, errores)
    for n, f in enumerate(t or [], 1):
        if vacio(f["Cambio"]):
            continue
        ubic = donde(u0, f"fila {n}")
        c = _comun(f, ubic, errores)
        if c is None:
            continue
        cambio, existente = c
        if not _id_pool(existente, pool, "contrato", ubic, errores):
            continue
        tarea, input_ = _texto(f, "Tarea"), _texto(f, "Input")
        if tarea is None or input_ is None:
            errores.append(f"{ubic}: faltan la Tarea o el Input")
            continue
        if existente is not None and not existente.endswith(f"/contrato/{tarea}/{input_}"):
            errores.append(f"{ubic}: Existente «{existente}» no corresponde a «{tarea}» / «{input_}»")
            continue
        n_err = len(errores)
        datos = {"tarea": tarea, "input": input_, "tipo": _texto(f, "Tipo"),
                 "multiple": _booleano(f, "Múltiple", ubic, errores),
                 "obligatorio": _booleano(f, "Obligatorio", ubic, errores)}
        if cambio == "agrega" and datos["tipo"] is None:
            errores.append(f"{ubic}: un input nuevo necesita Tipo")
        if len(errores) == n_err:
            out.append({"cambio": cambio, "existente": existente, "clase": "contrato", "pool": pool,
                        "datos": datos, "ubic": ubic})


def leer_cambios(doc: Documento) -> tuple[list[dict], list[str]]:
    errores: list[str] = []
    out: list[dict] = []
    encontradas = 0
    for sec in doc.raiz._recorrer():
        titulo = sec.titulo.replace("`", "")
        if titulo.startswith("Objetos de negocio"):
            encontradas += 1
            _objetos(sec, errores, out)
        elif titulo.startswith("Organización"):
            encontradas += 1
            _organizacion(sec, errores, out)
        elif titulo.startswith("Proceso "):
            encontradas += 1
            m = _SECCION_PROCESO.match(sec.titulo.strip())
            if m is None:
                errores.append(f"{donde(FC, sec.titulo)}: el título debe ser «Proceso `<Pool>` <versión>»")
                continue
            pool = f"{m.group(1).strip()}@{m.group(2)}"
            for h in sec.hijas:
                ht = h.titulo.replace("`", "")
                if ht.startswith("Nodos"):
                    _nodos(h, sec.titulo, pool, errores, out)
                elif ht.startswith("Contratos"):
                    _contratos(h, sec.titulo, pool, errores, out)
                else:
                    errores.append(f"{donde(FC, sec.titulo, h.titulo)}: subsección desconocida; use «Nodos» o "
                                   f"«Contratos»")
    if not encontradas:
        errores.append(f"{FC}: no tiene ninguna sección de cambios (Objetos de negocio, Organización o "
                       f"Proceso `<Pool>` <versión>)")
    return out, errores
