"""Journey Newman generado desde los `caminos` de la spec: una colección Postman v2.1 que se corre contra el bundle.

Estructura: carpeta «preparación» (login admin, cada usuario de la organización instalado y ya en el perfil `User`
—lo mapea el paso posterior al despliegue `tools/arnes.sh perfiles`, que `run-journey.sh` corre antes de Newman; aquí
solo se comprueba—, logout) y una carpeta por camino. Por paso: login del usuario; «(instanciacion)» busca el proceso
por nombre **y** versión e instancia con el payload; una tarea humana se busca por su nombre en el caso raíz
(`rootCaseId`, el `rootProcessInstanceId` de la API Java: así aparecen también las del subproceso), se asigna al
usuario y se ejecuta con el payload; «(esperar <timer>)» sondea hasta que la tarea anfitriona del timer, ya vista,
desaparece del caso (máx. 60 s). Antes de asignar, la tarea tiene que estar entre las pendientes del usuario
(`f=user_id`): así el journey mide el actor mapping y no solo que la API deje asignar. Al final: caso archivado, el
fin esperado (y ningún otro fin del pool) deducido de los flow nodes archivados del caso, y cada atributo esperado
leído del objeto BDM **de este caso** (contexto del caso archivado → `<bv>_ref.storageId` →
`API/bdm/businessData/<clase>/<storageId>`), como el journey del lab, que evita leer datos de otro caso.

Los eventos no se archivan (runtime 11.1.0: `DefaultArchivingStrategy` de `bonita-server-11.1.0.jar` solo archiva
tareas, compuertas, call activities, subprocesos, conectores, datos y el caso; comprobado en el journey de Task 13:
`archivedFlowNode` nunca devuelve un END_EVENT). Por eso el fin se deduce de lo que lo precede (`evidencia_de_fin`):
la fuente de una transición al fin terminada (`completed`) y, si es una compuerta exclusiva, ninguna de sus otras
salidas observables ejecutada; si la fuente es un timer de borde interruptor, su tarea anfitriona `aborted`.
`archivedFlowNode` se filtra por `caseId` (con `rootCaseId` el runtime responde 500 «Can't find value corresponding
to rootCaseId»); su `caseId` es el del caso raíz (los nodos del subproceso aparecen con el `caseId` del padre), así
que además se filtra por `processId` (la definición instanciada): un nodo del subproceso con el mismo nombre no cuenta.
Los ids de nodo son únicos por pool: cada paso se resuelve con `nodo_de_paso` (pool principal primero).

R-15 (contrato del Plan 5, §2.14): un `{"$archivo": nombre}` del payload se sube antes (`_archivos`: multipart
escrito en la colección a `API/formFileUpload`) y su sitio lo ocupa `{filename, tempPath, contentType}`; «(no ve
<tarea>)» espera la tarea lista y comprueba que no está entre las pendientes del usuario; «(denegado MÉTODO ruta)»
comprueba el código (los `{bv}` de la ruta salen del contexto del caso vivo; con «[subscription]» y el bundle de
desarrollo Community, `edicion_desarrollo`, el paso se omite con un aviso); los correos esperados se comparan con el SMTP de prueba
(`herramientas/smtp_prueba.py`, variable `smtpUrl`, vaciado al empezar el camino) y las consultas esperadas se leen por
`API/bdm/businessData/<clase>?q=…` al final. Sin nada de esto, la colección es la de siempre (vacaciones no cambia).

Las variables se leen con `pm.variables.get` (respeta `--env-var`) y se escriben con `pm.collectionVariables.set`;
`baseUrl` se sobreescribe con `--env-var baseUrl=…`. Los sondeos usan `postman.setNextRequest(<su nombre>)`: los
nombres de las peticiones son únicos en la colección."""
from __future__ import annotations

import json
import re
from urllib.parse import quote

from generadores.escribir import journey_filas as filas
from generadores.escribir.organizacion import candidato

SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
BASE_URL = "http://localhost:8096/bonita"
INSTANCIACION = "(instanciacion)"
ESPERAR = "(esperar)"
NO_VE = "(no ve)"
DENEGADO = "(denegado)"
ARCHIVO = "$archivo"
SMTP_URL = "http://127.0.0.1:8025"  # HTTP del SMTP de prueba (herramientas/smtp_prueba.py); --env-var smtpUrl=…
LIMITE = "----trycoreJourneyLimite"
# contentType por extensión (tabla fija: `mimetypes` depende de la máquina y el journey tiene que ser determinista).
TIPOS_ARCHIVO = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                 "gif": "image/gif", "txt": "text/plain", "csv": "text/csv", "json": "application/json",
                 "xml": "application/xml", "zip": "application/zip", "doc": "application/msword",
                 "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "xls": "application/vnd.ms-excel",
                 "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
# Límite de cada sondeo (tarea lista, timer, caso archivado) y pausa entre intentos.
LIMITE_MS = 60000
PAUSA_MS = 2000


def _j(valor) -> str:
    """Literal JavaScript (JSON) de un valor de Python."""
    return json.dumps(valor, ensure_ascii=False)


