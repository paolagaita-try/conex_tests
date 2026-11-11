"""Lector de `docs/07-bonita/matriz-formularios.md`: formularios, campos y aplicaciones (Living Applications).

Un registro por fila de la matriz. El mapping del formulario es `Svelte` (v1), `External URL` o `No form`; `UI Designer`
no se admite nunca y UI Builder es una opción futura. `familia_formularios` es la columna «Familia» de la matriz
(FAM-*, la unidad de trabajo); `familia_actores` sale de «Familia visible» del detalle del formulario y decide a qué
aplicación va: si la visibilidad por familia no aplica, todos los formularios van a una sola aplicación cuyo token es
el nombre del proyecto. El valor de «Familia visible» empieza por el nombre de **una** familia (token o texto hasta el
primer «.», «(», «;», «:» o «,»); lo que sigue es explicación.

Qué familia es la interna lo declara la línea opcional «- **Familia interna**: `<familia>`» (en Convenciones); sin ella
la interna se llama `interna` (0.11.1). Solo con la línea la spec lleva `formularios.familia_interna`.

Del detalle de cada formulario el lector lee «Form mapping», «Familia visible» y «Acciones»; una etiqueta «**X**:» que
se parece a una de ellas es error (sugiere la correcta) y una dudosa, aviso por stderr: nunca se ignora en silencio.

De la sección «Aplicación» (0.12.1, `docs/plan-5/contrato-de-formato.md` §2.20) lee, por aplicación generada, los
perfiles, la página de inicio, el tema propio y los menús, y las páginas propias (las que no son formulario: bandejas,
«mis casos»…). Los alias de la documentación se resuelven aquí: la spec solo lleva tokens.
"""
from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher

from generadores.leer import columna, donde, filas, seccion, tabla, vacio
from generadores.md import _CAMPO, Seccion, codigo, leer_markdown

F = "matriz-formularios.md"
MAPPINGS = ("Svelte", "External URL", "No form")
TIPOS = ("Instantiation form", "Task form", "Case overview")
_PARAM = re.compile(r"param_\w+")
_BACKTICKS = re.compile(r"`([^`]+)`")
_COLUMNAS_MATRIZ = ("Formulario", "Tipo", "Tarea BPMN", "Actor", "Contrato", "Form mapping", "Familia")
FAMILIA_INTERNA = "interna"  # nombre de la familia interna si la matriz no declara «Familia interna»
ETIQUETAS_DEL_DETALLE = ("Form mapping", "Familia visible", "Acciones")  # las que el lector lee del detalle
_VARIAS = re.compile(r"(?i)^(las|los|todas|todos|ambas|ambos|cualquiera|varias|varios)\b")
# Tokens de aplicación que trae la plantilla (`app/applications/<token>.xml`, no generados): la de administración de
# parámetros del módulo. Una aplicación de la matriz con uno de ellos la pisaría; una columna suya en la tabla de
# aplicaciones se ignora.
TOKENS_DE_LA_PLANTILLA = ("parametros",)
TEMA_DE_BONITA = "custompage_themeBonita"  # el tema por defecto: nombrarlo no declara un tema propio
_TRAS_TOKEN = re.compile(r"\btoken\s+`([^`]+)`")
_ETIQUETA = re.compile(r"«([^»]+)»")
_RECURSO = re.compile(r"custompage_(\S+)")
_ALFANUMERICO = re.compile(r"[a-zA-Z0-9]+")
_COLUMNAS_CAMPOS = ("Control", "Input del contrato", "Objeto.atributo", "Obligatorio", "Validación", "Depende",
                    "Catálogo", "Visibilidad")


def _texto(celda: str) -> str | None:
    """Texto de la celda sin backticks; None si no tiene valor."""
    return None if vacio(celda) else celda.replace("`", "").strip()


def _referencia(celda: str) -> str | None:
    return None if vacio(celda) else codigo(celda).strip()


def _mapping(celda: str, u: str, errores: list[str]) -> str | None:
    m = codigo(celda).strip()
    if m == "UI Designer":
        errores.append(f"{u}: Form mapping «UI Designer» no se admite (Svelte en v1; UI Builder en el futuro); "
                       f"use {' | '.join(MAPPINGS)}")
        return None
    if m not in MAPPINGS:
        errores.append(f"{u}: Form mapping «{celda}» debe ser {' | '.join(MAPPINGS)}")
        return None
    return m


