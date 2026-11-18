"""Datos del `.proc`: tipos de dato, business y process variables, operaciones (plantilla `asignacion-directa`) y
dependencias de los scripts Groovy.

- Una operación por destino. Destino `bv.atributo`: `ASSIGNMENT` sobre la business variable entera con un script
  que asigna el atributo y devuelve la variable (patrón probado en el Plan 1 y el del piloto). Destino `pv`:
  `ASSIGNMENT` sobre la process variable con un script que devuelve el valor.
- Bonita no tiene operaciones de instanciación (ruling de Task 6): las de `operaciones["(instanciacion)"]` se
  convierten en el valor por defecto de su variable — un script que crea el objeto y le asigna cada atributo, o
  el script del valor de la process variable.
- Cada script declara como `referencedElements` todo símbolo externo que usa (business y process variables, inputs
  del contrato de SU contexto y constantes del motor): el motor solo pone en el binding lo declarado (piloto,
  `genera_proc_nivel3.py`, R-34). Comentarios y cadenas no cuentan (piloto).
- Groovy de la spec: una sentencia por línea y nunca un operador al principio de una línea (trampa D-15 del
  piloto: `return x` cierra la sentencia y la línea siguiente que empieza por `+` es código muerto silencioso).
- Plan 5, R-07: destino `bv` (sin punto, el nombre de una business variable) = operación sobre la variable entera:
  `ASSIGNMENT` con el Groovy de `expresiones.md` tal cual (devuelve el objeto, o la lista si la variable es
  múltiple), sin `set_<atributo>`. Lo que el Groovy llame de la biblioteca de helpers del proyecto (`extensions/`) es
  código del proyecto: el arnés no lo genera ni lo lee. En la instanciación, el Groovy es el valor por defecto de la
  variable, seguido de las asignaciones de sus atributos si las hay (en cualquier orden en la documentación: al
  instanciar no hay valor previo, y los destinos de input de la tabla del contrato van antes que la línea); si el
  Groovy nombra la propia variable, vale `null` (se declara delante: aún no existe).
- R-08: business variable múltiple → `multiple="true"` en su `BusinessObjectData` y en cada referencia; su valor es
  una `java.util.List` (medido en el bundle 2026.2-u0: D-60). Sin operación de instanciación no tiene valor por
  defecto; varias en la instanciación se evalúan en el orden de los `data` del pool (D-61).
- DAO de los objetos con business variable en el pool: `<objeto>DAO` (p. ej. `eventoDAO`) se declara, si el script
  lo usa, como `TYPE_BUSINESS_OBJECT_DAO` con `returnType` la interfaz `<paquete>.<Objeto>DAO` (la que lee
  `BusinessObjectDAOExpressionStrategy` del motor 11.1.0 para instanciar `<Objeto>DAOImpl`; D-62). Así un script
  puede pasar el DAO a un helper de la biblioteca, que no nombra clases del BDM (D-63).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from generadores.escribir.bom import CLASE_JAVA
from generadores.escribir.proc.ids import XMI_ID, elemento
from generadores.xmlutil import Ids

INSTANCIACION = "(instanciacion)"
DATATYPES = [("BooleanType", "Boolean"), ("DateType", "Date"), ("IntegerType", "Integer"),
             ("LongType", "Long"), ("DoubleType", "Double"), ("StringType", "Text"),
             ("JavaType", "Java_object"), ("XMLType", "XML"), ("BusinessObjectType", "Business_Object")]
# Tipo de process variable de la spec -> (datatype del pool, clase Java, ¿JavaObjectData?)
TIPOS_PV = {
    "TEXT": ("Text", "java.lang.String", False), "BOOLEAN": ("Boolean", "java.lang.Boolean", False),
    "INTEGER": ("Integer", "java.lang.Integer", False), "LONG": ("Long", "java.lang.Long", False),
    "DOUBLE": ("Double", "java.lang.Double", False), "DECIMAL": ("Double", "java.lang.Double", False),
    "DATE": ("Date", "java.util.Date", False),
    "LOCALDATE": ("Java_object", "java.time.LocalDate", True),
    "LOCALDATETIME": ("Java_object", "java.time.LocalDateTime", True),
    "OFFSETDATETIME": ("Java_object", "java.time.OffsetDateTime", True),
}
# Tipo de parámetro de la spec -> clase Java (doc 2026.2: text, Boolean, integer y double; bonita2bar 9.0.10,
# ParameterArtifactProvider.toSimpleTypeName acepta exactamente estas cuatro clases).
CLASE_PARAMETRO = {"String": "java.lang.String", "Integer": "java.lang.Integer", "Boolean": "java.lang.Boolean",
                   "Double": "java.lang.Double"}
# Tipo de input de contrato -> clase Java del valor (para comparar con el origen de un mapeo de call activity).
CLASE_INPUT = {"TEXT": "java.lang.String", "INTEGER": "java.lang.Integer", "DECIMAL": "java.lang.Double",
               "BOOLEAN": "java.lang.Boolean", "DATE": "java.util.Date", "LONG": "java.lang.Long",
               "LOCALDATE": "java.time.LocalDate", "LOCALDATETIME": "java.time.LocalDateTime",
               "OFFSETDATETIME": "java.time.OffsetDateTime", "COMPLEX": "java.util.Map", "FILE": None}
TIPOS_INPUT = ["TEXT", "INTEGER", "DECIMAL", "BOOLEAN", "DATE", "COMPLEX", "FILE", "LONG", "LOCALDATE",
               "LOCALDATETIME", "OFFSETDATETIME"]
# Constantes del motor (`org.bonitasoft.engine.expression.ExpressionConstants`) -> returnType; mismas que el piloto.
CONSTANTES_MOTOR = {
    "apiAccessor": "org.bonitasoft.engine.api.APIAccessor",
    "processInstanceId": "java.lang.Long",
    "rootProcessInstanceId": "java.lang.Long",
    "activityInstanceId": "java.lang.Long",
    "processDefinitionId": "java.lang.Long",
    "loggedUserId": "java.lang.Long",
    "taskAssigneeId": "java.lang.Long",
}
_CADENAS = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
_COMENTARIOS = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
# Operador binario o de continuación al principio de una línea (D-15). `++x`, `--x` y `?.` no cuentan.
_OPERADOR_AL_INICIO = re.compile(r"^(\+(?!\+)|-(?!-)|\*|/|%|&&|\|\||\?(?!\.)|:|==|!=|<|>|=|\band\b|\bor\b)")


def _limpio(texto: str) -> str:
    """El Groovy sin cadenas ni comentarios (lo que puede nombrar un símbolo)."""
    return _COMENTARIOS.sub(" ", _CADENAS.sub('""', texto))


def simbolos_usados(texto: str, nombres) -> list[str]:
    """Los `nombres` que el script usa como identificador (no tras un punto, no dentro de cadenas ni comentarios),
    en el orden de `nombres`."""
    limpio = _limpio(texto)
    return [n for n in nombres if re.search(rf"(?<![\w.$]){re.escape(n)}(?![\w$])", limpio)]


def comprobar_groovy(texto: str, donde: str) -> None:
    for i, linea in enumerate(_limpio(texto).split("\n"), 1):
        if _OPERADOR_AL_INICIO.match(linea.strip()):
            raise ValueError(f"{donde}: la línea {i} del Groovy empieza por un operador ({linea.strip()[:30]!r}); "
                             "déjalo al final de la línea anterior (trampa D-15: la línea sería código muerto)")


def _cadena(valor: str) -> str:
    """Literal Groovy entre comillas simples (String de Java, sin interpolación de `$`)."""
    escapado = valor.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    return f"'{escapado}'"


def literal(valor: str, tipo: str) -> str:
    """Valor literal de la documentación como expresión Groovy del tipo de su destino (atributo BDM o pv)."""
    v = str(valor)
    try:
        if tipo in ("STRING", "TEXT", "CHAR"):
            return _cadena(v)
        if tipo in ("INTEGER", "SHORT", "BYTE"):
            n = str(int(v))
            return n if tipo == "INTEGER" else f"({n} as {'Short' if tipo == 'SHORT' else 'Byte'})"
        if tipo == "LONG":
            return f"{int(v)}L"
        if tipo in ("DOUBLE", "DECIMAL", "FLOAT"):
            float(v)
            return f"{v}{'f' if tipo == 'FLOAT' else 'd'}"
        if tipo == "BOOLEAN":
            if v not in ("true", "false"):
                raise ValueError(v)
            return v
        if tipo == "LOCALDATE":
            return f"java.time.LocalDate.parse({_cadena(v)})"
        if tipo == "LOCALDATETIME":
            return f"java.time.LocalDateTime.parse({_cadena(v)})"
        if tipo == "OFFSETDATETIME":
            return f"java.time.OffsetDateTime.parse({_cadena(v)})"
        if tipo == "DATE":
            return (f"java.util.Date.from(java.time.LocalDate.parse({_cadena(v)})"
                    ".atStartOfDay(java.time.ZoneId.systemDefault()).toInstant())")
    except ValueError:
        raise ValueError(f"el literal «{v}» no es un valor de tipo {tipo}") from None
    raise ValueError(f"no hay literales de tipo {tipo}")


class Contexto:
    """Lo que un script puede nombrar en un punto del proceso: business y process variables y parámetros del pool,
    inputs del contrato de ese punto (los de la tarea humana o los de instanciación; ninguno en tareas automáticas),
    las constantes del motor y, en las operaciones de salida de un conector, sus salidas (`salidas`: nombre ->
    clase Java, declaradas como `CONNECTOR_OUTPUT_TYPE`)."""

    def __init__(self, ids: Ids, tipos: dict[str, str], bvs: dict[str, dict], pvs: dict[str, dict],
                 entradas: dict[str, dict] | None = None, params: dict[str, dict] | None = None,
                 salidas: dict[str, str] | None = None):
        self.ids, self.tipos, self.bvs, self.pvs = ids, tipos, bvs, pvs
        self.entradas = entradas or {}
        self.params = params or {}
        self.salidas = salidas or {}

    def con_entradas(self, entradas: list[dict]) -> "Contexto":
        return Contexto(self.ids, self.tipos, self.bvs, self.pvs, {i["nombre"]: i for i in entradas}, self.params)

    def con_salidas_de_conector(self, salidas: dict[str, str]) -> "Contexto":
        """El mismo contexto (entradas incluidas) más las salidas de un conector, para sus operaciones `outputs`."""
        return Contexto(self.ids, self.tipos, self.bvs, self.pvs, self.entradas, self.params, salidas)

    # --------------------------------------------------------------------------------------------- referencias
    def ref_bv(self, padre: ET.Element, nombre: str) -> None:
        # Orden de features de `Data` (process.ecore 9.0.10): name, multiple, dataType; después className.
        elemento(padre, "referencedElements", "process:BusinessObjectData", self.ids,
                 {"name": nombre, "multiple": "true" if self.bvs[nombre].get("multiple") else None,
                  "dataType": self.tipos["Business_Object"], "className": self.bvs[nombre]["clase"]})

    def daos(self) -> dict[str, str]:
        """`<objeto>DAO` -> interfaz DAO, de los objetos que tienen business variable en el pool (R-07)."""
        out = {}
        for info in self.bvs.values():
            paquete, _, simple = info["clase"].rpartition(".")
            out.setdefault(f"{simple[:1].lower()}{simple[1:]}DAO", f"{info['clase']}DAO")
        return out

    def ref_pv(self, padre: ET.Element, nombre: str) -> None:
        dt, clase, java = TIPOS_PV[self.pvs[nombre]["tipo"]]
        elemento(padre, "referencedElements", "process:JavaObjectData" if java else "process:Data", self.ids,
                 {"name": nombre, "dataType": self.tipos[dt], "className": clase if java else None})

    def ref_input(self, padre: ET.Element, nombre: str) -> None:
        i = self.entradas[nombre]
        elemento(padre, "referencedElements", "process:ContractInput", self.ids,
                 {"name": nombre, "type": i["tipo"], "multiple": "true" if i.get("multiple") else None})

    def ref_param(self, padre: ET.Element, nombre: str) -> None:
        elemento(padre, "referencedElements", "parameter:Parameter", self.ids,
                 {"name": nombre, "typeClassname": CLASE_PARAMETRO[self.params[nombre]["tipo"]]})

    def referencias(self, expr: ET.Element, texto: str, excluir: tuple[str, ...] = ()) -> None:
        """Declara en `expr` cada símbolo que usa `texto`. Si un input del contrato y una process variable se
        llaman igual, gana el input (es el dato del paso). `excluir` (la variable que el script inicializa) no quita
        los inputs: `numero` ← input `numero` necesita la referencia al input (si no, el motor falla al instanciar:
        «depends on numero is neither defined in the script nor in dependencies»)."""
        for n in simbolos_usados(texto, [b for b in self.bvs if b not in excluir]):
            self.ref_bv(expr, n)
        daos = self.daos()
        for n in simbolos_usados(texto, [d for d in daos if d not in self.bvs and d not in self.pvs]):
            elemento(expr, "referencedElements", "expression:Expression", self.ids,
                     {"name": n, "content": n, "type": "TYPE_BUSINESS_OBJECT_DAO", "returnType": daos[n]})
        for n in simbolos_usados(texto, [p for p in self.pvs if p not in excluir and p not in self.entradas]):
            self.ref_pv(expr, n)
        for n in simbolos_usados(texto, list(self.entradas)):
            self.ref_input(expr, n)
        for n in simbolos_usados(texto, [p for p in self.params if p not in excluir]):
            self.ref_param(expr, n)
        for n in simbolos_usados(texto, CONSTANTES_MOTOR):
            elemento(expr, "referencedElements", "expression:Expression", self.ids,
                     {"name": n, "content": n, "type": "TYPE_ENGINE_CONSTANT", "returnType": CONSTANTES_MOTOR[n]})
        # Salida de conector: así la resuelve el motor dentro del script de salida (piloto, xml_output_var).
        for n in simbolos_usados(texto, [s for s in self.salidas if s not in excluir]):
            elemento(expr, "referencedElements", "expression:Expression", self.ids,
                     {"name": n, "content": n, "type": "CONNECTOR_OUTPUT_TYPE", "returnType": self.salidas[n]})

    def script(self, padre: ET.Element, tag: str, nombre: str, contenido: str, tipo_retorno: str,
               fijo: bool = False, excluir: tuple[str, ...] = ()) -> ET.Element:
        e = elemento(padre, tag, "expression:Expression", self.ids,
                     {"name": nombre, "content": contenido, "interpreter": "GROOVY", "type": "TYPE_READ_ONLY_SCRIPT",
                      "returnType": tipo_retorno, "returnTypeFixed": "true" if fijo else None})
        self.referencias(e, contenido, excluir)
        return e

    # ----------------------------------------------------------------------------------------------- destinos
    def destino(self, ref: str, donde: str) -> dict:
        """`bv.atributo`, `pv` o `bv` (la variable entera) -> {clase: bv|pv|entera, nombre, atributo, tipo, multiple,
        java}."""
        if "." in ref:
            bv, atributo = ref.split(".", 1)
            info = self.bvs.get(bv)
            a = (info or {}).get("atributos", {}).get(atributo)
            if a is None:
                raise ValueError(f"{donde}: el destino «{ref}» no es un atributo de una business variable del pool")
            return {"clase": "bv", "nombre": bv, "atributo": atributo, "tipo": a["tipo"],
                    "multiple": bool(a.get("multiple"))}
        if ref not in self.pvs and ref in self.bvs:
            info = self.bvs[ref]
            return {"clase": "entera", "nombre": ref, "tipo": None, "multiple": bool(info.get("multiple")),
                    "java": "java.util.List" if info.get("multiple") else info["clase"]}
        if ref not in self.pvs:
            raise ValueError(f"{donde}: el destino «{ref}» no es una process variable, ni «bv.atributo», ni una "
                             "business variable del pool")
        return {"clase": "pv", "nombre": ref, "tipo": self.pvs[ref]["tipo"], "multiple": False,
                "java": TIPOS_PV[self.pvs[ref]["tipo"]][1]}

    def clase_java(self, ref: str, donde: str) -> str:
        """Clase Java del valor de `bv.atributo` o `pv` (un atributo múltiple es una lista)."""
        d = self.destino(ref, donde)
        if d["clase"] in ("pv", "entera"):
            return d["java"]
        return "java.util.List" if d["multiple"] else CLASE_JAVA[d["tipo"]]

    def _valor_input(self, ruta: str, donde: str) -> str:
        raiz, _, hijo = ruta.partition(".")
        entrada = self.entradas.get(raiz)
        if entrada is None or (hijo and hijo not in {h["nombre"] for h in entrada.get("hijos", [])}):
            raise ValueError(f"{donde}: el input «{ruta}» no está en el contrato de este paso "
                             f"({', '.join(self.entradas) or 'sin contrato'})")
        return ruta

    def asignacion(self, objetivo: str, expresion: dict, d: dict, donde: str) -> list[str]:
        """Líneas Groovy que asignan la expresión de la spec a `objetivo` (p. ej. `solicitud.estado`)."""
        tipo, valor = expresion.get("tipo"), expresion.get("valor")
        if tipo == "input":
            return [f"{objetivo} = {self._valor_input(valor, donde)}"]
        if tipo == "literal":
            if d["multiple"]:
                raise ValueError(f"{donde}: no hay literales para un atributo múltiple ({objetivo})")
            return [f"{objetivo} = {literal(valor, d['tipo'])}"]
        if tipo == "groovy":
            comprobar_groovy(valor, donde)
            return [f"{objetivo} = {{", *valor.split("\n"), "}.call()"]
        raise ValueError(f"{donde}: expresión de tipo «{tipo}» desconocido (input, literal o groovy)")

    def valor(self, expresion: dict, d: dict, donde: str) -> str:
        """Script que devuelve el valor de la expresión (para una process variable)."""
        tipo, valor = expresion.get("tipo"), expresion.get("valor")
        if tipo == "groovy":
            comprobar_groovy(valor, donde)
            return valor
        if tipo == "input":
            return f"return {self._valor_input(valor, donde)}"
        if tipo == "literal":
            return f"return {literal(valor, d['tipo'])}"
        raise ValueError(f"{donde}: expresión de tipo «{tipo}» desconocido (input, literal o groovy)")

    # ------------------------------------------------------------------------------------------- operaciones
    def operacion(self, padre: ET.Element, op: dict, donde: str, tag: str = "operations") -> None:
        """Operación `op` de la spec como hijo `tag` de `padre` (`operations` de una tarea u `outputs` de un
        conector)."""
        d = self.destino(op["destino"], donde)
        donde = f"{donde} › {op['destino']}"
        o = elemento(padre, tag, "expression:Operation", self.ids)
        if d["clase"] == "entera":
            bv = d["nombre"]
            if (op["expresion"] or {}).get("tipo") != "groovy":
                raise ValueError(f"{donde}: la business variable entera solo admite un script")
            comprobar_groovy(op["expresion"]["valor"], donde)
            izq = elemento(o, "leftOperand", "expression:Expression", self.ids,
                           {"name": bv, "content": bv, "type": "TYPE_VARIABLE", "returnType": d["java"]})
            self.ref_bv(izq, bv)
            self.script(o, "rightOperand", f"asignar_{bv}()", op["expresion"]["valor"], d["java"])
        elif d["clase"] == "bv":
            bv, clase = d["nombre"], self.bvs[d["nombre"]]["clase"]
            izq = elemento(o, "leftOperand", "expression:Expression", self.ids,
                           {"name": bv, "content": bv, "type": "TYPE_VARIABLE", "returnType": clase})
            self.ref_bv(izq, bv)
            lineas = self.asignacion(f"{bv}.{d['atributo']}", op["expresion"], d, donde) + [f"return {bv}"]
            self.script(o, "rightOperand", f"set_{d['atributo']}()", "\n".join(lineas), clase)
        else:
            pv = d["nombre"]
            izq = elemento(o, "leftOperand", "expression:Expression", self.ids,
                           {"name": pv, "content": pv, "type": "TYPE_VARIABLE", "returnType": d["java"]})
            self.ref_pv(izq, pv)
            self.script(o, "rightOperand", f"set_{pv}()", self.valor(op["expresion"], d, donde), d["java"])
        elemento(o, "operator", "expression:Operator", self.ids, {"type": "ASSIGNMENT"})


def tipos_de_dato(main: ET.Element, ids: Ids) -> dict[str, str]:
    """Los `datatypes` del MainProcess (como los escribe el Studio) -> nombre: xmi:id."""
    return {nombre: elemento(main, "datatypes", f"process:{clase}", ids, {"name": nombre}).get(XMI_ID)
            for clase, nombre in DATATYPES}


def business_variables(proceso: dict, bdm: dict) -> dict[str, dict]:
    """bv -> {clase: nombre calificado, atributos: {nombre: atributo del BDM}}."""
    paquete = bdm.get("paquete", "")
    objetos = {o["nombre"]: o for o in bdm.get("objetos", [])}
    out = {}
    for b in proceso.get("business_variables", []):
        objeto = b["objeto"]
        simple = objeto.rsplit(".", 1)[-1] if objeto.startswith(f"{paquete}.") else objeto
        if simple not in objetos:
            raise ValueError(f"proceso «{proceso['nombre']}»: la business variable «{b['nombre']}» es de «{objeto}», "
                             f"que no está en el BDM ({', '.join(objetos) or 'vacío'})")
        out[b["nombre"]] = {"clase": f"{paquete}.{simple}",
                            "atributos": {a["nombre"]: a for a in objetos[simple]["atributos"]},
                            "multiple": bool(b.get("multiple"))}
    return out


def parametros(proceso: dict) -> dict[str, dict]:
    """Parámetros del pool (nombre -> parámetro de la spec). Su valor es del entorno: va en el `.conf`."""
    out = {}
    for p in proceso.get("parametros", []):
        if p.get("tipo") not in CLASE_PARAMETRO:
            raise ValueError(f"proceso «{proceso['nombre']}» › parámetro «{p.get('nombre')}»: tipo «{p.get('tipo')}» "
                             f"no soportado ({', '.join(CLASE_PARAMETRO)})")
        out[p["nombre"]] = p
    return out


def parametros_del_pool(pool: ET.Element, ctx: Contexto) -> None:
    """`parameters` del pool (`parameter.ecore`): nombre y clase, sin valor."""
    for nombre, p in ctx.params.items():
        elemento(pool, "parameters", "parameter:Parameter", ctx.ids,
                 {"name": nombre, "typeClassname": CLASE_PARAMETRO[p["tipo"]]})


def variables_de_proceso(proceso: dict) -> dict[str, dict]:
    out = {}
    for v in proceso.get("variables", []):
        donde = f"proceso «{proceso['nombre']}» › variable «{v['nombre']}»"
        if v.get("tipo") not in TIPOS_PV:
            raise ValueError(f"{donde}: tipo «{v.get('tipo')}» desconocido ({', '.join(TIPOS_PV)})")
        if v.get("transitoria"):
            raise ValueError(f"{donde}: una variable del pool no puede ser transitoria (doc data/"
                             "specify-data-in-a-process-definition: solo las de tarea pueden serlo)")
        out[v["nombre"]] = v
    return out


def datos_del_pool(pool: ET.Element, proceso: dict, ctx: Contexto) -> None:
    """Process variables y business variables del pool, con su valor por defecto (de `defecto` o de las
    operaciones de instanciación)."""
    nombre = proceso["nombre"]
    inst = proceso.get("operaciones", {}).get(INSTANCIACION, [])
    donde = f"proceso «{nombre}» › {INSTANCIACION}"
    por_variable: dict[str, list[dict]] = {}
    for op in inst:
        d = ctx.destino(op["destino"], donde)
        por_variable.setdefault(d["nombre"], []).append(op)

    for pv, v in ctx.pvs.items():
        dt, clase, java = TIPOS_PV[v["tipo"]]
        e = elemento(pool, "data", "process:JavaObjectData" if java else "process:Data", ctx.ids,
                     {"name": pv, "dataType": ctx.tipos[dt], "className": clase if java else None})
        ops = por_variable.get(pv, [])
        if ops and v.get("defecto") is not None:
            raise ValueError(f"{donde}: «{pv}» tiene valor por defecto y operación de instanciación; deja una")
        d = ctx.destino(pv, donde)
        if ops:
            contenido = ctx.valor(ops[0]["expresion"], d, f"{donde} › {pv}")
        elif v.get("defecto") is not None:
            contenido = f"return {literal(v['defecto'], v['tipo'])}"
        else:
            elemento(e, "defaultValue", "expression:Expression", ctx.ids, {"name": "", "content": "", "returnType": ""})
            continue
        ctx.script(e, "defaultValue", f"init_{pv}()", contenido, clase, fijo=True, excluir=(pv,))

    for bv, info in ctx.bvs.items():
        multiple = bool(info.get("multiple"))
        e = elemento(pool, "data", "process:BusinessObjectData", ctx.ids,
                     {"name": bv, "multiple": "true" if multiple else None, "dataType": ctx.tipos["Business_Object"],
                      "className": info["clase"]})
        ops = por_variable.get(bv, [])
        if not ops:
            continue  # sin valor por defecto (R-08): la carga una operación posterior
        entera = [op for op in ops if "." not in op["destino"]]
        atributos = [op for op in ops if "." in op["destino"]]
        u = f"{donde} › bv {bv}"
        if len(entera) > 1:
            raise ValueError(f"{u}: una sola operación entera por variable")
        if multiple and atributos:
            raise ValueError(f"{u}: una business variable múltiple solo admite la operación entera")
        retorno = "java.util.List" if multiple else info["clase"]
        if entera:
            groovy = entera[0]["expresion"]["valor"]
            comprobar_groovy(groovy, u)
            propia = bool(simbolos_usados(groovy, [bv]))  # su propio valor inicial: aún no existe, vale null
            if not atributos:
                contenido = f"def {bv} = null\n{groovy}" if propia else groovy
                ctx.script(e, "defaultValue", f"init_{bv}()", contenido, retorno, fijo=True, excluir=(bv,))
                continue
            cabeza = [f"def {bv} = null", f"{bv} = {{"] if propia else [f"def {bv} = {{"]
            lineas = [*cabeza, *groovy.split("\n"), "}.call()"]
        else:
            lineas = [f"def {bv} = new {info['clase']}()"]
        for op in atributos:
            d = ctx.destino(op["destino"], donde)
            lineas += ctx.asignacion(f"{bv}.{d['atributo']}", op["expresion"], d, f"{donde} › {op['destino']}")
        lineas.append(f"return {bv}")
        ctx.script(e, "defaultValue", f"init_{bv}()", "\n".join(lineas), retorno, fijo=True, excluir=(bv,))