def _peticion(nombre: str, metodo: str, ruta: str, query: list[tuple[str, str]] | None = None, *,
              cuerpo: dict | None = None, form: list[tuple[str, str]] | None = None, token: bool = True,
              test: list[str], crudo: str | None = None, tipo: str = "application/json",
              base: str = "{{baseUrl}}") -> dict:
    """Petición Postman. `crudo`: cuerpo ya serializado (con huecos `{{…}}` sin comillas o multipart) de tipo `tipo`;
    `base`: variable de la raíz (`{{smtpUrl}}` para el SMTP de prueba)."""
    query = query or []
    raw = base + "/" + ruta + ("?" + "&".join(f"{k}={v}" for k, v in query) if query else "")
    cabeceras = [{"key": "X-Bonita-API-Token", "value": "{{token}}"}] if token else []
    request: dict = {"method": metodo, "header": cabeceras,
                     "url": {"raw": raw, "host": [base], "path": ruta.split("/"),
                             "query": [{"key": k, "value": v} for k, v in query]}}
    if form is not None:
        cabeceras.append({"key": "Content-Type", "value": "application/x-www-form-urlencoded"})
        request["body"] = {"mode": "urlencoded", "urlencoded": [{"key": k, "value": v} for k, v in form]}
    elif crudo is not None:
        cabeceras.append({"key": "Content-Type", "value": tipo})
        request["body"] = {"mode": "raw", "raw": crudo}
    elif cuerpo is not None:
        cabeceras.append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {"mode": "raw", "raw": json.dumps(cuerpo, ensure_ascii=False)}
    return {"name": nombre, "request": request, "event": [{"listen": "test", "script": {"exec": test}}]}


def _login(nombre: str, usuario: str, clave: str) -> dict:
    return _peticion(nombre, "POST", "loginservice", form=[("username", usuario), ("password", clave),
                                                            ("redirect", "false")], token=False, test=[
        f"pm.test({_j('login 204 de ' + usuario)}, () => pm.response.to.have.status(204));",
        'pm.collectionVariables.set("token", pm.cookies.get("X-Bonita-API-Token"));',
    ])


def _logout(nombre: str) -> dict:
    return _peticion(nombre, "GET", "logoutservice", [("redirect", "false")], test=[
        'pm.test("logout", () => pm.expect([200, 204]).to.include(pm.response.code));',
    ])


def _sondeo(nombre: str, listo: str) -> list[str]:
    """Cabecera de un script de sondeo: repite la petición cada PAUSA_MS hasta que `listo` (expresión JS) sea
    verdadera o pasen LIMITE_MS desde el primer intento; después sigue con las aserciones."""
    return [
        'const inicio = Number(pm.variables.get("sondeoInicio")) || Date.now();',
        'pm.collectionVariables.set("sondeoInicio", String(inicio));',
        f"const listo = {listo};",
        f"if (!listo && Date.now() - inicio < {LIMITE_MS}) {{ setTimeout(() => {{}}, {PAUSA_MS}); "
        f"postman.setNextRequest({_j(nombre)}); return; }}",
        'pm.collectionVariables.set("sondeoInicio", "");',
        "const esperaMs = Date.now() - inicio;",
    ]


_LISTA = "const r = pm.response.code === 200 ? pm.response.json() : [];"
_CASO = 'const caso = String(pm.variables.get("caseId"));'


def nodo_de_paso(procesos: list[dict], id_: str | None, tipos: set[str], que: str) -> tuple[dict, dict]:
    """`(pool, nodo)` del paso de un camino: los ids de nodo son únicos por pool, no en la spec. Primero el pool
    principal (`procesos[0]`); si no está ahí, el único otro pool que tiene un nodo `id_` de uno de los `tipos`.
    ValueError si no está en ninguno o si está en varios (como `_pool_de_tarea` de la spec). La usan el validador
    de la spec y el journey."""
    def en(p: dict) -> dict | None:
        return next((n for n in p.get("nodos", []) if n.get("id") == id_ and n.get("tipo") in tipos), None)

    if procesos and (n := en(procesos[0])) is not None:
        return procesos[0], n
    candidatos = [(p, n) for p in procesos[1:] if (n := en(p)) is not None]
    if len(candidatos) == 1:
        return candidatos[0]
    if not candidatos:
        raise ValueError(f"«{id_}» no es {que} de ningún pool")
    raise ValueError(f"«{id_}» no está en el pool principal y está en varios pools "
                     f"({', '.join(p.get('nombre', '?') for p, _ in candidatos)}); cambia el id en uno de ellos")


def _preparacion(spec: dict) -> dict:
    usuarios = [u["nombre"] for u in spec["organizacion"]["usuarios"]]
    item = [
        _login("0. login admin", "{{adminUsuario}}", "{{adminClave}}"),
        _peticion("0. id del perfil User", "GET", "API/portal/profile", [("f", "name=User"), ("p", "0"), ("c", "1")],
                  test=[
            "const p = pm.response.json();",
            'pm.test("perfil User existe", () => pm.expect(p.length).to.eql(1));',
            'pm.collectionVariables.set("profileId", p[0].id);',
        ]),
    ]
    for u in usuarios:
        item.append(_peticion(f"0. id de {u}", "GET", "API/identity/user",
                              [("f", f"userName={u}"), ("p", "0"), ("c", "1")], test=[
            "const u = pm.response.json();",
            f"pm.test({_j('el archive no se instaló: falta el usuario ' + u + ' de la organización')}, "
            "() => pm.expect(u.length).to.eql(1));",
            f"pm.collectionVariables.set({_j('userId_' + u)}, u[0].id);",
        ]))
    ids = ", ".join(f"pm.variables.get({_j('userId_' + u)})" for u in usuarios)
    item.append(_peticion("0. usuarios en el perfil User", "GET", "API/portal/profileMember",
                          [("f", "profile_id={{profileId}}"), ("f", "member_type=user"), ("p", "0"), ("c", "1000")],
                          test=[
        "const miembros = pm.response.json().map((m) => String(m.user_id));",
        f"const faltan = [{ids}].map(String).filter((id) => !miembros.includes(id));",
        f"pm.test({_j('cada usuario en el perfil User (lo mapea tools/arnes.sh perfiles tras el despliegue)')}, "
        "() => pm.expect(faltan).to.eql([]));",
    ]))
    item.append(_logout("0. logout admin"))
    return {"name": "preparación", "item": item}


