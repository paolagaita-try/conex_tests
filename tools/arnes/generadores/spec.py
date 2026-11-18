"""De la documentación a una spec validada.

`construir_spec(proyecto)` lee `proyecto/.trycore-bonita.json`, `proyecto/docs/07-bonita/*.md`,
`proyecto/docs/08-construccion/*.md` y `proyecto/docs/.flow-state.json`, combina los lectores de `generadores.leer`,
resuelve el Groovy contra `expresiones.md` (por ID, comprobando huella y origen) y corre `validar_spec`.
`validar_spec(spec)` hace las comprobaciones cruzadas que solo dependen de la spec (sirve también para specs escritas
a mano). Cada error nombra fichero › sección › fila de la documentación. En modo existente (`modo: existente` en
`.trycore-bonita.json`) `caminos.md` es opcional: sin él la spec no lleva `caminos` (el arnés no corre el journey).

Convenciones de la spec:
- `procesos[0]` es el pool principal (frontmatter `pool` de `bpmn.md`); el resto, en el orden del documento. Las
  business variables de `bdm.md › Decisión de persistencia` son del pool principal; los demás pools no tienen.
- Referencias a datos: `<business variable>.<atributo>` (p. ej. `solicitud.estado`) o `<process variable>`.
- Los caminos son del pool principal; sus valores esperados van tipados según el BDM.
"""
from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path

from generadores.escribir.journey import nodo_de_paso
from generadores.escribir.organizacion import actor_de_tarea, candidato, con_administradores
from generadores.escribir.proc.datos import comprobar_groovy
from generadores.leer import EXPR, donde
from generadores.leer.bdm import devuelve, leer_bdm
from generadores.leer.bpmn import leer_bpmn
from generadores.leer.catalogo import leer_catalogo
from generadores.leer.construccion import (huella, leer_caminos, leer_consultas, leer_expresiones,
                                           texto_de_origen)
from generadores.leer.contratos import leer_contratos
from generadores.leer.acceso import leer_acceso
from generadores.leer.extensiones import leer_extensiones, leer_filtros
from generadores.leer.handoff import leer_handoff
from generadores.leer.matriz import F as FMATRIZ, leer_matriz
from generadores.md import Documento, leer_markdown
from generadores.nombres import GRUPO, MENSAJE, NOMBRE_PROYECTO, VERSION_POOL, es, nombre_pool_valido
from generadores import validar as _validar_extra
from generadores.version import cargar_version

TIPOS_BDM = ["STRING", "TEXT", "INTEGER", "DOUBLE", "LONG", "FLOAT", "DATE", "BOOLEAN", "BYTE", "SHORT", "CHAR",
             "LOCALDATETIME", "LOCALDATE", "OFFSETDATETIME"]
TIPOS_INPUT = ["TEXT", "INTEGER", "DECIMAL", "BOOLEAN", "DATE", "COMPLEX", "FILE", "LONG", "LOCALDATE",
               "LOCALDATETIME", "OFFSETDATETIME"]
# Process variables: los nombres de tipo que usa la documentación (los de contrato, sin COMPLEX ni FILE, más DOUBLE).
TIPOS_PV = ["TEXT", "BOOLEAN", "INTEGER", "LONG", "DOUBLE", "DECIMAL", "DATE", "LOCALDATE", "LOCALDATETIME",
            "OFFSETDATETIME"]
# Parámetros de proceso (doc 2026.2 `data/parameters.adoc`: text, Boolean, integer, double).
TIPOS_PARAM = ["String", "Integer", "Boolean", "Double"]
TIPOS_NODO = ["inicio", "fin", "humana", "script", "servicio", "llamada", "xor", "and", "timer_borde"]
ENTORNOS = ["Local", "Qualification", "Production"]
EDICIONES = ["community", "subscription"]
# Plantillas de persistencia que el arnés conoce (R-07). Cualquier otro nombre de la fila «Plantilla de persistencia»
# de `bdm.md` es una plantilla del proyecto (sus helpers son código de `extensions/`, el arnés no los conoce).
# `asignacion-directa`: una operación por atributo, sin helpers; no admite destinos `bv`.
PLANTILLAS = ["asignacion-directa"]
# Input de contrato → tipos de destino compatibles (atributo BDM o process variable).
COMPATIBLES = {"TEXT": {"STRING", "TEXT"}, "INTEGER": {"INTEGER"}, "LONG": {"LONG"},
               "DECIMAL": {"DOUBLE", "FLOAT", "DECIMAL"}, "BOOLEAN": {"BOOLEAN"}, "DATE": {"DATE"},
               "LOCALDATE": {"LOCALDATE"}, "LOCALDATETIME": {"LOCALDATETIME"}, "OFFSETDATETIME": {"OFFSETDATETIME"}}
ENTEROS, DECIMALES = {"INTEGER", "LONG", "SHORT", "BYTE"}, {"DOUBLE", "FLOAT"}
INSTANCIACION = "(instanciacion)"

FB, FP, FC, FCAM = "bdm.md", "bpmn.md", "contratos.md", "caminos.md"
SECCION_NODO = {"humana": "Inventario de tareas", "script": "Inventario de tareas", "servicio": "Inventario de tareas",
                "llamada": "Inventario de tareas", "xor": "Compuertas", "and": "Compuertas", "inicio": "Eventos",
                "fin": "Eventos", "timer_borde": "Eventos"}


# ---------------------------------------------------------------------------------------------------- lectura

def _leer_doc(ruta: Path, nombre: str, errores: list[str]) -> Documento | None:
    if not ruta.is_file():
        errores.append(f"{nombre}: falta el fichero ({ruta})")
        return None
    return leer_markdown(ruta.read_text(encoding="utf-8"))


def _leer_json(ruta: Path, nombre: str, errores: list[str]) -> dict | None:
    if not ruta.is_file():
        errores.append(f"{nombre}: falta el fichero ({ruta})")
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errores.append(f"{nombre}: JSON mal formado ({e})")
        return None
    if not isinstance(datos, dict):
        errores.append(f"{nombre}: debe ser un objeto JSON")
        return None
    return datos


def _proyecto(datos: dict | None, errores: list[str]) -> dict:
    claves = ["nombre", "grupo", "version_bonita", "edicion_destino"]
    datos = datos or {}
    proyecto = {k: datos.get(k) for k in claves}
    if not datos:
        return proyecto
    for k in claves:
        if not isinstance(datos.get(k), str) or not datos[k]:
            errores.append(f".trycore-bonita.json › {k}: falta o no es texto")
    if proyecto["edicion_destino"] and proyecto["edicion_destino"] not in EDICIONES:
        errores.append(f".trycore-bonita.json › edicion_destino: «{proyecto['edicion_destino']}» debe ser "
                       f"{' o '.join(EDICIONES)}")
    if isinstance(proyecto["version_bonita"], str) and proyecto["version_bonita"]:
        try:
            cargar_version(proyecto["version_bonita"])
        except ValueError as e:
            errores.append(f".trycore-bonita.json › version_bonita: {e}")
    # Edición del runtime local de desarrollo (el bundle del journey): solo si no es la de siempre, community (G-5).
    desarrollo = datos.get("edicion_desarrollo")
    if desarrollo is not None and desarrollo not in EDICIONES:
        errores.append(f".trycore-bonita.json › edicion_desarrollo: «{desarrollo}» debe ser {' o '.join(EDICIONES)}")
    elif desarrollo not in (None, "community"):
        proyecto["edicion_desarrollo"] = desarrollo
    return proyecto


def _sin_temporales(x):
    if isinstance(x, dict):
        return {k: _sin_temporales(v) for k, v in x.items() if not k.startswith("_")}
    if isinstance(x, list):
        return [_sin_temporales(v) for v in x]
    return x


