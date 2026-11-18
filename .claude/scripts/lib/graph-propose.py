#!/usr/bin/env python3
"""graph-propose.py — propone una partición del grafo de épicas (issue #86, P1).

Busca la partición que balancea COSTE (tokens) y DURACIÓN (tiempo con k agentes), bajo las
restricciones de la política del grafo (§5-ter): tope de tamaño (P2), ninguna épica sin HU con
AC (P3), convexidad (P4), coherencia (una HU solo se une a épicas de su misma área de código)
y sin mezclar `draft` con `lista`. Determinista, sin red, sin dependencias de terceros.

MODELO DE COSTE (cuatro términos, P1). Por épica e con n HU y t tramos:
    w(e) = F + C_HU·n + max(0, t-1)·(S + ρ·n)
El coste total añade la INTEGRACIÓN: cada épica de negocio que CONVIVE en el tiempo con otra
(bajo k agentes) paga I. Con k=1 no hay convivencia y I no se paga.
    coste(k) = Σ_e w(e) + I·|épicas que solapan en el calendario|

DURACIÓN con k agentes: las fundacionales van en serie y primero (drenan el frente, P7/§5-bis);
las de negocio se planifican sobre k agentes respetando el DAG derivado (list scheduling).

OBJETIVO: minimizar  coste(k)/C* + duración(k)/T*  (un 1 % de tokens pesa igual que un 1 % de
tiempo). C*/T* son los de la partición ACTUAL, así que f=2.0 es la de partida y < 2.0 mejora.

Los parámetros F, C_HU, S, ρ, I son DEFAULTS razonables (calibrables por proyecto con
`--calibrate`, pendiente); se pueden sobreescribir por CLI. El prototipo de referencia vive en
el proyecto consumidor; aquí se reconstruye el modelo descrito en la issue.

Uso:
    graph-propose.py [--epicas …] [--historias …] [--agents 3] [--cap 6]
                     [--out docs/.reviews] [--format human|json] [--no-write]

Salida: la tabla de la FRONTERA (variantes: épicas, coste, duración con 2 y 3 agentes), la
partición RECOMENDADA, y —salvo `--no-write`— una propuesta en `docs/.reviews/` + un bundle
preparado. NUNCA escribe en el discovery (docs/01-prd … docs/04-historias).

Códigos de salida: 0 = propuesta generada · 1 = entrada ilegible.
"""
import datetime
import json
import math
import os
import re
import sys

sys.dont_write_bytecode = True

from graph_common import (DEFAULT_CAP, cargar_hus, construir_modelo, detectar_ciclos,
                          prefijo_glob)

# ── Parámetros del modelo de coste (defaults; calibrables con `--calibrate`) ──────────────
F_FIJO = 10.0        # coste fijo del ciclo por épica (DoR + change + TDD + smoke + adversarial)
C_HU = 2.0           # coste marginal por HU
S_TRAMO = 3.0        # coste fijo de un tramo extra
RHO = 0.5            # factor de relectura de contexto por tramo extra (sobre el tamaño W=n HU)
I_INTEGRACION = 8.0  # coste de integración por épica que convive con otra rama
TRAMO_SIZE = 3       # HU por tramo (tramos = ceil(n / TRAMO_SIZE))

# Fichero de costes calibrados (lo escribe `graph-calibrate.py`); si existe, gana sobre los
# defaults. Se puede fijar con `--cost`.
COST_DEFAULT_PATH = "docs/.reviews/graph-cost.json"


def cargar_costos(path):
    """Reasigna los parámetros del modelo desde un JSON {F,C_HU,S,RHO,I,TRAMO}. Silencioso si no
    existe o es ilegible (se usan los defaults). Devuelve la ruta usada o None."""
    global F_FIJO, C_HU, S_TRAMO, RHO, I_INTEGRACION, TRAMO_SIZE
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            c = json.load(fh)
    except (IOError, OSError, ValueError):
        return None
    if not isinstance(c, dict):
        return None
    F_FIJO = float(c.get("F", F_FIJO))
    C_HU = float(c.get("C_HU", C_HU))
    S_TRAMO = float(c.get("S", S_TRAMO))
    RHO = float(c.get("RHO", RHO))
    I_INTEGRACION = float(c.get("I", I_INTEGRACION))
    TRAMO_SIZE = int(c.get("TRAMO", TRAMO_SIZE)) or TRAMO_SIZE
    return path