def _instanciar(c: str, i: int, proceso: dict, paso: dict) -> list[dict]:
    nombre, version, u = proceso["nombre"], proceso["version"], paso["usuario"]
    subidas, cuerpo = _archivos(c, i, paso["payload"])
    # D-75: la búsqueda va filtrada por el usuario (`f=user_id`), como la hace un usuario real: con el dynamic check
    # activo, `GET API/bpm/process` sin ese filtro da 403 a quien no es administrador.
    return [*subidas,
        _peticion(f"[{c}] {i}. proceso {nombre} {version}", "GET", "API/bpm/process",
                  [("f", f"name={nombre}"), ("f", f"version={version}"), ("f", f"user_id={{{{userId_{u}}}}}"),
                   ("p", "0"), ("c", "10")], test=[
            "const p = pm.response.json();",
            f"pm.test({_j('no hay un proceso ' + nombre + ' ' + version + ' que ' + u + ' pueda iniciar (el archive no se instaló o el usuario no es candidato del iniciador)')}, "
            "() => pm.expect(p.length).to.eql(1));",
            f"pm.test(\"versión esperada\", () => pm.expect(p[0].version).to.eql({_j(version)}));",
            'pm.test("habilitado", () => pm.expect(p[0].activationState).to.eql("ENABLED"));',
            'pm.collectionVariables.set("processId", p[0].id);',
        ]),
        _peticion(f"[{c}] {i}. instanciar como {paso['usuario']}", "POST",
                  "API/bpm/process/{{processId}}/instantiation", **cuerpo, test=[
            'pm.test("instanciado (200)", () => pm.response.to.have.status(200));',
            'pm.collectionVariables.set("caseId", String(pm.response.json().caseId));',
        ]),
    ]


def _filtro_usuario(usuario: str | None) -> list[tuple[str, str]]:
    """`f=user_id` del usuario de la sesión (D-75): con el dynamic check activo, `GET API/bpm/humanTask` y
    `GET API/bpm/process` sin filtro de usuario dan 403 a quien no es administrador."""
    return [("f", f"user_id={{{{userId_{usuario}}}}}")] if usuario else []


def _buscar_tarea(c: str, i: int, tarea: dict, usuario: str | None = None) -> dict:
    """La tarea lista en el caso raíz; con `usuario`, entre las pendientes de ese usuario (como la busca él, D-75).
    Sin `usuario` (paso «(no ve)»), entre todas las del caso."""
    nombre = f"[{c}] {i}. tarea {tarea['id']}"
    return _peticion(nombre, "GET", "API/bpm/humanTask",
                     [("f", "rootCaseId={{caseId}}"), *_filtro_usuario(usuario), ("p", "0"), ("c", "50")],
                     test=[
        _LISTA, _CASO,
        f"const t = r.filter(x => x.name === {_j(tarea['nombre'])} && String(x.rootCaseId) === caso "
        '&& x.state === "ready");',
        *_sondeo(nombre, "t.length > 0"),
        'pm.test("humanTask 200", () => pm.response.to.have.status(200));',
        f"pm.test({_j('tarea «' + tarea['nombre'] + '» (' + tarea['id'] + ') lista en el caso raíz')}, "
        "() => pm.expect(t.length, \"tareas del caso: \" + r.map(x => x.name + \"/\" + x.state).join(\", \"))"
        ".to.eql(1));",
        'if (t.length) pm.collectionVariables.set("taskId", t[0].id);',
    ])


def _ejecutar(c: str, i: int, tarea: dict, paso: dict, proceso: dict | None = None, paquete: str = "") -> list[dict]:
    u = paso["usuario"]
    # Filas del caso nombradas en el payload (`{bv}`, `{bv[n]}`, `{bv.relacion[n]}`, `{caso}`; journey_filas.py): se
    # resuelven con la tarea ya asignada, antes de subir archivos y ejecutar. Sin ninguna, nada cambia.
    bvs = {b["nombre"]: b["objeto"] for b in (proceso or {}).get("business_variables", [])}
    refs = filas.referencias(paso["payload"], set(bvs) | {filas.CASO})
    payload = filas.sustituir(paso["payload"], i, refs) if refs else paso["payload"]
    resolver = filas.peticiones(c, i, refs, {b: f"{paquete}.{o}" for b, o in bvs.items()}, _peticion, _j)
    subidas, cuerpo = _archivos(c, i, payload)
    return [
        _buscar_tarea(c, i, tarea, u),
        _peticion(f"[{c}] {i}. {tarea['id']} pendiente para {u}", "GET", "API/bpm/humanTask",
                  [("f", "rootCaseId={{caseId}}"), ("f", f"user_id={{{{userId_{u}}}}}"), ("p", "0"), ("c", "50")], test=[
            _LISTA, _CASO,
            'const id = String(pm.variables.get("taskId"));',
            f"pm.test({_j('«' + tarea['nombre'] + '» es una tarea pendiente de ' + u + ' (actor mapping)')}, "
            "() => pm.expect(r.some(x => String(x.id) === id && String(x.rootCaseId) === caso)).to.be.true);",
        ]),
        _peticion(f"[{c}] {i}. asignar {tarea['id']} a {paso['usuario']}", "PUT", "API/bpm/humanTask/{{taskId}}",
                  cuerpo={"assigned_id": f"{{{{userId_{paso['usuario']}}}}}"}, test=[
            'pm.test("asignada", () => pm.expect([200, 204]).to.include(pm.response.code));',
        ]),
        *resolver,
        *subidas,
        _peticion(f"[{c}] {i}. ejecutar {tarea['id']}", "POST", "API/bpm/userTask/{{taskId}}/execution",
                  **cuerpo, test=[
            f"pm.test({_j('ejecutada ' + tarea['id'] + ' (204)')}, () => pm.response.to.have.status(204));",
        ]),
    ]


