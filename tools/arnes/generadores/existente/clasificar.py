"""Clasificación de los cambios documentados contra el mapa de lo existente.

Compara lo que `cambios.md` dice (agrega, modifica, quita) con lo que el mapa dice que existe, y por cada cambio
calcula la operación real, señala la discrepancia si la hay y marca lo que esta entrega no soporta. Para el proceso,
el BDM y la organización la última palabra la tiene la propia cirugía: se ensaya en memoria y lo que rechazaría queda
«no soportado» con su mensaje, así que nada que una persona confirme falla después al generar. Es lo que luego
confirma una persona; no escribe nada."""
from __future__ import annotations

from pathlib import Path

from generadores.existente.mapa import elemento, huella

HUECOS = "references/huecos-del-arnes.md"
SEMILLA_ENSAYO = "clasificar/ensayo"  # los ids del ensayo se tiran: la semilla no importa

# Operaciones de cirugía de esta entrega (spec 6.7 y 6.11) como pares (cambio, clase). Las condiciones que no caben
# en el par (tipo de tarea, tipos de input, una entrada y una salida) se comprueban en `_soporte`.
SOPORTADAS: frozenset[tuple[str, str]] = frozenset({
    ("agrega", "objeto"), ("agrega", "atributo"), ("modifica", "atributo"),
    ("agrega", "grupo"), ("agrega", "rol"), ("agrega", "usuario"), ("agrega", "membresia"),
    ("agrega", "nodo"), ("modifica", "nodo"), ("quita", "nodo"),
    ("agrega", "contrato"),
})

TIPOS_INPUT_SIMPLES = frozenset({"TEXT", "BOOLEAN", "INTEGER", "DECIMAL", "DATE", "LOCALDATE"})
TIPOS_ATRIBUTO_SIMPLES = frozenset({"STRING", "TEXT", "BOOLEAN", "INTEGER", "LONG", "DOUBLE", "FLOAT", "DATE",
                                    "LOCALDATE", "LOCALDATETIME", "OFFSETDATETIME"})
_HUMANA = {"task", "human", "humana", "humano"}
_SERVICIO = {"servicetask", "service", "servicio"}


def tipo_de_tarea(tipo: str | None) -> str | None:
    """«humana» o «servicio» según el `Tipo Bonita` (con o sin `process:`); None si no es una de las dos."""
    t = (tipo or "").lower().removeprefix("process:")
    return "humana" if t in _HUMANA else "servicio" if t in _SERVICIO else None


def nodo_del_pool(pool: dict, referencia: str | None) -> tuple[str | None, dict | None, bool]:
    """`(clave, nodo, ambiguo)` del nodo de `pool` que `referencia` nombra, por clave o por nombre único."""
    if referencia is None:
        return None, None, False
    if referencia in pool["nodos"]:
        return referencia, pool["nodos"][referencia], False
    coincidencias = [(k, n) for k, n in pool["nodos"].items() if n["nombre"] == referencia]
    if len(coincidencias) == 1:
        return coincidencias[0][0], coincidencias[0][1], False
    return None, None, len(coincidencias) > 1


def _sin_interpretar(pool: dict, nodo: dict) -> bool:
    """True si el lector no interpretó este nodo (su tipo de nodo no lo escribe el generador)."""
    for item in pool["no_interpretados"]:
        tipo, _, resto = item.partition(" en ")
        if tipo == nodo["tipo"] and resto.rsplit(" › ", 1)[-1] == nodo["nombre"]:
            return True
    return False


