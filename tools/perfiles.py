#!/usr/bin/env python3
"""Paso posterior al despliegue: mapea la organización del proyecto a sus perfiles del portal, por REST.

Un artefacto Community no puede llevar los mapeos de perfiles (`include.profiles` es solo de Subscription) y, sin el
perfil `User`, el portal no abre ninguna aplicación ni el filtro REST deja leer la API de parámetros. Este paso:

  1. mapea al perfil `User` a cada usuario de `bonita-project/app/organizations/<una>.xml` (la organización generada
     que viaja en el artefacto);
  2. por cada perfil de `bonita-project/app/profiles/*.xml` mapea sus roles a ese perfil si el runtime lo tiene: los
     por defecto de `default_profile.xml` (User a todos los roles; Administrator y Process manager al rol
     `administrador` del usuario `walter.bates`) y los propios (p. ej. `AdministracionParametros`). Si el runtime no lo
     tiene (Community no admite perfiles propios ni tiene Process manager), lo dice y sigue: la app de parámetros usa
     `User` y el módulo autoriza por el rol `superAdministradorParametros`, que ya llega en la organización.

Idempotente: lee una vez los miembros de cada perfil (`GET API/portal/profileMember`, con `f=member_type=user|role`
en minúscula: sin ese filtro la API no responde) y solo añade lo que falta. Se lanza con `tools/arnes.sh perfiles` y
lo reutilizan `tools/run-journey.sh` (antes de Newman) y la globalSetup de Playwright.

Uso: tools/perfiles.py [--url http://localhost:8080/bonita] [--usuario <admin>] [--clave-stdin]
Credenciales del administrador técnico, nunca en la línea de órdenes (la vería `ps` y quedaría en el historial):
  BONITA_ADMIN_USUARIO  usuario (o `--usuario`)
  BONITA_ADMIN_CLAVE    clave (o `--clave-stdin`: la primera línea de la entrada estándar)
  BONITA_URL            dirección del runtime (o `--url`)
Sin usuario o sin clave solo se usan las de desarrollo (install/install) si el runtime es local (localhost,
127.0.0.1: el bundle de run-journey.sh), y se dice; contra otro servidor es un error de uso.
Salida: 0 hecho; 1 fallo contra el runtime (login, usuario que falta, respuesta inesperada); 2 uso o proyecto mal.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# La raíz del proyecto: la carpeta de encima de tools/ o, si se lanza la copia del arnés instalado
# (tools/arnes/plantilla/tools/, la que usa `tools/arnes.sh`), la que diga TRYCORE_PROYECTO.
RAIZ = Path(os.environ.get("TRYCORE_PROYECTO") or Path(__file__).resolve().parent.parent).resolve()
APP = RAIZ / "bonita-project" / "app"
PAGINA = 100
LOCALES = {"localhost", "127.0.0.1", "::1"}
DESARROLLO = ("install", "install")
# Perfiles por defecto de Bonita (los de `app/profiles/default_profile.xml`): Process manager no está en Community.
POR_DEFECTO = {"User", "Administrator", "Process manager"}


class Fallo(Exception):
    """Un fallo contra el runtime: se dice y sale con 1."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def usuarios_de_la_organizacion(ruta: Path) -> list[str]:
    return [u.get("userName") for u in ET.parse(ruta).getroot().iter() if _local(u.tag) == "user" and u.get("userName")]


def perfiles_propios(carpeta: Path) -> list[tuple[str, list[str]]]:
    """(nombre, roles) de cada `profile` de `app/profiles/*.xml`, en orden de fichero."""
    salida = []
    for f in sorted(carpeta.glob("*.xml")) if carpeta.is_dir() else []:
        for p in ET.parse(f).getroot().iter():
            if _local(p.tag) == "profile" and p.get("name"):
                roles = [r.text.strip() for r in p.iter() if _local(r.tag) == "role" and (r.text or "").strip()]
                salida.append((p.get("name"), roles))
    return salida


