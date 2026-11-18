"""Custodio de cambios (modo «proyecto existente», spec 6.8): lo existente cambia exactamente lo confirmado.

- Por bytes: con una confirmación vigente (`cambios-confirmados.md`), regenera en una copia temporal desde la línea base
  y exige que cada fichero de la línea base y cada `.proc`/`.conf` de versión superior sean idénticos a los de la copia;
  sin ella, que cada fichero de la línea base sea idéntico a su original (la copia en `.trycore-bonita-linea-base/`).
- Por elemento: la diferencia entre lo existente según la línea base (`leer_existente` sobre su copia) y según el
  proyecto es exactamente la de los cambios confirmados, ni más ni menos. Un elemento es lo que nombra el mapa: objeto y
  atributo del BDM; grupo, rol, usuario y membresía; nodo, transición e input de contrato de cada pool. Una tarea que
  se inserta, renombra o quita arrastra sus transiciones y su contrato. Con una versión superior, la vieja no cambia y
  la nueva lleva los cambios de su pool.

Fuera del modo existente no hay nada que vigilar (verde).
"""
from __future__ import annotations

import sys
import tempfile
from collections import Counter
from pathlib import Path

from custodios import NoVerificable, ejecutar, regenerar_existente
from generadores.existente.clasificar import nodo_del_pool, transicion_del_pool
from generadores.existente.confirmar import caducada, leer_confirmados
from generadores.existente.leer_xml import leer_existente
from generadores.existente.linea_base import BONITA, COPIA, leer_linea_base, modo_existente, original

BOM = f"{BONITA}/bdm/bom.xml"
CLASES_PROC = ("nodo", "contrato")


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    if not modo_existente(proyecto):
        return []
    linea_base = leer_linea_base(proyecto)
    if linea_base is None:
        raise NoVerificable("falta la línea base (.trycore-bonita-linea-base.json); adopta el proyecto")
    hallazgos = _copia_de_la_linea_base(proyecto, linea_base)
    if hallazgos:
        return hallazgos  # sin un original fiable no hay con qué comparar
    motivos = caducada(proyecto)
    if motivos:
        confirmados = {"cambios": [], "procesos": {}}
        hallazgos += _contra_el_original(proyecto, linea_base, motivos)
    else:
        confirmados = leer_confirmados(proyecto)
        hallazgos += _contra_lo_regenerado(proyecto, linea_base)
    return hallazgos + _diferencia(proyecto, linea_base, confirmados)


# ------------------------------------------------------------------------------------------------ bytes

def _copia_de_la_linea_base(proyecto: Path, linea_base: dict) -> list[str]:
    hallazgos = []
    for rel in sorted(linea_base["ficheros"]):
        try:
            original(proyecto, rel)
        except ValueError as e:
            hallazgos.append(f"{rel}: la copia de la línea base no sirve ({e}); restáurala con git")
    return hallazgos


def _contra_el_original(proyecto: Path, linea_base: dict, motivos: list[str]) -> list[str]:
    hallazgos = []
    por_que = "; ".join(motivos)
    for rel in sorted(linea_base["ficheros"]):
        real = proyecto / rel
        if not real.is_file():
            hallazgos.append(f"{rel}: falta; es un fichero de la línea base")
        elif real.read_bytes() != original(proyecto, rel):
            hallazgos.append(f"{rel}: distinto de la línea base y no hay una confirmación vigente que lo justifique "
                             f"({por_que}); restaura con git o confirma y genera el cambio")
    return hallazgos


def _contra_lo_regenerado(proyecto: Path, linea_base: dict) -> list[str]:
    hallazgos = []
    with tempfile.TemporaryDirectory() as tmp:
        copia, _, cirugia = regenerar_existente(proyecto, Path(tmp))
        for rel in sorted(set(linea_base["ficheros"]) | cirugia):
            real = proyecto / rel
            if not real.is_file():
                hallazgos.append(f"{rel}: falta; lo genera la confirmación vigente (ejecuta generar)" if rel in cirugia
                                 else f"{rel}: falta; es un fichero de la línea base")
            elif real.read_bytes() != (copia / rel).read_bytes():
                hallazgos.append(f"{rel}: distinto de lo que genera la confirmación vigente (edición a mano sobre lo "
                                 "existente, o confirmación sin generar)")
    return hallazgos


# ------------------------------------------------------------------------------------------------ elementos

