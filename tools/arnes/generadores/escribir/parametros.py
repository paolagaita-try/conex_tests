"""Módulo de parámetros: la semilla de los parámetros de negocio y el bloque `familia.interna.actores`; y el bloque
`familias de actores` de la extensión de consultas (mismos actores internos: sin él, toda lectura del caso da 403).

La semilla tiene la forma que consume `parametros/semilla/aplicar` del módulo (`Semilla.groovy` de `parametros-core`):
`{proceso, version, definiciones, valores, invariantes}`. Sale de `spec["parametros_negocio"]` (filas del Catálogo).

Correspondencia con el core (decisiones documentadas, porque el Catálogo no lo trae todo):
- `codigo` = id sin `param_`, en snake_case y minúsculas (`param_topeDias` -> `tope_dias`); el core normaliza a
  minúsculas y solo admite `[a-z0-9_.-]`. Los formularios usan la misma función (`codigo_de_parametro`).
- Catálogo `valor` y `tramo` -> clase PARAMETRO; `lista` -> LISTA (TEXTO, una opción por trozo separado por `;`);
  `tramo-cascada` -> PARAMETRO con `dependeDe` = su lista padre (si el padre es una LISTA de la semilla) y un valor por
  cada pareja `opción: valor` cuya opción exista en el padre.
- `tipoDato` de un PARAMETRO se infiere del valor: entero -> ENTERO, decimal -> DECIMAL (con sus decimales),
  `n %` -> PORCENTAJE, true/false/sí/no -> BOOLEANO, el resto o sin valor (`[PENDIENTE]`) -> TEXTO.
- `impacto` = ALTO con doble control, si no NORMAL; el ALTO exige `fallback`: el valor conocido o, si no hay, el
  conservador de su tipo (0, 0.00..., false o texto vacío).
- `visibilidad` = CLIENTE para las listas (sus opciones se muestran en formularios) e INTERNA para el resto (el core
  rechaza por defecto lo interno a quien no es de la familia interna).
- `invariantes` = [] (el Catálogo no declara ninguna). `proceso`/`version` salen del primer proceso de la spec.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from generadores.leer.matriz import es_interna, familia_interna

INICIO = "# >>> generado: familia.interna.actores"
FIN = "# <<< generado: familia.interna.actores"
CLAVE_ACTORES = "familia.interna.actores"
# La extensión de consultas (lecturas del caso) lleva sus listas blancas en su propio configuration.properties, entre
# sus marcadores: los mismos actores internos que el módulo de parámetros y, si hay visibilidad por familia, los actores
# y las tareas de la familia cliente.
INICIO_CONSULTAS = "# >>> generado: familias de actores"
FIN_CONSULTAS = "# <<< generado: familias de actores"
PROPIEDADES = Path("bonita-project/parametros/configuration.properties")
CONSULTAS = Path("bonita-project/extensions/consultas-api-extension/src/main/resources/configuration.properties")
# Ficheros mixtos: solo su bloque entre marcadores es generado (lo vigila check_generados); el resto es del proyecto.
MIXTOS = {PROPIEDADES: (INICIO, FIN), CONSULTAS: (INICIO_CONSULTAS, FIN_CONSULTAS)}
_CABECERA = ("# Configuración del módulo de parámetros PARA ESTE PROYECTO. Lo que está entre los marcadores lo\n"
             "# genera el arnés desde los performers del BPMN; no se edita a mano.\n")

_ENTERO = re.compile(r"-?\d+")
_DECIMAL = re.compile(r"-?\d+[.,]\d+")
_PORCENTAJE = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*%")
_BOOLEANOS = {"true": "true", "false": "false", "sí": "true", "si": "true", "no": "false"}


def codigo_de_parametro(id_: str) -> str:
    """`param_topeDias` -> `tope_dias`: el código de la definición en el módulo."""
    s = re.sub(r"^param_", "", id_)
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)
    return s.lower()[:100]


# Una referencia del «Catálogo `param_*`» de la matriz: el parámetro o una definición derivada de su semilla (§2.18):
# `param_T.<nivel>`, `param_T.<campo>` o `param_L.<campo>` (el sufijo, en camelCase o snake_case).
REF_CATALOGO = re.compile(r"param_\w+(?:\.\w+)?")


def codigo_de_referencia(ref: str) -> str:
    """`param_estructura.area` -> `estructura.area`; `param_estados.estadoVisible` -> `estados.estado_visible`; sin
    sufijo, `codigo_de_parametro`. Es el código de la definición que leería el formulario."""
    base, _, sufijo = ref.partition(".")
    return codigo_de_parametro(base) + (f".{_snake(sufijo)}" if sufijo else "")


def es_nivel(ref: str, fila: dict | None) -> bool:
    """La referencia nombra un nivel de la cascada de `fila` (una LISTA de la semilla, no un PARAMETRO)."""
    _, _, sufijo = ref.partition(".")
    return bool(sufijo) and _snake(sufijo) in [_snake(n) for n in (fila or {}).get("niveles") or []]


def _slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:100]


def _sin_formato(texto: str) -> str:
    return texto.replace("`", "").strip()


def _conocido(texto: str) -> bool:
    return bool(texto) and "[" not in texto


def _tipo_y_valor(texto: str) -> tuple[str, str | None, dict]:
    """(tipoDato, valor canónico o None, atributos extra de la definición) de un valor escrito en el Catálogo."""
    t = _sin_formato(texto)
    if not _conocido(t):
        return "TEXTO", None, {}
    m = _PORCENTAJE.fullmatch(t)
    if m:
        n = m.group(1).replace(",", ".")
        return "PORCENTAJE", n, {"unidad": "%", "decimales": len(n.partition(".")[2])}
    if _ENTERO.fullmatch(t):
        return "ENTERO", str(int(t)), {}
    if _DECIMAL.fullmatch(t):
        n = t.replace(",", ".")
        return "DECIMAL", n, {"decimales": len(n.partition(".")[2])}
    if t.lower() in _BOOLEANOS:
        return "BOOLEANO", _BOOLEANOS[t.lower()], {}
    return "TEXTO", (t if len(t) <= 255 else None), {}


def _fallback(tipo: str, valor: str | None, extra: dict) -> str:
    if valor is not None:
        return valor
    if tipo == "BOOLEANO":
        return "false"
    if tipo in ("ENTERO",):
        return "0"
    if tipo in ("DECIMAL", "PORCENTAJE", "MONTO"):
        d = extra.get("decimales", 0)
        return "0" if not d else "0." + "0" * d
    return ""


def _partir(texto: str, sep: str) -> list[str]:
    """`texto` partido por `sep` fuera de corchetes y de backticks («[PENDIENTE — a; b]» es un solo trozo)."""
    out, actual, corchetes, token = [], [], 0, False
    for ch in texto:
        if ch == "`":
            token = not token
        elif not token and ch == "[":
            corchetes += 1
        elif not token and ch == "]" and corchetes:
            corchetes -= 1
        if ch == sep and not token and not corchetes:
            out.append("".join(actual))
            actual = []
        else:
            actual.append(ch)
    return out + ["".join(actual)]


def _trozos(texto: str) -> list[str]:
    """Los trozos de una celda «Valor(es)» separados por «;», sin los pendientes (los que empiezan por «[»)."""
    return [t.strip() for t in _partir(texto, ";") if t.strip() and not t.strip().startswith("[")]


# Contrato §2.18. Campos de una opción: «: campo=valor, campo=valor» (el nombre, con o sin backticks).
_NOMBRE_CAMPO = r"`?[A-Za-z][A-Za-z0-9_]*`?"
_INICIO_CAMPOS = re.compile(rf":\s*(?={_NOMBRE_CAMPO}\s*=)")
_EMPIEZA_CAMPO = re.compile(rf"{_NOMBRE_CAMPO}\s*=")
_CAMPO = re.compile(r"`?([A-Za-z][A-Za-z0-9_]*)`?\s*=\s*(.*)", re.S)
_CLAVE_Y_ETIQUETA = re.compile(r"`([^`]+)`\s*(.*)", re.S)
_CODIGO = re.compile(r"[a-z0-9_.-]{1,100}")
# «opción del padre: valor» (o «=»); el separador no puede ir seguido de «//» (una URL no es una pareja).
_PAR = re.compile(r"([^:=/\s][^:=]*?)\s*[:=](?!//)\s*(.*)", re.S)
_NIVEL = "›"


def _snake(nombre: str) -> str:
    """`estadoVisible` -> `estado_visible`: el sufijo de la definición de un campo o de un nivel."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", nombre).lower()


