"""`generar` en modo «proyecto existente» (spec 6.6 a 6.8.2): lo nuevo y la cirugía confirmada, todo o nada.

Exige un handoff en modo existente que corresponda al mapa actual y una confirmación vigente de una persona
(`cambios-confirmados.md`). Escribe los procesos nuevos de `docs/07-bonita/bpmn.md` como un proyecto nuevo, pero sin
tocar el BDM, la organización, los perfiles ni ningún fichero de la línea base, y aplica la cirugía confirmada sobre
lo existente (BDM, organización y cada pool, en su misma versión o en una superior). La cirugía parte siempre de la
copia de la línea base, no del fichero de trabajo: repetir `generar` deja los mismos bytes. Todo se calcula en memoria
y se valida antes de escribir; si algo falla, no se escribe ni se borra nada.

Con la fase cerrada (sin `cambios.md` ni `cambios-confirmados.md`, p. ej. tras `cerrar`) no hay cirugía que confirmar:
solo se escriben los procesos nuevos, sin exigir el handoff sobre el mapa actual ni la confirmación (spec 6.8.1)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from generadores.escribir import Plan, aplicar_plan, planear_proyecto
from generadores.escribir.frontend import MANIFIESTO
from generadores.existente.cirugia.bom import cirugia_bom
from generadores.existente.cirugia.organizacion import cirugia_organizacion
from generadores.existente.cirugia.proc import cirugia_proc
from generadores.existente.cirugia.version import copiar_conf, nombre_fichero, nueva_version
from generadores.existente.clasificar import HUECOS
from generadores.existente.confirmar import CAMBIOS, CONFIRMADOS, caducada, leer_confirmados
from generadores.existente.leer_xml import leer_existente
from generadores.existente.linea_base import BONITA, COPIA, leer_linea_base, modo_existente, original
from generadores.existente.mapa import DIRECTORIO
from generadores.leer.handoff import MODO_EXISTENTE, leer_handoff
from generadores.md import leer_markdown
from generadores.spec import construir_spec

HANDOFF = Path("docs/07-bonita/handoff.md")
FLOW_STATE = Path("docs/.flow-state.json")
BPMN = Path("docs/07-bonita/bpmn.md")
SPEC = Path("build/spec.json")
SEMILLA = "existente"  # de los xmi:id nuevos; con el pool (y la versión) da ids deterministas
CLASES_BDM = ("objeto", "atributo")
CLASES_ORG = ("grupo", "rol", "usuario", "membresia")
CLASES_PROC = ("nodo", "contrato")
EXTENSION_CONSULTAS = Path(BONITA) / "extensions" / "consultas-api-extension"
_FRONTMATTER = re.compile(r"\A(?:<!--.*?-->\n)?---\n(.*?)\n---\n", re.S)
_HUELLA = re.compile(r"^huella: (\S+)$", re.M)


def huella_del_mapa(proyecto: Path) -> str | None:
    """La `huella:` del frontmatter de los ficheros del mapa (`docs/07-bonita/existente/`), o None si falta el mapa,
    algún fichero no la tiene o no coinciden entre sí."""
    huellas = set()
    for f in sorted((Path(proyecto) / DIRECTORIO).glob("*.md")):
        frontmatter = _FRONTMATTER.match(f.read_text(encoding="utf-8"))
        m = _HUELLA.search(frontmatter.group(1)) if frontmatter else None
        huellas.add(m.group(1) if m else None)
    return huellas.pop() if len(huellas) == 1 else None


def _handoff(proyecto: Path) -> list[str]:
    """Motivos por los que el handoff no permite generar en modo existente (`[]` si lo permite)."""
    if not (proyecto / HANDOFF).is_file():
        return [f"falta {HANDOFF.as_posix()}"]
    if not (proyecto / FLOW_STATE).is_file():
        return [f"falta {FLOW_STATE.as_posix()}"]
    try:
        flow_state = json.loads((proyecto / FLOW_STATE).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{FLOW_STATE.as_posix()}: JSON mal formado ({e})"]
    if not isinstance(flow_state, dict):
        return [f"{FLOW_STATE.as_posix()}: debe ser un objeto JSON"]
    datos, errores = leer_handoff(leer_markdown((proyecto / HANDOFF).read_text(encoding="utf-8")), flow_state)
    if datos.get("modo") != MODO_EXISTENTE:
        return [f"{HANDOFF.as_posix()}: no está en modo existente (falta `modo: {MODO_EXISTENTE}` en su frontmatter)"]
    motivos = list(errores)
    actual = huella_del_mapa(proyecto)
    if actual is None:
        motivos.append(f"el mapa de {DIRECTORIO.as_posix()}/ falta o sus ficheros no tienen la misma huella; "
                       "regenéralo con «mapa»")
    elif datos["mapa_huella"] != actual:
        motivos.append(f"{HANDOFF.as_posix()}: mapa_huella «{datos['mapa_huella'] or '—'}» no es la del mapa actual "
                       f"({actual}); la documentación se hizo sobre otro mapa")
    return motivos


def _exigencias(proyecto: Path) -> list[str]:
    """Todo lo que impide generar en modo existente, o `[]`."""
    if not modo_existente(proyecto):
        return [f"{proyecto} no está en modo existente; adóptalo antes con «adoptar»"]
    if leer_linea_base(proyecto) is None:
        return ["falta la línea base (.trycore-bonita-linea-base.json); adopta el proyecto"]
    motivos = _handoff(proyecto)
    vencida = caducada(proyecto)
    if vencida:
        motivos.append(f"no hay una confirmación vigente ({CONFIRMADOS.as_posix()}); una persona ejecuta "
                       "`tools/arnes.sh cambios confirmar` en su propia terminal:")
        motivos += [f"  {m}" for m in vencida]
        return motivos
    for c in leer_confirmados(proyecto)["cambios"]:
        if c.get("confirmado") is not True:
            motivos.append(f"{c['ubic']}: el cambio no está confirmado")
        elif c["discrepancia"] or not c["soportado"]:
            motivo = c["discrepancia"] or f"no soportado: {c.get('motivo') or '—'}"
            motivos.append(f"{c['ubic']}: confirmado pero {motivo}")
    return motivos


def modulos_que_faltan(spec: dict, proyecto: Path) -> list[str]:
    """Los módulos de la plantilla que la spec de lo nuevo necesita y el proyecto no tiene (spec 6.8.2)."""
    proyecto = Path(proyecto)
    formularios = spec.get("formularios") or {}
    faltan = []
    # Solo los formularios Svelte (y las páginas propias) los genera el arnés en el frontend; «No form» y «External URL»
    # usan lo que el proyecto ya tiene.
    svelte = any(f.get("mapping") == "Svelte" for f in formularios.get("formularios", []))
    if (svelte or formularios.get("paginas")) and not (proyecto / MANIFIESTO).is_file():
        faltan.append(f"el frontend de la plantilla (`{MANIFIESTO.as_posix()}`) para los formularios Svelte generados")
    if spec.get("parametros_negocio") and not any((proyecto / BONITA / "extensions").glob("parametros-*")):
        faltan.append(f"el módulo de parámetros (`{BONITA}/extensions/parametros-*`) para los parámetros de negocio")
    lecturas = any(c.get("lee") for f in formularios.get("formularios", []) for c in f.get("campos", []))
    if (lecturas or formularios.get("paginas")) and not (proyecto / EXTENSION_CONSULTAS).is_dir():
        faltan.append(f"la extensión de consultas (`{EXTENSION_CONSULTAS.as_posix()}`) para las lecturas del caso")
    return faltan


def _organizacion_de_lo_nuevo(spec: dict, proyecto: Path) -> None:
    """`ValueError` si los actores de los procesos nuevos no se pueden mapear a la organización existente: sin
    organización documentada, o con un grupo o rol que ni existe en la copia de la línea base ni lo agrega `cambios.md`
    (confirmado)."""
    org = spec.get("organizacion")
    if not org:
        raise ValueError("los procesos nuevos no traen organización: documenta en bdm.md los actores de los procesos "
                         "nuevos y su grupo/rol de la organización existente")
    existente = leer_existente(proyecto / COPIA)["organizacion"]
    grupos = {g.strip("/") for g in existente["grupos"]}
    roles = set(existente["roles"])
    for c in (leer_confirmados(proyecto) or {"cambios": []})["cambios"]:
        if c["clase"] == "grupo":
            grupos.add(c["datos"]["ruta"].strip("/"))
        elif c["clase"] == "rol":
            roles.add(c["datos"]["rol"])
    faltan = []
    for actor, datos in sorted((org.get("actores") or {}).items()):
        if datos["grupo"].strip("/") not in grupos:
            faltan.append(f"el actor «{actor}» usa el grupo «{datos['grupo']}»")
        faltan += [f"el actor «{actor}» usa el rol «{r}»" for r in datos.get("roles") or [datos["rol"]]
                   if r not in roles]
    if faltan:
        raise ValueError("los actores de los procesos nuevos usan grupos o roles que no están en la organización "
                         "existente ni los agrega cambios.md: " + "; ".join(faltan))


def _procesos_nuevos(proyecto: Path) -> Plan:
    """El plan de escritura de los procesos nuevos de `bpmn.md` (vacío sin `bpmn.md`), con `build/spec.json`."""
    if not (proyecto / BPMN).is_file():
        return Plan([], [], [])
    spec, errores = construir_spec(proyecto)
    if errores:
        raise ValueError(f"la documentación de lo nuevo tiene {len(errores)} error(es):\n"
                         + "\n".join(f"  {e}" for e in errores))
    faltan = modulos_que_faltan(spec, proyecto)
    if faltan:
        raise ValueError("lo nuevo pide módulos de la plantilla que el proyecto no tiene: " + "; ".join(faltan)
                         + f". Agregar un módulo no está soportado en esta entrega; va a {HUECOS}")
    if "procesos" in spec:
        _organizacion_de_lo_nuevo(spec, proyecto)
    plan = planear_proyecto(spec, proyecto, existente=True)
    spec_json = (json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return Plan(plan.escrituras + [(proyecto / SPEC, spec_json)], plan.internas, plan.borrar)


def _texto(proyecto: Path, rel: str) -> str:
    return original(proyecto, rel).decode("utf-8")


def _libre(proyecto: Path, rel: str, contenido: bytes, que: str) -> None:
    """ValueError si `rel` ya existe con otro contenido (no es lo que esta misma generación escribió antes)."""
    ruta = proyecto / rel
    if ruta.exists() and (not ruta.is_file() or ruta.read_bytes() != contenido):
        raise ValueError(f"{que} ya existe ({rel}) y no es la que genera esta confirmación; no se pisa")


def _sin_ediciones(proyecto: Path, linea_base: dict, cirugia: dict[str, bytes]) -> None:
    """`ValueError` si un fichero de la línea base que la cirugía reescribe fue editado a mano después de la línea
    base: en disco debe estar el original (aún sin generar) o exactamente lo que esta generación calcula."""
    for rel, contenido in sorted(cirugia.items()):
        if rel not in linea_base["ficheros"]:
            continue
        actual = (proyecto / rel).read_bytes() if (proyecto / rel).is_file() else None
        if actual is not None and actual != contenido and actual != original(proyecto, rel):
            raise ValueError(f"{rel}: editado a mano después de la línea base; restaura con git o vuelve a confirmar")


def _nombre_seguro(nombre: str) -> str:
    """`nombre` (de un pool) apto para nombre de fichero: lo que no es letra, dígito, espacio, «.», «_» o «-» pasa a
    «_»."""
    return re.sub(r"[^\w .-]", "_", nombre).strip(" .") or "_"


def _cirugia_pools(proyecto: Path, linea_base: dict, datos: dict, cambios: list[dict]) -> dict[str, bytes]:
    """Ruta relativa -> contenido de cada `.proc` (y `.conf` de versión superior) que cambia la cirugía.

    La copia de versión superior se llama `<MainProcess>-<versión>.proc`; si más de un pool del mismo fichero sube de
    versión en esta generación, cada copia se llama `<Pool>-<versión>.proc` (el `MainProcess` es el mismo para todos).
    Dos destinos iguales son `ValueError`."""
    salida: dict[str, bytes] = {}
    origen: dict[str, str] = {}  # destino -> pool que lo escribe
    misma: dict[str, str] = {}  # fichero -> texto: varios pools de un fichero en su versión se acumulan
    suben: dict[str, int] = {}  # fichero -> cuántos de sus pools suben de versión
    for clave, p in datos["procesos"].items():
        if clave in linea_base["pools"] and p["version_resultante"] != clave.rpartition("@")[2]:
            fichero = linea_base["pools"][clave]["fichero"]
            suben[fichero] = suben.get(fichero, 0) + 1

    def escribir(rel: str, contenido: str, clave: str) -> None:
        if rel in salida:
            raise ValueError(f"las versiones superiores de {origen[rel]} y {clave} se llamarían igual ({rel}); "
                             "elige versiones distintas al confirmar")
        salida[rel], origen[rel] = contenido.encode("utf-8"), clave

    for clave in sorted(datos["procesos"]):
        pool = linea_base["pools"].get(clave)
        if pool is None:
            raise ValueError(f"el proceso {clave} no está en la línea base")
        del_pool = [c for c in cambios if c["pool"] == clave and c["clase"] in CLASES_PROC]
        version = datos["procesos"][clave]["version_resultante"]
        semilla = f"{SEMILLA}/{clave}"
        if version == clave.rpartition("@")[2]:
            texto = misma.get(pool["fichero"]) or _texto(proyecto, pool["fichero"])
            misma[pool["fichero"]] = cirugia_proc(texto, pool["xmi_id"], del_pool, semilla)
            continue
        # Versión superior: la cirugía sobre el original y la copia en la versión nueva sobre su resultado; el
        # fichero viejo no se toca.
        texto = cirugia_proc(_texto(proyecto, pool["fichero"]), pool["xmi_id"], del_pool, semilla)
        nuevo, remapeo = nueva_version(texto, pool["xmi_id"], version, f"{semilla}/{version}")
        nombre = (f"{_nombre_seguro(clave.rpartition('@')[0])}-{version}.proc" if suben[pool["fichero"]] > 1
                  else nombre_fichero(nuevo, version))
        rel = f"{BONITA}/app/diagrams/{nombre}"
        escribir(rel, nuevo, clave)
        _libre(proyecto, rel, salida[rel], f"la versión {version} de {clave.rpartition('@')[0]}")
        if pool["conf"]:
            conf = f"{BONITA}/app/process_configurations/{remapeo[pool['xmi_id']]}.conf"
            escribir(conf, copiar_conf(_texto(proyecto, pool["conf"]), remapeo), clave)
            _libre(proyecto, conf, salida[conf], f"la configuración de la versión {version} de {clave}")
    for rel, texto in misma.items():
        if rel in salida:
            raise ValueError(f"{rel}: lo escribirían a la vez una versión superior y una cirugía en la misma versión")
        salida[rel] = texto.encode("utf-8")
    return salida


def _cirugia(proyecto: Path) -> dict[str, bytes]:
    """Ruta relativa -> contenido de cada fichero existente que cambia (o que se crea por una versión superior)."""
    linea_base = leer_linea_base(proyecto)
    datos = leer_confirmados(proyecto)
    # Lo que la persona confirmó es la operación calculada (con discrepancias no se puede confirmar).
    cambios = [{**c, "confirmado": c["calculado"]} for c in datos["cambios"]]
    salida: dict[str, bytes] = {}
    bdm = [c for c in cambios if c["clase"] in CLASES_BDM]
    if bdm:
        rel = f"{BONITA}/bdm/bom.xml"
        paquete = leer_existente(proyecto / COPIA)["bdm"]["paquete"]
        salida[rel] = cirugia_bom(_texto(proyecto, rel), bdm, paquete).encode("utf-8")
    org = [c for c in cambios if c["clase"] in CLASES_ORG]
    if org:
        rels = sorted(f for f in linea_base["ficheros"] if f.startswith(f"{BONITA}/app/organizations/"))
        if len(rels) != 1:
            raise ValueError(f"la organización tiene {len(rels)} ficheros en la línea base ({', '.join(rels) or '—'}); "
                             "la cirugía necesita exactamente uno")
        salida[rels[0]] = cirugia_organizacion(_texto(proyecto, rels[0]), org).encode("utf-8")
    salida.update(_cirugia_pools(proyecto, linea_base, datos, cambios))
    return salida


def fase_cerrada(proyecto: Path) -> bool:
    """Sin `cambios.md` ni `cambios-confirmados.md` no hay un cambio sobre lo existente en curso (p. ej. tras `cerrar`,
    spec 6.8.1): lo único que se genera son los procesos nuevos de la documentación."""
    return not (Path(proyecto) / CAMBIOS).is_file() and not (Path(proyecto) / CONFIRMADOS).is_file()


def generar_existente(proyecto: Path) -> list[Path]:
    """Genera un proyecto en modo existente y devuelve las rutas escritas: la cirugía confirmada (BDM, organización y
    cada pool en su misma versión o en la superior, con su `.conf`) y, si hay `bpmn.md`, los procesos nuevos con
    `build/spec.json`. `ValueError` (o `NotImplementedError`) sin escribir ni borrar nada si falta una exigencia (modo,
    handoff, huella del mapa, confirmación vigente), si lo nuevo pide un módulo que el proyecto no tiene o si un
    cambio falla.

    Con la fase cerrada (`fase_cerrada`) y procesos nuevos documentados, no hay cirugía: se escriben solo los procesos
    nuevos, sin exigir el handoff sobre el mapa actual ni una confirmación (spec 6.8.1: un cambio sobre ellos es
    documentación + `generar`)."""
    proyecto = Path(proyecto)
    if (fase_cerrada(proyecto) and (proyecto / BPMN).is_file() and modo_existente(proyecto)
            and leer_linea_base(proyecto) is not None):
        return aplicar_plan(proyecto, _procesos_nuevos(proyecto))
    motivos = _exigencias(proyecto)
    if motivos:
        raise ValueError("no se puede generar en modo existente:\n" + "\n".join(f"  {m}" for m in motivos))
    nuevos = _procesos_nuevos(proyecto)
    cambios = _cirugia(proyecto)
    _sin_ediciones(proyecto, leer_linea_base(proyecto), cambios)
    cirugia = [(proyecto / rel, contenido) for rel, contenido in cambios.items()]
    de_lo_nuevo = {r for r, _ in nuevos.escrituras + nuevos.internas} | set(nuevos.borrar)
    choques = sorted(r.relative_to(proyecto).as_posix() for r, _ in cirugia if r in de_lo_nuevo)
    if choques:
        raise ValueError("lo nuevo y la cirugía escribirían o borrarían los mismos ficheros: " + ", ".join(choques))
    return aplicar_plan(proyecto, Plan(cirugia + nuevos.escrituras, nuevos.internas, nuevos.borrar))