def _ordinales(etiquetas: list[str]) -> list[str]:
    """Las etiquetas repetidas, con su orden de aparición (`«x» #2`)."""
    total, vistas, out = Counter(etiquetas), Counter(), []
    for e in etiquetas:
        vistas[e] += 1
        out.append(f"{e} #{vistas[e]}" if total[e] > 1 else e)
    return out


def _repetidos(pool: dict) -> set[str]:
    """Nombres de nodo que se repiten en el pool."""
    return {n for n, k in Counter(x["nombre"] for x in pool["nodos"].values()).items() if n and k > 1}


def _normalizar(pool: dict, ambiguos: set[str]) -> tuple[dict, dict[str, str]]:
    """El pool con claves estables y la correspondencia clave del mapa -> clave estable. El mapa nombra un nodo por su
    nombre y, si el nombre se repite (o falta), por su `xmi:id`, que una versión superior renueva y que deja de usar si
    un renombre hace único el nombre. Aquí un nodo se nombra por su nombre salvo que falte o esté en `ambiguos` (los
    repetidos en cualquiera de los dos lados que se comparan): entonces es `<nombre> [<tipo>]`, con su orden si aún se
    repite. Las transiciones se nombran por sus extremos estables y los contratos por su tarea estable."""
    claves = {k: n["nombre"] for k, n in pool["nodos"].items() if n["nombre"] and n["nombre"] not in ambiguos}
    otros = [k for k in pool["nodos"] if k not in claves]
    claves |= dict(zip(otros, _ordinales([f"{pool['nodos'][k]['nombre'] or ''} "
                                          f"[{(pool['nodos'][k]['tipo'] or '').removeprefix('process:')}]"
                                          for k in otros])))
    transiciones = [{"desde": claves.get(t["desde"], t["desde"]), "hacia": claves.get(t["hacia"], t["hacia"]),
                     "condicion": t["condicion"]} for t in pool["transiciones"].values()]
    nombres = _ordinales([f"{t['desde']}->{t['hacia']}" for t in transiciones])
    return ({"nodos": {claves[k]: {x: n[x] for x in ("nombre", "tipo", "lane")} for k, n in pool["nodos"].items()},
             "transiciones": dict(zip(nombres, transiciones)),
             "contratos": {claves.get(t, t): inputs for t, inputs in pool["contratos"].items()}}, claves)


def _elementos(existente: dict, pools: dict[str, str], ambiguos: dict[str, set[str]],
               con_bdm_y_org: bool = True) -> dict[str, dict]:
    """Identificador -> valor de cada elemento, sin `xmi:id`. `pools`: clave del pool en `existente` -> clave con la
    que se nombran sus elementos (la de la línea base, también para su versión superior); `ambiguos`, por esa clave,
    los nombres de nodo que se repiten en alguno de los dos lados."""
    out: dict[str, dict] = {}
    if con_bdm_y_org:
        for objeto, datos in existente["bdm"]["objetos"].items():
            out[f"bdm/{objeto}"] = {"paquete": datos["paquete"]}
            for atributo, a in datos["atributos"].items():
                out[f"bdm/{objeto}/{atributo}"] = a
        org = existente["organizacion"]
        out.update({f"org/grupo/{g}": {} for g in org["grupos"]})
        out.update({f"org/rol/{r}": {} for r in org["roles"]})
        for usuario, membresias in org["usuarios"].items():
            out[f"org/usuario/{usuario}"] = {}
            out.update({f"org/usuario/{usuario}/membresia/{rol} en {grupo}": {} for rol, grupo in membresias})
    for clave, nombre in pools.items():
        pool, _ = _normalizar(existente["pools"][clave], ambiguos[nombre])
        base = f"proc/{nombre}"
        out.update({f"{base}/nodo/{k}": n for k, n in pool["nodos"].items()})
        out.update({f"{base}/transicion/{k}": t for k, t in pool["transiciones"].items()})
        for tarea, inputs in pool["contratos"].items():
            out.update({f"{base}/contrato/{tarea}/{i}": {"tipo": tipo} for i, tipo in inputs.items()})
    return out