def _nuevos(cambios: list[dict]) -> set[str]:
    """Identificadores que el propio `cambios.md` agrega (para no tomar por discrepancia lo que se apoya en ellos)."""
    ids: set[str] = set()
    for c in cambios:
        if c["cambio"] != "agrega":
            continue
        d, clase = c["datos"], c["clase"]
        if clase == "objeto":
            ids.add(f"bdm/{d['objeto']}")
        elif clase == "atributo":
            ids.add(f"bdm/{d['objeto']}/{d['atributo']}")
        elif clase == "grupo":
            ids.add(f"org/grupo/{d['ruta']}")
        elif clase == "rol":
            ids.add(f"org/rol/{d['rol']}")
        elif clase == "usuario":
            ids.add(f"org/usuario/{d['usuario']}")
        elif clase == "nodo":
            ids.add(f"proc/{c['pool']}/nodo/{d['nombre']}")
    return ids


class _Contexto:
    def __init__(self, cambios: list[dict], existente: dict):
        self.existente = existente
        self.nuevos = _nuevos(cambios)
        self.nuevos_nodos = [c for c in cambios if c["cambio"] == "agrega" and c["clase"] == "nodo"]

    def hay(self, identificador: str) -> bool:
        return elemento(self.existente, identificador) is not None or identificador in self.nuevos


def _identificador(c: dict) -> str | None:
    """Identificador de lo que el cambio toca (el `Existente` o el que se deduce de sus celdas)."""
    if c["existente"]:
        return c["existente"]
    d, clase = c["datos"], c["clase"]
    if clase == "objeto":
        return f"bdm/{d['objeto']}"
    if clase == "atributo":
        return f"bdm/{d['objeto']}/{d['atributo']}"
    if clase == "grupo":
        return f"org/grupo/{d['ruta']}"
    if clase == "rol":
        return f"org/rol/{d['rol']}"
    if clase in ("usuario", "membresia"):
        return f"org/usuario/{d['usuario']}"
    return None  # nodo y contrato dependen del pool


def _localizar(c: dict, ctx: _Contexto) -> tuple[str | None, dict | None, str | None]:
    """`(identificador, elemento existente o None, discrepancia de forma o None)` de lo que el cambio toca."""
    clase, d = c["clase"], c["datos"]
    if clase in ("nodo", "contrato"):
        pool = ctx.existente["pools"].get(c["pool"])
        if pool is None:
            return None, None, f"el pool «{c['pool']}» no existe en el proyecto"
        if clase == "nodo":
            if c["existente"]:
                return c["existente"], elemento(ctx.existente, c["existente"]), None
            clave, nodo, ambiguo = nodo_del_pool(pool, d["nombre"])
            if ambiguo:
                return None, None, f"hay varias tareas llamadas «{d['nombre']}»; no se puede saber cuál es"
            return (f"proc/{c['pool']}/nodo/{clave}", nodo, None) if nodo else (None, None, None)
        ident = c["existente"] or f"proc/{c['pool']}/contrato/{d['tarea']}/{d['input']}"
        clave, _, _ = nodo_del_pool(pool, d["tarea"])
        if not c["existente"] and clave is not None:
            ident = f"proc/{c['pool']}/contrato/{clave}/{d['input']}"
        return ident, elemento(ctx.existente, ident), None
    if clase == "membresia":
        usuario = elemento(ctx.existente, f"org/usuario/{d['usuario']}")
        if usuario is not None and d["rol"] is not None and [d["rol"], d["grupo"]] in usuario["membresias"]:
            return f"org/usuario/{d['usuario']}", usuario, None
        return f"org/usuario/{d['usuario']}", None, None
    ident = _identificador(c)
    return ident, elemento(ctx.existente, ident), None


