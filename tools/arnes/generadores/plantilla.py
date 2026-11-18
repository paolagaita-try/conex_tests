"""Crea un proyecto Bonita nuevo a partir de `plantilla/`."""
import json
import shutil
import tempfile
from pathlib import Path

from generadores.nombres import GRUPO, MENSAJE, NOMBRE_PROYECTO, es
from generadores.version import RAIZ_REPO, cargar_version

PLANTILLA = RAIZ_REPO / "plantilla"
SUFIJOS_CON_PLACEHOLDERS = {".xml", ".project", ".groovy"}
# `package.json` y `package-lock.json`: los de `frontend/`, que llevan `{{NOMBRE}}-formularios`.
# `configuration.properties` del módulo de parámetros nombra la clase del adaptador del proyecto ({{GRUPO}}).
# Una carpeta `__grupo__` (el paquete `{{GRUPO}}` del adaptador de parámetros) se convierte en la ruta del grupo.
CARPETA_DEL_GRUPO = "__grupo__"
NOMBRES_CON_PLACEHOLDERS = {".project", "docker-compose.yml", "Dockerfile", "package.json", "package-lock.json",
                            "configuration.properties"}
FORMULARIOS = ("svelte",)
# Ficheros de texto en los que se fusiona (se añaden las líneas que faltan) en vez de chocar.
FUSIONABLES = (".gitignore", ".gitattributes")
# npm pack nunca empaqueta un `.gitignore`: la plantilla lo guarda sin el punto y el montaje le devuelve el nombre.
GITIGNORE_EN_PLANTILLA = "gitignore"


def nuevo_proyecto(destino: Path, nombre: str, grupo: str, version_bonita: str = "2026.2",
                   edicion_destino: str = "community", formularios: str = "svelte") -> Path:
    """Copia `plantilla/` a `destino`, sustituye `{{NOMBRE}}`, `{{GRUPO}}`, `{{MAVEN_PARENT}}`, `{{RUNTIME}}`,
    `{{CONECTOR_REST}}` y las marcas de imagen (`{{IMAGEN_BONITA}}`, `{{IMAGEN_POSTGRES}}`, `{{PLATAFORMA}}`, de
    `versiones/<v>.json`), escribe `destino/.trycore-bonita.json` y genera el proceso de ejemplo `hola` desde
    `plantilla/hola/spec-hola.json`: su `.proc` y su `.conf`, su formulario Svelte de tarea en la aplicación `hola`, su
    semilla de parámetros (`param_saludos`) y los bloques de actores de las extensiones.

    El destino puede tener contenido (p. ej. `docs/`, `.claude/`, `CLAUDE.md` de la documentación) mientras no tenga
    `bonita-project/` ni `.trycore-bonita.json`. Un fichero de la plantilla que ya existe: idéntico, se deja;
    `.gitignore` y `.gitattributes`, se añaden al final las líneas que falten; otro distinto, ValueError que los
    lista, antes de tocar el disco.

    Nombre, grupo, versión y formularios se validan antes de tocar el disco (ValueError); si algo falla después, se
    borra solo lo creado y se restauran `.gitignore` y `.gitattributes`."""
    destino = Path(destino)
    # Van a poms, `.project` y XML: con `&`, `<` o `/` los romperían. Se comprueban antes de tocar el disco.
    if not es(NOMBRE_PROYECTO, nombre):
        raise ValueError(f"--nombre «{nombre}»: {MENSAJE['nombre']}")
    if not es(GRUPO, grupo):
        raise ValueError(f"--grupo «{grupo}»: {MENSAJE['grupo']}")
    if formularios not in FORMULARIOS:
        raise ValueError(f"--formularios «{formularios}»: solo se admite {', '.join(FORMULARIOS)}")
    version = cargar_version(version_bonita)  # falla antes de tocar el disco si la versión no está en la matriz
    if destino.exists() and not destino.is_dir():
        raise ValueError(f"El destino {destino} existe y no es una carpeta")
    for marca in ("bonita-project", ".trycore-bonita.json"):
        if (destino / marca).exists():
            raise ValueError(f"El destino {destino} ya es un proyecto Bonita (existe {marca})")
    with tempfile.TemporaryDirectory() as tmp:
        # Todo se arma primero en una carpeta temporal: así se conoce el contenido final de cada fichero y se
        # detectan las colisiones sin haber tocado el destino.
        montaje = Path(tmp) / "montaje"
        _montar(montaje, nombre, grupo, version_bonita, edicion_destino, formularios, version)
        _volcar(montaje, destino)
    return destino


_IGNORAR_AL_MONTAR = shutil.ignore_patterns("__pycache__", "node_modules", "dist", "dist-zips", "parametros-kp.xml")


def _ignorar_al_montar(carpeta: str, nombres: list[str]) -> set[str]:
    """Lo que no se copia a un proyecto nuevo: restos de instalación y build, y los `.env`/`.env.*` locales (los de la
    máquina del arnés, con la clave de desarrollo), salvo `.env.example`, que sí es plantilla."""
    fuera = set(_IGNORAR_AL_MONTAR(carpeta, nombres))
    fuera |= {n for n in nombres if (n == ".env" or n.startswith(".env.")) and n != ".env.example"}
    return fuera