class _Esperado:
    """Lo que los cambios confirmados permiten cambiar (`ids`, `prefijos`, y por pool las tareas tocadas y los pares de
    nodos de las transiciones nuevas) y lo que exigen ver en el resultado (`exigidos`)."""

    def __init__(self, base: dict, cambios: list[dict], ambiguos: dict[str, set[str]]):
        self.ids: set[str] = set()
        self.prefijos: set[str] = set()
        self.tareas: dict[str, set[str]] = {}
        self.pares: dict[str, set[tuple[str, str]]] = {}
        self.exigidos: list[tuple[str, str, dict]] = []  # (identificador, agrega|quita|modifica|nombre, cambio)
        self.base = base
        self.claves = {clave: _normalizar(base["pools"][clave], a)[1] for clave, a in ambiguos.items()}
        self.renombres = {(c["pool"], self._clave(c["pool"], c["existente"].rsplit("/nodo/", 1)[-1])):
                          c["datos"]["nombre"] for c in cambios if c["clase"] == "nodo" and c["calculado"] == "modifica"}
        for c in cambios:
            getattr(self, f"_{c['clase']}")(c)

    def _clave(self, pool: str, clave: str | None) -> str | None:
        """La clave estable de un nodo de la línea base (la del mapa, si no es suya)."""
        return self.claves[pool].get(clave, clave)

    def _exigir(self, ident: str, como: str, c: dict) -> None:
        self.ids.add(ident)
        self.exigidos.append((ident, como, c))

    def _objeto(self, c: dict) -> None:
        self._exigir(f"bdm/{c['datos']['objeto']}", c["calculado"], c)

    def _atributo(self, c: dict) -> None:
        self._exigir(f"bdm/{c['datos']['objeto']}/{c['datos']['atributo']}", c["calculado"], c)

    def _grupo(self, c: dict) -> None:
        self._exigir(f"org/grupo/{c['datos']['ruta'].strip('/')}", c["calculado"], c)

    def _rol(self, c: dict) -> None:
        self._exigir(f"org/rol/{c['datos']['rol']}", c["calculado"], c)

    def _usuario(self, c: dict) -> None:
        ident = f"org/usuario/{c['datos']['usuario']}"
        self._exigir(ident, c["calculado"], c)
        self.prefijos.add(f"{ident}/membresia/")  # la membresía que trae su Detalle

    def _membresia(self, c: dict) -> None:
        d = c["datos"]
        self._exigir(f"org/usuario/{d['usuario']}/membresia/{d['rol']} en {d['grupo'].strip('/')}", c["calculado"], c)

    def _nodo(self, c: dict) -> None:
        pool, d, op = c["pool"], c["datos"], c["calculado"]
        transiciones = self.base["pools"][pool]["transiciones"]
        tareas = self.tareas.setdefault(pool, set())
        pares = self.pares.setdefault(pool, set())
        if op == "agrega":
            tareas.add(d["nombre"])
            self._exigir(f"proc/{pool}/nodo/{d['nombre']}", "agrega", c)
            partida = transicion_del_pool(self.base["pools"][pool], d["transicion"], pool)
            if partida is not None:
                t = transiciones[partida]
                pares.add((self._clave(pool, t["desde"]), self._clave(pool, t["hacia"])))
            return
        clave = c["existente"].rsplit("/nodo/", 1)[-1]
        tareas.add(self._clave(pool, clave))
        if op == "modifica":
            tareas.add(d["nombre"])
            self.ids.add(f"proc/{pool}/nodo/{self._clave(pool, clave)}")
            self._exigir(f"proc/{pool}/nodo/{d['nombre']}", "nombre", c)
            return
        self._exigir(f"proc/{pool}/nodo/{self._clave(pool, clave)}", "quita", c)
        pares.update((self._clave(pool, a["desde"]), self._clave(pool, b["hacia"]))
                     for a in transiciones.values() if a["hacia"] == clave
                     for b in transiciones.values() if b["desde"] == clave)

    def _contrato(self, c: dict) -> None:
        pool, d = c["pool"], c["datos"]
        clave = self._clave(pool, nodo_del_pool(self.base["pools"][pool], d["tarea"])[0]) or d["tarea"]
        tarea = self.renombres.get((pool, clave), clave)
        self._exigir(f"proc/{pool}/contrato/{tarea}/{d['input']}", c["calculado"], c)

    def permite(self, ident: str, antes: dict | None, despues: dict | None) -> bool:
        if ident in self.ids or any(ident.startswith(p) for p in self.prefijos):
            return True
        if not ident.startswith("proc/"):
            return False
        pool, _, resto = ident.removeprefix("proc/").partition("/")
        clase, _, clave = resto.partition("/")
        tareas = self.tareas.get(pool, set())
        if clase == "contrato":
            return clave.partition("/")[0] in tareas
        if clase == "transicion":
            extremos = [(v["desde"], v["hacia"]) for v in (antes, despues) if v is not None]
            return any(a in tareas or b in tareas or (a, b) in self.pares.get(pool, set()) for a, b in extremos)
        return False


