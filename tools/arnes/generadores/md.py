"""Lector de Markdown de la documentación (`docs/07-bonita/*.md`). Solo biblioteca estándar."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)
_TITULO = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_CAMPO = re.compile(r"^\s*(?:-\s+)?\*\*(.+?)\*\*(?:\s*\([^)]*\))?\s*:\s*(.*)$")
_PIPE = "\x00"


def _celdas(linea: str) -> list[str]:
    linea = linea.strip().replace("\\|", _PIPE)
    if linea.startswith("|"):
        linea = linea[1:]
    if linea.endswith("|"):
        linea = linea[:-1]
    out = []
    for c in linea.split("|"):
        c = c.replace(_PIPE, "|").strip()
        out.append(re.sub(r"<br\s*/?>", "\n", c, flags=re.IGNORECASE))
    return out


class Fila(dict):
    """Fila de una tabla: celda por título de columna. `sobrantes` son las celdas de más que trae la línea respecto a
    la cabecera (las descarta el dict); un lector las usa para detectar un `|` sin escapar dentro de una celda (D-59)."""

    sobrantes: list[str]

    def __init__(self, *args, sobrantes: list[str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sobrantes = list(sobrantes or [])


def _es_separador(linea: str) -> bool:
    return bool(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?", linea.strip()))


def codigo(celda: str) -> str:
    """Quita un par de backticks exterior."""
    c = celda.strip()
    if len(c) >= 2 and c.startswith("`") and c.endswith("`"):
        return c[1:-1]
    return c


def lista(celda: str, sep: str = ";") -> list[str]:
    return [p.strip() for p in celda.split(sep) if p.strip()]


@dataclass
class Seccion:
    titulo: str
    nivel: int
    texto: str = ""
    tablas: list[list[dict[str, str]]] = field(default_factory=list)
    hijas: list["Seccion"] = field(default_factory=list)

    def _recorrer(self):
        for h in self.hijas:
            yield h
            yield from h._recorrer()

    def seccion(self, prefijo: str) -> "Seccion":
        buscado = prefijo.replace("`", "")
        for s in self._recorrer():
            if s.titulo.replace("`", "").startswith(buscado):
                return s
        raise KeyError(f"No hay sección que empiece por {prefijo!r} en {self.titulo!r}. "
                       f"Disponibles: {[s.titulo for s in self._recorrer()]}")

    def campo(self, nombre: str) -> str | None:
        for linea in self.texto.splitlines():
            m = _CAMPO.match(linea)
            if m and m.group(1).strip() == nombre:
                return m.group(2).strip()
        return None


@dataclass
class Documento:
    frontmatter: dict[str, str]
    raiz: Seccion

    def seccion(self, prefijo: str) -> Seccion:
        buscado = prefijo.replace("`", "")
        for s in self.raiz._recorrer():
            if s.titulo.replace("`", "").startswith(buscado):
                return s
        raise KeyError(f"No hay sección que empiece por {prefijo!r}. "
                       f"Disponibles: {[s.titulo for s in self.raiz._recorrer()]}")


def _frontmatter(lineas: list[str]) -> tuple[dict[str, str], int]:
    if not lineas or lineas[0].strip() != "---":
        return {}, 0
    fm: dict[str, str] = {}
    for i in range(1, len(lineas)):
        if lineas[i].strip() == "---":
            return fm, i + 1
        if lineas[i].lstrip().startswith("#") or ":" not in lineas[i]:
            continue
        clave, valor = lineas[i].split(":", 1)
        valor = re.sub(r"(^|\s)#.*$", "", valor).strip()
        fm[clave.strip()] = valor
    return {}, 0  # sin cierre: no es frontmatter


def leer_markdown(texto: str) -> Documento:
    texto = _COMENTARIO.sub("", texto.replace("\r\n", "\n"))
    lineas = texto.split("\n")
    fm, inicio = _frontmatter(lineas)
    raiz = Seccion("", 0)
    pila = [raiz]
    actual = raiz
    prosa: list[str] = []
    bloque: list[str] = []
    en_codigo = False

    def cerrar_tabla():
        if len(bloque) >= 2 and _es_separador(bloque[1]):
            cab = _celdas(bloque[0])
            filas = []
            for l in bloque[2:]:
                c = _celdas(l)
                sobrantes = c[len(cab):]
                c = (c + [""] * len(cab))[:len(cab)]
                filas.append(Fila(zip(cab, c), sobrantes=sobrantes))
            actual.tablas.append(filas)
        else:
            prosa.extend(bloque)
        bloque.clear()

    def cerrar_seccion():
        cerrar_tabla()
        actual.texto = "\n".join(prosa).strip()
        prosa.clear()

    for linea in lineas[inicio:]:
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        m = None if en_codigo else _TITULO.match(linea)
        if m:
            cerrar_seccion()
            nueva = Seccion(m.group(2), len(m.group(1)))
            while pila[-1].nivel >= nueva.nivel:
                pila.pop()
            pila[-1].hijas.append(nueva)
            pila.append(nueva)
            actual = nueva
        elif not en_codigo and linea.lstrip().startswith("|"):
            bloque.append(linea)
        else:
            cerrar_tabla()
            prosa.append(linea)
    cerrar_seccion()
    return Documento(fm, raiz)