def _leer_campos(texto: str, trozo: str) -> list[tuple[str, str]]:
    """`[(campo, valor)]` de «campo=valor, campo=valor» (valor sin backticks; pendiente = sin valor)."""
    out: list[tuple[str, str]] = []
    for pieza in (p.strip() for p in _partir(texto, ",")):
        m = _CAMPO.fullmatch(pieza)
        if not m:
            raise ValueError(f"«{pieza}» no es «campo=valor» en «{_sin_formato(trozo)}» (los campos de una opción van "
                             "como «: campo=valor, campo=valor»; un valor no lleva «,»)")
        nombre, valor = m.group(1), _sin_formato(m.group(2))
        if any(_snake(n) == _snake(nombre) for n, _ in out):
            raise ValueError(f"campo «{_snake(nombre)}» repetido en «{_sin_formato(trozo)}»")
        if not valor:
            raise ValueError(f"el campo «{nombre}» no tiene valor en «{_sin_formato(trozo)}» (si aún no se conoce: "
                             "«[PENDIENTE]»)")
        out.append((nombre, valor))
    return out


def _clave(texto: str) -> str:
    c = texto.strip().lower()
    if not _CODIGO.fullmatch(c):
        raise ValueError(f"la clave «{texto.strip()}» no vale como código del módulo (minúsculas ASCII, dígitos, «_», "
                         "«.» o «-»; hasta 100)")
    return c


