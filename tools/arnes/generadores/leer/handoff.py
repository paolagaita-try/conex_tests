"""Lector de `docs/07-bonita/handoff.md` y de los gates de `docs/.flow-state.json`.

La documentación está lista para construir solo si el handoff dice `estado: listo-para-construccion` y los cinco
gates del perfil Bonita (`gates.bonita.{entrada, capa-0 … capa-3}`, formato de la skill `bonita-cerrar-capa`) están
en `pasa`, en el flow-state y en la tabla del handoff.

Con `modo: existente` en el frontmatter (proyecto Bonita ya existente) se añade el gate `cambios` (debe estar en `pasa`)
y las capas 0 a 3 pueden estar en `pasa` o en `no aplica`: el documento de cambios sustituye a las capas completas.
"""
from __future__ import annotations

from generadores.leer import donde, filas, seccion, tabla
from generadores.md import Documento

FH, FS = "handoff.md", ".flow-state.json"
GATES = ["entrada", "capa-0", "capa-1", "capa-2", "capa-3"]
LISTO = "listo-para-construccion"
MODO_EXISTENTE = "existente"
GATES_EXISTENTE = GATES + ["cambios"]
NO_APLICA = "no aplica"


def leer_handoff(doc: Documento | None, flow_state: dict | None) -> tuple[dict, list[str]]:
    errores: list[str] = []
    existente = doc is not None and doc.frontmatter.get("modo") == MODO_EXISTENTE
    gates_req = GATES_EXISTENTE if existente else GATES

    def admitidos(gate: str) -> tuple[str, ...]:
        return ("pasa", NO_APLICA) if existente and gate.startswith("capa") else ("pasa",)

    if doc is not None:
        estado = doc.frontmatter.get("estado")
        if estado != LISTO:
            errores.append(f"{FH}: estado «{estado or '—'}» en el frontmatter; debe ser «{LISTO}»")
        sec = seccion(doc, "Estado de los gates", FH, errores)
        t = filas(tabla(sec, "Gate", ("Estado",), donde(FH, "Estado de los gates"), errores))
        if sec is not None and len(t) != len(gates_req):
            errores.append(f"{donde(FH, 'Estado de los gates')}: debe tener {len(gates_req)} filas (una por gate)")
        for f in t:
            nombre = f["Gate"].split(" (")[0].strip()
            if f["Estado"].strip() not in admitidos(nombre.replace(" ", "-")):
                debe = " o ".join(f"«{e}»" for e in admitidos(nombre.replace(" ", "-")))
                errores.append(f"{donde(FH, 'Estado de los gates', nombre)}: "
                               f"estado «{f['Estado'].strip()}»; debe ser {debe}")
    if flow_state is not None:
        gates = (flow_state.get("gates") or {}).get("bonita")
        if not isinstance(gates, dict):
            errores.append(f"{FS}: falta «gates.bonita»")
            gates = {}
        for g in gates_req:
            u = donde(FS, "gates.bonita", g)
            if not isinstance(gates.get(g), dict):
                errores.append(f"{u}: falta el gate")
            elif gates[g].get("estado") not in admitidos(g):
                debe = " o ".join(f"«{e}»" for e in admitidos(g))
                errores.append(f"{u}: estado «{gates[g].get('estado')}»; debe ser {debe}")
    if existente:
        return {"modo": MODO_EXISTENTE, "mapa_huella": doc.frontmatter.get("mapa_huella", "")}, errores
    return {}, errores
