"""Organización de `bdm.md` (Plan 5, R-01): rutas de grupo, varios roles por actor, líneas **Grupos**/**Roles** y
tabla de usuarios con *manager* y correo.

Formato (contrato del Plan 5, §2.2):

- Tabla de actores: Grupo = una ruta (`` `/a/b` `` o `` `a` ``); Rol = uno o varios tokens separados por «, »;
  Membresía de prueba = los tokens fuera de paréntesis; Actor filter necesario, informativa. Una fila con «—» en Grupo
  y en Rol no entra en la organización ni en ningún actor mapping (Buzón, Sistema).
- Líneas opcionales «**Grupos** (n): …» y «**Roles** (n): …»: declaran grupos y roles aunque nadie los use; deben
  contener todos los que usan actores y usuarios.
- Tabla opcional de usuarios (primera columna `Usuario`): Usuario (uno o varios tokens), Grupo / rol (membresías
  «`ruta` / `rol`» separadas por «; », la primera es la principal), *Manager* y Correo (opcional).

Las rutas se guardan **sin barra inicial**; la lista de grupos lleva los intermedios y los padres antes que los hijos.
"""
from __future__ import annotations

import re

from generadores.leer import columna, donde, filas, sin_parentesis, tabla, vacio
from generadores.md import Seccion, codigo

_BACKTICKS = re.compile(r"`([^`]+)`")


def ruta_grupo(texto: str | None) -> str | None:
    """«`/a/b`» o «a» → «a/b»; celda vacía → None."""
    if texto is None or vacio(texto):
        return None
    tokens = _BACKTICKS.findall(texto)
    t = (tokens[0] if tokens else codigo(texto)).strip()
    return t.strip("/") or None


def con_ancestros(grupos: list[str]) -> list[str]:
    """Los grupos con sus intermedios, cada padre antes que sus hijos; el resto en el orden dado."""
    out: list[str] = []
    for g in grupos:
        partes = g.split("/")
        for i in range(1, len(partes) + 1):
            r = "/".join(partes[:i])
            if r not in out:
                out.append(r)
    return out


def _tokens(texto: str) -> list[str]:
    """Tokens de una celda de lista, sin las explicaciones entre paréntesis."""
    return [t.strip() for t in _BACKTICKS.findall(sin_parentesis(texto)) if t.strip()]


def _roles(celda: str) -> list[str]:
    if vacio(celda):
        return []
    return _tokens(celda) or [r.strip() for r in codigo(celda).split(",") if r.strip()]


def _membresia_de_prueba(celda: str) -> list[str]:
    """Usuarios de la columna «Membresía de prueba»: los tokens fuera de paréntesis; sin tokens, separados por «,»."""
    if vacio(celda):
        return []
    tokens = _tokens(celda)
    if tokens:
        return tokens
    return [codigo(x).strip() for x in sin_parentesis(celda).split(",") if x.strip() and not vacio(x)]


def _declarados(sec: Seccion, campo: str, normalizar) -> list[str] | None:
    valor = sec.campo(campo)
    if valor is None:
        return None
    return [normalizar(t) for t in _BACKTICKS.findall(sin_parentesis(valor))]


def _tabla_usuarios(sec: Seccion) -> list[dict[str, str]] | None:
    for t in sec.tablas:
        if t and list(t[0])[0] == "Usuario":
            return t
    return None


def _celda(fila: dict[str, str], nombre: str) -> str | None:
    """Valor de la columna cuyo título, sin asteriscos, empieza por `nombre` (la de *Manager* lleva cursiva)."""
    for k, v in fila.items():
        if k.replace("*", "").strip().startswith(nombre):
            return v
    return None


