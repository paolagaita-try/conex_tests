#!/usr/bin/env python3
"""graph-apply.py — escribe los campos estructurados del grafo en los docs (issue #86, --apply).

Tras la aprobación humana, materializa en los docs de discovery lo que hoy vive implícito:

  1. En `epicas.md`, un `depende_de: [EP-…]` ESTRUCTURADO por épica, con el grafo EFECTIVO
     (declarado ∪ derivado de las `depende_de_duras` de las HU). Hace explícito el grafo
     (resuelve #56 y la deriva P5) sin tocar ningún AC ni borrar nada.
  2. Opcional (`--from propuesta.json`, salida de `--propose`): reasigna el `epica:` de cada HU
     a su bloque de la partición aprobada. Solo con códigos de épica REALES (una partición con
     labels sintéticos de split —`EP-002-b`— se rechaza: la renumeración es decisión humana).

Carve-out §9.2: `epicas.md` y las `HU-*.md` son discovery, así que escribir aquí es un acto
con aprobación humana. Por eso **`--apply` es DRY-RUN por defecto**: enseña el plan y no escribe
nada hasta `--yes`. NUNCA toca los AC (solo el campo `depende_de` de la sección de la épica y el
frontmatter `epica:` de las HU). Prepara, además, el `graph-sync` posterior.

Uso:
    graph-apply.py [--epicas …] [--historias …] [--from propuesta.json] [--yes] [--format human|json]

Códigos de salida: 0 = plan generado (o aplicado con --yes) · 1 = entrada ilegible / propuesta
con labels no canónicos.
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True

from graph_common import (RE_CODIGO, cargar_hus, construir_modelo, grafo_efectivo)

RE_HEADING = re.compile(r"^(\s{0,3}#{1,6}\s+.*)$")
RE_DEPENDE_ESTRUCT = re.compile(r"^\s*(?:-\s*)?depende_de\s*:", re.IGNORECASE)
RE_EPICA_FM = re.compile(r"^(\s*epica\s*:\s*).*$", re.IGNORECASE)


def materializar_epicas(texto, deps_por_epica):
    """Devuelve (texto_nuevo, cambios[]) con un `depende_de: [...]` estructurado por sección de
    épica (lo actualiza si existe, lo inserta tras el encabezado si no). No toca más líneas."""
    lineas = texto.splitlines()
    # Localiza las secciones: (código, línea_encabezado).
    secciones = []
    for i, ln in enumerate(lineas):
        if RE_HEADING.match(ln):
            cods = RE_CODIGO.findall(ln)
            if cods:
                secciones.append((cods[0], i))
    cambios = []
    # Procesa de abajo a arriba para que las inserciones no corran los índices.
    for n in range(len(secciones) - 1, -1, -1):
        code, inicio = secciones[n]
        fin = secciones[n + 1][1] if n + 1 < len(secciones) else len(lineas)
        deps = deps_por_epica.get(code, [])
        valor = "[%s]" % ", ".join(deps)
        linea_nueva = "depende_de: %s" % valor
        # ¿Existe ya un depende_de estructurado en la sección?
        idx = None
        for j in range(inicio + 1, fin):
            if RE_DEPENDE_ESTRUCT.match(lineas[j]):
                idx = j
                break
        if idx is not None:
            if lineas[idx].strip() != linea_nueva:
                cambios.append("%s: depende_de %s → %s"
                               % (code, lineas[idx].split(":", 1)[1].strip(), valor))
                lineas[idx] = linea_nueva
        else:
            if deps:  # no ensuciar con `[]` donde no había nada
                lineas.insert(inicio + 1, linea_nueva)
                cambios.append("%s: + depende_de %s" % (code, valor))
    return "\n".join(lineas) + ("\n" if texto.endswith("\n") else ""), cambios


def reasignar_hus(dir_historias, asignacion):
    """asignacion: {hu: epica_destino}. Devuelve [(ruta, hu, de, a)] para las HU a mover.
    No escribe: solo planifica (el caller aplica con --yes)."""
    planes = []
    for ruta_base in sorted(os.listdir(dir_historias)) if os.path.isdir(dir_historias) else []:
        if not ruta_base.startswith("HU-") or not ruta_base.endswith(".md"):
            continue
        ruta = os.path.join(dir_historias, ruta_base)
        m = RE_CODIGO.search(ruta_base) or None
        try:
            with open(ruta, encoding="utf-8") as fh:
                lineas = fh.read().splitlines()
        except (IOError, OSError):
            continue
        # el código de la HU y su epica actual salen del frontmatter
        hu_code, epica_actual, idx_epica = None, None, None
        for j, ln in enumerate(lineas):
            mm = re.match(r"^\s*id\s*:\s*(\S+)", ln, re.IGNORECASE)
            if mm:
                c = re.search(r"\bHU-(?:[A-Za-z]{1,6}-)?\d{1,4}\b", mm.group(1))
                hu_code = c.group(0) if c else None
            me = RE_EPICA_FM.match(ln)
            if me:
                idx_epica = j
                ce = RE_CODIGO.search(ln)
                epica_actual = ce.group(0) if ce else None
        if not hu_code:
            c = re.search(r"\bHU-(?:[A-Za-z]{1,6}-)?\d{1,4}\b", ruta_base)
            hu_code = c.group(0) if c else None
        destino = asignacion.get(hu_code)
        if destino and idx_epica is not None and destino != epica_actual:
            planes.append((ruta, hu_code, epica_actual, destino, idx_epica, lineas))
    return planes


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts = {"epicas": "docs/03-backlog/epicas.md", "historias": "docs/04-historias",
            "from": None, "yes": False, "format": "human"}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--yes":
            opts["yes"] = True
            i += 1
            continue
        if a in ("--epicas", "--historias", "--from", "--format"):
            if i + 1 >= len(argv):
                print("graph-apply: %s exige un valor" % a, file=sys.stderr)
                return 1
            val = argv[i + 1]
            if a == "--format" and val not in ("human", "json"):
                print("graph-apply: --format debe ser human|json", file=sys.stderr)
                return 1
            opts[a[2:]] = val
            i += 2
            continue
        print("graph-apply: opción desconocida: %s" % a, file=sys.stderr)
        return 1

    if not os.path.isfile(opts["epicas"]) or not os.path.isdir(opts["historias"]):
        print("graph-apply: faltan los docs (%s / %s)" % (opts["epicas"], opts["historias"]),
              file=sys.stderr)
        return 1
    try:
        epicas, _, _ = construir_modelo(opts["epicas"], opts["historias"])
        with open(opts["epicas"], encoding="utf-8") as fh:
            texto = fh.read()
    except (IOError, OSError) as e:
        print("graph-apply: no se pudieron leer los docs: %s" % e, file=sys.stderr)
        return 1

    # Asignación de HU (solo con --from): valida que la partición use códigos REALES.
    asignacion = {}
    if opts["from"]:
        try:
            with open(opts["from"], encoding="utf-8") as fh:
                prop = json.load(fh)
        except (IOError, OSError, ValueError) as e:
            print("graph-apply: no se pudo leer la propuesta %s: %s" % (opts["from"], e),
                  file=sys.stderr)
            return 1
        for b in prop.get("particion") or []:
            label = b.get("label", "")
            if not re.match(r"^EP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", label) or label not in epicas:
                print("graph-apply: la partición usa el label no canónico %r (un split necesita "
                      "que un humano le asigne un EP-XXX real antes de --apply)" % label,
                      file=sys.stderr)
                return 1
            for h in b.get("hus") or []:
                asignacion[h] = label

    # El grafo efectivo (declarado ∪ derivado) por épica — lo que se materializa.
    g = grafo_efectivo(epicas)
    deps_por_epica = {c: sorted(g.get(c, ())) for c in epicas}
    texto_nuevo, cambios_ep = materializar_epicas(texto, deps_por_epica)
    planes_hu = reasignar_hus(opts["historias"], asignacion)

    if opts["format"] == "json":
        json.dump({"dry_run": not opts["yes"],
                   "epicas_cambios": cambios_ep,
                   "hus_reasignadas": [{"hu": p[1], "de": p[2], "a": p[3]} for p in planes_hu]},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        modo = "APLICAR" if opts["yes"] else "DRY-RUN (usa --yes para escribir)"
        print("graph-apply [%s] — carve-out §9.2: escribe discovery, NO toca AC." % modo)
        print("epicas.md: %d campo(s) `depende_de` a materializar" % len(cambios_ep))
        for c in cambios_ep:
            print("  · %s" % c)
        print("HU a reasignar `epica:`: %d" % len(planes_hu))
        for p in planes_hu:
            print("  · %s: %s → %s" % (p[1], p[2], p[3]))

    if opts["yes"]:
        if cambios_ep:
            with open(opts["epicas"], "w", encoding="utf-8") as fh:
                fh.write(texto_nuevo)
        for ruta, hu, de, a, idx, lineas in planes_hu:
            lineas[idx] = re.sub(r"(:\s*).*$", r"\g<1>%s" % a, lineas[idx], count=1)
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lineas) + "\n")
        print("\nEscrito. Siguiente: `slice-ops.sh graph-sync` para proponer el grafo al hub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
