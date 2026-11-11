"""R-14: bloque generado de `app/permisos/dynamic-permissions-checks-custom.properties` (fichero mixto: lo demás es del
proyecto). Las reglas son clases Groovy escritas a mano; el arnés solo lleva sus líneas de properties."""
from __future__ import annotations

from pathlib import Path

INICIO = "# >>> generado: reglas dinamicas"
FIN = "# <<< generado: reglas dinamicas"
PROPIEDADES = Path("bonita-project/app/permisos/dynamic-permissions-checks-custom.properties")
_CABECERA = ("# Comprobaciones dinamicas propias (solo Subscription). Lo entre los marcadores lo genera el arnes desde\n"
             "# bdm.md > Acceso al BDM; lo demas es del proyecto.\n")


def bloque(spec: dict) -> str:
    lineas = [l for r in (spec.get("acceso") or {}).get("reglas", []) for l in r["lineas"]]
    return "".join(f"{x}\n" for x in [INICIO, *lineas, FIN])


def extraer_bloque(texto: str) -> str | None:
    ini, fin = texto.find(INICIO), texto.find(FIN)
    return None if ini == -1 or fin <= ini else texto[ini:fin + len(FIN)]


def _latin1(texto: str) -> bytes:
    return "".join(c if ord(c) < 256 else f"\\u{ord(c):04x}" for c in texto).encode("iso-8859-1")


def generar_propiedades(spec: dict, existente: bytes | None) -> bytes:
    nuevo = bloque(spec)
    if existente is None:
        return _latin1(_CABECERA + nuevo)
    t = existente.decode("iso-8859-1")
    ini, fin = t.find(INICIO), t.find(FIN)
    if ini != -1 and fin > ini:
        fin = t.find("\n", fin)
        fin = len(t) if fin == -1 else fin + 1
        return _latin1(t[:ini] + nuevo + t[fin:])
    return _latin1(t + ("" if t.endswith("\n") or not t else "\n") + nuevo)
