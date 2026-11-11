"""Cirugía en un `.proc` del Studio (spec 6.7): inserta una tarea humana o de servicio sobre una transición existente
(la transición queda partida en dos), renombra una tarea, quita una tarea con una sola entrada y una sola salida (sus
vecinos se reconectan) y agrega inputs simples al contrato de una tarea humana. Lo demás lanza `NotImplementedError`.

El texto se edita por rangos (`generadores.existente.xmi`): lo que no se toca queda idéntico byte a byte. Los elementos
nuevos (nodo, transición, contrato, figura y conector) salen de los mismos constructores que usa el generador
(`generadores.escribir.proc`), así que tienen su forma exacta, con `xmi:id` deterministas (`Ids(semilla)`) que se saltan
los que el fichero ya usa. Los identificadores de los cambios (clave del mapa o `xmi:id`) se resuelven contra el
fichero tal como llega, antes de aplicar ningún cambio."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from generadores.escribir.proc import flujo, notacion
from generadores.escribir.proc.contratos import entrada, obligatorias, restriccion
from generadores.escribir.proc.datos import Contexto
from generadores.escribir.proc.ids import XMI_ID, XMI_TYPE, vista
from generadores.existente import xmi
from generadores.existente.cirugia import hijos_de, operacion, salto_de
from generadores.existente.clasificar import TIPOS_INPUT_SIMPLES, nodo_del_pool, tipo_de_tarea, transicion_del_pool
from generadores.existente.leer_xml import leer_pool
from generadores.xmlutil import Ids

SEPARACION = notacion.COLUMNA - notacion.CELDA  # hueco entre una figura y la siguiente, como en el generador
HOLGURA = 20  # espacio libre mínimo entre una figura nueva y las que ya están en su lane
_SHAPE = "notation:Shape"
PUNTOS_SIN_RUTA = "[0, 0, 0, 0]$[0, 0, 0, 0]"  # los `RelativeBendpoints` de un conector recién hecho

Caja = tuple[int, int, int, int]  # (x, y, ancho, alto) relativos a la lane


class _IdsLibres(Ids):
    """`Ids(semilla)` que se salta los `xmi:id` que ya están en el fichero (y los que ya dio)."""

    def __init__(self, semilla: str, ocupados):
        super().__init__(semilla)
        self._ocupados = set(ocupados)

    def siguiente(self) -> str:
        valor = super().siguiente()
        while valor in self._ocupados:
            valor = super().siguiente()
        self._ocupados.add(valor)
        return valor


def cirugia_proc(texto: str, pool_xmi_id: str, cambios: list[dict], semilla: str) -> str:
    """`texto` (un `.proc`) con los `cambios` confirmados de clase `nodo` y `contrato` aplicados al pool `pool_xmi_id`.

    - Insertar (`agrega` nodo con «Sobre la transición»): la transición `desde → hacia` pasa a `desde → nueva`
      (conserva su id y su condición) y se crea `nueva → hacia`. La tarea va al final de su lane; su figura, a la
      derecha de la de `desde` y sin superponerse a las de la lane (si no cabe, más a la derecha, en el primer hueco
      libre; si se sale de la lane, se ensanchan las lanes y el pool). Cada transición nueva lleva su conector.
    - Renombrar (`modifica` nodo): solo cambia `name`.
    - Quitar (`quita` nodo): se van la tarea (con su contrato, form mapping, operaciones y conectores), su figura, su
      transición de salida y el conector de esta. La transición de entrada se conserva entera (id, `name`, condición,
      `isDefault`, tabla de decisión y su lugar en el `outgoing` de `previo`) y solo cambia su `target` a `siguiente`;
      su conector pasa a llegar a la figura de `siguiente` (sin el anclaje ni los puntos de paso de la figura quitada).
      Si `previo → siguiente` ya existe, `NotImplementedError` (no se crean transiciones paralelas).
    - Agregar input (`agrega` contrato): tras los inputs del contrato, con su constraint `mandatory_<input>` al final de
      las constraints si es obligatorio. Vale para una tarea insertada en el mismo lote.

    `ValueError` si un cambio no cuadra con el fichero (no existe, ambiguo, ya existe, dos cambios tocan la misma
    transición o el mismo nodo); `NotImplementedError` si la operación no está en la spec 6.7."""
    return xmi.aplicar(texto, _Cirugia(texto, pool_xmi_id, semilla).ediciones(cambios))


def _ubic(c: dict) -> str:
    return c.get("ubic", "cambios.md")


def _input_simple(d: dict, ubic: str) -> dict:
    tipo = (d.get("tipo") or "").upper()
    if tipo not in TIPOS_INPUT_SIMPLES or d.get("multiple"):
        multiple = " múltiple" if d.get("multiple") else ""
        raise NotImplementedError(f"{ubic}: solo se agregan inputs simples ({', '.join(sorted(TIPOS_INPUT_SIMPLES))}) "
                                  f"de un valor; «{d['input']}» es {d.get('tipo')}{multiple}")
    return {"nombre": d["input"], "tipo": tipo, "obligatorio": bool(d.get("obligatorio"))}


def _se_tocan(a: Caja, b: Caja) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + HOLGURA <= bx or bx + bw + HOLGURA <= ax
                or ay + ah + HOLGURA <= by or by + bh + HOLGURA <= ay)


class _Cirugia:
    def __init__(self, texto: str, pool_xmi_id: str, semilla: str):
        self.texto = texto
        self.nodos = xmi.indexar(texto)
        xmi.por_id(self.nodos)  # ValueError si el fichero ya trae un xmi:id repetido
        self.pos = {n.attrs["xmi:id"]: i for i, n in enumerate(self.nodos) if "xmi:id" in n.attrs}
        self.ids = _IdsLibres(semilla, self.pos)
        raiz = ET.fromstring(texto)
        self.et = {e.get(XMI_ID): e for e in raiz.iter() if e.get(XMI_ID)}
        self.pool_e = self.et.get(pool_xmi_id)
        if self.pool_e is None or self.pool_e.get(XMI_TYPE) != "process:Pool":
            raise ValueError(f"el fichero no tiene un pool con xmi:id «{pool_xmi_id}»")
        self.pool = leer_pool(raiz, self.pool_e, "")
        self.salto = salto_de(texto)
        self.prefijos = {k[6:]: v for k, v in self.nodos[0].attrs.items() if k.startswith("xmlns:")}
        self.vistas: dict[str, list[int]] = {}  # id de un elemento del modelo -> posiciones de sus vistas
        for i, n in enumerate(self.nodos):
            if "element" in n.attrs and n.attrs.get("xmi:type", "").startswith("notation:"):
                self.vistas.setdefault(n.attrs["element"], []).append(i)
        self.nombres = {n["nombre"] for n in self.pool["nodos"].values()}
        # Ediciones pendientes, por posición de nodo en `self.nodos`.
        self.atributos: dict[tuple[int, str], str] = {}
        self.quitados: set[int] = set()
        self.tras: dict[int, list[ET.Element]] = {}  # hermanos nuevos tras el nodo
        self.antes: dict[int, list[ET.Element]] = {}  # hermanos nuevos antes del nodo
        self.dentro: dict[int, list[ET.Element]] = {}  # hijos nuevos al final del nodo
        self.flujos_tocados: set[str] = set()
        self.nodos_tocados: set[str] = set()
        self.quitadas: set[str] = set()
        self._cajas: dict[int, list[Caja]] | None = None
        self.ancho = 0  # ancho de lane necesario para las figuras nuevas (0: el que hay basta)

    # ------------------------------------------------------------------------------------------------- orquestación
    def ediciones(self, cambios: list[dict]) -> list[xmi.Edicion]:
        for c in cambios:
            op = operacion(c)
            if c["clase"] not in ("nodo", "contrato"):
                raise ValueError(f"{_ubic(c)}: la clase «{c['clase']}» no es del proceso")
            if c["clase"] == "contrato" and op != "agrega":
                raise NotImplementedError(f"{_ubic(c)}: en un contrato solo se agregan inputs (no «{op}»)")
        insertadas = {c["datos"]["nombre"]: c for c in cambios if c["clase"] == "nodo" and operacion(c) == "agrega"}
        inputs_nuevas: dict[str, list[dict]] = {}
        inputs_existentes: dict[str, list[tuple[dict, str]]] = {}
        for c in (x for x in cambios if x["clase"] == "contrato"):
            d, ubic = c["datos"], _ubic(c)
            i = _input_simple(d, ubic)
            if d["tarea"] in insertadas:
                if tipo_de_tarea(insertadas[d["tarea"]]["datos"]["tipo"]) != "humana":
                    raise NotImplementedError(f"{ubic}: los inputs solo se agregan al contrato de una tarea humana")
                if any(x["nombre"] == i["nombre"] for x in inputs_nuevas.get(d["tarea"], [])):
                    raise ValueError(f"{ubic}: el input «{i['nombre']}» ya se agrega a «{d['tarea']}»")
                inputs_nuevas.setdefault(d["tarea"], []).append(i)
            else:
                nodo = self._nodo(d["tarea"], ubic)
                if tipo_de_tarea(nodo["tipo"]) != "humana":
                    raise NotImplementedError(f"{ubic}: los inputs solo se agregan al contrato de una tarea humana; "
                                              f"«{nodo['nombre']}» es {nodo['tipo']}")
                inputs_existentes.setdefault(nodo["id"], []).append((i, ubic))
        for c in (x for x in cambios if x["clase"] == "nodo"):
            op = operacion(c)
            if op == "agrega":
                self._insertar(c, inputs_nuevas.get(c["datos"]["nombre"], []))
            elif op == "modifica":
                self._renombrar(c)
            else:
                self._quitar(c)
        for tarea, entradas in inputs_existentes.items():
            if tarea in self.quitadas:
                raise ValueError(f"{entradas[0][1]}: la tarea del contrato se quita en este mismo lote")
            self._agregar_inputs(tarea, entradas)
        self._ensanchar()
        return self._emitir()

    # -------------------------------------------------------------------------------------------------- operaciones
    def _insertar(self, c: dict, inputs: list[dict]) -> None:
        d, ubic = c["datos"], _ubic(c)
        tipo = tipo_de_tarea(d["tipo"])
        if tipo is None:
            raise NotImplementedError(f"{ubic}: solo se insertan tareas humanas o de servicio; «{d['tipo']}» no lo es")
        if d["transicion"] is None:
            raise NotImplementedError(f"{ubic}: insertar una tarea exige «Sobre la transición»")
        if not d["lane"]:
            raise ValueError(f"{ubic}: falta la Lane de la tarea nueva «{d['nombre']}»")
        lane = self.pool["lanes"].get(d["lane"])
        if lane is None:
            raise ValueError(f"{ubic}: la lane «{d['lane']}» no está en el pool ({', '.join(self.pool['lanes'])})")
        self._nombre_libre(d["nombre"], ubic)
        clave = transicion_del_pool(self.pool, d["transicion"], c["pool"])
        if clave is None:
            t = d["transicion"]
            raise ValueError(f"{ubic}: la transición «{t['desde']} -> {t['hacia']}» no existe en el pool (si un nodo "
                             f"tiene un nombre repetido, use su xmi:id)")
        flujo_id = self.pool["transiciones"][clave]["id"]
        self._tocar_flujo(flujo_id, ubic)
        original = self.et[flujo_id]
        desde, hacia = original.get("source"), original.get("target")

        # Modelo: el nodo y la transición nueva, con los constructores del generador.
        proceso = {"nombre": self.pool["nombre"], "transiciones": [],
                   "nodos": [{"id": "nueva", "tipo": tipo, "lane": d["lane"], "nombre": d["nombre"]}],
                   "contratos": {"nueva": {"inputs": inputs}} if inputs else {}}
        e = flujo.nodos({d["lane"]: ET.Element("elements")}, proceso, Contexto(self.ids, {}, {}, {}))["nueva"]
        f = flujo.secuencia(ET.Element("elements"), e.get(XMI_ID), hacia, self.ids)
        flujo.condicion_vacia(f, self.ids)
        e.set("incoming", flujo_id)
        e.set("outgoing", f.get(XMI_ID))
        self.atributos[(self.pos[flujo_id], "target")] = e.get(XMI_ID)
        self._cambiar_en_lista(hacia, "incoming", flujo_id, f.get(XMI_ID), ubic)
        self.tras.setdefault(self.pos[flujo_id], []).append(f)
        lane_pos = self.pos[lane["id"]]
        hermanas = hijos_de(self.nodos, lane_pos, "elements")
        if hermanas:
            self.tras.setdefault(hermanas[-1][0], []).append(e)
        else:
            self.dentro.setdefault(lane_pos, []).append(e)

        # Notación: la figura en su lane y el conector de la transición nueva; el de la original apunta a la figura.
        forma_desde, forma_hacia = self._forma(desde, ubic), self._forma(hacia, ubic)
        comp = self._compartimento(lane["id"], ubic)
        s = notacion.figura(ET.Element("children"), e, tipo, self.ids)
        notacion.limites(s, self._ubicar(comp, forma_desde, *notacion.TAMANOS[tipo]), self.ids)
        self.dentro.setdefault(comp, []).append(s)
        for v in self.vistas.get(flujo_id, []):
            self.atributos[(v, "target")] = s.get(XMI_ID)
        a = notacion.conector(ET.Element("edges"), f.get(XMI_ID), s.get(XMI_ID),
                              self.nodos[forma_hacia].attrs["xmi:id"], self.ids)
        self.dentro.setdefault(self._diagrama(forma_desde), []).append(a)

    def _renombrar(self, c: dict) -> None:
        d, ubic = c["datos"], _ubic(c)
        nodo = self._existente(c)
        self._es_tarea(nodo, ubic, "renombran")
        if d["nombre"] is None:
            raise NotImplementedError(f"{ubic}: de una tarea solo se soporta renombrarla (falta el nombre nuevo)")
        if d["tipo"] is not None and tipo_de_tarea(d["tipo"]) != tipo_de_tarea(nodo["tipo"]):
            raise NotImplementedError(f"{ubic}: cambiar el tipo de la tarea no está soportado; solo renombrarla")
        if d["lane"] is not None and d["lane"] != nodo["lane"]:
            raise NotImplementedError(f"{ubic}: cambiar la lane de la tarea no está soportado; solo renombrarla")
        self._tocar_nodo(nodo, ubic)
        if d["nombre"] == nodo["nombre"]:
            return
        self._nombre_libre(d["nombre"], ubic)
        self.atributos[(self.pos[nodo["id"]], "name")] = d["nombre"]

    def _quitar(self, c: dict) -> None:
        ubic = _ubic(c)
        nodo = self._existente(c)
        self._es_tarea(nodo, ubic, "quitan")
        self._tocar_nodo(nodo, ubic)
        e = self.et[nodo["id"]]
        if e.find("BoundaryIntermediateEvents") is not None:
            raise NotImplementedError(f"{ubic}: «{nodo['nombre']}» lleva eventos de borde; quitarla no está soportado")
        flujos = self.pool_e.findall("connections")
        entradas = [f for f in flujos if f.get("target") == nodo["id"]]
        salidas = [f for f in flujos if f.get("source") == nodo["id"]]
        if (len(entradas), len(salidas)) != (1, 1) or entradas[0] is salidas[0]:
            raise NotImplementedError(f"{ubic}: solo se quita una tarea con una entrada y una salida; "
                                      f"«{nodo['nombre']}» tiene {len(entradas)} entrada(s) y {len(salidas)} salida(s)")
        ent, sal = entradas[0], salidas[0]
        condicion_salida = sal.find("condition")
        if condicion_salida is not None and (condicion_salida.get("content") or "").strip():
            raise NotImplementedError(f"{ubic}: la salida de «{nodo['nombre']}» lleva condición; quitarla no está "
                                      f"soportado")
        ent_id, sal_id = ent.get(XMI_ID), sal.get(XMI_ID)
        previo, siguiente = ent.get("source"), sal.get("target")
        if any(f.get("source") == previo and f.get("target") == siguiente for f in flujos):
            raise NotImplementedError(f"{ubic}: ya hay una transición de «{self._nombre(previo)}» a "
                                      f"«{self._nombre(siguiente)}»; quitar «{nodo['nombre']}» la duplicaría")
        for f in (ent_id, sal_id):
            self._tocar_flujo(f, ubic)

        # La transición de entrada se queda (con su etiqueta, su condición y su tabla de decisión): solo cambia el
        # destino. La de salida se va.
        self.atributos[(self.pos[ent_id], "target")] = siguiente
        self.quitados |= {self.pos[sal_id], self.pos[nodo["id"]]}
        self.quitadas.add(nodo["id"])
        self._cambiar_en_lista(siguiente, "incoming", sal_id, ent_id, ubic)

        forma_siguiente = self.nodos[self._forma(siguiente, ubic)].attrs["xmi:id"]
        for elemento_id in (nodo["id"], sal_id):
            self.quitados.update(self.vistas.get(elemento_id, []))
        for v in self.vistas.get(ent_id, []):  # el conector de la entrada llega ahora a la figura de `siguiente`
            self.atributos[(v, "target")] = forma_siguiente
            for i, hijo in hijos_de(self.nodos, v):
                if hijo.tag == "targetAnchor":
                    self.quitados.add(i)
                elif hijo.tag == "bendpoints" and hijo.attrs.get("points", PUNTOS_SIN_RUTA) != PUNTOS_SIN_RUTA:
                    self.atributos[(i, "points")] = PUNTOS_SIN_RUTA

    def _agregar_inputs(self, tarea: str, entradas: list[tuple[dict, str]]) -> None:
        contrato = self.et[tarea].find("contract")
        if contrato is None:
            raise NotImplementedError(f"{entradas[0][1]}: la tarea no tiene contrato; crearlo no está soportado")
        nombres = {i.get("name") for i in contrato.findall("inputs")}
        restricciones = {k.get("name") for k in contrato.findall("constraints")}
        nuevos_inputs, nuevas_restricciones = [], []
        for i, ubic in entradas:
            if i["nombre"] in nombres:
                raise ValueError(f"{ubic}: el input «{i['nombre']}» ya está en el contrato de la tarea")
            nombres.add(i["nombre"])
            nuevos_inputs.append(entrada(ET.Element("contract"), i, self.ids, ubic, {}))
        for i, ubic in entradas:
            for nombre, expresion, mensaje, raiz in obligatorias([i]):
                if nombre in restricciones:
                    raise ValueError(f"{ubic}: la constraint «{nombre}» ya está en el contrato de la tarea")
                restricciones.add(nombre)
                nuevas_restricciones.append(restriccion(ET.Element("contract"), nombre, expresion, mensaje, [raiz],
                                                        self.ids))
        pos = self.pos[contrato.get(XMI_ID)]
        con_inputs, con_restricciones = hijos_de(self.nodos, pos, "inputs"), hijos_de(self.nodos, pos, "constraints")
        if not con_inputs and not con_restricciones:
            self.dentro.setdefault(pos, []).extend(nuevos_inputs + nuevas_restricciones)
            return
        if con_inputs:  # los inputs van antes que las constraints (orden de features de Contract)
            self.tras.setdefault(con_inputs[-1][0], []).extend(nuevos_inputs)
        else:
            self.antes.setdefault(con_restricciones[0][0], []).extend(nuevos_inputs)
        ultimo = con_restricciones[-1][0] if con_restricciones else con_inputs[-1][0]
        self.tras.setdefault(ultimo, []).extend(nuevas_restricciones)

    # ------------------------------------------------------------------------------------------------- resolución
    def _nodo(self, referencia: str, ubic: str) -> dict:
        """Nodo del pool por clave del mapa, nombre único o `xmi:id`."""
        _, nodo, ambiguo = nodo_del_pool(self.pool, referencia)
        if ambiguo:
            raise ValueError(f"{ubic}: hay varios nodos llamados «{referencia}»; use su xmi:id")
        if nodo is None:
            nodo = next((n for n in self.pool["nodos"].values() if n["id"] == referencia), None)
        if nodo is None:
            raise ValueError(f"{ubic}: el nodo «{referencia}» no está en el pool")
        return nodo

    def _existente(self, c: dict) -> dict:
        existente = c.get("existente") or ""
        if "/nodo/" not in existente:
            raise ValueError(f"{_ubic(c)}: Existente «{existente}» no es un nodo "
                             f"(proc/<Pool>@<v>/nodo/<nombre o xmi:id>)")
        return self._nodo(existente.split("/nodo/", 1)[1], _ubic(c))

    @staticmethod
    def _es_tarea(nodo: dict, ubic: str, verbo: str) -> None:
        if tipo_de_tarea(nodo["tipo"]) is None:
            raise NotImplementedError(f"{ubic}: solo se {verbo} tareas humanas o de servicio; «{nodo['nombre']}» es "
                                      f"{nodo['tipo']}")

    def _nombre_libre(self, nombre: str, ubic: str) -> None:
        if nombre in self.nombres:
            raise ValueError(f"{ubic}: ya hay un nodo llamado «{nombre}» en el pool")
        self.nombres.add(nombre)

    def _nombre(self, xmi_id: str) -> str:
        """`name` del elemento (o su `xmi:id` si no tiene)."""
        e = self.et.get(xmi_id)
        return (e.get("name") if e is not None else None) or xmi_id

    def _tocar_flujo(self, flujo_id: str, ubic: str) -> None:
        if flujo_id in self.flujos_tocados:
            f = self.et[flujo_id]
            raise ValueError(f"{ubic}: otro cambio de este lote ya toca la transición «{self._nombre(f.get('source'))} "
                             f"-> {self._nombre(f.get('target'))}» ({flujo_id})")
        self.flujos_tocados.add(flujo_id)

    def _tocar_nodo(self, nodo: dict, ubic: str) -> None:
        if nodo["id"] in self.nodos_tocados:
            raise ValueError(f"{ubic}: otro cambio de este lote ya renombra o quita «{nodo['nombre']}»")
        self.nodos_tocados.add(nodo["id"])

    def _cambiar_en_lista(self, xmi_id: str, atributo: str, viejo: str, nuevo: str, ubic: str) -> None:
        """Sustituye `viejo` por `nuevo` en la lista `incoming`/`outgoing` del nodo, en la misma posición."""
        pos = self.pos[xmi_id]
        lista = (self.atributos.get((pos, atributo), self.nodos[pos].attrs.get(atributo)) or "").split()
        if viejo not in lista:
            raise ValueError(f"{ubic}: el {atributo} de «{self.nodos[pos].attrs.get('name', xmi_id)}» no incluye la "
                             f"transición {viejo}; el fichero no es coherente")
        lista[lista.index(viejo)] = nuevo
        self.atributos[(pos, atributo)] = " ".join(lista)

    # --------------------------------------------------------------------------------------------------- notación
    def _forma(self, elemento_id: str, ubic: str) -> int:
        pos = next((v for v in self.vistas.get(elemento_id, []) if self.nodos[v].attrs.get("xmi:type") == _SHAPE), None)
        if pos is None:
            raise ValueError(f"{ubic}: el nodo «{self._nombre(elemento_id)}» no tiene figura en el diagrama")
        return pos

    def _compartimento(self, lane_id: str, ubic: str) -> int:
        compartimento = vista("LaneLaneCompartment")
        for v in self.vistas.get(lane_id, []):
            hallado = [i for i, n in hijos_de(self.nodos, v) if n.attrs.get("type") == compartimento]
            if hallado:
                return hallado[0]
        raise ValueError(f"{ubic}: la lane «{self._nombre(lane_id)}» no tiene vista en el diagrama")

    def _diagrama(self, pos: int) -> int:
        while self.nodos[pos].tag != "notation:Diagram":
            pos = self.nodos[pos].padre
        return pos

    def _bounds(self, pos: int) -> tuple[int | None, Caja]:
        """(posición del `Bounds` de la vista, su caja); (None, ceros) si no tiene."""
        for i, n in hijos_de(self.nodos, pos, "layoutConstraint"):
            if n.attrs.get("xmi:type") == "notation:Bounds":
                return i, tuple(int(n.attrs.get(k, "0")) for k in ("x", "y", "width", "height"))
        return None, (0, 0, 0, 0)

    def _caja(self, pos: int) -> tuple[Caja, int]:
        """Caja de la figura relativa a su lane (una figura de borde va relativa a su anfitrión) y posición del
        compartimento de la lane."""
        x = y = 0
        w = h = 0
        p = pos
        while self.nodos[p].attrs.get("xmi:type") == _SHAPE:
            bx, by, bw, bh = self._bounds(p)[1]
            x, y = x + bx, y + by
            if p == pos:
                w, h = bw, bh
            p = self.nodos[p].padre
        return (x, y, w, h), p

    def _ocupadas(self, comp: int) -> list[Caja]:
        if self._cajas is None:
            self._cajas = {}
            for i, n in enumerate(self.nodos):
                if n.attrs.get("xmi:type") == _SHAPE:
                    caja, de = self._caja(i)
                    self._cajas.setdefault(de, []).append(caja)
        return self._cajas.setdefault(comp, [])

    def _ubicar(self, comp: int, forma_desde: int, ancho: int, alto: int) -> Caja:
        """Caja de una figura nueva en la lane del compartimento `comp`: a la derecha de la de `desde` (a su altura si
        está en la misma lane; si no, en la primera fila) y, si choca con alguna, a la derecha de lo que choca."""
        (dx, dy, dw, dh), comp_desde = self._caja(forma_desde)
        lane = self.nodos[comp].padre
        _, (_, _, ancho_lane, alto_lane) = self._bounds(lane)
        x = dx + dw + SEPARACION
        if comp_desde == comp:
            y = dy + dh // 2 - alto // 2
        else:
            y = notacion.MARGEN_Y + (notacion.FILA - alto) // 2
        if alto_lane:
            y = min(y, alto_lane - alto)
        y = max(y, 0)
        ocupadas = self._ocupadas(comp)
        while choques := [c for c in ocupadas if _se_tocan((x, y, ancho, alto), c)]:
            x = max(cx + cw for cx, _, cw, _ in choques) + SEPARACION
        ocupadas.append((x, y, ancho, alto))
        if ancho_lane and x + ancho + notacion.MARGEN_X > ancho_lane:
            self.ancho = max(self.ancho, x + ancho + notacion.MARGEN_X)
        return x, y, ancho, alto

    def _ensanchar(self) -> None:
        """Si una figura nueva se sale de su lane, todas las lanes del pool pasan a ese ancho y el pool crece igual."""
        if not self.ancho:
            return
        tipo_lane = vista("Lane")
        lanes = [v for lane in self.pool["lanes"].values() for v in self.vistas.get(lane["id"], [])
                 if self.nodos[v].attrs.get("type") == tipo_lane]
        maximo = max(self._bounds(v)[1][2] for v in lanes)
        for v in lanes:
            pos, caja = self._bounds(v)
            if caja[2] < self.ancho:
                self.atributos[(pos, "width")] = str(self.ancho)
        for v in self.vistas.get(self.pool_e.get(XMI_ID), []):
            if self.nodos[v].attrs.get("type") == vista("Pool"):
                pos, caja = self._bounds(v)
                if pos is not None:
                    self.atributos[(pos, "width")] = str(caja[2] + self.ancho - maximo)

    # ---------------------------------------------------------------------------------------------------- emisión
    def _sangria(self, pos: int) -> str:
        """Blancos que preceden al nodo en su línea."""
        inicio = k = self.nodos[pos].inicio
        while k > 0 and self.texto[k - 1] in " \t":
            k -= 1
        return self.texto[k:inicio]

    def _fragmento(self, e: ET.Element, sangria: str) -> str:
        return xmi.fragmento(e, self.prefijos, sangria, self.salto)

    def _emitir(self) -> list[xmi.Edicion]:
        out = [xmi.poner_atributo(self.texto, self.nodos[p], atributo, valor)
               for (p, atributo), valor in self.atributos.items()]
        out += [xmi.quitar(self.nodos[p], self.texto) for p in sorted(self.quitados)]
        for p, nuevos in self.tras.items():
            s = self._sangria(p)
            out.append(xmi.Edicion(self.nodos[p].fin, self.nodos[p].fin,
                                   "".join(f"{self.salto}{s}{self._fragmento(e, s)}" for e in nuevos)))
        for p, nuevos in self.antes.items():
            s = self._sangria(p)
            out.append(xmi.Edicion(self.nodos[p].inicio, self.nodos[p].inicio,
                                   "".join(f"{self._fragmento(e, s)}{self.salto}{s}" for e in nuevos)))
        for p, nuevos in self.dentro.items():
            s = xmi.sangria_hijo(self.texto, self.nodos[p])
            out.append(xmi.insertar_hijos(self.texto, self.nodos[p], [self._fragmento(e, s) for e in nuevos]))
        return out