def _etiqueta(texto: str) -> str:
    if len(texto) > 255:
        raise ValueError(f"la etiqueta «{texto[:40]}…» pasa de 255 caracteres")
    return texto


def _opcion(texto: str) -> tuple[str, str]:
    """`(código, etiqueta)` de una opción sin sus campos: «`clave` Etiqueta», o la forma de hoy («Etiqueta» o «`texto`»
    solo: código = slug de la etiqueta)."""
    m = _CLAVE_Y_ETIQUETA.fullmatch(texto.strip())
    if m and m.group(2).strip():
        return _clave(m.group(1)), _etiqueta(_sin_formato(m.group(2)))
    etiqueta = _sin_formato(texto)
    if not _slug(etiqueta):
        raise ValueError(f"la opción «{etiqueta}» no da un código (escribe su clave: «`clave` {etiqueta}»)")
    return _slug(etiqueta), _etiqueta(etiqueta)


def _opciones(valores: str) -> list[dict]:
    """Las opciones de una lista del Catálogo: `[{codigo, etiqueta, campos: [(campo, valor)]}]`."""
    out: list[dict] = []
    for trozo in _trozos(valores):
        m = _INICIO_CAMPOS.search(trozo)
        cabeza, campos = (trozo[:m.start()], _leer_campos(trozo[m.end():], trozo)) if m else (trozo, [])
        if not _conocido(_sin_formato(cabeza)):
            continue
        c, etiqueta = _opcion(cabeza)
        if any(o["codigo"] == c for o in out):
            raise ValueError(f"opción «{c}» repetida (dos opciones con el mismo código)")
        out.append({"codigo": c, "etiqueta": etiqueta, "campos": campos})
    return out


def opciones_de_lista(valores: str) -> list[tuple[str, str]]:
    """`(código, etiqueta)` de cada opción de una lista del Catálogo, como las siembra el módulo."""
    return [(o["codigo"], o["etiqueta"]) for o in _opciones(valores)]


def _descripcion(f: dict) -> str:
    return f"Administra: {f['administra']}. Origen: {f['origen']}. Citado en: {f['citado_en']}."


def _de_la_opcion(texto: str, padre: str, codigos: list[str]) -> str:
    """El código de una opción del padre nombrada en un tramo-cascada: su clave o, como hoy, el slug de su etiqueta."""
    t = _sin_formato(texto)
    for c in (t.lower(), _slug(t)):
        if c in codigos:
            return c
    raise ValueError(f"«{t}» no es una opción de «{padre}» ({', '.join(codigos) or 'sin opciones'})")


def _tramo(valores: str, padre: str, codigos: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, list]]]:
    """Las parejas de un tramo-cascada con padre: `(simples, con_campos)`; una de las dos va vacía (no se mezclan)."""
    simples: list[tuple[str, str]] = []
    con_campos: list[tuple[str, list]] = []
    for trozo in _trozos(valores):
        m = _PAR.fullmatch(trozo)
        if not m:
            raise ValueError(f"«{_sin_formato(trozo)}» debe ser «opción del padre: valor» (o «opción: campo=valor, …»)")
        c = _de_la_opcion(m.group(1), padre, codigos)
        if any(x == c for x, _ in simples + con_campos):
            raise ValueError(f"opción «{c}» repetida")
        resto = m.group(2).strip()
        if _EMPIEZA_CAMPO.match(resto):
            con_campos.append((c, _leer_campos(resto, trozo)))
        elif _conocido(_sin_formato(resto)):
            simples.append((c, resto))
    if simples and con_campos:
        raise ValueError("todas las opciones de un tramo-cascada llevan un valor («opción: valor») o todas sus campos "
                         "(«opción: campo=valor, …»): no se mezclan")
    return simples, con_campos


