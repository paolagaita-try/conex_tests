"""Mapa de solo lectura de un proyecto existente: `docs/07-bonita/existente/*.md`.

Cada elemento del BDM, la organización y los pools tiene un identificador estable (`bdm/<Objeto>`,
`proc/<Pool>@<v>/nodo/<nombre>`…) que la documentación de cambios, la clasificación y la cirugía usan para
referirse a él. Los ficheros se regeneran enteros; llevan la huella del mapa completo."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from generadores.existente.leer_xml import leer_existente

DIRECTORIO = Path("docs") / "07-bonita" / "existente"
CABECERA = "<!-- generado por tools/arnes.sh mapa: no editar -->"


def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def huella(elem) -> str:
    """sha256 (12 hex) del JSON canónico de `elem`: cambia si cambia cualquier valor suyo."""
    return hashlib.sha256(_json(elem).encode("utf-8")).hexdigest()[:12]


def _indice(existente: dict) -> dict[str, dict]:
    """Identificador -> elemento, para todo lo que el mapa nombra."""
    idx: dict[str, dict] = {}
    for objeto, datos in existente["bdm"]["objetos"].items():
        idx[f"bdm/{objeto}"] = datos
        for atributo, a in datos["atributos"].items():
            idx[f"bdm/{objeto}/{atributo}"] = a
    org = existente["organizacion"]
    for g in org["grupos"]:
        idx[f"org/grupo/{g}"] = {"ruta": g}
    for r in org["roles"]:
        idx[f"org/rol/{r}"] = {"rol": r}
    for u, membresias in org["usuarios"].items():
        idx[f"org/usuario/{u}"] = {"usuario": u, "membresias": membresias}
    for clave, pool in existente["pools"].items():
        base = f"proc/{clave}"
        for k, n in pool["nodos"].items():
            idx[f"{base}/nodo/{k}"] = n
        for k, t in pool["transiciones"].items():
            idx[f"{base}/transicion/{k}"] = t
        for tarea, inputs in pool["contratos"].items():
            for i, tipo in inputs.items():
                idx[f"{base}/contrato/{tarea}/{i}"] = {"tarea": tarea, "input": i, "tipo": tipo}
    return idx


def elemento(existente: dict, identificador: str) -> dict | None:
    """El elemento de `existente` con ese identificador, o None si no existe."""
    return _indice(existente).get(identificador)


def _celda(valor) -> str:
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    return str(valor).replace("|", "\\|").replace("\n", "<br>")


def _tabla(columnas: list[str], filas: list[list]) -> list[str]:
    if not filas:
        return ["_(ninguno)_", ""]
    out = ["| " + " | ".join(columnas) + " |", "|" + "|".join("---" for _ in columnas) + "|"]
    out += ["| " + " | ".join(_celda(c) for c in fila) + " |" for fila in filas]
    return out + [""]


def _cabecera(titulo: str, h: str) -> list[str]:
    return [CABECERA, "---", f"huella: {h}", "---", "", f"# {titulo}", ""]


def _id(x: str) -> str:
    return f"`{x}`"


def _bdm(existente: dict, h: str) -> str:
    bdm = existente["bdm"]
    out = _cabecera("BDM existente", h)
    out += [f"Paquete: `{bdm['paquete']}`" if bdm["paquete"] else "Paquete: —", ""]
    out += ["## Objetos", ""] + _tabla(["Identificador", "Objeto", "Paquete"],
                                       [[_id(f"bdm/{o}"), o, d["paquete"]] for o, d in bdm["objetos"].items()])
    for objeto, datos in bdm["objetos"].items():
        out += [f"## {objeto}", "", f"Identificador: {_id('bdm/' + objeto)}", ""]
        out += _tabla(["Identificador", "Atributo", "Tipo", "Obligatorio", "Múltiple", "Longitud", "Relación"],
                      [[_id(f"bdm/{objeto}/{n}"), n, a["tipo"], a["obligatorio"], a["multiple"], a["longitud"],
                        a["relacion"]] for n, a in datos["atributos"].items()])
    return "\n".join(out).rstrip("\n") + "\n"


def _organizacion(existente: dict, h: str) -> str:
    org = existente["organizacion"]
    out = _cabecera("Organización existente", h)
    out += ["## Grupos", ""] + _tabla(["Identificador", "Grupo"], [[_id(f"org/grupo/{g}"), g] for g in org["grupos"]])
    out += ["## Roles", ""] + _tabla(["Identificador", "Rol"], [[_id(f"org/rol/{r}"), r] for r in org["roles"]])
    out += ["## Usuarios", ""] + _tabla(
        ["Identificador", "Usuario", "Membresías (rol en grupo)"],
        [[_id(f"org/usuario/{u}"), u, "; ".join(f"{r} en {g}" for r, g in ms)] for u, ms in org["usuarios"].items()])
    return "\n".join(out).rstrip("\n") + "\n"


def _pool(clave: str, pool: dict, h: str) -> str:
    base = f"proc/{clave}"
    out = _cabecera(f"Pool {clave}", h)
    out += [f"Fichero: `{pool['fichero']}`", f"xmi:id: `{pool['xmi_id']}`", ""]
    out += ["## Lanes", ""] + _tabla(["Lane", "xmi:id", "Actor"],
                                      [[n, d["id"], d["actor"]] for n, d in pool["lanes"].items()])
    out += ["## Nodos", ""] + _tabla(
        ["Identificador", "Nombre", "Tipo", "Lane", "xmi:id"],
        [[_id(f"{base}/nodo/{k}"), n["nombre"], n["tipo"], n["lane"], n["id"]] for k, n in pool["nodos"].items()])
    out += ["## Transiciones", ""] + _tabla(
        ["Identificador", "Desde", "Hacia", "Condición", "xmi:id"],
        [[_id(f"{base}/transicion/{k}"), t["desde"], t["hacia"], t["condicion"], t["id"]]
         for k, t in pool["transiciones"].items()])
    out += ["## Contratos", ""] + _tabla(
        ["Identificador", "Tarea", "Input", "Tipo"],
        [[_id(f"{base}/contrato/{t}/{i}"), t, i, tipo] for t, inputs in pool["contratos"].items()
         for i, tipo in inputs.items()])
    out += ["## No interpretados", ""] + (
        [f"- {x}" for x in pool["no_interpretados"]] + [""] if pool["no_interpretados"] else ["_(ninguno)_", ""])
    return "\n".join(out).rstrip("\n") + "\n"


def escribir_mapa(proyecto: Path) -> list[Path]:
    """Escribe el mapa en `docs/07-bonita/existente/` (bdm.md, organizacion.md y un fichero por pool) y devuelve las
    rutas. Lee todo antes de escribir: si algo falla, no se escribe nada."""
    proyecto = Path(proyecto)
    existente = leer_existente(proyecto)
    h = huella(existente)
    contenidos = {"bdm.md": _bdm(existente, h), "organizacion.md": _organizacion(existente, h)}
    for clave, pool in existente["pools"].items():
        contenidos[f"{clave.replace('@', '-')}.md"] = _pool(clave, pool, h)
    destino = proyecto / DIRECTORIO
    destino.mkdir(parents=True, exist_ok=True)
    rutas = []
    for nombre, texto in contenidos.items():
        ruta = destino / nombre
        ruta.write_text(texto, encoding="utf-8")
        rutas.append(ruta)
    return rutas