def tramos_de(n, declarado):
    if declarado is not None:
        return max(1, declarado)
    return max(1, math.ceil(n / TRAMO_SIZE)) if n else 1


def w_epica(n, tramos):
    return F_FIJO + C_HU * n + max(0, tramos - 1) * (S_TRAMO + RHO * n)


# ── Partición ──────────────────────────────────────────────────────────────────────────────
# Una partición es una lista de "épicas-partición": {label, hus:set, layer, linea, area,
# estado}. Se deriva del modelo de discovery y la búsqueda local la transforma.
class Particion:
    def __init__(self, bloques):
        self.bloques = bloques  # list of dicts

    def copia(self):
        return Particion([{**b, "hus": set(b["hus"])} for b in self.bloques])

    def deps(self, duras_hu, dueno):
        """Arcos entre bloques derivados de las deps duras entre HU."""
        label_de = {}
        for b in self.bloques:
            for h in b["hus"]:
                label_de[h] = b["label"]
        g = {b["label"]: set() for b in self.bloques}
        for h, destinos in duras_hu.items():
            la = label_de.get(h)
            if la is None:
                continue
            for d in destinos:
                lb = label_de.get(d)
                if lb and lb != la:
                    g[la].add(lb)
        return g


def particion_inicial(epicas, hus):
    """La partición ACTUAL, tal como la declaran los docs (una épica = un bloque)."""
    bloques = []
    for code in sorted(epicas):
        e = epicas[code]
        area = prefijo_glob(e["files_scope"][0]) if e["files_scope"] else code
        estados = {hus[h]["estado"] for h in e["hus"] if hus[h].get("estado")}
        estado = "lista" if estados == {"lista"} else ("draft" if estados else "lista")
        bloques.append({
            "label": code, "hus": set(e["hus"]), "layer": e["layer"] or "business",
            "linea": e["linea_release"], "area": area, "estado": estado,
        })
    return Particion(bloques)


# ── Simulación de duración y coste con k agentes ──────────────────────────────────────────
def planificar(particion, duras_hu, dueno, k):
    """List scheduling: fundacionales en serie primero, negocio sobre k agentes respetando el
    DAG derivado. Devuelve (duracion, intervalos{label:(ini,fin)}, n_solapan)."""
    g = particion.deps(duras_hu, dueno)
    por_label = {b["label"]: b for b in particion.bloques}
    dur = {}
    for b in particion.bloques:
        n = len(b["hus"])
        dur[b["label"]] = w_epica(n, tramos_de(n, None))

    intervalos = {}
    t_cursor = 0.0
    # Fundacionales en serie, en orden topológico aproximado (por nº de deps).
    fundacionales = [b["label"] for b in particion.bloques if b["layer"] == "foundational"]
    for la in sorted(fundacionales, key=lambda x: (len(g.get(x, ())), x)):
        intervalos[la] = (t_cursor, t_cursor + dur[la])
        t_cursor += dur[la]

    # Negocio: list scheduling sobre k agentes respetando deps de negocio.
    negocio = [b["label"] for b in particion.bloques if b["layer"] != "foundational"]
    pendientes = set(negocio)
    fin = {la: intervalos[la][1] for la in fundacionales}  # fundacionales ya terminadas
    agentes = [t_cursor] * max(1, k)  # cada agente libre a partir de t_cursor
    while pendientes:
        listos = [la for la in pendientes
                  if all((d not in pendientes) for d in g.get(la, ()))]
        if not listos:  # ciclo residual: romper determinista para no colgar
            listos = [sorted(pendientes)[0]]
        # Asigna el más pesado al agente que antes se libera (heurística LPT).
        listos.sort(key=lambda la: (-dur[la], la))
        for la in listos:
            if not pendientes:
                break
            if la not in pendientes:
                continue
            idx = min(range(len(agentes)), key=lambda i: agentes[i])
            inicio = max(agentes[idx],
                         max([fin.get(d, 0.0) for d in g.get(la, ())] + [t_cursor]))
            agentes[idx] = inicio + dur[la]
            intervalos[la] = (inicio, agentes[idx])
            fin[la] = agentes[idx]
            pendientes.discard(la)

    duracion = max((iv[1] for iv in intervalos.values()), default=0.0)

    # Integración: nº de bloques de negocio cuyo intervalo solapa con otro de negocio.
    solapan = 0
    for la in negocio:
        a0, a1 = intervalos[la]
        for lb in negocio:
            if lb == la:
                continue
            b0, b1 = intervalos[lb]
            if a0 < b1 and b0 < a1:
                solapan += 1
                break
    return duracion, intervalos, solapan


