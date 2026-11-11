"""Cirugía en `bdm/bom.xml`: agrega objetos y atributos simples y modifica tipo, obligatoriedad o longitud de un
atributo (spec 6.7). Quitar y el resto de operaciones lanzan `NotImplementedError`."""
from generadores.escribir.bom import CLASE_JAVA, PAQUETE_PARAMETROS, elemento_campo, elemento_objeto
from generadores.existente import xmi
from generadores.existente.cirugia import hijos_de, operacion, salto_de


def _bool_nullable(obligatorio: bool) -> str:
    return "false" if obligatorio else "true"


def _tipo_simple(tipo: str, ubic: str) -> str:
    t = tipo.upper()
    if t not in CLASE_JAVA:
        raise NotImplementedError(f"{ubic}: el tipo «{tipo}» no es un tipo simple del BDM (relaciones y objetos "
                                  f"anidados no se aplican en esta entrega)")
    return t


def _objeto_en(nodos, objetos, nombre: str, paquete: str):
    """`(posición, nodo)` del `businessObject` `nombre`: el del `paquete` o, si no, el único con ese nombre corto."""
    por_nombre = [(i, n) for i, n in objetos if n.attrs.get("qualifiedName", "").rsplit(".", 1)[-1] == nombre]
    exacto = [(i, n) for i, n in por_nombre if n.attrs.get("qualifiedName") == f"{paquete}.{nombre}"]
    if exacto:
        return exacto[0]
    if len(por_nombre) == 1:
        return por_nombre[0]
    if len(por_nombre) > 1:
        raise ValueError(f"bom.xml: el objeto «{nombre}» está en varios paquetes y ninguno es «{paquete}»")
    return None


def _rango_atributo(texto: str, valor: xmi.Edicion) -> tuple[int, int]:
    """Rango `[ inicio, fin )` de ` nombre="valor"` (con el blanco que lo precede) dado el del valor."""
    ini = valor.inicio - 1  # la comilla de apertura
    while texto[ini - 1] in " \t=":
        ini -= 1
    while texto[ini - 1] not in " \t\r\n":
        ini -= 1
    while texto[ini - 1] in " \t\r\n":
        ini -= 1
    return ini, valor.fin + 1


def _modificar(texto: str, campo: xmi.Nodo, d: dict, ubic: str) -> list[xmi.Edicion]:
    if campo.tag != "field":
        raise NotImplementedError(f"{ubic}: «{d['atributo']}» es una relación; solo se modifican atributos simples")
    if d.get("multiple") is not None and d["multiple"] != (campo.attrs.get("collection") == "true"):
        raise NotImplementedError(f"{ubic}: cambiar «Múltiple» no está soportado (solo tipo, obligatoriedad o longitud)")
    ediciones: list[xmi.Edicion] = []
    tipo_actual = campo.attrs.get("type", "")
    tipo = _tipo_simple(d["tipo"], ubic) if d.get("tipo") else tipo_actual
    if tipo != tipo_actual:
        ediciones.append(xmi.poner_atributo(texto, campo, "type", tipo))
    if d.get("obligatorio") is not None:
        nullable = _bool_nullable(d["obligatorio"])
        if nullable != campo.attrs.get("nullable"):
            ediciones.append(xmi.poner_atributo(texto, campo, "nullable", nullable))
    longitud, tiene = d.get("longitud"), "length" in campo.attrs
    if tipo != "STRING":
        if longitud is not None:
            raise ValueError(f"{ubic}: la Longitud solo aplica a STRING, no a {tipo}")
        if tiene:
            ediciones.append(xmi.Edicion(*_rango_atributo(texto, xmi.poner_atributo(texto, campo, "length", "0")),
                                         ""))
    elif longitud is not None and campo.attrs.get("length") != str(longitud):
        if tiene:
            ediciones.append(xmi.poner_atributo(texto, campo, "length", str(longitud)))
        else:  # va justo detrás de `type`, como lo escribe el Studio
            t = xmi.poner_atributo(texto, campo, "type", tipo)
            pos = t.fin + 1 if t.fin > t.inicio else t.fin
            ediciones.append(xmi.Edicion(pos, pos, f' length="{longitud}"'))
    return ediciones


