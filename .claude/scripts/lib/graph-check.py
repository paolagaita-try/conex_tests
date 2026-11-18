#!/usr/bin/env python3
"""graph-check.py — valida la GRANULARIDAD del grafo de épicas (issue #86).

Determinista, sin red, sin dependencias de terceros. Lee los docs de discovery
(`docs/03-backlog/epicas.md` + `docs/04-historias/HU-*.md`) y aplica la política del grafo
(METODOLOGIA §5-ter, P1–P12). Comprueba:

  DURAS (bloquean el DoR, rc 2):
    P2  tope de tamaño: > cap HU (default 6), o > 2 tramos si `tramos:` está declarado.
    P3  ninguna épica sin HU con AC: épica sin HU, o sin ninguna HU con Given/When/Then.
    P4  convexidad: el grafo de épicas (declarado ∪ derivado de las deps duras entre HU) es
        acíclico. Un ciclo se nombra con su camino y los pares de HU que lo causan.
    P10 cierre de líneas: una épica no depende de otra en una `linea_release` posterior
        (solo cuando ambas la declaran).

  AVISOS (informan, rc 0):
    P5  deriva: el `depende_de` declarado de la épica difiere del derivado de sus HU
        (solo cuando alguna HU declara `depende_de_duras`).
    capa ausente; solape de `files_scope` entre candidatas a ir en paralelo.

Es la ÚNICA fuente de verdad del veredicto del grafo: el DoR (`dor-dod-gatekeeper`) y el
claim de runtime lo invocan vía `slice-ops.sh graph-check` y OBEDECEN su rc. La aceptación
del PO no salta las reglas duras (se parte en épicas, no en tramos). El modelo del grafo vive
en `graph_common` y lo comparte con `graph-propose.py` (--propose).

Uso:
    graph-check.py [--epicas docs/03-backlog/epicas.md] [--historias docs/04-historias/] \
                   [--epic EP-XXX] [--cap 6] [--format human|json]

Entrada: ficheros del repo (NO stdin), para ser auditable y no depender de que el modelo
arme bien un JSON. `--epic` escopa P2/P3/P10 a esa épica (P4 se evalúa sobre el grafo entero
y reporta si la épica participa en un ciclo); sin `--epic` valida todas.

Códigos de salida:
    0 = sin violaciones DURAS (puede haber avisos)
    1 = entrada ilegible (ruta inexistente, épica desconocida con `--epic`, args mal)
    2 = ≥1 violación de gate DURO (un motivo por línea en stdout)
"""
import json
import os
import re
import sys

# No escribir bytecode en el árbol del paquete: `graph_common` es un módulo importable y su
# import generaría `scripts/lib/__pycache__/`, que no debe viajar en el tarball (#86).
sys.dont_write_bytecode = True

from graph_common import (DEFAULT_CAP, MAX_TRAMOS, alcanzable, clave_de_linea,
                          construir_modelo, detectar_ciclos, entero, files_scope_solapan,
                          grafo_efectivo, nombrar_arista)


