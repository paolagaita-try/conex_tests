"""Conectores del `.proc` (`process:Connector` en una tarea) y su mapeo definición → implementación del `.conf`.

`proceso["conectores"]` es una lista con **una entrada por invocación** (Plan 5, R-10): el mismo conector puede ir en
varias tareas y varias veces en una tarea; dentro de una tarea se escriben primero los de `entrada` y después los de
`salida`, cada grupo en su `orden`.

Dos tipos:

- `rest-get` (de `bonita-connector-rest`): ids y versiones de `versiones/<v>.json → conectores.rest.definiciones`
  (leídos del `.def`/`.impl` del jar en Task 11): la versión de la definición NO es la del jar (rest-get def 1.4.1,
  impl 1.5.1), y si no casan el proceso queda «unresolved» (D-14 del piloto). Una sola entrada, `url`; las demás
  entradas del `.def` toman su valor por defecto en la implementación (los getters de `AbstractRESTConnectorImpl`
  1.5.1 aceptan null). Cada salida `{destino, json}` es una operación `outputs` con
  `return (bodyAsObject?.a?.b as Tipo)`; `bodyAsObject` es la salida del conector con el JSON ya leído (solo si la
  respuesta es `application/json`) y se declara como `CONNECTOR_OUTPUT_TYPE`.
- `propio`: un conector del proyecto (`.def`/`.impl` escritos a mano en `bonita-project/extensions/<modulo>/`, leídos
  por `generadores.leer.extensiones`). Id y versión de la definición y de la implementación salen de
  `extensiones.definiciones[<definitionId>]`; cada entrada lleva como tipo de retorno el `type` de su `<input>` en el
  `.def`; cada salida `{destino, salida}` es una operación `outputs` con `return <salida>` (la salida, declarada
  como `CONNECTOR_OUTPUT_TYPE` con el `type` de su `<output>`).

Momento `entrada` → `ON_ENTER`, `salida` → `ON_FINISH`. Los «on enter» (con sus operaciones de salida) corren antes
que las operaciones de la tarea y los «on finish» después (doc `runtime/execution-sequence-states-and-transactions`,
que lo dice para la tarea humana; en una tarea de servicio lo midió Task 11 en el bundle 2026.2: la operación de la
tarea lee la pv que acaba de escribir el conector).

`ignorar_errores` → `ignoreErrors="true"`: si el conector falla, la tarea termina normalmente y el caso sigue
(`connectivity-overview.adoc`, «IGNORE»). Sin él, `ignoreErrors="false"`: un fallo deja la tarea en *failed*,
visible («FAIL»). Un 4xx/5xx del REST GET no es un fallo (`fail_on_http_4xx`/`5xx` por defecto false): el JSON no
llega y la salida queda null. `THROW ERROR` no se genera.

Nombre del conector en la tarea: su ID; si la tarea lo invoca más de una vez, `<ID>_<n>` (n = 1, 2… en el orden de
escritura), para que cada invocación tenga un nombre propio en el Studio y en los logs del motor.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from generadores.escribir.proc.datos import Contexto, comprobar_groovy
from generadores.escribir.proc.ids import elemento
from generadores.version import cargar_version

# Tipo de conector de la spec -> artefacto en `versiones/<v>.json → conectores`.
ARTEFACTO = {"rest-get": "rest"}
PROPIO = "propio"
TIPOS = (*ARTEFACTO, PROPIO)
MOMENTOS = {"entrada": "ON_ENTER", "salida": "ON_FINISH"}
# Salida del rest-get con el JSON de la respuesta (rest-get.def: `<output name="bodyAsObject" type="java.lang.Object"/>`).
SALIDA_JSON = ("bodyAsObject", "java.lang.Object")
# Tipo del destino (pv de la spec o atributo del BDM) -> clase Groovy del `as` de la salida.
CONVERSION = {"STRING": "String", "TEXT": "String", "CHAR": "Character", "INTEGER": "Integer", "LONG": "Long",
              "DOUBLE": "Double", "DECIMAL": "Double", "FLOAT": "Float", "BOOLEAN": "Boolean", "SHORT": "Short",
              "BYTE": "Byte"}
_RUTA_JSON = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*")
FALTA_DEFINICION = ("falta la definición `{id}` en bonita-project/extensions (escríbela antes; skill "
                    "`bonita-construir-conectores`)")


def de_la_spec(spec: dict) -> dict | None:
    """Lo que los escritores necesitan de las extensiones del proyecto: `{definiciones, filtros}` (`spec.extensiones`
    y `spec.filtros`). `None` si la spec no trae ninguna de las dos (vacaciones)."""
    definiciones = (spec.get("extensiones") or {}).get("definiciones") or {}
    filtros = spec.get("filtros") or {}
    if not definiciones and not filtros:
        return None
    return {"definiciones": definiciones, "filtros": filtros}


def definicion(tipo: str, version_bonita: str = "2026.2") -> dict:
    """{definitionId, definitionVersion, implementationId, implementationVersion} de un tipo de `versiones/`."""
    if tipo not in ARTEFACTO:
        raise NotImplementedError(f"el conector de tipo «{tipo}» todavía no se genera (solo {', '.join(TIPOS)})")
    artefacto = cargar_version(version_bonita).get("conectores", {}).get(ARTEFACTO[tipo])
    defs = artefacto.get("definiciones", {}) if isinstance(artefacto, dict) else {}
    if tipo not in defs:
        raise ValueError(f"versiones/{version_bonita}.json no tiene conectores.{ARTEFACTO[tipo]}.definiciones.{tipo}")
    return defs[tipo]


def definicion_propia(def_id: str | None, extensiones: dict | None, donde: str) -> dict:
    """La definición del proyecto `def_id` de `extensiones.definiciones` (falla si no está)."""
    d = ((extensiones or {}).get("definiciones") or {}).get(def_id)
    if d is None:
        raise ValueError(f"{donde}: {FALTA_DEFINICION.format(id=def_id)}")
    return d


def mapeo_propio(def_id: str, d: dict) -> dict:
    return {"definitionId": def_id, "definitionVersion": d["version"],
            "implementationId": d["implementacion"]["id"], "implementationVersion": d["implementacion"]["version"]}


def _ids(c: dict, version_bonita: str, extensiones: dict | None, donde: str) -> dict:
    if c.get("tipo") == PROPIO:
        return mapeo_propio(c.get("definicion"), definicion_propia(c.get("definicion"), extensiones, donde))
    return definicion(c.get("tipo"), version_bonita)


def de_la_tarea(proceso: dict, tarea: str) -> list[tuple[str, dict]]:
    """(nombre en el `.proc`, conector) de la tarea, en orden de escritura: entrada antes que salida, cada momento
    por `orden`."""
    suyos = [c for c in proceso.get("conectores", []) if c.get("tarea") == tarea]
    suyos.sort(key=lambda c: (list(MOMENTOS).index(c["momento"]) if c.get("momento") in MOMENTOS else 9,
                              c.get("orden") or 0))
    total = {c.get("id"): sum(1 for x in suyos if x.get("id") == c.get("id")) for c in suyos}
    vistos: dict[str, int] = {}
    out = []
    for c in suyos:
        vistos[c["id"]] = vistos.get(c["id"], 0) + 1
        out.append((c["id"] if total[c["id"]] == 1 else f"{c['id']}_{vistos[c['id']]}", c))
    return out


def validar(proceso: dict, extensiones: dict | None = None) -> None:
    """Cada conector va en una tarea del pool que admite conectores; un tipo que no se genera da
    `NotImplementedError` y un conector propio sin su `.def` en el proyecto, `ValueError`."""
    nombre = proceso["nombre"]
    conectores = proceso.get("conectores", [])
    if not isinstance(conectores, list):
        raise ValueError(f"proceso «{nombre}»: «conectores» debe ser una lista (una entrada por invocación)")
    por_id = {n["id"]: n for n in proceso["nodos"]}
    for c in conectores:
        donde = f"proceso «{nombre}» › {c.get('tarea')} › conector «{c.get('id')}»"
        if c.get("tipo") not in TIPOS:
            raise NotImplementedError(f"{donde}: es de tipo «{c.get('tipo')}», que todavía no se genera (solo "
                                      f"{', '.join(TIPOS)})")
        tarea = por_id.get(c.get("tarea"))
        if tarea is None or tarea.get("tipo") not in ("humana", "servicio", "script"):
            raise ValueError(f"{donde}: dice ir en «{c.get('tarea')}», que no es una tarea humana, de servicio o de "
                             "script del pool")
        if c.get("tipo") == PROPIO:
            definicion_propia(c.get("definicion"), extensiones, donde)


def _valor_json(ruta: str, d: dict, donde: str) -> str:
    if not isinstance(ruta, str) or not _RUTA_JSON.fullmatch(ruta):
        raise ValueError(f"{donde}: la ruta JSON «{ruta}» no es una lista de nombres separados por punto")
    if d["multiple"] or d["tipo"] not in CONVERSION:
        raise ValueError(f"{donde}: una salida JSON no se convierte a {d['tipo']}"
                         f"{' múltiple' if d['multiple'] else ''} (solo {', '.join(CONVERSION)})")
    acceso = "".join(f"?.{parte}" for parte in ruta.split("."))
    return f"return ({SALIDA_JSON[0]}{acceso} as {CONVERSION[d['tipo']]})"


def _parametro(conf: ET.Element, clave: str, groovy: str, tipo: str, nombre: str, ctx: Contexto,
               donde: str) -> None:
    if not groovy:
        raise ValueError(f"{donde}: falta el Groovy de la entrada «{clave}»")
    comprobar_groovy(groovy, f"{donde} › {clave}")
    p = elemento(conf, "parameters", "connectorconfiguration:ConnectorParameter", ctx.ids, {"key": clave})
    ctx.script(p, "expression", f"{clave}_{nombre}()", groovy, tipo, fijo=True)


def conector(tarea: ET.Element, nombre: str, c: dict, ctx: Contexto, donde: str,
             version_bonita: str = "2026.2", extensiones: dict | None = None) -> None:
    """`connectors` de la tarea `tarea` para una invocación `c` de la spec, con el nombre `nombre`. `ctx` es el
    contexto de la tarea (sus inputs solo si el conector corre al final)."""
    donde = f"{donde} › conector «{nombre}»"
    d = _ids(c, version_bonita, extensiones, donde)
    if c.get("momento") not in MOMENTOS:
        raise ValueError(f"{donde}: momento «{c.get('momento')}» desconocido ({', '.join(MOMENTOS)})")
    e = elemento(tarea, "connectors", "process:Connector", ctx.ids,
                 {"name": nombre, "definitionId": d["definitionId"], "definitionVersion": d["definitionVersion"],
                  "event": MOMENTOS[c["momento"]], "ignoreErrors": "true" if c.get("ignorar_errores") else "false",
                  "throwErrorEvent": "false", "namedError": ""})
    conf = elemento(e, "configuration", "connectorconfiguration:ConnectorConfiguration", ctx.ids,
                    {"definitionId": d["definitionId"], "version": d["definitionVersion"], "name": nombre})
    entradas = c.get("entradas") or {}
    if c.get("tipo") == PROPIO:
        propia = definicion_propia(c.get("definicion"), extensiones, donde)
        tipos = {i["nombre"]: i["tipo"] for i in propia["entradas"]}
        for clave, groovy in entradas.items():
            if clave not in tipos:
                raise ValueError(f"{donde}: «{clave}» no es una entrada de la definición «{c.get('definicion')}» "
                                 f"({', '.join(tipos)})")
            _parametro(conf, clave, groovy, tipos[clave], nombre, ctx, donde)
        salidas_def = {s["nombre"]: s["tipo"] for s in propia["salidas"]}
        salida = ctx.con_salidas_de_conector(salidas_def)
        for s in c.get("salidas", []):
            if s.get("salida") not in salidas_def:
                raise ValueError(f"{donde}: «{s.get('salida')}» no es una salida de la definición "
                                 f"«{c.get('definicion')}» ({', '.join(salidas_def) or 'ninguna'})")
            salida.destino(s.get("destino"), donde)
            salida.operacion(e, {"destino": s["destino"], "expresion": {"tipo": "groovy",
                                                                        "valor": f"return {s['salida']}"}},
                             donde, tag="outputs")
        return
    if set(entradas) != {"url"}:
        raise ValueError(f"{donde}: el REST GET lleva una sola entrada, `url` ({', '.join(entradas) or 'ninguna'})")
    _parametro(conf, "url", entradas["url"], "java.lang.String", nombre, ctx, donde)
    salida = ctx.con_salidas_de_conector(dict([SALIDA_JSON]))
    for s in c.get("salidas", []):
        destino = salida.destino(s.get("destino"), donde)
        valor = _valor_json(s.get("json"), destino, f"{donde} › {s.get('destino')}")
        salida.operacion(e, {"destino": s["destino"], "expresion": {"tipo": "groovy", "valor": valor}}, donde,
                         tag="outputs")


def mapeos(proceso: dict, version_bonita: str = "2026.2", extensiones: dict | None = None) -> list[dict]:
    """Un mapeo definición → implementación por definición distinta que usan los conectores del proceso, en orden."""
    out: list[dict] = []
    for c in proceso.get("conectores", []):
        d = _ids(c, version_bonita, extensiones, f"proceso «{proceso.get('nombre')}» › conector «{c.get('id')}»")
        if d not in out:
            out.append(d)
    return out