def _esperar(c: str, i: int, timer: dict, anfitriona: dict, usuario: str | None = None) -> dict:
    """Sondea hasta que la tarea anfitriona, ya vista, desaparece del caso. Con `usuario` (un candidato de la
    anfitriona), entre sus tareas pendientes (`f=user_id`, D-75)."""
    nombre = f"[{c}] {i}. esperar {timer['id']}"
    return _peticion(nombre, "GET", "API/bpm/humanTask",
                     [("f", "rootCaseId={{caseId}}"), *_filtro_usuario(usuario), ("p", "0"), ("c", "50")],
                     test=[
        _LISTA, _CASO,
        f"const t = r.filter(x => x.name === {_j(anfitriona['nombre'])} && String(x.rootCaseId) === caso);",
        # «Vista» primero: justo tras instanciar la tarea puede no existir todavía y no contaría como interrumpida.
        # Un HTTP distinto de 200 (401, 500…) no dice nada de la tarea: ni la da por vista ni por desaparecida.
        "const ok = pm.response.code === 200;",
        'const vista = pm.variables.get("anfitrionaVista") === "1" || (ok && t.length > 0);',
        'pm.collectionVariables.set("anfitrionaVista", vista ? "1" : "");',
        *_sondeo(nombre, "ok && vista && t.length === 0"),
        'pm.collectionVariables.set("anfitrionaVista", "");',
        f"console.log({_j('espera de ' + timer['id'] + ': ')} + esperaMs + \" ms\");",
        'pm.test("humanTask 200", () => pm.expect(pm.response.code).to.eql(200));',
        f"pm.test({_j('el timer ' + timer['id'] + ' interrumpió «' + anfitriona['nombre'] + '» en ≤ 60 s')}, "
        "() => pm.expect(ok && vista && t.length === 0, !ok ? \"HTTP \" + pm.response.code : vista ? "
        "\"la tarea sigue en el caso\" : \"la tarea anfitriona nunca apareció\").to.be.true);",
    ])


def completar_payload(payload, inputs: list[dict]):
    """El payload con `null` en cada input del contrato que no trae (D-52: el motor exige todos, también los
    opcionales), recursivo en los hijos de un COMPLEX y en cada elemento de un COMPLEX múltiple. Conserva el orden y lo
    que el payload trae (incluidas claves que no son inputs: las valida `generar`); los que faltan van al final, en el
    orden del contrato. Un payload completo queda idéntico."""
    if not isinstance(payload, dict) or es_archivo(payload):
        return payload
    out = dict(payload)
    for i in inputs:
        n = i.get("nombre")
        if n not in out:
            out[n] = None
        elif i.get("tipo") == "COMPLEX" and i.get("hijos"):
            v = out[n]
            out[n] = ([completar_payload(x, i["hijos"]) for x in v] if isinstance(v, list)
                      else completar_payload(v, i["hijos"]))
    return out


def _con_contrato(paso: dict, proceso: dict, contexto: str) -> dict:
    contrato = (proceso.get("contratos") or {}).get(contexto)
    if not contrato or not contrato.get("inputs") or not isinstance(paso.get("payload"), dict):
        return paso
    return {**paso, "payload": completar_payload(paso["payload"], contrato["inputs"])}


def es_archivo(v) -> bool:
    return isinstance(v, dict) and ARCHIVO in v


def tipo_de_archivo(nombre: str) -> str:
    ext = nombre.rsplit(".", 1)[1].lower() if "." in nombre else ""
    return TIPOS_ARCHIVO.get(ext, "application/octet-stream")


def _archivos(c: str, i: int, payload: dict | None) -> tuple[list[dict], dict]:
    """Subidas de los `{"$archivo": nombre}` del payload (en orden de aparición) y los argumentos del cuerpo de la
    petición que lo envía. Sin archivos, el cuerpo es el payload tal cual (el journey de hoy no cambia). Con archivos,
    cada uno se sube por `API/formFileUpload` y su sitio en el JSON lo ocupa, sin comillas, la variable
    `{{archivo_<i>_<k>}}`, que la subida deja con `{filename, tempPath, contentType}` serializado."""
    nombres: list[str] = []

    def cambiar(v):
        if es_archivo(v):
            nombres.append(v[ARCHIVO])
            return f"{{{{archivo_{i}_{len(nombres)}}}}}"
        if isinstance(v, dict):
            return {k: cambiar(x) for k, x in v.items()}
        if isinstance(v, list):
            return [cambiar(x) for x in v]
        return v

    cambiado = cambiar(payload or {})
    if not nombres:
        return [], {"cuerpo": payload or {}}
    crudo = json.dumps(cambiado, ensure_ascii=False)
    for k in range(1, len(nombres) + 1):
        crudo = crudo.replace(f'"{{{{archivo_{i}_{k}}}}}"', f"{{{{archivo_{i}_{k}}}}}")
    return [_subir(c, i, k, n) for k, n in enumerate(nombres, 1)], {"crudo": crudo}


