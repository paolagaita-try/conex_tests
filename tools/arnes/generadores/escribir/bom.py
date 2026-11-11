"""Generador del BDM: `spec["bdm"]` -> `bom.xml` (esquema `bom.xsd` 1.2.2). Sin comentarios XML."""
import hashlib
import re
import xml.etree.ElementTree as ET
from functools import cache
from pathlib import Path

from generadores.version import RAIZ_REPO

NS_BOM = "http://documentation.bonitasoft.com/bdm-xml-schema/1.0"

CLASE_JAVA = {
    "STRING": "java.lang.String", "TEXT": "java.lang.String", "INTEGER": "java.lang.Integer",
    "LONG": "java.lang.Long", "DOUBLE": "java.lang.Double", "FLOAT": "java.lang.Float",
    "BOOLEAN": "java.lang.Boolean", "BYTE": "java.lang.Byte", "SHORT": "java.lang.Short",
    "CHAR": "java.lang.Character", "DATE": "java.util.Date", "LOCALDATE": "java.time.LocalDate",
    "LOCALDATETIME": "java.time.LocalDateTime", "OFFSETDATETIME": "java.time.OffsetDateTime",
}
# Los 8 objetos fijos del módulo de parámetros viajan en un fragmento de la plantilla (un BDM completo con solo ellos):
# no se reescriben en Python y entran siempre, tras los del dominio.
FRAGMENTO_PARAMETROS = RAIZ_REPO / "plantilla" / "bonita-project" / "bdm" / "parametros-kp.xml"
PAQUETE_PARAMETROS = "com.trycore.parametros.model"
# Devuelve de una consulta → returnType (R-05: `conteo` → Long, como los `countFor…`); `uno`, el propio objeto.
RETORNO = {"lista": "java.util.List", "conteo": "java.lang.Long"}
_RELACION = {"composicion": "COMPOSITION", "agregacion": "AGGREGATION"}


def _booleano(valor: bool) -> str:
    return "true" if valor else "false"


# Nombre de un índice o de una unique constraint (D-100, medido con el validador del BDM de bonita-common 11.1.0 y
# 11.1.3, `SQLNameValidator(25)` de `IndexValidationRule` y `UniqueConstraintValidationRule`): una letra y hasta 25
# letras ASCII, dígitos, `_`, `#` o `@` (26 caracteres como máximo), y no una palabra bloqueada (`blocked_db_keywords`
# de bonita-business-object-model 1.2.2, copiada tal cual en `palabras-sql-bloqueadas.txt`). Fuera de eso,
# `generate-bdm-model` falla con «… is not a valid SQL identifier».
MAX_NOMBRE_SQL = 26
_NOMBRE_SQL = re.compile(r"[A-Za-z][0-9A-Za-z_#@]{0,%d}" % (MAX_NOMBRE_SQL - 1))
_PALABRAS = Path(__file__).with_name("palabras-sql-bloqueadas.txt")
_HUELLA = 6


@cache
def _bloqueadas() -> frozenset[str]:
    return frozenset(p.strip() for p in _PALABRAS.read_text(encoding="utf-8").splitlines() if p.strip())


def nombre_sql_valido(nombre: str) -> bool:
    """¿Acepta Bonita `nombre` como nombre de índice o de unique constraint? (D-100)"""
    return bool(_NOMBRE_SQL.fullmatch(nombre)) and nombre.upper() not in _bloqueadas()


def nombre_restriccion(prefijo: str, objeto: str, campos: list[str]) -> str:
    """El nombre generado de un índice (`IX`) o de una unique constraint (`UK`): `<PREFIJO>_<OBJETO>_<ATRIBUTOS>` en
    mayúsculas si es válido (vacaciones y compras no cambian); si no (largo o con caracteres no ASCII), sus primeros 19
    caracteres válidos, `_` y los 6 primeros hexadecimales en mayúscula del sha1 del nombre completo: estable y distinto
    por objeto y lista de atributos (`IX_MODIFICACION_SOL_<HUELLA>`)."""
    completo = f"{prefijo}_{objeto}_{'_'.join(campos)}".upper()
    if nombre_sql_valido(completo):
        return completo
    huella = hashlib.sha1(completo.encode("utf-8")).hexdigest()[:_HUELLA].upper()
    base = re.sub(r"[^0-9A-Z_]", "", completo)[:MAX_NOMBRE_SQL - _HUELLA - 1].rstrip("_")
    return f"{base}_{huella}"


