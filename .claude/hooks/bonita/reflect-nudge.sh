#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/reflect-nudge.sh
# reflect-nudge.sh — Stop.
# Ciclo autocorrectivo (reflexión post-unidad): NUNCA bloquea el cierre de sesión. Sugiere
# /bonita:reflect SOLO si el hub dice que hay unidades archivadas sin reflexionar. El cómputo lo
# hace el hub sobre TODO el proyecto (no este clon); aquí solo se renderiza su nudge. El
# razonamiento (qué se aprendió) lo hace el MODELO en /bonita:reflect.
# Cambios sobre el original: sin el camino con fichero de estado local (modo servidor siempre).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/projection.sh"

command -v python3 >/dev/null 2>&1 || exit 0   # fail-open: jamás impide cerrar sesión

# Mensaje a STDOUT: un Stop hook con exit 0 no bloquea el cierre; `2>/dev/null` suprime solo trazas.
projection_get nudges '[]' | python3 -c 'import json,sys
try: ns=json.load(sys.stdin)
except Exception: ns=[]
for n in (ns if isinstance(ns,list) else []):
    if isinstance(n,dict) and n.get("kind")=="reflect" and n.get("message"):
        print("💡 "+n["message"])
        print("   Ejecuta /bonita:reflect para proponer convenciones aprendidas (se aplican tras tu aprobación).")' 2>/dev/null
exit 0