def _diferencias(antes: dict[str, dict], despues: dict[str, dict], esperado: _Esperado, fichero) -> list[str]:
    hallazgos = []
    for ident in sorted(antes.keys() | despues.keys()):
        a, d = antes.get(ident), despues.get(ident)
        if a == d or esperado.permite(ident, a, d):
            continue
        que = "se agregó" if a is None else "se quitó" if d is None else "se modificó"
        hallazgos.append(f"{fichero(ident)} › {ident}: {que} y no está en los cambios confirmados")
    for ident, como, c in esperado.exigidos:
        a, d = antes.get(ident), despues.get(ident)
        aplicado = {"agrega": d is not None, "quita": d is None, "nombre": d is not None,
                    "modifica": d is not None and d != a and _con_los_valores(c, d)}[como]
        if not aplicado:
            hallazgos.append(f"{fichero(ident)} › {ident}: el cambio confirmado ({c['ubic']}: {c['calculado']} "
                             f"{c['clase']}) no está aplicado")
    return hallazgos


def _con_los_valores(c: dict, valor: dict) -> bool:
    """¿El atributo modificado tiene los valores que pide el cambio (los que documenta)?"""
    if c["clase"] != "atributo":
        return True
    d = c["datos"]
    return ((d["tipo"] is None or (valor["tipo"] or "").upper() == d["tipo"].upper())
            and all(d[k] is None or valor[k] == d[k] for k in ("obligatorio", "longitud")))


def _diferencia(proyecto: Path, linea_base: dict, confirmados: dict) -> list[str]:
    """La diferencia por elemento entre la línea base y el proyecto es exactamente la de `confirmados`."""
    base = leer_existente(proyecto / COPIA)
    try:
        resultado = leer_existente(proyecto)
    except ValueError as e:  # una edición a mano que rompe el XML: el fichero ya sale distinto por bytes
        return [f"no se puede leer lo existente del proyecto: {e}"]
    organizacion = next((f for f in sorted(linea_base["ficheros"]) if f.startswith(f"{BONITA}/app/organizations/")),
                        f"{BONITA}/app/organizations")
    hallazgos = []
    destino: dict[str, str] = {}  # pool de la línea base -> el del resultado que lleva sus cambios
    anteriores = []  # pools que quedan en su versión porque los cambios van a una superior: no cambian
    for clave in base["pools"]:
        version = (confirmados["procesos"].get(clave) or {}).get("version_resultante")
        nuevo = f"{clave.rpartition('@')[0]}@{version}" if version else clave
        for k in dict.fromkeys((nuevo, clave)):
            if k not in resultado["pools"]:
                hallazgos.append(f"{base['pools'][clave]['fichero']} › proc/{k}: el pool no está en el proyecto")
            elif k == nuevo:
                destino[clave] = k
            else:
                anteriores.append(k)

    def fichero(ident: str) -> str:
        if ident.startswith("bdm/"):
            return BOM
        if ident.startswith("org/"):
            return organizacion
        return resultado["pools"][destino[ident.removeprefix("proc/").partition("/")[0]]]["fichero"]

    cambios = [c for c in confirmados["cambios"] if c["clase"] not in CLASES_PROC or c["pool"] in destino]
    ambiguos = {c: _repetidos(base["pools"][c]) | _repetidos(resultado["pools"][k]) for c, k in destino.items()}
    hallazgos += _diferencias(_elementos(base, {c: c for c in destino}, ambiguos),
                              _elementos(resultado, {k: c for c, k in destino.items()}, ambiguos),
                              _Esperado(base, cambios, ambiguos), fichero)
    for k in anteriores:
        ambiguos = {k: _repetidos(base["pools"][k]) | _repetidos(resultado["pools"][k])}
        hallazgos += _diferencias(_elementos(base, {k: k}, ambiguos, False),
                                  _elementos(resultado, {k: k}, ambiguos, False),
                                  _Esperado(base, [], {}), lambda _ident, k=k: resultado["pools"][k]["fichero"])
    return hallazgos


def main() -> int:
    return ejecutar("check_cambios", comprobar)


if __name__ == "__main__":
    sys.exit(main())
