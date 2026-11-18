"""Cirugía en la organización (`app/organizations/*.xml`): agrega grupos, roles, usuarios y membresías (spec 6.7).
Modificar, quitar y el resto lanzan `NotImplementedError`."""
import re
import xml.etree.ElementTree as ET

from generadores.escribir.organizacion import elemento_grupo, elemento_membresia, elemento_rol, elemento_usuario
from generadores.existente import xmi
from generadores.existente.cirugia import local, operacion, salto_de

CONTRASENA_DEFECTO = "bpm"  # la misma que usa el journey cuando la organización no declara una
_ROL_GRUPO = re.compile(r"^(.+?)\s*/\s*(.+)$")
_CLASES = ("grupo", "rol", "usuario", "membresia")


def _texto(e: ET.Element, etiqueta: str) -> str:
    return next(((h.text or "").strip() for h in e if local(h) == etiqueta), "")


def _lo_que_hay(raiz: ET.Element) -> tuple[set[str], set[str], set[str], set[tuple[str, str, str]]]:
    """Grupos (rutas), roles, usuarios, membresías `(usuario, rol, grupo)`."""
    grupos, roles, usuarios, membresias = set(), set(), set(), set()
    for e in raiz.iter():
        t = local(e)
        if t == "group":
            grupos.add(f"{e.get('parentPath', '').strip('/')}/{e.get('name')}".strip("/"))
        elif t == "role":
            roles.add(e.get("name"))
        elif t == "user":
            usuarios.add(e.get("userName"))
        elif t == "membership":
            membresias.add((_texto(e, "userName"), _texto(e, "roleName"),
                            f"{_texto(e, 'groupParentPath').strip('/')}/{_texto(e, 'groupName')}".strip("/")))
    return grupos, roles, usuarios, membresias


def _contenedor(nodos: list[xmi.Nodo], etiqueta: str) -> xmi.Nodo:
    n = next((n for n in nodos if n.tag == etiqueta), None)
    if n is None:
        raise ValueError(f"organización: el fichero no tiene <{etiqueta}>")
    return n


def cirugia_organizacion(texto: str, cambios: list[dict]) -> str:
    """`texto` (la organización) con los `cambios` aplicados: cada grupo, rol, usuario y membresía nuevo va al final
    de su lista. Los grupos se agregan padres primero. El usuario nuevo lleva siempre la contraseña de prueba `bpm` (nunca copia la de
    otro usuario); si su Detalle es «rol / grupo», recibe además esa membresía. Una referencia a un grupo, rol o
    usuario que no está en el fichero ni entre los cambios es `ValueError`."""
    for c in cambios:
        op, ubic = operacion(c), c.get("ubic", "cambios.md")
        if c["clase"] not in _CLASES:
            raise ValueError(f"{ubic}: la clase «{c['clase']}» no es de la organización")
        if op != "agrega":
            raise NotImplementedError(f"{ubic}: en la organización solo se agrega (no «{op}») en esta entrega")
    grupos, roles, usuarios, membresias = _lo_que_hay(ET.fromstring(texto))
    nuevos_g: list[str] = []
    nuevos_r: list[str] = []
    nuevos_u: list[dict] = []
    nuevas_m: list[tuple[str, str, str]] = []
    pendientes: list[tuple[str, str, str, str]] = []  # (usuario, rol, grupo, ubic): se validan al final

    for c in cambios:
        d, ubic = c["datos"], c.get("ubic", "cambios.md")
        if c["clase"] == "grupo":
            if d["ruta"] in grupos or d["ruta"] in nuevos_g:
                raise ValueError(f"{ubic}: el grupo «{d['ruta']}» ya existe en la organización")
            nuevos_g.append(d["ruta"])
        elif c["clase"] == "rol":
            if d["rol"] in roles or d["rol"] in nuevos_r:
                raise ValueError(f"{ubic}: el rol «{d['rol']}» ya existe en la organización")
            nuevos_r.append(d["rol"])
        elif c["clase"] == "usuario":
            if d["usuario"] in usuarios or any(u["nombre"] == d["usuario"] for u in nuevos_u):
                raise ValueError(f"{ubic}: el usuario «{d['usuario']}» ya existe en la organización")
            u = {"nombre": d["usuario"]}
            if d.get("detalle"):
                m = _ROL_GRUPO.match(d["detalle"])
                if m is None:
                    raise ValueError(f"{ubic}: el Detalle de un usuario nuevo debe ser «rol / grupo»")
                u["rol"] = m.group(1).strip("` ")
                pendientes.append((d["usuario"], u["rol"], m.group(2).strip("` /"), ubic))
            nuevos_u.append(u)
        else:
            if not d.get("rol") or not d.get("grupo"):
                raise ValueError(f"{ubic}: la membresía necesita rol y grupo")
            pendientes.append((d["usuario"], d["rol"], d["grupo"], ubic))
    for usuario, rol, grupo, ubic in pendientes:
        if (usuario, rol, grupo) in membresias:
            raise ValueError(f"{ubic}: «{usuario}» ya es «{rol}» en «{grupo}»")
        if (usuario, rol, grupo) not in nuevas_m:  # la del Detalle de un usuario y su fila de membresía son una
            nuevas_m.append((usuario, rol, grupo))

    todos_g = grupos | set(nuevos_g)
    for ruta in nuevos_g:
        madre = ruta.rpartition("/")[0]
        if madre and madre not in todos_g:
            raise ValueError(f"organización: el grupo «{ruta}» cuelga de «{madre}», que no existe")
    ubic_de = {(u, r, g): ub for u, r, g, ub in pendientes}
    for usuario, rol, grupo in nuevas_m:
        for nombre, existe, tipo in ((usuario, usuarios | {u["nombre"] for u in nuevos_u}, "usuario"),
                                     (rol, roles | set(nuevos_r), "rol"), (grupo, todos_g, "grupo")):
            if nombre not in existe:
                raise ValueError(f"{ubic_de[(usuario, rol, grupo)]}: el {tipo} «{nombre}» no existe en la "
                                 f"organización ni entre los cambios")

    nodos = xmi.indexar(texto)
    salto = salto_de(texto)
    ediciones: list[xmi.Edicion] = []

    def insertar(etiqueta: str, elementos: list[ET.Element]) -> None:
        if not elementos:
            return
        nodo = _contenedor(nodos, etiqueta)
        sangria = xmi.sangria_hijo(texto, nodo)
        ediciones.append(xmi.insertar_hijos(texto, nodo, [xmi.fragmento(e, {}, sangria, salto) for e in elementos]))

    insertar("users", [elemento_usuario(u, CONTRASENA_DEFECTO) for u in nuevos_u])
    insertar("roles", [elemento_rol(r) for r in nuevos_r])
    insertar("groups", [elemento_grupo(g) for g in sorted(nuevos_g, key=lambda g: g.count("/"))])
    insertar("memberships", [elemento_membresia(*m) for m in nuevas_m])
    return xmi.aplicar(texto, ediciones)
