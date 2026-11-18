"""Living Applications (`app/applications/<token>.xml`) y direcciones de los formularios.

Una aplicación por familia de actores (o una sola, con el nombre del proyecto, si la visibilidad por familia no aplica;
las calcula el lector de la matriz: `spec["formularios"]["aplicaciones"]`). Cada formulario Svelte es una página de su
aplicación. Este módulo es el ÚNICO lugar donde se decide el nombre de una página; el `.proc` (form mapping) y el
descriptor de la aplicación lo reutilizan, y también lo hará la generación de los esqueletos Svelte:

    token de página  = `token_pagina(id)`            frm_2_revisarJefe -> frm2RevisarJefe  (solo [a-zA-Z0-9])
    recurso          = `recurso_pagina(id)`          custompage_frm2RevisarJefe
    dirección (U20)  = `/bonita/portal/resource/app/<token de la app>/<token de página>/content/`

Desde 0.12.1 (`docs/plan-5/contrato-de-formato.md` §2.20) el descriptor lleva también las páginas propias de la
aplicación (las que no son formulario: `spec["formularios"]["paginas"]`), la página de inicio, el tema propio y los
menús que declara la sección «Aplicación» de la matriz; el lector ya resolvió los alias a tokens.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.leer.matriz import TEMA_DE_BONITA, TOKENS_DE_LA_PLANTILLA, _camel

NS_APLICACIONES = "http://documentation.bonitasoft.com/application-xml-schema/1.1"
LAYOUT = "custompage_layoutBonita"
TEMA = TEMA_DE_BONITA
PERFIL_POR_DEFECTO = "User"
# `TOKENS_DE_LA_PLANTILLA` (vive en `leer/matriz.py`, que también lo usa): tokens de aplicación que trae la plantilla.


def token_pagina(id_formulario: str) -> str:
    """El id del formulario como token alfanumérico camelCase (`frm_2_revisarJefe` -> `frm2RevisarJefe`)."""
    token = _camel(id_formulario)
    if not token:
        raise ValueError(f"el formulario «{id_formulario}» no tiene caracteres alfanuméricos para su página")
    return token


def recurso_pagina(id_formulario: str) -> str:
    return f"custompage_{token_pagina(id_formulario)}"


def url_pagina(token_app: str, id_formulario: str) -> str:
    return f"/bonita/portal/resource/app/{token_app}/{token_pagina(id_formulario)}/content/"


def _aplicacion_de(form: dict, aplicaciones: list[dict]) -> dict:
    """La aplicación de un formulario Svelte: la de su familia de actores o, si no tiene, la única."""
    por_familia = [a for a in aplicaciones if a["familia_actores"] == form.get("familia_actores")]
    if len(por_familia) == 1:
        return por_familia[0]
    raise ValueError(f"formulario «{form['id']}»: no hay una aplicación para su familia visible "
                     f"«{form.get('familia_actores')}» ({', '.join(a['token'] for a in aplicaciones) or 'ninguna'})")


def mapeo(form: dict, aplicaciones: list[dict]) -> tuple[str, str | None]:
    """`(tipo, url)` del `formMapping` de un formulario: Svelte -> `URL` a su página; External URL -> `URL` a la
    matriz; No form -> `NONE`."""
    m = form["mapping"]
    if m == "Svelte":
        return "URL", url_pagina(_aplicacion_de(form, aplicaciones)["token"], form["id"])
    if m == "External URL":
        if not form.get("url"):
            raise ValueError(f"formulario «{form['id']}»: External URL sin la URL en el detalle de la matriz")
        return "URL", form["url"]
    if m == "No form":
        return "NONE", None
    raise ValueError(f"formulario «{form['id']}»: form mapping «{m}» no soportado")


def paginas(formularios: dict) -> dict[str, list[dict]]:
    """token de aplicación -> sus formularios Svelte (en el orden de la matriz). Falla si dos ids dan el mismo token
    de página."""
    apps = formularios.get("aplicaciones", [])
    out: dict[str, list[dict]] = {a["token"]: [] for a in apps}
    vistos: dict[str, str] = {}
    for f in formularios.get("formularios", []):
        if f["mapping"] != "Svelte":
            continue
        t = token_pagina(f["id"])
        if t in vistos:
            raise ValueError(f"los formularios «{vistos[t]}» y «{f['id']}» dan el mismo token de página «{t}»")
        vistos[t] = f["id"]
        out[_aplicacion_de(f, apps)["token"]].append(f)
    return out


def paginas_propias(formularios: dict) -> dict[str, list[dict]]:
    """token de aplicación -> sus páginas propias (en el orden de la tabla de páginas de la matriz)."""
    out: dict[str, list[dict]] = {a["token"]: [] for a in formularios.get("aplicaciones", [])}
    for p in formularios.get("paginas", []):
        for app in p["aplicaciones"]:
            out.setdefault(app, []).append(p)
    return out


def temas(formularios: dict) -> list[str]:
    """Los temas propios (`custompage_<x>`) de las aplicaciones, sin repetir, en el orden de las aplicaciones."""
    return list(dict.fromkeys(a["tema"] for a in formularios.get("aplicaciones", []) if a.get("tema")))


def generar_aplicacion(app: dict, formularios: list[dict], propias: list[dict] | tuple = ()) -> ET.ElementTree:
    """Descriptor de una aplicación: las páginas de sus formularios Svelte y después sus páginas propias. El
    descriptor admite un solo perfil (con más de uno, error; sin ninguno, `User`). `homePage` es la «Página de inicio»
    de la matriz o, sin ella, la primera página en el orden en que se escriben; `theme`, el tema propio o el de Bonita.
    Un `applicationMenu` de primer nivel por menú de la matriz (sin menús, `applicationMenus` vacío: el portal resuelve
    el form mapping y abre la página dentro de esta aplicación)."""
    paginas_app = [(recurso_pagina(f["id"]), token_pagina(f["id"])) for f in formularios] + \
                  [(p["recurso"], p["token"]) for p in propias]
    if not paginas_app:
        raise ValueError(f"la aplicación «{app['token']}» no tiene formularios Svelte ni páginas propias")
    if app["token"] in TOKENS_DE_LA_PLANTILLA:
        raise ValueError(f"aplicación «{app['token']}»: ese token es de la aplicación de administración de parámetros "
                         "de la plantilla; dale otro nombre a la aplicación en la matriz de formularios")
    tokens = [tok for _, tok in paginas_app]
    raiz = ET.Element("applications", {"xmlns": NS_APLICACIONES})
    perfiles = app.get("perfiles") or [PERFIL_POR_DEFECTO]
    if len(perfiles) > 1:
        raise ValueError(f"aplicación «{app['token']}»: «Perfiles con acceso» de la matriz de formularios lista "
                         f"{len(perfiles)} perfiles ({', '.join(perfiles)}); un descriptor de Living Application de "
                         "Bonita admite un solo perfil por aplicación. Deje uno (o separe las familias en "
                         "aplicaciones distintas)")
    inicio = app.get("inicio") or tokens[0]
    for que, tok in [("la página de inicio", inicio)] + [(f"el menú «{m['etiqueta']}»", m["pagina"])
                                                          for m in app.get("menus", [])]:
        if tok not in tokens:
            raise ValueError(f"aplicación «{app['token']}»: {que} apunta a «{tok}», que no es una página del "
                             f"descriptor ({', '.join(tokens)})")
    perfil = perfiles[0]
    a = ET.SubElement(raiz, "application", {"token": app["token"], "version": "1.0", "profile": perfil,
                                            "homePage": inicio, "state": "ACTIVATED", "layout": LAYOUT,
                                            "theme": app.get("tema") or TEMA})
    ET.SubElement(a, "displayName").text = app["nombre"]
    ET.SubElement(a, "description").text = f"Aplicación {app['nombre']}: contiene las pantallas de sus formularios."
    pags = ET.SubElement(a, "applicationPages")
    for recurso, tok in paginas_app:
        ET.SubElement(pags, "applicationPage", {"customPage": recurso, "token": tok})
    menus = ET.SubElement(a, "applicationMenus")
    for m in app.get("menus", []):
        ET.SubElement(ET.SubElement(menus, "applicationMenu", {"applicationPage": m["pagina"]}),
                      "displayName").text = m["etiqueta"]
    return ET.ElementTree(raiz)