def _tipo_de(valores: list[str]) -> tuple[str, dict]:
    """El tipo de dato común de unos valores (TEXTO si difieren) con sus atributos (unidad, decimales)."""
    tipos = {_tipo_y_valor(v)[0] for v in valores}
    tipo = tipos.pop() if len(tipos) == 1 else "TEXTO"
    if tipo == "TEXTO" or not valores:
        return "TEXTO", {}
    extra = _tipo_y_valor(valores[0])[2]
    if tipo in ("DECIMAL", "PORCENTAJE"):
        extra = {**extra, "decimales": max(_tipo_y_valor(v)[2].get("decimales", 0) for v in valores)}
    return tipo, extra


def _valor_de(tipo: str, texto: str) -> str:
    if tipo != "TEXTO":
        return _tipo_y_valor(texto)[1]
    t = _sin_formato(texto)
    if len(t) > 255:
        raise ValueError(f"el valor «{t[:40]}…» pasa de 255 caracteres (el módulo guarda hasta 255)")
    return t


def _por_opcion(f: dict, codigo: str, nombre: str, depende: str, pares: list[tuple[str, str]]) -> tuple[dict, list]:
    """Un PARAMETRO que depende de una lista, con un valor por opción (un campo de una lista o de un tramo-cascada)."""
    conocidos = [(c, v) for c, v in pares if _conocido(_sin_formato(v))]
    tipo, extra = _tipo_de([v for _, v in conocidos])
    d = {"codigo": codigo, "nombre": nombre, "descripcion": _descripcion(f), "clase": "PARAMETRO", "tipoDato": tipo,
         **extra, "impacto": "ALTO" if f["doble_control"] else "NORMAL", "visibilidad": "INTERNA", "dependeDe": depende}
    if f["doble_control"]:
        d["fallback"] = _fallback(tipo, None, extra)
    return d, [{"definicion": codigo, "codigoPadre": c, "valor": _valor_de(tipo, v)} for c, v in conocidos]


def _por_campo(f: dict, codigo: str, depende: str, filas: list[tuple[str, list]]) -> tuple[list, list]:
    """Un PARAMETRO `<codigo>.<campo>` por cada campo (en orden de aparición) de unas opciones con campos."""
    nombres = list(dict.fromkeys(n for _, campos in filas for n, _ in campos))
    defs: list[dict] = []
    vals: list[dict] = []
    for n in nombres:
        pares = [(c, v) for c, campos in filas for m, v in campos if m == n]
        d, v = _por_opcion(f, f"{codigo}.{_snake(n)}", f"{f['nombre']} {_NIVEL} {n}", depende, pares)
        defs.append(d)
        vals += v
    return defs, vals