def _nombre_familia(valor: str | None, u: str, etiqueta: str, errores: list[str]) -> str | None:
    """El nombre de la familia con que empieza el valor (token o texto hasta «.», «(», «;», «:» o «,»); None si es
    vacío o «no aplica…». Más de una familia es error: un formulario es de una sola (la aplicación de su form mapping)."""
    if valor is None or vacio(valor) or valor.strip().lower().startswith("no aplica"):
        return None
    v = valor.strip()
    if v.startswith("`") and v.count("`") >= 2:
        nombre = v[1:v.index("`", 1)].strip()
        resto = v[v.index("`", 1) + 1:]
        varias = re.match(r"\s*(,|y\s|e\s|/)\s*`", resto) is not None
    else:
        nombre = re.split(r"\.(?:\s|$)|[(;:,]", v, maxsplit=1)[0].strip().rstrip(".").strip()
        varias = "`" in nombre
    if varias or not nombre or _VARIAS.match(nombre):
        errores.append(f"{u}: «{etiqueta}» «{v}» no nombra una sola familia: un formulario es de una sola familia "
                       f"(la de la aplicación de su form mapping); escribe su nombre al principio, como token "
                       f"(`equipo`), y la explicación detrás")
        return None
    return nombre


def _familia_visible(det: Seccion | None, u: str, errores: list[str]) -> str | None:
    return _nombre_familia(det.campo("Familia visible") if det else None, u, "Familia visible", errores)


def _familia_interna(doc, errores: list[str]) -> str | None:
    """La familia que declara «- **Familia interna**: `<familia>`» (en cualquier sección; se documenta en
    Convenciones); None sin la línea o con «no aplica»."""
    valores = []
    for s in [doc.raiz, *doc.raiz._recorrer()]:
        for linea in s.texto.splitlines():
            m = _CAMPO.match(linea)
            if m and m.group(1).strip() == "Familia interna":
                nombre = _nombre_familia(m.group(2), F, "Familia interna", errores)
                if nombre is not None and nombre not in valores:
                    valores.append(nombre)
    if len(valores) > 1:
        errores.append(f"{F}: «Familia interna» aparece dos veces con valores distintos "
                       f"({', '.join(f'«{v}»' for v in valores)}); deja una sola línea en Convenciones")
    return valores[0] if valores else None


def _etiquetas_desconocidas(det: Seccion, u: str, errores: list[str]) -> None:
    """Una etiqueta «**X**:» del detalle que el lector no lee: si se parece mucho a una que sí lee, error con la
    correcta; si se parece algo, aviso por stderr; si no se parece, es una etiqueta propia del documento."""
    for s in [det, *det._recorrer()]:
        for linea in s.texto.splitlines():
            m = _CAMPO.match(linea)
            if not m or m.group(1).strip() in ETIQUETAS_DEL_DETALLE:
                continue
            etiqueta = m.group(1).strip()
            parecido, buena = max((SequenceMatcher(None, etiqueta.lower(), k.lower()).ratio(), k)
                                  for k in ETIQUETAS_DEL_DETALLE)
            if parecido >= 0.7:
                errores.append(f"{u}: etiqueta «{etiqueta}» desconocida; ¿es «{buena}»? Del detalle se leen "
                               f"{', '.join(f'«{k}»' for k in ETIQUETAS_DEL_DETALLE)} con esa etiqueta exacta: con "
                               f"otra, el dato se ignora")
            elif parecido >= 0.5 or any(w in etiqueta.lower() for w in ("visib", "mapping")):
                print(f"aviso: {u}: etiqueta «{etiqueta}» no se lee; si es «{buena}», escríbela así (las etiquetas "
                      f"que se leen del detalle son {', '.join(f'«{k}»' for k in ETIQUETAS_DEL_DETALLE)})",
                      file=sys.stderr)


def _titulo(det: Seccion | None) -> str | None:
    """El título del detalle («`frm_…` — Título»): el nombre visible de la pantalla; None si no lo trae."""
    if det is None or "—" not in det.titulo:
        return None
    return det.titulo.split("—", 1)[1].replace("`", "").strip() or None


