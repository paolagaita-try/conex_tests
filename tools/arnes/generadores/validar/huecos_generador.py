"""Validaciones del hilo `huecos-generador` (huecos del MVP «Política corta» con la 0.11.0).

- Nombres de índices y unique constraints (hueco 7, D-100): un nombre explícito de `bdm.md` («(nombre `X`)») debe
  ser válido para el validador del BDM de Bonita, y ningún nombre (explícito o generado, ni los de los `Kp*` del
  módulo de parámetros) puede repetirse.
- Formularios sin tabla de campos (hueco 2): solo valen si su contrato no tiene inputs.
"""
from __future__ import annotations

from generadores.escribir.bom import nombre_de, nombre_sql_valido, objetos_parametros
from generadores.leer import donde
from generadores.leer.matriz import F as FMATRIZ

FB = "bdm.md"
_TITULO = {"unicos": "Unique constraints", "indices": "Índices"}


def _nombres_kp() -> dict[str, str]:
    """Los nombres de índice y unique constraint del fragmento fijo del módulo de parámetros -> su objeto."""
    out = {}
    for bo in objetos_parametros():
        objeto = bo.get("qualifiedName", "").rpartition(".")[2]
        for e in bo.iter():
            if e.tag in ("uniqueConstraint", "index") and e.get("name"):
                out[e.get("name")] = f"{objeto} (módulo de parámetros)"
    return out


def _nombres_sql(bdm: dict, err: list[str]) -> None:
    vistos = _nombres_kp()
    for o in bdm.get("objetos", []):
        for clave in ("unicos", "indices"):
            u = donde(FB, "Objetos de negocio", o.get("nombre"), _TITULO[clave])
            explicitos = set(o.get(f"nombres_{clave}", {}).values())
            for campos in o.get(clave, []):
                nombre = nombre_de(o, clave, campos)
                if nombre in explicitos and not nombre_sql_valido(nombre):
                    err.append(f"{u}: el nombre «{nombre}» no es un nombre SQL válido para Bonita (debe ser una "
                               "letra y hasta 25 letras sin acentos, dígitos, «_», «#» o «@», 26 caracteres como "
                               "máximo, y no una palabra reservada de SQL; p. ej. «IX_SOL_ESTADO»). Sin "
                               "«(nombre …)» el arnés genera uno válido")
                    continue
                # Bonita no exige nombres distintos entre objetos (D-100), pero la base de datos guarda índices y
                # constraints en un mismo espacio de nombres por esquema [no verificado en H2 ni en PostgreSQL].
                if nombre in vistos:
                    err.append(f"{u}: el nombre «{nombre}» está repetido (también en {vistos[nombre]}); cada índice "
                               "y unique constraint lleva un nombre propio")
                    continue
                vistos[nombre] = f"«{o.get('nombre')} › {_TITULO[clave]}»"


def _formularios_sin_campos(spec: dict, err: list[str]) -> None:
    """Un formulario Svelte o External URL sin tabla de campos solo vale si su contrato no tiene inputs: el de
    instanciación de un pool sin inputs solo inicia el caso (MVP, `frm_instanciacion`)."""
    procesos = spec.get("procesos", [])
    for f in (spec.get("formularios") or {}).get("formularios", []):
        if not f.get("sin_tabla_campos"):
            continue
        inputs = _inputs_del_contrato(f, procesos)
        if inputs is None or inputs:
            motivo = (f"su contrato «{f.get('contrato')}» tiene inputs" if inputs else
                      f"no se encuentra su contrato «{f.get('contrato')}»")
            err.append(f"{donde(FMATRIZ, 'Detalle por formulario', f.get('id'))}: falta la tabla «| Campo | Control / "
                       f"widget | … |» ({motivo}; solo un formulario cuyo contrato no tiene inputs va sin ella)")


def _inputs_del_contrato(form: dict, procesos: list[dict]) -> list | None:
    """Los inputs del contrato del formulario (el de instanciación de su pool o el de su tarea); `None` si no lo
    encuentra. Un overview no tiene contrato: `[]`."""
    from generadores.escribir.frontend import _contrato_de  # el mismo emparejamiento que el escritor
    try:
        _, contrato = _contrato_de(form, procesos)
    except ValueError:
        return None
    return contrato.get("inputs", [])


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    _nombres_sql(spec.get("bdm", {}), err)
    _formularios_sin_campos(spec, err)
