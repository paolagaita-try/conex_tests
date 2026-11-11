"""Hueco 6 (contrato §2.14, «Filas del caso en el payload»): las referencias `{caso}`, `{bv}`, `{bv[n]}`,
`{bv.relacion[n]}`… de los payloads de `caminos.md` (gramática en `generadores/escribir/journey_filas.py`).

- En una tarea humana: la cabeza es `caso` (sin índice ni relación) o una business variable del pool de la tarea; una
  simple va sin índice y una múltiple con `[n]` (desde 1); la relación es un atributo con relación del objeto de la
  business variable, con `[n]` si es múltiple y sin él si es simple.
- En la instanciación no hay caso todavía: ninguna referencia.
- Un texto que es entero `{x}` con una cabeza que no es `caso` ni una business variable es un error (el journey lo
  enviaría tal cual y la tarea no casaría con ninguna fila); dentro de un texto más largo, `{x}` es texto.
"""
from __future__ import annotations

from generadores.escribir.journey import nodo_de_paso
from generadores.escribir.journey_filas import CASO, REF, referencias
from generadores.leer import donde

FCAM = "caminos.md"
INSTANCIACION = "(instanciacion)"
EJEMPLOS = "«{caso}», «{<bv>}», «{<bv>[n]}» o «{<bv>.<relación>[n]}» (p. ej. «{solicitud.eventos[1]}»)"


def _textos(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _textos(x)
    elif isinstance(v, list):
        for x in v:
            yield from _textos(x)


def _revisar(r, bvs: dict[str, dict], atributos: dict, up: str, err: list[str]) -> None:
    f = f"{up}: «{r.texto}»"
    if r.bv == CASO:
        if r.n is not None or r.relacion:
            err.append(f"{f}: «{{caso}}» es el caseId: no lleva índice ni relación")
        return
    bv = bvs[r.bv]
    if bv.get("multiple") and r.n is None:
        err.append(f"{f}: la business variable «{r.bv}» es múltiple: di qué fila con «{{{r.bv}[n]}}» (desde 1)")
    elif not bv.get("multiple") and r.n is not None:
        err.append(f"{f}: la business variable «{r.bv}» es simple: va sin índice («{{{r.bv}}}»)")
    for indice in (r.n, r.m):
        if indice is not None and indice < 1:
            err.append(f"{f}: el índice empieza en 1 (la primera fila es [1])")
    if not r.relacion:
        return
    objeto = bv.get("objeto")
    attr = atributos.get(objeto, {}).get(r.relacion)
    if not attr or not attr.get("relacion"):
        rels = sorted(a for a, d in atributos.get(objeto, {}).items() if d.get("relacion"))
        err.append(f"{f}: «{r.relacion}» no es una relación de «{objeto}» (relaciones: {', '.join(rels) or 'ninguna'})")
        return
    if attr.get("multiple") and r.m is None:
        err.append(f"{f}: la relación «{objeto}.{r.relacion}» es múltiple: di qué fila con «[n]» (desde 1)")
    elif not attr.get("multiple") and r.m is not None:
        err.append(f"{f}: la relación «{objeto}.{r.relacion}» es simple: va sin índice")


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    procesos = spec.get("procesos", [])
    if not procesos:
        return
    for c in spec.get("caminos", []):
        u = donde(FCAM, f"Camino `{c.get('id')}`")
        for i, paso in enumerate(c.get("pasos", []), 1):
            payload = paso.get("payload")
            if not isinstance(payload, (dict, list)):
                continue
            up = donde(u, str(i))
            tarea = paso.get("tarea")
            if tarea == INSTANCIACION:
                cabezas = {CASO} | {b.get("nombre") for b in procesos[0].get("business_variables", [])}
                for r in referencias(payload, cabezas):
                    err.append(f"{up}: «{r.texto}»: en la instanciación no hay caso todavía: una fila del caso solo "
                               "se nombra en el payload de una tarea humana")
                continue
            if not isinstance(tarea, str) or tarea.startswith("("):
                continue
            try:
                proceso, _ = nodo_de_paso(procesos, tarea, {"humana"}, "una tarea humana")
            except ValueError:
                continue  # ya lo dice _validar_caminos
            bvs = {b.get("nombre"): b for b in proceso.get("business_variables", [])}
            for r in referencias(payload, set(bvs) | {CASO}):
                _revisar(r, bvs, atributos, up, err)
            for t in _textos(payload):
                m = REF.fullmatch(t)
                if m and m.group(1) not in bvs and m.group(1) != CASO:
                    err.append(f"{up}: «{t}»: «{m.group(1)}» no es «caso» ni una business variable de "
                               f"«{proceso.get('nombre')}» ({', '.join(sorted(bvs)) or 'ninguna'}); una fila del "
                               f"caso se nombra {EJEMPLOS}")
