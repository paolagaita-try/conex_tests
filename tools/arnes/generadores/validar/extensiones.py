"""Validaciones del hilo `extensiones` (Plan 5, R-03 y R-10): filtros y conectores propios del proyecto.

- Actor filters: el conjunto de filtros que `bpmn.md` aplica (lanes y actores de tarea, `filtro_de_tarea`) es el de
  `bdm.md › Organización`; cada filtro asigna exactamente las tareas de su «Tarea que asigna» (en todos los pools);
  su definición está en `bonita-project/extensions` (`spec.extensiones`) y sus entradas son inputs del `.def`, con
  todos los obligatorios.
- Conectores propios: su definición está en el proyecto, sus entradas son inputs del `.def` (todos los obligatorios)
  y sus salidas, outputs del `.def`. Un mismo ID lleva siempre el mismo tipo y definición, en todos los pools.

Lo estructural de los conectores (tarea, tipo, momento, URL del REST GET, destinos de las salidas, orden) lo valida
`spec._validar_proceso`.
"""
from __future__ import annotations

from generadores.escribir.proc.conectores import FALTA_DEFINICION
from generadores.escribir.proc.filtros import filtro_de_tarea
from generadores.leer import donde

FB, FP = "bdm.md", "bpmn.md"


def _entradas(def_id: str, d: dict, entradas: dict, u: str, que: str, err: list[str]) -> None:
    nombres = [i.get("nombre") for i in d.get("entradas", [])]
    for clave, groovy in (entradas or {}).items():
        if clave not in nombres:
            err.append(f"{u}: {que}: «{clave}» no es una entrada de la definición «{def_id}» ({', '.join(nombres)})")
        elif not groovy:
            err.append(f"{u}: {que}: la entrada «{clave}» está sin Groovy en expresiones.md")
    for i in d.get("entradas", []):
        if i.get("obligatoria") and i.get("nombre") not in (entradas or {}):
            err.append(f"{u}: {que}: falta la entrada obligatoria «{i.get('nombre')}» de la definición «{def_id}»")


def _registrado(def_id: str, d: dict, u: str, err: list[str]) -> None:
    if d.get("registrado") is False:
        m = d.get("modulo")
        err.append(f"{u}: el módulo «{m}» de la definición «{def_id}» no está registrado en "
                   "bonita-project/extensions/pom.xml (<modules>) y bonita-project/app/pom.xml (dependencia): su .impl "
                   f"no entraría en el .bar. Regístralo con `python3 tools/arnes/herramientas/registrar_extension.py . "
                   f"{m}` (desde el arnés: `python3 herramientas/registrar_extension.py <proyecto> {m}`)")


def _filtros(spec: dict, definiciones: dict, err: list[str]) -> None:
    """Ningún filtro se pierde en silencio: el de cada lane y el de cada actor de tarea está declarado y se aplica a
    alguna tarea humana; cada filtro declarado lo aplica alguna lane o actor de tarea, a sus «Tarea que asigna»."""
    declarados = spec.get("filtros") or {}
    aplicados: dict[str, list[str]] = {}
    usados: set[str] = set()
    for p in spec.get("procesos", []):
        for n in p.get("nodos", []):
            f = filtro_de_tarea(p, n)
            if f is not None:
                aplicados.setdefault(f, []).append(n.get("id"))
        origenes = [(l.get("filtro"), donde(FP, "Pool y lanes", p.get("nombre"), l.get("nombre")), "la lane")
                    for l in p.get("lanes", []) if l.get("filtro")]
        origenes += [(a.get("filtro"), donde(FP, "Pool y lanes", p.get("nombre"), f"actor de tarea {a.get('nombre')}"),
                      "el actor de tarea") for a in p.get("actores_tarea", []) if a.get("filtro")]
        for f, u, quien in origenes:
            usados.add(f)
            if f not in declarados:
                err.append(f"{u}: usa el actor filter «{f}», que no está declarado en {FB} › Organización (tabla "
                           "«Actor filter»)")
            if quien == "la lane":
                lane = u.split(" › ")[-1]
                if not any(filtro_de_tarea(p, n) == f and n.get("lane") == lane for n in p.get("nodos", [])):
                    err.append(f"{u}: el actor filter «{f}» de la lane no se aplica a ninguna tarea humana (la lane no "
                               "tiene, o todas tienen actor de tarea): se perdería en silencio")
    for id_, f in declarados.items():
        u = donde(FB, "Organización", id_)
        if id_ not in usados:
            err.append(f"{u}: filtro declarado que ninguna lane ni actor de tarea de {FP} aplica")
        elif sorted(set(f.get("tareas_doc") or [])) != sorted(set(aplicados.get(id_, []))):
            err.append(f"{u}: «Tarea que asigna» {sorted(set(f.get('tareas_doc') or []))} no son las tareas humanas a "
                       f"las que {FP} aplica el filtro {sorted(set(aplicados.get(id_, [])))}")
        d = definiciones.get(f.get("definicion"))
        if d is None:
            err.append(f"{u}: {FALTA_DEFINICION.format(id=f.get('definicion'))}")
            continue
        if d.get("tipo") == "conector":
            err.append(f"{u}: la definición «{f.get('definicion')}» es un conector (su implementación extiende "
                       "AbstractConnector), no un actor filter (AbstractUserFilter)")
        _registrado(f.get("definicion"), d, u, err)
        _entradas(f.get("definicion"), d, f.get("entradas"), u, f"filtro «{id_}»", err)


def _conectores(spec: dict, definiciones: dict, err: list[str]) -> None:
    tipo_de: dict[str, tuple] = {}
    registro_avisado: set[str] = set()
    for p in spec.get("procesos", []):
        conectores = p.get("conectores", [])
        if not isinstance(conectores, list):
            continue  # ya lo dice _validar_proceso
        for c in conectores:
            u = donde(FP, "Conectores por tarea", p.get("nombre"), c.get("tarea"))
            clave = (c.get("tipo"), c.get("definicion"))
            if tipo_de.setdefault(c.get("id"), clave) != clave:
                err.append(f"{u}: el conector «{c.get('id')}» no lleva el mismo tipo y definición en todas sus filas")
            if c.get("tipo") != "propio":
                continue
            def_id = c.get("definicion")
            d = definiciones.get(def_id)
            if d is None:
                err.append(f"{u}: conector «{c.get('id')}»: {FALTA_DEFINICION.format(id=def_id)}")
                continue
            if d.get("tipo") == "filtro":
                err.append(f"{u}: conector «{c.get('id')}»: la definición «{def_id}» es un actor filter (su "
                           "implementación extiende AbstractUserFilter), no un conector (AbstractConnector)")
            if def_id not in registro_avisado:
                registro_avisado.add(def_id)
                _registrado(def_id, d, u, err)
            _entradas(def_id, d, c.get("entradas"), u, f"conector «{c.get('id')}»", err)
            salidas = [s.get("nombre") for s in d.get("salidas", [])]
            for s in c.get("salidas", []):
                if s.get("salida") not in salidas:
                    err.append(f"{u}: conector «{c.get('id')}»: «{s.get('salida')}» no es una salida de la definición "
                               f"«{def_id}» ({', '.join(salidas) or 'ninguna'})")


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    definiciones = (spec.get("extensiones") or {}).get("definiciones") or {}
    _filtros(spec, definiciones, err)
    _conectores(spec, definiciones, err)