def _url(det: Seccion | None) -> str | None:
    """Ruta del formulario externo: el primer `https://…` o `/ruta` que da la línea «Form mapping» del detalle."""
    linea = det.campo("Form mapping") if det else None
    for c in _BACKTICKS.findall(linea or ""):
        if re.match(r"(https?://|/)\S+$", c):
            return c
    return None


def _campos(det: Seccion, u: str, errores: list[str]) -> list[dict] | None:
    """Los campos de la tabla del detalle; `None` si el detalle no tiene la tabla. Sin ella solo vale un formulario
    cuyo contrato no tiene inputs (p. ej. el de instanciación que solo inicia el caso): lo decide
    `validar/huecos_generador.py`, que conoce los contratos."""
    t = tabla(det, "Campo", _COLUMNAS_CAMPOS, u, errores)
    if t is None:
        return None if not any(tb and list(tb[0])[0] == "Campo" for tb in det.tablas) else []
    out = []
    for f in filas(t):
        nombre = f["Campo"].strip()
        uc = donde(u, nombre)
        escribe, lee = _referencia(columna(f, "Input del contrato")), _referencia(columna(f, "Objeto.atributo"))
        if escribe is None and lee is None:
            errores.append(f"{uc}: campo sin origen ni destino (todo campo escribe en un input del contrato o lee "
                           f"de un objeto o consulta)")
        obligatorio = columna(f, "Obligatorio").strip().lower()
        if vacio(obligatorio):
            if escribe is not None:
                # Vacío no es «no»: quien escribe en el contrato dice si el dato es obligatorio.
                errores.append(f"{uc}: Obligatorio vacío en un campo que escribe «{escribe}»: debe ser «sí» o «no»")
        elif obligatorio not in ("sí", "si", "no"):
            errores.append(f"{uc}: Obligatorio «{obligatorio}» debe ser «sí» o «no»")
        catalogo = _texto(columna(f, "Catálogo"))
        if catalogo is not None and not _PARAM.search(catalogo):
            errores.append(f"{uc}: Catálogo «{catalogo}» debe ser «`param_<nombre>`»")
        out.append({"campo": nombre, "control": _texto(columna(f, "Control")), "escribe": escribe, "lee": lee,
                    "obligatorio": obligatorio in ("sí", "si"), "validacion": _texto(columna(f, "Validación")),
                    "depende": _texto(columna(f, "Depende")), "catalogo": catalogo,
                    "visibilidad": _texto(columna(f, "Visibilidad"))})
    return out


def _camel(texto: str, inicial_mayuscula: bool = False) -> str:
    """Solo [a-zA-Z0-9]: quita todo lo demás y pone en mayúscula la letra que sigue a cada carácter quitado."""
    out = []
    mayuscula = inicial_mayuscula
    for ch in texto:
        if re.fullmatch(r"[a-zA-Z0-9]", ch):
            out.append(ch.upper() if mayuscula else ch)
            mayuscula = False
        else:
            mayuscula = bool(out) or inicial_mayuscula
    return "".join(out)


def _comprobar_interna(interna: str | None, formularios: list[dict], errores: list[str]) -> None:
    """La familia interna declarada debe ser la «Familia visible» de algún formulario Svelte."""
    familias = list(dict.fromkeys(f["familia_actores"] for f in formularios
                                  if f["mapping"] == "Svelte" and f["familia_actores"]))
    if interna is None or not familias or interna.strip().lower() in {x.strip().lower() for x in familias}:
        return
    errores.append(f"{F}: la «Familia interna» declarada «{interna}» no es la «Familia visible» de ningún formulario "
                   f"Svelte (familias: {', '.join(familias)}); corrige la línea «- **Familia interna**: `<familia>`» "
                   f"de Convenciones con la familia del equipo interno")