def _cascada(f: dict, codigo: str, padre: str, padre_codigo: str, codigos: list[str], proceso: str
             ) -> tuple[list, list]:
    """Una LISTA por nivel (`<codigo>.<nivel>`), cada una dependiente de la anterior y la primera de la lista padre.
    Cada trozo es un camino «`opción del padre` › `clave` Etiqueta › …»; un nodo ya nombrado se repite solo con su
    clave. Una clave es única en su nivel (el código del padre del nivel siguiente la nombra sin ambigüedad)."""
    niveles = f["niveles"]
    nodos: list[dict[str, dict]] = [{} for _ in niveles]
    hojas: set[tuple[int, str]] = set()
    for trozo in _trozos(f["valores"]):
        partes = [p.strip() for p in _partir(trozo, _NIVEL)]
        if len(partes) < 2:
            raise ValueError(f"«{_sin_formato(trozo)}» necesita la opción del padre y al menos un nivel "
                             f"(«`opción` {_NIVEL} `clave` Etiqueta {_NIVEL} …»)")
        if len(partes) > len(niveles) + 1:
            raise ValueError(f"«{_sin_formato(trozo)}» tiene más niveles que los declarados ({', '.join(niveles)})")
        anterior = _de_la_opcion(partes[0], padre, codigos)
        for i, parte in enumerate(partes[1:]):
            if _INICIO_CAMPOS.search(parte):
                raise ValueError(f"«{_sin_formato(parte)}»: una cascada de niveles no lleva campos (solo clave y "
                                 "etiqueta)")
            m = _CLAVE_Y_ETIQUETA.fullmatch(parte)
            clave, etiqueta = ((_clave(m.group(1)), _sin_formato(m.group(2)) or None) if m
                               else _opcion(parte))
            nodo = nodos[i].get(clave)
            if nodo is None:
                nodos[i][clave] = {"padre": anterior, "etiqueta": etiqueta}
            elif nodo["padre"] != anterior:
                raise ValueError(f"la clave «{clave}» del nivel «{niveles[i]}» ya cuelga de «{nodo['padre']}» (no "
                                 f"puede colgar también de «{anterior}»: la clave es única en su nivel)")
            elif etiqueta and nodo["etiqueta"] and etiqueta != nodo["etiqueta"]:
                raise ValueError(f"«{clave}» del nivel «{niveles[i]}» tiene dos etiquetas: «{nodo['etiqueta']}» y "
                                 f"«{etiqueta}»")
            elif etiqueta:
                nodo["etiqueta"] = etiqueta
            anterior = clave
        hoja = (len(partes) - 1, anterior)
        if hoja in hojas:
            raise ValueError(f"«{_sin_formato(trozo)}» repetido")
        hojas.add(hoja)
    defs: list[dict] = []
    vals: list[dict] = []
    depende = padre_codigo
    for nivel, de_nivel in zip(niveles, nodos):
        c = f"{codigo}.{_snake(nivel)}"
        d = {"codigo": c, "nombre": f"{f['nombre']} {_NIVEL} {nivel}", "descripcion": _descripcion(f),
             "clase": "LISTA", "tipoDato": "TEXTO", "impacto": "ALTO" if f["doble_control"] else "NORMAL",
             "visibilidad": "CLIENTE", "dependeDe": depende}
        if f["doble_control"]:
            d["fallback"] = ""
        defs.append(d)
        orden: dict[str, int] = {}
        for clave, nodo in de_nivel.items():
            orden[nodo["padre"]] = orden.get(nodo["padre"], 0) + 1
            vals.append({"definicion": c, "proceso": proceso, "codigoPadre": nodo["padre"], "codigo": clave,
                         "etiqueta": nodo["etiqueta"] or clave, "orden": orden[nodo["padre"]]})
        depende = c
    return defs, vals


class _PadreConError(Exception):
    """El padre de la fila tiene su propio error: la fila no se siembra y no se repite el error."""


def _de_fila(f: dict, codigos: dict[str, str], tipos: dict[str, str], opciones: dict[str, list | None],
             proceso: str) -> tuple[list[dict], list[dict]]:
    """Las definiciones y los valores de una fila del Catálogo (ValueError si su forma no se puede sembrar)."""
    codigo, tipo_cat = codigos[f["id"]], f["tipo"]
    d: dict = {"codigo": codigo, "nombre": f["nombre"], "descripcion": _descripcion(f)}
    if tipo_cat == "lista":
        ops = _opciones(f["valores"])
        d.update(clase="LISTA", tipoDato="TEXTO", impacto="ALTO" if f["doble_control"] else "NORMAL",
                 visibilidad="CLIENTE")
        if f["doble_control"]:
            d["fallback"] = ""
        valores = [{"definicion": codigo, "proceso": proceso, "codigo": o["codigo"], "etiqueta": o["etiqueta"],
                    "orden": i} for i, o in enumerate(ops, 1)]
        defs, vals = _por_campo(f, codigo, codigo, [(o["codigo"], o["campos"]) for o in ops if o["campos"]])
        return [d] + defs, valores + vals
    padre_id = f["padre"] if tipo_cat == "tramo-cascada" else None
    pares: list[tuple[str, str]] = []
    padre = None
    if padre_id is not None:
        if tipos.get(padre_id) != "lista":
            raise ValueError(f"su padre «{padre_id}» no es una lista del módulo de parámetros (un tramo-cascada "
                             "cuelga de una lista del Catálogo con Representación «módulo de parámetros»)")
        if opciones[padre_id] is None:
            raise _PadreConError()
        padre, codigos_padre = codigos[padre_id], [o["codigo"] for o in opciones[padre_id]]
        if f.get("niveles"):
            return _cascada(f, codigo, padre_id, padre, codigos_padre, proceso)
        pares, con_campos = _tramo(f["valores"], padre_id, codigos_padre)
        if con_campos:
            return _por_campo(f, codigo, padre, con_campos)
    elif tipo_cat == "tramo-cascada" and any(_PAR.fullmatch(t) for t in _trozos(f["valores"])):
        raise ValueError("un tramo-cascada con «opción: valor» necesita su lista padre («depende de `param_x`» en la "
                         "columna Tipo): sin ella sus claves se perderían")
    if padre is not None and pares:
        tipo, extra = _tipo_de([v for _, v in pares])
        valor_fb = None
    else:
        texto = "" if padre is not None else f["valores"]
        tipo, valor_fb, extra = _tipo_y_valor(texto)
        if tipo == "TEXTO" and _conocido(_sin_formato(texto)) and valor_fb is None:
            raise ValueError(f"el valor «{_sin_formato(texto)[:40]}…» pasa de 255 caracteres (el módulo guarda hasta "
                             "255)")
    alto = f["doble_control"]
    d.update(clase="PARAMETRO", tipoDato=tipo, **extra, impacto="ALTO" if alto else "NORMAL", visibilidad="INTERNA")
    if padre is not None:
        d["dependeDe"] = padre
    if alto:
        d["fallback"] = _fallback(tipo, valor_fb, extra)
    if padre is not None:
        return [d], [{"definicion": codigo, "codigoPadre": c, "valor": _tipo_y_valor(v)[1] or ""} for c, v in pares]
    return [d], ([{"definicion": codigo, "valor": valor_fb}] if valor_fb is not None else [])


