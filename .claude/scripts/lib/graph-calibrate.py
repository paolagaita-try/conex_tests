#!/usr/bin/env python3
"""graph-calibrate.py — calibra el modelo de coste del grafo (issue #86, --calibrate / P12).

Lee la TELEMETRÍA de tokens por fase de las épicas ya archivadas y estima, por mínimos
cuadrados, los parámetros del modelo de coste que usa `--propose`:

    tokens(e) = F + C_HU·n + S·(t-1) + ρ·(t-1)·n + I·[convive con otra rama]

donde n = nº de HU, t = nº de tramos. Es una regresión lineal en [1, n, (t-1), (t-1)·n, conc];
se resuelve con álgebra pura (ecuaciones normales + inversa, sin numpy). Informa de cada
parámetro con su intervalo de confianza del 95 % (± 1,96·error estándar) y escribe el fichero de
costes que `graph-propose.py` carga (gana sobre los defaults).

TELEMETRÍA (entrada, `--telemetry`, JSON): lista —o {"epics":[…]}— de registros por épica
archivada:
    {"epic":"EP-001","hu":3,"tramos":1,"concurrent":false,"tokens":12345}
`tokens` puede venir desglosado por fase, y se suma:
    {"epic":"EP-002","hu":5,"tramos":2,"concurrent":true,
     "phases":{"dor":800,"change":5000,"tdd":3000,"smoke":600,"adversarial":4000,"dod":700,"integration":1500}}

Parámetros NO identificables (p.ej. ninguna épica con tramos>1, o ninguna concurrente) se dejan
en su default y se marcan como tales — no se inventan.

Uso:
    graph-calibrate.py [--telemetry docs/.reviews/graph-telemetry.json]
                       [--out docs/.reviews/graph-cost.json] [--format human|json] [--no-write]

Códigos de salida: 0 = calibrado · 1 = telemetría ilegible o insuficiente.
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True

# Defaults (espejo de graph-propose.py): base para los parámetros no identificables.
DEFAULTS = {"F": 10.0, "C_HU": 2.0, "S": 3.0, "RHO": 0.5, "I": 8.0, "TRAMO": 3}
# (nombre, función de la feature sobre (n, t, conc))
FEATURES = [
    ("F", lambda n, t, c: 1.0),
    ("C_HU", lambda n, t, c: float(n)),
    ("S", lambda n, t, c: float(t - 1)),
    ("RHO", lambda n, t, c: float((t - 1) * n)),
    ("I", lambda n, t, c: 1.0 if c else 0.0),
]


# ── Álgebra lineal mínima (pura, sin dependencias) ────────────────────────────────────────
def transpuesta(M):
    return [[M[i][j] for i in range(len(M))] for j in range(len(M[0]))]


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B)))
             for j in range(len(B[0]))] for i in range(len(A))]


def matvec(A, v):
    return [sum(A[i][k] * v[k] for k in range(len(v))) for i in range(len(A))]


def invertir(M):
    """Inversa por Gauss-Jordan con pivoteo parcial. Devuelve None si es singular."""
    n = len(M)
    A = [list(M[i]) + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) < 1e-12:
            return None
        A[col], A[piv] = A[piv], A[col]
        d = A[col][col]
        A[col] = [x / d for x in A[col]]
        for r in range(n):
            if r != col and abs(A[r][col]) > 1e-15:
                f = A[r][col]
                A[r] = [a - f * b for a, b in zip(A[r], A[col])]
    return [fila[n:] for fila in A]


# ── Carga de telemetría ───────────────────────────────────────────────────────────────────
def leer_telemetria(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    regs = raw.get("epics") if isinstance(raw, dict) else raw
    filas = []
    for r in regs or []:
        if not isinstance(r, dict):
            continue
        try:
            n = int(r.get("hu", 0))
            t = max(1, int(r.get("tramos", 1)))
            conc = bool(r.get("concurrent", False))
        except (TypeError, ValueError):
            continue
        if "tokens" in r:
            try:
                tok = float(r["tokens"])
            except (TypeError, ValueError):
                continue
        elif isinstance(r.get("phases"), dict):
            tok = sum(float(v) for v in r["phases"].values()
                      if isinstance(v, (int, float)))
        else:
            continue
        filas.append((n, t, conc, tok))
    return filas


def calibrar(filas):
    """Devuelve (params, info). params: {F,C_HU,S,RHO,I,TRAMO}. info trae intervalos, columnas
    activas, N y R²."""
    N = len(filas)
    # Columnas activas: el intercepto (F) siempre; las demás solo si su feature VARÍA en los
    # datos (una columna constante es inidentificable, se confunde con el intercepto).
    activas = [0]
    for idx in range(1, len(FEATURES)):
        vals = [FEATURES[idx][1](n, t, c) for n, t, c, _ in filas]
        if len(set(vals)) > 1:
            activas.append(idx)

    p = len(activas)
    if N < p:
        return None, {"error": "datos insuficientes: %d épicas para %d parámetros activos "
                               "(se necesitan ≥ %d)" % (N, p, p), "N": N}

    X = [[FEATURES[idx][1](n, t, c) for idx in activas] for n, t, c, _ in filas]
    y = [tok for _, _, _, tok in filas]
    Xt = transpuesta(X)
    XtX = matmul(Xt, X)
    XtXi = invertir(XtX)
    if XtXi is None:
        return None, {"error": "la telemetría es colineal: no identifica los parámetros", "N": N}
    beta = matvec(XtXi, matvec(Xt, y))

    # Residuos, varianza y errores estándar.
    pred = matvec(X, beta)
    rss = sum((yi - pi) ** 2 for yi, pi in zip(y, pred))
    ybar = sum(y) / N
    tss = sum((yi - ybar) ** 2 for yi in y) or 1.0
    r2 = 1.0 - rss / tss
    dof = max(1, N - p)
    sigma2 = rss / dof
    se = [math.sqrt(max(0.0, sigma2 * XtXi[i][i])) for i in range(p)]

    params = dict(DEFAULTS)
    intervalos = {}
    for pos, idx in enumerate(activas):
        nombre = FEATURES[idx][0]
        est = beta[pos]
        half = 1.96 * se[pos]
        params[nombre] = round(est, 3)
        intervalos[nombre] = {"estimado": round(est, 3), "ic95": round(half, 3),
                              "identificable": True}
    for idx, (nombre, _) in enumerate(FEATURES):
        if idx not in activas:
            intervalos[nombre] = {"estimado": DEFAULTS[nombre], "ic95": None,
                                  "identificable": False}
    return params, {"N": N, "r2": round(r2, 3), "intervalos": intervalos,
                    "activas": [FEATURES[i][0] for i in activas]}


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts = {"telemetry": "docs/.reviews/graph-telemetry.json",
            "out": "docs/.reviews/graph-cost.json", "format": "human", "write": True}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-write":
            opts["write"] = False
            i += 1
            continue
        if a in ("--telemetry", "--out", "--format"):
            if i + 1 >= len(argv):
                print("graph-calibrate: %s exige un valor" % a, file=sys.stderr)
                return 1
            val = argv[i + 1]
            if a == "--format" and val not in ("human", "json"):
                print("graph-calibrate: --format debe ser human|json", file=sys.stderr)
                return 1
            opts[a[2:]] = val
            i += 2
            continue
        print("graph-calibrate: opción desconocida: %s" % a, file=sys.stderr)
        return 1

    if not os.path.isfile(opts["telemetry"]):
        print("graph-calibrate: no se encuentra la telemetría: %s" % opts["telemetry"],
              file=sys.stderr)
        return 1
    try:
        filas = leer_telemetria(opts["telemetry"])
    except (IOError, OSError, ValueError) as e:
        print("graph-calibrate: telemetría ilegible: %s" % e, file=sys.stderr)
        return 1
    if not filas:
        print("graph-calibrate: la telemetría no tiene registros utilizables", file=sys.stderr)
        return 1

    params, info = calibrar(filas)
    if params is None:
        print("graph-calibrate: %s" % info.get("error"), file=sys.stderr)
        return 1

    out_path = None
    if opts["write"]:
        try:
            d = os.path.dirname(opts["out"])
            if d:
                os.makedirs(d, exist_ok=True)
            with open(opts["out"], "w", encoding="utf-8") as fh:
                json.dump(params, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            out_path = opts["out"]
        except (IOError, OSError) as e:
            print("graph-calibrate: no se pudo escribir %s: %s" % (opts["out"], e), file=sys.stderr)

    if opts["format"] == "json":
        json.dump({"params": params, "info": info, "cost_path": out_path},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("graph-calibrate: %d épicas archivadas · R²=%s" % (info["N"], info["r2"]))
        print("  %-6s %-12s %-16s %s" % ("param", "estimado", "IC 95%", "identificable"))
        for nombre, _ in FEATURES:
            iv = info["intervalos"][nombre]
            ic = ("± %s" % iv["ic95"]) if iv["identificable"] else "—"
            print("  %-6s %-12s %-16s %s"
                  % (nombre, iv["estimado"], ic, "sí" if iv["identificable"] else "no (default)"))
        if out_path:
            print("\nEscrito en %s — `graph-propose` lo cargará automáticamente." % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