class Bonita:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        self.abridor = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def _pedir(self, metodo: str, ruta: str, cuerpo: bytes | None = None, tipo: str | None = None):
        cabeceras = {"Accept": "application/json"}
        if tipo:
            cabeceras["Content-Type"] = tipo
        token = next((c.value for c in self.cookies if c.name == "X-Bonita-API-Token"), None)
        if token and metodo != "GET":
            cabeceras["X-Bonita-API-Token"] = token
        peticion = urllib.request.Request(f"{self.url}/{ruta}", data=cuerpo, method=metodo, headers=cabeceras)
        try:
            with self.abridor.open(peticion, timeout=30) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as e:
            raise Fallo(f"no hay runtime en {self.url}: {e}") from e

    def entrar(self, usuario: str, clave: str) -> None:
        datos = urllib.parse.urlencode({"username": usuario, "password": clave, "redirect": "false"}).encode()
        codigo, _ = self._pedir("POST", "loginservice", datos, "application/x-www-form-urlencoded")
        if codigo not in (200, 204):
            raise Fallo(f"login de {usuario} en {self.url}: HTTP {codigo}")

    def salir(self) -> None:
        try:
            self._pedir("GET", "logoutservice?redirect=false")
        except Fallo:
            pass

    def get(self, recurso: str, **filtros: str) -> list[dict]:
        consulta = [("f", f"{k}={v}") for k, v in filtros.items()]
        todo: list[dict] = []
        pagina = 0
        while True:
            q = urllib.parse.urlencode(consulta + [("p", str(pagina)), ("c", str(PAGINA))])
            codigo, texto = self._pedir("GET", f"API/{recurso}?{q}")
            que = f"GET API/{recurso} ({', '.join(f'{k}={v}' for k, v in filtros.items())})"
            if codigo != 200:
                raise Fallo(f"{que}: HTTP {codigo} {texto[:200]}")
            try:
                trozo = json.loads(texto)
            except json.JSONDecodeError as e:
                raise Fallo(f"{que}: la respuesta no es JSON ({texto[:120]!r}); ¿la URL es la de Bonita?") from e
            if not isinstance(trozo, list):
                raise Fallo(f"{que}: se esperaba una lista JSON y llegó {type(trozo).__name__}")
            todo += trozo
            if len(trozo) < PAGINA:
                return todo
            pagina += 1

    def uno(self, recurso: str, **filtros: str) -> dict | None:
        lista = self.get(recurso, **filtros)
        return lista[0] if lista else None

    def miembros(self, perfil_id: str, tipo: str) -> set[str]:
        """Los ids de los miembros de un tipo (`user` o `role`) del perfil: se lee una vez por perfil y tipo."""
        campo = "user_id" if tipo == "user" else "role_id"
        return {str(m.get(campo)) for m in self.get("portal/profileMember", profile_id=perfil_id, member_type=tipo)}

    def mapear(self, perfil_id: str, tipo: str, miembro_id: str, ya: set[str]) -> bool:
        """Añade el miembro al perfil si no está en `ya` (que se actualiza). True si lo añadió."""
        campo = "user_id" if tipo == "user" else "role_id"
        if miembro_id in ya:
            return False
        ya.add(miembro_id)
        cuerpo = json.dumps({"profile_id": perfil_id, "member_type": tipo.upper(), campo: miembro_id}).encode()
        codigo, texto = self._pedir("POST", "API/portal/profileMember", cuerpo, "application/json")
        if codigo == 403 and "already exists" in texto:
            return False
        if codigo != 200:
            raise Fallo(f"POST API/portal/profileMember ({tipo} {miembro_id} en el perfil {perfil_id}): HTTP {codigo} "
                        f"{texto[:200]}")
        return True


def organizacion() -> Path:
    xmls = sorted((APP / "organizations").glob("*.xml"))
    if len(xmls) != 1:
        raise SystemExit(f"FALLA: se esperaba una sola organización en bonita-project/app/organizations/ y hay "
                         f"{len(xmls)}")
    return xmls[0]


