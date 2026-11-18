"""Escritura de los artefactos Bonita generados a partir de una spec (completa o parcial)."""
import json
import re
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from generadores.escribir import acceso
from generadores.escribir.aplicaciones import generar_aplicacion, paginas, paginas_propias, token_pagina
from generadores.escribir.bom import generar_bom
from generadores.escribir.conf import generar_conf
from generadores.escribir.frontend import FORMS, MANIFIESTO, generar_frontend
from generadores.escribir.journey import generar_journey
from generadores.escribir.proc.configuraciones import ENTORNOS, NOMBRE_ENTORNO, entornos
from generadores.escribir.organizacion import con_administrador_studio, generar_organizacion
from generadores.escribir.parametros import (CONSULTAS, PROPIEDADES, generar_propiedades,
                                             generar_propiedades_consultas, semilla_bytes)
from generadores.escribir.perfiles import archivo_perfil, generar_perfiles, generar_perfiles_por_defecto
from generadores.escribir.proc import generar_proc, id_pool
from generadores.escribir.proc.conectores import de_la_spec
from generadores.version import RAIZ_REPO
from generadores.xmlutil import xml_bytes

# El proceso de ejemplo `hola` de la plantilla usa este BO; sin él en el BDM no compila.
_BO_HOLA = "com.trycore.hola.model.Saludo"
_ORGANIZACION_HOLA = "organizations/hola.xml"
_PROC_HOLA = "diagrams/Hola-1.0.proc"
# Spec de hola: su BDM y su organización son los de la plantilla (los que usa una spec que no trae los suyos).
SPEC_HOLA = RAIZ_REPO / "plantilla" / "hola" / "spec-hola.json"
# Lista de los .proc/.conf/aplicaciones que escribió escribir_proyecto (rutas relativas al proyecto).
GENERADOS = Path("build") / "generados.json"
# Lo único que se borra desde esa lista: un .proc, un .conf o una aplicación directamente en su carpeta.
_BORRABLE = re.compile(r"bonita-project/app/(diagrams/[^/]+\.proc|process_configurations/[^/]+\.conf|applications/[^/]+\.xml)")


# Lo que la plantilla genera de `hola` con los escritores reales: su proceso, su formulario Svelte de tarea en su propia
# aplicación y su parámetro de negocio (`proyecto.nombre` = `hola` nombra su semilla). Su BDM y su organización son los
# de la plantilla, que no se regeneran.
_CLAVES_HOLA = ("proyecto", "procesos", "formularios", "parametros_negocio")


def _spec_hola() -> dict:
    return json.loads(SPEC_HOLA.read_text(encoding="utf-8"))


def spec_de_hola() -> dict:
    """La spec con la que la plantilla genera `hola` (la que usan `nuevo_proyecto` y el custodio de generados en la
    unidad 0)."""
    hola = _spec_hola()
    return {k: hola[k] for k in _CLAVES_HOLA if k in hola}


def _leer_generados(proyecto: Path) -> list[str]:
    ruta = proyecto / GENERADOS
    if not ruta.is_file():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))["generados"]


def _borrable(proyecto: Path, rel: str) -> Path | None:
    """La ruta de una entrada de `generados.json` si es un .proc/.conf del propio proyecto (relativa, sin `..`, en
    `app/diagrams` o `app/process_configurations`, y que resuelve dentro del proyecto); si no, None."""
    if not isinstance(rel, str) or not _BORRABLE.fullmatch(rel) or ".." in PurePosixPath(rel).parts:
        return None
    ruta = proyecto / rel
    # Un enlace simbólico en el camino podría sacarla del proyecto.
    return ruta if ruta.resolve().is_relative_to(proyecto.resolve()) else None


