#!/usr/bin/env python3
"""front-plan.py — selecciona el conjunto disjunto máximo de épicas no fundacionales.

[EP-OR-08-C] Este script SIGUE SIENDO LOCAL (spec §4.2-C rev. 4): es el generador del plan
(conjunto disjunto + merge_order) que un humano aprueba al abrir el front en la consola del
hub. No llama al runtime ni lee el estado: entra JSON por stdin, sale JSON por stdout.

stdin: JSON [{"epica","layer","files_scope":[glob],"depends_on":[EP-XXX],"family"?}]
stdout: {"selected":[...],"serialized":[{"epica","reason"}],"excluded_foundational":[...]}
opciones: --width N (P9, default 3) · --built-families f1,f2 (P8)
Determinista: orden por 'epica'. Solape de globs por prefijo de directorio o glob idéntico.

Las compuertas, en orden (METODOLOGIA §5 «Compuertas del front» y §5-ter P8/P9):
  G1  `layer` fundacional  -> excluded_foundational (nunca en paralelo).
  P8  regla del pionero: en una familia (campo `family`, o el área derivada del files_scope) SIN
      miembro ya archivado (`--built-families`), solo la pionera (menor código) entra; las
      hermanas esperan a que sus patrones suban al cimiento -> serialized.
  G2a `files_scope` vacío o ausente -> serialized. «Sin `files_scope` declarado, una épica no
      es candidata al front» (METODOLOGIA:343): fail-CLOSED. Que dos épicas sin ámbito
      declarado salieran «disjuntas» era exactamente el fallo que el front no puede permitirse.
  G2b camino en el DAG de `depends_on` con una épica ya seleccionada -> serialized. Dos épicas
      encadenadas no son paralelizables aunque sus ficheros no se toquen: la de abajo construye
      sobre lo que la de arriba todavía no ha mergeado.
  G2c solape de `files_scope` con una épica ya seleccionada -> serialized.
  P9  ancho del frente: a lo sumo --width épicas en paralelo (2–3); el resto espera -> serialized.
"""
import json, sys, fnmatch

def overlap(a, b):
    for ga in a:
        for gb in b:
            if ga == gb or fnmatch.fnmatch(ga, gb) or fnmatch.fnmatch(gb, ga):
                return True
            pa, pb = ga.split("*", 1)[0], gb.split("*", 1)[0]
            # Fail closed: a leading/empty-prefix wildcard could match anything → assume overlap.
            if not pa or not pb:
                return True
            if pa.startswith(pb) or pb.startswith(pa):
                return True
    return False

def is_foundational(cand):
    """G1 normalizada. El bundle del grafo emite `layer` en MAYÚSCULA (graph-bundle.py lo
    `.upper()`a porque el hub lo exige así) mientras METODOLOGIA lo escribe en minúscula: un
    `== "foundational"` a secas dejaba pasar `FOUNDATIONAL` al front, en silencio y justo en la
    compuerta que más caro sale saltarse."""
    layer = cand.get("layer")
    return isinstance(layer, str) and layer.strip().lower() == "foundational"

def reachability(cands):
    """Alcance transitivo de `depends_on` entre las candidatas (clausura por Floyd-Warshall
    booleano; los conjuntos de épicas de un front son de decenas, no de miles).

    Se calcula sobre TODAS las candidatas, fundacionales incluidas: un camino EP-A → EP-F → EP-B
    encadena A y B aunque la fundacional del medio no entre al front. Las referencias a épicas
    que no vienen en la entrada se ignoran — aquí no se inventa un grafo que no se ha visto."""
    codes = [c.get("epica") for c in cands if isinstance(c.get("epica"), str)]
    known = set(codes)
    reach = {c: set() for c in codes}
    for c in cands:
        code = c.get("epica")
        if code not in known:
            continue
        for dep in c.get("depends_on") or []:
            if isinstance(dep, str) and dep in known and dep != code:
                reach[code].add(dep)
    for k in codes:
        for i in codes:
            if k in reach[i]:
                reach[i] |= reach[k]
    return reach

def _empty_result():
    return {"selected": [], "serialized": [], "excluded_foundational": []}

DEFAULT_WIDTH = 3  # P9: ancho máximo del frente (2–3 agentes); más solo añade coordinación.