def coste_total(particion, solapan):
    base = 0.0
    for b in particion.bloques:
        n = len(b["hus"])
        base += w_epica(n, tramos_de(n, None))
    return base + I_INTEGRACION * solapan


def evaluar(particion, duras_hu, dueno, k):
    dur, _, solapan = planificar(particion, duras_hu, dueno, k)
    return coste_total(particion, solapan), dur


# ── Restricciones ───────────────────────────────────────────────────────────────────────
def factible(particion, hus, cap):
    g = particion.deps(hus_duras_map(hus), None)
    if detectar_ciclos(g):
        return False  # P4
    for b in particion.bloques:
        n = len(b["hus"])
        if n == 0 or n > cap:
            return False  # P2 / P3 (vacía)
        if not any(hus[h]["has_ac"] for h in b["hus"]):
            return False  # P3 (sin AC)
    return True


def hus_duras_map(hus):
    return {h: [d for d in hus[h]["duras"] if d in hus] for h in hus}


# ── Búsqueda local (hill-climbing con merge / split / mover-HU) ───────────────────────────
def candidatas_merge(particion):
    """Pares de bloques fusionables: misma área, misma capa, misma línea, mismo estado."""
    out = []
    bs = particion.bloques
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, b = bs[i], bs[j]
            if (a["area"] == b["area"] and a["layer"] == b["layer"]
                    and a["linea"] == b["linea"] and a["estado"] == b["estado"]):
                out.append((a["label"], b["label"]))
    return out


def aplicar_merge(particion, la, lb):
    p = particion.copia()
    a = next(b for b in p.bloques if b["label"] == la)
    bb = next(b for b in p.bloques if b["label"] == lb)
    a["hus"] |= bb["hus"]
    p.bloques = [b for b in p.bloques if b["label"] != lb]
    return p


def aplicar_split(particion, label, cap):
    b = next(x for x in particion.bloques if x["label"] == label)
    if len(b["hus"]) < 2:
        return None
    p = particion.copia()
    blk = next(x for x in p.bloques if x["label"] == label)
    hus_ord = sorted(blk["hus"])
    mitad = len(hus_ord) // 2
    nuevo = {**blk, "hus": set(hus_ord[mitad:]), "label": label + "-b"}
    blk["hus"] = set(hus_ord[:mitad])
    p.bloques.append(nuevo)
    return p


def buscar_local(inicial, hus, cap, k, c_star, t_star, max_iter=200):
    duras = hus_duras_map(hus)
    actual = inicial
    f_actual = objetivo(actual, duras, k, c_star, t_star)
    for _ in range(max_iter):
        mejor, f_mejor = None, f_actual
        # Splits (parte lo que excede el tope o es grande).
        for b in list(actual.bloques):
            if len(b["hus"]) > min(cap, TRAMO_SIZE * 2):
                cand = aplicar_split(actual, b["label"], cap)
                if cand and factible(cand, hus, cap):
                    f = objetivo(cand, duras, k, c_star, t_star)
                    if f < f_mejor:
                        mejor, f_mejor = cand, f
        # Merges (une bloques pequeños coherentes).
        for la, lb in candidatas_merge(actual):
            cand = aplicar_merge(actual, la, lb)
            if factible(cand, hus, cap):
                f = objetivo(cand, duras, k, c_star, t_star)
                if f < f_mejor:
                    mejor, f_mejor = cand, f
        if mejor is None:
            break
        actual, f_actual = mejor, f_mejor
    return actual, f_actual


def objetivo(particion, duras, k, c_star, t_star):
    coste, dur = evaluar(particion, duras, None, k)
    return (coste / c_star if c_star else 0) + (dur / t_star if t_star else 0)


