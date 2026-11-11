#!/usr/bin/env python3
"""Registra un módulo de `bonita-project/extensions/<modulo>/` en un proyecto del arnés (Plan 5, R-03/R-10).

Uso: `python3 herramientas/registrar_extension.py <proyecto> <modulo>`

Hace dos cosas, idempotentes, editando el texto (el resto de cada pom, comentarios incluidos, queda igual):

1. `<module><modulo></module>` al final de `<modules>` de `bonita-project/extensions/pom.xml`.
2. Una dependencia `${project.groupId}:<artifactId del módulo>:${project.version}` al final de `<dependencies>` de
   `bonita-project/app/pom.xml`: como `parametros-adaptador`, el jar del módulo viaja en el classpath del `.bar`, y
   el plugin de Bonita descubre los `.def`/`.impl` de sus dependencias para meter en el `.bar` la implementación
   que mapea cada `.conf` (D-14).

El módulo (su `pom.xml` con `artifactId` y su código) lo escribe el proyecto; el arnés no genera filtros ni
conectores propios. Sale 0 si queda registrado (o ya lo estaba) y 2 si no puede (módulo o proyecto que no existen).
"""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "{http://maven.apache.org/POM/4.0.0}"


class Error(Exception):
    pass


def _artifact_id(pom: Path) -> str:
    try:
        raiz = ET.parse(pom).getroot()
    except (ET.ParseError, OSError) as e:
        raise Error(f"{pom}: no se puede leer ({e})") from None
    a = raiz.findtext(f"{NS}artifactId") or raiz.findtext("artifactId")
    if not a or not a.strip():
        raise Error(f"{pom}: falta <artifactId>")
    return a.strip()


def _sangria(texto: str, cierre: str) -> str:
    m = re.search(r"\n([ \t]*)" + re.escape(cierre), texto)
    return m.group(1) if m else ""


def registrar(proyecto: Path, modulo: str) -> list[str]:
    """Registra `modulo` y devuelve lo que cambió (vacío si ya estaba)."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", modulo):
        raise Error(f"«{modulo}» no vale como nombre de módulo (solo letras, cifras, «.», «_» y «-»)")
    bp = Path(proyecto) / "bonita-project"
    ext_pom, app_pom = bp / "extensions" / "pom.xml", bp / "app" / "pom.xml"
    mod_pom = bp / "extensions" / modulo / "pom.xml"
    for f in (ext_pom, app_pom):
        if not f.is_file():
            raise Error(f"{f}: no existe (¿es un proyecto del arnés?)")
    if not mod_pom.is_file():
        raise Error(f"{mod_pom}: no existe; escribe primero el módulo «{modulo}» en bonita-project/extensions")
    artefacto = _artifact_id(mod_pom)
    cambios = []

    texto = ext_pom.read_text(encoding="utf-8")
    modulos = [m.text.strip() for m in ET.fromstring(texto).iter(f"{NS}module") if m.text]
    if modulo not in modulos:
        if "</modules>" not in texto:
            raise Error(f"{ext_pom}: no tiene <modules>")
        s = _sangria(texto, "</modules>")
        texto = texto.replace("</modules>", f"  <module>{modulo}</module>\n{s}</modules>", 1)
        ext_pom.write_text(texto, encoding="utf-8")
        cambios.append(f"{ext_pom.relative_to(proyecto)}: módulo {modulo}")

    texto = app_pom.read_text(encoding="utf-8")
    raiz = ET.fromstring(texto)
    deps = raiz.find(f"{NS}dependencies")
    ya = deps is not None and any((d.findtext(f"{NS}artifactId") or "").strip() == artefacto
                                  for d in deps.findall(f"{NS}dependency"))
    if not ya:
        # El primer </dependencies> tras <dependencies> de primer nivel: el de la plantilla está antes de <build>.
        m = re.search(r"\n([ \t]*)</dependencies>", texto)
        if m is None:
            raise Error(f"{app_pom}: no tiene <dependencies>")
        s = m.group(1)
        bloque = (f"\n{s}  <!-- Extensión del proyecto «{modulo}» (herramientas/registrar_extension.py): sus "
                  f".def/.impl\n{s}       entran al .bar con su jar. -->\n"
                  f"{s}  <dependency>\n{s}    <groupId>${{project.groupId}}</groupId>\n"
                  f"{s}    <artifactId>{artefacto}</artifactId>\n{s}    <version>${{project.version}}</version>\n"
                  f"{s}  </dependency>")
        texto = texto[:m.start()] + bloque + texto[m.start():]
        app_pom.write_text(texto, encoding="utf-8")
        cambios.append(f"{app_pom.relative_to(proyecto)}: dependencia {artefacto}")
    return cambios


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: registrar_extension.py <proyecto> <modulo>", file=sys.stderr)
        return 2
    try:
        cambios = registrar(Path(argv[0]), argv[1])
    except Error as e:
        print(f"registrar_extension: {e}", file=sys.stderr)
        return 2
    for c in cambios or [f"«{argv[1]}» ya estaba registrado"]:
        print(c)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
