#!/usr/bin/env bash
# Construye el proyecto Bonita con Maven (sin Studio) y comprueba que sale un único application archive.
set -euo pipefail
cd "$(dirname "$0")/.."
# Bonita 2026.2 se construye con JDK 17; Maven de Homebrew trae JDK 27 por defecto.
export JAVA_HOME="${BONITA_JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
if ! "$JAVA_HOME/bin/java" -version 2>&1 | grep -q '"17'; then
  echo "FALLA: JAVA_HOME no es JDK 17 ($JAVA_HOME). Define BONITA_JAVA_HOME."; exit 1
fi
mkdir -p evidencia
# Primero los formularios Svelte (el mismo paso y la misma guarda de zips que usa run-journey.sh).
tools/frontend.sh || exit 1
# Log completo en evidencia/ultimo-build.log y su resumen (nunca vacío) en evidencia/ultimo-build.txt.
log="evidencia/ultimo-build.log"
BUILD=(mvn -f bonita-project/pom.xml -B clean install "$@")
estado=0
"${BUILD[@]}" >"$log" 2>&1 || estado=$?
bash tools/resumen-build.sh "$estado" "$log" "${BUILD[@]}" > evidencia/ultimo-build.txt
if [ "$estado" != 0 ]; then
  echo "FALLA: mvn package (ver $log)"; tail -25 "$log"; exit 1
fi
shopt -s nullglob
zips=(bonita-project/app/target/*.zip)
if [ "${#zips[@]}" -ne 1 ]; then
  echo "FALLA: se esperaba 1 zip en bonita-project/app/target, hay ${#zips[@]}"; exit 1
fi
echo "OK: ${zips[0]}"
