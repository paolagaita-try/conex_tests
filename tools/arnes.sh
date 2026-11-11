#!/usr/bin/env bash
# arnes.sh — punto de entrada del arnés Bonita dentro del proyecto (instalado en tools/arnes.sh).
#   tools/arnes.sh generar|verificar     generadores y custodios de tools/arnes/ (código de salida tal cual)
#   tools/arnes.sh mapa                  modo existente: regenera el mapa de lo existente (docs/07-bonita/existente/)
#   tools/arnes.sh cambios mostrar|confirmar
#                                        modo existente: clasificación de cambios.md; la confirmación la responde una
#                                        persona en su terminal
#   tools/arnes.sh linea-base actualizar --micro-work <id>
#                                        modo existente: cierra el micro-cambio (archiva su documentación y el
#                                        resultado pasa a ser la nueva línea base)
#   tools/arnes.sh journey [opciones]    journey completo; las opciones pasan a tools/run-journey.sh
#   tools/arnes.sh perfiles [--url URL]  tras desplegar: usuarios de la organización al perfil User y roles de cada
#                                        perfil propio a su perfil, por REST (tools/perfiles.py; idempotente);
#                                        credenciales por BONITA_ADMIN_USUARIO / BONITA_ADMIN_CLAVE o --clave-stdin
#   tools/arnes.sh studio [opciones]     lleva el proyecto al Bonita Studio: build, copia espejo que el Studio clona
#                                        (../<nombre>-studio) y, con el Studio abierto, REST API, páginas, aplicaciones,
#                                        perfiles y permisos en su motor local (tools/studio.py; idempotente)
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARNES="$RAIZ/tools/arnes"

uso() { echo "uso: tools/arnes.sh generar|verificar|mapa|cambios mostrar|cambios confirmar|linea-base actualizar --micro-work <id>|journey|perfiles|studio [opciones]" >&2; }
[ $# -ge 1 ] || { uso; exit 2; }
cmd="$1"; shift

if [ ! -d "$ARNES/generadores" ]; then
  echo "FALLA: no está tools/arnes/generadores. Instala el arnés con: trycore-bonita init" >&2
  exit 2
fi

case "$cmd" in
  generar|verificar|mapa|cambios|linea-base)
    cd "$RAIZ"
    # `cambios` y `linea-base` llevan una acción antes del proyecto (`cambios confirmar .`) y `linea-base` además sus
    # opciones (`--micro-work x`); el código de salida pasa tal cual.
    accion=()
    case "$cmd" in cambios|linea-base) accion=("${1:-}"); [ $# -eq 0 ] || shift ;; *) set -- ;; esac
    # Sin __pycache__ dentro de tools/arnes/: no está en el manifiesto (uninstall no lo quitaría) y `git add -A` lo versionaría.
    # Windows/MSYS: python3 nativo no entiende PYTHONPATH en formato /c/...; se convierte a C:/... con cygpath.
    PP="$ARNES"; command -v cygpath >/dev/null 2>&1 && PP="$(cygpath -m "$ARNES")"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" exec python3 -m generadores "$cmd" ${accion[@]+"${accion[@]}"} . "$@"
    ;;
  journey)
    cd "$RAIZ"
    NOMBRE=$(python3 -c 'import json; print(json.load(open(".trycore-bonita.json"))["nombre"])') \
      || { echo "FALLA: no pude leer el nombre de .trycore-bonita.json" >&2; exit 2; }
    COLECCION="journey/$NOMBRE.postman_collection.json"
    [ -f "$COLECCION" ] || COLECCION="hola/hola.postman_collection.json"
    MOCK_PID=""
    parar_mock() {
      if [ -n "$MOCK_PID" ]; then kill "$MOCK_PID" 2>/dev/null || true; wait "$MOCK_PID" 2>/dev/null || true; fi
    }
    trap parar_mock EXIT
    if [ -f mock.json ]; then
      MOCK_PUERTO="${MOCK_PUERTO:-8099}"
      python3 "$ARNES/herramientas/mock_http.py" --puerto "$MOCK_PUERTO" --rutas mock.json >/dev/null 2>&1 &
      MOCK_PID=$!
      for _ in $(seq 1 50); do
        (exec 3<>"/dev/tcp/127.0.0.1/$MOCK_PUERTO") 2>/dev/null && break
        kill -0 "$MOCK_PID" 2>/dev/null || { echo "FALLA: el mock no arrancó" >&2; exit 1; }
        sleep 0.2
      done
      (exec 3<>"/dev/tcp/127.0.0.1/$MOCK_PUERTO") 2>/dev/null || { echo "FALLA: el mock no escucha en $MOCK_PUERTO" >&2; exit 1; }
    fi
    estado=0
    tools/run-journey.sh --coleccion "$COLECCION" "$@" || estado=$?
    exit "$estado"
    ;;
  perfiles|studio)
    cd "$RAIZ"
    # La copia del arnés instalado (tools/arnes/plantilla/tools/, al día con `trycore-bonita update`) sobre este
    # proyecto; si no está, la del proyecto (la que trajo su plantilla).
    SCRIPT="$ARNES/plantilla/tools/$cmd.py"
    [ -f "$SCRIPT" ] || SCRIPT="tools/$cmd.py"
    [ -f "$SCRIPT" ] || { echo "FALLA: falta tools/$cmd.py; reinstala el arnés con: trycore-bonita update" >&2; exit 2; }
    TRYCORE_PROYECTO="$RAIZ" PYTHONDONTWRITEBYTECODE=1 exec python3 "$SCRIPT" "$@"
    ;;
  *) uso; exit 2 ;;
esac
