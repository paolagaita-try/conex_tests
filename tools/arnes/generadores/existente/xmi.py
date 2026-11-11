"""Índice de rangos y edición del XML sin reformatear.

Los ficheros del Studio (`.proc`, `bom.xml`, organizaciones) se editan insertando, reemplazando o quitando texto por
rangos de caracteres: lo que no se toca queda idéntico byte a byte. Por eso aquí no se usa ElementTree para escribir,
solo un escáner de etiquetas propio que respeta las comillas (un `>` dentro de un valor no cierra la etiqueta) e
ignora comentarios, `<?xml?>`, CDATA y `<!DOCTYPE>`."""
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

# Etiqueta: <nombre atributos> | <nombre atributos/> | </nombre>; las comillas se respetan.
_ETIQUETA = re.compile(r"<(/?)([^\s/>!?][^\s/>]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>")
_ATRIBUTO = re.compile(r"""([^\s=/]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_OMITIR = (("<!--", "-->"), ("<?", "?>"), ("<![CDATA[", "]]>"))


@dataclass(frozen=True)
class Nodo:
    tag: str
    attrs: dict[str, str]
    inicio: int  # offset del `<` de apertura
    fin: int  # offset posterior al último `>` del elemento
    abre_fin: int  # offset posterior al `>` de la etiqueta de apertura
    cierra_inicio: int | None  # offset del `<` de `</tag>`; None si el elemento es `<x ... />`
    padre: int | None  # posición del padre en la lista de `indexar`


@dataclass(frozen=True)
class Edicion:
    inicio: int
    fin: int
    nuevo: str


def _atributos(cuerpo: str) -> dict[str, str]:
    return {m.group(1): html.unescape(m.group(2) if m.group(2) is not None else m.group(3))
            for m in _ATRIBUTO.finditer(cuerpo)}


def indexar(texto: str) -> list[Nodo]:
    """Elementos del documento en orden de documento, con los rangos de su texto."""
    abiertos: list[tuple[int, str, dict, int, int | None]] = []  # (posición en `nodos`, tag, attrs, inicio, abre_fin)
    nodos: list[Nodo | None] = []
    pila: list[int] = []
    pos = 0
    while True:
        i = texto.find("<", pos)
        if i < 0:
            break
        omitido = next(((a, c) for a, c in _OMITIR if texto.startswith(a, i)), None)
        if omitido:
            f = texto.find(omitido[1], i + len(omitido[0]))
            if f < 0:
                raise ValueError(f"XML mal formado: «{omitido[0]}» sin cerrar en {i}")
            pos = f + len(omitido[1])
            continue
        if texto.startswith("<!", i):  # <!DOCTYPE ...>
            f = texto.find(">", i)
            if f < 0:
                raise ValueError(f"XML mal formado: declaración sin cerrar en {i}")
            pos = f + 1
            continue
        m = _ETIQUETA.match(texto, i)
        if not m:
            raise ValueError(f"XML mal formado: etiqueta no válida en {i}")
        pos = m.end()
        cierre, tag, cuerpo = m.group(1), m.group(2), m.group(3)
        if cierre:
            if not pila:
                raise ValueError(f"XML mal formado: «</{tag}>» sin apertura en {i}")
            k = pila.pop()
            n = nodos[k]
            if n.tag != tag:
                raise ValueError(f"XML mal formado: «</{tag}>» cierra «{n.tag}» en {i}")
            nodos[k] = Nodo(n.tag, n.attrs, n.inicio, m.end(), n.abre_fin, i, n.padre)
            continue
        vacio = cuerpo.rstrip().endswith("/")
        padre = pila[-1] if pila else None
        nodo = Nodo(tag, _atributos(cuerpo), i, m.end(), m.end(), None, padre)
        nodos.append(nodo)
        if not vacio:
            pila.append(len(nodos) - 1)
    if pila:
        raise ValueError(f"XML mal formado: «{nodos[pila[-1]].tag}» sin cerrar")
    return nodos


def por_id(nodos: list[Nodo]) -> dict[str, Nodo]:
    """Nodos por `xmi:id`. `ValueError` si un id se repite."""
    r: dict[str, Nodo] = {}
    for n in nodos:
        v = n.attrs.get("xmi:id")
        if v is None:
            continue
        if v in r:
            raise ValueError(f"xmi:id repetido: {v}")
        r[v] = n
    return r


def aplicar(texto: str, ediciones: list[Edicion]) -> str:
    """Aplica las ediciones (sobre los offsets del texto original). Varias inserciones en el mismo punto se aplican en
    el orden de la lista (orden estable). `ValueError` si dos rangos no vacíos se solapan o si una edición es inválida."""
    orden = sorted(ediciones, key=lambda e: (e.inicio, e.fin > e.inicio))  # estable: las inserciones antes que el rango
    partes, cursor = [], 0
    for e in orden:
        if e.fin < e.inicio or e.inicio < cursor:
            raise ValueError(f"Ediciones solapadas o fuera de rango: [{e.inicio}, {e.fin}) con cursor {cursor}")
        partes += [texto[cursor:e.inicio], e.nuevo]
        cursor = e.fin
    partes.append(texto[cursor:])
    return "".join(partes)


def _salto(texto: str) -> str:
    return "\r\n" if "\r\n" in texto else "\n"


def _sangria_de(texto: str, pos: int) -> str:
    """Espacio en blanco que precede a `pos` en su línea (vacío si antes hay otro texto)."""
    k = pos
    while k > 0 and texto[k - 1] in " \t":
        k -= 1
    return texto[k:pos] if k == 0 or texto[k - 1] == "\n" else ""


def sangria_hijo(texto: str, nodo: Nodo) -> str:
    """Sangría que tendría un hijo nuevo de `nodo`: la del último hijo, o la de `nodo` más dos espacios."""
    ultimo = _ultimo_hijo(texto, nodo)
    if ultimo is not None:
        s = _sangria_de(texto, ultimo.inicio)
        if s or texto[:ultimo.inicio].rstrip(" \t").endswith("\n") or ultimo.inicio == 0:
            return s
    return _sangria_de(texto, nodo.inicio) + "  "


def _ultimo_hijo(texto: str, nodo: Nodo) -> Nodo | None:
    if nodo.cierra_inicio is None:
        return None
    internos = indexar(texto[nodo.abre_fin:nodo.cierra_inicio])
    tops = [n for n in internos if n.padre is None]
    if not tops:
        return None
    u = tops[-1]
    d = nodo.abre_fin
    return Nodo(u.tag, u.attrs, u.inicio + d, u.fin + d, u.abre_fin + d,
                None if u.cierra_inicio is None else u.cierra_inicio + d, None)


def insertar_hijos(texto: str, nodo: Nodo, fragmentos: list[str]) -> Edicion:
    """Añade `fragmentos` (en orden) como últimos hijos de `nodo`, con la sangría del último hijo (o la de `nodo` más
    dos espacios) y el salto del fichero. Cada fragmento va sin sangría en su primera línea (las siguientes ya la
    traen, ver `fragmento`). Devuelve UNA sola `Edicion`, así que funciona igual si `nodo` es autocerrado
    (`<x ... />` pasa a `<x ...>` + hijos + `</x>`), está vacío (con o sin blancos dentro) o ya tiene hijos.
    Para meter varios hijos en un mismo nodo hay que usar esta función una sola vez: dos `Edicion` que reescriben
    el mismo nodo vacío o autocerrado se solaparían. `ValueError` si `fragmentos` está vacío."""
    if not fragmentos:
        raise ValueError("insertar_hijos necesita al menos un fragmento")
    salto = _salto(texto)
    s = sangria_hijo(texto, nodo)
    s_nodo = _sangria_de(texto, nodo.inicio)
    if nodo.cierra_inicio is None or _ultimo_hijo(texto, nodo) is None:
        cuerpo = f"{salto}{s}".join(fragmentos)
        if nodo.cierra_inicio is None:  # `<x ... />` -> `<x ...>` + hijos + `</x>`
            etiqueta = texto[nodo.inicio:nodo.abre_fin]
            corte = nodo.inicio + len(etiqueta.rstrip("> ").rstrip("/").rstrip())
            return Edicion(corte, nodo.fin, f">{salto}{s}{cuerpo}{salto}{s_nodo}</{nodo.tag}>")
        # sin hijos: lo que haya dentro (blancos) se sustituye
        return Edicion(nodo.abre_fin, nodo.cierra_inicio, f"{salto}{s}{cuerpo}{salto}{s_nodo}")
    ultimo = _ultimo_hijo(texto, nodo)
    en_linea_propia = texto[:ultimo.inicio].rstrip(" \t").endswith("\n")
    union = salto + s if en_linea_propia else ""
    return Edicion(ultimo.fin, ultimo.fin, "".join(union + f for f in fragmentos))


def insertar_hijo(texto: str, nodo: Nodo, fragmento: str) -> Edicion:
    """Añade un `fragmento` como último hijo de `nodo` (ver `insertar_hijos`, a la que delega). Para varios hijos
    en el mismo nodo no encadenes llamadas: usa `insertar_hijos`."""
    return insertar_hijos(texto, nodo, [fragmento])


def quitar(nodo: Nodo, texto: str) -> Edicion:
    """Quita el elemento con el salto de línea y la sangría que lo preceden (si está en su propia línea)."""
    k = nodo.inicio
    while k > 0 and texto[k - 1] in " \t":
        k -= 1
    if k > 0 and texto[k - 1] == "\n":
        k -= 2 if k > 1 and texto[k - 2] == "\r" else 1
    else:
        k = nodo.inicio
    return Edicion(k, nodo.fin, "")


def _escapar_atributo(valor: str) -> str:
    return (valor.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            .replace("\r", "&#xD;").replace("\n", "&#xA;").replace("\t", "&#x9;"))


def poner_atributo(texto: str, nodo: Nodo, nombre: str, valor: str) -> Edicion:
    """Cambia el valor de `nombre` (solo ese atributo) o lo añade al final de la etiqueta de apertura."""
    etiqueta = texto[nodo.inicio:nodo.abre_fin]
    nuevo = _escapar_atributo(valor)
    ultimo_fin = None
    for m in _ATRIBUTO.finditer(etiqueta, 1 + len(nodo.tag)):
        if m.group(1) == nombre:
            g = 2 if m.group(2) is not None else 3
            comilla = '"' if g == 2 else "'"
            if comilla == "'":
                nuevo = nuevo.replace("&quot;", '"').replace("'", "&apos;")
            return Edicion(nodo.inicio + m.start(g), nodo.inicio + m.end(g), nuevo)
        ultimo_fin = m.end()
    if ultimo_fin is None:
        ultimo_fin = 1 + len(nodo.tag)
    pos = nodo.inicio + ultimo_fin
    return Edicion(pos, pos, f' {nombre}="{nuevo}"')


def _escapar_texto(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fragmento(elem: ET.Element, prefijos: dict[str, str], sangria: str, salto: str) -> str:
    """Serializa `elem` con los prefijos del documento y sin declaraciones `xmlns`. La primera línea sale sin
    sangría; las siguientes llevan `sangria` más dos espacios por nivel (`sangria` es la del propio elemento). Los
    elementos vacíos salen como `<x ... />`, igual que el Studio. `prefijos` mapea prefijo -> URI (o URI -> prefijo)."""
    por_uri = {u: p for p, u in prefijos.items()} if not any(k.startswith(("http:", "https:")) for k in prefijos) \
        else dict(prefijos)

    def nombre(n: str) -> str:
        if n.startswith("{"):
            uri, local = n[1:].split("}", 1)
            if uri not in por_uri:
                raise ValueError(f"Espacio de nombres sin prefijo en el documento: {uri}")
            return f"{por_uri[uri]}:{local}"
        return n

    def ser(e: ET.Element, nivel: int) -> str:
        pad = sangria + "  " * nivel
        attrs = "".join(f' {nombre(k)}="{_escapar_atributo(v)}"' for k, v in e.attrib.items())
        hijos = list(e)
        texto = (e.text or "").strip()
        if not hijos and not texto:
            return f"<{nombre(e.tag)}{attrs} />"
        if not hijos:
            return f"<{nombre(e.tag)}{attrs}>{_escapar_texto(e.text)}</{nombre(e.tag)}>"
        cuerpo = "".join(f"{salto}{pad}  {ser(h, nivel + 1)}" for h in hijos)
        return f"<{nombre(e.tag)}{attrs}>{cuerpo}{salto}{pad}</{nombre(e.tag)}>"

    return ser(elem, 0)
