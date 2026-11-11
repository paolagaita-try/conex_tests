"""Frontend de los formularios Svelte: lo generado desde la documentación y el esqueleto editable de cada pantalla.

Por cada formulario `Svelte` de la matriz (`spec["formularios"]`), en `frontend/src/forms/<token de página>/`:

- GENERADO (protegido por el guard; cada `generar` lo reescribe):
  - `generado/contrato.ts`: `FORMULARIO` (identidad), `ENTRADAS` (todo input del contrato), los tipos del cuerpo
    (`Entrada<Input>` por input COMPLEX y `CuerpoDelContrato`), `CUERPO_VACIO` (todo a `null`), `CAMPOS` (los campos
    de la matriz que escriben en el contrato, con la forma que consume `CamposDeContrato`), `LECTURAS` (los de solo
    lectura, con el `atributo` del objeto del caso) y `cuerpoDelContrato(valores, subidos)`, que arma el cuerpo con
    TODO input del contrato: lo que la matriz no usa va a `null` (el motor responde 400 si falta uno). Un FILE viaja
    como la referencia `{ filename, tempPath, contentType }` que devuelve la subida (`$lib/bonita/archivos`, al
    enviar; una subida fallida bloquea el envío). Un BOOLEAN obligatorio sin marcar es `false`; LOCALDATE va como
    `aaaa-mm-dd`; DATE y OFFSETDATETIME, al inicio del día con el desfase local del navegador.
  - `generado/esquema.ts`: el esquema zod del cuerpo (obligatoriedad de la matriz, opciones cerradas, enteros); la
    verdad última sigue siendo el contrato de Bonita (sus constraints Groovy no se traducen).
- EDITABLE (se escribe solo si no existe; después es del proyecto): `index.html`, `main.ts`, `<Nombre>.svelte`
  (usa `CamposDeContrato`; carga al abrir los datos de solo lectura por la extensión de lecturas del caso,
  `$lib/bonita/caso`, nunca `/API/bdm`, y dice si fallan), `textos.ts`, `validacion.ts` y `pantalla.test.ts`.

Por cada página propia de la matriz (0.12.1, §2.20: bandejas, «mis casos»… `spec["formularios"]["paginas"]`), en
`frontend/src/forms/<token>/`, un esqueleto EDITABLE (`index.html`, `main.ts`, `<Nombre>.svelte`, `pantalla.test.ts`):
una página mínima con su título, que el proyecto completa leyendo por las extensiones de solo lectura. Por cada tema
propio de una aplicación (`custompage_<x>`), `frontend/src/forms/<x>/tema.css`, también editable; `build-form.js` lo
empaqueta sobre Bootstrap 3.

Y `frontend/forms.manifest.json` (generado): las entradas técnicas que ya tenga (`_semilla`, `_muestra`, la página
de parámetros… todo lo que no es `tipo: negocio`, `pagina` o `tema`), ordenadas por id, seguidas de una entrada
`negocio` por formulario Svelte en el orden de la matriz, una `pagina` por página propia y una `tema` por tema propio.
Lo demás del fichero (`_comment`, `version`) se conserva.

Nombres (decisión): la carpeta, el `id` del manifiesto (el `FORM_ID` de vite y de `build-form.js`) y el token de la
página en la aplicación son el mismo `token_pagina(id)` de `aplicaciones.py` (`frm_2_revisarJefe` -> `frm2RevisarJefe`);
el recurso, `recurso_pagina(id)`. Así coinciden con la URL del form mapping del `.proc` y con el descriptor de la app.

Campos (decisiones):
- `ruta` = el «Input del contrato» de la matriz (`decisionInput.resultado`); `grupo` = el input sin el sufijo
  `Input` (`decision`) o `datos` para un input simple; `etiqueta` = la columna «Campo».
- `tipo`: el del contrato reducido a lo que pinta la galería (LONG -> INTEGER; LOCALDATE, LOCALDATETIME,
  OFFSETDATETIME -> DATE); `tipoContrato` guarda el original, que decide cómo viaja en el cuerpo.
- `constraint`: las opciones del control (`Radio buttons (a / b)` -> `∈ {a, b}`), el mensaje de la constraint que
  espeja la validación, lo «propio de UI» y la anotación del catálogo (`∈ catálogo <codigo>`, `depende: <ruta>`).
- Catálogo `param_*` -> `codigo_de_referencia` (`parametros.py`): un parámetro `lista` o `tramo-cascada` es la lista
  del campo (`catalogo`); uno de valor en un campo numérico es su tope (`tope`). Una derivada de la semilla (§2.18)
  se nombra `param_T.<nivel>` (una lista) o `param_T.<campo>` / `param_L.<campo>` (como un valor); que la semilla la
  siembre lo comprueba `validar/parametros.py`. `depende` es la ruta del campo que
  nombra la columna «Depende de» (por su nombre o su ruta) o, si no es un campo, el texto tal cual (dato del caso).
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from generadores.escribir.aplicaciones import recurso_pagina, temas, token_pagina
from generadores.escribir.e2e import RUTA as E2E_PARAMETROS, e2e_de_parametros
from generadores.escribir.parametros import REF_CATALOGO, codigo_de_referencia, es_nivel
from generadores.leer.matriz import _camel, es_interna

FORMS = Path("frontend") / "src" / "forms"
MANIFIESTO = Path("frontend") / "forms.manifest.json"
GENERADO = "generado"
# Ficheros del esqueleto (más `<Nombre>.svelte`): editables, se escriben una sola vez.
ESQUELETO = ("index.html", "main.ts", "textos.ts", "validacion.ts", "pantalla.test.ts")
# El esqueleto de un tema propio: su hoja de estilos (las imágenes las añade el proyecto en `images/`).
ESQUELETO_TEMA = ("tema.css",)
# Tipos del manifiesto que reescribe `generar` (los demás son técnicos o de administración y se conservan).
TIPOS_GENERADOS = ("negocio", "pagina", "tema")
INSTANCIACION = "(instanciacion)"
INSTANCIACION_PRINCIPAL = "frm_instanciacion"

# Tipo de input del contrato -> tipo que pinta `CamposDeContrato` y tipo TypeScript del valor en el cuerpo.
TIPO_CAMPO = {"TEXT": "TEXT", "INTEGER": "INTEGER", "LONG": "INTEGER", "DECIMAL": "DECIMAL", "BOOLEAN": "BOOLEAN",
              "DATE": "DATE", "LOCALDATE": "DATE", "LOCALDATETIME": "DATE", "OFFSETDATETIME": "DATE", "FILE": "FILE"}
TIPO_TS = {"TEXT": "string", "INTEGER": "number", "LONG": "number", "DECIMAL": "number", "BOOLEAN": "boolean",
           "DATE": "string", "LOCALDATE": "string", "LOCALDATETIME": "string", "OFFSETDATETIME": "string",
           "FILE": "ArchivoSubido"}
# Tipo de input -> conversor del valor tecleado al valor del cuerpo (funciones de `contrato.ts`).
CONVERSOR = {"TEXT": "texto", "INTEGER": "entero", "LONG": "entero", "DECIMAL": "numero", "BOOLEAN": "booleano",
             "DATE": "fechaConZona", "LOCALDATE": "fecha", "LOCALDATETIME": "fechaHora", "OFFSETDATETIME": "fechaConZona",
             }
# FILE no tiene conversor: viaja como su referencia subida (`subidos[ruta]`); un BOOLEAN obligatorio usa `casilla`.
_CONVERSORES_TS = {
    "texto": ("/** Un texto; vacío o de otro tipo, `null`. */\n"
              "function texto(v: ValorDeCampo): string | null {\n"
              "  return typeof v === 'string' && v !== '' ? v : null;\n}"),
    "numero": ("/** Un número tecleado; si no, `null`. */\n"
               "function numero(v: ValorDeCampo): number | null {\n"
               "  return typeof v === 'number' && Number.isFinite(v) ? v : null;\n}"),
    "entero": ("/** Un entero: tecleado, o el código numérico de una opción de lista (`'36'`); si no, `null`. */\n"
               "function entero(v: ValorDeCampo): number | null {\n"
               "  if (typeof v === 'number') return Number.isInteger(v) ? v : null;\n"
               "  return typeof v === 'string' && /^\\d+$/.test(v) ? Number(v) : null;\n}"),
    "booleano": ("/** Una casilla; sin tocar, `null`. */\n"
                 "function booleano(v: ValorDeCampo): boolean | null {\n"
                 "  return typeof v === 'boolean' ? v : null;\n}"),
    "casilla": ("/** Una casilla obligatoria: sin marcar es `false`, no `null`. */\n"
                "function casilla(v: ValorDeCampo): boolean {\n"
                "  return v === true;\n}"),
    "fecha": ("/** Una fecha `aaaa-mm-dd` (LOCALDATE). */\n"
              "function fecha(v: ValorDeCampo): string | null {\n"
              "  return typeof v === 'string' && /^\\d{4}-\\d{2}-\\d{2}$/.test(v) ? v : null;\n}"),
    "fechaHora": ("/** Una fecha como fecha y hora local al inicio del día (LOCALDATETIME). */\n"
                  "function fechaHora(v: ValorDeCampo): string | null {\n"
                  "  return typeof v === 'string' && /^\\d{4}-\\d{2}-\\d{2}$/.test(v) ? `${v}T00:00:00` : null;\n}"),
    "fechaConZona": ("/** Una fecha como el inicio del día con el desfase local del navegador (DATE, OFFSETDATETIME). */\n"
                     "function fechaConZona(v: ValorDeCampo): string | null {\n"
                     "  if (typeof v !== 'string' || !/^\\d{4}-\\d{2}-\\d{2}$/.test(v)) return null;\n"
                     "  const minutos = -new Date(`${v}T00:00:00`).getTimezoneOffset();\n"
                     "  const signo = minutos < 0 ? '-' : '+';\n"
                     "  const abs = Math.abs(minutos);\n"
                     "  const hh = String(Math.floor(abs / 60)).padStart(2, '0');\n"
                     "  const mm = String(abs % 60).padStart(2, '0');\n"
                     "  return `${v}T00:00:00${signo}${hh}:${mm}`;\n}"),
}
_ORDEN_CONVERSORES = ("texto", "numero", "entero", "booleano", "casilla", "fecha", "fechaHora", "fechaConZona")

# Permisos REST de la página (`resources` de su `page.properties`), por tipo de formulario.
PERMISOS = {
    "tarea": ["GET|bpm/userTask", "POST|bpm/userTask", "GET|bpm/humanTask", "GET|bpm/case", "GET|system/session"],
    "instanciacion": ["GET|bpm/process", "POST|bpm/process", "GET|system/session"],
    "resumen": ["GET|bpm/case", "GET|bpm/process", "GET|system/session"],
    # Página propia de una aplicación (bandeja, «mis casos»…): lee por las extensiones de solo lectura, nunca /API/bdm.
    # `parametros/valores` lo pide `marcaEnVivo` (la marca del proyecto); sin tarea solo devuelve definiciones de cliente.
    "pagina": ["GET|system/session", "GET|identity/user", "GET|bpm/humanTask", "GET|bpm/case",
               "GET|extension/consultas", "GET|extension/parametros/valores"],
}
PERMISO_PARAMETROS = "GET|extension/parametros/valores"
# Los datos de solo lectura del caso: la extensión de lecturas del caso (`$lib/bonita/caso`), nunca `/API/bdm`.
PERMISO_CONSULTAS = "GET|extension/consultas"
TIPO_FORMULARIO = {"Task form": "tarea", "Instantiation form": "instanciacion", "Case overview": "resumen"}
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_CABECERA = ("// GENERADO por el arnés desde docs/07-bonita/contratos.md y docs/07-bonita/matriz-formularios.md.\n"
             "// NO SE EDITA A MANO: cambia la documentación y corre `tools/arnes.sh generar`. Lo propio de la pantalla\n"
             "// va en los ficheros de la carpeta del formulario (el esqueleto), que el generador no vuelve a tocar.\n")


# ------------------------------------------------------------------------------------------------- utilidades

def _js(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def _clave(nombre: str) -> str:
    return nombre if _IDENT.fullmatch(nombre) else _js(nombre)


def _objeto(d: dict) -> str:
    return "{ " + ", ".join(f"{_clave(k)}: {_js(v)}" for k, v in d.items()) + " }"


def _comentario(texto: str) -> str:
    """Texto seguro dentro de un comentario de bloque (`/* … */`): no lo cierra antes de tiempo."""
    return texto.replace("*/", "*\\/")


def _comilla(texto: str) -> str:
    """Literal TypeScript entre comillas simples."""
    return "'" + texto.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ") + "'"


def nombre_componente(id_formulario: str) -> str:
    """`frm_2_revisarJefe` -> `Frm2RevisarJefe` (el `<Nombre>.svelte` del esqueleto): el token con mayúscula inicial."""
    token = token_pagina(id_formulario)
    return token[:1].upper() + token[1:]


def es_esqueleto(rel: str) -> bool:
    """¿Es `rel` (relativa al proyecto, con `/`) un fichero del esqueleto editable de un formulario, de una página propia
    o de un tema (o la prueba e2e de la app de parámetros, `escribir/e2e.py`)?"""
    if rel == E2E_PARAMETROS:
        return True
    partes = rel.split("/")
    if len(partes) != 5 or partes[:3] != ["frontend", "src", "forms"]:
        return False
    return (partes[4] in ESQUELETO or partes[4] in ESQUELETO_TEMA
            or partes[4] == f"{partes[3][:1].upper()}{partes[3][1:]}.svelte")


# ------------------------------------------------------------------------------------------- contrato del form

def _contrato_de(form: dict, procesos: list[dict]) -> tuple[dict | None, dict]:
    """`(proceso, contrato)` del formulario. Instanciación: `frm_instanciacion` es la del pool principal y
    `frm_instanciacion_<Pool>` la de ese pool; tarea: el pool con esa tarea humana; overview: sin contrato."""
    tipo = form["tipo"]
    if tipo == "Instantiation form":
        if form["id"] == INSTANCIACION_PRINCIPAL:
            p = procesos[0] if procesos else None
        else:
            nombre = form["id"].removeprefix(f"{INSTANCIACION_PRINCIPAL}_")
            p = next((x for x in procesos if x["nombre"] == nombre), None)
        if p is None or INSTANCIACION not in p.get("contratos", {}):
            raise ValueError(f"formulario «{form['id']}»: no hay un contrato de instanciación para él (el pool "
                             "principal para `frm_instanciacion`, el pool <P> para `frm_instanciacion_<P>`)")
        return p, p["contratos"][INSTANCIACION]
    if tipo == "Task form":
        for p in procesos:
            humanas = {n["id"] for n in p.get("nodos", []) if n.get("tipo") == "humana"}
            if form.get("tarea") in humanas and form["tarea"] in p.get("contratos", {}):
                return p, p["contratos"][form["tarea"]]
        raise ValueError(f"formulario «{form['id']}»: la tarea «{form.get('tarea')}» no es una tarea humana con "
                         "contrato en contratos.md")
    return _pool_del_resumen(form, procesos), {"inputs": [], "restricciones": []}


def _pool_del_resumen(form: dict, procesos: list[dict]) -> dict | None:
    """El pool de un overview por su fila de la matriz: el pool que nombra la columna «Tarea BPMN» (p. ej.
    «(overview de `Pool`)») o el sufijo del id (`frm_overview_<Pool>`); si no nombra ninguno, el pool principal (el
    form mapping del overview es del pool principal)."""
    nombres = {p["nombre"]: p for p in procesos}
    for palabra in re.findall(r"\w+", form.get("tarea") or ""):
        if palabra in nombres:
            return nombres[palabra]
    sufijo = form["id"].removeprefix("frm_overview_")
    if sufijo != form["id"] and sufijo in nombres:
        return nombres[sufijo]
    return procesos[0] if procesos else None


def _grupo(input_: dict) -> str:
    if not input_["hijos"]:
        return "datos"
    return re.sub(r"Input$", "", input_["nombre"]) or input_["nombre"]


def _opciones(control: str | None) -> list[str]:
    """`Radio buttons (aprobar / rechazar)` -> `["aprobar", "rechazar"]`."""
    m = re.search(r"\(([^)]*/[^)]*)\)", control or "")
    return [o.strip() for o in m.group(1).split("/") if o.strip()] if m else []


def _widget(control: str | None) -> str | None:
    c = (control or "").lower()
    for claves, w in ((("ficha", "radio"), "fichas"), (("autocomplet",), "autocompletar"),
                      (("desplegable", "select", "dropdown", "combo"), "desplegable")):
        if any(k in c for k in claves):
            return w
    return None


def _validacion(texto: str | None, restricciones: dict[str, dict]) -> list[str]:
    out = []
    for parte in (texto or "").split(";"):
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"espeja\s+(\w+)", parte)
        if m:
            r = restricciones.get(m.group(1))
            if r and r.get("mensaje"):
                out.append(r["mensaje"])
            continue
        parte = re.sub(r"^propia de UI\s*:\s*", "", parte, flags=re.IGNORECASE)
        if parte:
            out.append(parte)
    return out


def _campos(form: dict, contrato: dict, parametros_negocio: list[dict]) -> tuple[list[dict], list[dict]]:
    """`(campos, lecturas)`: los campos de la matriz que escriben en el contrato, en orden, ya resueltos contra sus
    inputs; y los de solo lectura."""
    inputs = {i["nombre"]: i for i in contrato.get("inputs", [])}
    restricciones = {r["nombre"]: r for r in contrato.get("restricciones", [])}
    tipos_param = {p["id"]: p["tipo"] for p in parametros_negocio}
    filas_param = {p["id"]: p for p in parametros_negocio}
    campos, lecturas, vistas = [], [], {}
    for c in form.get("campos", []):
        escribe = c.get("escribe")
        if not escribe:
            if c.get("lee"):
                m = re.fullmatch(r"[A-Z]\w*\.(\w+)", c["lee"].strip())
                lecturas.append({"etiqueta": c["campo"], "lee": c["lee"], "atributo": m.group(1) if m else None})
            continue
        nombre_input, _, hijo = escribe.partition(".")
        i = inputs.get(nombre_input)
        if i is not None and i.get("solo_lectura") and not hijo:
            # La fila documenta el input de solo lectura entero (p. ej. «Oculto (lo llena el formulario)»): no es un
            # campo editable; lo pone la pantalla y llega por `externos`, igual que sin fila (integración, compras).
            continue
        camino = _camino(i, hijo) if i else None
        if camino is None or camino[-1]["hijos"]:
            raise ValueError(f"formulario «{form['id']}», campo «{c['campo']}»: escribe «{escribe}», que no es un "
                             f"input (ni el hijo de un input COMPLEX) del contrato «{form.get('contrato')}»")
        if escribe in vistas:
            raise ValueError(f"formulario «{form['id']}»: los campos «{vistas[escribe]}» y «{c['campo']}» escriben "
                             f"el mismo input «{escribe}»")
        vistas[escribe] = c["campo"]
        hoja = camino[-1]
        tipo = hoja["tipo"]
        if tipo not in TIPO_CAMPO:
            raise ValueError(f"formulario «{form['id']}», campo «{c['campo']}»: el input «{escribe}» es {tipo}; "
                             "un campo escribe un dato simple o el hijo de un COMPLEX")
        obligatorio = bool(c.get("obligatorio"))
        campo = {"ruta": escribe, "grupo": _grupo(i), "nombre": hoja["nombre"], "etiqueta": c["campo"],
                 "tipo": TIPO_CAMPO[tipo], "tipoContrato": tipo, "multiple": any(n["multiple"] for n in camino),
                 "obligatorio": "sí" if obligatorio else "no", "requeridoSiempre": obligatorio}
        partes = []
        opciones = _opciones(c.get("control"))
        if opciones:
            partes.append("∈ {" + ", ".join(opciones) + "}")
        partes += _validacion(c.get("validacion"), restricciones)
        anotacion: dict = {}
        param = next(iter(REF_CATALOGO.findall(c.get("catalogo") or "")), None)
        if param:
            codigo = codigo_de_referencia(param)
            base, _, sufijo = param.partition(".")
            # Una derivada de la semilla (§2.18): un nivel es una LISTA; un campo, un PARAMETRO (como un `valor`).
            tipo_param = ("lista" if es_nivel(param, filas_param.get(base)) else "valor") if sufijo \
                else tipos_param.get(param)
            if tipo_param in ("lista", "tramo-cascada") or TIPO_CAMPO[tipo] not in ("INTEGER", "DECIMAL"):
                anotacion["catalogo"] = codigo
                partes.append(f"∈ catálogo {codigo}")
                w = _widget(c.get("control"))
                if w:
                    anotacion["widget"] = w
                    partes.append(f"widget: {w}")
            else:
                anotacion["tope"] = codigo
                partes.append(f"tope: {codigo}")
        campo["constraint"] = "; ".join(partes)
        campo["_depende"] = c.get("depende")
        campo.update(anotacion)
        campos.append(campo)
    _obligatorios_escritos(form, contrato, campos)
    # `depende`: la ruta del campo que nombra la columna (por su nombre visible o por su ruta), o el texto tal cual.
    por_nombre = {x["etiqueta"].lower(): x["ruta"] for x in campos} | {x["ruta"].lower(): x["ruta"] for x in campos}
    for x in campos:
        dep = x.pop("_depende")
        if dep and ("catalogo" in x or "tope" in x):
            ruta = por_nombre.get(dep.strip().lower(), dep.strip())
            x["depende"] = ruta
            x["constraint"] = "; ".join(p for p in (x["constraint"], f"depende: {ruta}") if p)
    return campos, lecturas


def _obligatorios_escritos(form: dict, contrato: dict, campos: list[dict]) -> None:
    """Todo input (o hijo de un COMPLEX) obligatorio del contrato lo escribe un campo de la matriz marcado «sí».

    El cuerpo lleva a `null` lo que la matriz no usa; para un input obligatorio eso es un 400 seguro del motor (la
    constraint `mandatory_<ruta>` que genera `proc/contratos.py`), que nadie vería hasta que un usuario envía. Por eso
    es un error del generador, no un `null`."""
    por_ruta = {c["ruta"]: c for c in campos}
    ctr = form.get("contrato")
    for i in contrato.get("inputs", []):
        n = i["nombre"]
        if _externo(i, campos):
            continue  # solo lectura sin campos: lo pone la pantalla (`externos`), no la matriz
        # Los hijos de un COMPLEX opcional no tienen por qué llegar (ni con obligatoriedad propia: «si llega el padre»).
        hojas = (_hojas_obligatorias(i, n) if i.get("obligatorio") else []) if i["hijos"] else [(n, i)]
        if i.get("obligatorio") and not any(r == n or r.startswith(n + ".") for r in por_ruta):
            raise ValueError(f"formulario «{form['id']}»: el input obligatorio «{n}» del contrato «{ctr}» no lo "
                             "escribe ningún campo de la matriz; el formulario lo enviaría a null y el motor "
                             "rechazaría el envío. Añade el campo en matriz-formularios.md o marca el input como no "
                             "obligatorio en contratos.md")
        for ruta, nodo in hojas:
            if not nodo.get("obligatorio"):
                continue
            c = por_ruta.get(ruta)
            if c is None:
                raise ValueError(f"formulario «{form['id']}»: el input obligatorio «{ruta}» del contrato «{ctr}» "
                                 "no lo escribe ningún campo de la matriz; el formulario lo enviaría a null y el "
                                 "motor rechazaría el envío. Añade el campo en matriz-formularios.md o marca el "
                                 "input como no obligatorio en contratos.md")
            if not c["requeridoSiempre"]:
                raise ValueError(f"formulario «{form['id']}», campo «{c['etiqueta']}»: escribe el input "
                                 f"obligatorio «{ruta}» del contrato «{ctr}»; su «Obligatorio» en la matriz debe "
                                 "ser «sí» (vacío, el formulario dejaría enviarlo a null)")


def _camino(i: dict, resto: str) -> list[dict] | None:
    """Los nodos del input `i` hasta la ruta relativa `resto` (`""` = el propio input; `b.c` = un nieto)."""
    camino = [i]
    for parte in resto.split(".") if resto else []:
        h = next((x for x in camino[-1]["hijos"] if x["nombre"] == parte), None)
        if h is None:
            return None
        camino.append(h)
    return camino


def _hojas_obligatorias(nodo: dict, ruta: str) -> list[tuple[str, dict]]:
    """(ruta, hoja) de los hijos simples bajo `nodo` (sin COMPLEX), descendiendo solo por los hijos obligatorios: un
    hijo obligatorio de un padre opcional no tiene por qué llegar (semántica «si llega el padre»)."""
    out = []
    for h in nodo["hijos"]:
        r = f"{ruta}.{h['nombre']}"
        if h["hijos"]:
            if h.get("obligatorio"):
                out += _hojas_obligatorias(h, r)
        else:
            out.append((r, h))
    return out


def _usado(ruta: str, campos: list[dict]) -> bool:
    return any(c["ruta"] == ruta or c["ruta"].startswith(ruta + ".") for c in campos)


def _externo(i: dict, campos: list[dict]) -> bool:
    """Input de solo lectura que ningún campo escribe: lo rellena la pantalla (p. ej. desde el módulo de
    parámetros) y llega por `externos` en `cuerpoDelContrato`."""
    return bool(i.get("solo_lectura")) and not _usado(i["nombre"], campos)


# ------------------------------------------------------------------------------------------------ contrato.ts

def _tipo_valor(nodo: dict) -> str:
    base = TIPO_TS[nodo["tipo"]]
    return f"{base}[]" if nodo["multiple"] else base


def _nombre_interfaz(input_: dict, prefijo: str = "") -> str:
    return "Entrada" + prefijo + _camel(input_["nombre"], True)


def _interfaces(nodo: dict, prefijo: str = "") -> list[str]:
    """Las interfaces TS de un input COMPLEX y de sus hijos COMPLEX (anidados), en ese orden."""
    nombre = _nombre_interfaz(nodo, prefijo)
    lineas = [f"/** Input COMPLEX `{nodo['nombre']}`{' (múltiple)' if nodo['multiple'] else ''}. */",
              f"export interface {nombre} {{"]
    for h in nodo["hijos"]:
        t = (_nombre_interfaz(h, nombre.removeprefix("Entrada")) + ("[]" if h["multiple"] else "")) if h["hijos"] \
            else _tipo_valor(h)
        lineas.append(f"  {_clave(h['nombre'])}: {t} | null;")
    lineas += ["}", ""]
    for h in nodo["hijos"]:
        if h["hijos"]:
            lineas += _interfaces(h, nombre.removeprefix("Entrada"))
    return lineas


def _tiene_file(nodo: dict) -> bool:
    return nodo["tipo"] == "FILE" or any(_tiene_file(h) for h in nodo["hijos"])


def contrato_ts(form: dict, proceso: dict | None, contrato: dict, campos: list[dict], lecturas: list[dict]) -> str:
    inputs = contrato.get("inputs", [])
    tipo = TIPO_FORMULARIO.get(form["tipo"], "resumen")
    hay_archivo = any(_tiene_file(i) for i in inputs)
    externos = [i["nombre"] for i in inputs if _externo(i, campos)]
    por_ruta = {c["ruta"]: c for c in campos}
    usados: set[str] = set()

    def valor(nodo: dict, ruta: str) -> str:
        """La expresión del valor de una hoja usada: FILE, su referencia subida; BOOLEAN obligatorio, `false` sin
        marcar; el resto, su conversor."""
        if nodo["tipo"] == "FILE":
            usados.add("subidos")
            v = f"subidos[{_js(ruta)}] ?? null"
        else:
            nombre = "casilla" if nodo["tipo"] == "BOOLEAN" and por_ruta[ruta]["requeridoSiempre"] \
                else CONVERSOR[nodo["tipo"]]
            usados.update((nombre, "valores"))
            v = f"{nombre}(valores[{_js(ruta)}])"
        if nodo["multiple"]:
            usados.add("lista")
            return f"lista({v})"
        return v

    def nodo_cuerpo(nodo: dict, ruta: str, sangria: str) -> list[str]:
        """Las líneas del valor de `nodo` en el cuerpo: `null` si ningún campo lo usa; una hoja, su valor; un
        COMPLEX, su objeto (en una lista de uno si es múltiple) con sus hijos a cualquier profundidad."""
        if not _usado(ruta, campos):
            return [f"{sangria}{_clave(nodo['nombre'])}: null,"]
        if not nodo["hijos"]:
            return [f"{sangria}{_clave(nodo['nombre'])}: {valor(nodo, ruta)},"]
        abre, cierra = ("[{", "}],") if nodo["multiple"] else ("{", "},")
        out = [f"{sangria}{_clave(nodo['nombre'])}: {abre}"]
        for h in nodo["hijos"]:
            out += nodo_cuerpo(h, f"{ruta}.{h['nombre']}", sangria + "  ")
        return out + [f"{sangria}{cierra}"]

    cuerpo: list[str] = []
    if not inputs:
        cuerpo.append("  return {};")
    else:
        cuerpo.append("  return {")
        for i in inputs:
            n = i["nombre"]
            if n in externos:
                cuerpo.append(f"    {_clave(n)}: externos.{n} ?? null,")
            else:
                cuerpo += nodo_cuerpo(i, n, "    ")
        cuerpo.append("  };")

    lineas = [_CABECERA]
    if hay_archivo:
        lineas.append("import type { ArchivoSubido } from '$lib/bonita/archivos';")
    lineas.append("import type { Lectura } from '$lib/bonita/caso';")
    if usados & {"valores"}:
        lineas.append("import type { ValorDeCampo, ValoresDelFormulario } from '$lib/ui/valores';")
    else:
        lineas.append("import type { ValoresDelFormulario } from '$lib/ui/valores';")
    lineas.append("")
    identidad = {"id": form["id"], "pagina": token_pagina(form["id"]), "tipo": tipo,
                 "tarea": form.get("tarea") if tipo == "tarea" else None, "contrato": form.get("contrato"),
                 "proceso": proceso["nombre"] if proceso else None, "version": proceso["version"] if proceso else None}
    lineas += ["/** Identidad del formulario: su id en la matriz, su página, su tarea, su contrato y su proceso. */",
               f"export const FORMULARIO = {_objeto(identidad)} as const;", ""]
    lineas += ["/** Todos los inputs del contrato, en su orden: el cuerpo los lleva siempre. */",
               f"export const ENTRADAS = [{', '.join(_js(i['nombre']) for i in inputs)}] as const;", ""]
    for i in inputs:
        if i["hijos"]:
            lineas += _interfaces(i)
    lineas.append("/** El cuerpo que se envía al motor (`execution` / `instantiation`). */")
    if inputs:
        lineas.append("export type CuerpoDelContrato = {")
        for i in inputs:
            t = _nombre_interfaz(i) + ("[]" if i["multiple"] else "") if i["hijos"] else _tipo_valor(i)
            lineas.append(f"  {_clave(i['nombre'])}: {t} | null;")
        lineas.append("};")
    else:
        lineas.append("export type CuerpoDelContrato = { [entrada: string]: never };")
    lineas += ["", "/** El cuerpo con todo input a `null`. */",
               "export const CUERPO_VACIO: CuerpoDelContrato = {"]
    lineas += [f"  {_clave(i['nombre'])}: null," for i in inputs]
    lineas += ["};", ""]
    lineas += ["/** Un campo del contrato, con la forma que consume `CamposDeContrato`. */",
               "export interface CampoDeContrato {",
               "  readonly ruta: string;", "  readonly grupo: string;", "  readonly nombre: string;",
               "  /** La columna «Campo» de la matriz de formularios. */", "  readonly etiqueta: string;",
               "  readonly tipo: 'TEXT' | 'DECIMAL' | 'INTEGER' | 'BOOLEAN' | 'DATE' | 'FILE';",
               "  /** El tipo del input en el contrato (decide cómo viaja en el cuerpo). */",
               "  readonly tipoContrato: string;", "  readonly multiple: boolean;", "  readonly obligatorio: string;",
               "  readonly requeridoSiempre: boolean;", "  readonly constraint: string;",
               "  readonly catalogo?: string;",
               "  readonly widget?: 'fichas' | 'desplegable' | 'autocompletar';",
               "  readonly depende?: string;", "  readonly tope?: string;", "}", ""]
    lineas.append("/** Los campos de la matriz que escriben en el contrato, en el orden de la matriz. */")
    if campos:
        lineas.append("export const CAMPOS: readonly CampoDeContrato[] = [")
        lineas += [f"  {_objeto(c)}," for c in campos]
        lineas.append("];")
    else:
        lineas.append("export const CAMPOS: readonly CampoDeContrato[] = [];")
    lineas += ["", "/**", " * Los datos de solo lectura del caso que la pantalla muestra («Datos que carga al abrir»): `atributo` es el del",
               " * objeto raíz del caso que devuelve la extensión de lecturas del caso (`$lib/bonita/caso`); `null` si `lee`",
               " * no es `Objeto.atributo`.", " */"]
    if lecturas:
        lineas.append("export const LECTURAS: readonly Lectura[] = [")
        lineas += [f"  {_objeto(x)}," for x in lecturas]
        lineas.append("];")
    else:
        lineas.append("export const LECTURAS: readonly Lectura[] = [];")
    lineas.append("")
    # Conversores usados, en orden fijo.
    for n in _ORDEN_CONVERSORES:
        if n in usados:
            lineas += [_CONVERSORES_TS[n], ""]
    if "lista" in usados:
        lineas += ["/** Un input simple múltiple: el valor como lista de uno, o vacía. */",
                   "function lista<T>(v: T | null): T[] {", "  return v === null ? [] : [v];", "}", ""]
    p_valores = "valores" if "valores" in usados else "_valores"
    p_subidos = "subidos" if "subidos" in usados else "_subidos"
    tipo_subidos = "ArchivoSubido" if hay_archivo else "never"
    lineas += ["/**",
               " * El cuerpo del contrato desde los valores del formulario (por ruta) y los archivos ya subidos (por ruta, de",
               " * `subirArchivosDe`). Lleva TODO input del contrato: el que la matriz no usa va a `null`, porque el motor",
               " * responde 400 si falta uno. Un FILE viaja como su referencia subida `{ filename, tempPath, contentType }`.",
               *([f" * Los inputs de solo lectura sin campos ({', '.join(externos)}) los pone la pantalla en `externos`."]
                 if externos else []),
               " */",
               f"export function cuerpoDelContrato(\n  {p_valores}: ValoresDelFormulario,\n"
               f"  {p_subidos}: Readonly<Record<string, {tipo_subidos}>> = {{}},\n"
               + ("  externos: Partial<CuerpoDelContrato> = {},\n" if externos else "")
               + "): CuerpoDelContrato {"]
    lineas += cuerpo
    lineas += ["}", ""]
    return "\n".join(lineas)


# ------------------------------------------------------------------------------------------------- esquema.ts

def _zod_hoja(nodo: dict, campo: dict | None) -> str:
    if campo is None:
        return "z.null()"
    t = nodo["tipo"]
    obligatorio = campo["requeridoSiempre"]
    err = "{ required_error: OBLIGATORIO, invalid_type_error: OBLIGATORIO }"
    opciones = _opciones_de_constraint(campo["constraint"])
    if opciones and t == "TEXT":
        base = f"z.enum([{', '.join(_js(o) for o in opciones)}], {{ errorMap: () => ({{ message: OPCION }}) }})"
    elif t == "TEXT" or t in ("DATE", "LOCALDATE", "LOCALDATETIME", "OFFSETDATETIME"):
        base = f"z.string({err})" + (".min(1, OBLIGATORIO)" if obligatorio else "")
    elif t in ("INTEGER", "LONG"):
        base = f"z.number({err}).int(ENTERO)"
    elif t == "DECIMAL":
        base = f"z.number({err})"
    elif t == "BOOLEAN":
        base = f"z.boolean({err})"
    else:  # FILE: la referencia que devuelve la subida
        base = f"z.object({{ filename: z.string(), tempPath: z.string(), contentType: z.string() }}, {err})"
    if nodo["multiple"]:
        base = f"z.array({base}, {err})" + (".min(1, OBLIGATORIO)" if obligatorio else "")
    return base if obligatorio else f"{base}.nullable()"


def _opciones_de_constraint(constraint: str) -> list[str]:
    m = re.match(r"∈\s*\{([^}]*)\}", constraint)
    return [o.strip() for o in m.group(1).split(",") if o.strip()] if m else []


def esquema_ts(contrato: dict, campos: list[dict]) -> str:
    por_ruta = {c["ruta"]: c for c in campos}
    lineas = [_CABECERA, "import { z } from 'zod';", "import type { CuerpoDelContrato } from './contrato';", "",
              "const OBLIGATORIO = 'Este dato es obligatorio.';",
              "const OPCION = 'Elija una de las opciones.';",
              "const ENTERO = 'Escriba un número entero.';", "",
              "/**",
              " * El esquema del cuerpo del contrato: la obligatoriedad de la matriz, las opciones cerradas y los enteros.",
              " * Lo que la matriz no usa debe ir a `null`. Las constraints del contrato las valida el motor al enviar.",
              " */",
              "export const esquema = z.object({"]
    def nodo_zod(nodo: dict, ruta: str, sangria: str) -> list[str]:
        if not _usado(ruta, campos):
            return [f"{sangria}{_clave(nodo['nombre'])}: z.null(),"]
        if not nodo["hijos"]:
            return [f"{sangria}{_clave(nodo['nombre'])}: {_zod_hoja(nodo, por_ruta.get(ruta))},"]
        out = [f"{sangria}{_clave(nodo['nombre'])}: {'z.array(' if nodo['multiple'] else ''}z.object({{"]
        for h in nodo["hijos"]:
            out += nodo_zod(h, f"{ruta}.{h['nombre']}", sangria + "  ")
        cierre = (")" + (".min(1, OBLIGATORIO)" if nodo["obligatorio"] else "")) if nodo["multiple"] else ""
        return out + [f"{sangria}}}){cierre},"]

    for i in contrato.get("inputs", []):
        if _externo(i, campos):
            # Lo pone la pantalla; sus constraints las valida el motor.
            lineas.append(f"  {_clave(i['nombre'])}: z.custom<CuerpoDelContrato[{_js(i['nombre'])}]>(),")
        else:
            lineas += nodo_zod(i, i["nombre"], "  ")
    lineas.append("}) satisfies z.ZodType<CuerpoDelContrato>;")
    lineas += ["", "/** Los mensajes, para las reglas propias de la pantalla (`validacion.ts`). */",
               "export const MENSAJES = { OBLIGATORIO, OPCION, ENTERO } as const;", ""]
    return "\n".join(lineas)


# ------------------------------------------------------------------------------------------------- manifiesto

def _familia(form: dict, matriz: dict | None = None) -> str:
    """`interno` sin visibilidad por familia o con la familia interna (la que declara «Familia interna» en la matriz;
    sin esa línea, `interna`); `cliente` para las demás familias."""
    fam = form.get("familia_actores")
    return "interno" if not (fam or "").strip() or es_interna(fam, matriz) else "cliente"


def entrada_manifiesto(form: dict, campos: list[dict], lecturas: list[dict] | None = None,
                       matriz: dict | None = None) -> dict:
    tipo = TIPO_FORMULARIO.get(form["tipo"], "resumen")
    permisos = list(PERMISOS[tipo])
    if any("catalogo" in c or "tope" in c for c in campos):
        permisos.append(PERMISO_PARAMETROS)
    if lecturas:
        permisos.append(PERMISO_CONSULTAS)
    que = {"tarea": f"de la tarea {form.get('tarea')}", "instanciacion": "de inicio del proceso",
           "resumen": "de resumen del caso"}[tipo]
    contrato = f" (contrato {form['contrato']})" if form.get("contrato") else ""
    return {"id": token_pagina(form["id"]), "tipo": "negocio", "custompage": recurso_pagina(form["id"]),
            "displayName": form.get("titulo") or form["id"],
            "descripcion": f"Pantalla {que}{contrato}: formulario {form['id']} de la matriz de formularios.",
            "familia": _familia(form, matriz), "userTask": form.get("tarea") if tipo == "tarea" else None,
            "contrato": form.get("contrato"), "permisos": permisos}


def _familia_de_app(app: dict | None, matriz: dict | None) -> str:
    """`interno` / `cliente` de una aplicación, por su familia de actores (como `_familia` de un formulario)."""
    fam = (app or {}).get("familia_actores")
    return "interno" if not (fam or "").strip() or es_interna(fam, matriz) else "cliente"


def entrada_pagina(pagina: dict, matriz: dict) -> dict:
    """La entrada `tipo: pagina` de una página propia: familia de su primera aplicación y los permisos de lectura."""
    apps = {a["token"]: a for a in matriz.get("aplicaciones", [])}
    return {"id": pagina["token"], "tipo": "pagina", "custompage": pagina["recurso"],
            "displayName": pagina.get("titulo") or pagina["alias"],
            "descripcion": f"Página «{pagina['alias']}» de la aplicación {', '.join(pagina['aplicaciones'])} "
                           f"(matriz de formularios): código del proyecto.",
            "familia": _familia_de_app(apps.get(pagina["aplicaciones"][0]), matriz), "userTask": None,
            "contrato": None, "permisos": list(PERMISOS["pagina"])}


def entrada_tema(tema: str, matriz: dict) -> dict:
    """La entrada `tipo: tema` de un tema propio (`custompage_<x>`): sin permisos REST."""
    apps = [a["token"] for a in matriz.get("aplicaciones", []) if a.get("tema") == tema]
    return {"id": tema.removeprefix("custompage_"), "tipo": "tema", "custompage": tema,
            "displayName": f"Tema {tema.removeprefix('custompage_')}",
            "descripcion": f"Tema de la aplicación {', '.join(apps)} (matriz de formularios): Bootstrap 3 y la hoja "
                           f"propia del proyecto.",
            "userTask": None, "contrato": None, "permisos": []}


def manifiesto_bytes(existente: bytes | None, entradas: list[dict]) -> bytes:
    """El manifiesto: lo del existente que no son formularios, sus entradas técnicas (las que no son `negocio`,
    `pagina` ni `tema`) ordenadas por id y las generadas de `entradas`, en su orden. Determinista e idempotente."""
    if existente is None:
        datos: dict = {"version": 2, "formularios": []}
    else:
        try:
            datos = json.loads(existente.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as e:
            raise ValueError(f"{MANIFIESTO.as_posix()}: no es JSON válido ({e}); no se puede fusionar") from e
        if not isinstance(datos, dict) or not isinstance(datos.get("formularios", []), list):
            raise ValueError(f"{MANIFIESTO.as_posix()}: debe ser un objeto con la lista «formularios»")
    tecnicas = [f for f in datos.get("formularios", [])
                if isinstance(f, dict) and f.get("tipo") not in TIPOS_GENERADOS]
    ids = {e["id"] for e in entradas}
    for t in tecnicas:
        if t.get("id") in ids:
            raise ValueError(f"{MANIFIESTO.as_posix()}: la entrada técnica «{t['id']}» tiene el id de la página de "
                             "un formulario, de una página propia o de un tema de la matriz; renombre una de las dos")
    datos = dict(datos)
    datos["formularios"] = sorted(tecnicas, key=lambda f: str(f.get("id"))) + entradas
    return (json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# -------------------------------------------------------------------------------------------------- esqueleto

def _accion(form: dict) -> str:
    """«Enviar (fija solicitudInput).» -> «Enviar»: la acción principal de la columna «Acciones»."""
    texto = re.split(r"[(.;]", form.get("acciones") or "", maxsplit=1)[0].strip()
    return texto or "Enviar"


def esqueleto(form: dict, campos: list[dict], lecturas: list[dict] | None = None,
              solo_accion: bool = False) -> dict[str, str]:
    """Los ficheros editables del formulario (nombre -> contenido). `solo_accion`: el contrato no tiene inputs y la
    matriz no tiene campos (p. ej. la instanciación que solo inicia el caso): la pantalla es la acción, sin campos."""
    nombre = nombre_componente(form["id"])
    titulo = form.get("titulo") or form["id"]
    tipo = TIPO_FORMULARIO.get(form["tipo"], "resumen")
    out = {
        "index.html": ("<!doctype html>\n<html lang=\"es\">\n  <head>\n    <meta charset=\"UTF-8\" />\n"
                       "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
                       f"    <title>{html.escape(titulo)}</title>\n  </head>\n  <body>\n    <div id=\"app\"></div>\n"
                       "    <script type=\"module\" src=\"./main.ts\"></script>\n  </body>\n</html>\n"),
        "main.ts": ("import { mount } from 'svelte';\n"
                    "// Los tokens de identidad visual: el tema de la Living Application los sobreescribe en runtime.\n"
                    "import '$lib/estilos/tokens.css';\n"
                    "// La marca del proyecto (nombre, logo, colores) es un parámetro del módulo: se aplica sobre los tokens.\n"
                    "import '$lib/estilos/marcaEnVivo';\n"
                    "// Embebida en una bandeja, la pantalla no repite su cabecera.\n"
                    "import '$lib/estilos/enMarco';\n"
                    f"import {nombre} from './{nombre}.svelte';\n\n"
                    "const destino = document.getElementById('app');\n"
                    "if (!destino) throw new Error('No existe el contenedor #app');\n\n"
                    f"export default mount({nombre}, {{ target: destino }});\n"),
        "textos.ts": (f"/**\n * Textos de la pantalla «{_comentario(titulo)}» (`{form['id']}`). Este fichero es del proyecto: el arnés lo escribió\n"
                      " * una vez y no lo vuelve a tocar.\n */\n"
                      "export const TEXTOS = {\n"
                      f"  titulo: {_comilla(titulo)},\n"
                      f"  accion: {_comilla(_accion(form))},\n"
                      "  enviado: 'Listo',\n"
                      "  enviadoDetalle: 'Recibimos sus datos.',\n"
                      "  error: 'No se pudo enviar',\n"
                      "  sinContexto: 'La pantalla no se abrió desde su tarea o su proceso en el portal.',\n"
                      "  errorGenerico: 'Ocurrió un error inesperado.',\n"
                      "  cargando: 'Cargando…',\n"
                      "  errorLectura: 'No se pudieron cargar los datos del caso',\n"
                      "  sinDatosNoSeEnvia: 'Sin los datos del caso no se puede enviar. Vuelva a abrir la pantalla.',\n"
                      "  subidaFallida: 'No se pudo subir un archivo; no se envió nada.',\n"
                      "} as const;\n\n"
                      "/** Etiquetas propias por ruta del contrato; sin una, se usa la «Campo» de la matriz (`generado/contrato.ts`). */\n"
                      "export const ETIQUETAS: Readonly<Record<string, string>> = {};\n"),
        "validacion.ts": ("/**\n * Validación de la pantalla antes de enviar. El esquema generado (`generado/esquema.ts`) espeja la matriz;\n"
                          " * las reglas propias de esta pantalla se añaden aquí. La verdad última es el contrato de Bonita.\n */\n"
                          "import { esquema } from './generado/esquema';\n"
                          "import type { CuerpoDelContrato } from './generado/contrato';\n\n"
                          "/** Los errores por ruta (`grupo.campo`); vacío = se puede enviar. */\n"
                          "export function erroresDe(cuerpo: CuerpoDelContrato): Record<string, string> {\n"
                          "  const resultado = esquema.safeParse(cuerpo);\n"
                          "  const errores: Record<string, string> = {};\n"
                          "  if (resultado.success) return errores;\n"
                          "  for (const problema of resultado.error.issues) {\n"
                          "    // Un input múltiple trae el índice en la ruta: el campo es el mismo para todos.\n"
                          "    const ruta = problema.path.filter((p): p is string => typeof p === 'string').join('.');\n"
                          "    if (!(ruta in errores)) errores[ruta] = problema.message;\n"
                          "  }\n"
                          "  return errores;\n"
                          "}\n"),
    }
    if solo_accion and tipo != "resumen":
        out[f"{nombre}.svelte"] = _svelte_solo_accion(form, tipo, titulo)
        out["pantalla.test.ts"] = _prueba_solo_accion(form, tipo, nombre)
    else:
        out[f"{nombre}.svelte"] = _svelte(form, tipo, titulo, campos)
        out["pantalla.test.ts"] = _prueba(form, tipo, nombre, campos, lecturas)
    return out


_LECTURAS_SVELTE = """  {#if LECTURAS.length > 0}
    {#if falloLectura}
      <Aviso tono="error" titulo={TEXTOS.errorLectura}><p>{falloLectura}</p>@BLOQUEA@</Aviso>
    {:else}
      <!-- Datos del caso de solo lectura, de la extensión de lecturas del caso. -->
      <dl class="lecturas" aria-busy={lecturas === null}>
        {#each LECTURAS as lectura, i (i)}
          <dt>{lectura.etiqueta}</dt>
          <dd data-lee={lectura.lee}>{lecturas ? lecturas[i] : TEXTOS.cargando}</dd>
        {/each}
      </dl>
    {/if}
  {/if}
"""

_ESTILO_SVELTE = """<style>
  main {
    max-inline-size: 60rem;
    margin-inline: auto;
    padding: var(--esp-5, 1.5rem);
  }

  .lecturas {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: var(--esp-2, 0.5rem) var(--esp-4, 1rem);
    margin: 0 0 var(--esp-5, 1.5rem);
  }
</style>
"""


def _hay_archivos(campos: list[dict]) -> bool:
    return any(c["tipo"] == "FILE" for c in campos)


def _svelte(form: dict, tipo: str, titulo: str, campos: list[dict] | None = None) -> str:
    campos = campos or []
    resumen = tipo == "resumen"
    archivos = _hay_archivos(campos)
    imp = []
    ui = "Aviso" if resumen else "Aviso, AccionesDeFormulario, CamposDeContrato, type ValoresDelFormulario"
    imp.append(f"  import {{ {ui} }} from '$lib/ui';")
    imp.append("  import { leerContexto } from '$lib/bonita/contexto';")
    if not resumen:
        imp.append(f"  import {{ {'ejecutarTarea' if tipo == 'tarea' else 'instanciarProceso'} }} from '$lib/bonita/cliente';")
    if archivos:
        imp.append("  import { subirArchivosDe, type ArchivoSubido } from '$lib/bonita/archivos';")
    imp.append("  import { cargarLecturas } from '$lib/bonita/caso';")
    if resumen:
        imp += ["  import { LECTURAS } from './generado/contrato';", "  import { TEXTOS } from './textos';"]
    else:
        imp += ["  import type { LectorDeValores } from '$lib/parametros/opciones';",
                "  import { CAMPOS, LECTURAS, cuerpoDelContrato, type CuerpoDelContrato } from './generado/contrato';",
                "  import { ETIQUETAS, TEXTOS } from './textos';",
                "  import { erroresDe } from './validacion';"]
    cuerpo_js = [
        "",
        "  const contexto = leerContexto();",
        "",
        "  function textoDelFallo(e: unknown): string {",
        "    return e instanceof Error ? e.message : TEXTOS.errorGenerico;",
        "  }",
        "",
        "  // Los datos de solo lectura se cargan una vez al abrir; si la lectura falla, se dice (no se pintan vacíos).",
        "  let lecturas = $state<string[] | null>(null);",
        "  let falloLectura = $state<string | null>(null);",
        "",
        "  async function cargar(): Promise<void> {",
        "    try {",
        f"      lecturas = await cargarLecturas(LECTURAS, contexto, {'true' if resumen else 'false'});",
        "    } catch (e) {",
        "      falloLectura = textoDelFallo(e);",
        "    }",
        "  }",
        "",
        "  if (LECTURAS.length > 0) void cargar();",
    ]
    if not resumen:
        id_ctx = "idTarea" if tipo == "tarea" else "idProceso"
        llamada = ("ejecutarTarea(contexto.idTarea, { ...cuerpo })" if tipo == "tarea"
                   else "instanciarProceso(contexto.idProceso, { ...cuerpo })")
        cuerpo_js += [
            "",
            "  interface Props {",
            "    /** Envía el cuerpo del contrato al motor; las pruebas inyectan un doble. */",
            "    enviar?: (cuerpo: CuerpoDelContrato) => Promise<unknown>;",
            "    /** Quién lee el módulo de parámetros (listas y topes); las pruebas inyectan un doble. */",
            "    lector?: LectorDeValores;",
            "  }",
            "",
            "  async function alMotor(cuerpo: CuerpoDelContrato): Promise<unknown> {",
            f"    if (!contexto.{id_ctx}) throw new Error(TEXTOS.sinContexto);",
            f"    return {llamada};",
            "  }",
            "",
            "  const { enviar = alMotor, lector }: Props = $props();",
            "",
            "  let valores = $state<ValoresDelFormulario>({});",
            "  let errores = $state<Record<string, string | null>>({});",
            "  let problemas = $state<Record<string, string>>({});",
            "  let estado = $state<'ocioso' | 'enviando' | 'enviado' | 'error'>('ocioso');",
            "  let fallo = $state<string | null>(null);",
            "",
            "  /** Con datos del caso que leer, no se envía mientras cargan ni si la lectura falló. */",
            "  const sinDatosDelCaso = $derived(LECTURAS.length > 0 && (lecturas === null || falloLectura !== null));",
            "",
            "  /** La etiqueta propia (`textos.ts`) o la «Campo» de la matriz. */",
            "  const etiquetas = Object.fromEntries(CAMPOS.map((c) => [c.ruta, ETIQUETAS[c.ruta] ?? c.etiqueta]));",
        ]
        if archivos:
            cuerpo_js += [
                "  /** Los campos FILE: su archivo se sube al enviar y el cuerpo lleva su referencia. */",
                "  const RUTAS_DE_ARCHIVO = new Set(CAMPOS.filter((c) => c.tipo === 'FILE').map((c) => c.ruta));",
            ]
        cuerpo_js += [
            "",
            "  async function alEnviar(evento: SubmitEvent): Promise<void> {",
            "    evento.preventDefault();",
            "    if (sinDatosDelCaso) return;",
        ]
        if archivos:
            cuerpo_js += [
                "    // Primero lo que no es archivo: no se sube nada si el resto no está listo.",
                "    const previos = erroresDe(cuerpoDelContrato(valores));",
                "    errores = Object.fromEntries(",
                "      Object.entries(previos).filter(([ruta]) => !(RUTAS_DE_ARCHIVO.has(ruta) && valores[ruta])),",
                "    );",
                "    if (Object.keys(errores).length > 0 || Object.keys(problemas).length > 0) return;",
                "    estado = 'enviando';",
                "    fallo = null;",
                "    let subidos: Record<string, ArchivoSubido>;",
                "    try {",
                "      subidos = await subirArchivosDe(CAMPOS, valores);",
                "    } catch (e) {",
                "      // Una subida fallida bloquea el envío y se dice: el contrato no recibiría el archivo.",
                "      estado = 'error';",
                "      fallo = `${TEXTOS.subidaFallida} ${textoDelFallo(e)}`;",
                "      return;",
                "    }",
                "    const cuerpo = cuerpoDelContrato(valores, subidos);",
                "    errores = erroresDe(cuerpo);",
                "    if (Object.keys(errores).length > 0) {",
                "      estado = 'ocioso';",
                "      return;",
                "    }",
            ]
        else:
            cuerpo_js += [
                "    const cuerpo = cuerpoDelContrato(valores);",
                "    errores = erroresDe(cuerpo);",
                "    if (Object.keys(errores).length > 0 || Object.keys(problemas).length > 0) return;",
                "    estado = 'enviando';",
                "    fallo = null;",
            ]
        cuerpo_js += [
            "    try {",
            "      await enviar(cuerpo);",
            "      estado = 'enviado';",
            "    } catch (e) {",
            "      estado = 'error';",
            "      fallo = textoDelFallo(e);",
            "    }",
            "  }",
        ]
    formulario = "" if resumen else (
        "  {#if estado === 'enviado'}\n"
        "    <Aviso tono=\"exito\" titulo={TEXTOS.enviado}><p>{TEXTOS.enviadoDetalle}</p></Aviso>\n"
        "  {:else}\n"
        "    {#if estado === 'error'}\n"
        "      <Aviso tono=\"error\" titulo={TEXTOS.error}><p>{fallo ?? TEXTOS.errorGenerico}</p></Aviso>\n"
        "    {/if}\n"
        "    <form id=\"formulario\" onsubmit={alEnviar} novalidate>\n"
        "      <CamposDeContrato\n"
        "        campos={CAMPOS}\n"
        "        bind:valores\n"
        "        {errores}\n"
        "        {etiquetas}\n"
        "        tarea={contexto.idTarea}\n"
        + ("        instanciacion={contexto.idProceso}\n" if tipo == "instanciacion" else "") +
        "        {lector}\n"
        "        bind:problemas\n"
        "      />\n"
        "      <AccionesDeFormulario\n"
        "        principal={TEXTOS.accion}\n"
        "        ocupado={estado === 'enviando'}\n"
        "        deshabilitado={sinDatosDelCaso}\n"
        "      />\n"
        "    </form>\n"
        "  {/if}\n")
    return ("<script lang=\"ts\">\n"
            "  /**\n"
            f"   * Pantalla «{_comentario(titulo)}» (`{form['id']}`). ESQUELETO: el arnés lo escribió una vez y es del\n"
            "   * proyecto; edítalo. Lo que sale de la documentación —los campos, el cuerpo del contrato y su esquema— está\n"
            "   * en `generado/` y se regenera con `tools/arnes.sh generar`.\n"
            "   */\n"
            + "\n".join(imp + cuerpo_js) + "\n"
            "</script>\n\n"
            "<main data-formulario={contexto.tipo}>\n"
            "  <header class=\"cabecera\">\n"
            "    <h1>{TEXTOS.titulo}</h1>\n"
            "  </header>\n\n"
            + _LECTURAS_SVELTE.replace("@BLOQUEA@", "" if resumen else "<p>{TEXTOS.sinDatosNoSeEnvia}</p>")
            + ("\n" + formulario if formulario else "") +
            "</main>\n\n" + _ESTILO_SVELTE)


def _svelte_solo_accion(form: dict, tipo: str, titulo: str) -> str:
    """La pantalla de un formulario cuyo contrato no tiene inputs ni la matriz campos (hueco 2 del MVP): la acción
    principal, que envía el cuerpo vacío (`instantiation` o `execution`). Sin `CamposDeContrato`, validación ni
    lecturas: no hay nada que capturar ni que mostrar (una lectura sería una fila de la matriz)."""
    instancia = tipo == "instanciacion"
    id_ctx = "idProceso" if instancia else "idTarea"
    llamada = "instanciarProceso(contexto.idProceso, {})" if instancia else "ejecutarTarea(contexto.idTarea, {})"
    que = "inicia el caso" if instancia else "completa la tarea"
    return ("<script lang=\"ts\">\n"
            "  /**\n"
            f"   * Pantalla «{_comentario(titulo)}» (`{form['id']}`). ESQUELETO: el arnés lo escribió una vez y es del\n"
            f"   * proyecto; edítalo. El contrato no tiene inputs: la pantalla solo {que} (envía el cuerpo vacío).\n"
            "   * Si el contrato gana inputs, la matriz lleva su tabla de campos y `generado/` se regenera con\n"
            "   * `tools/arnes.sh generar`.\n"
            "   */\n"
            "  import { Aviso, AccionesDeFormulario } from '$lib/ui';\n"
            "  import { leerContexto } from '$lib/bonita/contexto';\n"
            f"  import {{ {'instanciarProceso' if instancia else 'ejecutarTarea'} }} from '$lib/bonita/cliente';\n"
            "  import type { CuerpoDelContrato } from './generado/contrato';\n"
            "  import { TEXTOS } from './textos';\n"
            "\n"
            "  const contexto = leerContexto();\n"
            "\n"
            "  function textoDelFallo(e: unknown): string {\n"
            "    return e instanceof Error ? e.message : TEXTOS.errorGenerico;\n"
            "  }\n"
            "\n"
            "  interface Props {\n"
            "    /** Envía el cuerpo del contrato (vacío) al motor; las pruebas inyectan un doble. */\n"
            "    enviar?: (cuerpo: CuerpoDelContrato) => Promise<unknown>;\n"
            "  }\n"
            "\n"
            "  async function alMotor(_cuerpo: CuerpoDelContrato): Promise<unknown> {\n"
            f"    if (!contexto.{id_ctx}) throw new Error(TEXTOS.sinContexto);\n"
            f"    return {llamada};\n"
            "  }\n"
            "\n"
            "  const { enviar = alMotor }: Props = $props();\n"
            "\n"
            "  let estado = $state<'ocioso' | 'enviando' | 'enviado' | 'error'>('ocioso');\n"
            "  let fallo = $state<string | null>(null);\n"
            "\n"
            "  async function alEnviar(evento: SubmitEvent): Promise<void> {\n"
            "    evento.preventDefault();\n"
            "    if (estado === 'enviando') return;\n"
            "    estado = 'enviando';\n"
            "    fallo = null;\n"
            "    try {\n"
            "      await enviar({});\n"
            "      estado = 'enviado';\n"
            "    } catch (e) {\n"
            "      estado = 'error';\n"
            "      fallo = textoDelFallo(e);\n"
            "    }\n"
            "  }\n"
            "</script>\n\n"
            "<main data-formulario={contexto.tipo}>\n"
            "  <header class=\"cabecera\">\n"
            "    <h1>{TEXTOS.titulo}</h1>\n"
            "  </header>\n\n"
            "  {#if estado === 'enviado'}\n"
            "    <Aviso tono=\"exito\" titulo={TEXTOS.enviado}><p>{TEXTOS.enviadoDetalle}</p></Aviso>\n"
            "  {:else}\n"
            "    {#if estado === 'error'}\n"
            "      <Aviso tono=\"error\" titulo={TEXTOS.error}><p>{fallo ?? TEXTOS.errorGenerico}</p></Aviso>\n"
            "    {/if}\n"
            "    <form id=\"formulario\" onsubmit={alEnviar} novalidate>\n"
            "      <AccionesDeFormulario principal={TEXTOS.accion} ocupado={estado === 'enviando'} />\n"
            "    </form>\n"
            "  {/if}\n"
            "</main>\n\n" + _ESTILO_SVELTE.replace(
                "\n  .lecturas {\n    display: grid;\n    grid-template-columns: max-content 1fr;\n"
                "    gap: var(--esp-2, 0.5rem) var(--esp-4, 1rem);\n    margin: 0 0 var(--esp-5, 1.5rem);\n  }\n", ""))


def _prueba_solo_accion(form: dict, tipo: str, nombre: str) -> str:
    """Las pruebas de la pantalla de solo acción: no pinta campos, envía el cuerpo vacío y dice si el motor falla."""
    accion = "instancia el proceso" if tipo == "instanciacion" else "completa la tarea"
    return (f"/** Pruebas de la pantalla `{form['id']}`. Del proyecto: el arnés las escribió una vez. */\n"
            "import { fireEvent, render } from '@testing-library/svelte';\n"
            "import { describe, expect, it, vi } from 'vitest';\n"
            f"import {nombre} from './{nombre}.svelte';\n"
            "import { ENTRADAS } from './generado/contrato';\n"
            "\n"
            f"describe('pantalla {form['id']}', () => {{\n"
            "  it('el contrato no tiene inputs: no pinta campos, solo la acción', () => {\n"
            f"    const {{ container, getByTestId }} = render({nombre}, {{ props: {{ enviar: vi.fn(async () => undefined) }} }});\n"
            "    expect(ENTRADAS).toHaveLength(0);\n"
            "    expect(container.querySelectorAll('form input, form select, form textarea')).toHaveLength(0);\n"
            "    expect(getByTestId('accion-principal')).toBeTruthy();\n"
            "  });\n"
            "\n"
            f"  it('la acción {accion} con el cuerpo vacío', async () => {{\n"
            "    const enviar = vi.fn(async () => undefined);\n"
            f"    const {{ container }} = render({nombre}, {{ props: {{ enviar }} }});\n"
            "    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);\n"
            "    expect(enviar).toHaveBeenCalledTimes(1);\n"
            "    expect(enviar).toHaveBeenCalledWith({});\n"
            "  });\n"
            "\n"
            "  it('si el motor rechaza el envío, lo dice', async () => {\n"
            "    const enviar = vi.fn(async () => {\n"
            "      throw new Error('rechazado por el motor');\n"
            "    });\n"
            f"    const {{ container, findByText }} = render({nombre}, {{ props: {{ enviar }} }});\n"
            "    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);\n"
            "    expect(await findByText('rechazado por el motor')).toBeTruthy();\n"
            "  });\n"
            "});\n")


def _prueba(form: dict, tipo: str, nombre: str, campos: list[dict], lecturas: list[dict] | None = None) -> str:
    resumen = tipo == "resumen"
    hay_lecturas = bool(lecturas)
    obligatorios = any(c["requeridoSiempre"] for c in campos)
    testing = ["render"] + ([] if resumen else ["fireEvent"]) + (["waitFor"] if hay_lecturas else [])
    contrato = ([] if resumen else ["CAMPOS", "CUERPO_VACIO", "ENTRADAS"]) + (["LECTURAS"] if hay_lecturas or resumen else [])
    if not resumen and not obligatorios:
        contrato.append("type CuerpoDelContrato")
    props = "" if resumen else ", { props: { enviar: vi.fn(async () => undefined) } }"
    lineas = [f"/** Pruebas de la pantalla `{form['id']}`. Del proyecto: el arnés las escribió una vez. */",
              f"import {{ {', '.join(sorted(testing))} }} from '@testing-library/svelte';",
              "import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';",
              f"import {nombre} from './{nombre}.svelte';",
              f"import {{ {', '.join(contrato)} }} from './generado/contrato';"]
    if hay_lecturas:
        lineas += ["import { TEXTOS } from './textos';", "import { NO_LEIDO } from '$lib/bonita/caso';"]
    lineas += ["",
               "/** La plataforma: la extensión de lecturas del caso responde `caso` (con `null`, falla). */",
               "function plataforma(caso: Record<string, unknown> | null): string[] {",
               "  const pedidas: string[] = [];",
               "  vi.stubGlobal(",
               "    'fetch',",
               "    vi.fn(async (entrada: string | URL) => {",
               "      const url = String(entrada);",
               "      pedidas.push(url);",
               "      if (!url.includes('/extension/consultas/caso')) return new Response('{}', { status: 404 });",
               "      return caso === null ? new Response('{}', { status: 500 }) : new Response(JSON.stringify(caso), { status: 200 });",
               "    }),",
               "  );",
               "  return pedidas;",
               "}",
               "",
               "beforeEach(() => {",
               "  window.history.replaceState(null, '', '/?caseId=7');",
               "  plataforma({});",
               "});",
               "afterEach(() => {",
               "  vi.unstubAllGlobals();",
               "  window.history.replaceState(null, '', '/');",
               "});",
               "",
               f"describe('pantalla {form['id']}', () => {{"]
    pruebas = []
    if resumen:
        pruebas.append("  it('muestra cada dato de solo lectura de la matriz', () => {\n"
                       f"    const {{ container }} = render({nombre});\n"
                       "    expect(container.querySelectorAll('[data-lee]')).toHaveLength(LECTURAS.length);\n"
                       "  });\n")
    else:
        pruebas.append("  it('pinta un campo por cada dato del contrato que usa la matriz', () => {\n"
                       f"    const {{ container }} = render({nombre}{props});\n"
                       "    for (const campo of CAMPOS) {\n"
                       "      const prueba = `campo-${campo.ruta.replace(/\\./g, '-')}`;\n"
                       "      expect(container.querySelector(`[data-testid^=\"${prueba}\"]`), campo.ruta).not.toBeNull();\n"
                       "    }\n"
                       "  });\n")
        pruebas.append("  it('el cuerpo vacío lleva todas las entradas del contrato', () => {\n"
                       "    expect(Object.keys(CUERPO_VACIO).sort()).toEqual([...ENTRADAS].sort());\n"
                       "  });\n")
        if obligatorios:
            pruebas.append("  it('con los obligatorios vacíos no envía', async () => {\n"
                           "    const enviar = vi.fn(async () => undefined);\n"
                           f"    const {{ container }} = render({nombre}, {{ props: {{ enviar }} }});\n"
                           "    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);\n"
                           "    expect(enviar).not.toHaveBeenCalled();\n"
                           "  });\n")
        else:
            espera = ("    // Sin los datos del caso no se envía: se espera a que lleguen.\n"
                      "    await waitFor(() => expect(container.querySelector('dl.lecturas')?.getAttribute('aria-busy')).toBe('false'));\n"
                      if hay_lecturas else "")
            pruebas.append("  it('envía el cuerpo con todas las entradas del contrato', async () => {\n"
                           "    const enviar = vi.fn(async (_cuerpo: CuerpoDelContrato) => undefined);\n"
                           f"    const {{ container }} = render({nombre}, {{ props: {{ enviar }} }});\n"
                           + espera +
                           "    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);\n"
                           "    expect(enviar).toHaveBeenCalledTimes(1);\n"
                           "    expect(Object.keys(enviar.mock.calls[0][0]).sort()).toEqual([...ENTRADAS].sort());\n"
                           "  });\n")
    if hay_lecturas:
        pruebas.append("  it('muestra los datos del caso que lee de la extensión de lecturas del caso', async () => {\n"
                       "    const caso = Object.fromEntries(\n"
                       "      LECTURAS.flatMap((l): [string, string][] => (l.atributo ? [[l.atributo, `valor de ${l.etiqueta}`]] : [])),\n"
                       "    );\n"
                       "    const pedidas = plataforma(caso);\n"
                       f"    const {{ container }} = render({nombre}{props});\n"
                       "    await waitFor(() => expect(container.querySelector('dl.lecturas')?.getAttribute('aria-busy')).toBe('false'));\n"
                       "    const textos = [...container.querySelectorAll('[data-lee]')].map((e) => e.textContent);\n"
                       "    expect(textos).toEqual(LECTURAS.map((l) => (l.atributo ? `valor de ${l.etiqueta}` : NO_LEIDO)));\n"
                       "    expect(pedidas).toContain('/bonita/API/extension/consultas/caso?caseId=7');\n"
                       "  });\n")
        pruebas.append("  it('si la lectura del caso falla, lo dice', async () => {\n"
                       "    plataforma(null);\n"
                       f"    const {{ findByText }} = render({nombre}{props});\n"
                       "    expect(await findByText(TEXTOS.errorLectura)).toBeTruthy();\n"
                       "  });\n")
        if not resumen:
            pruebas.append("  it('si la lectura del caso falla, no deja enviar y lo dice', async () => {\n"
                           "    plataforma(null);\n"
                           "    const enviar = vi.fn(async () => undefined);\n"
                           f"    const {{ container, findByText, getByTestId }} = render({nombre}, {{ props: {{ enviar }} }});\n"
                           "    expect(await findByText(TEXTOS.sinDatosNoSeEnvia)).toBeTruthy();\n"
                           "    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(true);\n"
                           "    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);\n"
                           "    expect(enviar).not.toHaveBeenCalled();\n"
                           "  });\n")
            pruebas.append("  it('mientras la lectura del caso carga, no deja enviar', async () => {\n"
                           "    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)));\n"
                           "    const enviar = vi.fn(async () => undefined);\n"
                           f"    const {{ container, getByTestId }} = render({nombre}, {{ props: {{ enviar }} }});\n"
                           "    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(true);\n"
                           "    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);\n"
                           "    expect(enviar).not.toHaveBeenCalled();\n"
                           "  });\n")
            pruebas.append("  it('con los datos del caso leídos, deja enviar', async () => {\n"
                           f"    const {{ container, getByTestId }} = render({nombre}{props});\n"
                           "    await waitFor(() => expect(container.querySelector('dl.lecturas')?.getAttribute('aria-busy')).toBe('false'));\n"
                           "    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(false);\n"
                           "  });\n")
    return "\n".join(lineas) + "\n" + "\n".join(pruebas) + "});\n"


# ------------------------------------------------------------------------------- páginas propias y temas

def esqueleto_pagina(pagina: dict) -> dict[str, str]:
    """Los ficheros editables de una página propia (nombre -> contenido): una página mínima y accesible con su título,
    y una prueba que la pinta. Del proyecto: el arnés la escribe una vez."""
    token = pagina["token"]
    nombre = token[:1].upper() + token[1:]
    titulo = pagina.get("titulo") or pagina["alias"]
    apps = ", ".join(pagina["aplicaciones"])
    return {
        "index.html": ("<!doctype html>\n<html lang=\"es\">\n  <head>\n    <meta charset=\"UTF-8\" />\n"
                       "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
                       f"    <title>{html.escape(titulo)}</title>\n  </head>\n  <body>\n    <div id=\"app\"></div>\n"
                       "    <script type=\"module\" src=\"./main.ts\"></script>\n  </body>\n</html>\n"),
        "main.ts": ("import { mount } from 'svelte';\n"
                    "// Los tokens de identidad visual: el tema de la Living Application los sobreescribe en runtime.\n"
                    "import '$lib/estilos/tokens.css';\n"
                    "// La marca del proyecto (nombre, logo, colores) es un parámetro del módulo: se aplica sobre los tokens.\n"
                    "import '$lib/estilos/marcaEnVivo';\n"
                    "// Embebida en una bandeja, la pantalla no repite su cabecera.\n"
                    "import '$lib/estilos/enMarco';\n"
                    f"import {nombre} from './{nombre}.svelte';\n\n"
                    "const destino = document.getElementById('app');\n"
                    "if (!destino) throw new Error('No existe el contenedor #app');\n\n"
                    f"export default mount({nombre}, {{ target: destino }});\n"),
        f"{nombre}.svelte": ("<script lang=\"ts\">\n"
                             "  /**\n"
                             f"   * Página «{_comentario(titulo)}» (`{pagina['alias']}`, recurso `{pagina['recurso']}`) de la\n"
                             f"   * aplicación {apps}. ESQUELETO: el arnés lo escribió una vez desde la matriz de formularios\n"
                             "   * y es código del proyecto; edítalo. Lee solo por las extensiones de solo lectura (la de\n"
                             "   * consultas, `$lib/bonita/caso`) y la sesión; nunca por la API de datos de negocio. Si\n"
                             "   * necesita otro recurso REST, la entrada del manifiesto lo declara (se cambia en el arnés).\n"
                             "   */\n"
                             f"  const TITULO = {_comilla(titulo)};\n"
                             "</script>\n\n"
                             "<main>\n"
                             "  <header class=\"cabecera\">\n"
                             "    <h1>{TITULO}</h1>\n"
                             "  </header>\n"
                             "</main>\n\n"
                             "<style>\n"
                             "  main {\n"
                             "    max-inline-size: 60rem;\n"
                             "    margin-inline: auto;\n"
                             "    padding: var(--esp-5, 1.5rem);\n"
                             "  }\n"
                             "</style>\n"),
        "pantalla.test.ts": (f"/** Pruebas de la página `{pagina['alias']}`. Del proyecto: el arnés las escribió una vez. */\n"
                             "import { render } from '@testing-library/svelte';\n"
                             "import { describe, expect, it } from 'vitest';\n"
                             f"import {nombre} from './{nombre}.svelte';\n"
                             "\n"
                             f"describe('página {pagina['alias']}', () => {{\n"
                             "  it('pinta su título como encabezado principal', () => {\n"
                             f"    const {{ getByRole }} = render({nombre});\n"
                             f"    expect(getByRole('heading', {{ level: 1 }}).textContent).toBe({_comilla(titulo)});\n"
                             "  });\n"
                             "});\n"),
    }


def esqueleto_tema(tema: str, apps: list[str]) -> dict[str, str]:
    """El fichero editable de un tema propio: `tema.css`, que `build-form.js` añade tras Bootstrap 3."""
    return {"tema.css": (
        "/*\n"
        f" * Tema `{tema}` de la aplicación {', '.join(apps)}. ESQUELETO: el arnés lo escribió una vez desde la matriz\n"
        " * de formularios y es del proyecto; edítalo.\n"
        " *\n"
        " * `scripts/build-form.js` empaqueta `resources/theme.css` = Bootstrap 3.4.1 (lo que espera el layout de Bonita)\n"
        " * + este fichero, las fuentes de Bootstrap y la carpeta `images/` de aquí si existe (el logo, p. ej.\n"
        " * `images/logo.png`, se referencia como `url(images/logo.png)`). Las páginas enlazan este tema después de sus\n"
        " * estilos: sus variables (`$lib/estilos/tokens.css`) sobreescriben las de la plantilla sin recompilar.\n"
        " */\n"
        ":root {\n"
        "  /* --marca-nombre: 'Nombre de la marca'; */\n"
        "  /* --marca-logo: url(images/logo.png); */\n"
        "  /* --color-primario: #1f4e79; */\n"
        "}\n")}


# ------------------------------------------------------------------------------------------------- entrada

def generar_frontend(spec: dict, proyecto: Path) -> tuple[list[tuple[Path, bytes]], list[tuple[Path, bytes]]]:
    """`(generados, esqueleto)`: lo generado (contrato y esquema de cada formulario Svelte y el manifiesto, que se
    fusiona con el que hay en `proyecto`) y el esqueleto editable (quien escribe decide no pisar lo que ya existe)."""
    proyecto = Path(proyecto)
    procesos = spec.get("procesos") or []
    parametros = spec.get("parametros_negocio") or []
    generados: list[tuple[Path, bytes]] = []
    editables: list[tuple[Path, bytes]] = []
    entradas: list[dict] = []
    vistos: dict[str, str] = {}
    for form in (spec.get("formularios") or {}).get("formularios", []):
        if form.get("mapping") != "Svelte":
            continue
        token = token_pagina(form["id"])
        if token in vistos:
            raise ValueError(f"los formularios «{vistos[token]}» y «{form['id']}» dan la misma página «{token}»")
        vistos[token] = form["id"]
        proceso, contrato = _contrato_de(form, procesos)
        campos, lecturas = _campos(form, contrato, parametros)
        carpeta = proyecto / FORMS / token
        generados.append((carpeta / GENERADO / "contrato.ts",
                          contrato_ts(form, proceso, contrato, campos, lecturas).encode("utf-8")))
        generados.append((carpeta / GENERADO / "esquema.ts", esquema_ts(contrato, campos).encode("utf-8")))
        solo_accion = not contrato.get("inputs") and not form.get("campos")
        editables += [(carpeta / n, texto.encode("utf-8"))
                      for n, texto in esqueleto(form, campos, lecturas, solo_accion).items()]
        entradas.append(entrada_manifiesto(form, campos, lecturas, spec.get("formularios")))
    matriz = spec.get("formularios") or {}
    for pagina in matriz.get("paginas", []):
        if pagina["token"] in vistos:
            raise ValueError(f"la página propia «{pagina['alias']}» y el formulario «{vistos[pagina['token']]}» dan la "
                             f"misma página «{pagina['token']}»")
        vistos[pagina["token"]] = pagina["alias"]
        editables += [(proyecto / FORMS / pagina["token"] / n, texto.encode("utf-8"))
                      for n, texto in esqueleto_pagina(pagina).items()]
        entradas.append(entrada_pagina(pagina, matriz))
    for tema in temas(matriz):
        x = tema.removeprefix("custompage_")
        if x in vistos:
            raise ValueError(f"el tema «{tema}» se llama como la página «{x}»")
        apps = [a["token"] for a in matriz.get("aplicaciones", []) if a.get("tema") == tema]
        editables += [(proyecto / FORMS / x / n, texto.encode("utf-8")) for n, texto in esqueleto_tema(tema, apps).items()]
        entradas.append(entrada_tema(tema, matriz))
    ruta = proyecto / MANIFIESTO
    generados.append((ruta, manifiesto_bytes(ruta.read_bytes() if ruta.is_file() else None, entradas)))
    e2e = e2e_de_parametros(spec)
    if e2e is not None:
        editables.append((proyecto / E2E_PARAMETROS, e2e.encode("utf-8")))
    return generados, editables