# ── Frontera y propuesta ──────────────────────────────────────────────────────────────────
def variantes(inicial, hus, cap, k, c_star, t_star):
    """Genera las variantes de la frontera: actual, solo-splits (fina), solo-merges (gruesa),
    y el óptimo de la búsqueda local."""
    duras = hus_duras_map(hus)
    vs = [("Actual", inicial)]

    # Fina: parte todo lo que supere TRAMO_SIZE, mientras sea factible.
    fina = inicial.copia()
    cambiado = True
    while cambiado:
        cambiado = False
        for b in list(fina.bloques):
            if len(b["hus"]) > TRAMO_SIZE:
                cand = aplicar_split(fina, b["label"], cap)
                if cand and factible(cand, hus, cap):
                    fina, cambiado = cand, True
                    break
    vs.append(("Fina", fina))

    # Gruesa: fusiona todo lo coherente hasta el tope.
    gruesa = inicial.copia()
    cambiado = True
    while cambiado:
        cambiado = False
        for la, lb in candidatas_merge(gruesa):
            cand = aplicar_merge(gruesa, la, lb)
            if factible(cand, hus, cap):
                gruesa, cambiado = cand, True
                break
    vs.append(("Gruesa", gruesa))

    opt, _ = buscar_local(inicial, hus, cap, k, c_star, t_star)
    vs.append(("Óptimo (búsqueda local)", opt))
    return vs


def fila_frontera(nombre, particion, duras):
    c2, d2 = evaluar(particion, duras, None, 2)
    c3, d3 = evaluar(particion, duras, None, 3)
    return {"variante": nombre, "epicas": len(particion.bloques),
            "coste": round(c2, 1), "dur_2": round(d2, 1), "dur_3": round(d3, 1)}


