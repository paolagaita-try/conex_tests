#!/usr/bin/env python3
"""graph-bundle.py — prepara el BUNDLE DE GRAFO que un ADMIN sube en la consola del hub.

[EP-OR-08-C] El import del grafo es un acto de GOBIERNO (spec §4.1-D rev. 4): la superficie
`POST …/graph/import` exige sesión de ADMIN y rechaza el token de agente. Por eso el arnés
**prepara y valida** el bundle en local — nunca lo sube — y `/build:onboard` se lo entrega a
una persona.

[issue #41] `epics` sale en el FORMATO EXACTO del hub (`GraphService.import_graph`,
`validate_graph`): `layer` en MAYÚSCULA (`VALID_LAYERS = {FOUNDATIONAL, BUSINESS}` — un layer
inválido rechaza el grafo ENTERO, GraphIntegrityError), historias con `code` + `title`
(el hub hace `story_in["code"]`), `title` obligatorio por épica e historia, y `release_line`
como string POR ÉPICA (las `release_lines` de la entrada se pliegan aquí). Así el mismo
objeto sirve para la pantalla de import del grafo y para embeberse como sección `graph`
del bundle de estado (`trycore-build migrate`).

[issue #56] Las dependencias entre épicas viven como PROSA en `docs/03-backlog/epicas.md`
(`**Depende de**: EP-001 (…)`), y delegar su lectura al modelo las dejó VACÍAS en el piloto
(41/41 épicas con `depends_on: []`, Lienzo sin una sola arista). `--from-docs` extrae ese
grafo de forma DETERMINISTA — regex de códigos `EP-…` sobre el campo `Depende de` de cada
sección de épica, excluyendo la propia — y lo une a lo que traiga el JSON de entrada. Si la
épica declara el campo estructurado `depende_de: [EP-001, …]`, ese gana sobre la prosa.

[EP-OR-17] `--for-sync` emite la PROYECCIÓN DE CONTRATO del carril `graph-sync`: `{"epics":[…]}`
y nada más (`GraphSyncBundle` es `extra="forbid"`; las claves de preparación son un 422). En ese
modo lo que aquí es aviso pasa a ser RECHAZO con rc 2 — el import de admin lo revisa un humano
antes de subirlo, pero una propuesta de re-sync viaja sola, y el hub rechaza el grafo ENTERO ante
una sola épica mal formada.

Uso:
    python3 graph-bundle.py < epics.json > bundle.json      # avisos por stderr
    python3 graph-bundle.py --from-docs docs/03-backlog/epicas.md < epics.json > bundle.json
    python3 graph-bundle.py --print-deps docs/03-backlog/epicas.md   # solo el grafo extraído
    python3 graph-bundle.py --for-sync --from-docs docs/03-backlog/epicas.md < epics.json

Entrada (stdin, JSON — formato de discovery, sin cambios):
    {"project_ref": "…",
     "epics": [{"code","title","layer","files_scope":[],"depends_on":[],
                "stories":[{"id"|"code","title"}]}],
     "release_lines": [{"id","epics":[]}]}

Salida (stdout, JSON): el bundle normalizado y DETERMINISTA (orden estable por código);
los problemas no bloquean: se listan como avisos en stderr y en `warnings` del bundle, con
el criterio del arnés — nada se pierde en silencio, nada bloquea la preparación.

Códigos de salida: 0 = bundle generado (con o sin avisos) · 1 = entrada ilegible
(incluye una ruta `--from-docs` que no se puede leer: se pidió extraer y no se pudo, y un
grafo sin aristas no falla solo — empobrece en silencio, que es justo lo que causó #56)
· 2 = solo con `--for-sync`: el bundle no cumple el contrato del hub (un motivo por línea en
stderr, cada uno nombrando la épica y el campo).
"""
import json
import sys
import datetime

# No escribir bytecode en el árbol del paquete: importar `graph_common` generaría
# `scripts/lib/__pycache__/`, que no debe viajar en el tarball (#86).
sys.dont_write_bytecode = True

