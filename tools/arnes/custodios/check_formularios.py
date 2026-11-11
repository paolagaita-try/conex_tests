"""Custodio de formularios: los formularios Svelte generados cuadran con la matriz y no rompen las reglas de lectura.

Contra `docs/07-bonita/matriz-formularios.md` (lector de la matriz y nombres de `escribir/aplicaciones.py`, la única
fuente de nombres), por cada formulario Svelte:

- tiene su carpeta `frontend/src/forms/<token>/` con `generado/contrato.ts` y `generado/esquema.ts`;
- tiene su entrada `tipo: negocio` en `frontend/forms.manifest.json` (y no sobra ninguna);
- es página (`token` + `customPage`) del descriptor de su aplicación `app/applications/<app>.xml`;
- algún `formMapping`/`overviewFormMapping` de los `.proc` apunta a su URL; y ningún mapping a una página de una
  aplicación del proyecto apunta a un formulario que la matriz no tiene (un External URL a otro sitio no cuenta).

Páginas propias y temas (0.12.1, `docs/plan-5/contrato-de-formato.md` §2.20):

- cada página propia tiene su carpeta con su esqueleto (`index.html`), su entrada `tipo: pagina` en el manifiesto y
  está en el descriptor de cada aplicación suya; cada tema propio tiene `tema.css`, su entrada `tipo: tema` y es el
  `theme` del descriptor de sus aplicaciones;
- cada menú de un descriptor apunta a una página de ese descriptor;
- no sobra ninguna entrada `pagina` o `tema` que la matriz no declare.

Reglas de lectura, sobre `frontend/src/forms/**` SIN `generado/` (el esqueleto editable, pruebas incluidas):

- no aparece la API de datos de negocio (`API/bdm` sin distinguir mayúsculas, `/bdm/businessData...`, `${...}/bdm`; los datos del caso se leen por la extensión de consultas, `$lib/bonita/caso`);
- no aparece `processParameter` (los parámetros se leen del módulo, `$lib/parametros`, vía
  `extension/parametros/valores`; las lecturas permitidas son esa y `extension/consultas/*`);
- ningún campo con `catalogo` (columna «Catálogo» de la matriz) trae sus opciones como lista literal.

Heurística de la última regla (textual, sin analizar TypeScript): del campo con catálogo se toma su ruta de contrato
(`decisionInput.resultado`) y se busca, en cada fichero del formulario que no sea una prueba (`*.test.ts`), esa ruta entre
comillas (a) como clave de un array literal (`'ruta': [` o `'ruta']: [`) o (b) seguida, dentro de los 300 caracteres
siguientes, de `opciones: [`/`opciones = [`. Límites: una lista literal construida sin nombrar la ruta (p. ej. por un
alias o un fichero compartido), o más lejos de 300 caracteres de ella, no se detecta; y un `opciones: [` cercano a la
ruta por otra razón (p. ej. un campo vecino sin catálogo) da un falso positivo, que se arregla separándolos. Los
comentarios se ignoran antes de buscar `/API/bdm` y `processParameter`, para que explicarlos no sea una infracción.

Un proyecto sin documentación de Bonita (unidad 0) sale verde; sin matriz pero con documentación, no se puede
verificar (código 2), como el resto de custodios.

En modo existente solo se vigila lo que genera el arnés: los form mappings de los procesos nuevos (no los de los pools
de la línea base, en ninguna versión) y, si el proyecto no tiene el frontend de la plantilla, el manifiesto solo se
exige cuando la matriz pide formularios Svelte (sin ellos, lo nuevo es «No form» o «External URL»). Las aplicaciones
propias del proyecto en `app/applications/` y sus páginas son del proyecto.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from custodios import NoVerificable, docs_de_procesos_nuevos, ejecutar, pools_existentes, ruta_doc
from generadores.escribir.aplicaciones import (mapeo, paginas, paginas_propias, recurso_pagina, temas, token_pagina,
                                              url_pagina)
from generadores.existente.linea_base import modo_existente
from generadores.leer.matriz import F as FMATRIZ, leer_matriz

FORMS = Path("frontend") / "src" / "forms"
MANIFIESTO = Path("frontend") / "forms.manifest.json"
APLICACIONES = Path("bonita-project") / "app" / "applications"
DIAGRAMAS = Path("bonita-project") / "app" / "diagrams"
GENERADOS = ("contrato.ts", "esquema.ts")
PORTAL = re.compile(r"^/bonita/portal/resource/app/([^/]+)/([^/]+)/content/?$")
_API_BDM = re.compile(r"API/bdm|(?<![\w])/bdm/(?:businessData|businessDataReference)\b|\$\{[^}]*\}/bdm", re.I)
_VENTANA = 300
_TIPO = "{http://www.omg.org/XMI}type"


def _parsear(ruta: Path) -> ET.Element:
    try:
        return ET.parse(ruta).getroot()
    except ET.ParseError as e:
        raise NoVerificable(f"{ruta.name}: XML mal formado ({e})") from e


def _matriz(proyecto: Path) -> dict:
    errores: list[str] = []
    try:
        datos = json.loads((proyecto / ".trycore-bonita.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        datos = {}
    m = leer_matriz(ruta_doc(proyecto, f"07-bonita/{FMATRIZ}").read_text(encoding="utf-8"), errores,
                    datos.get("nombre") or "")
    if errores:
        raise ValueError(f"{FMATRIZ}: " + "; ".join(errores))
    return m


def _carpetas_y_manifiesto(proyecto: Path, svelte: list[dict]) -> list[str]:
    hallazgos = []
    ruta = proyecto / MANIFIESTO
    if not svelte and not ruta.exists() and modo_existente(proyecto):
        return []  # modo existente sin el frontend de la plantilla ni formularios Svelte que lo pidan
    try:
        negocio = {e["id"] for e in json.loads(ruta.read_text(encoding="utf-8")).get("formularios", [])
                   if e.get("tipo") == "negocio"}
    except (OSError, ValueError):
        negocio = None
        hallazgos.append(f"{MANIFIESTO.as_posix()}: no existe o no es JSON válido")
    esperados = set()
    for f in svelte:
        token = token_pagina(f["id"])
        esperados.add(token)
        carpeta = proyecto / FORMS / token
        if not carpeta.is_dir():
            hallazgos.append(f"{f['id']}: falta la carpeta {(FORMS / token).as_posix()}")
        else:
            for g in GENERADOS:
                if not (carpeta / "generado" / g).is_file():
                    hallazgos.append(f"{f['id']}: falta {(FORMS / token / 'generado' / g).as_posix()}")
        if negocio is not None and token not in negocio:
            hallazgos.append(f"{f['id']}: falta su entrada «{token}» (tipo negocio) en {MANIFIESTO.as_posix()}")
    for sobra in sorted((negocio or set()) - esperados):
        hallazgos.append(f"{MANIFIESTO.as_posix()}: la entrada de negocio «{sobra}» no corresponde a ningún "
                         f"formulario Svelte de {FMATRIZ}")
    return hallazgos


def _aplicaciones(proyecto: Path, matriz: dict) -> list[str]:
    hallazgos = []
    try:
        por_app = paginas(matriz)
    except ValueError as e:
        return [str(e)]
    propias = paginas_propias(matriz)
    apps = {a["token"]: a for a in matriz.get("aplicaciones", [])}
    for token in dict.fromkeys([*por_app, *propias]):
        forms, suyas = por_app.get(token, []), propias.get(token, [])
        if not forms and not suyas:
            continue
        ruta = proyecto / APLICACIONES / f"{token}.xml"
        if not ruta.is_file():
            hallazgos.append(f"falta el descriptor {(APLICACIONES / (token + '.xml')).as_posix()} de la aplicación "
                             f"«{token}»")
            continue
        raiz = _parsear(ruta)
        tiene = {(p.get("token"), p.get("customPage")) for p in raiz.iter() if p.tag.endswith("applicationPage")}
        for f in forms:
            if (token_pagina(f["id"]), recurso_pagina(f["id"])) not in tiene:
                hallazgos.append(f"{f['id']}: la aplicación «{token}» no tiene la página «{token_pagina(f['id'])}» "
                                 f"({recurso_pagina(f['id'])})")
        for p in suyas:
            if (p["token"], p["recurso"]) not in tiene:
                hallazgos.append(f"{p['token']}: la aplicación «{token}» no tiene la página «{p['token']}» "
                                 f"({p['recurso']}), página propia «{p['alias']}» de {FMATRIZ}")
        tema = (apps.get(token) or {}).get("tema")
        app_xml = next((e for e in raiz.iter() if e.tag.endswith("}application") or e.tag == "application"), None)
        if tema and app_xml is not None and app_xml.get("theme") != tema:
            hallazgos.append(f"{tema}: el descriptor de la aplicación «{token}» tiene theme=«{app_xml.get('theme')}» "
                             f"y la matriz declara el tema propio «{tema}»")
        tokens = {tok for tok, _ in tiene}
        for m in (e for e in raiz.iter() if e.tag.endswith("applicationMenu")):
            nombre = next((d.text for d in m if d.tag.endswith("displayName")), None) or "?"
            if m.get("applicationPage") not in tokens:
                hallazgos.append(f"el menú «{nombre}» de la aplicación «{token}» apunta a la página "
                                 f"«{m.get('applicationPage')}», que no está en su descriptor")
    return hallazgos


def _paginas_y_temas(proyecto: Path, matriz: dict) -> list[str]:
    """Esqueleto y entrada del manifiesto de cada página propia y de cada tema; ninguna entrada que sobre."""
    hallazgos = []
    try:
        entradas = json.loads((proyecto / MANIFIESTO).read_text(encoding="utf-8")).get("formularios", [])
    except (OSError, ValueError):
        entradas = None  # ya lo dice `_carpetas_y_manifiesto`
    declaradas = {tipo: {e["id"] for e in entradas or [] if e.get("tipo") == tipo} for tipo in ("pagina", "tema")}
    esperadas: dict[str, dict[str, str]] = {"pagina": {}, "tema": {}}
    for p in matriz.get("paginas", []):
        esperadas["pagina"][p["token"]] = "index.html"
    for tema in temas(matriz):
        esperadas["tema"][tema.removeprefix("custompage_")] = "tema.css"
    for tipo, porid in esperadas.items():
        for id_, fichero in porid.items():
            carpeta = proyecto / FORMS / id_
            if not carpeta.is_dir():
                hallazgos.append(f"{id_}: falta la carpeta {(FORMS / id_).as_posix()} ({tipo} de {FMATRIZ}; "
                                 f"`tools/arnes.sh generar` escribe su esqueleto)")
            elif not (carpeta / fichero).is_file():
                hallazgos.append(f"{id_}: falta {(FORMS / id_ / fichero).as_posix()} ({tipo} de {FMATRIZ})")
            if entradas is not None and id_ not in declaradas[tipo]:
                hallazgos.append(f"{id_}: falta su entrada «{id_}» (tipo {tipo}) en {MANIFIESTO.as_posix()}")
        for sobra in sorted(declaradas[tipo] - porid.keys()):
            hallazgos.append(f"{MANIFIESTO.as_posix()}: la entrada «{sobra}» (tipo {tipo}) no la declara la sección "
                             f"«Aplicación» de {FMATRIZ}")
    return hallazgos


def _mappings(proyecto: Path, matriz: dict) -> list[str]:
    hallazgos = []
    urls: set[str] = set()
    existentes = pools_existentes(proyecto)  # modo existente: sus form mappings son del proyecto
    for f in sorted((proyecto / DIAGRAMAS).glob("*.proc")):
        for pool in _parsear(f).iter("elements"):
            if pool.get(_TIPO) != "process:Pool" or pool.get("name") in existentes:
                continue
            for e in pool.iter():
                if e.tag in ("formMapping", "overviewFormMapping") and e.get("url"):
                    urls.add(e.get("url"))
    esperadas = {}
    for f in matriz["formularios"]:
        if f["mapping"] == "Svelte":
            esperadas[mapeo(f, matriz["aplicaciones"])[1]] = f["id"]
    for url, id_ in sorted(esperadas.items()):
        if url not in urls:
            hallazgos.append(f"{id_}: ningún form mapping de los .proc apunta a {url}")
    apps = {a["token"] for a in matriz["aplicaciones"]}
    for url in sorted(urls - esperadas.keys()):
        m = PORTAL.match(url)
        if m and m.group(1) in apps:
            hallazgos.append(f"el form mapping {url} apunta a un formulario inexistente en {FMATRIZ}")
    return hallazgos


def _sin_comentarios(texto: str) -> str:
    """Quita `// ...`, `/* ... */` y `<!-- ... -->` solo fuera de literales (las comillas simples y dobles acaban
    en la línea; las invertidas pueden ocupar varias): un `//` dentro de una cadena no esconde lo que sigue."""
    out, i, n = [], 0, len(texto)
    while i < n:
        c = texto[i]
        if c in "'\"`":
            j = i + 1
            while j < n and texto[j] != c and not (texto[j] == "\n" and c != "`"):
                j += 2 if texto[j] == "\\" else 1
            out.append(texto[i:j + 1])
            i = j + 1
        elif texto.startswith("//", i):
            j = texto.find("\n", i)
            i = n if j < 0 else j
        elif texto.startswith("/*", i):
            j = texto.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif texto.startswith("<!--", i):
            j = texto.find("-->", i + 4)
            i = n if j < 0 else j + 3
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _lectura(proyecto: Path, matriz: dict) -> list[str]:
    hallazgos = []
    catalogos: dict[str, list[tuple[str, str]]] = {}
    for f in matriz["formularios"]:
        if f["mapping"] == "Svelte":
            catalogos[token_pagina(f["id"])] = [(c["escribe"], c["campo"]) for c in f["campos"]
                                                if c["catalogo"] and c["escribe"]]
    raiz = proyecto / FORMS
    if not raiz.is_dir():
        return hallazgos
    for fichero in sorted(p for p in raiz.rglob("*") if p.is_file() and "generado" not in p.relative_to(raiz).parts
                          and p.suffix in (".svelte", ".ts", ".js", ".html")):
        rel = fichero.relative_to(proyecto).as_posix()
        texto = fichero.read_text(encoding="utf-8")
        limpio = _sin_comentarios(texto)
        if _API_BDM.search(limpio):
            hallazgos.append(f"{rel}: usa la API de datos de negocio (`/API/bdm`); los datos del caso se leen por la extensión de consultas "
                             "(`$lib/bonita/caso`)")
        if "processParameter" in limpio:
            hallazgos.append(f"{rel}: usa `processParameter`; los parámetros se leen del módulo de parámetros "
                             "(`$lib/parametros`, `extension/parametros/valores`)")
        if fichero.name.endswith(".test.ts"):
            continue
        carpeta = fichero.relative_to(raiz).parts[0]
        for ruta, campo in catalogos.get(carpeta, []):
            q = rf"""['"]{re.escape(ruta)}['"]"""
            if re.search(rf"{q}\]?\s*:\s*\[", limpio) or re.search(
                    rf"{q}[\s\S]{{0,{_VENTANA}}}?\bopciones\s*[:=]\s*\[", limpio):
                hallazgos.append(f"{rel}: el campo «{campo}» ({ruta}) tiene catálogo y su lista de opciones es "
                                 "literal; debe venir de `$lib/parametros`")
    return hallazgos


def comprobar(proyecto: Path) -> list[str]:
    proyecto = Path(proyecto)
    if not docs_de_procesos_nuevos(proyecto):
        return []
    matriz = _matriz(proyecto)
    svelte = [f for f in matriz["formularios"] if f["mapping"] == "Svelte"]
    return (_carpetas_y_manifiesto(proyecto, svelte) + _aplicaciones(proyecto, matriz)
            + _paginas_y_temas(proyecto, matriz) + _mappings(proyecto, matriz) + _lectura(proyecto, matriz))


def main() -> int:
    return ejecutar("check_formularios", comprobar)


if __name__ == "__main__":
    sys.exit(main())