def aplicar(bonita: Bonita, org: Path, perfiles_dir: Path) -> list[str]:
    informe = []
    user = bonita.uno("portal/profile", name="User")
    if user is None:
        raise Fallo("el runtime no tiene el perfil User")
    nuevos = ya = 0
    faltan = []
    miembros_user = bonita.miembros(str(user["id"]), "user")
    for nombre in usuarios_de_la_organizacion(org):
        u = bonita.uno("identity/user", userName=nombre)
        if u is None:
            faltan.append(nombre)
            continue
        if bonita.mapear(str(user["id"]), "user", str(u["id"]), miembros_user):
            nuevos += 1
        else:
            ya += 1
    if faltan:
        raise Fallo(f"el runtime no tiene a {', '.join(faltan)} de {org.name}: ¿se desplegó la organización?")
    informe.append(f"perfil User: {nuevos} usuario(s) añadidos, {ya} ya estaban")
    for nombre, roles in perfiles_propios(perfiles_dir):
        p = bonita.uno("portal/profile", name=nombre)
        if p is None and nombre in POR_DEFECTO:
            informe.append(f"perfil {nombre}: el runtime no lo tiene (no existe en esta edición); se omite")
            continue
        if p is None:
            informe.append(f"perfil {nombre}: el runtime no lo tiene (Community no admite perfiles propios; en "
                           f"Subscription, no se desplegó); sus roles "
                           f"({', '.join(roles)}) entran con el perfil User y el rol que reconoce cada módulo")
            continue
        nuevos = 0
        miembros_rol = bonita.miembros(str(p["id"]), "role")
        for rol in roles:
            r = bonita.uno("identity/role", name=rol)
            if r is None:
                raise Fallo(f"el runtime no tiene el rol {rol} del perfil {nombre}")
            nuevos += bonita.mapear(str(p["id"]), "role", str(r["id"]), miembros_rol)
        informe.append(f"perfil {nombre}: {nuevos} rol(es) añadidos de {len(roles)}")
    return informe


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Mapea la organización del proyecto a sus perfiles del portal (REST).")
    a.add_argument("--url", default=os.environ.get("BONITA_URL", "http://localhost:8080/bonita"))
    a.add_argument("--usuario", default=os.environ.get("BONITA_ADMIN_USUARIO"),
                   help="administrador técnico (por defecto BONITA_ADMIN_USUARIO)")
    a.add_argument("--clave-stdin", action="store_true",
                   help="lee la clave de la primera línea de la entrada estándar (si no, BONITA_ADMIN_CLAVE)")
    args = a.parse_args(argv)
    usuario = args.usuario
    clave = sys.stdin.readline().rstrip("\r\n") if args.clave_stdin else os.environ.get("BONITA_ADMIN_CLAVE")
    if not usuario or not clave:
        if (urllib.parse.urlsplit(args.url).hostname or "") not in LOCALES:
            print(f"FALLA: faltan las credenciales del administrador técnico de {args.url}: define "
                  "BONITA_ADMIN_USUARIO y BONITA_ADMIN_CLAVE (o pasa la clave con --clave-stdin). Las de desarrollo "
                  "(install/install) solo se usan contra un runtime local.", file=sys.stderr)
            return 2
        print(f"perfiles: sin BONITA_ADMIN_USUARIO/BONITA_ADMIN_CLAVE, uso las credenciales de desarrollo "
              f"{DESARROLLO[0]}/{DESARROLLO[1]} (solo contra localhost: el bundle de desarrollo)")
        usuario, clave = usuario or DESARROLLO[0], clave or DESARROLLO[1]
    try:
        org = organizacion()
    except SystemExit as e:
        print(e, file=sys.stderr)
        return 2
    bonita = Bonita(args.url)
    try:
        bonita.entrar(usuario, clave)
        try:
            informe = aplicar(bonita, org, APP / "profiles")
        finally:
            bonita.salir()
    except Fallo as e:
        print(f"FALLA: {e}", file=sys.stderr)
        return 1
    for linea in informe:
        print(f"perfiles: {linea}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
