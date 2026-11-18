"""Lector de `bdm.md` › Acceso al BDM › tabla «Regla dinámica» (R-14).

Cada fila nombra una clase Groovy (`bonita-project/app/permisos/reglas/<Regla>.groovy`, la escribe el proyecto) y las
líneas de `dynamic-permissions-checks-custom.properties` que la usan. Falta el fichero -> error; fichero sin fila ->
error. Devuelve `{"reglas": [{nombre, lineas}]}` o `{}` si no hay filas (así la spec de vacaciones no cambia).
"""
from __future__ import annotations

from pathlib import Path

from generadores.leer import columna, donde, filas, seccion, tabla, vacio
from generadores.md import Documento, codigo

F = "bdm.md"
REGLAS = Path("bonita-project/app/permisos/reglas")


def leer_acceso(doc: Documento | None, proyecto: Path | None = None) -> tuple[dict, list[str]]:
    errores: list[str] = []
    reglas: list[dict] = []
    if doc is not None:
        try:
            sec = doc.seccion("Acceso al BDM")
        except KeyError:
            sec = None  # la falta de la sección ya la anota el lector del BDM
        todas = [x for s in ([sec, *sec._recorrer()] if sec else []) for x in s.tablas
                 if x and list(x[0])[0] == "Regla dinámica"]
        if len(todas) > 1:  # la segunda se perdería en silencio (revisión final, M-5)
            errores.append(f"{donde(F, 'Acceso al BDM', 'Reglas dinámicas')}: hay {len(todas)} tablas «Regla dinámica "
                           "| …»; las reglas van en una sola tabla (una fila por regla)")
        t = None
        for s in ([sec, *sec._recorrer()] if sec else []):  # la tabla puede estar en una subsección
            t = tabla(s, "Regla dinámica", ("Líneas",), donde(F, "Acceso al BDM", "Reglas dinámicas"), errores)
            if t is not None:
                break
        for f in filas(t):
            nombre = codigo(f["Regla dinámica"]).strip()
            u = donde(F, "Acceso al BDM", "Reglas dinámicas", nombre)
            celda = columna(f, "Líneas")
            lineas = [] if vacio(celda) else [codigo(x.strip()) for x in celda.split("; ") if x.strip()]
            if not lineas:
                errores.append(f"{u}: la fila no trae líneas; debe ser una o varias líneas de "
                               "dynamic-permissions-checks-custom.properties, cada una entre backticks y separadas por "
                               "«; » (p. ej. `GET\\|bdm/businessData/com.empresa.m.Solicitud=[check\\|CasoPropioRule]`)")
            reglas.append({"nombre": nombre, "lineas": lineas})
    if proyecto is not None:
        carpeta = Path(proyecto) / REGLAS
        presentes = {p.stem for p in carpeta.glob("*.groovy")} if carpeta.is_dir() else set()
        for r in reglas:
            if r["nombre"] not in presentes:
                errores.append(f"{donde(F, 'Acceso al BDM', 'Reglas dinámicas', r['nombre'])}: falta el fichero "
                               f"{REGLAS.as_posix()}/{r['nombre']}.groovy (la clase de la regla, sin `package` e "
                               "`implements PermissionRule`)")
        if doc is not None:
            for n in sorted(presentes - {r["nombre"] for r in reglas}):
                errores.append(f"{REGLAS.as_posix()}/{n}.groovy: regla sin fila en {donde(F, 'Acceso al BDM', 'Regla dinámica')}")
    return ({"reglas": reglas} if reglas else {}), errores
