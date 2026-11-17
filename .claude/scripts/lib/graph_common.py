"""graph_common.py — extractor DETERMINISTA de dependencias del grafo de épicas.

Núcleo compartido por `graph-bundle.py` (prepara el bundle de grafo para el hub) y
`graph-check.py` (valida la granularidad del grafo, issue #86). Vive aquí, y no dentro de
`graph-bundle.py`, porque el guion de ese nombre lo hace NO importable; ambos consumidores
están co-ubicados en `scripts/lib/` (y en `.claude/scripts/lib/` del consumidor), así que
`import graph_common` resuelve en los dos canales de distribución.

[issue #56] Las dependencias entre épicas viven como PROSA en `docs/03-backlog/epicas.md`
(`**Depende de**: EP-001 (…)`); delegar su lectura al modelo las dejó VACÍAS en el piloto.
`extraer_dependencias` las saca de forma determinista —regex de códigos `EP-…` sobre el campo
`Depende de` de cada sección de épica, excluyendo la propia—. Si la épica declara el campo
estructurado `depende_de: [EP-001, …]`, ese gana sobre la prosa.
"""
import glob
import os
import re

# Códigos de épica: EP-001 y también los compuestos del estilo EP-OR-08.
RE_CODIGO = re.compile(r"\bEP-(?:[A-Za-z]{1,6}-)?\d{1,4}\b")
# Encabezado de sección de épica: `## EP-001 — Título` (cualquier nivel).
RE_ENCABEZADO = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
# El campo en prosa que escribe la metodología: `**Depende de**: …` (puede ir a mitad de
# línea, p. ej. `**Anexo A**: Fase 3 · **Depende de**: EP-002`).
RE_DEPENDE_DE = re.compile(r"depende\s+de", re.IGNORECASE)
# El campo estructurado (frontmatter o cuerpo): `depende_de: [EP-001, EP-002]`.
RE_DEPENDE_DE_ESTRUCTURADO = re.compile(r"^\s*(?:-\s*)?depende_de\s*:", re.IGNORECASE)
# Fin del párrafo del campo: encabezado, regla horizontal, viñeta/cita/tabla o campo nuevo.
RE_FIN_DE_CAMPO = re.compile(r"^\s*(?:#{1,6}\s|-{3,}\s*$|\*{3,}\s*$|[-*+>|]\s|\*\*)")


def extraer_dependencias(texto):
    """Devuelve ({codigo: [deps ordenadas]}, {códigos con sección}, avisos).

    Solo entran las épicas que DECLARAN el campo (en prosa o estructurado): "no lo declara"
    y "declara que no depende de nada" son cosas distintas y ninguna se inventa aquí.
    """
    avisos = []
    lineas = texto.splitlines()
    # (código de la épica, línea donde abre su sección)
    secciones = []
    for i, linea in enumerate(lineas):
        m = RE_ENCABEZADO.match(linea)
        if not m:
            continue
        codigos = RE_CODIGO.findall(m.group(2))
        if codigos:
            secciones.append((codigos[0], i))
    if not secciones:
        avisos.append("no se reconoció ninguna sección de épica en los docs "
                      "(se esperaban encabezados del estilo `## EP-001 — Título`)")
        return {}, set(), avisos

    deps = {}
    for n, (codigo, inicio) in enumerate(secciones):
        fin = secciones[n + 1][1] if n + 1 < len(secciones) else len(lineas)
        cuerpo = lineas[inicio + 1:fin]
        prosa, estructurado = None, None
        for j, linea in enumerate(cuerpo):
            if estructurado is None and RE_DEPENDE_DE_ESTRUCTURADO.match(linea):
                estructurado = RE_CODIGO.findall(linea.split(":", 1)[1])
                continue
            if prosa is not None:
                continue
            m = RE_DEPENDE_DE.search(linea)
            if not m:
                continue
            # El campo puede continuar en las líneas siguientes hasta el fin del párrafo.
            trozos = [linea[m.end():]]
            for siguiente in cuerpo[j + 1:]:
                if not siguiente.strip() or RE_FIN_DE_CAMPO.match(siguiente):
                    break
                trozos.append(siguiente)
            prosa = RE_CODIGO.findall(" ".join(trozos))
        # El campo estructurado es determinista: gana sobre la heurística de la prosa.
        encontrado = estructurado if estructurado is not None else prosa
        if encontrado is None:
            continue
        deps[codigo] = sorted({c for c in encontrado if c != codigo})
    return deps, {c for c, _ in secciones}, avisos