def render_markdown(frontera, recomendada, k, epicas_recom):
    hoy = datetime.date.today().isoformat()
    L = ["# Propuesta de grafo de épicas (balance coste/paralelismo)", "",
         "> Generada por `graph-propose.py` (#86, P1) el %s. Es una PROPUESTA de solo lectura:" % hoy,
         "> no toca el discovery. La aprobación es humana; `--apply` la escribe tras el visto bueno.",
         "", "## Frontera coste vs. duración", "",
         "| Variante | Épicas | Coste (rel.) | Duración 2 agentes | Duración 3 agentes |",
         "|---|---|---|---|---|"]
    for f in frontera:
        marca = " **(recomendada)**" if f["variante"] == recomendada else ""
        L.append("| %s%s | %d | %s | %s | %s |"
                 % (f["variante"], marca, f["epicas"], f["coste"], f["dur_2"], f["dur_3"]))
    L += ["", "## Partición recomendada (%d agentes)" % k, ""]
    for b in epicas_recom:
        L.append("- **%s** (%s, %d HU, línea %s): %s"
                 % (b["label"], b["layer"], len(b["hus"]), b["linea"] or "—",
                    ", ".join(sorted(b["hus"]))))
    L += ["", "## Parámetros del modelo (defaults, calibrables)",
          "- F=%.0f · C_HU=%.0f · S=%.0f · ρ=%.1f · I=%.0f · tramo=%d HU"
          % (F_FIJO, C_HU, S_TRAMO, RHO, I_INTEGRACION, TRAMO_SIZE), ""]
    return "\n".join(L) + "\n"


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts = {"epicas": "docs/03-backlog/epicas.md", "historias": "docs/04-historias",
            "agents": 2, "cap": DEFAULT_CAP, "out": "docs/.reviews",
            "format": "human", "write": True, "cost": None}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-write":
            opts["write"] = False
            i += 1
            continue
        if a in ("--epicas", "--historias", "--agents", "--cap", "--out", "--format", "--cost"):
            if i + 1 >= len(argv):
                print("graph-propose: %s exige un valor" % a, file=sys.stderr)
                return 1
            val = argv[i + 1]
            if a == "--agents":
                opts["agents"] = max(1, int(val)) if val.isdigit() else 2
            elif a == "--cap":
                opts["cap"] = max(1, int(val)) if val.isdigit() else DEFAULT_CAP
            elif a == "--format":
                if val not in ("human", "json"):
                    print("graph-propose: --format debe ser human|json", file=sys.stderr)
                    return 1
                opts["format"] = val
            else:
                opts[a[2:]] = val
            i += 2
            continue
        print("graph-propose: opción desconocida: %s" % a, file=sys.stderr)
        return 1

    # Costes calibrados: --cost explícito, o el fichero convencional si existe (si no, defaults).
    cost_usado = cargar_costos(opts["cost"] or COST_DEFAULT_PATH)

    if not os.path.isfile(opts["epicas"]) or not os.path.isdir(opts["historias"]):
        print("graph-propose: faltan los docs (%s / %s)" % (opts["epicas"], opts["historias"]),
              file=sys.stderr)
        return 1
    try:
        epicas, _, _ = construir_modelo(opts["epicas"], opts["historias"])
        hus = cargar_hus(opts["historias"])
    except (IOError, OSError) as e:
        print("graph-propose: no se pudieron leer los docs: %s" % e, file=sys.stderr)
        return 1
    hus = {h: v for h, v in hus.items() if v["epica"] in epicas}
    if not epicas or not hus:
        print("graph-propose: no hay épicas/HU que optimizar", file=sys.stderr)
        return 1

    k = opts["agents"]
    inicial = particion_inicial(epicas, hus)
    duras = hus_duras_map(hus)
    c_star, t_star = evaluar(inicial, duras, None, k)
    c_star = c_star or 1.0
    t_star = t_star or 1.0

    vs = variantes(inicial, hus, opts["cap"], k, c_star, t_star)
    frontera = [fila_frontera(n, p, duras) for n, p in vs]
    # Recomendada: mínima f al nº de agentes pedido, entre las factibles.
    mejor_nombre, mejor_f, mejor_part = None, float("inf"), inicial
    for n, p in vs:
        if not factible(p, hus, opts["cap"]):
            continue
        f = objetivo(p, duras, k, c_star, t_star)
        if f < mejor_f:
            mejor_nombre, mejor_f, mejor_part = n, f, p

    epicas_recom = sorted(mejor_part.bloques, key=lambda b: b["label"])
    salida_path = None
    if opts["write"]:
        try:
            os.makedirs(opts["out"], exist_ok=True)
            salida_path = os.path.join(opts["out"],
                                       "%s-grafo-propuesta.md" % datetime.date.today().isoformat())
            with open(salida_path, "w", encoding="utf-8") as fh:
                fh.write(render_markdown(frontera, mejor_nombre, k, epicas_recom))
        except (IOError, OSError) as e:
            print("graph-propose: no se pudo escribir la propuesta: %s" % e, file=sys.stderr)
            salida_path = None

    if opts["format"] == "json":
        json.dump({"agents": k, "recomendada": mejor_nombre, "frontera": frontera,
                   "particion": [{"label": b["label"], "layer": b["layer"],
                                  "linea": b["linea"], "hus": sorted(b["hus"])}
                                 for b in epicas_recom],
                   "proposal_path": salida_path, "cost_source": cost_usado},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        if cost_usado:
            print("Costes calibrados de %s (F=%.1f C_HU=%.1f S=%.1f ρ=%.2f I=%.1f)."
                  % (cost_usado, F_FIJO, C_HU, S_TRAMO, RHO, I_INTEGRACION))
        print("Frontera coste vs. duración (%d agentes objetivo):" % k)
        print("  %-26s %-7s %-12s %-10s %-10s" % ("variante", "épicas", "coste", "dur@2", "dur@3"))
        for f in frontera:
            marca = "  ← recomendada" if f["variante"] == mejor_nombre else ""
            print("  %-26s %-7d %-12s %-10s %-10s%s"
                  % (f["variante"], f["epicas"], f["coste"], f["dur_2"], f["dur_3"], marca))
        print("\nPartición recomendada (%s): %d épicas" % (mejor_nombre, len(epicas_recom)))
        for b in epicas_recom:
            print("  %s (%s, %d HU, línea %s)" % (b["label"], b["layer"], len(b["hus"]),
                                                  b["linea"] or "—"))
        if salida_path:
            print("\nPropuesta escrita en %s (no se tocó el discovery)." % salida_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