def _hola_a_quitar(proyecto: Path) -> list[Path]:
    """Lo de `hola` que exista en el proyecto: su .proc, el .conf de su pool (nombre derivado del id del pool), su
    semilla de parámetros, los ficheros de su formulario Svelte (generados y esqueleto: son de la plantilla, no del
    proyecto) y sus pruebas e2e. Su aplicación sale por `build/generados.json`, como toda aplicación generada."""
    app = proyecto / "bonita-project" / "app"
    proc = app / _PROC_HOLA
    if not proc.is_file():
        return []
    hola = spec_de_hola()
    conf = app / "process_configurations" / f"{id_pool(ET.parse(proc))}.conf"
    semilla = proyecto / "bonita-project" / "parametros" / "semillas" / f"{hola['proyecto']['nombre']}.json"
    formularios = []
    for form in hola["formularios"]["formularios"]:
        carpeta = proyecto / FORMS / token_pagina(form["id"])
        if carpeta.is_dir() and not carpeta.is_symlink():
            formularios += sorted(f for f in carpeta.rglob("*") if f.is_file() or f.is_symlink())
    # Sus pruebas e2e (Playwright) se van con él: la de su tarea y la de la app de parámetros, que usa su semilla y sus
    # administradores. El apoyo (`e2e/apoyo/`), la página y la aplicación de parámetros son de la plantilla y se quedan.
    e2e = [proyecto / "frontend" / "e2e" / f for f in ("hola.spec.ts", "parametros.spec.ts")]
    return [f for f in (proc, conf, semilla, *e2e) if f.is_file()] + formularios


def _dentro(proyecto: Path, ruta: Path) -> Path:
    """`ruta` si resuelve dentro de `proyecto`; si no (un `..` o un enlace simbólico en un nombre que viene de la
    configuración o de la documentación), ValueError. Es la guarda única de toda escritura y todo borrado."""
    if not ruta.resolve().is_relative_to(proyecto.resolve()):
        raise ValueError(f"«{ruta}» queda fuera del proyecto {proyecto}: nombre no válido en la spec (no se escribió "
                         "nada)")
    return ruta


def xml_entorno(nombre: str) -> bytes:
    """El XML de un entorno que el generador crea (los que no son Qualification ni Production, que vienen de la
    plantilla)."""
    return xml_bytes(ET.ElementTree(ET.Element("environment:Environment", {
        "xmlns:environment": "http://www.bonitasoft.org/ns/studio/environment", "name": nombre,
        "description": f"Entorno {nombre}"})))