def leer_dependencias_de_docs(ruta):
    """Lee el fichero de épicas; lanza IOError/OSError si no se puede (rc 1 arriba)."""
    with open(ruta, encoding="utf-8") as fh:
        return extraer_dependencias(fh.read())


def secciones_cuerpo(texto):
    """Devuelve {codigo: cuerpo} — el texto de cada sección de épica (sin su encabezado).

    Mismo troceo determinista que `extraer_dependencias` (encabezado con un código `EP-…`),
    pero devuelve el cuerpo completo para que un consumidor lea campos por sección (layer,
    files_scope, tramos, linea_release). Si un código abre dos secciones, gana la primera.
    """
    lineas = texto.splitlines()
    secciones = []
    for i, linea in enumerate(lineas):
        m = RE_ENCABEZADO.match(linea)
        if not m:
            continue
        codigos = RE_CODIGO.findall(m.group(2))
        if codigos:
            secciones.append((codigos[0], i))
    cuerpos = {}
    for n, (codigo, inicio) in enumerate(secciones):
        fin = secciones[n + 1][1] if n + 1 < len(secciones) else len(lineas)
        if codigo not in cuerpos:
            cuerpos[codigo] = "\n".join(lineas[inicio + 1:fin])
    return cuerpos


# ── Modelo del grafo de épicas (issue #86) ────────────────────────────────────────────────
# Compartido por graph-check.py (validación) y graph-propose.py (optimización). Construye, desde
# los docs de discovery, el grafo de épicas con sus HU, capas, dependencias duras/blandas,
# líneas de release y tramos — todo determinista y sin dependencias de terceros.

# Código de HU: HU-001 y compuestos (HU-OR-01), como el de épica.
RE_HU = re.compile(r"\bHU-(?:[A-Za-z]{1,6}-)?\d{1,4}\b")
# AC en Given/When/Then (inglés) o Dado/Cuando/Entonces (español): se exige abrir y cerrar.
RE_AC_ABRE = re.compile(r"\b(given|dado|dada)\b", re.IGNORECASE)
RE_AC_CIERRA = re.compile(r"\b(then|entonces)\b", re.IGNORECASE)
DEFAULT_CAP = 6
MAX_TRAMOS = 2


def frontmatter(texto):
    """Devuelve el frontmatter YAML (entre los dos `---` iniciales) como dict simple:
    escalares a str, listas a [str]. Sin PyYAML (los scripts del arnés son sin dependencias).
    Si no hay frontmatter, devuelve {}."""
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        return {}
    fm = {}
    clave = None
    for linea in lineas[1:]:
        if linea.strip() == "---":
            break
        m = re.match(r"^\s*-\s+(.*)$", linea)
        if m and isinstance(fm.get(clave), list):
            fm[clave].append(m.group(1).strip().strip("\"'"))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", linea)
        if not m:
            continue
        clave, val = m.group(1), m.group(2).strip()
        if val == "":
            fm[clave] = []  # puede seguir una lista en bloque `- item`
        elif val.startswith("["):
            fm[clave] = [x.strip().strip("\"'") for x in val.strip("[]").split(",") if x.strip()]
        else:
            fm[clave] = val.strip("\"'")
    return fm


def campo_escalar(cuerpo, *nombres):
    """Lee `nombre: valor` o `**Nombre**: valor` del cuerpo de una sección markdown."""
    for nombre in nombres:
        m = re.search(r"(?im)^\s*(?:\*\*\s*%s\s*\*\*|%s)\s*:\s*(.+?)\s*$"
                      % (re.escape(nombre), re.escape(nombre)), cuerpo)
        if m:
            return m.group(1).strip().strip("\"'`")
    return None


