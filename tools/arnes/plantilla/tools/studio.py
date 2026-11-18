#!/usr/bin/env python3
"""Lleva el proyecto al Bonita Studio: copia espejo que el Studio clona y despliegue en su motor local de lo que su
Deploy no lleva. Se lanza con `tools/arnes.sh studio`.

Por qué hace falta (medido con el Studio Subscription 2026.2 sobre el ejemplo vacaciones):
  - El Studio solo clona un repositorio cuyo proyecto Bonita está en la raíz; en un proyecto del arnés está en
    `bonita-project/`, junto a `docs/`, `tools/` y `frontend/`. La copia espejo (por defecto `../<nombre>-studio`, un git
    local) lleva `bonita-project/` en la raíz y `frontend/` dentro, con los zips de los formularios ya compilados.
  - El Deploy del Studio despliega procesos, BDM, organización y perfiles, pero no lo que el arnés mete en el artefacto
    con Maven: las REST API, las páginas Svelte y las aplicaciones. Este paso las sube por REST, en ese orden (una
    página que declara recursos de una REST API que aún no está se queda sin permisos: «Unknown resource»).
  - El motor del Studio no recibe `app/permisos/custom-permissions-mapping.properties`: sin esa línea la REST API de
    parámetros responde 403. Su configuración vive en su base H2 (`AUTO_SERVER=TRUE`: admite un segundo proceso); este
    paso fusiona ahí las líneas del proyecto y avisa de que hay que reiniciar el servidor del Studio.
  - Reiniciar el servidor o volver a desplegar borra los mapeos de perfiles: este paso los repone (los de
    `tools/perfiles.py`), así que se vuelve a lanzar después de cada Deploy o reinicio del Studio.

Pasos: construir (`tools/construir.sh`: frontend + `mvn install`) -> espejo (commit si cambió) -> si el motor del Studio
responde en `--url`: REST API, páginas, aplicaciones, perfiles y permisos. Idempotente.

Uso: tools/studio.py [--url http://localhost:8080/bonita] [--espejo RUTA] [--sin-construir] [--solo-espejo]
Credenciales del administrador técnico como en tools/perfiles.py (BONITA_ADMIN_USUARIO / BONITA_ADMIN_CLAVE o
`--clave-stdin`; sin ellas, las de desarrollo install/install, solo contra el motor local).
Salida: 0 hecho; 1 fallo contra el motor o el build; 2 uso o proyecto mal.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import uuid
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import perfiles  # noqa: E402  (mismo directorio: tools/perfiles.py)
import reglas  # noqa: E402  (mismo directorio: tools/reglas.py)

# La raíz del proyecto: la carpeta de encima de tools/ o, si se lanza la copia del arnés instalado
# (tools/arnes/plantilla/tools/, la que usa `tools/arnes.sh`), la que diga TRYCORE_PROYECTO.
RAIZ = Path(os.environ.get("TRYCORE_PROYECTO") or Path(__file__).resolve().parent.parent).resolve()
Bonita, Fallo = perfiles.Bonita, perfiles.Fallo
# Lo que no viaja al espejo: builds, dependencias, bases locales y entornos con claves.
_FUERA_BONITA = shutil.ignore_patterns("target", ".flattened-pom.xml", "dependency-reduced-pom.xml", "h2_database",
                                       "__pycache__", ".DS_Store")
_FUERA_FRONTEND = shutil.ignore_patterns("node_modules", "dist", "coverage", "test-results", "playwright-report",
                                         ".vite", "temp_build", "*.tsbuildinfo", ".env", ".env.*", ".DS_Store")
GITIGNORE_ESPEJO = """# Copia espejo para el Bonita Studio (tools/arnes.sh studio): no se edita a mano, se regenera.
target/
.flattened-pom.xml
dependency-reduced-pom.xml
h2_database/
.DS_Store
bin
.classpath
.settings
app/web_widgets/
app/web_page/.metadata/
app/dependencies/
# Los zips de los formularios (frontend/dist-zips/) sí se versionan: el Studio construye sin Node.
frontend/node_modules/
"""
PERMISOS = "custom-permissions-mapping.properties"
_LINEA = re.compile(r"^\s*([^#!\s][^=]*?)\s*=\s*\[(.*)\]\s*$")


# ---------------------------------------------------------------- permisos
def _lista(valor: str) -> list[str]:
    return [p.strip() for p in valor.split(",") if p.strip()]


def fusionar_permisos(actual: str, proyecto: str) -> tuple[str, list[str]]:
    """El contenido de `actual` con las líneas `clave=[permisos]` de `proyecto`: una clave nueva se añade al final y una
    que ya está recibe los permisos que le faltan (en su sitio). Devuelve el texto y los cambios («clave: p1, p2»)."""
    lineas = actual.splitlines()
    cambios: list[str] = []
    for linea in proyecto.splitlines():
        m = _LINEA.match(linea)
        if not m:
            continue
        clave, permisos = m.group(1), _lista(m.group(2))
        i = next((k for k, l in enumerate(lineas) if (x := _LINEA.match(l)) and x.group(1) == clave), None)
        if i is None:
            lineas.append(f"{clave}=[{', '.join(permisos)}]")
            cambios.append(f"{clave}: {', '.join(permisos)}")
            continue
        ya = _lista(_LINEA.match(lineas[i]).group(2))
        faltan = [p for p in permisos if p not in ya]
        if faltan:
            lineas[i] = f"{clave}=[{', '.join(ya + faltan)}]"
            cambios.append(f"{clave}: {', '.join(faltan)}")
    return "\n".join(lineas) + "\n", cambios


class H2:
    """La tabla `configuration` de la base H2 del motor del Studio, con la consola de H2 (`org.h2.tools.Shell`)."""

    def __init__(self, java: Path, jar: Path, base: Path):
        self.java, self.jar, self.base = java, jar, base

    def sql(self, sentencia: str) -> str:
        url = f"jdbc:h2:file:{self.base};IGNORECASE=TRUE;AUTO_SERVER=TRUE"
        r = subprocess.run([str(self.java), "-cp", str(self.jar), "org.h2.tools.Shell", "-url", url, "-user", "sa",
                            "-password", "", "-sql", sentencia], capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or "Exception" in r.stdout + r.stderr:
            raise Fallo(f"H2 ({self.base}): {(r.stdout + r.stderr).strip()[:300]}")
        return r.stdout

    _FILA = "WHERE content_type='TENANT_PORTAL' AND resource_name='custom-permissions-mapping.properties'"

    _TIPO_REGLAS = "TENANT_SECURITY_SCRIPTS"
    _FILA_PERMISOS = ("TENANT_PORTAL", PERMISOS)

    @staticmethod
    def _q(texto: str) -> str:
        return texto.replace("'", "''")

    def _donde(self, tipo: str, nombre: str) -> str:
        return f"WHERE content_type='{self._q(tipo)}' AND resource_name='{self._q(nombre)}'"

    def leer_fila(self, tipo: str, nombre: str, codificacion: str = "utf-8") -> str | None:
        """El texto de la fila (tipo, nombre) de la tabla `configuration`, o None si no está. Un `.properties` va en
        ISO-8859-1 (`codificacion`), como lo lee Bonita."""
        salida = self.sql(f"SELECT RAWTOHEX(resource_content) FROM configuration {self._donde(tipo, nombre)}")
        hexa = [l.strip() for l in salida.splitlines() if re.fullmatch(r"[0-9a-fA-F]+", l.strip() or "x")]
        return bytes.fromhex(hexa[0]).decode(codificacion) if len(hexa) == 1 else None

    def escribir_fila(self, tipo: str, nombre: str, texto: str, plantilla: tuple[str, str] | None = None,
                      codificacion: str = "utf-8") -> None:
        """Pone `texto` en la fila (tipo, nombre); si no existe la crea con el tenant de la fila `plantilla`
        (por defecto la de los permisos). [no verificado] la forma de la fila de `TENANT_SECURITY_SCRIPTS` en el
        motor del Studio (A-3): el despliegue de reglas lo comprueba leyéndola de vuelta."""
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as f:
            f.write(_codificar(texto, codificacion))
        try:
            ruta = self._q(Path(f.name).resolve().as_posix())
            if self.leer_fila(tipo, nombre, codificacion) is None:
                pt, pn = plantilla or self._FILA_PERMISOS
                self.sql("INSERT INTO configuration (tenant_id, content_type, resource_name, resource_content) "
                         f"SELECT tenant_id, '{self._q(tipo)}', '{self._q(nombre)}', FILE_READ('{ruta}') "
                         f"FROM configuration {self._donde(pt, pn)}")
            else:
                self.sql(f"UPDATE configuration SET resource_content = FILE_READ('{ruta}') {self._donde(tipo, nombre)}")
        finally:
            os.unlink(f.name)
        if self.leer_fila(tipo, nombre, codificacion) != texto:
            raise Fallo(f"H2 ({self.base}): la fila {tipo}/{nombre} no quedó como se escribió")

    def leer_permisos(self) -> str:
        salida = self.sql(f"SELECT RAWTOHEX(resource_content) FROM configuration {self._FILA}")
        hexa = [l.strip() for l in salida.splitlines() if re.fullmatch(r"[0-9a-fA-F]+", l.strip() or "x")]
        if len(hexa) != 1:
            raise Fallo(f"H2 ({self.base}): no encuentro la fila de {PERMISOS} del tenant")
        return bytes.fromhex(hexa[0]).decode("utf-8")

    def escribir_permisos(self, texto: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".properties", delete=False, encoding="utf-8") as f:
            f.write(texto)
        try:
            ruta = Path(f.name).resolve().as_posix().replace("'", "''")
            self.sql(f"UPDATE configuration SET resource_content = FILE_READ('{ruta}') {self._FILA}")
        finally:
            os.unlink(f.name)
        if self.leer_permisos() != texto:
            raise Fallo(f"H2 ({self.base}): {PERMISOS} no quedó como se escribió")


LATIN1 = "iso-8859-1"


def _codificar(texto: str, codificacion: str) -> bytes:
    """`texto` en `codificacion`; en ISO-8859-1, lo que no cabe como escape `\\uXXXX` de properties."""
    if codificacion == LATIN1:
        return "".join(c if ord(c) < 256 else f"\\u{ord(c):04x}" for c in texto).encode(LATIN1)
    return texto.encode(codificacion)


def motor_desde_ps(texto: str) -> tuple[Path, Path] | None:
    """(carpeta H2, catalina.home) del proceso del motor del Studio en la salida de `ps`, o None."""
    for linea in texto.splitlines():
        if "org.bonitasoft.studio" not in linea:
            continue
        h2 = re.search(r"-Dorg\.bonitasoft\.h2\.database\.dir=(\S+)", linea)
        tomcat = re.search(r"-Dcatalina\.home=(\S+)", linea)
        if h2 and tomcat:
            return Path(h2.group(1)), Path(tomcat.group(1))
    return None


def _java() -> Path:
    casa = os.environ.get("BONITA_JAVA_HOME") or os.environ.get("JAVA_HOME")
    if casa and (Path(casa) / "bin/java").exists():
        return Path(casa) / "bin/java"
    encontrado = shutil.which("java")
    if not encontrado:
        raise Fallo("no hay java para abrir la base H2 del Studio (define BONITA_JAVA_HOME)")
    return Path(encontrado)


def _h2_del_motor() -> H2:
    ps = subprocess.run(["ps", "-axww", "-o", "args="], capture_output=True, text=True).stdout
    motor = motor_desde_ps(ps)
    if motor is None:
        raise Fallo("no encuentro el proceso del motor del Studio (¿está abierto el Studio con su servidor?)")
    carpeta, tomcat = motor
    jars = sorted((tomcat / "lib" / "bonita").glob("h2-*.jar"))
    if not jars:
        raise Fallo(f"no encuentro el jar de H2 en {tomcat / 'lib/bonita'}")
    return H2(_java(), jars[-1], carpeta / "bonita_journal.db")


def aplicar_permisos(proyecto: str) -> list[str]:
    """Fusiona las líneas del proyecto en la configuración del motor del Studio. Devuelve los cambios."""
    h2 = _h2_del_motor()
    nuevo, cambios = fusionar_permisos(h2.leer_permisos(), proyecto)
    if cambios:
        h2.escribir_permisos(nuevo)
    return cambios


# ---------------------------------------------------------------- reglas dinámicas (R-14)
def reglas_para_studio(raiz: Path, edicion: str, h2: H2 | None = None) -> list[str]:
    """Despliega las reglas dinámicas del proyecto en el motor del Studio y devuelve los mensajes («aviso: …» o lo
    hecho). Son de las ediciones Subscription: con `edicion_destino` `community` solo avisa. Sin reglas, nada.
    `h2` se abre del proceso del Studio si no se pasa."""
    app = Path(raiz) / "bonita-project/app"
    grupo = reglas.reglas(app)
    if not grupo:
        return []
    if edicion != "subscription":
        return [f"aviso: {v}" for v in reglas.desplegar(app, Path(os.devnull), edicion)[1]]
    h2 = h2 or _h2_del_motor()
    informe = []
    for g in grupo:
        h2.escribir_fila(H2._TIPO_REGLAS, g.name, g.read_text(encoding="utf-8"))
        informe.append(f"regla dinámica {g.name} en el motor del Studio")
    props = app / "permisos" / reglas.PROPIEDADES
    if props.is_file():
        actual = h2.leer_fila("TENANT_PORTAL", reglas.PROPIEDADES, codificacion=LATIN1)
        if actual is None:
            raise Fallo(f"no encuentro la fila de {reglas.PROPIEDADES} en el motor del Studio (¿es un Studio "
                        "Subscription?)")
        # El properties lo escribe `generar` en ISO-8859-1 (como lo lee Bonita): un perfil acentuado no es UTF-8.
        nuevo, cambios = fusionar_permisos(actual, props.read_text(encoding=LATIN1))
        if cambios:
            h2.escribir_fila("TENANT_PORTAL", reglas.PROPIEDADES, nuevo, codificacion=LATIN1)
            informe.append(f"líneas dinámicas añadidas: {'; '.join(cambios)}")
    return informe


# ---------------------------------------------------------------- espejo
def _git(espejo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(espejo), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise Fallo(f"git {' '.join(args)} en {espejo}: {r.stderr.strip()[:300]}")
    return r.stdout


def _vaciar(espejo: Path) -> None:
    for hijo in espejo.iterdir():
        if hijo.name == ".git":
            continue
        shutil.rmtree(hijo) if hijo.is_dir() and not hijo.is_symlink() else hijo.unlink()


def sincronizar_espejo(proyecto: Path, espejo: Path) -> str | None:
    """Deja en `espejo` (un git local; se crea si no existe) `bonita-project/` en la raíz y `frontend/` dentro, y hace
    commit si algo cambió. Devuelve el sha del commit o None si no había cambios."""
    if espejo.resolve() == proyecto.resolve() or proyecto.resolve() in espejo.resolve().parents:
        raise SystemExit(f"FALLA: el espejo {espejo} no puede estar dentro del proyecto")
    if espejo.exists() and not (espejo / ".git").is_dir():
        raise SystemExit(f"FALLA: {espejo} existe y no es un repositorio git (no lo toco)")
    if not espejo.exists():
        espejo.mkdir(parents=True)
        _git(espejo, "init", "-q", "-b", "main")
    _vaciar(espejo)
    shutil.copytree(proyecto / "bonita-project", espejo, ignore=_FUERA_BONITA, dirs_exist_ok=True)
    if (proyecto / "frontend").is_dir():
        shutil.copytree(proyecto / "frontend", espejo / "frontend", ignore=_FUERA_FRONTEND, dirs_exist_ok=True)
    (espejo / ".gitignore").write_text(GITIGNORE_ESPEJO, encoding="utf-8")
    _git(espejo, "add", "-A")
    if not _git(espejo, "status", "--porcelain").strip():
        return None
    origen = subprocess.run(["git", "-C", str(proyecto), "rev-parse", "--short", "HEAD"], capture_output=True,
                            text=True).stdout.strip() or "sin commit"
    _git(espejo, "-c", "user.name=trycore-bonita", "-c", "user.email=arnes@trycore.invalid", "commit", "-q", "-m",
         f"Espejo para el Bonita Studio de {proyecto.name} ({origen})")
    return _git(espejo, "rev-parse", "--short", "HEAD").strip()


# ---------------------------------------------------------------- artefacto y despliegue
def _nombre_de_pagina(datos: bytes) -> tuple[str | None, str | None]:
    """(name, contentType) del page.properties de un zip de página, o (None, None) si no lo es."""
    try:
        with zipfile.ZipFile(__import__("io").BytesIO(datos)) as z:
            props = z.read("page.properties").decode("iso-8859-1")
    except (zipfile.BadZipFile, KeyError):
        return None, None
    valores = dict(l.split("=", 1) for l in props.splitlines() if "=" in l and not l.lstrip().startswith("#"))
    return valores.get("name", "").strip() or None, valores.get("contentType", "").strip() or None


def artefactos(zip_app: Path, destino: Path) -> dict:
    """Del application archive (`app/target/*.zip`), lo que el Deploy del Studio no despliega: REST API
    (`extensions/*.zip` con contentType=apiExtension), páginas del proyecto (`pages/custompage_*.zip`; las de Bonita
    `page-*` no) y aplicaciones (`applications/*.xml`; las `bonita-*` las trae el motor). Extrae a `destino`."""
    destino.mkdir(parents=True, exist_ok=True)
    salida: dict[str, list] = {"extensiones": [], "paginas": [], "aplicaciones": []}
    with zipfile.ZipFile(zip_app) as z:
        for nombre in sorted(z.namelist()):
            carpeta, _, fichero = nombre.partition("/")
            if not fichero or "/" in fichero:
                continue
            datos = z.read(nombre)
            if carpeta == "extensions" and fichero.endswith(".zip"):
                pagina, tipo = _nombre_de_pagina(datos)
                if tipo == "apiExtension" and pagina:
                    (destino / fichero).write_bytes(datos)
                    salida["extensiones"].append((destino / fichero, pagina))
            elif carpeta == "pages" and fichero.startswith("custompage_") and fichero.endswith(".zip"):
                pagina, _ = _nombre_de_pagina(datos)
                (destino / fichero).write_bytes(datos)
                salida["paginas"].append((destino / fichero, pagina or fichero[:-4]))
            elif carpeta == "applications" and fichero.endswith(".xml") and not fichero.startswith("bonita-"):
                (destino / fichero).write_bytes(datos)
                salida["aplicaciones"].append(destino / fichero)
    return salida


def _subir(bonita: Bonita, servlet: str, fichero: Path) -> str:
    limite = uuid.uuid4().hex
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fichero.name}\"\r\n"
              "Content-Type: application/octet-stream\r\n\r\n").encode() + fichero.read_bytes() \
        + f"\r\n--{limite}--\r\n".encode()
    codigo, texto = bonita._pedir("POST", servlet, cuerpo, f"multipart/form-data; boundary={limite}")
    if codigo != 200 or not texto.strip():
        raise Fallo(f"subir {fichero.name} ({servlet}): HTTP {codigo} {texto[:200]}")
    return texto.strip()


def _pagina(bonita: Bonita, fichero: Path, nombre: str) -> str:
    temporal = _subir(bonita, "portal/pageUpload?action=add", fichero)
    previa = bonita.uno("portal/page", urlToken=nombre)
    cuerpo = json.dumps({"pageZip": temporal}).encode()
    if previa:
        codigo, texto = bonita._pedir("PUT", f"API/portal/page/{previa['id']}", cuerpo, "application/json")
        hecho = "actualizada"
    else:
        codigo, texto = bonita._pedir("POST", "API/portal/page", cuerpo, "application/json")
        hecho = "creada"
    if codigo != 200:
        raise Fallo(f"página {nombre}: HTTP {codigo} {texto[:300]}")
    return f"{nombre} {hecho}"


def desplegar(bonita: Bonita, a: dict) -> list[str]:
    """REST API, después páginas (sus recursos ya existen) y al final aplicaciones (sus páginas ya existen)."""
    informe = [f"REST API {_pagina(bonita, f, n)}" for f, n in a["extensiones"]]
    informe += [f"página {_pagina(bonita, f, n)}" for f, n in a["paginas"]]
    for f in a["aplicaciones"]:
        temporal = _subir(bonita, "portal/applicationsUpload", f)
        datos = urllib.parse.urlencode({"importPolicy": "REPLACE_DUPLICATES", "applicationsDataUpload": temporal})
        codigo, texto = bonita._pedir("POST", "services/application/import", datos.encode(),
                                      "application/x-www-form-urlencoded")
        errores = json.loads(texto).get("errors") if codigo == 200 and texto.startswith("{") else None
        if codigo != 200 or errores:
            raise Fallo(f"aplicación {f.name}: HTTP {codigo} {texto[:300]}")
        informe.append(f"aplicación {f.name} importada")
    return informe


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    nombre = json.loads((RAIZ / ".trycore-bonita.json").read_text(encoding="utf-8")).get("nombre", RAIZ.name) \
        if (RAIZ / ".trycore-bonita.json").is_file() else RAIZ.name
    a = argparse.ArgumentParser(description="Lleva el proyecto al Bonita Studio (espejo + despliegue en su motor).")
    a.add_argument("--url", default=os.environ.get("BONITA_STUDIO_URL", "http://localhost:8080/bonita"))
    a.add_argument("--espejo", type=Path, default=RAIZ.parent / f"{nombre}-studio")
    a.add_argument("--sin-construir", action="store_true", help="usa el build que ya está en bonita-project/app/target")
    a.add_argument("--solo-espejo", action="store_true", help="solo actualiza la copia espejo")
    a.add_argument("--usuario", default=os.environ.get("BONITA_ADMIN_USUARIO"))
    a.add_argument("--clave-stdin", action="store_true")
    args = a.parse_args(argv)
    if (urllib.parse.urlsplit(args.url).hostname or "") not in perfiles.LOCALES:
        print(f"FALLA: {args.url} no es el motor local del Studio; este paso solo trabaja contra localhost "
              "(para otros entornos: el artefacto y tools/arnes.sh perfiles)", file=sys.stderr)
        return 2
    try:
        if not args.sin_construir:
            r = subprocess.run(["bash", str(RAIZ / "tools/construir.sh")], cwd=RAIZ)
            if r.returncode != 0:
                print("FALLA: el build (tools/construir.sh)", file=sys.stderr)
                return 1
        sha = sincronizar_espejo(RAIZ, args.espejo.resolve())
        url_espejo = args.espejo.resolve().as_uri()
        print(f"studio: espejo {'actualizado (' + sha + ')' if sha else 'sin cambios'} en {args.espejo.resolve()}")
        print(f"studio:   clónalo en el Studio con la URL {url_espejo} (o haz Pull si ya lo tienes) y haz Deploy",
              flush=True)
        if args.solo_espejo:
            return 0
        zips = sorted((RAIZ / "bonita-project/app/target").glob("*.zip"))
        if len(zips) != 1:
            print(f"FALLA: se esperaba 1 zip en bonita-project/app/target y hay {len(zips)} (construye sin "
                  "--sin-construir)", file=sys.stderr)
            return 2
        clave = sys.stdin.readline().rstrip("\r\n") if args.clave_stdin else os.environ.get("BONITA_ADMIN_CLAVE")
        usuario = args.usuario or perfiles.DESARROLLO[0]
        clave = clave or perfiles.DESARROLLO[1]
        bonita = Bonita(args.url)
        try:
            bonita.entrar(usuario, clave)
        except Fallo as e:
            print(f"studio: el motor del Studio no responde en {args.url} ({e}); abre el Studio, haz Deploy del "
                  "proyecto y vuelve a lanzar tools/arnes.sh studio --sin-construir")
            return 0
        try:
            with tempfile.TemporaryDirectory() as tmp:
                for linea in desplegar(bonita, artefactos(zips[0], Path(tmp))):
                    print(f"studio: {linea}", flush=True)
            try:
                informe = perfiles.aplicar(bonita, perfiles.organizacion(), perfiles.APP / "profiles")
            except Fallo as e:
                raise Fallo(f"{e}. En el Studio, haz Deploy del proyecto (con la organización marcada) y vuelve a "
                            "lanzar tools/arnes.sh studio --sin-construir") from e
        finally:
            bonita.salir()
        for linea in informe:
            print(f"studio: perfiles: {linea}", flush=True)
        permisos = RAIZ / "bonita-project/app/permisos" / PERMISOS
        cambios = aplicar_permisos(permisos.read_text(encoding="utf-8")) if permisos.is_file() else []
        if cambios:
            print(f"studio: permisos REST añadidos al motor del Studio: {'; '.join(cambios)}")
            print("studio: REINICIA el servidor del Studio para que los lea y después vuelve a lanzar "
                  "tools/arnes.sh studio --sin-construir (el reinicio borra los mapeos de perfiles y este paso los "
                  "repone)")
        else:
            print("studio: permisos REST del proyecto ya estaban en el motor del Studio")
        for linea in reglas_para_studio(RAIZ, reglas.edicion(RAIZ)):
            print(f"studio: {linea}")
    except Fallo as e:
        print(f"FALLA: {e}", file=sys.stderr)
        return 1
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