def _aplicaciones(formularios: list[dict], doc, proyecto: str, errores: list[str],
                  con_error: frozenset[str] = frozenset()) -> list[dict]:
    """Una aplicación por familia de actores; sin visibilidad por familia, una sola con el nombre del proyecto.
    `con_error`: formularios cuya «Familia visible» ya dio error (no se repite como «no tiene»). Los perfiles los pone
    después `_aplicacion_completa`."""
    familias = list(dict.fromkeys(f["familia_actores"] for f in formularios
                                  if f["mapping"] == "Svelte" and f["familia_actores"]))
    base = _camel(proyecto)
    if not familias:
        if not base:
            errores.append(f"{F}: el nombre del proyecto «{proyecto}» no tiene caracteres alfanuméricos para el "
                           f"token de la aplicación")
        return [{"token": base, "nombre": proyecto, "perfiles": [], "familia_actores": None}]
    for f in formularios:
        if f["mapping"] == "Svelte" and not f["familia_actores"] and f["id"] not in con_error:
            errores.append(f"{donde(F, 'Detalle por formulario', f['id'])}: la visibilidad por familia aplica a otros "
                           f"formularios Svelte y este no tiene «Familia visible»")
    out = []
    for fam in familias:
        token = base + _camel(fam, True)
        if not _camel(fam):
            errores.append(f"{F}: la familia visible «{fam}» no tiene caracteres alfanuméricos para el token")
        out.append({"token": token, "nombre": fam, "perfiles": [], "familia_actores": fam})
    return out


# ------------------------------------------------------------------------- sección «Aplicación» (0.12.1, §2.20)

def _humano(alias: str) -> str:
    """`detalleCasoCliente` -> «Detalle caso cliente»: el nombre visible de una página propia sin menú."""
    palabras = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", alias).replace("_", " ").split()
    texto = " ".join(palabras).lower()
    return texto[:1].upper() + texto[1:]


def _token_de_aplicacion(celda: str) -> tuple[str | None, str | None]:
    """`(alias, token)` de la celda «Application descriptor» de una columna: el token va tras «token» o, sin esa
    palabra, es el primero entre comillas invertidas; el alias es siempre el primero."""
    tokens = _BACKTICKS.findall(celda)
    if not tokens:
        return None, None
    m = _TRAS_TOKEN.search(celda)
    return tokens[0].strip(), (m.group(1) if m else tokens[0]).strip()


def _columnas_de_aplicacion(t: list[dict], apps: list[dict], u: str, errores: list[str]) -> dict[str, list[dict]]:
    """Columna de la tabla de aplicaciones -> aplicaciones a las que valen sus filas. `| Elemento | Valor |`: todas; una
    columna por aplicación: la que nombra su celda «Application descriptor…» (las de la plantilla se ignoran)."""
    columnas = list(t[0])[1:] if t else []
    fila = next((f for f in filas(t) if f["Elemento"].strip().startswith("Application descriptor")), None)
    valor = next((c for c in columnas if c.startswith("Valor")), None)
    # Con una columna «Valor…» manda la forma de la plantilla (las demás columnas son notas), salvo que haya varias
    # columnas y la fila «Application descriptor» traiga un token en cada una.
    if valor is not None and (len(columnas) == 1 or fila is None
                              or not all(_BACKTICKS.findall(fila[c]) for c in columnas)):
        return {valor: list(apps)}
    if fila is None:
        errores.append(f"{u}: la tabla de aplicaciones tiene una columna por aplicación ({', '.join(columnas)}) y no "
                       f"tiene la fila «Application descriptor» que dice el token de cada una (`` token `<token>` ``)")
        return {}
    por_token = {a["token"]: a for a in apps}
    out: dict[str, list[dict]] = {}
    for c in columnas:
        alias, token = _token_de_aplicacion(fila[c])
        if token in TOKENS_DE_LA_PLANTILLA:
            continue
        if token is None or token not in por_token:
            errores.append(f"{donde(u, c)}: la aplicación «{token or fila[c].strip()}» no es ninguna de las que se "
                           f"generan (una por «Familia visible»: {', '.join(por_token) or 'ninguna'}); escribe su "
                           f"token tras la palabra «token» en la fila «Application descriptor»")
            continue
        por_token[token]["_alias"] = alias
        out[c] = [por_token[token]]
    return out


