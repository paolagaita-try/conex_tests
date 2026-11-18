"""Documentos del `.proc` (R-09, hilo `contratos-documentos`): `process:Document` del pool, inicialización desde el
contrato de instanciación y operaciones de documento en las tareas humanas.

Medido en el modelo y en el convertidor (no recordado):
- `process.ecore` 9.0.10: `Pool.documents` (contención) de `Document` con `multiple`, `documentType` (`NONE` por
  defecto, `CONTRACT`) y `contractInput` (referencia a un `ContractInput`).
- bonita2bar 9.0.10 (`SingleDocumentEngineDefinitionBuilder`, `MultipleDocumentEngineDefinitionBuilder`,
  `DocumentGroovyScriptExpressionFactory`): `documentType="CONTRACT"` da al documento (o a la lista) un valor inicial que
  es un script sobre el input; un input hijo se lee con su ruta (`padre.hijo`) y, con un múltiple en la jerarquía,
  `padre.collect{it.hijo}.flatten()`. Sin `mimeType` ni `url` no falla (comprueba nulos).
- `EngineExpressionUtil`: operando izquierdo `DOCUMENT_REF_TYPE` con el `Document` como `referencedElements` ->
  `DOCUMENT` o `DOCUMENT_LIST` según `multiple`; operadores `DOCUMENT_CREATE_UPDATE` y `DOCUMENT_LIST_SET`
  (`ExpressionConstants`) -> `ASSIGNMENT` en el motor.
- Motor 11.1.0 (`DocumentLeftOperandHandler`): un valor `null` **borra** el documento; un `DocumentValue(id)` sin
  cambios lo deja como está; `FileInputValue` con `id` y sin contenido, igual. Por eso la operación generada devuelve,
  si el input llega nulo, el documento vigente (`DocumentValue(id)`), y en una lista, la lista vigente: un FILE nulo
  conserva lo que había (R-09, C-7).

Bonita no tiene operaciones de instanciación: en `(instanciacion)` el documento se inicializa desde el contrato.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc.ids import elemento

INSTANCIACION = "(instanciacion)"
_RUTA = "_ruta_contrato"  # atributo temporal del Document hasta que `contratos.contrato` crea el ContractInput
DOCUMENT_VALUE = "org.bonitasoft.engine.bpm.document.DocumentValue"


def _nodo(entradas: list[dict], ruta: str) -> list[dict] | None:
    """Los nodos del contrato de la raíz a la hoja de `ruta`, o None si no existe."""
    camino, nivel = [], entradas
    for parte in ruta.split("."):
        n = next((x for x in nivel if x.get("nombre") == parte), None)
        if n is None:
            return None
        camino.append(n)
        nivel = n.get("hijos", [])
    return camino


def es_lista(camino: list[dict]) -> bool:
    """El input FILE de `camino` da varios archivos: él o algún antepasado es múltiple."""
    return any(n.get("multiple") for n in camino)


def comprobar(proceso: dict, contexto: str, entradas: list[dict], donde: str) -> list[tuple[dict, dict, list[dict]]]:
    """(operación de documento, documento, camino del input) de un contexto; ValueError si no cuadra."""
    por_nombre = {d["nombre"]: d for d in proceso.get("documentos", [])}
    out, vistos = [], set()
    for od in proceso.get("operaciones_documento", {}).get(contexto, []):
        u = f"{donde} › doc. {od.get('documento')}"
        d = por_nombre.get(od.get("documento"))
        if d is None:
            raise ValueError(f"{u}: el documento no está en Documentos del proceso del pool")
        camino = _nodo(entradas, od.get("input", ""))
        if camino is None or camino[-1].get("tipo") != "FILE":
            raise ValueError(f"{u}: «{od.get('input')}» no es un input FILE del contrato de este paso")
        if es_lista(camino) != bool(d.get("multiple")):
            raise ValueError(f"{u}: el input «{od['input']}» da {'varios archivos' if es_lista(camino) else 'uno'}; "
                             f"el documento debe ser {'múltiple' if es_lista(camino) else 'simple'}")
        if d["nombre"] in vistos:
            raise ValueError(f"{u}: dos inputs escriben el documento (uno por documento y paso)")
        vistos.add(d["nombre"])
        out.append((od, d, camino))
    return out


def documentos_del_pool(pool: ET.Element, proceso: dict, ids, entradas: list[dict]) -> None:
    """`documents` del pool, en el orden de `bpmn.md`. El que aporta la instanciación lleva `documentType="CONTRACT"`
    y, cuando exista, su `contractInput` (`enlazar_documentos`)."""
    desde_contrato = {d["nombre"]: od["input"] for od, d, _ in
                      comprobar(proceso, INSTANCIACION, entradas, f"proceso «{proceso['nombre']}» › {INSTANCIACION}")}
    for d in proceso.get("documentos", []):
        ruta = desde_contrato.get(d["nombre"])
        e = elemento(pool, "documents", "process:Document", ids,
                     {"name": d["nombre"], "multiple": "true" if d.get("multiple") else None,
                      "documentType": "CONTRACT" if ruta else None})
        if ruta:
            e.set(_RUTA, ruta)


def enlazar_documentos(padre: ET.Element, rutas: dict[str, str], donde: str) -> None:
    """Pone el `contractInput` de cada documento inicializado desde el contrato de `padre` (el pool)."""
    for e in padre.findall("documents"):
        ruta = e.attrib.pop(_RUTA, None)
        if ruta is None:
            continue
        if ruta not in rutas:
            raise ValueError(f"{donde}: el documento «{e.get('name')}» se inicializa desde «{ruta}», que no está en "
                             "el contrato de instanciación")
        e.set("contractInput", rutas[ruta])


def _acceso(camino: list[dict]) -> str:
    """Groovy que lee el input de `camino`: `a?.b`; con un múltiple en la jerarquía, la lista de sus archivos no
    nulos (`null` si no llega la raíz)."""
    expr, lista = camino[0]["nombre"], bool(camino[0].get("multiple"))
    for n in camino[1:]:
        if lista:
            expr += f"?.findAll {{ x -> x != null }}?.collect {{ x -> x.{n['nombre']} }}"
            if n.get("multiple"):
                expr += "?.flatten()"
        else:
            expr += f"?.{n['nombre']}"
            lista = bool(n.get("multiple"))
    if len(camino) > 1 and es_lista(camino):
        expr += "?.findAll { x -> x != null }"
    return expr


def _script(nombre: str, camino: list[dict], multiple: bool) -> str:
    """Operando derecho de la operación de documento. Escribe el documento por la API del caso al evaluarse y devuelve
    al motor el documento ya escrito sin cambios: el motor evalúa los operandos derechos de todas las operaciones de la
    tarea antes de persistir ninguno (D-114), así que sin esto una operación posterior de la misma tarea (la de la
    business variable entera que guarda su ID) no lo ve. Un `DocumentValue(id)` sin cambios lo deja como está (D-55)."""
    api = "apiAccessor.processAPI"
    if multiple:
        # Cada FILE como lo convierte el motor (`DocumentHelper.toDocumentValue`): sin id, nuevo; con id y contenido,
        # nueva versión de ese documento; con id y sin contenido, el mismo sin cambios.
        return "\n".join([
            f"def __archivos = {_acceso(camino)}",
            "if (__archivos != null) {",
            f"def __valores = __archivos.collect {{ a -> a.id == null ? new {DOCUMENT_VALUE}(a.content, a.contentType, "
            f"a.fileName) : a.content != null ? new {DOCUMENT_VALUE}(Long.valueOf(a.id), a.content, a.contentType, "
            f"a.fileName) : new {DOCUMENT_VALUE}(Long.valueOf(a.id)) }}",
            f"{api}.setDocumentList(processInstanceId, '{nombre}', __valores)",
            "}",
            "try {",
            f"return {api}.getDocumentList(processInstanceId, '{nombre}', 0, Integer.MAX_VALUE)"
            f".collect {{ d -> new {DOCUMENT_VALUE}(d.id) }}",
            "} catch (org.bonitasoft.engine.bpm.document.DocumentNotFoundException e) {", "return []", "}"])
    return "\n".join([
        f"def __archivo = {_acceso(camino)}",
        "def __vigente = null",
        "try {",
        f"__vigente = {api}.getLastDocument(processInstanceId, '{nombre}')",
        "} catch (org.bonitasoft.engine.bpm.document.DocumentNotFoundException e) {", "}",
        "if (__archivo == null) {",
        f"return __vigente == null ? null : new {DOCUMENT_VALUE}(__vigente.id)",
        "}",
        "if (__archivo.content == null) {", "return __archivo", "}",
        f"def __valor = new {DOCUMENT_VALUE}(__archivo.content, __archivo.contentType, __archivo.fileName)",
        f"def __escrito = __vigente == null ? {api}.addDocument(processInstanceId, '{nombre}', '', __valor) : "
        f"{api}.updateDocument(__vigente.id, __valor)",
        f"return new {DOCUMENT_VALUE}(__escrito.id)"])


def operaciones(tarea_e: ET.Element, proceso: dict, tarea: str, ctx, entradas: list[dict], donde: str) -> None:
    """Operaciones de documento de una tarea humana, antes de las demás (contrato §2.8): documento simple
    (`DOCUMENT_CREATE_UPDATE`) o lista (`DOCUMENT_LIST_SET`) desde su input FILE; un FILE nulo conserva el vigente. El
    operando derecho escribe el documento por la API (`_script`), así que las operaciones posteriores de la tarea ya lo
    ven (D-114, D-115)."""
    for od, d, camino in comprobar(proceso, tarea, entradas, donde):
        multiple = bool(d.get("multiple"))
        nombre = d["nombre"]
        o = elemento(tarea_e, "operations", "expression:Operation", ctx.ids)
        izq = elemento(o, "leftOperand", "expression:Expression", ctx.ids,
                       {"name": nombre, "content": nombre, "type": "DOCUMENT_REF_TYPE",
                        "returnType": "java.util.List" if multiple else DOCUMENT_VALUE})
        elemento(izq, "referencedElements", "process:Document", ctx.ids,
                 {"name": nombre, "multiple": "true" if multiple else None})
        ctx.script(o, "rightOperand", f"doc_{nombre}()", _script(nombre, camino, multiple),
                   "java.util.List" if multiple else "java.lang.Object")
        elemento(o, "operator", "expression:Operator", ctx.ids,
                 {"type": "DOCUMENT_LIST_SET" if multiple else "DOCUMENT_CREATE_UPDATE"})