def analizar(epicas, procedencia, cap, scope):
    """Devuelve (duras, avisos) — listas de {rule, epic, detail}."""
    duras, avisos = [], []
    g = grafo_efectivo(epicas)
    objetivo = [scope] if scope else sorted(epicas)

    # P2 / P3 — por épica (escopadas a --epic si se pidió).
    for code in objetivo:
        e = epicas[code]
        n_hu = len(e["hus"])
        if n_hu > cap:
            duras.append({"rule": "P2", "epic": code,
                          "detail": "%d HU (> %d) — pártela en épicas, no en tramos; la "
                                    "aceptación del PO no lo salta" % (n_hu, cap)})
        if e["tramos"] is not None and e["tramos"] > MAX_TRAMOS:
            duras.append({"rule": "P2", "epic": code,
                          "detail": "%d tramos (> %d) — pártela en épicas"
                                    % (e["tramos"], MAX_TRAMOS)})
        if n_hu == 0:
            duras.append({"rule": "P3", "epic": code,
                          "detail": "sin ninguna HU (`epica: %s`)" % code})
        elif not e["hus_con_ac"]:
            duras.append({"rule": "P3", "epic": code,
                          "detail": "ninguna de sus %d HU tiene AC en Given/When/Then "
                                    "(Dado/Cuando/Entonces) — el verificador adversarial no "
                                    "tiene ancla" % n_hu})

    # P4 — convexidad (grafo entero; con --epic solo se reportan los ciclos que lo incluyen).
    for ciclo in detectar_ciclos(g):
        if scope and scope not in ciclo:
            continue
        cerrado = ciclo + [ciclo[0]]
        aristas = " · ".join("%s→%s (%s)" % (cerrado[i], cerrado[i + 1],
                                             nombrar_arista(cerrado[i], cerrado[i + 1], procedencia))
                             for i in range(len(ciclo)))
        duras.append({"rule": "P4", "epic": ciclo[0],
                      "detail": "ciclo %s — por %s" % (" → ".join(cerrado), aristas)})

    # P10 — cierre de líneas: no depender de una línea posterior (solo cuando ambas declaran).
    for code in objetivo:
        e = epicas[code]
        ki = clave_de_linea(e["linea_release"]) if e["linea_release"] else None
        if ki is None:
            continue
        for dep in sorted(g.get(code, ())):
            de = epicas[dep]
            kd = clave_de_linea(de["linea_release"]) if de["linea_release"] else None
            if kd is not None and kd > ki:
                duras.append({"rule": "P10", "epic": code,
                              "detail": "depende de %s, que está en una línea posterior "
                                        "(%s → %s)" % (dep, e["linea_release"], de["linea_release"])})

    # P5 — deriva declarado vs derivado (aviso; solo cuando hay deps duras entre HU).
    for code in objetivo:
        e = epicas[code]
        if not e["derivadas"]:
            continue
        solo_declarado = e["declaradas"] - e["derivadas"]
        solo_derivado = e["derivadas"] - e["declaradas"]
        if solo_declarado or solo_derivado:
            partes = []
            if solo_derivado:
                partes.append("derivado añade %s" % ", ".join(sorted(solo_derivado)))
            if solo_declarado:
                partes.append("declarado tiene de más %s" % ", ".join(sorted(solo_declarado)))
            avisos.append({"rule": "P5", "epic": code,
                           "detail": "deriva: " + "; ".join(partes)})

    # Capa ausente (aviso).
    for code in objetivo:
        if epicas[code]["layer"] is None:
            avisos.append({"rule": "layer", "epic": code, "detail": "sin `layer` declarado"})

    # Solape de files_scope entre candidatas a ir en paralelo (aviso): dos épicas de negocio
    # con scope solapado y sin relación de dependencia en ninguno de los dos sentidos.
    negocio = [c for c in objetivo if epicas[c]["layer"] == "business" and epicas[c]["files_scope"]]
    reportados = set()
    for a in negocio:
        for b in sorted(epicas):
            if b == a or epicas[b]["layer"] != "business" or not epicas[b]["files_scope"]:
                continue
            par = tuple(sorted((a, b)))
            if par in reportados:
                continue
            if files_scope_solapan(epicas[a], epicas[b]) \
                    and not alcanzable(g, a, b) and not alcanzable(g, b, a):
                reportados.add(par)
                avisos.append({"rule": "files_scope", "epic": a,
                               "detail": "solapa `files_scope` con %s sin dependencia entre "
                                         "ambas (no son disjuntas para el front)" % b})

    # P6 — siembras cruzadas (R16): dos épicas con dependencias BLANDAS recíprocas (cada una
    # necesita la forma del dato de la otra) acaban repitiendo siembras; deberían ir juntas.
    reportados_p6 = set()
    for a in objetivo:
        for b in sorted(epicas[a]["blandas"]):
            par = tuple(sorted((a, b)))
            if par in reportados_p6 or b not in epicas:
                continue
            if a in epicas[b]["blandas"]:
                reportados_p6.add(par)
                avisos.append({"rule": "P6", "epic": a,
                               "detail": "siembra cruzada con %s (dependencias blandas "
                                         "recíprocas): considera unirlas en la misma épica" % b})

    return duras, avisos