def _tema(celda: str, u: str, errores: list[str]) -> str | None:
    """El tema propio de «Layout / tema»: el primer `custompage_<x>` entre comillas invertidas que no es un layout ni
    el tema de Bonita; None si no hay."""
    for tok in _BACKTICKS.findall(celda):
        tok = tok.strip()
        if not tok.startswith("custompage_") or tok.startswith("custompage_layout") or tok == TEMA_DE_BONITA:
            continue
        if not _ALFANUMERICO.fullmatch(tok.removeprefix("custompage_")):
            errores.append(f"{u}: el tema «{tok}» no es válido: tras `custompage_` solo caracteres alfanuméricos "
                           f"(con otros, Bonita no instala la aplicación)")
            return None
        if tok.removeprefix("custompage_") in TOKENS_DE_LA_PLANTILLA:
            errores.append(f"{u}: el tema «{tok}» se llama como una página de la plantilla "
                           f"({', '.join(TOKENS_DE_LA_PLANTILLA)}); dale otro nombre")
            return None
        return tok
    return None


def _es_menu(etiqueta: str) -> bool:
    """¿Da menú la etiqueta? «sin menú», «—» y vacío no."""
    e = etiqueta.replace("`", "").strip()
    return not vacio(e) and not e.lower().startswith("sin menú")


def _resolver(nombre: str, alias: dict[str, str]) -> str | None:
    return alias.get(nombre.strip())