def _subir(c: str, i: int, k: int, nombre: str) -> dict:
    """POST multipart a `API/formFileUpload` con un fichero sintético (texto) llamado `nombre`; el cuerpo multipart va
    escrito en la colección (sin ficheros en disco ni `--working-dir`). La respuesta da el `tempPath` (JSON; si es texto,
    el texto entero) que el contrato recibe como `{filename, tempPath, contentType}`."""
    tipo = tipo_de_archivo(nombre)
    contenido = (f"%PDF-1.4\n% archivo sintético del journey: {nombre}\n%%EOF" if tipo == "application/pdf"
                 else f"archivo sintético del journey: {nombre}")
    crudo = (f"--{LIMITE}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nombre}\"\r\n"
             f"Content-Type: {tipo}\r\n\r\n{contenido}\r\n--{LIMITE}--\r\n")
    variable = f"archivo_{i}_{k}"
    return _peticion(f"[{c}] {i}. subir {nombre} ({k})", "POST", "API/formFileUpload", crudo=crudo,
                     tipo=f"multipart/form-data; boundary={LIMITE}", test=[
        f"pm.test({_j('formFileUpload 200 (' + nombre + ')')}, () => pm.response.to.have.status(200));",
        "let r = null;",
        "try { r = pm.response.json(); } catch (e) { r = null; }",
        "const tempPath = r && typeof r === \"object\" ? r.tempPath : pm.response.text().trim();",
        f"pm.test({_j('tempPath de ' + nombre)}, () => pm.expect(Boolean(tempPath), pm.response.text()).to.be.true);",
        f"pm.collectionVariables.set({_j(variable)}, JSON.stringify({{filename: {_j(nombre)}, tempPath: tempPath, "
        f"contentType: {_j(tipo)}}}));",
    ])


def _no_ve(c: str, i: int, tarea: dict, paso: dict) -> list[dict]:
    """La tarea ya está lista en el caso (mismo sondeo que antes de ejecutarla) y no está entre las pendientes de
    `usuario` (`f=user_id`): mide el actor mapping y el actor filter en negativo."""
    u = paso["usuario"]
    return [
        _buscar_tarea(c, i, tarea),
        _peticion(f"[{c}] {i}. {tarea['id']} no pendiente para {u}", "GET", "API/bpm/humanTask",
                  [("f", "rootCaseId={{caseId}}"), ("f", f"user_id={{{{userId_{u}}}}}"), ("p", "0"), ("c", "50")], test=[
            'pm.test("humanTask 200", () => pm.response.to.have.status(200));',
            _LISTA, _CASO,
            'const id = String(pm.variables.get("taskId"));',
            f"pm.test({_j('«' + tarea['nombre'] + '» no es una tarea pendiente de ' + u)}, "
            "() => pm.expect(r.some(x => String(x.id) === id && String(x.rootCaseId) === caso), "
            "\"pendientes: \" + r.map(x => x.name).join(\", \")).to.eql(false));",
        ]),
    ]


def _huecos_bv(texto: str) -> list[str]:
    """Business variables nombradas como `{bv}` en un texto (en orden, sin repetir; `{caso}` no cuenta)."""
    return list(dict.fromkeys(h for h in re.findall(r"\{(\w+)\}", texto) if h != "caso"))


def _con_huecos(texto: str) -> str:
    """`{caso}` → `{{caseId}}`; `{bv}` → `{{bv_storageId}}` (variables de la colección)."""
    return re.sub(r"\{(\w+)\}", lambda m: "{{caseId}}" if m.group(1) == "caso" else f"{{{{{m.group(1)}_storageId}}}}",
                  texto)


def _guardar_storage_ids(bvs: list[str]) -> list[str]:
    return [l for bv in bvs for l in (
        f"pm.test({_j('el caso tiene su referencia ' + bv + '_ref')}, "
        f"() => pm.expect(ctx[{_j(bv + '_ref')}] && ctx[{_j(bv + '_ref')}].storageId).to.be.ok);",
        f"pm.collectionVariables.set({_j(bv + '_storageId')}, String(ctx[{_j(bv + '_ref')}].storageId_string "
        f"|| ctx[{_j(bv + '_ref')}].storageId));",
    )]


def _denegado(c: str, i: int, paso: dict, lector: str, clave: str, edicion: str | None) -> list[dict]:
    """La petición del usuario devuelve uno de los códigos aceptados. Los `{bv}` de la ruta salen del contexto del caso
    vivo, leído por el lector del camino (el que instancia). Con «[subscription]» y un bundle de desarrollo Community
    (`edicion_desarrollo`, lo que corre el journey local aunque el destino sea Subscription; revisión final, I-7), el
    paso se omite con un aviso (`pm.execution.skipRequest`; si el Newman no lo tiene, una prueba omitida)."""
    metodo, ruta = paso["peticion"]["metodo"], paso["peticion"]["ruta"]
    u = paso["usuario"]
    titulo = f"(denegado {metodo} {ruta})"
    if paso.get("edicion") == "subscription" and edicion == "community":
        aviso = f"AVISO: {titulo} de {u} se omite: es de Subscription y el bundle de desarrollo es Community"
        p = _peticion(f"[{c}] {i}. {titulo} omitido en Community", "GET", "API/system/session/unusedId", token=False,
                      test=[f"pm.test.skip({_j(aviso)}, () => {{}});"])
        p["event"].insert(0, {"listen": "prerequest", "script": {"exec": [
            f"console.log({_j(aviso)});",
            "if (pm.execution && pm.execution.skipRequest) pm.execution.skipRequest();",
        ]}})
        return [p]
    out: list[dict] = []
    bvs = _huecos_bv(ruta)
    if bvs:
        out += [_login(f"[{c}] {i}. login {lector} (contexto del caso)", lector, clave),
                _peticion(f"[{c}] {i}. contexto del caso", "GET", "API/bpm/case/{{caseId}}/context", test=[
                    'pm.test("contexto del caso 200", () => pm.response.to.have.status(200));',
                    "const ctx = pm.response.json();", *_guardar_storage_ids(bvs)]),
                _logout(f"[{c}] {i}. logout {lector} (contexto del caso)")]
    ruta_pm, _, qs = _con_huecos(ruta).partition("?")
    query = [tuple(q.split("=", 1)) if "=" in q else (q, "") for q in qs.split("&") if q] if qs else None
    cuerpo = {} if metodo in ("POST", "PUT", "PATCH") else None
    codigos = paso["codigos"]
    out += [_login(f"[{c}] {i}. login {u}", u, clave),
            _peticion(f"[{c}] {i}. {titulo} de {u}", metodo, ruta_pm, query, cuerpo=cuerpo, test=[
                f"pm.test({_j(titulo + ' de ' + u + ' responde ' + ' o '.join(map(str, codigos)))}, "
                f"() => pm.expect({_j(codigos)}, \"HTTP \" + pm.response.code).to.include(pm.response.code));",
            ]),
            _logout(f"[{c}] {i}. logout {u}")]
    return out


