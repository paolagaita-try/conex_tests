"""Generador de perfiles personalizados (solo Subscription): `profiles.xsd` de `bonita-profile-model:1.2.2`."""
import re
import unicodedata
import xml.etree.ElementTree as ET

NS_PERFILES = "http://documentation.bonitasoft.com/profile-xml-schema/1.0"

# Perfil de los roles que administran parámetros: lo referencia la app de administración de parámetros.
PERFIL_ADMIN_PARAMETROS = "AdministracionParametros"
# Rol con el que el módulo reconoce a la superadministración de parámetros (`Autorizacion.ROL` de parametros-core): sin
# él, la API de parámetros no deja escribir a nadie. Lo reciben los usuarios de los roles de «Quién administra».
ROL_ADMIN_PARAMETROS = "superAdministradorParametros"
# Usuario por defecto del Deploy del Studio («Default user name»): el Studio inicia sesión con él tras desplegar. Toda
# organización generada lo trae (`con_administrador_studio`) con el rol de administración de la plataforma.
USUARIO_STUDIO = "walter.bates"
ROL_ADMINISTRADOR = "administrador"
# Perfiles por defecto de Bonita y a quién se mapean en `default_profile.xml`: User a todos los roles (todo usuario de
# la organización entra a sus aplicaciones), Administrator y Process manager al rol `administrador`.
PERFILES_POR_DEFECTO = ("User", "Administrator", "Process manager")


def archivo_perfil(nombre: str) -> str:
    """Fichero de `app/profiles/` del perfil `nombre` (R-16: el nombre puede llevar espacios y acentos): minúsculas,
    sin acentos, espacios → «-» y fuera lo que no sea `[a-z0-9_-]`. Para los nombres de la 0.10.0 (`\\w+` sin
    acentos) es el nombre en minúsculas, como antes («Jefes» → `jefes.xml`); el «_» se conserva por eso. Un nombre
    con «/» o «\\» es ValueError (lo rechaza antes `validar/organizacion.py`)."""
    if re.search(r"[/\\\\]", nombre) or nombre.strip(". ") == "":
        raise ValueError(f"el nombre del perfil «{nombre}» tiene separadores de ruta o solo puntos: su fichero quedaría "
                         "fuera del proyecto (app/profiles/)")
    plano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9_-]", "", re.sub(r"\s+", "-", plano.strip()))
    return f"{slug or 'perfil'}.xml"


def generar_perfiles(org: dict, perfiles: list[dict]) -> ET.ElementTree | None:
    """Un `profile` por entrada, mapeado a los roles de la entrada (todos deben existir en `org["roles"]`).
    `None` si no hay perfiles."""
    if not perfiles:
        return None
    raiz = ET.Element("profiles:profiles", {"xmlns:profiles": NS_PERFILES})
    for p in perfiles:
        desconocidos = [r for r in p["roles"] if r not in org["roles"]]
        if desconocidos:
            raise ValueError(f"el perfil {p['nombre']} usa roles que no están en la organización: {desconocidos}")
        nodo = ET.SubElement(raiz, "profile", {"name": p["nombre"], "isDefault": "false"})
        ET.SubElement(nodo, "description").text = f"Perfil {p['nombre']} (roles: {', '.join(p['roles'])})"
        roles = ET.SubElement(ET.SubElement(nodo, "profileMapping"), "roles")
        for r in p["roles"]:
            ET.SubElement(roles, "role").text = r
    return ET.ElementTree(raiz)


def generar_perfiles_por_defecto(org: dict) -> ET.ElementTree:
    """`default_profile.xml`: los perfiles por defecto con sus mapeos por rol. Sin él, el Studio crea uno que mapea el
    rol `member` de su organización de ejemplo y, tras reiniciar su servidor, ningún usuario del proyecto entra. La
    organización debe traer el rol `administrador` (`con_administrador_studio`); si no, ValueError."""
    if ROL_ADMINISTRADOR not in org["roles"]:
        raise ValueError(f"la organización no tiene el rol {ROL_ADMINISTRADOR} (con_administrador_studio)")
    raiz = ET.Element("profiles:profiles", {"xmlns:profiles": NS_PERFILES})
    for nombre in PERFILES_POR_DEFECTO:
        nodo = ET.SubElement(raiz, "profile", {"name": nombre, "isDefault": "true"})
        ET.SubElement(nodo, "description").text = (
            "Perfil por defecto de Bonita (no cambiar nombre ni descripción en el runtime); mapeo generado por el arnés.")
        mapeo = ET.SubElement(nodo, "profileMapping")
        for vacio in ("users", "groups", "memberships"):
            ET.SubElement(mapeo, vacio)
        roles = ET.SubElement(mapeo, "roles")
        for r in (org["roles"] if nombre == "User" else [ROL_ADMINISTRADOR]):
            ET.SubElement(roles, "role").text = r
    return ET.ElementTree(raiz)