def _montar(montaje: Path, nombre: str, grupo: str, version_bonita: str, edicion_destino: str, formularios: str,
            version: dict) -> None:
    sustituciones = {
        "{{NOMBRE}}": nombre,
        "{{GRUPO}}": grupo,
        "{{MAVEN_PARENT}}": version["maven_parent"]["version"],
        "{{RUNTIME}}": version["runtime"],
        "{{CONECTOR_REST}}": version["conectores"]["rest"]["version"],
        "{{IMAGEN_BONITA}}": version["docker"]["bonita"],
        "{{IMAGEN_POSTGRES}}": version["docker"]["postgres"],
        "{{PLATAFORMA}}": version["docker"]["platform"],
    }
    # Lo que deja una instalación o un build local en `frontend/` no es plantilla; `parametros-kp.xml` solo alimenta al
    # generador del BDM.
    shutil.copytree(PLANTILLA, montaje, ignore=_ignorar_al_montar)
    (montaje / GITIGNORE_EN_PLANTILLA).rename(montaje / ".gitignore")
    for f in montaje.rglob("*"):
        if f.is_file() and (f.suffix in SUFIJOS_CON_PLACEHOLDERS or f.name in NOMBRES_CON_PLACEHOLDERS):
            # Un `.properties` lo lee la plataforma en ISO-8859-1 (`Properties.load`): se respeta su codificación.
            codificacion = "iso-8859-1" if f.suffix == ".properties" else "utf-8"
            texto = f.read_text(encoding=codificacion)
            for clave, valor in sustituciones.items():
                texto = texto.replace(clave, valor)
            f.write_text(texto, encoding=codificacion)
    for carpeta in sorted(montaje.rglob(CARPETA_DEL_GRUPO), key=lambda c: len(c.parts), reverse=True):
        if carpeta.is_dir():
            destino_pkg = carpeta.parent.joinpath(*grupo.split("."))
            destino_pkg.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(carpeta), str(destino_pkg))
    meta = {"nombre": nombre, "grupo": grupo, "version_bonita": version_bonita,
            "edicion_desarrollo": "community", "edicion_destino": edicion_destino, "formularios": formularios}
    (montaje / ".trycore-bonita.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # hola no se versiona: su .proc, su formulario Svelte (mapeado por URL en su aplicación `hola`), su semilla de
    # parámetros y los bloques de actores salen de su spec con los escritores reales (BDM y organización de la plantilla).
    from generadores.escribir import escribir_proyecto, spec_de_hola
    escribir_proyecto(spec_de_hola(), montaje)


def _escribir(ruta: Path, datos: bytes) -> None:
    ruta.write_bytes(datos)


def _fusionar(existente: bytes, nuevo: bytes) -> bytes | None:
    """`existente` con al final las líneas de `nuevo` que le faltan; None si no falta ninguna."""
    tengo = {l.strip() for l in existente.decode("utf-8").splitlines()}
    faltan = [l for l in nuevo.decode("utf-8").splitlines() if l.strip() and l.strip() not in tengo]
    if not faltan:
        return None
    base = existente.decode("utf-8")
    if base and not base.endswith("\n"):
        base += "\n"
    return (base + "\n".join(faltan) + "\n").encode("utf-8")


def _volcar(montaje: Path, destino: Path) -> None:
    """Pasa lo montado a `destino`. Primero planea (y detecta colisiones) sin escribir; después escribe, y si algo
    falla borra lo creado y restaura los ficheros fusionados."""
    crear: list[tuple[Path, bytes, int]] = []  # (ruta, contenido, permisos)
    fusionar: list[tuple[Path, bytes, bytes]] = []  # (ruta, original, fusionado)
    choques: list[str] = []
    for origen in sorted(montaje.rglob("*")):
        rel = origen.relative_to(montaje)
        real = destino / rel
        if origen.is_dir():
            if real.exists() and not real.is_dir():
                choques.append(f"{rel.as_posix()} (existe un fichero donde la plantilla pone una carpeta)")
            continue
        datos = origen.read_bytes()
        if not real.exists() and not real.is_symlink():
            if any(p.is_file() or p.is_symlink() for p in real.parents if p != destino and destino in p.parents):
                choques.append(f"{rel.as_posix()} (un tramo de su ruta es un fichero)")
            else:
                crear.append((real, datos, origen.stat().st_mode & 0o777))
        elif real.is_dir():
            choques.append(f"{rel.as_posix()} (existe una carpeta donde la plantilla pone un fichero)")
        elif real.read_bytes() == datos:
            continue
        elif rel.as_posix() in FUSIONABLES:
            original = real.read_bytes()
            try:
                fusionado = _fusionar(original, datos)
            except UnicodeDecodeError:
                choques.append(f"{rel.as_posix()} (no es texto UTF-8; no se puede fusionar)")
                continue
            if fusionado is not None:
                fusionar.append((real, original, fusionado))
        else:
            choques.append(f"{rel.as_posix()} (ya existe y es distinto de la plantilla)")
    if choques:
        raise ValueError("El destino tiene ficheros que chocan con la plantilla; muévelos o renómbralos y vuelve a "
                         f"intentarlo (no se escribió nada): {'; '.join(choques)}")
    existia = destino.exists()
    creados: list[Path] = []  # ficheros y carpetas nuevos, en orden de creación
    hechos: list[tuple[Path, bytes]] = []
    try:
        if not existia:
            destino.mkdir(parents=True)
            creados.append(destino)
        for ruta, datos, modo in crear:
            falta = [p for p in reversed(ruta.parents) if not p.exists()]
            for p in falta:
                p.mkdir()
                creados.append(p)
            creados.append(ruta)  # antes de escribir: un fallo a medias del propio fichero también se limpia
            _escribir(ruta, datos)
            ruta.chmod(modo)  # los scripts de tools/ conservan el permiso de ejecución
        for ruta, original, fusionado in fusionar:
            hechos.append((ruta, original))
            _escribir(ruta, fusionado)
    except BaseException:
        for ruta, original in hechos:
            ruta.write_bytes(original)
        for p in reversed(creados):
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
        raise