class _Resolutor:
    """Sustituye cada marcador `{"$expresion": id, ...}` por el Groovy de `expresiones.md`."""

    def __init__(self, expresiones: dict[str, dict], docs: dict[str, Documento], errores: list[str]):
        self.expresiones, self.docs, self.errores = expresiones, docs, errores
        self.usadas: dict[str, str] = {}

    def resolver(self, x):
        if isinstance(x, dict):
            if EXPR in x:
                return self._uno(x)
            return {k: self.resolver(v) for k, v in x.items()}
        if isinstance(x, list):
            return [self.resolver(v) for v in x]
        return x

    def _uno(self, m: dict) -> str | None:
        id_, fuente, ubic = m[EXPR], m["fuente"], m["donde"]
        if id_ in self.usadas:
            self.errores.append(f"{ubic}: el ID de expresión «{id_}» ya lo usa {self.usadas[id_]}")
            return None
        self.usadas[id_] = ubic
        fila = self.expresiones.get(id_)
        if fila is None:
            self.errores.append(f"{ubic}: falta en expresiones.md (ID «{id_}», texto «{fuente}»)")
            return None
        u = donde("expresiones.md", "Expresiones", id_)
        if fila["huella"] != huella(fuente):
            self.errores.append(f"{u}: la huella {fila['huella']} no coincide con el texto de origen «{fuente}» "
                                f"({huella(fuente)}); revisa el Groovy y actualiza la fila")
        try:
            origen = texto_de_origen(fila["origen"], id_, self.docs)
            if " ".join(origen.split()) != " ".join(fuente.split()):
                self.errores.append(f"{u}: el Origen «{fila['origen']}» apunta a «{origen}», no a {ubic}")
        except ValueError as e:
            self.errores.append(f"{u}: el Origen «{fila['origen']}» no resuelve ({e})")
        if fila["groovy"]:
            # La misma comprobación que hace el escritor, aquí para que el error señale la fila de la documentación.
            try:
                comprobar_groovy(fila["groovy"], u)
            except ValueError as e:
                self.errores.append(str(e))
        return fila["groovy"] or None

    def sin_uso(self) -> None:
        for id_ in self.expresiones:
            if id_ not in self.usadas:
                self.errores.append(f"{donde('expresiones.md', 'Expresiones', id_)}: ninguna parte de la "
                                    "documentación pide esta expresión (fila sin uso)")


def _normalizar_ref(ref: str, bv_por_objeto: dict[str, str], ubic: str, errores: list[str],
                    nombres_bv: list[str] | None = None) -> str:
    """`Objeto.atributo` → `bv.atributo`; `pv x` → `x`; `bv x` (la business variable entera, R-07) → `x`.
    `nombres_bv` son las business variables del pool (por defecto, las de `bv_por_objeto`)."""
    if ref.startswith("pv "):
        return ref[3:].strip()
    if ref.startswith("bv "):
        nombre = ref[3:].strip()
        nombres = list(bv_por_objeto.values()) if nombres_bv is None else nombres_bv
        if nombre not in nombres:
            errores.append(f"{ubic}: «{ref}»: el pool no tiene la business variable «{nombre}» "
                           f"({', '.join(nombres) or 'ninguna'}; bdm.md › Decisión de persistencia)")
        return nombre
    if "." not in ref:
        errores.append(f"{ubic}: «{ref}» debe ser «Objeto.atributo» o «pv variable»")
        return ref
    objeto, atributo = ref.split(".", 1)
    if objeto not in bv_por_objeto:
        errores.append(f"{ubic}: «{ref}»: el pool no tiene business variable del objeto «{objeto}»")
        return ref
    return f"{bv_por_objeto[objeto]}.{atributo}"


def _combinar_bdm(parcial: dict, consultas: dict[tuple[str, str], dict], errores: list[str]) -> dict:
    """Pone a cada consulta de `bdm.md` su JPQL de `consultas.md`, que va por (Objeto, Consulta) (contrato §2.6.1)."""
    bdm = parcial["bdm"]
    usadas = set()
    for o in bdm["objetos"]:
        for q in o["consultas"]:
            u = donde(FB, "Objetos de negocio", o["nombre"], q["nombre"])
            clave = (o["nombre"], q["nombre"])
            fila = consultas.get(clave)
            if q.get("por_defecto"):
                # R-05: la genera Bonita; no lleva JPQL ni va a bom.xml.
                if fila is not None:
                    usadas.add(clave)
                    errores.append(f"{u}: es «(por defecto)» (la genera Bonita): no lleva JPQL; quítala de "
                                   "consultas.md")
                continue
            if fila is None:
                otros = sorted(ob for ob, n in consultas if n == q["nombre"] and ob != o["nombre"])
                if otros:
                    errores.append(f"{u}: consultas.md la pone en el objeto «{'», «'.join(otros)}» (falta su fila "
                                   f"con Objeto «{o['nombre']}»)")
                else:
                    errores.append(f"{u}: falta su JPQL en consultas.md")
                continue
            usadas.add(clave)
            leido = devuelve(fila["devuelve"]) or (fila["devuelve"], False)
            if fila["parametros"] != q["parametros"] or leido != (q["devuelve"], bool(q.get("paginada"))):
                errores.append(f"{u}: parámetros o «Devuelve» distintos en consultas.md")
            q["jpql"] = fila["jpql"]
    for objeto, nombre in consultas:
        if (objeto, nombre) not in usadas:
            errores.append(f"{donde('consultas.md', 'Consultas', f'{objeto}.{nombre}')}: no está en bdm.md (en el "
                           f"objeto «{objeto}»)")
    return bdm


def _pool_de_tarea(tarea: str, pista: str | None, procesos: list[dict], ubic: str, errores: list[str]) -> dict | None:
    candidatos = [p for p in procesos if any(n["id"] == tarea for n in p["nodos"])]
    if pista is not None:
        candidatos = [p for p in candidatos if p["nombre"] == pista]
    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        errores.append(f"{ubic}: la tarea «{tarea}» no está en bpmn.md" + (f" (pool «{pista}»)" if pista else ""))
    else:
        errores.append(f"{ubic}: la tarea «{tarea}» está en varios pools; indica «(pool `X`)»")
    return None


def _conector_de_servicio(p: dict, tarea: str, bloque: dict, errores: list[str]) -> list[str]:
    """Compara la columna Conector de `contratos.md` (el conjunto de tokens `conn_*`; sin ellos, la celda) con los
    conectores de la tarea en `bpmn.md` y devuelve los destinos que escriben sus salidas (hilo `extensiones`)."""
    celda = bloque["_conector"] or ""
    doc = sorted(set(re.findall(r"\bconn_\w+", celda)) or ({celda.strip()} if celda.strip() else set()))
    bpmn = sorted({c["id"] for c in p["conectores"] if c["tarea"] == tarea})
    if doc != bpmn:
        errores.append(f"{bloque['_ubic']}: Conector «{', '.join(doc) or '—'}»; bpmn.md dice "
                       f"«{', '.join(bpmn) or '—'}»")
    return [s["destino"] for c in p["conectores"] if c["tarea"] == tarea for s in c["salidas"]]


def _escribe_de_servicio(p: dict, bloque: dict, salidas: list[str], errores: list[str]) -> None:
    """Compara «Escribe» y «Process variables» con lo que escriben las operaciones y los conectores (hilo
    `persistencia`)."""
    destinos = [o["destino"] for o in bloque["operaciones"]] + salidas
    bdm_escrito = sorted({d for d in destinos if not d.startswith(("pv ", "bv "))})
    pv_escrita = sorted({d[3:] for d in destinos if d.startswith("pv ")})
    # R-07: lo que pertenece a un objeto cuya business variable tiene operación entera es informativo (también el
    # nombre del objeto solo); lo que escriben las operaciones por atributo y los conectores sigue siendo exacto.
    objeto_de = {b["nombre"]: b["objeto"] for b in p.get("business_variables", [])}
    enteros = {objeto_de.get(d[3:]) for d in destinos if d.startswith("bv ")} - {None}
    escribe = [e for e in bloque["_escribe"] if e in bdm_escrito or e.split(".", 1)[0] not in enteros]
    if sorted(set(escribe)) != bdm_escrito:
        errores.append(f"{bloque['_ubic']}: «Escribe» {bloque['_escribe']} no son los atributos que escriben "
                       f"sus operaciones y su conector {bdm_escrito}")
    if sorted(set(bloque["_pv"])) != pv_escrita:
        errores.append(f"{bloque['_ubic']}: «Process variables» {bloque['_pv']} no son las que escriben sus "
                       f"operaciones y su conector {pv_escrita}")


def _operaciones_documento(p: dict, contexto: str, contrato: dict) -> None:
    """Los inputs FILE con «doc. `<documento>`» del contrato de `contexto` -> `p["operaciones_documento"]` (hilo
    `contratos-documentos`; la clave solo existe si hay alguna, G-5)."""
    documentos = contrato.get("_documentos", [])
    if documentos:
        p.setdefault("operaciones_documento", {})[contexto] = [dict(d) for d in documentos]