def nombre_de(obj: dict, clave: str, campos: list[str]) -> str:
    """El nombre del índice (`clave` = `indices`) o de la unique constraint (`unicos`) de `campos` en `obj`: el
    explícito de `bdm.md` («(nombre `X`)», `nombres_<clave>`) o el generado."""
    explicito = obj.get(f"nombres_{clave}", {}).get(",".join(campos))
    return explicito or nombre_restriccion("IX" if clave == "indices" else "UK", obj["nombre"], campos)


def _lista_campos(padre: ET.Element, campos: list[str]) -> None:
    nombres = ET.SubElement(padre, "fieldNames")
    for c in campos:
        ET.SubElement(nombres, "fieldName").text = c


def _sin_espacio_de_nombres(nodo: ET.Element) -> ET.Element:
    """`nodo` y sus hijos sin el `{ns}` de la etiqueta, y sin sangría heredada del fichero (la pone `xml_bytes`)."""
    for e in nodo.iter():
        e.tag = e.tag.rpartition("}")[2]
        e.text = (e.text or "").strip() or None
        e.tail = None
    return nodo


def objetos_parametros() -> list[ET.Element]:
    """Los `businessObject` fijos del módulo de parámetros, en el orden del fragmento."""
    raiz = ET.parse(FRAGMENTO_PARAMETROS).getroot()
    return [_sin_espacio_de_nombres(bo) for bo in raiz.iter(f"{{{NS_BOM}}}businessObject")]


def elemento_campo(paquete: str, a: dict) -> ET.Element:
    """El `field` (o `relationField` si `a["relacion"]`) de un atributo del BDM, sin colgar de ningún padre."""
    if a.get("relacion"):
        return ET.Element("relationField", {
            "type": _RELACION[a["relacion"]], "reference": f"{paquete}.{a['tipo']}",
            "fetchType": "LAZY", "name": a["nombre"], "nullable": _booleano(not a["obligatorio"]),
            "collection": _booleano(a["multiple"])})
    atrs = {"type": a["tipo"]}
    if a["tipo"] == "STRING" and a.get("longitud"):
        atrs["length"] = str(a["longitud"])
    atrs.update(name=a["nombre"], nullable=_booleano(not a["obligatorio"]), collection=_booleano(a["multiple"]))
    return ET.Element("field", atrs)


def elemento_objeto(paquete: str, obj: dict) -> ET.Element:
    """El `businessObject` de `obj` (`nombre`, `atributos` y, si los hay, `unicos`, `consultas`, `indices`)."""
    nombre = obj["nombre"]
    bo = ET.Element("businessObject", {"qualifiedName": f"{paquete}.{nombre}"})
    campos = ET.SubElement(bo, "fields")
    for a in obj["atributos"]:
        campos.append(elemento_campo(paquete, a))
    unicos = ET.SubElement(bo, "uniqueConstraints")
    for cols in obj.get("unicos", []):
        _lista_campos(ET.SubElement(unicos, "uniqueConstraint", {"name": nombre_de(obj, "unicos", cols)}), cols)
    consultas = ET.SubElement(bo, "queries")
    for q in obj.get("consultas", []):
        if q.get("por_defecto"):
            continue  # la genera Bonita (por atributo, por unique constraint o findByPersistenceId): no va aquí
        retorno = RETORNO.get(q["devuelve"], f"{paquete}.{nombre}")
        nodo = ET.SubElement(consultas, "query", {"name": q["nombre"], "content": q["jpql"], "returnType": retorno})
        if q["parametros"]:
            params = ET.SubElement(nodo, "queryParameters")
            for p in q["parametros"]:
                ET.SubElement(params, "queryParameter", {"name": p["nombre"], "className": CLASE_JAVA[p["tipo"]]})
    indices = ET.SubElement(bo, "indexes")
    for cols in obj.get("indices", []):
        _lista_campos(ET.SubElement(indices, "index", {"name": nombre_de(obj, "indices", cols)}), cols)
    return bo


def generar_bom(bdm: dict) -> ET.ElementTree:
    """Árbol de `bom.xml` para `bdm` (`paquete` y `objetos`) más los 8 `Kp*` fijos del módulo de parámetros. Los elementos van sin prefijo y la raíz lleva
    el atributo `xmlns` literal, para no registrar el espacio de nombres por defecto en `ElementTree`."""
    paquete = bdm["paquete"]
    raiz = ET.Element("businessObjectModel", {"xmlns": NS_BOM, "modelVersion": "1.0"})
    objetos = ET.SubElement(raiz, "businessObjects")
    for obj in bdm["objetos"]:
        objetos.append(elemento_objeto(paquete, obj))
    objetos.extend(objetos_parametros())
    return ET.ElementTree(raiz)
