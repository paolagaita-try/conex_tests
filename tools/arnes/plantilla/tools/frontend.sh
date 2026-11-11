#!/usr/bin/env bash
# Construye los formularios Svelte (si hay frontend/package.json) y comprueba que cada formulario de negocio, cada
# página propia y cada tema del manifiesto (`tipo` negocio, pagina o tema) tiene su zip. Lo usan `construir.sh` y `run-journey.sh`: es la única definición de este paso.
# Maven no compila el frontend: copia a la aplicación los zips que encuentre en frontend/dist-zips/ (app/pom.xml,
# `copy-form-pages`). Por eso dist-zips/ se vacía antes del build (el zip de un formulario quitado no puede viajar) y
# se para aquí, antes de Maven, si falta uno de esos (si no, el portal no abriría la tarea, la aplicación no tendría su
# página o no instalaría su tema).
# Log en evidencia/ultimo-frontend.log.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f frontend/package.json ] || exit 0
mkdir -p evidencia
rm -rf frontend/dist-zips
estado=0
(cd frontend && npm ci && npm run build:all) > evidencia/ultimo-frontend.log 2>&1 || estado=$?
[ "$estado" = 0 ] || { tail -40 evidencia/ultimo-frontend.log; echo "FALLA: build del frontend (npm ci && npm run build:all en frontend/)"; exit 1; }
if [ -f frontend/forms.manifest.json ]; then
  faltan=$(python3 -c '
import json, pathlib
m = json.load(open("frontend/forms.manifest.json", encoding="utf-8"))
for f in m.get("formularios", []):
    if f.get("tipo") in ("negocio", "pagina", "tema") and not pathlib.Path("frontend/dist-zips", f["custompage"] + ".zip").is_file():
        print(f["custompage"] + ".zip")
') || { echo "FALLA: no pude leer frontend/forms.manifest.json"; exit 1; }
  if [ -n "$faltan" ]; then
    echo "FALLA: faltan en frontend/dist-zips/ los zips de formularios de negocio, páginas o temas del manifiesto:"
    echo "$faltan" | sed 's/^/  /'
    exit 1
  fi
fi
