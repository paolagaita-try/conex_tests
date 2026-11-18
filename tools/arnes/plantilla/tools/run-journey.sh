#!/usr/bin/env bash
# Journey contra el bundle Tomcat + H2 nativo (perfil Maven `bundle`, como el proyecto piloto): sin Docker
# ni emulación amd64. Construye los formularios Svelte (si hay frontend/package.json) y después el bundle, lo extrae
# limpio en cada corrida (H2 nueva), lo levanta en $PORT, corre Newman y las pruebas e2e de los
# formularios (Playwright, si hay frontend/e2e/*.spec.ts) y lo para. Tras arrancar, el paso posterior al despliegue
# `tools/perfiles.py` (el de `tools/arnes.sh perfiles`) mapea la organización al perfil User: un artefacto Community
# no lo puede llevar. La semilla del módulo de parámetros no necesita paso propio: la aplican la API en su primera
# invocación tras el despliegue y `ParametrosDeProceso.usar` en el primer uso desde un script (D-113).
# Uso: tools/run-journey.sh [--sin-build] [--mantener] [--coleccion <ruta>] [-- <opciones extra de newman>]
# La colección por defecto es hola/hola.postman_collection.json (relativa a la raíz del proyecto).
# Si la colección declara la variable `smtpUrl` (algún camino con «Correos esperados»), levanta antes de Newman el SMTP
# de prueba (`tools/arnes/herramientas/smtp_prueba.py`, o el de $SMTP_PRUEBA) en $SMTP_PUERTO (2525: el
# `param_smtpPuerto` de Local) con su HTTP de consulta en $SMTP_HTTP_PUERTO (8025), y le pasa `--env-var smtpUrl=…`.
set -euo pipefail
cd "$(dirname "$0")/.."
SIN_BUILD=0; MANTENER=0; EXTRA=(); COLECCION="hola/hola.postman_collection.json"
while [ $# -gt 0 ]; do
  case "$1" in
    --sin-build) SIN_BUILD=1 ;;
    --mantener) MANTENER=1 ;;
    --coleccion) [ $# -ge 2 ] || { echo "--coleccion necesita una ruta"; exit 2; }; COLECCION="$2"; shift ;;
    --) shift; EXTRA=("$@"); break ;;
    *) echo "opción desconocida: $1"; exit 2 ;;
  esac
  shift
done
NOMBRE=$(python3 -c 'import json; print(json.load(open(".trycore-bonita.json"))["nombre"])') \
  || { echo "FALLA: no pude leer el nombre de .trycore-bonita.json"; exit 1; }
PORT="${PORT:-8096}"; SHUTDOWN=$((PORT + 10000))
BASE="http://localhost:$PORT/bonita"
export JAVA_HOME="${BONITA_JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"

# El puerto tiene que estar libre: si no, el journey hablaría con otro runtime y saldría verde midiendo otra cosa.
for p in "$PORT" "$SHUTDOWN"; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN -t >/dev/null 2>&1; then echo "FALLA: el puerto $p está ocupado"; exit 1; fi
done

# SMTP de prueba (R-15): solo si la colección lo usa. Se comprueba aquí, antes del build, que se puede levantar.
SMTP=0
SMTP_PUERTO="${SMTP_PUERTO:-2525}"; SMTP_HTTP_PUERTO="${SMTP_HTTP_PUERTO:-8025}"
SMTP_PRUEBA="${SMTP_PRUEBA:-tools/arnes/herramientas/smtp_prueba.py}"
if [ -f "$COLECCION" ] && python3 - "$COLECCION" <<'PY'
import json, sys
variables = json.load(open(sys.argv[1], encoding="utf-8")).get("variable", [])
sys.exit(0 if any(v.get("key") == "smtpUrl" for v in variables) else 1)
PY
then
  SMTP=1
  [ -f "$SMTP_PRUEBA" ] || { echo "FALLA: el journey espera correos y no está el SMTP de prueba ($SMTP_PRUEBA; SMTP_PRUEBA=<ruta>)"; exit 1; }
  for p in "$SMTP_PUERTO" "$SMTP_HTTP_PUERTO"; do
    if lsof -nP -iTCP:"$p" -sTCP:LISTEN -t >/dev/null 2>&1; then echo "FALLA: el puerto $p (SMTP de prueba) está ocupado"; exit 1; fi
  done
fi

if [ "$SIN_BUILD" = 0 ]; then
  mkdir -p evidencia
  # Primero los formularios Svelte y la guarda de sus zips (tools/frontend.sh, el mismo paso que usa construir.sh).
  tools/frontend.sh || exit 1
  # Log completo en evidencia/ultimo-build.log y su resumen (nunca vacío) en evidencia/ultimo-build.txt: la
  # evidencia del build que citan los gates y el wiring de U0.
  BUILD=(mvn -f bonita-project/pom.xml -B clean install -Pbundle)
  estado_build=0
  "${BUILD[@]}" > evidencia/ultimo-build.log 2>&1 || estado_build=$?
  bash tools/resumen-build.sh "$estado_build" evidencia/ultimo-build.log "${BUILD[@]}" > evidencia/ultimo-build.txt
  [ "$estado_build" = 0 ] || { tail -40 evidencia/ultimo-build.log; echo "FALLA: build -Pbundle"; exit 1; }
