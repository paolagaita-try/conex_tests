"""Filas del caso en el payload de un paso del journey (hueco 6 del MVP «Política corta»; contrato §2.14, «Filas del
caso en el payload»).

Un texto del payload de una tarea humana puede nombrar el `persistenceId` de una fila de un agregado del caso, que
los contratos con `persistenceId_string` necesitan (editar una fila existente):

| Forma | Es |
|---|---|
| `{caso}` | el caseId |
| `{bv}` | la fila de la business variable simple `bv` |
| `{bv[n]}` | la n-ésima fila (desde 1) de la business variable múltiple `bv` |
| `{bv.relacion}` | el objeto de la relación simple `relacion` del objeto de `bv` |
| `{bv.relacion[n]}` | la n-ésima fila de la relación múltiple `relacion` |
| `{bv[n].relacion[m]}` | lo mismo, desde la n-ésima fila de una business variable múltiple |

Se sustituye como texto (dentro de las comillas del JSON). Se resuelve justo antes de ejecutar la tarea, ya asignada,
como lo haría su formulario: `GET API/bpm/userTask/<id>/context` da `<bv>_ref` (`storageId_string` en una simple,
`storageIds_string` en una múltiple, en el orden de la lista) y, con relación,
`GET API/bdm/businessData/<clase de bv>/<id>/<relacion>` da la lista (o el objeto) del que se toma `persistenceId_string`.
Formato de `storageIds`/`storageIds_string` y la ruta de la relación sobre una composición no `LAZY`: medidos en el
bundle 2026.2 (D-85, D-86 de `conocimiento/compatibilidad-2026.2.md`); la relación simple (el objeto) y la
agregación múltiple por esa ruta quedan [no verificado]. Una cabeza que no es `caso` ni una business
variable del pool de la tarea no es una referencia: el texto se envía tal cual (lo valida `validar/journey_filas.py`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# `{{x}}` (una variable de Postman) no es una referencia.
REF = re.compile(r"(?<!\{)\{([A-Za-z_]\w*)(?:\[(\d+)\])?(?:\.([A-Za-z_]\w*)(?:\[(\d+)\])?)?\}(?!\})")
CASO = "caso"


@dataclass(frozen=True)
class Referencia:
    texto: str
    bv: str
    n: int | None
    relacion: str | None
    m: int | None


def _de(m: re.Match) -> Referencia:
    return Referencia(m.group(0), m.group(1), int(m.group(2)) if m.group(2) else None, m.group(3),
                      int(m.group(4)) if m.group(4) else None)


def _textos(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _textos(x)
    elif isinstance(v, list):
        for x in v:
            yield from _textos(x)


def referencias(payload, cabezas: set[str] | None = None) -> list[Referencia]:
    """Las referencias de los textos de `payload`, en orden y sin repetir; con `cabezas`, solo las que empiezan por
    una de ellas."""
    vistas: dict[str, Referencia] = {}
    for t in _textos(payload):
        for m in REF.finditer(t):
            r = _de(m)
            if (cabezas is None or r.bv in cabezas) and r.texto not in vistas:
                vistas[r.texto] = r
    return list(vistas.values())


def _variable(i: int, k: int) -> str:
    return f"fila_{i}_{k}"


def sustituir(payload, i: int, refs: list[Referencia]):
    """El payload con cada referencia cambiada por su variable de la colección (`{caso}` → `{{caseId}}`)."""
    por_texto = {r.texto: f"{{{{{_variable(i, k)}}}}}" for k, r in enumerate(_filas(refs), 1)}
    por_texto.update({r.texto: "{{caseId}}" for r in refs if r.bv == CASO})

    def cambiar(v):
        if isinstance(v, str):
            return REF.sub(lambda m: por_texto.get(m.group(0), m.group(0)), v)
        if isinstance(v, dict):
            return {k: cambiar(x) for k, x in v.items()}
        if isinstance(v, list):
            return [cambiar(x) for x in v]
        return v

    return cambiar(payload)


def _filas(refs: list[Referencia]) -> list[Referencia]:
    return [r for r in refs if r.bv != CASO]


def peticiones(c: str, i: int, refs: list[Referencia], clases: dict[str, str], peticion, j) -> list[dict]:
    """Contexto de la tarea (`{{taskId}}`) y, por cada referencia con relación, la lectura de la relación. `clases`:
    business variable -> clase Java de su objeto; `peticion` y `j` son `_peticion` y `_j` de journey.py."""
    filas = _filas(refs)
    if not filas:
        return []
    lineas = ['pm.test("contexto de la tarea 200", () => pm.response.to.have.status(200));',
              "const ctx = pm.response.code === 200 ? pm.response.json() : {};",
              "const id = (x) => x === undefined || x === null ? undefined : String(x);"]
    for k, r in enumerate(filas, 1):
        destino = _variable(i, k) + ("_padre" if r.relacion else "")
        ref = f"ctx[{j(r.bv + '_ref')}]"
        if r.n is None:
            valor = f"{ref} && id({ref}.storageId_string !== undefined ? {ref}.storageId_string : {ref}.storageId)"
        else:
            valor = (f"{ref} && id(({ref}.storageIds_string || {ref}.storageIds || [])[{r.n - 1}])")
        lineas += [
            f"const v{k} = {valor};",
            f"pm.test({j('contexto: ' + r.texto + ' (' + r.bv + '_ref)')}, () => pm.expect(Boolean(v{k}), "
            f"JSON.stringify({ref})).to.be.true);",
            f"pm.collectionVariables.set({j(destino)}, v{k} || \"\");",
        ]
    out = [peticion(f"[{c}] {i}. contexto de la tarea", "GET", "API/bpm/userTask/{{taskId}}/context", test=lineas)]
    for k, r in enumerate(filas, 1):
        if not r.relacion:
            continue
        variable = _variable(i, k)
        indice = (r.m or 1) - 1
        out.append(peticion(f"[{c}] {i}. fila {r.texto}", "GET",
                            f"API/bdm/businessData/{clases[r.bv]}/{{{{{variable}_padre}}}}/{r.relacion}", test=[
            f"pm.test({j(r.relacion + ' 200')}, () => pm.response.to.have.status(200));",
            "const r = pm.response.code === 200 ? pm.response.json() : null;",
            ("const filas = Array.isArray(r) ? r : [];" if r.m else "const filas = r && !Array.isArray(r) ? [r] : [];"),
            f"const f = filas[{indice}];",
            f"pm.test({j(r.relacion + ' de la fila padre tiene ≥ ' + str(indice + 1) + ' filas (' + r.texto + ')')}, "
            "() => pm.expect(Boolean(f && f.persistenceId !== undefined), JSON.stringify(r)).to.be.true);",
            f"pm.collectionVariables.set({j(variable)}, f ? String(f.persistenceId_string !== undefined ? "
            "f.persistenceId_string : f.persistenceId) : \"\");",
        ]))
    return out

