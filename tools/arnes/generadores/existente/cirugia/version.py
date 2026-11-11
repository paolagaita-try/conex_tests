"""Versión superior de un proceso: copia del `.proc` con el pool en otra versión y todos los `xmi:id` nuevos.

La versión anterior queda intacta en el proyecto (Bonita deja convivir dos versiones del mismo proceso) y los casos en
curso terminan con ella. La forma de la copia es una decisión sin medir en el Studio `[no verificado]` (spec 6.6).

Orden de uso: la cirugía se aplica primero al texto original y `nueva_version` después sobre su resultado, por eso
funciona con los ids `_h…` que inserta el generador."""
import re

from generadores.existente import xmi
from generadores.xmlutil import Ids

_ID = "[A-Za-z0-9_-]"
# Atributos con los que la notación nombra los extremos de lo que se quita (el punto fijo de abajo).
_EXTREMOS = ("element", "source", "target")


def _referencias(attrs: dict[str, str], nombres: tuple[str, ...]) -> set[str]:
    return {v for n in nombres for v in attrs.get(n, "").split()}


def _hijos_directos(nodos: list[xmi.Nodo], i: int) -> list[int]:
    return [k for k, n in enumerate(nodos) if n.padre == i]


def _subarbol(nodos: list[xmi.Nodo], i: int) -> list[int]:
    n = nodos[i]
    return [k for k, m in enumerate(nodos) if n.inicio <= m.inicio and m.fin <= n.fin]


def _es_pool(n: xmi.Nodo) -> bool:
    return n.attrs.get("xmi:type") == "process:Pool"


def _quitar_otros_pools(texto: str, pool_xmi_id: str) -> str:
    """Quita los demás pools del `MainProcess` y todo lo que solo les pertenece: sus elementos de notación y los
    conectores que los nombran. `ValueError` si algo que se queda aún referencia un id quitado."""
    nodos = xmi.indexar(texto)
    mapa = xmi.por_id(nodos)
    if pool_xmi_id not in mapa or not _es_pool(mapa[pool_xmi_id]):
        raise ValueError(f"El pool {pool_xmi_id} no existe en el .proc")
    principal = mapa[pool_xmi_id].padre
    otros = [k for k in _hijos_directos(nodos, principal)
             if _es_pool(nodos[k]) and nodos[k].attrs.get("xmi:id") != pool_xmi_id]
    if not otros:
        return texto
    quitar = set(otros)
    quitados = {nodos[k].attrs["xmi:id"] for o in otros for k in _subarbol(nodos, o) if "xmi:id" in nodos[k].attrs}
    cambio = True
    while cambio:  # punto fijo: quitar una figura puede dejar huérfano el conector que la une
        cambio = False
        for k, n in enumerate(nodos):
            if k in quitar or any(a in quitar for a in _ascendientes(nodos, k)):
                continue
            if _referencias(n.attrs, _EXTREMOS) & quitados:
                quitar.add(k)
                quitados |= {nodos[j].attrs["xmi:id"] for j in _subarbol(nodos, k) if "xmi:id" in nodos[j].attrs}
                cambio = True
    ediciones = [xmi.quitar(nodos[k], texto) for k in sorted(quitar)
                 if not any(a in quitar for a in _ascendientes(nodos, k))]
    nuevo = xmi.aplicar(texto, ediciones)
    _sin_colgando(nuevo, quitados)
    return nuevo


def _sin_colgando(texto: str, quitados: set[str]) -> None:
    """Comprobación genérica: ningún id quitado puede aparecer en el texto que queda (en cualquier atributo, solo o
    dentro de una lista separada por espacios, ni en cualquier otro texto). `ValueError` nombrando dónde."""
    patron = re.compile(rf"(?<!{_ID})(?:" + "|".join(re.escape(v) for v in sorted(quitados, key=len, reverse=True))
                        + rf")(?!{_ID})")
    for n in xmi.indexar(texto):
        for atributo, valor in n.attrs.items():
            colgando = sorted(set(patron.findall(valor)))
            if colgando:
                raise ValueError(f"«{n.tag}» {n.attrs.get('xmi:id', '')} referencia {colgando} de otro pool en "
                                 f"«{atributo}»; no se puede dejar solo el pool que sube de versión")
    resto = patron.search(texto)
    if resto:
        raise ValueError(f"El id {resto.group(0)} de otro pool sigue en el texto; no se puede dejar solo el pool "
                         "que sube de versión")


def _ascendientes(nodos: list[xmi.Nodo], k: int):
    p = nodos[k].padre
    while p is not None:
        yield p
        p = nodos[p].padre


def _sustituir(texto: str, remapeo: dict[str, str]) -> str:
    """Cambia cada aparición textual de un id viejo (atributos, expresiones, documentación) por el nuevo."""
    if not remapeo:
        return texto
    viejos = sorted(remapeo, key=len, reverse=True)
    patron = re.compile(rf"(?<!{_ID})(?:" + "|".join(re.escape(v) for v in viejos) + rf")(?!{_ID})")
    return patron.sub(lambda m: remapeo[m.group(0)], texto)


def nueva_version(texto_proc: str, pool_xmi_id: str, version: str, semilla: str) -> tuple[str, dict[str, str]]:
    """Copia del `.proc` con el pool y el `MainProcess` en `version` y todos los `xmi:id` reasignados (más las
    referencias que los nombran, en cualquier atributo o texto). Si el `.proc` tiene varios pools, la copia solo
    conserva el que sube de versión. Devuelve el texto nuevo y el remapeo viejo -> nuevo (solo de lo que se conserva).
    Determinista: la misma entrada y semilla dan el mismo resultado."""
    if not version or re.search(r"\s", version):
        raise ValueError(f"La versión «{version}» no puede estar vacía ni tener espacios")
    texto = _quitar_otros_pools(texto_proc, pool_xmi_id)
    nodos = xmi.indexar(texto)
    mapa = xmi.por_id(nodos)
    principal = nodos[mapa[pool_xmi_id].padre]
    ediciones = [xmi.poner_atributo(texto, mapa[pool_xmi_id], "version", version),
                 xmi.poner_atributo(texto, principal, "version", version)]
    texto = xmi.aplicar(texto, ediciones)
    viejos = [n.attrs["xmi:id"] for n in xmi.indexar(texto) if "xmi:id" in n.attrs]
    ocupados = set(viejos) | set(xmi.por_id(xmi.indexar(texto_proc)))
    ids = Ids(semilla)
    remapeo: dict[str, str] = {}
    for v in viejos:
        nuevo = ids.siguiente()
        while nuevo in ocupados:  # p. ej. un id `_h…` que insertó la cirugía con la misma semilla
            nuevo = ids.siguiente()
        remapeo[v] = nuevo
    return _sustituir(texto, remapeo), remapeo


def nombre_fichero(texto_proc: str, version: str) -> str:
    """`<nombre del MainProcess>-<version>.proc`."""
    principal = next((n for n in xmi.indexar(texto_proc) if n.tag.endswith(":MainProcess")), None)
    if principal is None:
        raise ValueError("El .proc no tiene MainProcess")
    return f"{principal.attrs['name']}-{version}.proc"


def copiar_conf(texto_conf: str, remapeo: dict[str, str]) -> str:
    """El `.conf` de la versión nueva: el de la anterior con los ids viejos cambiados por los nuevos. Se guarda como
    `<xmi:id nuevo del pool>.conf`."""
    return _sustituir(texto_conf, remapeo)