def generar_semilla(spec: dict, errores: list[str] | None = None) -> dict:
    """La semilla del módulo de parámetros con los parámetros de negocio de la spec (vacía si no hay).

    Una fila cuya forma no se puede sembrar sin perder información es un error con su ubicación en el Catálogo: con
    `errores` se añade ahí y la fila no se siembra (así lo usa `generadores/validar/parametros.py`); sin él, ValueError."""
    from generadores.leer import donde
    from generadores.leer.catalogo import F

    procesos = spec.get("procesos") or []
    proceso = procesos[0]["nombre"] if procesos else spec.get("proyecto", {}).get("nombre", "proceso")
    version = procesos[0]["version"] if procesos else "1.0"
    filas = spec.get("parametros_negocio") or []
    codigos = {f["id"]: codigo_de_parametro(f["id"]) for f in filas}
    tipos = {f["id"]: f["tipo"] for f in filas}
    opciones: dict[str, list | None] = {}  # las de cada lista, antes que nada: un tramo-cascada puede ir antes
    for f in filas:
        if f["tipo"] == "lista":
            try:
                opciones[f["id"]] = _opciones(f["valores"])
            except ValueError:
                opciones[f["id"]] = None
    vistos: dict[str, str] = {}
    definiciones: list[dict] = []
    valores: list[dict] = []
    for f in filas:
        try:
            defs, vals = _de_fila(f, codigos, tipos, opciones, proceso)
            for d in defs:
                c = d["codigo"]
                if c in vistos:
                    raise ValueError(f"los parámetros «{vistos[c]}» y «{f['id']}» dan el mismo código «{c}» en el "
                                     "módulo de parámetros (el core rechazaría la semilla)")
                if len(c) > 100 or len(d["nombre"]) > 255:
                    raise ValueError(f"la definición «{c[:60]}» pasa del largo del módulo (código hasta 100 "
                                     "caracteres, nombre hasta 255)")
        except _PadreConError:
            continue
        except ValueError as e:
            mensaje = f"{donde(F, 'Catálogo', f['id'])}: {e}"
            if errores is None:
                raise ValueError(mensaje) from None
            errores.append(mensaje)
            continue
        vistos.update({d["codigo"]: f["id"] for d in defs})
        definiciones += defs
        valores += vals
    return {"proceso": proceso, "version": version, "definiciones": definiciones, "valores": valores,
            "invariantes": []}


def _en_bonita(spec: dict) -> dict[str, str]:
    """Actor de negocio de cada lane -> su actor del `.proc` (`actor_bonita` si la lane lo declara; si no, el mismo).
    Las lanes sin actor (`sin_actor`, solo tareas automáticas) no tienen actor que comparar."""
    lanes = [lane for p in spec.get("procesos", []) for lane in p.get("lanes", []) if not lane.get("sin_actor")]
    out = {lane["actor"]: lane["actor_bonita"] for lane in lanes if lane.get("actor_bonita")}
    return {**{lane["actor"]: lane["actor"] for lane in lanes}, **out}


