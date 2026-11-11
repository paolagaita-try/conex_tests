"""Validaciones del hilo `organizacion` (Plan 5): nombres (R-16), jerarquía y *manager* (R-01), lanes sin actor y
actores de tarea (R-02), fin terminate (R-12) y consultas (R-05).

Lo que ya comprobaba `spec._validar_organizacion` (grupo y rol de actores y usuarios) sigue allí, ampliado a varios
roles y a las membresías extra; aquí va lo nuevo.
"""
from __future__ import annotations

from generadores.escribir.organizacion import actor_bonita
from generadores.escribir.perfiles import archivo_perfil
from generadores.leer import donde
from generadores.nombres import LANE_PROHIBIDO, PERFIL_PROHIBIDO, ROL, SEGMENTO_GRUPO, USUARIO, es

FB, FP = "bdm.md", "bpmn.md"
U_ORG = donde(FB, "Organización")
U_PERFILES = donde(FB, "Acceso al BDM", "Perfiles previstos")

MENSAJE = {
    "usuario": "debe ser letras, cifras, «.», «_» o «-» (p. ej. `solicitante.prueba1`)",
    "rol": "debe empezar por letra y seguir con letras, cifras, «_» o «-» (p. ej. `VPAdministrativo`)",
    "grupo": "cada tramo de la ruta debe ser letras, cifras, «_» o «-» (p. ej. `/empresa/compras`)",
    "perfil": "el nombre del perfil no puede tener «/», «\\», backticks ni caracteres de control "
              "(p. ej. `Solicitante SyP`)",
    "lane": "el nombre de la lane no puede tener backticks, «|» ni caracteres de control",
}


def _nombres(org: dict, err: list[str]) -> None:
    for u in org.get("usuarios", []):
        if not es(USUARIO, u.get("nombre")):
            err.append(f"{donde(U_ORG, str(u.get('nombre')))}: usuario «{u.get('nombre')}» {MENSAJE['usuario']}")
    for r in org.get("roles", []):
        if not es(ROL, r):
            err.append(f"{U_ORG}: rol «{r}» {MENSAJE['rol']}")
    grupos = org.get("grupos", [])
    for g in grupos:
        if not isinstance(g, str) or not all(es(SEGMENTO_GRUPO, s) for s in g.split("/")):
            err.append(f"{U_ORG}: grupo «/{g}» {MENSAJE['grupo']}")
            continue
        madre = g.rpartition("/")[0]
        if madre and madre not in grupos:
            err.append(f"{U_ORG}: el grupo «/{g}» no tiene a su padre «/{madre}» en grupos")
        elif madre and grupos.index(madre) > grupos.index(g):
            err.append(f"{U_ORG}: el grupo «/{g}» va antes que su padre «/{madre}» (los padres primero)")
    archivos: dict[str, str] = {}
    for pf in org.get("perfiles", []):
        nombre = pf.get("nombre")
        if not isinstance(nombre, str) or not nombre.strip(". ") or PERFIL_PROHIBIDO.search(nombre):
            err.append(f"{donde(U_PERFILES, str(nombre))}: «{nombre}»: {MENSAJE['perfil']}")
            continue
        fichero = archivo_perfil(nombre)
        if fichero in archivos:
            err.append(f"{donde(U_PERFILES, nombre)}: su fichero «{fichero}» es el mismo que el del perfil "
                       f"«{archivos[fichero]}»; cambia uno de los nombres")
        archivos.setdefault(fichero, nombre)


def _managers(org: dict, err: list[str]) -> None:
    nombres = {u.get("nombre") for u in org.get("usuarios", [])}
    for u in org.get("usuarios", []):
        m = u.get("manager")
        if m is None:
            continue
        uu = donde(U_ORG, str(u.get("nombre")))
        if m == u.get("nombre"):
            err.append(f"{uu}: el *manager* «{m}» es el propio usuario")
        elif m not in nombres:
            err.append(f"{uu}: el *manager* «{m}» no es un usuario de la organización (tabla de usuarios o "
                       "Membresía de prueba)")


