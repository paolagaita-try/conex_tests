"""Generador de la organización: `spec["organizacion"]` -> `app/organizations/<proyecto>.xml` (formato de `hola.xml`)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from generadores.escribir.perfiles import (PERFIL_ADMIN_PARAMETROS, ROL_ADMIN_PARAMETROS, ROL_ADMINISTRADOR,
                                           USUARIO_STUDIO)

NS_ORG = "http://documentation.bonitasoft.com/organization-xml-schema/1.1"


def membresias_de(org: dict, usuario: str) -> list[tuple[str, str]]:
    """(grupo, rol) de `usuario`: la principal de `org["usuarios"]` y las de `org["membresias"]`. Vacía si no está."""
    u = next((x for x in org.get("usuarios", []) if x.get("nombre") == usuario), None)
    if u is None:
        return []
    out = [(u.get("grupo"), u.get("rol"))]
    out += [(m.get("grupo"), m.get("rol")) for m in org.get("membresias", []) if m.get("usuario") == usuario]
    return out


def en_grupo(grupo_usuario: str | None, grupo_mapeo: str | None) -> bool:
    """¿El grupo del usuario es el del mapeo o uno de sus subgrupos? El motor amplía un actor mapping por membresía a
    los subgrupos: `/empresa` + `empleado` da `actorMember` también en `/empresa/rrhh` y `/empresa/rrhh/nomina`, y sus
    usuarios pueden iniciar el proceso (D-31, Community 2026.2-u0)."""
    if not grupo_usuario or not grupo_mapeo:
        return False
    return grupo_usuario == grupo_mapeo or grupo_usuario.startswith(grupo_mapeo + "/")


def actor_de_negocio(proceso: dict, nombre: str | None) -> str | None:
    """El actor de negocio que designa `nombre` (el iniciador): él mismo si es el actor de una lane, o el actor de
    negocio de la lane cuyo Actor Bonita es `nombre`."""
    if nombre is None:
        return None
    lanes = proceso.get("lanes", [])
    if any(l.get("actor") == nombre for l in lanes):
        return nombre
    return next((l.get("actor") for l in lanes if l.get("actor_bonita") == nombre), nombre)


def actor_bonita(lane: dict) -> str | None:
    """Nombre del actor de la lane en el `.proc` y el `.conf` (None si la lane va sin actor)."""
    if lane.get("sin_actor"):
        return None
    return lane.get("actor_bonita") or lane.get("actor")


def actor_iniciador(proceso: dict) -> str | None:
    """Actor Bonita iniciador: el de la lane del evento de inicio si su actor es el iniciador; si no, el de la primera
    lane con ese actor (de negocio o Bonita). None si el proceso no tiene iniciador."""
    ini = proceso.get("iniciador")
    if ini is None:
        return None
    lanes = [l for l in proceso.get("lanes", []) if actor_bonita(l)]
    inicio = next((n.get("lane") for n in proceso.get("nodos", []) if n.get("tipo") == "inicio"), None)
    candidatas = [l for l in lanes if ini in (l.get("actor"), actor_bonita(l))]
    lane = next((l for l in candidatas if l.get("nombre") == inicio), candidatas[0] if candidatas else None)
    return actor_bonita(lane) if lane else None


def actor_de_tarea(proceso: dict, tarea: str) -> dict | None:
    """El actor de nivel tarea (`proceso["actores_tarea"]`) que ejecuta `tarea`, o None."""
    return next((a for a in proceso.get("actores_tarea", []) if tarea in a.get("tareas", [])), None)


def candidato(org: dict, proceso: dict, tarea: str | None, usuario: str) -> bool:
    """¿Puede `usuario` ejecutar `tarea` de `proceso`? (o instanciarlo, si `tarea` es `None`).

    - Con actor de tarea (`actores_tarea`): alguna membresía del usuario tiene uno de sus `roles` (cualquier grupo)
      o es una de sus `membresias` (grupo y rol).
    - Si no, el actor de negocio de la lane de la tarea (o el del iniciador): alguna membresía del usuario es el grupo
      del actor con uno de sus roles (`roles`, o `rol` si no los hay). Una lane sin actor no tiene candidatos.
    Las membresías del usuario son la principal y las de `org["membresias"]`. Un usuario que no está en
    `org["usuarios"]` no es candidato; un actor que no está en `org["actores"]` no se compara (no hay con qué), igual
    que en la validación de caminos de la 0.10.0. Un mapeo por membresía incluye los subgrupos del grupo (`en_grupo`;
    D-31)."""
    suyas = membresias_de(org, usuario)
    if not suyas:
        return False
    if tarea is None:
        actor = actor_de_negocio(proceso, proceso.get("iniciador"))
    else:
        propio = actor_de_tarea(proceso, tarea)
        if propio is not None:
            return any(r in propio.get("roles", []) or any(m.get("rol") == r and en_grupo(g, m.get("grupo"))
                                                           for m in propio.get("membresias", []))
                       for g, r in suyas)
        lane_n = next((n.get("lane") for n in proceso.get("nodos", []) if n.get("id") == tarea), None)
        lane = next((l for l in proceso.get("lanes", []) if l.get("nombre") == lane_n), None)
        if lane is not None and lane.get("sin_actor"):
            return False
        actor = lane.get("actor") if lane else None
    esperado = org.get("actores", {}).get(actor)
    if esperado is None:
        return True
    roles = esperado.get("roles") or [esperado.get("rol")]
    return any(en_grupo(g, esperado.get("grupo")) and r in roles for g, r in suyas)


def _titulo(nombre: str) -> str:
    return nombre[:1].upper() + nombre[1:]


def _grupo_xml(padre: ET.Element, ruta: str) -> None:
    """`groupName` y, si el grupo no es raíz, `groupParentPath` (forma del `ACME.xml` del Studio 2026.2-u3)."""
    madre, _, nombre = ruta.rpartition("/")
    ET.SubElement(padre, "groupName").text = nombre
    if madre:
        ET.SubElement(padre, "groupParentPath").text = f"/{madre}"


def _membresia(padre: ET.Element, usuario: str, rol: str, grupo: str) -> None:
    padre.append(elemento_membresia(usuario, rol, grupo))


def elemento_usuario(u: dict, contrasena: str) -> ET.Element:
    """El `user` de `u` (`nombre` y, si lo hay, `rol`; `manager` y `correo` opcionales). Sin `rol` no lleva
    `lastName` ni `jobTitle`."""
    nodo = ET.Element("user", {"userName": u["nombre"]})
    ET.SubElement(nodo, "firstName").text = _titulo(u["nombre"])
    if u.get("rol"):
        ET.SubElement(nodo, "lastName").text = _titulo(u["rol"])
        ET.SubElement(nodo, "jobTitle").text = _titulo(u["rol"])
    if u.get("manager"):
        ET.SubElement(nodo, "manager").text = u["manager"]
    if u.get("correo"):
        ET.SubElement(ET.SubElement(nodo, "professionalData"), "email").text = u["correo"]
    ET.SubElement(nodo, "enabled").text = "true"
    ET.SubElement(nodo, "password", {"encrypted": "false"}).text = contrasena
    return nodo


def elemento_rol(rol: str) -> ET.Element:
    nodo = ET.Element("role", {"name": rol})
    ET.SubElement(nodo, "displayName").text = _titulo(rol)
    return nodo


def elemento_grupo(ruta: str) -> ET.Element:
    """El `group` de la ruta `a/b/c`: el grupo `c` con `parentPath="/a/b"`."""
    madre, _, nombre = ruta.rpartition("/")
    atrs = {"name": nombre, **({"parentPath": f"/{madre}"} if madre else {})}
    nodo = ET.Element("group", atrs)
    ET.SubElement(nodo, "displayName").text = _titulo(nombre)
    return nodo


def elemento_membresia(usuario: str, rol: str, grupo: str) -> ET.Element:
    nodo = ET.Element("membership")
    ET.SubElement(nodo, "userName").text = usuario
    ET.SubElement(nodo, "roleName").text = rol
    _grupo_xml(nodo, grupo)
    return nodo


def generar_organizacion(org: dict) -> ET.ElementTree:
    """Árbol de la organización: usuarios (contraseña en claro de `org["contrasena"]`; `manager` tras `jobTitle` y
    `professionalData/email` si el usuario los tiene), roles, grupos (una ruta `a/b/c` es el grupo `c` con
    `parentPath="/a/b"`; los padres van antes en `org["grupos"]`), una `membership` por usuario y, detrás, las de
    `org["membresias"]` (`usuario`, `rol`, `grupo`; las de la tabla de usuarios y las que añade
    `con_administradores`); en un grupo no raíz la membresía lleva `groupParentPath`. Orden de los hijos de `user`,
    `group` y `membership` como en el `ACME.xml` del Studio 2026.2-u3. La raíz lleva el `xmlns:organization`
    literal."""
    raiz = ET.Element("organization:Organization", {"xmlns:organization": NS_ORG})
    usuarios = ET.SubElement(raiz, "users")
    for u in org["usuarios"]:
        usuarios.append(elemento_usuario(u, org["contrasena"]))
    roles = ET.SubElement(raiz, "roles")
    for r in org["roles"]:
        roles.append(elemento_rol(r))
    grupos = ET.SubElement(raiz, "groups")
    for g in org["grupos"]:
        grupos.append(elemento_grupo(g))
    membresias = ET.SubElement(raiz, "memberships")
    for u in org["usuarios"]:
        _membresia(membresias, u["nombre"], u["rol"], u["grupo"])
    for extra in org.get("membresias", []):
        _membresia(membresias, extra["usuario"], extra["rol"], extra["grupo"])
    return ET.ElementTree(raiz)


_SEPARADOR_ROLES = re.compile(r"\s*(?:,|/|;|\s+y\s+)\s*")


def roles_que_administran(celda: str) -> list[str]:
    """Roles de la celda «Quién administra»: varios separados por «,», «/», «;» o « y »; se quitan los backticks.
    Una celda vacía o «—» no nombra a nadie."""
    limpia = celda.replace("`", "").strip()
    if not limpia or limpia.startswith("—") or limpia == "-":
        return []
    return [r.strip() for r in _SEPARADOR_ROLES.split(limpia) if r.strip()]


def _como_rol(rol: str, roles: list[str]) -> str | None:
    """El rol de la organización que el nombre designa (sin distinguir mayúsculas), o `None`."""
    return next((r for r in roles if r.casefold() == rol.casefold()), None)


def con_administradores(org: dict, filas: list[dict], errores: list[str]) -> dict:
    """Copia de `org` con lo que piden las filas del Catálogo de parámetros en «Quién administra» y «Doble control».

    - Un rol de «Quién administra» que no está en `org["roles"]` es un error (no se inventa el rol).
    - Todos los roles administradores forman el perfil `AdministracionParametros` (el que referencia la app de
      administración de parámetros); si el perfil ya existe, se le suman los roles.
    - Doble control: por cada rol de una fila con «Doble control = sí», dos usuarios de prueba `<rol>1` y `<rol>2`
      (rol en minúsculas y solo alfanuméricos) con la contraseña de prueba de la organización. Su grupo es el del
      primer usuario ya declarado con ese rol o, si no hay, el primer grupo de la organización. Si el usuario ya
      existe con ese rol se respeta; si existe con otro rol es un error.
    - El módulo de parámetros solo deja escribir al rol `superAdministradorParametros` (`ROL_ADMIN_PARAMETROS`): si hay
      administradores, ese rol entra en la organización y cada usuario de un rol administrador (los de doble control
      también) recibe una membership más con él, en su mismo grupo (`salida["membresias"]`). Así quien administra un
      parámetro según el catálogo puede administrarlo en la app de parámetros. Decisión: «Quién administra» se traduce
      a superadministración (el módulo no tiene administradores por parámetro; las delegaciones son por ámbito)."""
    salida = {**org, "perfiles": [dict(p) for p in org.get("perfiles", [])], "usuarios": list(org.get("usuarios", [])),
              "roles": list(org.get("roles", [])), "membresias": [dict(m) for m in org.get("membresias", [])]}
    roles = org.get("roles", [])
    administradores: list[str] = []
    doble: list[str] = []
    for f in filas:
        ubic = f"catalogo-parametros.md › Catálogo › {f['id']}"
        for nombre in roles_que_administran(f.get("administra", "")):
            rol = _como_rol(nombre, roles)
            if rol is None:
                errores.append(f"{ubic}: el rol «{nombre}» de «Quién administra» no está en los roles de la "
                               f"organización ({', '.join(roles) or 'ninguno'})")
                continue
            if rol not in administradores:
                administradores.append(rol)
            if f.get("doble_control") and rol not in doble:
                doble.append(rol)
    if administradores:
        perfil = next((p for p in salida["perfiles"] if p["nombre"] == PERFIL_ADMIN_PARAMETROS), None)
        if perfil is None:
            salida["perfiles"].append({"nombre": PERFIL_ADMIN_PARAMETROS, "roles": list(administradores)})
        else:
            perfil["roles"] = perfil["roles"] + [r for r in administradores if r not in perfil["roles"]]
    for rol in doble:
        base = re.sub(r"[^a-z0-9]", "", rol.lower())
        if not base:
            errores.append(f"organización: el rol «{rol}» no tiene caracteres alfanuméricos para nombrar a sus usuarios")
            continue
        grupo = next((u["grupo"] for u in salida["usuarios"] if u["rol"] == rol), None) \
            or (org.get("grupos") or [None])[0]
        if grupo is None:
            errores.append(f"organización: no hay ningún grupo donde sembrar a los usuarios del rol «{rol}»")
            continue
        for n in (1, 2):
            nombre = f"{base}{n}"
            previo = next((u for u in salida["usuarios"] if u["nombre"] == nombre), None)
            if previo is None:
                salida["usuarios"].append({"nombre": nombre, "grupo": grupo, "rol": rol})
            elif previo["rol"] != rol:
                errores.append(f"organización: el usuario de doble control «{nombre}» ya existe con el rol "
                               f"«{previo['rol']}», no «{rol}»")
    if administradores:
        if ROL_ADMIN_PARAMETROS not in salida["roles"]:
            salida["roles"].append(ROL_ADMIN_PARAMETROS)
        for u in salida["usuarios"]:
            extra = {"usuario": u["nombre"], "rol": ROL_ADMIN_PARAMETROS, "grupo": u["grupo"]}
            if u["rol"] in administradores and extra not in salida["membresias"]:
                salida["membresias"].append(extra)
    return salida


def con_administrador_studio(org: dict) -> dict:
    """Copia de `org` con el administrador que el Studio necesita: el rol `administrador` y el usuario `walter.bates`
    (el «Default user name» del Deploy del Studio) en el primer grupo, con la contraseña de prueba de la organización.
    Si el usuario ya está declarado con otro rol, se respeta y recibe además una membership con `administrador`.
    Idempotente. Sin grupos no hay dónde ponerlo: ValueError."""
    salida = {**org, "usuarios": list(org.get("usuarios", [])), "roles": list(org.get("roles", [])),
              "membresias": [dict(m) for m in org.get("membresias", [])]}
    if ROL_ADMINISTRADOR not in salida["roles"]:
        salida["roles"].append(ROL_ADMINISTRADOR)
    previo = next((u for u in salida["usuarios"] if u["nombre"] == USUARIO_STUDIO), None)
    if previo is None:
        if not org.get("grupos"):
            raise ValueError(f"organización sin grupos: no hay dónde poner al administrador {USUARIO_STUDIO}")
        salida["usuarios"].append({"nombre": USUARIO_STUDIO, "grupo": org["grupos"][0], "rol": ROL_ADMINISTRADOR})
    elif previo["rol"] != ROL_ADMINISTRADOR:
        extra = {"usuario": USUARIO_STUDIO, "rol": ROL_ADMINISTRADOR, "grupo": previo["grupo"]}
        if extra not in salida["membresias"]:
            salida["membresias"].append(extra)
    return salida