def _combinar_procesos(bpmn: dict, contratos: dict, bdm_parcial: dict, errores: list[str]) -> list[dict]:
    principal = bpmn["principal"]["nombre"]
    procesos = sorted(bpmn["procesos"], key=lambda p: p["nombre"] != principal)
    org = bdm_parcial["organizacion"]
    persistencia = bdm_parcial["persistencia"]
    parametros = dict(bdm_parcial["parametros"])
    # R-07: familia de plantillas (`persistencia.plantillas`, nivel de lectura); sin ella, la plantilla única de hoy.
    familia = persistencia.get("plantillas") or ([persistencia["plantilla"]] if persistencia["plantilla"] else [])

    for p in procesos:
        p["business_variables"] = list(persistencia["business_variables"]) if p["nombre"] == principal else []
        p["parametros"] = parametros.pop(p["nombre"], [])
        p["contratos"], p["operaciones"] = {}, {}
        for l in p["lanes"]:
            # Grupo/rol de la lane: el conjunto {grupo, roles} del actor, en cualquier orden, barra inicial indiferente.
            ul = donde(FP, "Pool y lanes", p["nombre"], l["nombre"])
            actor = org["actores"].get(l["actor"])
            if not l.get("sin_actor") and l["actor"] in org.get("_sin_organizacion", []):
                errores.append(f"{ul}: el actor «{l['actor']}» va sin grupo ni rol en bdm.md («— / —»); la lane debe ir "
                               "sin actor («—» en la columna Actor Bonita) y sin tareas humanas")
            if actor and l["_grupo_rol"]:
                esperado = [actor["grupo"], *actor.get("roles", [actor["rol"]])]
                if set(l["_grupo_rol"]) != set(esperado):
                    errores.append(f"{ul}: grupo/rol {' / '.join(l['_grupo_rol'])} no es el del actor «{l['actor']}» "
                                   f"en bdm.md ({' / '.join(esperado)})")
        for n in p["nodos"]:
            u = donde(FP, "Inventario de tareas", p["nombre"], n["id"])
            if n["tipo"] == "humana" and n.get("_contrato") != f"ctr_{n['id']}":
                errores.append(f"{u}: Contrato «{n.get('_contrato') or '—'}» debe ser «ctr_{n['id']}»")
            elif n["tipo"] != "humana" and n.get("_contrato"):
                errores.append(f"{u}: solo las tareas humanas llevan contrato («{n['_contrato']}»)")
    for pool, ps in parametros.items():
        for prm in ps:
            errores.append(f"{donde(FB, 'Parámetros', prm['nombre'])}: el pool «{pool}» no está en bpmn.md")

    def plantilla(bloque: dict):
        nombre = bloque["plantilla"]
        if nombre and familia and nombre not in familia:
            errores.append(f"{bloque['_ubic']}: plantilla «{nombre}» distinta de la de bdm.md › Decisión de "
                           f"persistencia ({', '.join(f'«{x}»' for x in familia)})")
        enteras = [o["destino"] for o in bloque["operaciones"] if o["destino"].startswith("bv ")]
        if nombre in PLANTILLAS and enteras:
            errores.append(f"{bloque['_ubic']}: la plantilla «{nombre}» (una operación por atributo, sin helpers) no "
                           f"admite operaciones sobre la business variable entera ({', '.join(enteras)}); declara la "
                           "plantilla del proyecto en bdm.md › Decisión de persistencia")

    por_nombre = {p["nombre"]: p for p in procesos}
    for pool, bloque in contratos["instanciacion"].items():
        if pool not in por_nombre:
            errores.append(f"{bloque['_ubic']}: el pool «{pool}» no está en bpmn.md")
            continue
        plantilla(bloque)
        por_nombre[pool]["contratos"][INSTANCIACION] = bloque["contrato"]
        por_nombre[pool]["operaciones"][INSTANCIACION] = bloque["operaciones"]
        _operaciones_documento(por_nombre[pool], INSTANCIACION, bloque["contrato"])
    for tarea, bloque in contratos["tareas"].items():
        p = _pool_de_tarea(tarea, bloque["pool"], procesos, bloque["_ubic"], errores)
        if p is None:
            continue
        plantilla(bloque)
        p["contratos"][tarea] = bloque["contrato"]
        p["operaciones"][tarea] = bloque["operaciones"]
        _operaciones_documento(p, tarea, bloque["contrato"])
    for tarea, bloque in contratos["servicio"].items():
        p = _pool_de_tarea(tarea, None, procesos, bloque["_ubic"], errores)
        if p is None:
            continue
        plantilla(bloque)
        if tarea in p["operaciones"]:
            errores.append(f"{bloque['_ubic']}: la tarea «{tarea}» ya tiene operaciones en otra sección")
        p["operaciones"][tarea] = bloque["operaciones"]
        destinos_conector = _conector_de_servicio(p, tarea, bloque, errores)
        _escribe_de_servicio(p, bloque, destinos_conector, errores)

    for p in procesos:
        bv = {b["objeto"]: b["nombre"] for b in p["business_variables"]}
        nombres_bv = [b["nombre"] for b in p["business_variables"]]
        objetos_bv = [b["objeto"] for b in p["business_variables"]]
        for clave, ops in p["operaciones"].items():
            u = _ubic_operaciones(p, clave)
            for o in ops:
                objeto = o["destino"].split(".", 1)[0] if "." in o["destino"] else None
                if objeto and objetos_bv.count(objeto) > 1:
                    errores.append(f"{u}: «{o['destino']}» es ambiguo: el pool tiene varias business variables de "
                                   f"«{objeto}»; escribe la variable entera con un script (`bv <nombre>` ← …)")
                o["destino"] = _normalizar_ref(o["destino"], bv, u, errores, nombres_bv)
        for c in p["conectores"]:
            for s in c["salidas"]:
                s["destino"] = _normalizar_ref(s["destino"], bv, donde(FP, "Conectores por tarea", p["nombre"],
                                                                       c["tarea"]), errores)
        for n in p["nodos"]:
            if n["llamado"]:
                for e in n["llamado"]["entradas"]:
                    e["origen"] = _normalizar_ref(e["origen"], bv, donde(FP, "Inventario de tareas", p["nombre"],
                                                                         n["id"]), errores)
    return [{**p} for p in procesos]


def _tipar_esperados(caminos: list[dict], procesos: list[dict], bdm: dict, errores: list[str]) -> None:
    if not procesos:
        return
    objetos = {o["nombre"]: {a["nombre"]: a["tipo"] for a in o["atributos"]} for o in bdm["objetos"]}
    bv = {b["nombre"]: b["objeto"] for b in procesos[0]["business_variables"]}
    for c in caminos:
        for clave, valor in list(c["esperado"].items()):
            nombre_bv, _, atributo = clave.partition(".")
            tipo = objetos.get(bv.get(nombre_bv), {}).get(atributo)
            u = donde(FCAM, f"Camino `{c['id']}`", clave)
            try:
                if tipo in ENTEROS:
                    c["esperado"][clave] = int(valor)
                elif tipo in DECIMALES:
                    c["esperado"][clave] = float(valor)
                elif tipo == "BOOLEAN":
                    if valor not in ("true", "false"):
                        raise ValueError
                    c["esperado"][clave] = valor == "true"
            except ValueError:
                errores.append(f"{u}: «{valor}» no es un valor {tipo}")


FCAT = "catalogo-parametros.md"


