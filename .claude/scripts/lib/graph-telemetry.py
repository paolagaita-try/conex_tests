#!/usr/bin/env python3
"""graph-telemetry.py — registra la telemetría de coste de una épica archivada (issue #86, P12).

Cierra el bucle de calibración: al archivar una épica, deja un registro con su tamaño (HU,
tramos), si convivió con otra rama, y una MEDIDA DE COSTE, en `docs/.reviews/graph-telemetry.json`
— que `graph-calibrate.py` consume para estimar F/C_HU/S/ρ/I.

El arnés aún NO cuenta tokens por fase; hasta que lo haga, la medida por defecto es el **nº de
commits** de la épica (el proxy que usó la evidencia de la issue: «commits por épica como
indicador del coste»). Se puede dar explícitamente con `--tokens` o desglosada con `--phases`.

Uso:
    graph-telemetry.py --epic EP-XXX [--telemetry docs/.reviews/graph-telemetry.json]
        [--tokens N | --phases '{"dor":..,"change":..}' | --commits N | --auto]
        [--concurrent] [--hu N] [--tramos N] [--epicas …] [--historias …] [--format human|json]

`--auto` cuenta los commits cuyo mensaje menciona el código de la épica (`git log --grep`). HU y
tramos se derivan de los docs si no se dan. El registro reemplaza al previo de la misma épica
(idempotente). NO toca el discovery: solo escribe en `docs/.reviews/` (carve-out §9.2).

Códigos de salida: 0 = registrado · 1 = entrada inválida / sin medida de coste.
"""
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

from graph_common import construir_modelo


def commits_de_epica(code):
    """Cuenta los commits cuyo mensaje menciona el código de la épica. Fail-open: 0 si no hay git."""
    try:
        out = subprocess.run(["git", "log", "--all", "--oneline", "--grep", code],
                             capture_output=True, text=True, timeout=15)
        if out.returncode != 0:
            return None
        return sum(1 for ln in out.stdout.splitlines() if ln.strip())
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts = {"epic": None, "telemetry": "docs/.reviews/graph-telemetry.json",
            "tokens": None, "phases": None, "commits": None, "auto": False,
            "concurrent": False, "hu": None, "tramos": None,
            "epicas": "docs/03-backlog/epicas.md", "historias": "docs/04-historias",
            "format": "human"}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--concurrent", "--auto"):
            opts[a[2:]] = True
            i += 1
            continue
        if a in ("--epic", "--telemetry", "--tokens", "--phases", "--commits",
                 "--hu", "--tramos", "--epicas", "--historias", "--format"):
            if i + 1 >= len(argv):
                print("graph-telemetry: %s exige un valor" % a, file=sys.stderr)
                return 1
            opts[a[2:]] = argv[i + 1]
            i += 2
            continue
        print("graph-telemetry: opción desconocida: %s" % a, file=sys.stderr)
        return 1

    code = opts["epic"]
    if not code or not re.match(r"^EP-[A-Za-z0-9-]+$", code):
        print("graph-telemetry: --epic EP-XXX es obligatorio", file=sys.stderr)
        return 1

    # HU / tramos: de los args, o derivados de los docs.
    hu = int(opts["hu"]) if opts["hu"] and str(opts["hu"]).isdigit() else None
    tramos = int(opts["tramos"]) if opts["tramos"] and str(opts["tramos"]).isdigit() else None
    if hu is None or tramos is None:
        try:
            epicas, _, _ = construir_modelo(opts["epicas"], opts["historias"])
        except (IOError, OSError):
            epicas = {}
        e = epicas.get(code)
        if e:
            if hu is None:
                hu = len(e["hus"])
            if tramos is None:
                tramos = e["tramos"] or 1
    hu = hu if hu is not None else 0
    tramos = tramos if tramos is not None else 1

    # Medida de coste.
    registro = {"epic": code, "hu": hu, "tramos": tramos,
                "concurrent": bool(opts["concurrent"])}
    medida = None
    if opts["phases"]:
        try:
            ph = json.loads(opts["phases"])
        except ValueError:
            print("graph-telemetry: --phases no es un JSON válido", file=sys.stderr)
            return 1
        if isinstance(ph, dict) and ph:
            # El valor por nodo puede ser un número (tokens) o un objeto rico
            # {tokens, started_at, ended_at, cost_usd} (vía `graph-otel-phases --format phases-rich`).
            # Se guarda tal cual; el total lo suma quien reporte al hub.
            registro["phases"] = ph
            medida = "phases"
    elif opts["tokens"] is not None:
        try:
            registro["tokens"] = float(opts["tokens"])
            medida = "tokens"
        except ValueError:
            print("graph-telemetry: --tokens debe ser numérico", file=sys.stderr)
            return 1
    elif opts["commits"] is not None:
        try:
            registro["tokens"] = float(opts["commits"])
            registro["measure"] = "commits"
            medida = "commits"
        except ValueError:
            print("graph-telemetry: --commits debe ser numérico", file=sys.stderr)
            return 1
    elif opts["auto"]:
        n = commits_de_epica(code)
        if n is None:
            print("graph-telemetry: --auto no pudo contar commits (¿sin git?); usa --tokens/--commits",
                  file=sys.stderr)
            return 1
        registro["tokens"] = float(n)
        registro["measure"] = "commits"
        medida = "commits(auto)=%d" % n
    if medida is None:
        print("graph-telemetry: falta la medida de coste (--tokens | --phases | --commits | --auto)",
              file=sys.stderr)
        return 1

    # Append/replace idempotente en el fichero de telemetría.
    data = {"epics": []}
    if os.path.isfile(opts["telemetry"]):
        try:
            with open(opts["telemetry"], encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, dict) and isinstance(raw.get("epics"), list):
                data = raw
            elif isinstance(raw, list):
                data = {"epics": raw}
        except (IOError, OSError, ValueError):
            pass
    data["epics"] = [r for r in data["epics"]
                     if not (isinstance(r, dict) and r.get("epic") == code)]
    data["epics"].append(registro)
    data["epics"].sort(key=lambda r: r.get("epic", ""))

    try:
        d = os.path.dirname(opts["telemetry"])
        if d:
            os.makedirs(d, exist_ok=True)
        with open(opts["telemetry"], "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    except (IOError, OSError) as e:
        print("graph-telemetry: no se pudo escribir %s: %s" % (opts["telemetry"], e),
              file=sys.stderr)
        return 1

    if opts["format"] == "json":
        json.dump({"registrado": registro, "total": len(data["epics"]),
                   "telemetry": opts["telemetry"]}, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("graph-telemetry: registrada %s (hu=%d tramos=%d conc=%s medida=%s) — %d épicas en %s"
              % (code, hu, tramos, registro["concurrent"], medida, len(data["epics"]),
                 opts["telemetry"]))
        if len(data["epics"]) >= 5:
            print("  Ya hay suficientes para calibrar: `slice-ops.sh graph-calibrate`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
