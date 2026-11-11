"""Plan 5, hilo huecos-parametros (contrato §2.18): toda fila de negocio del Catálogo se puede sembrar en el módulo de
parámetros sin perder información (claves de las listas, campos por opción, tramo-cascada de varios campos, cascada
de niveles). Lo que no, es un error de `generar` con su ubicación («catalogo-parametros.md › Catálogo › param_x: …»):
nunca se aplana en silencio.

Integración del Plan 5: el «Catálogo `param_*`» de la matriz de formularios nombra una definición que la semilla
siembra. Una cascada de niveles o un tramo-cascada con campos no tiene definición `T` (solo `T.<nivel>` / `T.<campo>`):
un formulario que la nombrara recibiría `NO_EXISTE` del módulo (D-110). Es error, con los nombres correctos sugeridos.
"""
from __future__ import annotations

from generadores.escribir.parametros import REF_CATALOGO, codigo_de_parametro, codigo_de_referencia, generar_semilla
from generadores.leer import donde
from generadores.leer.matriz import F as FMATRIZ


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    if spec.get("parametros_negocio"):
        semilla = generar_semilla(spec, err)
        _validar_catalogos_de_formularios(spec, [d["codigo"] for d in semilla["definiciones"]], err)


def _validar_catalogos_de_formularios(spec: dict, sembradas: list[str], err: list[str]) -> None:
    ids = {f["id"] for f in spec["parametros_negocio"]}
    for form in (spec.get("formularios") or {}).get("formularios", []):
        for c in form.get("campos", []):
            for ref in REF_CATALOGO.findall(c.get("catalogo") or ""):
                base = ref.partition(".")[0]
                codigo = codigo_de_referencia(ref)
                if base not in ids or codigo in sembradas:
                    continue  # un parámetro que no es de negocio ya lo dice la lectura de la matriz (spec.py)
                raiz = codigo_de_parametro(base)
                candidatas = ([base] if raiz in sembradas else []) + [
                    f"{base}.{d[len(raiz) + 1:]}" for d in sembradas if d.startswith(raiz + ".")]
                if not candidatas:
                    continue  # la fila del Catálogo no se pudo sembrar: su error ya está
                err.append(f"{donde(FMATRIZ, 'Detalle por formulario', form['id'], c['campo'])}: el catálogo «{ref}» "
                           "no es una definición que siembre la semilla del módulo de parámetros (la semilla no tiene "
                           f"«{codigo}»); usa " + " o ".join(f"«{x}»" for x in candidatas))