def _combinar_parametros_negocio(proyecto: Path, nombres: list[str], declarados: list[str] | None,
                                 errores: list[str]) -> list[dict]:
    """Filas del Catálogo de los parámetros de negocio de `bdm.md`.

    El catálogo se lee siempre que exista, y cada fila suya debe tener su fila de Representación en
    `bdm.md › Parámetros` (negocio o técnica): una fila sin representación no entraría ni en la semilla ni en el
    `.conf`, y nada lo diría hasta que el proceso la pidiera en runtime (`declarados` es None si `bdm.md` no se pudo
    leer: ese error ya está dicho). Sin catálogo solo es error si `bdm.md` nombra parámetros de negocio."""
    ruta = proyecto / "docs" / "00-parametros" / FCAT
    if not ruta.is_file():
        if nombres:
            errores.append(f"{FCAT}: falta el fichero ({ruta}); hay parámetros de negocio en "
                           f"{donde(FB, 'Parámetros')}")
        return []
    filas = {f["id"]: f for f in leer_catalogo(ruta.read_text(encoding="utf-8"), errores)}
    for id_ in filas if declarados is not None else ():
        if id_ not in declarados:
            errores.append(f"{donde(FCAT, 'Catálogo', id_)}: no tiene fila de Representación en "
                           f"{donde(FB, 'Parámetros')} (módulo de parámetros o parámetro de proceso)")
    out = []
    for n in nombres:
        if n not in filas:
            errores.append(f"{donde(FB, 'Parámetros', n)}: no tiene fila en {FCAT} (docs/00-parametros/)")
        else:
            out.append(filas[n])
    return out


_PARAM = re.compile(r"param_\w+")


def _choques_con_el_manifiesto(proyecto: Path, matriz: dict, errores: list[str]) -> None:
    """Una página propia o un tema que se llama (id o recurso) como una entrada técnica o de administración del
    manifiesto del proyecto (`_semilla`, `_muestra`, `parametros`…) la pisaría al desplegar: error de `generar`."""
    ruta = proyecto / "frontend" / "forms.manifest.json"
    try:
        entradas = json.loads(ruta.read_text(encoding="utf-8")).get("formularios", [])
    except (OSError, ValueError, AttributeError):
        return
    tecnicas = [e for e in entradas if isinstance(e, dict) and e.get("tipo") not in ("negocio", "pagina", "tema")]
    propias = [(p["token"], p["recurso"], "la página propia") for p in matriz.get("paginas", [])]
    propias += [(t.removeprefix("custompage_"), t, "el tema") for t in
                dict.fromkeys(a["tema"] for a in matriz.get("aplicaciones", []) if a.get("tema"))]
    for id_, recurso, que in propias:
        for e in tecnicas:
            if id_ == e.get("id") or recurso == e.get("custompage"):
                errores.append(f"{donde(FMATRIZ, 'Aplicación')}: {que} «{recurso}» se llama como la entrada "
                               f"«{e.get('id')}» ({e.get('custompage')}, tipo {e.get('tipo')}) de "
                               f"frontend/forms.manifest.json, que es de la plantilla; dale otro nombre")


def _combinar_formularios(proyecto: Path, nombre: str | None, parametros_negocio: list[dict],
                          errores: list[str]) -> dict:
    """Lee la matriz de formularios y cruza el «Catálogo `param_*`» de cada campo con los parámetros de negocio."""
    ruta = proyecto / "docs" / "07-bonita" / FMATRIZ
    if not ruta.is_file():
        errores.append(f"{FMATRIZ}: falta el fichero ({ruta})")
        return {"formularios": [], "aplicaciones": []}
    try:
        matriz = leer_matriz(ruta.read_text(encoding="utf-8"), errores, nombre or "")
    except KeyError as e:
        errores.append(f"{FMATRIZ}: falta la columna o la sección {e} que pide el formato de la plantilla")
        return {"formularios": [], "aplicaciones": []}
    _choques_con_el_manifiesto(proyecto, matriz, errores)
    ids = {p["id"] for p in parametros_negocio}
    for f in matriz["formularios"]:
        for c in f["campos"]:
            for param in _PARAM.findall(c["catalogo"] or ""):
                if param not in ids:
                    errores.append(f"{donde(FMATRIZ, 'Detalle por formulario', f['id'], c['campo'])}: el catálogo "
                                   f"«{param}» no es un parámetro de negocio del módulo de parámetros "
                                   f"(Representación «módulo de parámetros» en {FB} › Parámetros)")
    return matriz


def construir_spec(proyecto: Path) -> tuple[dict, list[str]]:
    """Lee la documentación de `proyecto` y devuelve `(spec, errores)`. Con errores, la spec es parcial."""
    proyecto = Path(proyecto)
    errores: list[str] = []
    extra: dict = {}  # claves de nivel superior que añaden los hilos: `extra["…"] = …` en su punto de anclaje
    bonita, construccion = proyecto / "docs" / "07-bonita", proyecto / "docs" / "08-construccion"
    docs = {n: _leer_doc(bonita / n, n, errores) for n in ("bdm.md", "bpmn.md", "contratos.md", "handoff.md")}
    from generadores.existente.linea_base import modo_existente  # diferido: el modo existente importa la spec
    # En modo existente no hay journey (spec 6.4 y 6.8): sin `caminos.md` la spec no lleva caminos.
    sin_journey = modo_existente(proyecto) and not (construccion / FCAM).is_file()
    cons = {n: _leer_doc(construccion / n, n, errores)
            for n in ("expresiones.md", "consultas.md", *(() if sin_journey else (FCAM,)))}
    flow_state = _leer_json(proyecto / "docs" / ".flow-state.json", ".flow-state.json", errores)
    datos_proyecto = _leer_json(proyecto / ".trycore-bonita.json", ".trycore-bonita.json", errores)
    # Extensiones propias (filtros y conectores: `.def`/`.impl` de bonita-project/extensions), hilo `extensiones`.
    definiciones, errs_ext = leer_extensiones(proyecto / "bonita-project" / "extensions")
    errores.extend(errs_ext)
    if definiciones is not None:
        extra["extensiones"] = definiciones

    def leer(doc, lector, vacio):
        if doc is None:
            return vacio
        try:
            parcial, errs = lector(doc)
        except KeyError as e:
            nombre = next(k for k, v in {**docs, **cons}.items() if v is doc)
            errores.append(f"{nombre}: falta la columna o la sección {e} que pide el formato de la plantilla")
            return vacio
        errores.extend(errs)
        return parcial

    bdm_p = leer(docs["bdm.md"], leer_bdm, {"bdm": {"paquete": None, "objetos": []},
                                             "organizacion": {"grupos": [], "roles": [], "usuarios": [], "actores": {},
                                                              "perfiles": [], "contrasena": None},
                                             "parametros": {}, "parametros_negocio": [],
                                             "persistencia": {"business_variables": [],
                                                                                "plantilla": None}})
    bpmn_p = leer(docs["bpmn.md"], leer_bpmn, {"principal": {"nombre": None, "version": None}, "procesos": []})
    ctr_p = leer(docs["contratos.md"], leer_contratos, {"instanciacion": {}, "tareas": {}, "servicio": {}})
    expresiones = leer(cons["expresiones.md"], leer_expresiones, {})
    consultas = leer(cons["consultas.md"], leer_consultas, {})
    caminos = leer(cons.get(FCAM), leer_caminos, [])
    errores.extend(leer_handoff(docs["handoff.md"], flow_state)[1])
    # R-14 (hilo acceso): reglas dinámicas de `bdm.md` › Acceso al BDM
    acceso_p, errs_acceso = leer_acceso(docs["bdm.md"], proyecto)
    errores.extend(errs_acceso)
    if acceso_p:
        extra["acceso"] = acceso_p

    parametros_negocio = _combinar_parametros_negocio(proyecto, bdm_p.get("parametros_negocio", []),
                                                      bdm_p.pop("parametros_declarados", None), errores)
    bdm_p["organizacion"] = con_administradores(bdm_p["organizacion"], parametros_negocio, errores)
    formularios = _combinar_formularios(proyecto, (datos_proyecto or {}).get("nombre"), parametros_negocio, errores)
    bdm = _combinar_bdm(bdm_p, consultas, errores)
    procesos = _combinar_procesos(bpmn_p, ctr_p, bdm_p, errores)
    resolutor = _Resolutor(expresiones, {k: v for k, v in docs.items() if v is not None}, errores)
    procesos = _sin_temporales(resolutor.resolver(procesos))
    # Actor filters declarados en bdm.md › Organización, con su Groovy resuelto (hilo `extensiones`).
    filtros = leer(docs["bdm.md"], leer_filtros, {})
    if filtros:
        extra["filtros"] = _sin_temporales(resolutor.resolver(filtros))
    if cons["expresiones.md"] is not None:
        resolutor.sin_uso()
    _tipar_esperados(caminos, procesos, bdm, errores)
    spec = {"proyecto": _proyecto(datos_proyecto, errores), "bdm": bdm,
            "organizacion": _sin_temporales(bdm_p["organizacion"]), "parametros_negocio": parametros_negocio, "procesos": procesos,
            "caminos": caminos, "formularios": formularios}
    if sin_journey:
        del spec["caminos"]
    spec.update(extra)
    errores.extend(validar_spec(spec))
    return spec, list(dict.fromkeys(errores))