def _discrepancia(c: dict, ident: str | None, elem: dict | None, forma: str | None, ctx: _Contexto) -> str | None:
    if forma:
        return forma
    cambio, clase, d = c["cambio"], c["clase"], c["datos"]
    if cambio == "agrega" and elem is not None:
        return f"se agrega algo que ya existe (`{ident}`)"
    if cambio != "agrega" and elem is None:
        return f"se {cambio} algo que no existe en el proyecto (`{ident}`)"
    # Lo que el cambio necesita para poder aplicarse.
    if cambio == "agrega" and clase == "atributo" and not ctx.hay(f"bdm/{d['objeto']}"):
        return f"el objeto «{d['objeto']}» del atributo no existe ni se agrega en este documento"
    if cambio == "agrega" and clase == "membresia":
        for faltante in (f"org/usuario/{d['usuario']}", f"org/rol/{d['rol']}", f"org/grupo/{d['grupo']}"):
            if not ctx.hay(faltante):
                return f"la membresía se apoya en algo que no existe ni se agrega: `{faltante}`"
    pool = ctx.existente["pools"].get(c["pool"]) if c["pool"] else None
    if cambio == "agrega" and clase == "contrato":
        clave, nodo, ambiguo = nodo_del_pool(pool, d["tarea"])
        if ambiguo:
            return f"hay varias tareas llamadas «{d['tarea']}»; use el xmi:id en la columna Tarea"
        if nodo is None and f"proc/{c['pool']}/nodo/{d['tarea']}" not in ctx.nuevos:
            return f"la tarea «{d['tarea']}» del contrato no existe ni se agrega en este documento"
    if cambio == "agrega" and clase == "nodo" and d["transicion"] is not None:
        if transicion_del_pool(pool, d["transicion"], c["pool"]) is None:
            t = d["transicion"]
            return f"la transición «{t['desde']} -> {t['hacia']}» sobre la que se inserta no existe en {c['pool']}"
    if cambio == "modifica" and clase == "atributo":
        if all(d[k] is None or d[k] == elem[k] for k in ("tipo", "obligatorio", "longitud")):
            return f"el atributo ya tiene esos valores (`{ident}`)"
    if cambio == "modifica" and clase == "nodo" and d["nombre"] == elem["nombre"]:
        return f"la tarea ya se llama «{d['nombre']}» (`{ident}`)"
    return None


def transicion_del_pool(pool: dict | None, t: dict, nombre_pool: str) -> str | None:
    """Clave de la transición existente `desde -> hacia` (con claves o nombres de nodo), o None."""
    if pool is None:
        return None
    prefijo = f"proc/{nombre_pool}/transicion/"
    claves = []
    for lado in (t["desde"].removeprefix(prefijo), t["hacia"]):
        clave, _, _ = nodo_del_pool(pool, lado)
        claves.append(clave)
    if None in claves:
        return None
    k = f"{claves[0]}->{claves[1]}"
    return k if k in pool["transiciones"] else None