def campo_lista(cuerpo, *nombres):
    """Lee una lista inline `nombre: [a, b]` o un valor único del cuerpo de la sección."""
    val = campo_escalar(cuerpo, *nombres)
    if not val:
        return []
    if val.startswith("["):
        return [x.strip().strip("\"'`") for x in val.strip("[]").split(",") if x.strip()]
    return [val]


def normalizar_capa(val):
    if not val:
        return None
    v = val.strip().lower()
    if v in ("foundational", "fundacional"):
        return "foundational"
    if v in ("business", "negocio", "technical", "tecnica", "técnica"):
        return "business"
    return v


def entero(val):
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return None


def clave_de_linea(linea_id):
    """Índice de orden de una línea de release: el primer entero de su id (`R2-mvp` → 2)."""
    m = re.search(r"\d+", linea_id or "")
    return int(m.group(0)) if m else None


def cargar_hus(dir_historias):
    """Devuelve {hu: {epica, has_ac, complejidad, estado, duras:[hu], blandas:[hu]}} leyendo las
    HU-*.md (recursivo). `complejidad`/`estado` alimentan el modelo de coste y la separación
    draft/lista de --propose; graph-check los ignora."""
    hus = {}
    patrones = [os.path.join(dir_historias, "HU-*.md"),
                os.path.join(dir_historias, "**", "HU-*.md")]
    rutas = sorted({r for p in patrones for r in glob.glob(p, recursive=True)})
    for ruta in rutas:
        try:
            with open(ruta, encoding="utf-8") as fh:
                texto = fh.read()
        except (IOError, OSError):
            continue
        fm = frontmatter(texto)
        idval = fm.get("id") if isinstance(fm.get("id"), str) else ""
        mcode = RE_HU.search(idval) or RE_HU.search(os.path.basename(ruta))
        if not mcode:
            continue
        hcode = mcode.group(0)
        epica = fm.get("epica") if isinstance(fm.get("epica"), str) else None
        mep = RE_CODIGO.search(epica or "")
        epica = mep.group(0) if mep else None
        duras = [c for v in (fm.get("depende_de_duras") or []) for c in RE_HU.findall(str(v))]
        blandas = [c for v in (fm.get("depende_de_blandas") or []) for c in RE_HU.findall(str(v))]
        comp = fm.get("complejidad") if isinstance(fm.get("complejidad"), str) else None
        estado = fm.get("estado") if isinstance(fm.get("estado"), str) else None
        hus[hcode] = {
            "epica": epica,
            "has_ac": bool(RE_AC_ABRE.search(texto) and RE_AC_CIERRA.search(texto)),
            "complejidad": (comp or "").strip().lower() or None,
            "estado": (estado or "").strip().lower() or None,
            "duras": duras,
            "blandas": blandas,
        }
    return hus


