"""Configuraciones por entorno embebidas en el `.proc`. Bonita guarda la configuración Local en
`process_configurations/<id del pool>.conf`; las demás (Qualification, Production) van dentro del `.proc` como
`configurations` del pool (`AbstractProcess.configurations` de process.ecore, clase `Configuration` de
configuration.ecore; doc `process/managing-dependencies`: «configurations embedded in .proc files (Qualification,
Production, etc.)»). Sin ellas, `-Dbonita.environment=Qualification` construye un `.bar` sin mapeo de actores ni
parámetros (avisos «qualification configuration not found» y «No actor mapping found» del Plan 1).

El contenido es el mismo que el del `.conf`: se reutiliza `generar_conf`."""
from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET

from generadores.escribir.proc.ids import XMI_ID
from generadores.xmlutil import Ids

LOCAL = "Local"
ENTORNOS = ("Qualification", "Production")
NOMBRE_ENTORNO = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def entornos(proceso: dict) -> list[str]:
    """Entornos embebidos: Qualification y Production, más cualquier otro (no Local) con valores en un parámetro."""
    extra: list[str] = []
    for p in proceso.get("parametros", []):
        for e in (p.get("valores") or {}):
            if not NOMBRE_ENTORNO.fullmatch(e):
                raise ValueError(f"el parámetro {p.get('nombre')} del proceso {proceso.get('nombre')} tiene el entorno "
                                 f"«{e}» con un nombre no válido (letra inicial y solo letras, cifras, «_» o «-»)")
            if e != LOCAL and e not in ENTORNOS and e not in extra:
                extra.append(e)
    return [*ENTORNOS, *extra]


def configuraciones(pool: ET.Element, proceso: dict, organizacion: dict, ids: Ids,
                    version_bonita: str = "2026.2", extensiones: dict | None = None) -> None:
    """Añade al pool un `configurations` por entorno distinto de Local, con actorMappings, definitionMappings,
    processDependencies y parameters del entorno. Falla si un parámetro no tiene valor en alguno."""
    from generadores.escribir.conf import generar_conf  # import tardío: conf importa módulos de este paquete

    for entorno in entornos(proceso):
        conf = generar_conf(proceso, organizacion, entorno, version_bonita, extensiones).getroot()
        c = ET.SubElement(pool, "configurations")
        c.set(XMI_ID, ids.siguiente())
        c.set("name", conf.get("name"))
        c.set("version", conf.get("version"))
        for hijo in conf:
            c.append(copy.deepcopy(hijo))