def _actor_del_bpmn(form: dict, spec: dict, en_bonita: dict[str, str]) -> str | None:
    """El actor (del `.proc`) de un formulario según el BPMN: el actor de tarea que lista su tarea o el de la lane de
    la tarea; el de un formulario de instanciación sin tarea, el iniciador de su pool. None si no se resuelve."""
    procesos = spec.get("procesos", [])
    m = re.match(r"[\w.-]+", (form.get("tarea") or "").strip())
    if m:
        for p in procesos:
            at = next((a for a in p.get("actores_tarea") or [] if m.group(0) in a.get("tareas", [])), None)
            if at:
                return at["nombre"]
            nodo = next((n for n in p.get("nodos", []) if n.get("id") == m.group(0)), None)
            lane = nodo and next((l for l in p.get("lanes", []) if l.get("nombre") == nodo.get("lane")), None)
            if lane and not lane.get("sin_actor"):
                return lane.get("actor_bonita") or lane["actor"]
    if form.get("tipo") == "Instantiation form":
        pool = form["id"].removeprefix("frm_instanciacion_") if form["id"].startswith("frm_instanciacion_") else None
        p = next((p for p in procesos if p.get("nombre") == pool), None) if pool else (procesos[0] if procesos
                                                                                     else None)
        if p and p.get("iniciador"):
            return en_bonita.get(p["iniciador"], p["iniciador"])
    return None


def _actores_de(formularios: list[dict], spec: dict) -> set[str]:
    """Los actores (del `.proc`) de unos formularios. La columna Actor de la matriz, por comas, si todos sus elementos
    son actores (de negocio de una lane, que se traduce a su actor Bonita, Bonita o de tarea); si no (p. ej.
    «Analista · `filtroDelCaso`»), el actor del BPMN (`_actor_del_bpmn`). Un case overview sin actor reconocible no
    aporta ninguno (no tiene tarea); otro formulario sin resolver conserva la columna tal cual (y falla después si no
    vale como actor)."""
    en_bonita = _en_bonita(spec)
    conocidos = set(en_bonita) | set(en_bonita.values()) | {a["nombre"] for p in spec.get("procesos", [])
                                                             for a in p.get("actores_tarea") or []}
    out: set[str] = set()
    for f in formularios:
        columna = [a.strip() for a in (f.get("actor") or "").split(",") if a.strip()]
        if columna and all(a in conocidos for a in columna):
            out |= {en_bonita.get(a, a) for a in columna}
            continue
        del_bpmn = _actor_del_bpmn(f, spec, en_bonita)
        if del_bpmn:
            out.add(del_bpmn)
        elif f.get("tipo") != "Case overview":
            out |= {en_bonita.get(a, a) for a in columna}
    return out


def actores_internos(spec: dict) -> list[str]:
    """Los actores de la familia interna, ordenados, con su nombre del `.proc`: el módulo compara con el actor de la
    tarea que le da el motor (`TareasBonita`).

    Sin «Familia visible» en ningún formulario Svelte hay una sola familia: todos los actores de los carriles
    (performers: el Actor Bonita de cada lane que tiene actor) y los actores de tarea son internos. Con visibilidad por
    familia, solo los actores de los formularios de la familia interna: la que declara «Familia interna» en la matriz
    o, sin esa línea, `interna` (sin distinguir mayúsculas); si ninguno es de ella es un error (no se adivina). Un
    actor con coma, barra invertida o espacios es un error: rompería la lista blanca separada por comas."""
    en_bonita = _en_bonita(spec)
    carriles = set(en_bonita.values()) | {a["nombre"] for p in spec.get("procesos", [])
                                          for a in p.get("actores_tarea") or []}
    matriz = spec.get("formularios") or {}
    formularios = [f for f in matriz.get("formularios", []) if f.get("mapping") == "Svelte"]
    if any(f.get("familia_actores") for f in formularios):
        internos = [f for f in formularios if es_interna(f.get("familia_actores"), matriz)]
        if not internos:
            familias = ", ".join(dict.fromkeys(f["familia_actores"] for f in formularios if f.get("familia_actores")))
            raise ValueError(f"hay visibilidad por familia («Familia visible» en la matriz de formularios: "
                             f"{familias}) pero ningún formulario es de la familia interna «{familia_interna(matriz)}»"
                             f": no se puede decidir qué actores son internos. Declárala en Convenciones de "
                             f"matriz-formularios.md con «- **Familia interna**: `<familia>`» (sin esa línea, la "
                             f"interna se llama `interna`)")
        actores = _actores_de(internos, spec)
    else:
        actores = carriles
    for a in sorted(carriles | actores):
        if re.search(r"[,\\\s]", a):
            raise ValueError(f"el actor «{a}» tiene coma, barra invertida o espacios: no vale en "
                             f"{CLAVE_ACTORES} (lista separada por comas)")
    return sorted(actores)