# [issue #86] El extractor determinista de dependencias (regex + `extraer_dependencias` +
# `leer_dependencias_de_docs`) se factorizó a `graph_common` para compartirlo con
# `graph-check.py` sin duplicarlo. Co-ubicados en `scripts/lib/`, el import resuelve en el
# repo y en `.claude/scripts/lib/` del consumidor.
from graph_common import extraer_dependencias, leer_dependencias_de_docs  # noqa: F401

BUNDLE_VERSION = 2

# El contrato del hub: `validate_graph` rechaza el grafo ENTERO si un layer no está aquí.
VALID_LAYERS = {"FOUNDATIONAL", "BUSINESS"}


def norm_list(v):
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def parsear_argumentos(argv):
    """({from_docs, print_deps, for_sync}, error) — sin dependencias, mismo estilo que el resto."""
    opciones = {"from_docs": None, "print_deps": None, "for_sync": False}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--for-sync":
            opciones["for_sync"] = True
            i += 1
            continue
        if arg in ("--from-docs", "--print-deps"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                return opciones, "%s exige la ruta del fichero de épicas" % arg
            opciones["from_docs" if arg == "--from-docs" else "print_deps"] = argv[i + 1]
            i += 2
            continue
        return opciones, "opción desconocida: %s" % arg
    if opciones["from_docs"] and opciones["print_deps"]:
        # Ignorar una de las dos en silencio es exactamente el error que corrige #56.
        return opciones, "--from-docs y --print-deps son excluyentes"
    return opciones, None


# ── Proyección de contrato para el carril `graph-sync` [EP-OR-17] ─────────────────────
# `GraphSyncBundle` (event_catalog.py del hub) es `extra="forbid"` y admite SOLO `epics`: las
# claves de preparación (`bundle_version`, `kind`, `project_ref`, `generated_at`,
# `generated_by`, `depends_on_source`, `warnings`) son un 422 garantizado.
#
# Y aquí los avisos se vuelven RECHAZOS. El bundle de preparación puede seguir adelante con
# `layer` ausente porque un ADMIN lo revisa antes de subirlo; el carril de sync no tiene humano
# en medio, y el hub rechaza el grafo ENTERO ante una sola épica mal formada. Un aviso que nadie
# lee es un 422 con pasos extra.
MAX_EPICAS = 200
MAX_HISTORIAS = 100
MAX_FILES_SCOPE = 200
MAX_DEPENDS_ON = 50
LARGOS = {"code": 50, "title": 300, "release_line": 100, "docs_ref": 500,
          "acceptance_ref": 500, "files_scope_item": 500, "depends_on_item": 50}


def emitir_para_sync(epicas):
    """Imprime `{"epics":[…]}` en el formato del contrato; rc 2 si algo no lo cumple."""
    errores = []
    if not epicas:
        errores.append("el bundle no tiene ni una épica: no hay nada que proponer")
    if len(epicas) > MAX_EPICAS:
        errores.append("%d épicas: el contrato admite %d como máximo"
                       % (len(epicas), MAX_EPICAS))
    salida = []
    for code in sorted(epicas):
        e = epicas[code]
        if len(code) > LARGOS["code"]:
            errores.append("%s: el `code` excede %d caracteres" % (code, LARGOS["code"]))
        if not e.get("title"):
            errores.append("%s: sin `title` (el contrato lo exige no vacío)" % code)
        elif len(e["title"]) > LARGOS["title"]:
            errores.append("%s: el `title` excede %d caracteres" % (code, LARGOS["title"]))
        if e.get("layer") not in VALID_LAYERS:
            errores.append("%s: `layer` es %r y el contrato exige FOUNDATIONAL o BUSINESS "
                           "(declárala en los docs de discovery)" % (code, e.get("layer")))
        fs = e.get("files_scope") or []
        if len(fs) > MAX_FILES_SCOPE:
            errores.append("%s: %d entradas en `files_scope` y el contrato admite %d"
                           % (code, len(fs), MAX_FILES_SCOPE))
        for x in fs:
            if not x or len(x) > LARGOS["files_scope_item"]:
                errores.append("%s: una entrada de `files_scope` está vacía o excede %d "
                               "caracteres" % (code, LARGOS["files_scope_item"]))
                break
        deps = e.get("depends_on") or []
        if len(deps) > MAX_DEPENDS_ON:
            errores.append("%s: %d entradas en `depends_on` y el contrato admite %d"
                           % (code, len(deps), MAX_DEPENDS_ON))
        for x in deps:
            if not x or len(x) > LARGOS["depends_on_item"]:
                errores.append("%s: una entrada de `depends_on` está vacía o excede %d "
                               "caracteres" % (code, LARGOS["depends_on_item"]))
                break
        historias = e.get("stories") or []
        if len(historias) > MAX_HISTORIAS:
            errores.append("%s: %d historias y el contrato admite %d por épica"
                           % (code, len(historias), MAX_HISTORIAS))
        hs = []
        for h in historias:
            hcode = h.get("code") or ""
            if not hcode or len(hcode) > LARGOS["code"]:
                errores.append("%s: una historia no tiene `code` o excede %d caracteres"
                               % (code, LARGOS["code"]))
                continue
            htitle = h.get("title") or ""
            if not htitle:
                errores.append("%s: la historia %s no tiene `title`" % (code, hcode))
                continue
            historia = {"code": hcode, "title": htitle[:LARGOS["title"]]}
            # `acceptance_ref` opcional (contrato del hub, ≤500): trunca sin error, igual que
            # `release_line`/`docs_ref` de la épica. Omitirlo deja la columna «Criterios —».
            if h.get("acceptance_ref"):
                historia["acceptance_ref"] = h["acceptance_ref"][:LARGOS["acceptance_ref"]]
            hs.append(historia)
        proyectada = {"code": code, "title": (e.get("title") or "")[:LARGOS["title"]],
                      "layer": e.get("layer"),
                      "files_scope": fs, "depends_on": deps, "stories": hs}
        # Opcionales: solo viajan si tienen valor. `null` es legal en el contrato, pero omitirlos
        # deja más corto el delta que el humano revisa en la consola.
        if e.get("release_line"):
            proyectada["release_line"] = e["release_line"][:LARGOS["release_line"]]
        if isinstance(e.get("priority"), int):
            proyectada["priority"] = e["priority"]
        if e.get("docs_ref"):
            proyectada["docs_ref"] = e["docs_ref"][:LARGOS["docs_ref"]]
        salida.append(proyectada)
    if errores:
        print("graph-bundle --for-sync: el bundle NO cumple el contrato del hub "
              "(no se envía nada):", file=sys.stderr)
        for x in errores:
            print("  ⛔ %s" % x, file=sys.stderr)
        return 2
    json.dump({"epics": salida}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def main():
    avisos = []
    opciones, error = parsear_argumentos(sys.argv[1:])
    if error:
        print("graph-bundle: %s" % error, file=sys.stderr)
        return 1

    # `--print-deps`: solo el grafo extraído (diagnóstico; no toca stdin ni arma bundle).
    if opciones["print_deps"]:
        try:
            deps, _, avisos_docs = leer_dependencias_de_docs(opciones["print_deps"])
        except (IOError, OSError) as e:
            print("graph-bundle: no se pudo leer %s: %s" % (opciones["print_deps"], e),
                  file=sys.stderr)
            return 1
        json.dump(deps, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        for a in avisos_docs:
            print("aviso: %s" % a, file=sys.stderr)
        return 0

    deps_docs = None
    if opciones["from_docs"]:
        try:
            deps_docs, secciones_docs, avisos_docs = \
                leer_dependencias_de_docs(opciones["from_docs"])
        except (IOError, OSError) as e:
            print("graph-bundle: no se pudo leer %s: %s" % (opciones["from_docs"], e),
                  file=sys.stderr)
            return 1
        avisos.extend(avisos_docs)

    try:
        raw = json.load(sys.stdin)
    except Exception as e:
        print("graph-bundle: entrada ilegible (se esperaba JSON por stdin): %s" % e,
              file=sys.stderr)
        return 1
    if not isinstance(raw, dict):
        print("graph-bundle: la entrada debe ser un objeto JSON", file=sys.stderr)
        return 1

    epicas = {}
    for e in raw.get("epics") or []:
        if not isinstance(e, dict):
            continue
        code = e.get("code")
        if not isinstance(code, str) or not code:
            avisos.append("épica sin `code`: descartada")
            continue
        if code in epicas:
            avisos.append("código duplicado %s: se conserva la PRIMERA aparición" % code)
            continue
        # `title` es obligatorio en el hub (EpicIn, min_length=1): cae al código.
        titulo = e.get("title")
        if not isinstance(titulo, str) or not titulo:
            avisos.append("%s sin `title`: se usa el código (el hub lo exige)" % code)
            titulo = code
        # `layer` viaja en MAYÚSCULA; ausente o inválido, el import del hub
        # rechaza el grafo ENTERO (GraphIntegrityError) — se avisa, no se inventa.
        layer = e.get("layer")
        if isinstance(layer, str) and layer:
            layer = layer.upper()
            if layer not in VALID_LAYERS:
                avisos.append("%s con layer %r fuera de FOUNDATIONAL|BUSINESS: "
                              "el hub rechazará el grafo entero" % (code, e.get("layer")))
        else:
            layer = None
            avisos.append("%s sin `layer`: el hub rechazará el grafo entero "
                          "(FOUNDATIONAL|BUSINESS)" % code)
        historias = []
        for h in e.get("stories") or []:
            if not isinstance(h, dict):
                continue
            # El hub hace `story_in["code"]`; la entrada de discovery trae `id`.
            hcode = h.get("code") if isinstance(h.get("code"), str) else h.get("id")
            if not isinstance(hcode, str) or not hcode:
                continue
            htitle = h.get("title")
            if not isinstance(htitle, str) or not htitle:
                avisos.append("%s: historia %s sin `title`: se usa el código" % (code, hcode))
                htitle = hcode
            historia = {"code": hcode, "title": htitle}
            # `acceptance_ref` referencia los AC en git (contrato del hub, ≤500): viaja si
            # viene bien tipado. Sin él la ficha de la épica muestra «Criterios —» aunque la
            # HU tenga sus AC en G/W/T, y el delta del re-sync no lo detecta (nunca cambia).
            if isinstance(h.get("acceptance_ref"), str) and h.get("acceptance_ref"):
                historia["acceptance_ref"] = h["acceptance_ref"]
            historias.append(historia)
        epica = {
            "code": code,
            "title": titulo,
            "layer": layer,
            "files_scope": sorted(norm_list(e.get("files_scope"))),
            "depends_on": sorted(norm_list(e.get("depends_on"))),
            "release_line": e.get("release_line")
                            if isinstance(e.get("release_line"), str) else None,
            "stories": sorted(historias, key=lambda h: h["code"]),
        }
        # Opcionales del contrato del hub: pasan tal cual si vienen bien tipados.
        if isinstance(e.get("priority"), int):
            epica["priority"] = e["priority"]
        if isinstance(e.get("docs_ref"), str):
            epica["docs_ref"] = e["docs_ref"]
        epicas[code] = epica

    # [issue #56] Las dependencias de los docs se UNEN a las declaradas: el extractor es la
    # fuente fiable, y lo que ya venía en el JSON no se pierde (se avisa si no está en docs).
    if deps_docs is not None:
        aristas = 0
        for code, e in epicas.items():
            if code not in deps_docs:
                if code in secciones_docs:
                    avisos.append("%s tiene sección en %s pero no declara el campo "
                                  "`Depende de`: sus dependencias quedan como vinieran en el "
                                  "JSON" % (code, opciones["from_docs"]))
                else:
                    avisos.append("%s no aparece como sección de épica en %s: sus "
                                  "dependencias no se pudieron extraer de los docs"
                                  % (code, opciones["from_docs"]))
                continue
            solo_json = [d for d in e["depends_on"] if d not in deps_docs[code]]
            if solo_json:
                avisos.append("%s: %s viene del JSON de entrada pero no del campo `Depende de` "
                              "de los docs: verifica cuál manda"
                              % (code, ", ".join(solo_json)))
            e["depends_on"] = sorted(set(e["depends_on"]) | set(deps_docs[code]))
            aristas += len(e["depends_on"])
        for code in sorted(deps_docs):
            if code not in epicas:
                avisos.append("%s está en %s pero no en el JSON de entrada: el grafo del hub "
                              "quedaría sin esa épica" % (code, opciones["from_docs"]))
        print("info: dependencias extraídas de %s -> %d épicas con campo `Depende de`, "
              "%d aristas en el grafo" % (opciones["from_docs"], len(deps_docs), aristas),
              file=sys.stderr)

    for code, e in epicas.items():
        for dep in e["depends_on"]:
            if dep not in epicas:
                avisos.append("%s depende de %s, que no está en el grafo" % (code, dep))

    # Ciclos: DFS iterativa (nada de recursión: un grafo hostil no debe reventar la pila).
    estado = {}
    for raiz in sorted(epicas):
        if estado.get(raiz):
            continue
        pila = [(raiz, iter(epicas[raiz]["depends_on"]))]
        estado[raiz] = 1
        while pila:
            nodo, it = pila[-1]
            avanzo = False
            for dep in it:
                if dep not in epicas:
                    continue
                if estado.get(dep) == 1:
                    avisos.append("ciclo de dependencias detectado: %s → %s" % (nodo, dep))
                    continue
                if not estado.get(dep):
                    estado[dep] = 1
                    pila.append((dep, iter(epicas[dep]["depends_on"])))
                    avanzo = True
                    break
            if not avanzo:
                estado[nodo] = 2
                pila.pop()

    # Las `release_lines` de la entrada se PLIEGAN al `release_line` (string) por
    # épica que el hub persiste — gana la primera asignación (orden estable por id).
    lineas = [r for r in (raw.get("release_lines") or [])
              if isinstance(r, dict) and isinstance(r.get("id"), str)]
    lineas.sort(key=lambda r: r["id"])
    for r in lineas:
        for c in norm_list(r.get("epics")):
            if c not in epicas:
                avisos.append("la línea %s referencia %s, que no está en el grafo" % (r["id"], c))
                continue
            if epicas[c]["release_line"] is None:
                epicas[c]["release_line"] = r["id"]
            elif epicas[c]["release_line"] != r["id"]:
                avisos.append("%s ya está en la línea %s: se ignora %s "
                              "(el hub guarda UNA línea por épica)"
                              % (c, epicas[c]["release_line"], r["id"]))

    # [EP-OR-17] El carril de sync se lleva la proyección de contrato y NADA más: los avisos
    # siguen saliendo por stderr (arriba se han ido acumulando), pero el `warnings` del bundle
    # de preparación no existe en `GraphSyncBundle` y viajaría como un 422.
    if opciones["for_sync"]:
        for a in avisos:
            print("aviso: %s" % a, file=sys.stderr)
        return emitir_para_sync(epicas)

    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "kind": "graph",
        "project_ref": raw.get("project_ref"),
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "trycore-build-harness/graph-bundle.py",
        "depends_on_source": ("docs:%s" % opciones["from_docs"]) if deps_docs is not None
                             else "input",
        "epics": [epicas[c] for c in sorted(epicas)],
        "warnings": avisos,
    }
    json.dump(bundle, sys.stdout, indent=2, ensure_ascii=False, sort_keys=False)
    sys.stdout.write("\n")
    for a in avisos:
        print("aviso: %s" % a, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