def _lanes_y_actores(p: dict, org: dict, err: list[str]) -> None:
    nombre = p.get("nombre")
    up = donde(FP, "Pool y lanes", nombre)
    nodos = p.get("nodos", [])
    humanas = {n.get("id") for n in nodos if n.get("tipo") == "humana"}
    for l in p.get("lanes", []):
        ul = donde(up, str(l.get("nombre")))
        if not isinstance(l.get("nombre"), str) or LANE_PROHIBIDO.search(l["nombre"]):
            err.append(f"{ul}: {MENSAJE['lane']}")
        if l.get("sin_actor"):
            tareas = [n.get("id") for n in nodos if n.get("lane") == l.get("nombre") and n.get("tipo") == "humana"]
            if tareas:
                err.append(f"{ul}: la lane va sin actor («—» en Actor Bonita) y tiene tareas humanas "
                           f"({', '.join(tareas)}); solo puede tener tareas automáticas")
            if any(n.get("tipo") == "inicio" and n.get("lane") == l.get("nombre") for n in nodos) \
                    and p.get("iniciador") is not None:
                err.append(f"{ul}: el evento de inicio está en una lane sin actor y el pool tiene iniciador")
    nombres_lane = {actor_bonita(l) for l in p.get("lanes", []) if actor_bonita(l)}
    vistos: dict[str, str] = {}
    roles, grupos = org.get("roles", []), org.get("grupos", [])
    for a in p.get("actores_tarea", []):
        ua = donde(up, "Actor Bonita", str(a.get("nombre")))
        if a.get("nombre") in nombres_lane:
            err.append(f"{ua}: el actor de tarea se llama como el actor de una lane")
        if not a.get("roles") and not a.get("membresias"):
            err.append(f"{ua}: el actor de tarea no tiene Mapeo (roles o «`ruta` / `rol`»)")
        for r in a.get("roles", []):
            if r not in roles:
                err.append(f"{ua}: el rol «{r}» del Mapeo no está en bdm.md › Organización")
        for m in a.get("membresias", []):
            if m.get("grupo") not in grupos or m.get("rol") not in roles:
                err.append(f"{ua}: la membresía «/{m.get('grupo')} / {m.get('rol')}» del Mapeo no está en "
                           "bdm.md › Organización")
        if not a.get("tareas"):
            err.append(f"{ua}: el actor de tarea no nombra ninguna tarea")
        for t in a.get("tareas", []):
            if t not in humanas:
                err.append(f"{ua}: «{t}» no es una tarea humana del pool «{nombre}»")
            elif t in vistos:
                err.append(f"{ua}: la tarea «{t}» ya tiene el actor de tarea «{vistos[t]}»")
            vistos.setdefault(t, a.get("nombre"))
    for n in nodos:
        if n.get("terminar") and n.get("tipo") != "fin":
            err.append(f"{donde(FP, 'Eventos', nombre, str(n.get('id')))}: solo un evento de fin puede ser terminate")


def _consultas(bdm: dict, atributos: dict, err: list[str]) -> None:
    for o in bdm.get("objetos", []):
        u = donde(FB, "Objetos de negocio", o.get("nombre"))
        por_nombre = {q.get("nombre"): q for q in o.get("consultas", [])}
        simples = [a.get("nombre") for a in o.get("atributos", []) if not a.get("relacion") and not a.get("multiple")]
        # Doc 2026.2 (define-and-deploy-the-bdm): por unique constraint, por atributo simple y «Select All» (`find`).
        # Medido en Community 2026.2-u0 (D-36); con una unique constraint de dos atributos, [no verificado].
        defecto = {"find", "findByPersistenceId"} | {f"findBy{_cap(a)}" for a in simples}
        defecto |= {"findBy" + "And".join(_cap(c) for c in grupo) for grupo in o.get("unicos", [])}
        for q in o.get("consultas", []):
            uq = donde(u, q.get("nombre"))
            if q.get("por_defecto"):
                if q.get("nombre") not in defecto:
                    err.append(f"{uq}: «(por defecto)» solo vale para las que genera Bonita: find, findByPersistenceId, "
                               "findBy<Atributo> (atributo simple) o findBy<A>And<B> (unique constraint)")
                if q.get("jpql"):
                    err.append(f"{uq}: una consulta «(por defecto)» no lleva JPQL (quítala de consultas.md)")
            if q.get("paginada") and not q.get("por_defecto"):  # la de una por defecto la crea Bonita
                if q.get("devuelve") != "lista":
                    err.append(f"{uq}: solo una lista puede ser paginada")
                cuenta = f"countFor{_cap(q.get('nombre') or '')}"
                c = por_nombre.get(cuenta)
                if c is None:
                    err.append(f"{uq}: es «lista paginada» y falta su consulta «{cuenta}» (Devuelve «conteo», mismos "
                               "parámetros); Bonita la pide para paginar")
                elif c.get("devuelve") != "conteo" or c.get("parametros") != q.get("parametros"):
                    err.append(f"{donde(u, cuenta)}: debe devolver «conteo» con los mismos parámetros que "
                               f"«{q.get('nombre')}»")


def _cap(nombre: str) -> str:
    return nombre[:1].upper() + nombre[1:]


def validar(spec: dict, atributos: dict, err: list[str]) -> None:
    org = spec.get("organizacion", {})
    _nombres(org, err)
    _managers(org, err)
    _consultas(spec.get("bdm", {}), atributos, err)
    for p in spec.get("procesos", []):
        _lanes_y_actores(p, org, err)