def cirugia_bom(texto: str, cambios: list[dict], paquete: str) -> str:
    """`texto` (el `bom.xml`) con los `cambios` aplicados. Un objeto nuevo entra tras el último objeto del dominio
    (antes de los `Kp*` del módulo de parámetros); un atributo nuevo, al final de los `fields` de su objeto."""
    for c in cambios:
        op, ubic = operacion(c), c.get("ubic", "cambios.md")
        if c["clase"] not in ("objeto", "atributo"):
            raise ValueError(f"{ubic}: la clase «{c['clase']}» no es del BDM")
        if op == "quita":
            raise NotImplementedError(f"{ubic}: quitar en el BDM no está soportado en esta entrega")
        if c["clase"] == "objeto" and op != "agrega":
            raise NotImplementedError(f"{ubic}: solo se puede agregar un objeto (no «{op}»)")
    nodos = xmi.indexar(texto)
    raiz = next((i for i, n in enumerate(nodos) if n.tag == "businessObjects"), None)
    if raiz is None:
        raise ValueError("bom.xml: no tiene <businessObjects>")
    objetos = hijos_de(nodos, raiz, "businessObject")

    nuevos: dict[str, dict] = {}
    for c in cambios:
        if c["clase"] == "objeto":
            nombre = c["datos"]["objeto"]
            if nombre in nuevos or _objeto_en(nodos, objetos, nombre, paquete) is not None:
                raise ValueError(f"{c.get('ubic', 'cambios.md')}: el objeto «{nombre}» ya existe en bom.xml")
            nuevos[nombre] = {"nombre": nombre, "atributos": []}

    ediciones: list[xmi.Edicion] = []
    agregados: dict[int, list[str]] = {}  # posición del `fields` -> fragmentos
    sangria_campo: dict[int, str] = {}
    salto = salto_de(texto)
    for c in (x for x in cambios if x["clase"] == "atributo"):
        d, op, ubic = c["datos"], operacion(c), c.get("ubic", "cambios.md")
        if op == "agrega":
            if d.get("tipo") is None:
                raise ValueError(f"{ubic}: un atributo nuevo necesita Tipo")
            tipo = _tipo_simple(d["tipo"], ubic)
            if d.get("longitud") is not None and tipo != "STRING":
                raise ValueError(f"{ubic}: la Longitud solo aplica a STRING, no a {tipo}")
            atributo = {"nombre": d["atributo"], "tipo": tipo, "obligatorio": bool(d.get("obligatorio")),
                        "multiple": bool(d.get("multiple")), "longitud": d.get("longitud")}
            if d["objeto"] in nuevos:
                nuevos[d["objeto"]]["atributos"].append(atributo)
                continue
        hallado = _objeto_en(nodos, objetos, d["objeto"], paquete)
        if hallado is None:
            raise ValueError(f"{ubic}: el objeto «{d['objeto']}» no existe en bom.xml")
        bo_pos, bo = hallado
        campos = hijos_de(nodos, bo_pos, "fields")
        if not campos:
            raise ValueError(f"{ubic}: el objeto «{d['objeto']}» no tiene <fields>")
        f_pos, f_nodo = campos[0]
        existente = next((n for _, n in hijos_de(nodos, f_pos) if n.attrs.get("name") == d["atributo"]), None)
        if op == "agrega":
            if existente is not None:
                raise ValueError(f"{ubic}: el atributo «{d['objeto']}.{d['atributo']}» ya existe en bom.xml")
            if f_pos not in sangria_campo:
                sangria_campo[f_pos] = xmi.sangria_hijo(texto, f_nodo)
            agregados.setdefault(f_pos, []).append(
                xmi.fragmento(elemento_campo(paquete, atributo), {},
                              sangria_campo[f_pos], salto))
        else:
            if existente is None:
                raise ValueError(f"{ubic}: el atributo «{d['objeto']}.{d['atributo']}» no existe en bom.xml")
            ediciones += _modificar(texto, existente, d, ubic)
    for f_pos, fragmentos in agregados.items():
        ediciones.append(xmi.insertar_hijos(texto, nodos[f_pos], fragmentos))

    if nuevos:
        sangria = xmi.sangria_hijo(texto, nodos[raiz])
        fragmentos = [xmi.fragmento(elemento_objeto(paquete, o), {}, sangria, salto) for o in nuevos.values()]
        dominio = [n for _, n in objetos if not n.attrs.get("qualifiedName", "").startswith(PAQUETE_PARAMETROS + ".")]
        if dominio:
            ediciones.append(xmi.Edicion(dominio[-1].fin, dominio[-1].fin,
                                         "".join(f"{salto}{sangria}{f}" for f in fragmentos)))
        else:
            ediciones.append(xmi.insertar_hijos(texto, nodos[raiz], fragmentos))
    return xmi.aplicar(texto, ediciones)