# ── Entrada / salida ─────────────────────────────────────────────────────────────────────
def parsear_argumentos(argv):
    opts = {"epicas": "docs/03-backlog/epicas.md", "historias": "docs/04-historias",
            "epic": None, "cap": DEFAULT_CAP, "format": "human"}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--epicas", "--historias", "--epic", "--cap", "--format"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return opts, "%s exige un valor" % arg
            val = argv[i + 1]
            clave = arg[2:]
            if clave == "cap":
                n = entero(val)
                if n is None or n < 1:
                    return opts, "--cap debe ser un entero ≥ 1"
                opts["cap"] = n
            elif clave == "format":
                if val not in ("human", "json"):
                    return opts, "--format debe ser human|json"
                opts["format"] = val
            else:
                opts[clave] = val
            i += 2
            continue
        return opts, "opción desconocida: %s" % arg
    if opts["epic"] and not re.match(r"^EP-[A-Za-z0-9-]+$", opts["epic"]):
        return opts, "--epic debe ser un código de épica (p.ej. EP-040)"
    return opts, None


def emitir_humano(duras, avisos, resumen):
    for d in duras:
        print("⛔ [%s] %s: %s" % (d["rule"], d["epic"], d["detail"]))
    for a in avisos:
        print("⚠ [%s] %s: %s" % (a["rule"], a["epic"], a["detail"]))
    print(resumen)


def main():
    # Salida en UTF-8 pase lo que pase: este validador es un GATE y no debe reventar por la
    # codificación de la consola (p. ej. cp1252 en Windows no admite los símbolos ⛔/⚠).
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts, error = parsear_argumentos(sys.argv[1:])
    if error:
        print("graph-check: %s" % error, file=sys.stderr)
        return 1
    if not os.path.isfile(opts["epicas"]):
        print("graph-check: no se encuentra el fichero de épicas: %s" % opts["epicas"],
              file=sys.stderr)
        return 1
    if not os.path.isdir(opts["historias"]):
        print("graph-check: no se encuentra el directorio de historias: %s "
              "(sin las HU-*.md no se puede validar el tamaño ni los AC)" % opts["historias"],
              file=sys.stderr)
        return 1
    try:
        epicas, procedencia, avisos_docs = construir_modelo(opts["epicas"], opts["historias"])
    except (IOError, OSError) as e:
        print("graph-check: no se pudieron leer los docs: %s" % e, file=sys.stderr)
        return 1

    if not epicas:
        print("graph-check: no se reconoció ninguna épica en %s "
              "(se esperaban encabezados `## EP-001 — Título`)" % opts["epicas"], file=sys.stderr)
        return 1
    if opts["epic"] and opts["epic"] not in epicas:
        print("graph-check: la épica %s no está en el grafo de %s"
              % (opts["epic"], opts["epicas"]), file=sys.stderr)
        return 1

    duras, avisos = analizar(epicas, procedencia, opts["cap"], opts["epic"])
    for a in avisos_docs:
        print("aviso: %s" % a, file=sys.stderr)

    if opts["format"] == "json":
        salida = {
            "ok": not duras,
            "cap": opts["cap"],
            "scope_epic": opts["epic"],
            "hard": duras,
            "warnings": avisos,
            "epics": {c: {"hu_count": len(e["hus"]),
                          "hus_con_ac": len(e["hus_con_ac"]),
                          "layer": e["layer"],
                          "tramos": e["tramos"],
                          "linea_release": e["linea_release"],
                          "declaradas": sorted(e["declaradas"]),
                          "derivadas": sorted(e["derivadas"])}
                      for c, e in sorted(epicas.items())},
        }
        json.dump(salida, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        ambito = (" de %s" % opts["epic"]) if opts["epic"] else ""
        resumen = ("graph-check%s: %d violación(es) dura(s), %d aviso(s) — %d épicas"
                   % (ambito, len(duras), len(avisos), len(epicas)))
        emitir_humano(duras, avisos, resumen)

    return 2 if duras else 0


if __name__ == "__main__":
    sys.exit(main())
