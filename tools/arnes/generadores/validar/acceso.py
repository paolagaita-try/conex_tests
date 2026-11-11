"""Validación de `spec["acceso"]["reglas"]` (R-14): forma de cada línea y referencias `check|X`."""
from __future__ import annotations

import re

from generadores.leer import donde

_LINEA = re.compile(r"(GET|POST|PUT|DELETE)\|([^=\s\[\]]+)=\[(.*)\]")
_CLASE = re.compile(r"[A-Z]\w*")
_CHECK = re.compile(r"check\|([^,\]]+)")


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    reglas = (spec.get("acceso") or {}).get("reglas") or []
    nombres = [r.get("nombre") for r in reglas]
    claves: set[str] = set()
    for r in reglas:
        n = r.get("nombre")
        if not isinstance(n, str) or not _CLASE.fullmatch(n):
            err.append(f"{donde('bdm.md', 'Acceso al BDM', 'Reglas dinámicas', n)}: «{n}» debe ser un nombre de clase "
                       "Groovy (empieza por mayúscula; solo letras, números y «_»)")
    vistos: set[str] = set()
    for i, r in enumerate(reglas):
        n = r.get("nombre")
        u = donde("bdm.md", "Acceso al BDM", "Reglas dinámicas", n)
        if n in vistos:
            err.append(f"{u}: regla repetida")
        vistos.add(n)
        for linea in r.get("lineas", []):
            m = _LINEA.fullmatch(linea)
            if not m:
                err.append(f"{u}: la línea «{linea}» debe ser «MÉTODO|recurso=[elemento, …]» con MÉTODO GET, POST, "
                           "PUT o DELETE (p. ej. GET|bdm/businessData/com.empresa.m.Solicitud=[check|MiRegla])")
                continue
            clave = f"{m.group(1)}|{m.group(2)}"
            if clave in claves:
                err.append(f"{u}: la clave «{clave}» está repetida (una sola línea por clave; "
                           "los elementos van todos en ella)")
            claves.add(clave)
            for c in (x.strip() for x in _CHECK.findall(m.group(3))):
                if c not in nombres:
                    err.append(f"{u}: «check|{c}» no es una regla de la tabla ({', '.join(map(str, nombres))})")