def leer_organizacion(sec: Seccion, ubic: str, errores: list[str]) -> dict:
    """La organización de la sección `## Organización` (sin perfiles ni contraseña, que lee `leer.bdm`)."""
    org: dict = {"grupos": [], "roles": [], "usuarios": [], "actores": {}}
    sin_organizacion: list[str] = []
    grupos_usados: list[str] = []
    roles_usados: list[str] = []
    de_actor: dict[str, list[str]] = {}  # usuario -> actores en cuya Membresía de prueba está
    orden: list[str] = []

    def usar(lista: list[str], x: str) -> None:
        if x not in lista:
            lista.append(x)

    for f in filas(tabla(sec, "Actor (actores-proceso.md)", ("Grupo", "Rol", "Membresía", "Actor filter"), ubic,
                         errores)):
        actor = codigo(f["Actor (actores-proceso.md)"]).strip()
        u = donde(ubic, actor)
        if actor in org["actores"] or actor in sin_organizacion:
            errores.append(f"{u}: actor repetido")
            continue
        grupo, roles = ruta_grupo(f["Grupo"]), _roles(f["Rol"])
        if grupo is None and not roles:
            sin_organizacion.append(actor)
            if _membresia_de_prueba(columna(f, "Membresía")):
                errores.append(f"{u}: un actor sin grupo ni rol («—» / «—») no tiene usuarios de prueba")
            continue
        if grupo is None or not roles:
            errores.append(f"{u}: el actor necesita grupo y rol («`/ruta`» y «`Rol`»), o «—» en los dos si no entra "
                           "en la organización")
            continue
        actor_d = {"grupo": grupo, "rol": roles[0]}
        if len(roles) > 1:
            actor_d["roles"] = roles
        org["actores"][actor] = actor_d
        usar(grupos_usados, grupo)
        for r in roles:
            usar(roles_usados, r)
        for usuario in _membresia_de_prueba(columna(f, "Membresía")):
            de_actor.setdefault(usuario, []).append(actor)
            usar(orden, usuario)

    # Tabla de usuarios: membresías propias, manager y correo.
    tabla_u: dict[str, dict] = {}
    t_usuarios = _tabla_usuarios(sec)
    if t_usuarios is not None:
        cab = list(t_usuarios[0])
        faltan = [c for c in ("Grupo / rol", "Manager") if not any(k.replace("*", "").strip().startswith(c)
                                                                    for k in cab)]
        if faltan:
            errores.append(f"{ubic}: a la tabla «Usuario | …» le faltan las columnas {faltan} (formato de la "
                           "plantilla)")
            t_usuarios = None
    for f in filas(t_usuarios):
        nombres = _tokens(f["Usuario"])
        uf = donde(ubic, ", ".join(nombres) or f["Usuario"])
        if not nombres:
            errores.append(f"{uf}: Usuario «{f['Usuario']}» debe ser uno o varios «`usuario`»")
            continue
        membresias = []
        celda = _celda(f, "Grupo / rol") or ""
        for parte in [p for p in celda.split(";") if p.strip()]:
            tokens = _BACKTICKS.findall(parte)
            if len(tokens) != 2 or "/" not in _BACKTICKS.sub("", parte):
                errores.append(f"{uf}: membresía «{parte.strip()}» debe ser «`ruta` / `rol`» (varias separadas por "
                               "«; »; nada de «ídem»)")
                continue
            membresias.append({"grupo": tokens[0].strip().strip("/"), "rol": tokens[1].strip()})
        if not membresias:
            if not any("debe ser «`ruta` / `rol`»" in e and e.startswith(uf) for e in errores):
                errores.append(f"{uf}: falta su membresía «`ruta` / `rol`»")
            continue
        manager_c = _celda(f, "Manager")
        manager = None if manager_c is None or vacio(manager_c) else (_tokens(manager_c) or [codigo(manager_c)])[0]
        correo_c = _celda(f, "Correo")
        correo = None if correo_c is None or vacio(correo_c) else (_tokens(correo_c) or [codigo(correo_c)])[0]
        for n in nombres:
            if n in tabla_u:
                errores.append(f"{donde(ubic, n)}: usuario repetido en la tabla de usuarios")
                continue
            tabla_u[n] = {"membresias": membresias, "manager": manager, "correo": correo}
            usar(orden, n)
        for m in membresias:
            usar(grupos_usados, m["grupo"])
            usar(roles_usados, m["rol"])

    extra: list[dict] = []
    for usuario in orden:
        actores = de_actor.get(usuario, [])
        propio = tabla_u.get(usuario)
        if propio is None:
            if len(actores) > 1:
                errores.append(f"{donde(ubic, actores[1])}: el usuario «{usuario}» ya es miembro de «{actores[0]}»; "
                               "un usuario de prueba sin fila en la tabla de usuarios tiene un solo grupo y rol")
            a = org["actores"][actores[0]]
            org["usuarios"].append({"nombre": usuario, "grupo": a["grupo"], "rol": a["rol"]})
            continue
        for actor in actores:
            a = org["actores"][actor]
            if not any(m["grupo"] == a["grupo"] and m["rol"] in a.get("roles", [a["rol"]])
                       for m in propio["membresias"]):
                errores.append(f"{donde(ubic, usuario)}: es usuario de prueba del actor «{actor}» y ninguna de sus "
                               f"membresías de la tabla de usuarios es «/{a['grupo']}» con uno de sus roles "
                               f"({', '.join(a.get('roles', [a['rol']]))})")
        principal, *resto = propio["membresias"]
        u = {"nombre": usuario, "grupo": principal["grupo"], "rol": principal["rol"]}
        if propio["manager"] is not None:
            u["manager"] = propio["manager"]
        if propio["correo"] is not None:
            u["correo"] = propio["correo"]
        org["usuarios"].append(u)
        for m in resto:
            extra.append({"usuario": usuario, "grupo": m["grupo"], "rol": m["rol"]})
    if extra:
        org["membresias"] = extra

    # Líneas Grupos / Roles: si están, mandan el orden y deben contener todo lo usado.
    for campo, usados, normalizar, clave in (("Grupos", grupos_usados, lambda t: t.strip().strip("/"), "grupos"),
                                             ("Roles", roles_usados, lambda t: t.strip(), "roles")):
        declarados = _declarados(sec, campo, normalizar)
        if declarados is None:
            org[clave] = list(usados)
            continue
        for x in usados:
            if x not in declarados:
                errores.append(f"{ubic}: «{x}» lo usa un actor o un usuario y no está en la línea «**{campo}**»")
        org[clave] = list(dict.fromkeys(declarados))
    org["grupos"] = con_ancestros(org["grupos"])
    if sin_organizacion:
        org["_sin_organizacion"] = sin_organizacion
    return org