# ---------------------------------------------------------------------------------------------------- validación

def _ubic_nodo(p: dict, n: dict) -> str:
    return donde(FP, SECCION_NODO.get(n.get("tipo"), "Inventario de tareas"), p.get("nombre"), n.get("id"))


def _ubic_operaciones(p: dict, clave: str) -> str:
    if clave == INSTANCIACION:
        return donde(FC, "Contrato de instanciación", p.get("nombre"))
    tipo = next((n.get("tipo") for n in p.get("nodos", []) if n.get("id") == clave), None)
    if tipo == "humana":
        return donde(FC, "Contratos de tarea humana", f"ctr_{clave}")
    return donde(FC, "Operaciones de tareas de servicio y script", clave)


def _alcanzables(desde: str, sucesores: dict[str, list[str]]) -> set[str]:
    vistos, cola = set(), deque(sucesores.get(desde, []))
    while cola:
        x = cola.popleft()
        if x not in vistos:
            vistos.add(x)
            cola.extend(sucesores.get(x, []))
    return vistos


def _validar_bdm(bdm: dict, err: list[str]) -> dict[str, dict[str, dict]]:
    paquete = bdm.get("paquete") or ""
    if not re.fullmatch(r"[a-z]\w*(\.[a-z]\w*)*", paquete):
        err.append(f"{donde(FB, 'Convenciones')}: paquete «{paquete}» no es un paquete Java válido")
    objetos = bdm.get("objetos", [])
    nombres = [o.get("nombre") for o in objetos]
    atributos: dict[str, dict[str, dict]] = {}
    for o in objetos:
        u = donde(FB, "Objetos de negocio", o.get("nombre"))
        if nombres.count(o.get("nombre")) > 1:
            err.append(f"{u}: objeto repetido")
        atributos[o.get("nombre")] = {a.get("nombre"): a for a in o.get("atributos", [])}
        if not o.get("atributos"):
            err.append(f"{u}: el objeto no tiene atributos")
        vistos = set()
        for a in o.get("atributos", []):
            ua = donde(u, a.get("nombre"))
            if a.get("nombre") in vistos:
                err.append(f"{ua}: atributo repetido")
            vistos.add(a.get("nombre"))
            tipo = a.get("tipo")
            if a.get("relacion") is not None:
                if a.get("relacion") not in ("composicion", "agregacion"):
                    err.append(f"{ua}: relación «{a.get('relacion')}» debe ser composicion o agregacion")
                if tipo not in nombres:
                    err.append(f"{ua}: relación a «{tipo}», que no es un objeto del BDM ({', '.join(nombres)})")
            elif tipo in nombres:
                err.append(f"{ua}: el tipo «{tipo}» es un objeto; falta la relación (composición o agregación)")
            elif tipo not in TIPOS_BDM:
                err.append(f"{ua}: tipo «{tipo}» desconocido (permitidos: {', '.join(TIPOS_BDM)})")
            if a.get("longitud") is not None and tipo != "STRING":
                err.append(f"{ua}: la longitud solo aplica a STRING")
        for clave, titulo in (("unicos", "Unique constraints"), ("indices", "Índices")):
            for grupo in o.get(clave, []):
                for x in grupo:
                    if x not in vistos:
                        err.append(f"{donde(u, titulo)}: «{x}» no es un atributo de {o.get('nombre')}")
        for q in o.get("consultas", []):
            uq = donde(u, q.get("nombre"))
            if q.get("devuelve") not in ("lista", "uno", "conteo"):
                err.append(f"{uq}: Devuelve «{q.get('devuelve')}» debe ser lista, uno o conteo")
            if not q.get("jpql") and not q.get("por_defecto"):
                err.append(f"{uq}: falta su JPQL (consultas.md)")
            for prm in q.get("parametros", []):
                if prm.get("tipo") not in TIPOS_BDM:
                    err.append(f"{uq}: parámetro «{prm.get('nombre')}» de tipo «{prm.get('tipo')}» desconocido")
    return atributos


def _validar_organizacion(org: dict, err: list[str]) -> None:
    """Grupo y roles de cada actor, y grupo y rol de cada membresía (principal y extra), están en grupos/roles; los
    roles de los perfiles, en roles. Nombres, jerarquía y *manager*: `validar/organizacion.py`."""
    grupos, roles = org.get("grupos", []), org.get("roles", [])
    for actor, gr in org.get("actores", {}).items():
        roles_a = gr.get("roles") or [gr.get("rol")]
        if gr.get("grupo") not in grupos or any(r not in roles for r in roles_a):
            err.append(f"{donde(FB, 'Organización', actor)}: grupo/rol «{gr.get('grupo')}/{', '.join(map(str, roles_a))}» "
                       "no están en grupos/roles")
    for us in org.get("usuarios", []):
        if us.get("grupo") not in grupos or us.get("rol") not in roles:
            err.append(f"{donde(FB, 'Organización', us.get('nombre'))}: grupo/rol desconocidos")
    for m in org.get("membresias", []):
        if m.get("grupo") not in grupos or m.get("rol") not in roles:
            err.append(f"{donde(FB, 'Organización', m.get('usuario'))}: la membresía «/{m.get('grupo')} / "
                       f"{m.get('rol')}» tiene grupo o rol desconocidos")
    for pf in org.get("perfiles", []):
        for r in pf.get("roles", []):
            if r not in roles:
                err.append(f"{donde(FB, 'Acceso al BDM', 'Perfiles previstos', pf.get('nombre'))}: el rol «{r}» "
                           "no está en la organización")


def _tipo_de_ref(ref: str, p: dict, atributos: dict) -> tuple[bool, str | None]:
    """(existe, tipo) de una referencia `bv.atributo` o `pv`."""
    if "." in ref:
        bv, atributo = ref.split(".", 1)
        objeto = next((b.get("objeto") for b in p.get("business_variables", []) if b.get("nombre") == bv), None)
        a = atributos.get(objeto, {}).get(atributo)
        return (a is not None, a.get("tipo") if a else None)
    v = next((v for v in p.get("variables", []) if v.get("nombre") == ref), None)
    return (v is not None, v.get("tipo") if v else None)


def _es_bv_entera(ref, p: dict) -> bool:
    """`ref` (de una operación) es una business variable entera del pool: sin punto y con ese nombre (R-07). Una
    process variable con el mismo nombre la tapa (es error aparte: los nombres no pueden coincidir)."""
    return (isinstance(ref, str) and "." not in ref
            and any(b.get("nombre") == ref for b in p.get("business_variables", []))
            and not any(v.get("nombre") == ref for v in p.get("variables", [])))


def _ref_doc(ref: str, p: dict) -> str:
    """La referencia como la escribe la documentación (para los mensajes)."""
    if "." in ref:
        bv, atributo = ref.split(".", 1)
        objeto = next((b.get("objeto") for b in p.get("business_variables", []) if b.get("nombre") == bv), bv)
        return f"{objeto}.{atributo}"
    return f"pv {ref}"


def _rutas_input(inputs: list[dict], prefijo: str = "") -> dict[str, dict]:
    """Ruta (`a`, `a.b`, `a.b.c`…) -> input o hijo, a cualquier profundidad."""
    out = {}
    for i in inputs:
        ruta = f"{prefijo}{i.get('nombre')}"
        out[ruta] = i
        out.update(_rutas_input(i.get("hijos", []), ruta + "."))
    return out


def _validar_hijos(i: dict, ui: str, err: list[str]) -> None:
    """Hijos de un COMPLEX, a cualquier profundidad: un hijo COMPLEX tiene hijos y uno simple no."""
    nombres = [h.get("nombre") for h in i.get("hijos", [])]
    if len(set(nombres)) != len(nombres):
        err.append(f"{ui}: hijos repetidos")
    for h in i.get("hijos", []):
        if h.get("tipo") not in TIPOS_INPUT:
            err.append(f"{ui}: el hijo «{h.get('nombre')}» tiene tipo «{h.get('tipo')}» desconocido o no "
                       f"soportado (permitidos: {', '.join(TIPOS_INPUT)})")
        elif h.get("tipo") == "COMPLEX" and not h.get("hijos"):
            err.append(f"{ui}: el hijo COMPLEX «{h.get('nombre')}» necesita hijos")
        elif h.get("tipo") != "COMPLEX" and h.get("hijos"):
            err.append(f"{ui}: el hijo «{h.get('nombre')}» no es COMPLEX y tiene hijos")
        _validar_hijos(h, donde(ui, h.get("nombre")), err)