def _vaciar_smtp(c: str) -> dict:
    return _peticion(f"[{c}] 0. vaciar el SMTP de prueba", "DELETE", "mensajes", token=False, base="{{smtpUrl}}",
                     test=['pm.test("SMTP de prueba vaciado (¿está arrancado? tools/run-journey.sh lo levanta)", '
                           '() => pm.expect([200, 204]).to.include(pm.response.code));'])


def _correos(c: str, i: int, correos: list[dict]) -> dict:
    """Mensajes del SMTP de prueba tras el caso: tantos como filas y cada fila casa con uno distinto (asunto contiene;
    Para y CC como conjuntos, sin mayúsculas). Sin filas («ninguno»): cero mensajes."""
    nombre = f"[{c}] {i}. correos recibidos"
    n = len(correos)
    lineas = ['const r = pm.response.code === 200 ? pm.response.json() : [];']
    if n:
        lineas += _sondeo(nombre, f"r.length >= {n}")
    lineas += [
        'pm.test("SMTP de prueba 200", () => pm.response.to.have.status(200));',
        f"const ESPERADOS = {_j(correos)};",
        "const norm = (xs) => (xs || []).map(x => String(x).toLowerCase()).sort();",
        "const igual = (a, b) => JSON.stringify(norm(a)) === JSON.stringify(norm(b));",
        "const casa = (e, m) => String(m.asunto).includes(e.asunto) && igual(e.para, m.para) && igual(e.cc, m.cc);",
        "const asignar = (k, libres) => k === ESPERADOS.length || libres.some((m, j) => casa(ESPERADOS[k], m) "
        "&& asignar(k + 1, libres.filter((_, x) => x !== j)));",
        "const recibidos = r.map(m => \"«\" + m.asunto + \"» → \" + norm(m.para).join(\", \") + "
        "(m.cc && m.cc.length ? \" cc \" + norm(m.cc).join(\", \") : \"\")).join(\"; \") || \"ninguno\";",
        f"pm.test({_j(str(n) + ' correos recibidos')}, () => pm.expect(r.length, \"recibidos: \" + recibidos)"
        f".to.eql({n}));",
        *[f"pm.test({_j('correo «' + e['asunto'] + '» para ' + ', '.join(e['para']) + (' cc ' + ', '.join(e['cc']) if e['cc'] else ''))}, "
          f"() => pm.expect(r.some(m => casa(ESPERADOS[{k}], m)), \"recibidos: \" + recibidos).to.be.true);"
          for k, e in enumerate(correos)],
        'pm.test("cada correo esperado casa con uno distinto", () => pm.expect(asignar(0, r), '
        '"recibidos: " + recibidos).to.be.true);',
    ]
    return _peticion(nombre, "GET", "mensajes", token=False, base="{{smtpUrl}}", test=lineas)


def _consulta(c: str, i: int, k: int, paquete: str, q: dict) -> dict:
    """Lectura de filas múltiples: `API/bdm/businessData/<clase>?q=<consulta>&p=0&c=…&f=<param>=<valor>`; número exacto
    de filas y, por atributo, los valores en el orden que devuelve la consulta."""
    ref = f"{q['objeto']}.{q['consulta']}"
    query = [("q", q["consulta"]), ("p", "0"), ("c", str(max(100, q["filas"] + 1)))]
    for n, v in q["parametros"].items():
        query.append(("f", f"{n}={_con_huecos(v) if _huecos_bv(v) else quote(v, safe='')}"))
    return _peticion(f"[{c}] {i}. consulta {k} {ref}", "GET", f"API/bdm/businessData/{paquete}.{q['objeto']}", query,
                     test=[
        f"pm.test({_j(ref + ' 200')}, () => pm.response.to.have.status(200));",
        _LISTA,
        f"pm.test({_j(ref + ' devuelve ' + str(q['filas']) + ' filas')}, () => pm.expect(r.length, "
        f"JSON.stringify(r)).to.eql({q['filas']}));",
        *[f"pm.test({_j(ref + ': ' + a + ' = ' + ', '.join(vs))}, () => pm.expect(r.map(o => String(o[{_j(a)}])))"
          f".to.eql({_j(vs)}));" for a, vs in q["valores"].items()],
    ])