def construir_modelo(ruta_epicas, dir_historias):
    """Construye el grafo de épicas. Lanza IOError/OSError si `epicas.md` no se puede leer.

    Devuelve (epicas, procedencia, avisos_docs) donde:
      epicas[code] = {hus, hus_con_ac, layer, tramos, linea_release, files_scope,
                      declaradas:set, derivadas:set}
      procedencia[(epica, dep)] = [(hu_origen, hu_destino), …]  (para nombrar ciclos/derivas)
    """
    with open(ruta_epicas, encoding="utf-8") as fh:
        texto_epicas = fh.read()
    declaradas, secciones, avisos_docs = extraer_dependencias(texto_epicas)
    cuerpos = secciones_cuerpo(texto_epicas)
    hus = cargar_hus(dir_historias)

    codigos = set(secciones) | set(cuerpos) | {h["epica"] for h in hus.values() if h["epica"]}
    epicas = {}
    for code in codigos:
        cuerpo = cuerpos.get(code, "")
        propias = [h for h, v in hus.items() if v["epica"] == code]
        epicas[code] = {
            "hus": sorted(propias),
            "hus_con_ac": sorted([h for h in propias if hus[h]["has_ac"]]),
            "layer": normalizar_capa(campo_escalar(cuerpo, "layer", "capa", "Capa")),
            "tramos": entero(campo_escalar(cuerpo, "tramos", "Tramos")),
            "linea_release": campo_escalar(cuerpo, "linea_release", "release_line",
                                           "linea", "línea", "Línea"),
            "files_scope": campo_lista(cuerpo, "files_scope", "Files scope"),
            "declaradas": {d for d in declaradas.get(code, [])},
            "derivadas": set(),
            "blandas": set(),
        }

    # Deps DERIVADAS (duras) con procedencia, y las BLANDAS (P6) entre épicas, desde las HU.
    procedencia = {}
    for hcode, hv in hus.items():
        epica = hv["epica"]
        if not epica or epica not in epicas:
            continue
        for destino in hv["duras"]:
            dueno = hus.get(destino, {}).get("epica")
            if dueno and dueno in epicas and dueno != epica:
                epicas[epica]["derivadas"].add(dueno)
                procedencia.setdefault((epica, dueno), []).append((hcode, destino))
        for destino in hv["blandas"]:
            dueno = hus.get(destino, {}).get("epica")
            if dueno and dueno in epicas and dueno != epica:
                epicas[epica]["blandas"].add(dueno)

    return epicas, procedencia, avisos_docs


def grafo_efectivo(epicas):
    """Arcos efectivos = declarados ∪ derivados (más conservador: un ciclo que ninguno tiene
    por separado pero sí juntos es una contradicción real que vale bloquear)."""
    return {code: {d for d in (e["declaradas"] | e["derivadas"]) if d in epicas}
            for code, e in epicas.items()}


def detectar_ciclos(g):
    """DFS iterativa (sin recursión). Devuelve una lista de ciclos (cada uno, lista de códigos
    en orden de camino de retorno), deduplicados por el conjunto de nodos."""
    ciclos, firmas = [], set()
    estado = {}  # ausente/0=blanco, 1=en pila, 2=cerrado
    for raiz in sorted(g):
        if estado.get(raiz):
            continue
        pila = [(raiz, iter(sorted(g[raiz])))]
        camino = [raiz]
        estado[raiz] = 1
        while pila:
            nodo, it = pila[-1]
            avanzo = False
            for dep in it:
                if dep not in g:
                    continue
                if estado.get(dep) == 1:
                    ciclo = camino[camino.index(dep):]
                    firma = frozenset(ciclo)
                    if firma not in firmas:
                        firmas.add(firma)
                        ciclos.append(ciclo)
                    continue
                if not estado.get(dep):
                    estado[dep] = 1
                    pila.append((dep, iter(sorted(g[dep]))))
                    camino.append(dep)
                    avanzo = True
                    break
            if not avanzo:
                estado[nodo] = 2
                pila.pop()
                camino.pop()
    return ciclos


def nombrar_arista(a, b, procedencia):
    """Describe la arista a→b: con el par de HU que la derivó, o `(declarado)` si vino del
    campo `Depende de` de la sección."""
    pares = procedencia.get((a, b))
    if pares:
        return ", ".join("%s depende_de_duras %s" % (x, y) for x, y in pares[:3])
    return "declarado en epicas.md"


def prefijo_glob(glob_str):
    return glob_str.split("*", 1)[0].rstrip("/")


def files_scope_solapan(ea, eb):
    for a in ea["files_scope"]:
        for b in eb["files_scope"]:
            pa, pb = prefijo_glob(a), prefijo_glob(b)
            if pa and pb and (pa.startswith(pb) or pb.startswith(pa)):
                return True
    return False


def alcanzable(g, origen, destino):
    vistos, cola = {origen}, [origen]
    while cola:
        for d in g.get(cola.pop(), ()):
            if d == destino:
                return True
            if d not in vistos:
                vistos.add(d)
                cola.append(d)
    return False