def _validar_contrato(c: dict, u: str, err: list[str]) -> None:
    nombres = []
    for i in c.get("inputs", []):
        ui = donde(u, i.get("nombre"))
        nombres.append(i.get("nombre"))
        if i.get("tipo") not in TIPOS_INPUT:
            err.append(f"{ui}: tipo de input «{i.get('tipo')}» desconocido (permitidos: {', '.join(TIPOS_INPUT)})")
        if i.get("tipo") == "COMPLEX" and not i.get("hijos"):
            err.append(f"{ui}: un input COMPLEX necesita hijos")
        if i.get("tipo") != "COMPLEX" and i.get("hijos"):
            err.append(f"{ui}: solo un input COMPLEX tiene hijos")
        _validar_hijos(i, ui, err)
    if len(set(nombres)) != len(nombres):
        err.append(f"{u}: inputs repetidos")
    for r in c.get("restricciones", []):
        if not r.get("groovy") or not r.get("mensaje"):
            err.append(f"{donde(u, r.get('nombre'))}: constraint sin Groovy o sin mensaje")


def _ubic_contrato(p: dict, clave: str) -> str:
    if clave == INSTANCIACION:
        return donde(FC, "Contrato de instanciación", p.get("nombre"))
    return donde(FC, "Contratos de tarea humana", f"ctr_{clave}")