_EVENTOS = {"inicio", "fin", "timer_borde"}


def evidencia_de_fin(pool: dict) -> dict[str, list[dict]]:
    """Fin (nombre) -> alternativas observables en los flow nodes archivados del caso; el fin se alcanzó si se cumple
    alguna: `{"nodo": nombre, "estado": estado archivado, "sin": [nombres que no deben aparecer]}`. Un fin sin
    alternativas no se puede observar (p. ej. inicio → fin)."""
    nodos = {n["id"]: n for n in pool["nodos"]}
    salidas: dict[str, list[str]] = {}
    for t in pool["transiciones"]:
        salidas.setdefault(t["desde"], []).append(t["hacia"])
    out: dict[str, list[dict]] = {}
    for fin in (n for n in pool["nodos"] if n["tipo"] == "fin"):
        alternativas = []
        for t in (t for t in pool["transiciones"] if t["hacia"] == fin["id"]):
            fuente = nodos[t["desde"]]
            if fuente["tipo"] == "timer_borde" and fuente.get("interruptor") and fuente.get("anfitrion"):
                alternativas.append({"nodo": nodos[fuente["anfitrion"]]["nombre"], "estado": "aborted", "sin": []})
            elif fuente["tipo"] not in _EVENTOS:
                otras = [nodos[h] for h in salidas.get(fuente["id"], []) if h != fin["id"]]
                sin = [o["nombre"] for o in otras if o["tipo"] not in _EVENTOS] if fuente["tipo"] == "xor" else []
                alternativas.append({"nodo": fuente["nombre"], "estado": "completed", "sin": sin})
        out[fin["nombre"]] = alternativas
    return out


def _final(c: str, i: int, spec: dict, camino: dict, lector: str, clave: str) -> list[dict]:
    pool = spec["procesos"][0]
    nodos = {n["id"]: n for n in pool["nodos"]}
    if camino["fin"] not in nodos or nodos[camino["fin"]]["tipo"] != "fin":
        raise ValueError(f"camino «{camino['id']}»: «{camino['fin']}» no es un evento de fin de {pool['nombre']}")
    fin = nodos[camino["fin"]]["nombre"]
    evidencia = evidencia_de_fin(pool)
    if not evidencia[fin]:
        raise ValueError(f"camino «{camino['id']}»: el fin «{camino['fin']}» no se puede observar en los flow nodes "
                         "archivados (ninguna tarea, compuerta o timer de borde lo precede)")
    bvs = {b["nombre"]: b["objeto"] for b in pool.get("business_variables", [])}
    por_bv: dict[str, list[tuple[str, object]]] = {}
    for clave_attr, valor in camino["esperado"].items():
        bv, _, attr = clave_attr.partition(".")
        if bv not in bvs or not attr:
            raise ValueError(f"camino «{camino['id']}»: «{clave_attr}» no es <business variable>.<atributo> de "
                             f"{pool['nombre']}")
        por_bv.setdefault(bv, []).append((attr, valor))
    consultas = camino.get("consultas", [])
    del_contexto = list(por_bv) + [b for q in consultas for v in q["parametros"].values() for b in _huecos_bv(v)
                                   if b not in por_bv]
    del_contexto = list(dict.fromkeys(del_contexto))
    nombre_arch = f"[{c}] {i}. caso archivado"
    out = [
        _login(f"[{c}] {i}. login {lector} (comprobación)", lector, clave),
        _peticion(nombre_arch, "GET", "API/bpm/archivedCase", [("f", "sourceObjectId={{caseId}}"), ("p", "0"),
                                                               ("c", "1")], test=[
            _LISTA,
            *_sondeo(nombre_arch, "r.length > 0"),
            'pm.test("caso terminado (archivado)", () => pm.expect(r.length).to.eql(1));',
            'if (r.length) pm.collectionVariables.set("archivedCaseId", String(r[0].id));',
        ]),
        _peticion(f"[{c}] {i}. fin {camino['fin']}", "GET", "API/bpm/archivedFlowNode",
                  [("f", "caseId={{caseId}}"), ("p", "0"), ("c", "500")], test=[
            'pm.test("archivedFlowNode 200", () => pm.response.to.have.status(200));',
            _LISTA, _CASO,
            # Solo los nodos del pool principal (processId = definición instanciada): uno del subproceso con el mismo
            # nombre no da un fin por alcanzado.
            'const proceso = String(pm.variables.get("processId"));',
            "const delCaso = r.filter(x => String(x.rootCaseId) === caso && String(x.processId) === proceso);",
            "const hay = (n, e) => delCaso.some(x => x.name === n && (!e || x.state === e));",
            "const alcanzado = (alts) => alts.some(a => hay(a.nodo, a.estado) && a.sin.every(n => !hay(n)));",
            "// Los eventos no se archivan: cada fin se deduce de lo que lo precede (evidencia_de_fin).",
            f"const FINES = {_j(evidencia)};",
            "const vistos = delCaso.map(x => x.name + \"/\" + x.state).join(\", \");",
            f"pm.test({_j('el caso termina en ' + camino['fin'])}, () => pm.expect(alcanzado(FINES[{_j(fin)}]), "
            "\"flow nodes archivados: \" + vistos).to.be.true);",
            f"pm.test(\"ningún otro fin del pool\", () => pm.expect(Object.keys(FINES).filter(f => f !== {_j(fin)} "
            "&& alcanzado(FINES[f]))).to.eql([]));",
        ]),
        _peticion(f"[{c}] {i}. contexto del caso archivado", "GET", "API/bpm/archivedCase/{{archivedCaseId}}/context",
                  test=[
            "const ctx = pm.response.json();",
            *_guardar_storage_ids(del_contexto),
        ]),
    ]
    for bv, attrs in por_bv.items():
        clase = f"{spec['bdm']['paquete']}.{bvs[bv]}"
        out.append(_peticion(f"[{c}] {i}. {bv} de este caso en el BDM", "GET",
                             f"API/bdm/businessData/{clase}/{{{{{bv}_storageId}}}}", test=[
            f"pm.test({_j(bvs[bv] + ' 200')}, () => pm.response.to.have.status(200));",
            "const o = pm.response.json();",
            *[f"pm.test({_j(bv + '.' + a + ' = ' + str(v))}, () => pm.expect(String(o[{_j(a)}]))"
              f".to.eql(String({_j(v)})));" for a, v in attrs],
        ]))
    out += [_consulta(c, i, k, spec["bdm"]["paquete"], q) for k, q in enumerate(consultas, 1)]
    out.append(_logout(f"[{c}] {i}. logout {lector} (comprobación)"))
    if camino.get("correos") is not None:
        out.append(_correos(c, i, camino["correos"]))
    return out