def _aplicacion_completa(doc, formularios: list[dict], apps: list[dict], errores: list[str]) -> list[dict]:
    """Lee la sección «Aplicación» sobre las aplicaciones generadas (las completa en el sitio: `perfiles`, `inicio`,
    `tema`, `menus`) y devuelve las páginas propias. `inicio` solo se pone si no es la página por defecto (la primera
    de formulario), `tema` solo si es propio y `menus` solo si hay alguno: una matriz sin lo nuevo da la misma spec."""
    try:
        sec = doc.seccion("Aplicación")
    except KeyError:
        return []
    u = donde(F, sec.titulo)
    t = tabla(sec, "Elemento")
    columnas = _columnas_de_aplicacion(t, apps, u, errores) if t else {}
    # `| Elemento | Valor |` vale para todas: su «Página de inicio» solo se aplica a las aplicaciones que tienen esa página.
    para_todas = len(columnas) == 1 and next(iter(columnas)).startswith("Valor")
    inicio_pedido: dict[str, str] = {}
    for f in filas(t):
        elemento = f["Elemento"].strip()
        for c, destino in columnas.items():
            celda, uc = f[c], donde(u, elemento, c)
            for a in destino:
                if elemento.startswith("Perfiles con acceso"):
                    a["perfiles"] = _BACKTICKS.findall(celda)
                elif elemento.startswith("Página de inicio"):
                    tokens = _BACKTICKS.findall(celda)
                    if tokens:
                        inicio_pedido[a["token"]] = tokens[0].strip()
                elif elemento.startswith("Layout / tema"):
                    tema = _tema(celda, uc, errores)
                    if tema is not None:
                        a["tema"] = tema
    por_token = {a["token"]: a for a in apps}
    alias_app = {a["token"]: a["token"] for a in apps}
    alias_app.update({a.pop("_alias"): a["token"] for a in apps if "_alias" in a})

    # Páginas de formulario (su aplicación la decide su familia) y alias de la documentación.
    svelte = [f for f in formularios if f["mapping"] == "Svelte"]
    app_de_form: dict[str, str] = {}
    for f in svelte:
        destino = [a for a in apps if a["familia_actores"] == f.get("familia_actores")] or apps
        if len(destino) == 1 and _camel(f["id"]):
            app_de_form[_camel(f["id"])] = destino[0]["token"]
    alias: dict[str, str] = {tok: tok for tok in app_de_form}
    for f in svelte:  # el id del formulario (`frm_2_revisarJefe`) también nombra su página
        if _camel(f["id"]) in app_de_form:
            alias.setdefault(f["id"], _camel(f["id"]))
    propias: list[dict] = []
    menus_de_fila: list[tuple[str, str, str]] = []  # (aplicación, etiqueta, página) de la columna «Menú»

    def nombrar(a: str, tok: str, uf: str) -> bool:
        for nombre in dict.fromkeys((a, tok)):
            if alias.get(nombre, tok) != tok:
                errores.append(f"{uf}: el nombre «{nombre}» ya es el de la página «{alias[nombre]}»; un alias o un "
                               f"token solo puede nombrar una página")
                return False
        alias.setdefault(a, tok)
        alias.setdefault(tok, tok)  # por token también vale
        return True

    tp = tabla(sec, "Página")
    # Sin columna «Recurso» (la tabla de la plantilla), la tabla solo nombra formularios: las demás filas se ignoran.
    con_recurso = bool(tp) and any(k.startswith("Recurso") for k in tp[0])
    for f in filas(tp):
        celda = f["Página"]
        uf = donde(u, "Página", celda.replace("`", "").strip())
        tokens = [x.strip() for x in _BACKTICKS.findall(celda)]
        m = _TRAS_TOKEN.search(celda)
        try:
            recurso_celda = codigo(columna(f, "Recurso")).strip()
        except KeyError:
            recurso_celda = ""
        recurso = None if vacio(recurso_celda) or "<" in recurso_celda else recurso_celda
        if not tokens:
            errores.append(f"{uf}: la celda «Página» no nombra ninguna página entre comillas invertidas")
            continue
        if m:
            paginas_fila = [(tokens[0], m.group(1).strip())]
        elif len(tokens) > 1:
            paginas_fila = [(x, x) for x in tokens]
        else:
            r = _RECURSO.fullmatch(recurso or "")
            paginas_fila = [(tokens[0], r.group(1) if r and not app_de_form.get(tokens[0]) else tokens[0])]
        try:
            celda_apps = columna(f, "Aplicación")
        except KeyError:
            celda_apps = None
        apps_fila = [x.strip() for x in _BACKTICKS.findall(celda_apps or "")]
        try:
            etiquetas = [e.strip() for e in _ETIQUETA.findall(columna(f, "Menú")) if _es_menu(e)]
        except KeyError:
            etiquetas = []
        for a, tok in paginas_fila:
            if tok in app_de_form:
                nombrar(a, tok, uf)
                if len(paginas_fila) == 1 and len(apps_fila) == 1 and len(etiquetas) == 1:
                    menus_de_fila.append((apps_fila[0], etiquetas[0], a))
                continue
            # Página propia.
            if not con_recurso:
                continue
            if tok in TOKENS_DE_LA_PLANTILLA:
                errores.append(f"{uf}: la página propia «{a}» se llama como una página de la plantilla «{tok}»; dale "
                               f"otro token")
                continue
            if recurso is None:
                errores.append(f"{uf}: «{a}» no es un formulario Svelte de la matriz, así que es una página propia: "
                               f"su «Recurso» debe ser `custompage_<token>` (falta la columna o el valor)")
                continue
            if recurso != f"custompage_{tok}" or not _ALFANUMERICO.fullmatch(tok):
                errores.append(f"{uf}: el «Recurso» «{recurso}» de la página propia «{a}» debe ser `custompage_<token>` "
                               f"con el token de la página («{tok}») y solo caracteres alfanuméricos tras "
                               f"`custompage_` (con otros, Bonita no instala la aplicación)")
                continue
            if any(p["token"] == tok for p in propias):
                errores.append(f"{uf}: la página propia «{tok}» está dos veces en la tabla de páginas")
                continue
            if celda_apps is None or not apps_fila:
                errores.append(f"{uf}: la página propia «{a}» no dice en qué aplicación va (columna «Aplicación…», "
                               f"con el alias o el token de la aplicación)")
                continue
            destino = []
            for x in apps_fila:
                if x not in alias_app:
                    errores.append(f"{uf}: la aplicación «{x}» de la página propia «{a}» no es ninguna de las que se "
                                   f"generan ({', '.join(por_token) or 'ninguna'}; o su alias de la fila "
                                   f"«Application descriptor»)")
                elif alias_app[x] not in destino:
                    destino.append(alias_app[x])
            if not destino or not nombrar(a, tok, uf):
                continue
            propias.append({"token": tok, "alias": a, "recurso": recurso, "aplicaciones": destino, "titulo": None})
            if len(apps_fila) == 1 and len(etiquetas) == 1:
                menus_de_fila.append((apps_fila[0], etiquetas[0], a))

    def paginas_de(app: str) -> list[str]:
        return [tok for tok, ap in app_de_form.items() if ap == app] + \
               [p["token"] for p in propias if app in p["aplicaciones"]]

    # Un tema no puede llamarse como una página (comparten carpeta en frontend/src/forms y entrada del manifiesto).
    for a in apps:
        x = a.get("tema", "").removeprefix("custompage_")
        if x and (x in app_de_form or any(p["token"] == x for p in propias)):
            errores.append(f"{u}: el tema «{a['tema']}» de la aplicación «{a['token']}» se llama como la página «{x}»; "
                           f"dale otro nombre al tema")
            del a["tema"]

    # Menús: la tabla «| Menú | Aplicación | Página |» o, sin ella, la columna «Menú» de la tabla de páginas.
    tm = tabla(sec, "Menú")
    if tm is not None:
        crudos = []
        for f in filas(tm):
            etiqueta = _ETIQUETA.findall(f["Menú"])
            etiqueta = etiqueta[0].strip() if etiqueta else f["Menú"].replace("`", "").strip()
            if not _es_menu(etiqueta):
                continue
            try:
                ap = (_BACKTICKS.findall(columna(f, "Aplicación")) or [columna(f, "Aplicación")])[0].strip()
                pag = (_BACKTICKS.findall(columna(f, "Página")) or [columna(f, "Página")])[0].strip()
            except KeyError as e:
                errores.append(f"{donde(u, 'Menú')}: a la tabla de menús le falta la columna {e} "
                               f"(«| Menú | Aplicación | Página |»)")
                break
            crudos.append((ap, etiqueta, pag))
    else:
        crudos = menus_de_fila
    for ap, etiqueta, pag in crudos:
        um = donde(u, "Menú", f"«{etiqueta}»")
        if ap not in alias_app:
            errores.append(f"{um}: la aplicación «{ap}» no es ninguna de las que se generan "
                           f"({', '.join(por_token) or 'ninguna'})")
            continue
        app = alias_app[ap]
        tok = _resolver(pag, alias)
        if tok is None:
            errores.append(f"{um}: la página «{pag}» no es ninguna página de la tabla de páginas ni un formulario "
                           f"Svelte de la matriz")
        elif tok not in paginas_de(app):
            errores.append(f"{um}: la página «{pag}» no está en la aplicación «{app}» (sus páginas: "
                           f"{', '.join(paginas_de(app)) or 'ninguna'})")
        elif {"etiqueta": etiqueta, "pagina": tok} in por_token[app].get("menus", []):
            errores.append(f"{um}: el menú «{etiqueta}» a la página «{tok}» está dos veces en la aplicación «{app}»")
        else:
            por_token[app].setdefault("menus", []).append({"etiqueta": etiqueta, "pagina": tok})

    # Página de inicio: por alias o token, de esa aplicación; la de defecto (la primera de formulario) no se anota.
    avisados: set[str] = set()
    for app, pedido in inicio_pedido.items():
        tok = _resolver(pedido, alias)
        propias_app = paginas_de(app)
        if tok is None or tok not in propias_app:
            if para_todas:
                # La tabla de la plantilla vale para todas: si es la página de otra aplicación, esta se queda con la
                # de defecto; si no es de ninguna (p. ej. una página de Bonita), 0.12.0 la ignoraba: aviso.
                if pedido not in avisados and not (tok is not None and
                                                   any(tok in paginas_de(a["token"]) for a in apps)):
                    print(f"aviso: {donde(u, 'Página de inicio')}: «{pedido}» no es una página de ninguna aplicación "
                          f"generada (formulario Svelte o página propia); se usa la de defecto, la primera página "
                          f"de formulario", file=sys.stderr)
                avisados.add(pedido)
                continue
            errores.append(f"{donde(u, 'Página de inicio')}: «{pedido}» no es una página de la aplicación «{app}» "
                           f"(sus páginas: {', '.join(propias_app) or 'ninguna'}; por alias o token)")
            continue
        if tok != propias_app[0]:  # la de defecto: la primera de formulario o, sin formularios, la primera propia
            por_token[app]["inicio"] = tok

    for p in propias:
        p["titulo"] = next((m["etiqueta"] for a in apps for m in a.get("menus", []) if m["pagina"] == p["token"]),
                           None) or _humano(p["alias"])
    return propias


