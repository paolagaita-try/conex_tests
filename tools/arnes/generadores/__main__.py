"""CLI de los generadores: `python3 -m generadores nuevo|generar|verificar`.

- `nuevo <destino> --nombre <n> --grupo <g> [--version 2025.1|2025.2|2026.1|2026.2] [--edicion-destino community|subscription]
  [--formularios svelte]`; el destino puede tener contenido (docs, .claude, CLAUDE.md) si no es ya un proyecto Bonita
- `adoptar <proyecto> [--nombre n] [--grupo g]`: adopta un proyecto del Studio (`modo: existente`) y crea su línea base.
- `mapa <proyecto>`: escribe el mapa de solo lectura de lo existente (`docs/07-bonita/existente/`); solo en modo existente.
- `cambios mostrar <proyecto>`: imprime la clasificación de `cambios.md` y sus discrepancias (0 sin discrepancias ni
  no soportados, 1 si los hay, 2 si no se puede leer).
- `cambios confirmar <proyecto>`: una persona confirma en su terminal la clasificación, las instancias vivas y el aviso
  del BDM; escribe `docs/08-construccion/cambios-confirmados.md` (sin terminal: código 2).
- `linea-base actualizar <proyecto> --micro-work <id>`: cierra un micro-cambio (exige `verificar` en 0): archiva
  `cambios.md` y `cambios-confirmados.md` en `docs/07-bonita/historial/<id>/`, convierte lo generado sobre lo existente
  en la nueva línea base y regenera el mapa.
- `generar <proyecto>`: documentación -> spec -> artefactos. En modo existente, lo nuevo de `bpmn.md` más la cirugía
  confirmada en `cambios-confirmados.md` sobre lo existente; sin confirmación vigente, código 2. Sin `cambios.md` ni
  `cambios-confirmados.md` (p. ej. tras cerrar), solo los procesos nuevos, sin exigir handoff ni confirmación.
- `verificar <proyecto>`: los custodios; `check_cambios` vigila lo existente en modo existente (fuera de él, verde).

Códigos de salida (los usa el arnés npm del Plan 3):
- 0: bien (`verificar`: los seis custodios en verde).
- 1: solo `verificar`: algún custodio tiene hallazgos (lo versionado no cuadra con la documentación, o la
  documentación tiene errores).
- 2: error. En `nuevo` y `generar`, no se escribió nada (nombre no válido, documentación con errores, elemento no
  soportado, Groovy inválido, fallo de disco…). En `verificar`, «no se puede verificar»: falta un documento que un
  custodio necesita o el generador falla con esta documentación; 2 gana a 1.
Los errores y los «no se puede verificar» van por stderr; lo escrito y los hallazgos, por stdout.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from custodios import (NO_VERIFICABLE, check_cambios, check_caminos, check_expresiones, check_formularios,
                       check_generados, check_inventario)
from generadores.escribir import escribir_proyecto
from generadores.existente.cerrar import cerrar
from generadores.existente.confirmar import clasificacion, confirmar, preguntar_tty
from generadores.existente.generar import generar_existente
from generadores.existente.linea_base import adoptar, modo_existente
from generadores.existente.mapa import escribir_mapa
from generadores.plantilla import FORMULARIOS, nuevo_proyecto
from generadores.spec import construir_spec

# Excepciones que son un error del usuario o del entorno (no un fallo del arnés): mensaje y código 2.
ERRORES = (ValueError, NotImplementedError, KeyError, OSError)
CUSTODIOS = (("check_inventario", check_inventario), ("check_expresiones", check_expresiones),
             ("check_caminos", check_caminos), ("check_generados", check_generados),
             ("check_formularios", check_formularios), ("check_cambios", check_cambios))


def _error(e: BaseException) -> str:
    return e.args[0] if isinstance(e, KeyError) and e.args else str(e)


def _nuevo(a) -> int:
    try:
        destino = nuevo_proyecto(Path(a.destino), a.nombre, a.grupo, a.version, a.edicion_destino, a.formularios)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        return 2
    print(f"proyecto creado en {destino}")
    return 0


def _adoptar(a) -> int:
    try:
        destino = adoptar(Path(a.proyecto), a.nombre, a.grupo)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        return 2
    print(f"proyecto adoptado en {destino}")
    return 0


def _mapa(a) -> int:
    proyecto = Path(a.proyecto)
    if not modo_existente(proyecto):
        print(f"error: {proyecto} no está en modo existente; adóptalo antes con «adoptar»", file=sys.stderr)
        return 2
    try:
        escritos = escribir_mapa(proyecto)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        return 2
    for ruta in escritos:
        print("escrito", ruta.relative_to(proyecto))
    return 0


def _cambios_mostrar(a) -> int:
    proyecto = Path(a.proyecto)
    if not modo_existente(proyecto):
        print(f"error: {proyecto} no está en modo existente; adóptalo antes con «adoptar»", file=sys.stderr)
        return 2
    try:
        resultado = clasificacion(proyecto)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        return 2
    problemas = 0
    for c in resultado:
        print(f"{c['ubic']}: {c['cambio']} {c['clase']} -> calculado: {c['calculado']}")
        if c["discrepancia"]:
            print(f"  discrepancia: {c['discrepancia']}")
            problemas += 1
        if not c["soportado"]:
            print(f"  no soportado: {c['motivo']}")
            problemas += 1
    print(f"{len(resultado)} cambio(s); {problemas} problema(s)")
    return 1 if problemas else 0


def _linea_base_actualizar(a) -> int:
    proyecto = Path(a.proyecto)
    try:
        escritos = cerrar(proyecto, a.micro_work)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        return 2
    for ruta in escritos:
        print("escrito", ruta.relative_to(proyecto))
    return 0


def _quien() -> str:
    try:
        nombre = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        nombre = ""
    return nombre.strip() or os.environ.get("USER", "") or "desconocido"


def _cambios_confirmar(a) -> int:
    proyecto = Path(a.proyecto)
    try:
        preguntar = preguntar_tty()  # primero: sin terminal no hay nada que hacer, y el agente no puede responder
        if not modo_existente(proyecto):
            print(f"error: {proyecto} no está en modo existente; adóptalo antes con «adoptar»", file=sys.stderr)
            return 2
        ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        ruta = confirmar(proyecto, preguntar, _quien(), ahora)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        return 2
    print("escrito", ruta.relative_to(proyecto))
    return 0


def _generar_existente(proyecto: Path) -> int:
    try:
        escritos = generar_existente(proyecto)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        print("no se escribió nada", file=sys.stderr)
        return 2
    for ruta in escritos:
        print("escrito", ruta.relative_to(proyecto))
    return 0


def _generar(a) -> int:
    proyecto = Path(a.proyecto)
    if modo_existente(proyecto):
        return _generar_existente(proyecto)
    try:
        spec, errores = construir_spec(proyecto)
        if errores:
            for e in errores:
                print(f"error: {e}", file=sys.stderr)
            print(f"{len(errores)} error(es); no se escribió nada", file=sys.stderr)
            return 2
        # El spec.json se serializa antes de escribir: si algo falla, no queda nada a medias.
        spec_json = json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        escritos = escribir_proyecto(spec, proyecto)
    except ERRORES as e:
        print(f"error: {_error(e)}", file=sys.stderr)
        print("no se escribió nada", file=sys.stderr)
        return 2
    for ruta in escritos:
        print("escrito", ruta.relative_to(proyecto))
    salida = proyecto / "build" / "spec.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(spec_json, encoding="utf-8")
    print("escrito", salida.relative_to(proyecto))
    return 0


def _verificar(a) -> int:
    proyecto = Path(a.proyecto)
    fallos = no_verificables = 0
    for nombre, modulo in CUSTODIOS:
        try:
            hallazgos = modulo.comprobar(proyecto)
        except NO_VERIFICABLE as e:
            print(f"[{nombre}] no se puede verificar: {_error(e)}", file=sys.stderr)
            no_verificables += 1
            continue
        for h in hallazgos:
            print(f"[{nombre}] {h}")
        if not hallazgos:
            print(f"[{nombre}] verde")
        fallos += bool(hallazgos)
    return 2 if no_verificables else 1 if fallos else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python3 -m generadores", epilog="Códigos de salida: 0 bien; 1 hallazgos de "
                                "los custodios (verificar); 2 error, sin escribir nada (nuevo, generar) o no se "
                                "puede verificar (verificar).")
    sub = p.add_subparsers(dest="orden", required=True)
    n = sub.add_parser("nuevo", help="crea un proyecto Bonita desde la plantilla")
    n.add_argument("destino")
    n.add_argument("--nombre", required=True)
    n.add_argument("--grupo", required=True)
    n.add_argument("--version", default="2026.2")
    n.add_argument("--edicion-destino", default="community", choices=("community", "subscription"))
    n.add_argument("--formularios", default="svelte", choices=FORMULARIOS)
    n.set_defaults(f=_nuevo)
    ad = sub.add_parser("adoptar", help="adopta un proyecto hecho en el Studio sin tocar bonita-project/ (0 bien, 2 error)")
    ad.add_argument("proyecto")
    ad.add_argument("--nombre")
    ad.add_argument("--grupo")
    ad.set_defaults(f=_adoptar)
    m = sub.add_parser("mapa", help="escribe el mapa de lo existente en docs/07-bonita/existente/ (0 bien, 2 error o "
                                    "proyecto sin adoptar)")
    m.add_argument("proyecto")
    m.set_defaults(f=_mapa)
    ca = sub.add_parser("cambios", help="clasificación y confirmación de los cambios sobre lo existente")
    ca_sub = ca.add_subparsers(dest="accion", required=True)
    cm = ca_sub.add_parser("mostrar", help="imprime la clasificación (0 sin problemas, 1 discrepancias o no "
                                           "soportados, 2 no se puede leer)")
    cm.add_argument("proyecto")
    cm.set_defaults(f=_cambios_mostrar)
    cc = ca_sub.add_parser("confirmar", help="una persona confirma en su terminal (sin terminal: 2)")
    cc.add_argument("proyecto")
    cc.set_defaults(f=_cambios_confirmar)
    lb = sub.add_parser("linea-base", help="la línea base de lo existente")
    lb_sub = lb.add_subparsers(dest="accion", required=True)
    la = lb_sub.add_parser("actualizar", help="cierra un micro-cambio: archiva su documentación y el resultado pasa a "
                                              "ser la nueva línea base (0 bien, 2 error o `verificar` no sale 0)")
    la.add_argument("proyecto")
    la.add_argument("--micro-work", required=True, help="nombre de la carpeta del historial (letras, números, . _ -)")
    la.set_defaults(f=_linea_base_actualizar)
    g = sub.add_parser("generar", help="genera los artefactos desde la documentación (0 bien, 2 errores sin escribir "
                                       "nada)")
    g.add_argument("proyecto")
    g.set_defaults(f=_generar)
    v = sub.add_parser("verificar", help="corre los seis custodios (0 verde, 1 hallazgos, 2 no se puede verificar)")
    v.add_argument("proyecto")
    v.set_defaults(f=_verificar)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
