"""Custodio de generados: lo versionado es exactamente lo que produce el generador.

Regenera la documentación en una copia temporal del proyecto (el real no se toca) y compara byte a byte cada fichero
que `escribir_proyecto` escribe, salvo el esqueleto editable de los formularios (es del proyecto: que falte no es un
hallazgo, y `generar` lo repone). Además, un `.proc` o `.conf` sin spec que lo produzca es un huérfano: el build usa
los ficheros versionados, no los regenerados, así que uno de más se compilaría sin que nadie lo haya pedido.

Una documentación con errores es un hallazgo; si falta un documento o el generador falla con ella, no se puede
verificar (`NoVerificable`, código 2).

En modo existente (spec 6.8) lo generado de los procesos nuevos se compara igual, regenerando en una copia con
`generar_existente`; lo que cambia la cirugía (ficheros de la línea base y `.proc`/`.conf` de versión superior) lo
vigila `check_cambios`. Los ficheros de la línea base y los de versión superior nunca son huérfanos. Con la fase
cerrada (sin `cambios.md` ni confirmación, p. ej. tras `cerrar`) solo se regeneran los procesos nuevos, sin exigir el
handoff sobre el mapa actual ni una confirmación.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from custodios import (IGNORAR, NoVerificable, docs_de_procesos_nuevos, ejecutar, mensaje, regenerar_existente,
                       ruta_doc, sin_documentacion_bonita)
from generadores.existente.confirmar import caducada
from generadores.existente.linea_base import leer_linea_base, modo_existente
from generadores.escribir.parametros import MIXTOS, extraer_bloque
from generadores.escribir import escribir_proyecto, spec_de_hola, xml_entorno
from generadores.escribir.frontend import es_esqueleto
from generadores.escribir.proc.configuraciones import ENTORNOS, entornos
from generadores.plantilla import PLANTILLA
from generadores.spec import construir_spec

# Carpetas donde un fichero que ninguna spec produce es un huérfano (el build lo usaría sin que nadie lo pida).
_CARPETAS = (("bonita-project/app/diagrams", "*.proc"), ("bonita-project/app/process_configurations", "*.conf"),
             ("bonita-project/app/profiles", "*.xml"), ("bonita-project/app/organizations", "*.xml"))
# Ficheros mixtos (los configuration.properties del módulo de parámetros y de la extensión de consultas): solo se
# compara su bloque generado entre marcadores.
_ENTORNOS = "bonita-project/app/environements"
# Sin docs (unidad 0), la organización es la de la plantilla, que el generador no reescribe.
_ORGANIZACION_PLANTILLA = "bonita-project/app/organizations/hola.xml"
# Y sus perfiles por defecto (los que genera `generar_perfiles_por_defecto` para esa organización).
_PERFILES_PLANTILLA = "bonita-project/app/profiles/default_profile.xml"


# Lo que lee `construir_spec`: sin uno de ellos no hay nada que regenerar (no se puede verificar, código 2).
_DOCS = ("07-bonita/bdm.md", "07-bonita/bpmn.md", "07-bonita/contratos.md", "07-bonita/handoff.md",
         "08-construccion/expresiones.md", "08-construccion/consultas.md", "08-construccion/caminos.md")
# En modo existente no hay journey: `caminos.md` no hace falta.
_DOCS_EXISTENTE = tuple(d for d in _DOCS if d != "08-construccion/caminos.md")


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    if modo_existente(proyecto):
        return _comprobar_existente(proyecto)
    if sin_documentacion_bonita(proyecto):
        # Unidad 0: lo único generado es `hola`; se vigila contra su spec (sin BDM ni organización propios).
        spec = spec_de_hola()
    else:
        for rel in _DOCS:
            ruta_doc(proyecto, rel)
        spec, errores = construir_spec(proyecto)
        if errores:
            return [f"la documentación no construye la spec: {e}" for e in errores]
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / (proyecto.resolve().name or "proyecto")
        shutil.copytree(proyecto, copia, ignore=IGNORAR)
        try:
            escritos = escribir_proyecto(spec, copia)
        except (ValueError, NotImplementedError, KeyError, OSError) as e:
            raise NoVerificable(f"el generador falla con esta documentación: {mensaje(e)}") from e
        hallazgos, esperados = _comparar(proyecto, copia, escritos)
    if "organizacion" not in spec:
        esperados |= {Path(_ORGANIZACION_PLANTILLA), Path(_PERFILES_PLANTILLA)}
    hallazgos += _comprobar_entornos(proyecto, spec)
    return hallazgos + _huerfanos(proyecto, esperados)


def _comprobar_existente(proyecto: Path) -> list[str]:
    """Modo existente: lo nuevo, como siempre; la línea base y las versiones superiores no son huérfanos."""
    linea_base = leer_linea_base(proyecto)
    if linea_base is None:
        raise NoVerificable("falta la línea base (.trycore-bonita-linea-base.json); adopta el proyecto")
    nuevos = docs_de_procesos_nuevos(proyecto)
    spec: dict = {}
    if nuevos:
        for rel in _DOCS_EXISTENTE:
            ruta_doc(proyecto, rel)
        spec, errores = construir_spec(proyecto)
        if errores:
            return [f"la documentación no construye la spec: {e}" for e in errores]
    esperados = {Path(rel) for rel in linea_base["ficheros"]}
    hallazgos: list[str] = []
    # Sin procesos nuevos ni confirmación vigente no se genera nada: todo .proc/.conf fuera de la línea base sobra.
    if nuevos or not caducada(proyecto):
        with tempfile.TemporaryDirectory() as tmp:
            copia, escritos, cirugia = regenerar_existente(proyecto, Path(tmp))
            hallazgos, vistos = _comparar(proyecto, copia, escritos, omitir=cirugia)
            esperados |= vistos
    hallazgos += _comprobar_entornos(proyecto, spec, set(linea_base["ficheros"]))
    return hallazgos + _huerfanos(proyecto, esperados)


def _comparar(proyecto: Path, copia: Path, escritos: list[Path],
              omitir: set[str] = frozenset()) -> tuple[list[str], set[Path]]:
    """Compara con el proyecto cada fichero que la generación escribió en `copia` (salvo el esqueleto y `omitir`) y
    devuelve los hallazgos y las rutas relativas escritas (las esperadas en el proyecto)."""
    hallazgos: list[str] = []
    esperados = set()
    for ruta in escritos:
        rel = ruta.relative_to(copia)
        esperados.add(rel)
        if es_esqueleto(rel.as_posix()) or rel.as_posix() in omitir:
            # El esqueleto es del proyecto: generar lo escribe una vez (y lo repone si falta), nunca lo vigila. Lo de
            # la cirugía (`omitir`) lo vigila check_cambios.
            continue
        real = proyecto / rel
        if not real.is_file():
            hallazgos.append(f"{rel}: falta; lo genera la documentación y no está en el proyecto")
        elif rel in MIXTOS:
            inicio, fin = MIXTOS[rel]
            esperado = extraer_bloque(ruta.read_text(encoding="iso-8859-1"), inicio, fin)
            actual = extraer_bloque(real.read_text(encoding="iso-8859-1"), inicio, fin)
            if actual is None:
                hallazgos.append(f"{rel}: falta el bloque generado entre los marcadores «{inicio}» y «{fin}»")
            elif actual != esperado:
                hallazgos.append(f"{rel}: el bloque generado es distinto de lo que genera la documentación "
                                 "(edición a mano dentro de los marcadores o documentación cambiada sin "
                                 "regenerar)")
        elif real.read_bytes() != ruta.read_bytes():
            hallazgos.append(f"{rel}: distinto de lo que genera la documentación (edición a mano o "
                             "documentación cambiada sin regenerar)")
    return hallazgos, esperados


def _huerfanos(proyecto: Path, esperados: set[Path]) -> list[str]:
    hallazgos = []
    for carpeta, patron in _CARPETAS:
        base = proyecto / carpeta
        for f in sorted(base.glob(patron)) if base.is_dir() else []:
            if f.relative_to(proyecto) not in esperados:
                hallazgos.append(f"{f.relative_to(proyecto)}: huérfano; ninguna spec lo produce y el build lo "
                                 "compilaría")
    return hallazgos


def _comprobar_entornos(proyecto: Path, spec: dict, linea_base: set[str] | None = None) -> list[str]:
    """Los entornos que usa la spec existen y son los esperados: Qualification y Production, los de la plantilla; los
    demás, lo que genera el generador. (Los que faltan y genera el generador ya salen como «falta» en
    `escribir_proyecto`.) En modo existente (`linea_base`, sus ficheros) los entornos son los del proyecto: solo se
    vigilan los que genera el generador y no están en la línea base."""
    hallazgos: list[str] = []
    for nombre in sorted({e for p in spec.get("procesos", []) for e in entornos(p)}):
        rel = Path(_ENTORNOS) / f"{nombre}.xml"
        real = proyecto / rel
        if linea_base is not None and (nombre in ENTORNOS or rel.as_posix() in linea_base):
            continue
        if nombre in ENTORNOS:
            esperado = (PLANTILLA / rel).read_bytes()
            if not real.is_file():
                hallazgos.append(f"{rel}: falta; lo declara la plantilla y no está en el proyecto")
                continue
        elif real.is_file():
            esperado = xml_entorno(nombre)
        else:
            continue
        if real.read_bytes() != esperado:
            hallazgos.append(f"{rel}: distinto de lo que generan la plantilla y la documentación (edición a mano)")
    return hallazgos


def main() -> int:
    return ejecutar("check_generados", comprobar)


if __name__ == "__main__":
    sys.exit(main())