def _camino(spec: dict, camino: dict, clave: str) -> dict:
    c = camino["id"]
    pool = spec["procesos"][0]
    pasos = camino["pasos"]
    if not pasos or pasos[0]["tarea"] != INSTANCIACION:
        raise ValueError(f"camino «{c}»: el primer paso tiene que ser {INSTANCIACION}")
    lector = pasos[0]["usuario"]
    item: list[dict] = [_vaciar_smtp(c)] if camino.get("correos") is not None else []
    edicion = (spec.get("proyecto") or {}).get("edicion_desarrollo") or "community"  # el runtime del journey
    for i, paso in enumerate(pasos, 1):
        if paso["tarea"] == DENEGADO:
            item += _denegado(c, i, paso, lector, clave, edicion)
            continue
        if paso["tarea"] == NO_VE:
            usuario = paso["usuario"]
            try:
                _, tarea = nodo_de_paso(spec["procesos"], paso.get("objetivo"), {"humana"}, "una tarea humana")
            except ValueError as e:
                raise ValueError(f"camino «{c}»: {e}") from None
            cuerpo = _no_ve(c, i, tarea, paso)
        elif paso["tarea"] == ESPERAR:
            try:
                dueno, timer = nodo_de_paso(spec["procesos"], paso.get("evento"), {"timer_borde"}, "un timer de borde")
            except ValueError as e:
                raise ValueError(f"camino «{c}»: {e}") from None
            anfitriona = next((n for n in dueno["nodos"] if n["id"] == timer.get("anfitrion")), None)
            if anfitriona is None:
                raise ValueError(f"camino «{c}»: «{paso.get('evento')}» no es un evento de borde con tarea anfitriona")
            # Sondea un candidato de la anfitriona con su filtro de usuario (D-75); si no hay, quien instancia.
            vigilante = next((u["nombre"] for u in spec["organizacion"]["usuarios"]
                              if candidato(spec["organizacion"], dueno, anfitriona["id"], u["nombre"])), None)
            usuario = vigilante or lector
            cuerpo = [_esperar(c, i, timer, anfitriona, vigilante)]
        elif paso["tarea"] == INSTANCIACION:
            usuario = paso["usuario"]
            cuerpo = _instanciar(c, i, pool, _con_contrato(paso, pool, INSTANCIACION))
        else:
            usuario = paso["usuario"]
            try:
                dueno, tarea = nodo_de_paso(spec["procesos"], paso["tarea"], {"humana"}, "una tarea humana")
            except ValueError as e:
                raise ValueError(f"camino «{c}»: {e}") from None
            cuerpo = _ejecutar(c, i, tarea, _con_contrato(paso, dueno, tarea["id"]), dueno, spec["bdm"]["paquete"])
        item += [_login(f"[{c}] {i}. login {usuario}", usuario, clave), *cuerpo, _logout(f"[{c}] {i}. logout {usuario}")]
    item += _final(c, len(pasos) + 1, spec, camino, lector, clave)
    return {"name": c, "item": item}


def generar_journey(spec: dict) -> dict:
    """Colección Postman v2.1 con la preparación y una carpeta por camino de `spec["caminos"]` (pool principal =
    `spec["procesos"][0]`). Falla con ValueError si un paso nombra una tarea, un timer, un fin o un atributo que la
    spec no tiene."""
    clave = spec["organizacion"].get("contrasena") or "bpm"
    usuarios = {u["nombre"] for u in spec["organizacion"]["usuarios"]}
    for camino in spec["caminos"]:
        for paso in camino["pasos"]:
            if paso["tarea"] != ESPERAR and paso["usuario"] not in usuarios:
                raise ValueError(f"camino «{camino['id']}»: el usuario «{paso['usuario']}» no está en la organización")
    nombre = spec.get("proyecto", {}).get("nombre", "proyecto")
    variables = [("baseUrl", BASE_URL), ("adminUsuario", "install"), ("adminClave", "install"), ("token", ""),
                 ("sondeoInicio", ""), ("anfitrionaVista", "")]
    if any(c.get("correos") is not None for c in spec["caminos"]):
        variables.append(("smtpUrl", SMTP_URL))  # run-journey.sh arranca el SMTP de prueba si la ve
    return {
        "info": {"name": f"{nombre} — journey generado desde los caminos", "schema": SCHEMA},
        "item": [_preparacion(spec), *[_camino(spec, c, clave) for c in spec["caminos"]]],
        "variable": [{"key": k, "value": v} for k, v in variables],
    }