def _validar_proceso(p: dict, procesos: list[dict], org: dict, atributos: dict, err: list[str]) -> None:
    nombre = p.get("nombre")
    nodos = p.get("nodos", [])
    por_id = {n.get("id"): n for n in nodos}
    lanes = [l.get("nombre") for l in p.get("lanes", [])]
    actores = org.get("actores", {})
    params = {prm.get("nombre"): prm for prm in p.get("parametros", [])}
    trans = p.get("transiciones", [])

    # Nombre y versión van al nombre del `.proc` (`<pool>-<versión>.proc`): nada de rutas.
    if not nombre_pool_valido(nombre):
        err.append(f"{donde(FP, 'Pool y lanes', str(nombre))}: «{nombre}» no vale como nombre del pool; "
                   f"{MENSAJE['pool']}")
    if not p.get("version"):
        err.append(f"{donde(FP, 'Pool y lanes', nombre)}: falta la versión del pool")
    elif not es(VERSION_POOL, p["version"]):
        err.append(f"{donde(FP, 'Pool y lanes', nombre)}: «{p['version']}»: {MENSAJE['version_pool']}")
    if p.get("iniciador") is not None:
        # El iniciador es un actor de negocio o el Actor Bonita de una lane (R-02).
        de_lane = [l for l in p.get("lanes", []) if not l.get("sin_actor")
                   and p["iniciador"] in (l.get("actor"), l.get("actor_bonita"))]
        if p["iniciador"] not in actores and not de_lane:
            err.append(f"{donde(FP, 'Pool y lanes', nombre)}: el iniciador «{p['iniciador']}» no es un actor de "
                       "bdm.md › Organización ni el Actor Bonita de una lane")
        elif not de_lane:
            err.append(f"{donde(FP, 'Pool y lanes', nombre)}: ninguna lane tiene el actor iniciador «{p['iniciador']}»")
    for l in p.get("lanes", []):
        if not l.get("sin_actor") and l.get("actor") not in actores:
            err.append(f"{donde(FP, 'Pool y lanes', nombre, l.get('nombre'))}: el actor «{l.get('actor')}» no está "
                       "en bdm.md › Organización")
    if len(set(lanes)) != len(lanes):
        err.append(f"{donde(FP, 'Pool y lanes', nombre)}: lanes repetidas")
    # El .proc nombra los nodos por su nombre (no por el id de la documentación): deben ser únicos en el pool.
    primero: dict[str, dict] = {}
    for n in nodos:
        previo = primero.setdefault(n.get("nombre"), n)
        if previo is not n:
            err.append(f"{_ubic_nodo(p, n)}: el nombre «{n.get('nombre')}» está repetido en el pool «{nombre}» "
                       f"(también lo lleva «{previo.get('id')}»); el nombre de cada nodo debe ser único")
    for b in p.get("business_variables", []):
        if b.get("objeto") not in atributos:
            err.append(f"{donde(FB, 'Decisión de persistencia', 'Business variables del pool')}: «{b.get('objeto')}» "
                       "no es un objeto del BDM")
    # (R-08: nombres repetidos, `multiple` y choque con process variables, en generadores/validar/persistencia.py.)
    for v in p.get("variables", []):
        if v.get("tipo") not in TIPOS_PV:
            err.append(f"{donde(FP, 'Process variables', nombre, v.get('nombre'))}: tipo «{v.get('tipo')}» "
                       f"desconocido (permitidos: {', '.join(TIPOS_PV)})")
    for prm in p.get("parametros", []):
        u = donde(FB, "Parámetros", prm.get("nombre"))
        if prm.get("tipo") not in TIPOS_PARAM:
            err.append(f"{u}: tipo «{prm.get('tipo')}» no soportado (permitidos: {', '.join(TIPOS_PARAM)})")
        for e in ENTORNOS:
            valor = (prm.get("valores") or {}).get(e)
            if not valor:
                err.append(f"{u}: falta el valor de {e}")
            elif prm.get("tipo") == "Integer" and not re.fullmatch(r"-?\d+", valor):
                err.append(f"{u}: el valor de {e} «{valor}» no es Integer")
            elif prm.get("tipo") == "Double" and not re.fullmatch(r"-?\d+(\.\d+)?", valor):
                err.append(f"{u}: el valor de {e} «{valor}» no es Double")
            elif prm.get("tipo") == "Boolean" and valor not in ("true", "false"):
                err.append(f"{u}: el valor de {e} «{valor}» no es Boolean")

    # Nodos
    ids = [n.get("id") for n in nodos]
    for n in nodos:
        u = _ubic_nodo(p, n)
        if ids.count(n.get("id")) > 1:
            err.append(f"{u}: ID repetido en el pool")
        if n.get("tipo") not in TIPOS_NODO:
            err.append(f"{u}: tipo de nodo «{n.get('tipo')}» desconocido")
        if n.get("lane") is None:
            err.append(f"{u}: no tiene lane (ni se deduce de su anfitriona, del iniciador o de su primer predecesor)")
        elif n.get("lane") not in lanes:
            err.append(f"{u}: la lane «{n.get('lane')}» no está en Pool y lanes ({', '.join(lanes)})")
        if len(n.get("documentacion") or "") > 255:
            err.append(f"{u}: la documentación tiene {len(n['documentacion'])} caracteres (máximo 255)")
        if n.get("tipo") == "timer_borde":
            anf = por_id.get(n.get("anfitrion"))
            if anf is None:
                err.append(f"{u}: la tarea anfitriona «{n.get('anfitrion')}» no está en el pool")
            elif anf.get("tipo") not in ("humana", "llamada"):
                err.append(f"{u}: borde en «{anf.get('id')}» ({anf.get('tipo')}); un timer de borde solo va en una "
                           "tarea humana o call activity (doc process/events)")
            if n.get("duracion") not in params:
                err.append(f"{u}: la duración «{n.get('duracion')}» debe ser un parámetro del pool "
                           f"({', '.join(params) or 'ninguno'})")
            if not isinstance(n.get("interruptor"), bool):
                err.append(f"{u}: falta si el borde es interruptor")
        if n.get("tipo") == "llamada":
            _validar_llamada(p, n, procesos, atributos, u, err)
        if n.get("tipo") == "humana" and n.get("id") not in p.get("contratos", {}):
            err.append(f"{u}: tarea humana sin contrato en contratos.md (ctr_{n.get('id')})")
    if [n.get("tipo") for n in nodos].count("inicio") != 1:
        err.append(f"{donde(FP, 'Eventos', nombre)}: el pool debe tener exactamente un evento de inicio")
    if "fin" not in [n.get("tipo") for n in nodos]:
        err.append(f"{donde(FP, 'Eventos', nombre)}: el pool no tiene evento de fin")

    # Transiciones
    sucesores: dict[str, list[str]] = {}
    entradas: dict[str, list[str]] = {}
    for t in trans:
        d, h = t.get("desde"), t.get("hacia")
        u = donde(FP, "Transiciones", nombre, f"{d}→{h}")
        for x in (d, h):
            if x not in por_id:
                err.append(f"{u}: «{x}» no es un nodo del pool")
        sucesores.setdefault(d, []).append(h)
        entradas.setdefault(h, []).append(d)
        tipo_d = por_id.get(d, {}).get("tipo")
        if por_id.get(h, {}).get("tipo") in ("inicio", "timer_borde"):
            err.append(f"{u}: no puede entrar una transición a un evento de inicio o de borde")
        if tipo_d == "fin":
            err.append(f"{u}: no puede salir una transición de un evento de fin")
        if tipo_d == "xor":
            if t.get("defecto") and t.get("expresion"):
                err.append(f"{u}: la salida por defecto no lleva condición")
            if not t.get("defecto") and not (t.get("expresion") or "").strip():
                err.append(f"{u}: salida no por defecto sin condición (sin Groovy en expresiones.md)")
        elif t.get("expresion") or t.get("defecto"):
            err.append(f"{u}: solo las salidas de una compuerta exclusiva llevan condición o «(por defecto)»")
    for n in nodos:
        u = _ubic_nodo(p, n)
        tipo = n.get("tipo")
        salen, entran = sucesores.get(n.get("id"), []), entradas.get(n.get("id"), [])
        if tipo != "fin" and not salen:
            err.append(f"{u}: no sale ninguna transición")
        if tipo not in ("inicio", "timer_borde") and not entran:
            err.append(f"{u}: no llega ninguna transición")
        if tipo == "xor":
            defectos = [t for t in trans if t.get("desde") == n.get("id") and t.get("defecto")]
            if len(defectos) != 1:
                err.append(f"{u}: compuerta exclusiva con {len(defectos)} salidas por defecto; debe tener una "
                           "(«(por defecto)»)")
            if len(salen) < 2:
                err.append(f"{u}: compuerta exclusiva con menos de dos salidas")

    # Borde interruptor en una rama de paralela que se une en un AND join. Cada fork se empareja con SU join: se
    # recorre cada rama desde el fork hasta el primer AND join que no cierra una paralela anidada, sin pasarlo (así
    # una tarea posterior al join, o un bucle de reproceso, no cuentan como rama; ni un join de otra paralela).
    forks = [n.get("id") for n in nodos if n.get("tipo") == "and" and len(sucesores.get(n.get("id"), [])) > 1]
    joins = {n.get("id") for n in nodos if n.get("tipo") == "and" and len(entradas.get(n.get("id"), [])) > 1}
    rama: dict[str, set[str]] = {}
    join_de: dict[str, set[str]] = {}
    for f in forks:
        en_rama: set[str] = set()
        cierres: set[str] = set()
        vistos: set[tuple[str, int]] = set()
        cola = deque((x, 0) for x in sucesores[f])
        while cola:
            x, prof = cola.popleft()
            if (x, prof) in vistos or prof > len(nodos):
                continue
            vistos.add((x, prof))
            if x in joins:
                if prof == 0:
                    cierres.add(x)
                    continue
                prof -= 1
            en_rama.add(x)
            if x in forks:
                prof += 1
            cola.extend((y, prof) for y in sucesores.get(x, []))
        rama[f], join_de[f] = en_rama, cierres
    for n in nodos:
        if n.get("tipo") != "timer_borde" or n.get("interruptor") is not True or n.get("anfitrion") not in por_id:
            continue
        for f in forks:
            if n["anfitrion"] in rama[f]:
                for j in sorted(join_de[f]):
                    err.append(f"{_ubic_nodo(p, n)}: borde interruptor en «{n['anfitrion']}», rama de la paralela "
                               f"«{f}» que se une en «{j}»: el join espera todas sus entradas y el caso se cuelga "
                               "(doc process/gateways)")

    # Contratos y operaciones
    humanas = {n.get("id") for n in nodos if n.get("tipo") == "humana"}
    for clave, c in p.get("contratos", {}).items():
        u = _ubic_contrato(p, clave)
        if clave != INSTANCIACION and clave not in humanas:
            err.append(f"{u}: «{clave}» no es una tarea humana del pool «{nombre}»")
        _validar_contrato(c, u, err)
    for clave, ops in p.get("operaciones", {}).items():
        u = _ubic_operaciones(p, clave)
        if clave != INSTANCIACION and clave not in por_id:
            err.append(f"{u}: «{clave}» no es una tarea del pool «{nombre}»")
        rutas = _rutas_input(p.get("contratos", {}).get(clave, {}).get("inputs", []))
        destinos = []
        for o in ops:
            destino, expr = o.get("destino"), o.get("expresion") or {}
            # R-07: destino sin punto que es una business variable = la variable entera (lo valida
            # `generadores/validar/persistencia.py`); aquí solo cuenta para «una operación por destino».
            if _es_bv_entera(destino, p):
                if destino in destinos:
                    err.append(f"{u}: dos operaciones escriben «bv {destino}» (una por business variable)")
                destinos.append(destino)
                continue
            existe, tipo_destino = _tipo_de_ref(destino, p, atributos)
            if not existe:
                err.append(f"{u}: destino «{_ref_doc(destino, p)}» no existe en bdm.md ni en Process variables")
            if destino in destinos:
                err.append(f"{u}: dos operaciones escriben «{_ref_doc(destino, p)}» (una por destino)")
            destinos.append(destino)
            if expr.get("tipo") not in ("input", "literal", "groovy"):
                err.append(f"{u}: operación sobre «{destino}» de tipo «{expr.get('tipo')}» desconocido")
            elif expr["tipo"] == "input":
                entrada = rutas.get(expr.get("valor"))
                if entrada is None:
                    err.append(f"{u}: el input «{expr.get('valor')}» no está en el contrato")
                elif existe and tipo_destino not in COMPATIBLES.get(entrada.get("tipo"), set()):
                    err.append(f"{u}: el input «{expr.get('valor')}» ({entrada.get('tipo')}) no cabe en "
                               f"«{_ref_doc(destino, p)}» ({tipo_destino})")
            elif expr["tipo"] == "groovy" and not expr.get("valor"):
                err.append(f"{u}: la operación sobre «{_ref_doc(destino, p)}» no tiene Groovy")

    # Conectores: una entrada por invocación (Plan 5, R-10). Lo que depende de las definiciones propias
    # (`extensiones`) lo valida `generadores/validar/extensiones.py`.
    conectores = p.get("conectores", [])
    if not isinstance(conectores, list):
        err.append(f"{donde(FP, 'Conectores por tarea', nombre)}: «conectores» debe ser una lista (una entrada por "
                   "invocación)")
        conectores = []
    for c in conectores:
        u = donde(FP, "Conectores por tarea", nombre, c.get("tarea"))
        id_ = c.get("id")
        tarea = por_id.get(c.get("tarea"))
        if tarea is None:
            err.append(f"{u}: la tarea no está en el pool")
        elif tarea.get("tipo") not in ("humana", "servicio", "script"):
            err.append(f"{u}: el conector «{id_}» va en «{tarea.get('id')}» ({tarea.get('tipo')}); un conector solo "
                       "va en una tarea humana, de servicio o de script")
        if c.get("tipo") not in ("rest-get", "propio"):
            err.append(f"{u}: tipo de conector «{c.get('tipo')}» no soportado (solo rest-get o propio)")
        if c.get("momento") not in ("entrada", "salida"):
            err.append(f"{u}: momento «{c.get('momento')}» debe ser entrada o salida")
        entradas = c.get("entradas") or {}
        if c.get("tipo") == "rest-get" and not entradas.get("url"):
            err.append(f"{u}: el conector no tiene Groovy de la URL ({id_}.url)")
        for nombre_e, groovy in entradas.items():
            if not groovy:
                err.append(f"{u}: la entrada «{nombre_e}» del conector «{id_}» no tiene Groovy en expresiones.md")
        for s in c.get("salidas", []):
            if not _tipo_de_ref(s.get("destino"), p, atributos)[0]:
                err.append(f"{u}: la salida a «{_ref_doc(s.get('destino'), p)}» no existe")
            if c.get("tipo") == "rest-get" and not s.get("json"):
                err.append(f"{u}: la salida a «{s.get('destino')}» no dice qué campo del JSON lee")
            if c.get("tipo") == "propio" and not s.get("salida"):
                err.append(f"{u}: la salida a «{s.get('destino')}» no dice qué salida del conector lee")
    for (tarea_, momento), grupo in _por_tarea_y_momento(conectores).items():
        if [c.get("orden") for c in grupo] != list(range(1, len(grupo) + 1)):
            err.append(f"{donde(FP, 'Conectores por tarea', nombre, tarea_)}: el orden de los conectores de "
                       f"«{momento}» debe ser 1…{len(grupo)} en el orden de la tabla")