def _soporte(c: dict, elem: dict | None, ctx: _Contexto) -> str | None:
    """Motivo por el que esta entrega no soporta el cambio, o None si lo soporta."""
    cambio, clase, d = c["cambio"], c["clase"], c["datos"]
    pool = ctx.existente["pools"].get(c["pool"]) if c["pool"] else None
    # Un cambio sobre un elemento no interpretado siempre es «no soportado».
    if pool is not None and elem is not None and clase == "nodo" and _sin_interpretar(pool, elem):
        return f"el nodo es de un tipo que el arnés no interpreta ({elem['tipo']})"
    if cambio == "quita" and clase in ("objeto", "atributo"):
        return "quitar del BDM está desactivado en esta entrega"
    if (cambio, clase) not in SOPORTADAS:
        return f"«{cambio}» sobre {clase} no está entre las operaciones de esta entrega"
    if clase == "atributo":
        if cambio == "agrega" and (d["tipo"] not in TIPOS_ATRIBUTO_SIMPLES or d["multiple"]):
            return f"solo se agregan atributos simples y de un valor; «{d['tipo']}» no lo es"
        if cambio == "modifica" and elem is not None:
            if elem["relacion"] is not None:
                return "el atributo es una relación entre objetos"
            if d["multiple"] is not None and d["multiple"] != elem["multiple"]:
                return "cambiar si el atributo es múltiple no está soportado"
    if clase == "contrato":
        nodo = nodo_del_pool(pool, d["tarea"])[1] if pool else None
        tipo_tarea = tipo_de_tarea(nodo["tipo"]) if nodo else None
        if nodo is None:  # la tarea se agrega en este mismo documento
            tipo_tarea = next((tipo_de_tarea(x["datos"]["tipo"]) for x in ctx.nuevos_nodos
                               if x["pool"] == c["pool"] and x["datos"]["nombre"] == d["tarea"]), None)
        if tipo_tarea != "humana":
            return "los inputs solo se agregan al contrato de una tarea humana"
        if d["tipo"] not in TIPOS_INPUT_SIMPLES or d["multiple"]:
            return f"solo se agregan inputs simples ({', '.join(sorted(TIPOS_INPUT_SIMPLES))}) de un valor"
    if clase == "nodo":
        if cambio == "agrega":
            if tipo_de_tarea(d["tipo"]) is None:
                return f"solo se insertan tareas humanas o de servicio; «{d['tipo']}» no lo es"
            if d["transicion"] is None:
                return "insertar una tarea exige «Sobre la transición»"
        elif elem is not None:
            if tipo_de_tarea(elem["tipo"]) is None:
                return f"solo se renombran o quitan tareas humanas o de servicio; el nodo es {elem['tipo']}"
            if cambio == "modifica":
                if d["tipo"] is not None and tipo_de_tarea(d["tipo"]) != tipo_de_tarea(elem["tipo"]):
                    return "cambiar el tipo de la tarea no está soportado; solo renombrarla"
                if d["lane"] is not None and d["lane"] != elem["lane"]:
                    return "cambiar el lane de la tarea no está soportado; solo renombrarla"
                if d["nombre"] is None:
                    return "de una tarea solo se soporta renombrarla (falta el nombre nuevo)"
            else:  # quita
                clave = c["existente"].rsplit("/nodo/", 1)[-1]
                entradas = sum(1 for t in pool["transiciones"].values() if t["hacia"] == clave)
                salidas = sum(1 for t in pool["transiciones"].values() if t["desde"] == clave)
                if (entradas, salidas) != (1, 1):
                    return (f"solo se quita una tarea con una entrada y una salida; esta tiene {entradas} "
                            f"entrada(s) y {salidas} salida(s)")
    return None


_CLASES_BDM = ("objeto", "atributo")
_CLASES_ORG = ("grupo", "rol", "usuario", "membresia")


def _ensayos(resultado: list[dict], existente: dict, proyecto: Path) -> dict[tuple[str, str | None], tuple]:
    """Los lotes que se ensayan, cada uno con la cirugía que le toca: `(tipo, pool) -> (cambios, ensayo)`, donde
    `ensayo(cambios)` lanza lo que la cirugía lanzaría. Un lote por pool (`.proc`), uno para el BDM y uno para la
    organización, con los cambios que hasta aquí se pueden aplicar."""
    # Diferido: la cirugía importa este módulo.
    from generadores.existente.cirugia.bom import cirugia_bom
    from generadores.existente.cirugia.organizacion import cirugia_organizacion
    from generadores.existente.cirugia.proc import cirugia_proc
    from generadores.existente.linea_base import BONITA

    proyecto = Path(proyecto)
    lotes: dict[tuple[str, str | None], list[dict]] = {}
    for r in resultado:
        if r["discrepancia"] is not None or not r["soportado"]:
            continue
        if r["clase"] in ("nodo", "contrato"):
            lotes.setdefault(("proc", r["pool"]), []).append(r)
        elif r["clase"] in _CLASES_BDM:
            lotes.setdefault(("bdm", None), []).append(r)
        elif r["clase"] in _CLASES_ORG:
            lotes.setdefault(("org", None), []).append(r)
    def no_soportado(mensaje: str):
        def ensayo(_lote):
            raise NotImplementedError(mensaje)
        return ensayo

    ensayos = {}
    for (tipo, clave), lote in lotes.items():
        if tipo == "proc":
            pool = existente["pools"][clave]
            texto = (proyecto / pool["fichero"]).read_bytes().decode("utf-8")
            ensayo = lambda l, t=texto, x=pool["xmi_id"]: cirugia_proc(t, x, l, SEMILLA_ENSAYO)  # noqa: E731
        elif tipo == "bdm":
            bom = proyecto / BONITA / "bdm" / "bom.xml"
            if not bom.is_file():
                ensayo = no_soportado(f"el proyecto no tiene {BONITA}/bdm/bom.xml; crear el BDM no está soportado")
            else:
                texto = bom.read_bytes().decode("utf-8")
                ensayo = lambda l, t=texto, p=existente["bdm"]["paquete"]: cirugia_bom(t, l, p)  # noqa: E731
        else:
            # Como en `generar`: la cirugía de la organización necesita exactamente un fichero.
            rels = sorted((proyecto / BONITA / "app" / "organizations").glob("*.xml"))
            if len(rels) != 1:
                ensayo = no_soportado(f"la organización tiene {len(rels)} ficheros en {BONITA}/app/organizations/; "
                                      "la cirugía necesita exactamente uno")
            else:
                texto = rels[0].read_bytes().decode("utf-8")
                ensayo = lambda l, t=texto: cirugia_organizacion(t, l)  # noqa: E731
        ensayos[(tipo, clave)] = (lote, ensayo)
    return ensayos