def extraer_bloque(texto: str, inicio: str = INICIO, fin_: str = FIN) -> str | None:
    """El bloque entre marcadores (marcadores incluidos) de un configuration.properties, o None si falta."""
    ini, fin = texto.find(inicio), texto.find(fin_)
    if ini == -1 or fin <= ini:
        return None
    return texto[ini:fin + len(fin_)]


def bloque_actores(spec: dict) -> str:
    """El bloque generado de configuration.properties, marcadores incluidos, terminado en salto de línea."""
    return f"{INICIO}\n{CLAVE_ACTORES}={','.join(actores_internos(spec))}\n{FIN}\n"


def _familia_cliente(spec: dict) -> tuple[list[str], list[str]]:
    """(actores, tareas) de la familia cliente: los de los formularios Svelte con «Familia visible» distinta de la
    interna; las tareas, solo las de sus formularios de tarea (ids del BPMN). Sin visibilidad por familia, vacíos."""
    matriz = spec.get("formularios") or {}
    formularios = [f for f in matriz.get("formularios", []) if f.get("mapping") == "Svelte"]
    cliente = [f for f in formularios if f.get("familia_actores") and not es_interna(f["familia_actores"], matriz)]
    actores = _actores_de(cliente, spec)
    tareas = {f["tarea"] for f in cliente if f.get("tipo") == "Task form" and f.get("tarea")}
    for x in sorted(actores | tareas):
        if re.search(r"[,\\\s]", x):
            raise ValueError(f"«{x}» tiene coma, barra invertida o espacios: no vale en una lista blanca de la "
                             "extensión de consultas (lista separada por comas)")
    return sorted(actores), sorted(tareas)


def bloque_consultas(spec: dict) -> str:
    """El bloque generado del configuration.properties de la extensión de consultas, marcadores incluidos."""
    actores, tareas = _familia_cliente(spec)
    return (f"{INICIO_CONSULTAS}\n{CLAVE_ACTORES}={','.join(actores_internos(spec))}\n"
            f"familia.cliente.actores={','.join(actores)}\nfamilia.cliente.tareas={','.join(tareas)}\n{FIN_CONSULTAS}\n")


def aplicar_bloque(existente: str | None, bloque: str, inicio: str = INICIO, fin_: str = FIN) -> str:
    """Sustituye el bloque entre marcadores conservando el resto; sin marcadores lo añade al final; sin fichero crea
    el fichero con su cabecera."""
    if existente is None:
        return _CABECERA + bloque
    ini, fin = existente.find(inicio), existente.find(fin_)
    if ini != -1 and fin > ini:
        fin = existente.find("\n", fin)
        fin = len(existente) if fin == -1 else fin + 1
        return existente[:ini] + bloque + existente[fin:]
    return existente + ("" if existente.endswith("\n") or not existente else "\n") + bloque


def _a_latin1(texto: str) -> bytes:
    """ISO-8859-1; lo que no cabe se escribe como escape `\\uXXXX` (convención de .properties)."""
    return "".join(c if ord(c) < 256 else f"\\u{ord(c):04x}" for c in texto).encode("iso-8859-1")


def generar_propiedades(spec: dict, existente: bytes | None) -> bytes:
    """El configuration.properties del módulo con el bloque de actores puesto al día (ISO-8859-1)."""
    previo = existente.decode("iso-8859-1") if existente is not None else None
    return _a_latin1(aplicar_bloque(previo, bloque_actores(spec)))


def generar_propiedades_consultas(spec: dict, existente: bytes) -> bytes:
    """El configuration.properties de la extensión de consultas (que trae la plantilla) con su bloque al día."""
    return _a_latin1(aplicar_bloque(existente.decode("iso-8859-1"), bloque_consultas(spec), INICIO_CONSULTAS,
                                    FIN_CONSULTAS))


def semilla_bytes(spec: dict) -> bytes:
    return (json.dumps(generar_semilla(spec), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