def _por_tarea_y_momento(conectores: list[dict]) -> dict[tuple, list[dict]]:
    out: dict[tuple, list[dict]] = {}
    for c in conectores:
        out.setdefault((c.get("tarea"), c.get("momento")), []).append(c)
    return out


def _validar_llamada(p: dict, n: dict, procesos: list[dict], atributos: dict, u: str, err: list[str]) -> None:
    ll = n.get("llamado")
    if not ll:
        err.append(f"{u}: la call activity no dice a qué proceso llama")
        return
    hijo = next((q for q in procesos if q.get("nombre") == ll.get("proceso") and q.get("version") == ll.get("version")),
                None)
    if hijo is None:
        err.append(f"{u}: llama a «{ll.get('proceso')}» {ll.get('version')}, que no es un pool de bpmn.md")
        return
    if hijo is p:
        err.append(f"{u}: la call activity se llama a sí misma")
    inputs = {i.get("nombre"): i for i in hijo.get("contratos", {}).get(INSTANCIACION, {}).get("inputs", [])}
    mapeados = set()
    for e in ll.get("entradas", []):
        if e.get("input") not in inputs:
            err.append(f"{u}: «{e.get('input')}» no es un input de ctr_instanciacion de «{hijo.get('nombre')}»")
        mapeados.add(e.get("input"))
        if not _tipo_de_ref(e.get("origen"), p, atributos)[0]:
            err.append(f"{u}: el origen «{_ref_doc(e.get('origen'), p)}» no existe en el pool «{p.get('nombre')}»")
    for nombre, i in inputs.items():
        if i.get("obligatorio") and nombre not in mapeados:
            err.append(f"{u}: no envía el input obligatorio «{nombre}» de «{hijo.get('nombre')}»")


def _validar_caminos(spec: dict, atributos: dict, err: list[str]) -> None:
    procesos = spec.get("procesos", [])
    caminos = spec.get("caminos", [])
    if not procesos:
        return
    principal = procesos[0]
    org = spec.get("organizacion", {})
    usuarios = {us.get("nombre"): us for us in org.get("usuarios", [])}
    nodos_p = {n.get("id"): n for n in principal.get("nodos", [])}
    trans_p = {(t.get("desde"), t.get("hacia")) for t in principal.get("transiciones", [])}
    ids = [c.get("id") for c in caminos]
    for c in caminos:
        u = donde(FCAM, f"Camino `{c.get('id')}`")
        if ids.count(c.get("id")) > 1:
            err.append(f"{u}: camino repetido")
        if nodos_p.get(c.get("fin"), {}).get("tipo") != "fin":
            err.append(f"{u}: el fin esperado «{c.get('fin')}» no es un evento de fin de «{principal.get('nombre')}»")
        for s in c.get("salidas", []):
            g, _, d = s.partition("→")
            if nodos_p.get(g, {}).get("tipo") != "xor" or (g, d) not in trans_p:
                err.append(f"{u}: la salida cubierta «{s}» no es una salida de compuerta exclusiva de "
                           f"«{principal.get('nombre')}»")
        for i, paso in enumerate(c.get("pasos", []), 1):
            up = donde(u, str(i))
            tarea = paso.get("tarea")
            if tarea == "(esperar)":
                try:
                    nodo_de_paso(procesos, paso.get("evento"), {"timer_borde"}, "un timer de borde")
                except ValueError as e:
                    err.append(f"{up}: {e}")
                continue
            if tarea in ("(no ve)", "(denegado)"):
                continue  # pasos negativos de R-15: los valida generadores/validar/journey.py
            if tarea == INSTANCIACION:
                proceso, actor = principal, principal.get("iniciador")
                if actor is None:
                    err.append(f"{up}: el pool principal no tiene iniciador")
            else:
                try:
                    proceso, _ = nodo_de_paso(procesos, tarea, {"humana"}, "una tarea humana")
                except ValueError as e:
                    err.append(f"{up}: {e}")
                    continue
                lane = next(q_n.get("lane") for q_n in proceso.get("nodos", []) if q_n.get("id") == tarea)
                actor = next((l.get("actor") for l in proceso.get("lanes", []) if l.get("nombre") == lane), None)
            usuario = usuarios.get(paso.get("usuario"))
            if usuario is None:
                err.append(f"{up}: el usuario «{paso.get('usuario')}» no está en bdm.md › Organización")
            elif not candidato(org, proceso, None if tarea == INSTANCIACION else tarea, usuario.get("nombre")):
                propio = None if tarea == INSTANCIACION else actor_de_tarea(proceso, tarea)
                if propio is not None:
                    err.append(f"{up}: el usuario «{usuario.get('nombre')}» no es candidato del actor de tarea "
                               f"«{propio.get('nombre')}» (roles {', '.join(propio.get('roles', [])) or '—'}) que "
                               f"ejecuta «{tarea}»")
                else:
                    err.append(f"{up}: el usuario «{usuario.get('nombre')}» no tiene el rol del actor «{actor}» que "
                               f"ejecuta «{tarea}»")
            inputs = {i_.get("nombre"): i_ for i_ in proceso.get("contratos", {}).get(tarea, {}).get("inputs", [])}
            payload = paso.get("payload")
            if isinstance(payload, dict):
                for clave in payload:
                    if clave not in inputs:
                        err.append(f"{up}: el payload trae «{clave}», que no es un input del contrato de «{tarea}»")
                for nombre, i_ in inputs.items():
                    if i_.get("obligatorio") and nombre not in payload:
                        err.append(f"{up}: el payload no trae el input obligatorio «{nombre}»")
        bvs = {b.get("nombre"): b.get("objeto") for b in principal.get("business_variables", [])}
        for clave in c.get("esperado", {}):
            bv, _, atributo = clave.partition(".")
            if atributo not in atributos.get(bvs.get(bv), {}):
                err.append(f"{donde(u, clave)}: no es «<business variable>.<atributo>» de «{principal.get('nombre')}»")


def _validar_proyecto(proyecto: dict, err: list[str]) -> None:
    """Nombre y grupo del proyecto (`.trycore-bonita.json`): van a nombres de fichero y a poms."""
    for clave, patron in (("nombre", NOMBRE_PROYECTO), ("grupo", GRUPO)):
        valor = proyecto.get(clave)
        if isinstance(valor, str) and valor and not es(patron, valor):
            err.append(f".trycore-bonita.json › {clave}: «{valor}» {MENSAJE[clave]}")


def validar_spec(spec: dict) -> list[str]:
    """Comprobaciones cruzadas de una spec; lista vacía = válida."""
    err: list[str] = []
    _validar_proyecto(spec.get("proyecto") or {}, err)
    atributos = _validar_bdm(spec.get("bdm", {}), err)
    _validar_organizacion(spec.get("organizacion", {}), err)
    procesos = spec.get("procesos", [])
    nombres = [p.get("nombre") for p in procesos]
    if not procesos:
        err.append(f"{FP}: no hay ningún pool")
    for p in procesos:
        if nombres.count(p.get("nombre")) > 1:
            err.append(f"{donde(FP, 'Pool y lanes', p.get('nombre'))}: pool repetido")
        _validar_proceso(p, procesos, spec.get("organizacion", {}), atributos, err)
    _validar_caminos(spec, atributos, err)
    for modulo in _validar_extra.VALIDADORES():
        modulo.validar(spec, atributos, err)
    return list(dict.fromkeys(err))