def _ensayar(resultado: list[dict], existente: dict, proyecto: Path) -> None:
    """Ensaya en memoria la cirugía con los cambios que hasta aquí se pueden aplicar (la del `.proc` pool a pool, la
    del BDM y la de la organización) y marca «no soportado» cada cambio que la cirugía rechaza, con el mensaje de la
    cirugía como motivo. Tras cada rechazo se ensaya otra vez sin ese cambio, para dar todos los motivos de una vez. Si
    el mensaje no dice qué cambio falla (no empieza por su ubicación), se marcan todos los que quedan de ese lote."""
    for lote, ensayo in _ensayos(resultado, existente, proyecto).values():
        while lote:
            try:
                ensayo(lote)
                break
            except (NotImplementedError, ValueError) as error:
                mensaje = str(error)
                culpables = [r for r in lote if mensaje.startswith(f"{r['ubic']}: ")] or lote
                for r in culpables:
                    motivo = mensaje.removeprefix(f"{r['ubic']}: ")
                    # Lo que la cirugía no implementa es un hueco del arnés; lo demás se corrige en cambios.md.
                    r["soportado"] = False
                    r["motivo"] = f"{motivo}; va a {HUECOS}" if isinstance(error, NotImplementedError) else motivo
                lote = [r for r in lote if all(r is not x for x in culpables)]


def clasificar(cambios: list[dict], existente: dict, proyecto: Path) -> list[dict]:
    """Cada cambio más: `calculado` (agrega si no existe en el mapa; si existe, quita para un `quita` y modifica
    para lo demás), `huella` del elemento existente (o None), `discrepancia` (str | None), `soportado` y `motivo`.
    `existente` es el mapa leído de `proyecto`; de `proyecto` se leen también los `.proc` para ensayar la cirugía."""
    ctx = _Contexto(cambios, existente)
    resultado = []
    for c in cambios:
        ident, elem, forma = _localizar(c, ctx)
        discrepancia = _discrepancia(c, ident, elem, forma, ctx)
        motivo = _soporte(c, elem, ctx)
        calculado = "agrega" if elem is None else "quita" if c["cambio"] == "quita" else "modifica"
        resultado.append({**c, "calculado": calculado, "huella": huella(elem) if elem is not None else None,
                          "discrepancia": discrepancia, "soportado": motivo is None,
                          "motivo": f"{motivo}; va a {HUECOS}" if motivo else None})
    _ensayar(resultado, existente, proyecto)
    return resultado
