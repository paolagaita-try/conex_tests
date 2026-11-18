#!/usr/bin/env bash
# Extrae los .ecore del modelo EMF del Studio instalado a .cache/modelo-studio/ (ignorado por git).
# Son la referencia de cada atributo del .proc. Uso: extraer_modelo_studio.sh [ruta-jar]
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PLUGINS="${STUDIO_PLUGINS:-/Applications/BonitaStudioSubscription-2026.2-u3.app/Contents/Eclipse/plugins}"
JAR="${1:-$PLUGINS/org.bonitasoft.bpm.model_9.0.10.jar}"
DESTINO="$RAIZ/.cache/modelo-studio"

mkdir -p "$DESTINO"
unzip -q -o -j "$JAR" '*.ecore' -d "$DESTINO"
ls "$DESTINO"/*.ecore