def _json_bytes(datos) -> bytes:
    return (json.dumps(datos, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _version_bonita(spec: dict, proyecto: Path) -> str:
    """Versión de Bonita del proyecto (ids de los conectores): la de la spec, si no la de `.trycore-bonita.json`, y
    si no 2026.2."""
    v = spec.get("proyecto", {}).get("version_bonita")
    meta = proyecto / ".trycore-bonita.json"
    if not v and meta.is_file():
        v = json.loads(meta.read_text(encoding="utf-8")).get("version_bonita")
    return v or "2026.2"


class Plan(NamedTuple):
    """Lo que `escribir_proyecto` hará en disco, calculado en memoria: `escrituras` (las que devuelve), `internas`
    (`build/generados.json`) y `borrar`."""
    escrituras: list[tuple[Path, bytes]]
    internas: list[tuple[Path, bytes]]
    borrar: list[Path]


def escribir_proyecto(spec: dict, proyecto: Path, existente: bool = False) -> list[Path]:
    """Escribe bajo `proyecto/bonita-project/` y `proyecto/journey/` lo que la spec (parcial) describe y
    devuelve las rutas escritas (`planear_proyecto` y después `aplicar_plan`). Con un BDM propio, `hola` (que depende
    del suyo) se quita de la plantilla entero: .proc, .conf, semilla, aplicación y formulario.

    Por cada proceso: `app/diagrams/<nombre>-<version>.proc` y `app/process_configurations/<id del pool>.conf`
    (con la organización de la spec o, si no la trae, la de la plantilla; igual con el BDM). Antes borra los
    .proc/.conf que generó en una corrida anterior (`build/generados.json`); los ficheros ajenos no se tocan. Con
    `caminos` (y la spec completa que nombran), el journey Newman en `journey/<nombre>.postman_collection.json`.
    Con `formularios` y `procesos`, el frontend de cada formulario Svelte (`escribir/frontend.py`): su contrato y su
    esquema generados y `frontend/forms.manifest.json`, y su esqueleto editable solo donde no existe. Con `procesos`,
    el bloque generado de los dos `configuration.properties` mixtos (`parametros.MIXTOS`: el del módulo de parámetros
    y, si el proyecto tiene la extensión de consultas, el suyo); el resto de cada fichero se conserva.

    Todo (BDM, organización, perfiles, .proc, .conf, entornos y journey) se genera en memoria antes de tocar el
    disco, y cada destino o borrado tiene que resolver dentro del proyecto: un elemento no soportado, un Groovy
    inválido o un nombre con `..` hacen fallar la llamada (ValueError, NotImplementedError…) sin escribir ni borrar
    nada.

    Con `existente=True` (proyecto en modo «proyecto existente»: lo nuevo junto a lo hecho en el Studio) no escribe
    `bom.xml`, la organización ni los perfiles, no quita `hola`, solo pone al día el `configuration.properties` del
    módulo de parámetros y el frontend (`frontend/forms.manifest.json`) si el proyecto ya los tiene, no reescribe la
    semilla de parámetros si lo nuevo no trae parámetros de negocio, y ningún fichero de la línea base se escribe ni
    se borra (`ValueError` si la spec lo pisaría)."""
    proyecto = Path(proyecto)
    return aplicar_plan(proyecto, planear_proyecto(spec, proyecto, existente))


def planear_proyecto(spec: dict, proyecto: Path, existente: bool = False) -> Plan:
    """El `Plan` de `escribir_proyecto(spec, proyecto, existente)`, sin tocar el disco."""
    proyecto = Path(proyecto)
    app = proyecto / "bonita-project" / "app"
    escrituras: list[tuple[Path, bytes]] = []  # en orden; las que se devuelven
    borrar: list[Path] = []
    previos = _leer_generados(proyecto)
    quitados: set[str] = set()
    procesos = []
    if "procesos" in spec:
        hola = _spec_hola()
        bdm = spec.get("bdm") or hola["bdm"]
        org = spec.get("organizacion") or hola["organizacion"]
        v = _version_bonita(spec, proyecto)
        ext = de_la_spec(spec)  # conectores y filtros propios del proyecto (Plan 5, hilo extensiones)
        procesos = [(p, generar_proc(p, bdm, spec["procesos"], v, org, spec.get("formularios"), extensiones=ext),
                    generar_conf(p, org, version_bonita=v, extensiones=ext))
                    for p in spec["procesos"]]
    if "bdm" in spec and not existente:
        escrituras.append((proyecto / "bonita-project" / "bdm" / "bom.xml", xml_bytes(generar_bom(spec["bdm"]))))
        calificados = {f"{spec['bdm']['paquete']}.{o['nombre']}" for o in spec["bdm"]["objetos"]}
        if _BO_HOLA not in calificados:
            for f in _hola_a_quitar(proyecto):
                borrar.append(f)
                quitados.add(str(f.relative_to(proyecto)))
    if "organizacion" in spec and not existente:
        # Siempre con el administrador del Studio y los mapeos de los perfiles por defecto (`default_profile.xml`).
        org = con_administrador_studio(spec["organizacion"])
        nombre = spec.get("proyecto", {}).get("nombre") or proyecto.name
        ruta = app / "organizations" / f"{nombre}.xml"
        # El build admite una sola organización: se quita la de `hola` (nombre exacto) salvo que sea la propia.
        hola_org = app / _ORGANIZACION_HOLA
        if hola_org != ruta and hola_org.is_file():
            borrar.append(hola_org)
        escrituras.append((ruta, xml_bytes(generar_organizacion(org))))
        escrituras.append((app / "profiles" / "default_profile.xml", xml_bytes(generar_perfiles_por_defecto(org))))
        if generar_perfiles(org, org.get("perfiles", [])) is not None:
            for p in org["perfiles"]:
                escrituras.append((app / "profiles" / archivo_perfil(p["nombre"]),
                                   xml_bytes(generar_perfiles(org, [p]))))
    # En modo existente la semilla del proyecto no se pisa si lo nuevo no trae parámetros de negocio.
    if "parametros_negocio" in spec and (spec["parametros_negocio"] or not existente):
        nombre = spec.get("proyecto", {}).get("nombre") or proyecto.name
        semilla = proyecto / "bonita-project" / "parametros" / "semillas" / f"{nombre}.json"
        if existente and semilla.is_file() and semilla.read_bytes() != semilla_bytes(spec):
            raise ValueError(f"{semilla.relative_to(proyecto).as_posix()}: el proyecto ya tiene su semilla de "
                             "parámetros y lo nuevo trae parámetros de negocio; combinar semillas no está soportado "
                             "en esta entrega (va a references/huecos-del-arnes.md)")
        escrituras.append((semilla, semilla_bytes(spec)))
    # R-14 (hilo acceso): bloque de reglas dinámicas en el properties mixto; sin reglas, solo si ya tiene el bloque.
    reglas_props = proyecto / acceso.PROPIEDADES
    if spec.get("acceso", {}).get("reglas") or (
            reglas_props.is_file() and acceso.INICIO in reglas_props.read_text(encoding="iso-8859-1")):
        escrituras.append((reglas_props, acceso.generar_propiedades(
            spec, reglas_props.read_bytes() if reglas_props.is_file() else None)))
    props = proyecto / PROPIEDADES
    if "procesos" in spec and (props.is_file() or not existente):
        escrituras.append((props, generar_propiedades(spec, props.read_bytes() if props.is_file() else None)))
    if "procesos" in spec:
        # La extensión de consultas es código de la plantilla: su configuración solo se pone al día si está.
        consultas = proyecto / CONSULTAS
        if consultas.is_file():
            escrituras.append((consultas, generar_propiedades_consultas(spec, consultas.read_bytes())))
    aplicaciones: list[tuple[Path, bytes]] = []
    if spec.get("formularios"):
        por_app = paginas(spec["formularios"])
        propias = paginas_propias(spec["formularios"])
        for a in spec["formularios"].get("aplicaciones", []):
            # Una aplicación sin páginas Svelte ni páginas propias no tiene nada que contener.
            if por_app.get(a["token"]) or propias.get(a["token"]):
                aplicaciones.append((app / "applications" / f"{a['token']}.xml",
                                     xml_bytes(generar_aplicacion(a, por_app.get(a["token"], []),
                                                                  propias.get(a["token"], [])))))
        escrituras.extend(aplicaciones)
    # En modo existente, un proyecto sin el frontend de la plantilla no lo recibe: sus formularios nuevos son «No form»
    # o «External URL» (con uno Svelte, `generar` ya se detuvo pidiendo el módulo; spec 6.8.2).
    if spec.get("formularios") and "procesos" in spec and (not existente or (proyecto / MANIFIESTO).is_file()):
        # Contrato, esquema y manifiesto se reescriben; el esqueleto de cada pantalla, solo si aún no existe.
        generados_fe, esqueleto = generar_frontend(spec, proyecto)
        escrituras.extend(generados_fe)
        # Lo que se va a borrar (el formulario de `hola`) no cuenta como existente.
        escrituras.extend((r, d) for r, d in esqueleto if not r.exists() or r in borrar)
    lista_generados: list[str] | None = None
    if "procesos" in spec:
        for rel in sorted(previos, key=str):
            if isinstance(rel, str) and rel in quitados:
                continue
            viejo = _borrable(proyecto, rel)
            if viejo is None:
                warnings.warn(f"{GENERADOS}: se ignora «{rel}» (solo se borran .proc de app/diagrams y .conf de "
                              "app/process_configurations del propio proyecto)", UserWarning, stacklevel=2)
            elif viejo.is_file():
                borrar.append(viejo)
        lista_generados = []
        for p, proc, conf in procesos:
            for ruta, arbol in ((app / "diagrams" / f"{p['nombre']}-{p['version']}.proc", proc),
                                (app / "process_configurations" / f"{id_pool(proc)}.conf", conf)):
                escrituras.append((ruta, xml_bytes(arbol)))
                lista_generados.append(str(ruta.relative_to(proyecto)))
        lista_generados.extend(str(r.relative_to(proyecto)) for r, _ in aplicaciones)
        for e in sorted({e for p, _, _ in procesos for e in entornos(p)} - set(ENTORNOS)):
            if not NOMBRE_ENTORNO.fullmatch(e):  # defensa en el escritor: nunca una ruta fuera de environements/
                raise ValueError(f"nombre de entorno no válido: «{e}»")
            ruta = app / "environements" / f"{e}.xml"
            if not ruta.is_file():
                escrituras.append((ruta, xml_entorno(e)))
    elif quitados and previos:
        lista_generados = [r for r in previos if r not in quitados]
    if "caminos" in spec:
        nombre = spec.get("proyecto", {}).get("nombre") or proyecto.name
        escrituras.append((proyecto / "journey" / f"{nombre}.postman_collection.json",
                           _json_bytes(generar_journey(spec))))
    internas = [(proyecto / GENERADOS, _json_bytes({"generados": sorted(set(lista_generados))}))] \
        if lista_generados is not None else []
    if existente:
        _sin_tocar_la_linea_base(proyecto, [r for r, _ in escrituras] + borrar)
        _sin_pisar_lo_del_proyecto(proyecto, escrituras, set(lista_generados or []), set(previos))
    return Plan(escrituras, internas, borrar)


def _sin_pisar_lo_del_proyecto(proyecto: Path, escrituras: list[tuple[Path, bytes]], generados: set[str],
                               previos: set[str]) -> None:
    """ValueError si una escritura de lo que el arnés genera (`.proc`, `.conf` y aplicaciones, los de
    `build/generados.json`) reescribiría con otro contenido un fichero del proyecto que no generó una generación
    anterior (no está en `build/generados.json`): p. ej. una aplicación propia con el mismo token que la de un proceso
    nuevo."""
    for ruta, datos in escrituras:
        rel = ruta.relative_to(proyecto).as_posix()
        if rel in generados and rel not in previos and ruta.is_file() and ruta.read_bytes() != datos:
            raise ValueError(f"{rel} es del proyecto (no lo generó el arnés: no está en {GENERADOS.as_posix()}) y lo "
                             "nuevo lo reescribiría; no se pisa. Una aplicación propia con el mismo token que la de "
                             "un proceso nuevo no está soportada en esta entrega (va a "
                             "references/huecos-del-arnes.md): da otro token a la aplicación de lo nuevo (p. ej. con "
                             "«Familia visible» en matriz-formularios.md)")


def _sin_tocar_la_linea_base(proyecto: Path, rutas: list[Path]) -> None:
    """ValueError si alguna ruta es un fichero de la línea base (solo la cirugía confirmada los cambia)."""
    from generadores.existente.linea_base import leer_linea_base  # diferido: el modo existente importa escribir
    datos = leer_linea_base(proyecto) or {"ficheros": {}}
    pisados = sorted({r.relative_to(proyecto).as_posix() for r in rutas} & set(datos["ficheros"]))
    if pisados:
        raise ValueError("lo nuevo pisaría ficheros existentes de la línea base (" + ", ".join(pisados) + "); solo "
                         "los cambia la cirugía confirmada: da otro nombre o versión al proceso nuevo")


def aplicar_plan(proyecto: Path, plan: Plan) -> list[Path]:
    """Lleva `plan` al disco y devuelve las rutas de sus `escrituras`. Antes de tocar nada, cada destino y cada
    borrado tiene que resolver dentro del proyecto (ValueError si no)."""
    proyecto = Path(proyecto)
    escrituras, internas, borrar = plan
    # La guarda, sobre todo lo planeado y antes de tocar nada.
    for ruta in [r for r, _ in escrituras + internas] + borrar:
        _dentro(proyecto, ruta)
    for f in borrar:
        if f.is_file() or f.is_symlink():
            f.unlink()
    # Las carpetas que quedan vacías bajo frontend/src/forms (el formulario de `hola`) se van con sus ficheros.
    forms = proyecto / FORMS
    for carpeta in sorted({p for f in borrar for p in f.parents if forms in p.parents}, key=lambda p: -len(p.parts)):
        if carpeta.is_dir() and not carpeta.is_symlink() and not any(carpeta.iterdir()):
            carpeta.rmdir()
    for ruta, datos in escrituras + internas:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(datos)
    return [r for r, _ in escrituras]