def leer_matriz(texto: str, errores: list[str], proyecto: str = "") -> dict:
    """`{"formularios": [...], "aplicaciones": [...]}`; `proyecto` es el token de la aplicación única."""
    doc = leer_markdown(texto)
    sec = seccion(doc, "Matriz de formularios", F, errores)
    t = tabla(sec, "Formulario", _COLUMNAS_MATRIZ, donde(F, "Matriz de formularios"), errores)
    if t is None:
        if sec is not None and not any(tb and list(tb[0])[0] == "Formulario" for tb in sec.tablas):
            errores.append(f"{donde(F, 'Matriz de formularios')}: falta la tabla «| Formulario | Tipo | … |»")
        return {"formularios": [], "aplicaciones": []}
    try:
        detalles = {}
        for s in doc.seccion("Detalle por formulario").hijas:
            ids = _BACKTICKS.findall(s.titulo)
            if ids:
                detalles[ids[0]] = s
    except KeyError:
        detalles = {}
        errores.append(f"{F}: falta la sección «Detalle por formulario»")
    out: list[dict] = []
    con_error: set[str] = set()
    for f in filas(t):
        id_ = codigo(f["Formulario"]).strip()
        u = donde(F, "Matriz de formularios", id_)
        if not id_.startswith("frm_"):
            errores.append(f"{u}: el ID debe empezar por «frm_»")
        if any(o["id"] == id_ for o in out):
            errores.append(f"{u}: ID repetido")
        tipo = f["Tipo"].strip()
        if tipo not in TIPOS:
            errores.append(f"{u}: tipo «{tipo}» debe ser {' | '.join(TIPOS)}")
        mapping = _mapping(columna(f, "Form mapping"), u, errores)
        familia = _texto(columna(f, "Familia"))
        det = detalles.get(id_)
        antes = len(errores)
        familia_actores = _familia_visible(det, donde(F, "Detalle por formulario", id_), errores)
        if len(errores) > antes:
            con_error.add(id_)
        form = {"id": id_, "tipo": tipo, "tarea": _texto(columna(f, "Tarea BPMN")),
                "actor": _texto(columna(f, "Actor")), "contrato": _referencia(columna(f, "Contrato")),
                "mapping": mapping, "familia_formularios": familia,
                "familia_actores": familia_actores, "titulo": _titulo(det), "campos": [], "acciones": ""}
        if mapping == "External URL":
            form["url"] = _url(det)
        if mapping in ("Svelte", "External URL"):
            if familia is None:
                errores.append(f"{u}: el formulario {mapping} no tiene familia (columna «Familia»)")
            if det is None:
                errores.append(f"{donde(F, 'Detalle por formulario', id_)}: falta el detalle del formulario")
            else:
                ud = donde(F, "Detalle por formulario", id_)
                _etiquetas_desconocidas(det, ud, errores)
                campos = _campos(det, ud, errores)
                form["campos"] = campos or []
                if campos is None:
                    form["sin_tabla_campos"] = True  # solo cuando falta (G-5)
                form["acciones"] = " ".join((det.campo("Acciones") or "").replace("`", "").split())
        out.append(form)
    apps = _aplicaciones(out, doc, proyecto, errores, frozenset(con_error))
    resultado = {"formularios": out, "aplicaciones": apps}
    propias = _aplicacion_completa(doc, out, apps, errores)
    if propias:
        resultado["paginas"] = propias
    interna = _familia_interna(doc, errores)
    _comprobar_interna(interna, out, errores)
    if interna is not None:
        resultado["familia_interna"] = interna
    return resultado


def familia_interna(formularios: dict | None) -> str:
    """El nombre de la familia interna de `spec["formularios"]`: el declarado o `interna`."""
    return (formularios or {}).get("familia_interna") or FAMILIA_INTERNA


def es_interna(familia: str | None, formularios: dict | None) -> bool:
    """¿Es `familia` (la «Familia visible» de un formulario) la interna? Sin distinguir mayúsculas."""
    return (familia or "").strip().lower() == familia_interna(formularios).strip().lower()