fi
zips=(bonita-project/app/target/*-local-bundle.zip)
[ "${#zips[@]}" = 1 ] && [ -f "${zips[0]}" ] || { echo "FALLA: se esperaba un solo *-local-bundle.zip"; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/$NOMBRE-bundle.XXXX")
unzip -q "${zips[0]}" -d "$WORK"
START=$(find "$WORK" -maxdepth 2 -name start-bonita.sh | head -1)
[ -n "$START" ] || { echo "FALLA: el bundle no trae start-bonita.sh"; exit 1; }
DIR=$(dirname "$START")
sed -i.orig -e "s/port=\"8080\"/port=\"$PORT\"/" -e "s/port=\"8005\"/port=\"$SHUTDOWN\"/" "$DIR/server/conf/server.xml"
grep -q "port=\"$PORT\"" "$DIR/server/conf/server.xml" || { echo "FALLA: no pude cambiar el puerto"; exit 1; }

parar() {
  if [ "$MANTENER" = 1 ]; then echo "runtime vivo en $BASE ($DIR)"; return; fi
  (cd "$DIR" && bash stop-bonita.sh >/dev/null 2>&1) || true
  for _ in $(seq 1 30); do lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1 || break; sleep 2; done
  pid=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)
  if [ -n "$pid" ] && ps -o command= -p "$pid" | grep -qF "$WORK"; then kill "$pid" || true; fi
  rm -rf "$WORK"
}
trap parar EXIT

# Reglas dinámicas (R-14): solo en bundles Subscription (en Community las omite con un aviso). Decide la edición del
# bundle local (`edicion_desarrollo`), no la de destino. Con reglas desplegadas el bundle arranca con las
# comprobaciones dinámicas activas; sin ellas, como siempre (false).
DINAMICO=$(python3 tools/reglas.py --desarrollo --bundle "$(dirname "$START")/setup/platform_conf/initial") || exit 1
[ "$DINAMICO" = true ] || DINAMICO=false

inicio=$(date +%s)
(cd "$DIR" && nohup env BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=$DINAMICO bash start-bonita.sh -Dh2.noconfirm \
  > "$WORK/stdout.log" 2>&1 &)
tools/esperar-api.sh "$BASE" 300 || { tail -60 "$DIR/server/logs/bonita"*.log 2>/dev/null; exit 1; }
echo "arranque del bundle: $(( $(date +%s) - inicio )) s"

# El mismo paso que se corre tras desplegar en cualquier entorno (tools/arnes.sh perfiles): idempotente.
python3 tools/perfiles.py --url "$BASE" || { echo "FALLA: el mapeo de perfiles tras el despliegue"; exit 1; }

SMTP_VARS=()
if [ "$SMTP" = 1 ]; then
  mkdir -p evidencia
  python3 "$SMTP_PRUEBA" --smtp-puerto "$SMTP_PUERTO" --http-puerto "$SMTP_HTTP_PUERTO" > evidencia/smtp-prueba.log 2>&1 &
  SMTP_PID=$!
  parar_smtp() { kill "$SMTP_PID" 2>/dev/null || true; wait "$SMTP_PID" 2>/dev/null || true; }
  trap 'parar_smtp; parar' EXIT
  for _ in $(seq 1 50); do
    curl -sf "http://127.0.0.1:$SMTP_HTTP_PUERTO/salud" >/dev/null 2>&1 && break
    kill -0 "$SMTP_PID" 2>/dev/null || { cat evidencia/smtp-prueba.log; echo "FALLA: el SMTP de prueba no arrancó"; exit 1; }
    sleep 0.2
  done
  curl -sf "http://127.0.0.1:$SMTP_HTTP_PUERTO/salud" >/dev/null 2>&1 \
    || { cat evidencia/smtp-prueba.log; echo "FALLA: el SMTP de prueba no responde en $SMTP_HTTP_PUERTO"; exit 1; }
  echo "SMTP de prueba en 127.0.0.1:$SMTP_PUERTO (mensajes en http://127.0.0.1:$SMTP_HTTP_PUERTO/mensajes)"
  SMTP_VARS=(--env-var "smtpUrl=http://127.0.0.1:$SMTP_HTTP_PUERTO")
fi

npx --no-install newman run "$COLECCION" --bail \
  --env-var "baseUrl=$BASE" ${SMTP_VARS[@]+"${SMTP_VARS[@]}"} ${EXTRA[@]+"${EXTRA[@]}"}

# Después de Newman, los formularios en un navegador real contra el mismo runtime (si el proyecto trae pruebas e2e).
# La globalSetup de Playwright vuelve a pasar tools/perfiles.py (idempotente) por si el runtime se levantó a mano.
if compgen -G "frontend/e2e/*.spec.ts" >/dev/null; then
  PORT="$PORT" WORKDIR_ESPERADO="$WORK" tools/playwright.sh
fi