def familia(c):
    """Área/familia de una épica (P8). Prefiere el campo `family`; si no, la deriva de los dos
    primeros segmentos del prefijo de su primer `files_scope` (p.ej. `src/pagos/**` → `src/pagos`).
    None si no hay señal — entonces P8 no aplica a esa épica."""
    fam = c.get("family")
    if isinstance(fam, str) and fam.strip():
        return fam.strip()
    sc = c.get("files_scope") or []
    if not sc or not isinstance(sc[0], str):
        return None
    pref = sc[0].split("*", 1)[0].strip("/")
    if not pref:
        return None
    return "/".join(pref.split("/")[:2])

def parse_args(argv):
    """({width, built}, error). --width N (P9, default 3); --built-families csv (P8: familias
    que ya tienen un miembro archivado, cuyas hermanas sí pueden paralelizarse)."""
    opts = {"width": DEFAULT_WIDTH, "built": set()}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--width", "--built-families"):
            if i + 1 >= len(argv):
                return opts, "%s exige un valor" % a
            if a == "--width":
                v = argv[i + 1]
                if not v.isdigit() or int(v) < 1:
                    return opts, "--width debe ser un entero ≥ 1"
                opts["width"] = int(v)
            else:
                opts["built"] = {x.strip() for x in argv[i + 1].split(",") if x.strip()}
            i += 2
            continue
        return opts, "opción desconocida: %s" % a
    return opts, None

def main():
    opts, err = parse_args(sys.argv[1:])
    if err:
        # Fail-open: una opción mal escrita no debe tumbar el plan; se usan los defaults.
        opts = {"width": DEFAULT_WIDTH, "built": set()}
    try:
        cands = json.load(sys.stdin)
        if not isinstance(cands, list) or not all(isinstance(c, dict) for c in cands):
            raise ValueError("entrada inválida: se esperaba una lista de objetos")
        cands = sorted(cands, key=lambda c: c.get("epica",""))
        reach = reachability(cands)
        excluded = [c["epica"] for c in cands if is_foundational(c)]
        pool = [c for c in cands if not is_foundational(c)]
        serialized = []

        # P8 — regla del pionero: en una familia SIN miembro ya archivado, solo la pionera (la
        # de menor código) entra; sus hermanas esperan a que sus patrones suban al cimiento. Las
        # familias ya iniciadas (en --built-families) no se restringen.
        por_familia = {}
        for c in pool:
            fam = familia(c)
            if fam is not None:
                por_familia.setdefault(fam, []).append(c["epica"])
        no_pioneras = set()
        for fam, miembros in por_familia.items():
            if fam in opts["built"] or len(miembros) < 2:
                continue
            pionera = sorted(miembros)[0]
            for code in miembros:
                if code != pionera:
                    no_pioneras.add(code)
        if no_pioneras:
            pool = [c for c in pool if c["epica"] not in no_pioneras]
            for code in sorted(no_pioneras):
                serialized.append({"epica": code,
                                   "reason": "regla del pionero (P8): la primera épica de la familia se construye sola"})

        # G2 — selección disjunta.
        selected, sel_scopes = [], []
        for c in pool:
            code = c["epica"]
            sc = c.get("files_scope") or []
            if not sc:
                serialized.append({"epica": code,
                                   "reason": "sin files_scope declarado: no es candidata al front (METODOLOGIA §5 G2)"})
            elif any(code in reach.get(s, ()) or s in reach.get(code, ()) for s in selected):
                serialized.append({"epica": code,
                                   "reason": "dependencia en el grafo con una épica ya seleccionada"})
            elif any(overlap(sc, s) for s in sel_scopes):
                serialized.append({"epica": code, "reason": "solape de files_scope con épica seleccionada"})
            else:
                selected.append(code); sel_scopes.append(sc)

        # P9 — ancho del frente: a lo sumo `width` épicas en paralelo; el resto espera (coste de
        # integración, rebase y re-smoke crecen con el ancho). Determinista: quedan las primeras.
        if len(selected) > opts["width"]:
            for code in selected[opts["width"]:]:
                serialized.append({"epica": code,
                                   "reason": "ancho del frente (P9): máximo %d épicas en paralelo" % opts["width"]})
            selected = selected[:opts["width"]]

        print(json.dumps({"selected":selected,"serialized":serialized,"excluded_foundational":excluded}))
    except Exception:
        print(json.dumps(_empty_result()))
    return 0

if __name__ == "__main__":
    sys.exit(main())
