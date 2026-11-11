#!/usr/bin/env bash
# Extrae los VISUAL_ID de las clases *EditPart del jar del editor de diagramas del Studio.
# Uso: ids_visuales.sh <ruta-jar> > conocimiento/ids-visuales-2026.2.json
# Salida: JSON determinista (claves ordenadas). Compatible con bash 3.2 (macOS).
set -euo pipefail

JAR="${1:?uso: ids_visuales.sh <ruta-jar-diagram>}"
JAVA_HOME="${BONITA_JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
STUDIO="${STUDIO_VERSION:-2026.2-u3}"
PAQUETE="org/bonitasoft/studio/model/process/diagram/edit/parts"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
unzip -q -o "$JAR" "$PAQUETE/*EditPart.class" -d "$TMP"

PARES="$TMP/pares.txt"
: > "$PARES"
for clase in "$TMP/$PAQUETE"/*EditPart.class; do
  nombre="$(basename "$clase" .class)"
  valor="$("$JAVA_HOME/bin/javap" -constants -cp "$TMP" "${PAQUETE//\//.}.$nombre" \
    | sed -n 's/.*[ ]VISUAL_ID = \([0-9][0-9]*\);.*/\1/p' | head -n 1)"
  [ -n "$valor" ] && printf '%s %s\n' "${nombre%EditPart}" "$valor" >> "$PARES"
done

python3 -I - "$PARES" "$STUDIO" "$(basename "$JAR")" <<'PY'
import json, sys
pares, studio, plugin = sys.argv[1:4]
ids = {}
for linea in open(pares, encoding="utf-8"):
    k, v = linea.split()
    ids[k] = int(v)
print(json.dumps({"studio": studio, "plugin": plugin, "ids": ids}, indent=2, sort_keys=True, ensure_ascii=False))
PY
