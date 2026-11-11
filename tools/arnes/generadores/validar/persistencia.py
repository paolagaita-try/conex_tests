"""Validaciones del hilo `persistencia` (Plan 5, R-07 y R-08) sobre una spec ya combinada.

- Business variables (R-08): nombres únicos en el pool, distintos de los de las process variables, y `multiple`
  booleano. Una variable múltiple solo admite operaciones sobre la variable entera.
- Operación sobre la business variable entera (R-07; `destino` sin punto que es una business variable): solo un
  script (`expresion.tipo == "groovy"`). Una por variable y contexto (lo dice también «una operación por destino» de
  `spec.py`).
- Inputs con `por_operacion` (§3.4, los produce `contratos-documentos`): cada ID `op_<contexto>.<bv>` debe ser una
  operación entera de ese mismo contexto (la instanciación o la tarea del contrato) y su Groovy debe nombrar el input
  (o su raíz, si es un hijo).

Los mensajes siguen G-8: `fichero › sección › fila: qué falla («valor» debe ser «forma»)`.
"""
from __future__ import annotations

from generadores.escribir.proc.datos import simbolos_usados
from generadores.leer import donde

FB, FC = "bdm.md", "contratos.md"
INSTANCIACION = "(instanciacion)"
_BV = donde(FB, "Decisión de persistencia", "Business variables del pool")


def _ubic_operaciones(p: dict, clave: str) -> str:
    if clave == INSTANCIACION:
        return donde(FC, "Contrato de instanciación", p.get("nombre"))
    tipo = next((n.get("tipo") for n in p.get("nodos", []) if n.get("id") == clave), None)
    if tipo == "humana":
        return donde(FC, "Contratos de tarea humana", f"ctr_{clave}")
    return donde(FC, "Operaciones de tareas de servicio y script", clave)


def _contexto(clave: str) -> str:
    """Contexto de la marca `op_<contexto>.<bv>` (§2.17)."""
    return "instanciacion" if clave == INSTANCIACION else clave


def _business_variables(p: dict, err: list[str]) -> dict[str, dict]:
    pvs = {v.get("nombre") for v in p.get("variables", [])}
    vistas: dict[str, dict] = {}
    for b in p.get("business_variables", []):
        nombre = b.get("nombre")
        u = donde(_BV, nombre)
        if nombre in vistas:
            err.append(f"{u}: business variable repetida en el pool «{p.get('nombre')}»")
        if nombre in pvs:
            err.append(f"{u}: «{nombre}» es a la vez business variable y process variable del pool "
                       f"«{p.get('nombre')}»; los nombres no pueden coincidir")
        if not isinstance(b.get("multiple", False), bool):
            err.append(f"{u}: multiple «{b.get('multiple')}» debe ser true o false («`{nombre}: {b.get('objeto')}` "
                       "(múltiple)» en bdm.md)")
        vistas.setdefault(nombre, b)
    return vistas


def _operaciones(p: dict, bvs: dict[str, dict], err: list[str]) -> None:
    pvs = {v.get("nombre") for v in p.get("variables", [])}
    for clave, ops in p.get("operaciones", {}).items():
        u = _ubic_operaciones(p, clave)
        for o in ops:
            destino, expr = o.get("destino"), o.get("expresion") or {}
            if not isinstance(destino, str):
                continue
            if "." in destino:
                bv = destino.split(".", 1)[0]
                if bvs.get(bv, {}).get("multiple"):
                    err.append(f"{u}: «{destino}»: la business variable «{bv}» es múltiple y solo admite operaciones "
                               f"sobre la variable entera («`bv {bv}` ← `texto` (`op_{_contexto(clave)}.{bv}`)»)")
                continue
            if destino not in bvs or destino in pvs:
                continue
            if expr.get("tipo") != "groovy":
                err.append(f"{u}: «bv {destino}» (la business variable entera) solo admite un script, no "
                           f"«{expr.get('tipo')}» («`bv {destino}` ← `texto` (`op_{_contexto(clave)}.{destino}`)»)")


def _inputs(inputs: list[dict], ruta: str = ""):
    for i in inputs:
        r = f"{ruta}{i.get('nombre')}"
        yield r, i
        yield from _inputs(i.get("hijos") or [], r + ".")


def _por_operacion(p: dict, bvs: dict[str, dict], err: list[str]) -> None:
    for clave, c in p.get("contratos", {}).items():
        ctx = _contexto(clave)
        ops = {f"op_{ctx}.{o.get('destino')}": o for o in p.get("operaciones", {}).get(clave, [])
               if isinstance(o.get("destino"), str) and o["destino"] in bvs}
        u_ctr = (donde(FC, "Contrato de instanciación", p.get("nombre")) if clave == INSTANCIACION
                 else donde(FC, "Contratos de tarea humana", f"ctr_{clave}"))
        for ruta, i in _inputs(c.get("inputs", [])):
            raiz = ruta.split(".", 1)[0]
            for id_ in i.get("por_operacion") or []:
                u = donde(u_ctr, ruta)
                op = ops.get(id_)
                if op is None:
                    err.append(f"{u}: op. «{id_}» no existe en esta tarea (operaciones enteras de «{clave}»: "
                               f"{', '.join(ops) or 'ninguna'}); debe ser «op_{ctx}.<business variable>»")
                    continue
                valor = (op.get("expresion") or {}).get("valor")
                if isinstance(valor, str) and not simbolos_usados(valor, [raiz]):
                    err.append(f"{u}: el Groovy de «{id_}» no nombra el input «{raiz}» que dice consumir")


def _orden_de_instanciacion(p: dict, err: list[str]) -> None:
    """El motor evalúa los valores iniciales de las business variables en el orden de `bdm.md` (D-61): el Groovy de
    una operación de instanciación no puede leer una business variable declarada después (la vería nula). Revisión
    final, I-4."""
    orden = [b.get("nombre") for b in p.get("business_variables", [])]
    for o in p.get("operaciones", {}).get(INSTANCIACION, []):
        e = o.get("expresion") or {}
        duena = (o.get("destino") or "").split(".", 1)[0]
        if e.get("tipo") != "groovy" or duena not in orden:
            continue
        despues = orden[orden.index(duena) + 1:]
        for otra in simbolos_usados(e.get("valor") or "", despues):
            err.append(f"{donde(_ubic_operaciones(p, INSTANCIACION), o.get('destino'))}: el valor inicial de «{duena}» "
                       f"lee la business variable «{otra}», declarada después en {FB} › Decisión de persistencia "
                       "(Business variables del pool); el motor las inicializa en ese orden (D-61) y la vería nula. "
                       f"Declara «{otra}» antes que «{duena}»")


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    for p in spec.get("procesos", []):
        bvs = _business_variables(p, err)
        _operaciones(p, bvs, err)
        _por_operacion(p, bvs, err)
        _orden_de_instanciacion(p, err)
