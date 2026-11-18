#!/usr/bin/env bash
# Pruebas e2e de los formularios con Playwright (chromium) contra el runtime ya levantado en $PORT. Lo llama
# `run-journey.sh` después de Newman, con WORKDIR_ESPERADO = la carpeta del bundle (la globalSetup comprueba que quien
# escucha el puerto es ese runtime y no otro). Informe en frontend/playwright-report/ y vídeos en frontend/test-results/
# (ignorados por git).
# El navegador NO se descarga aquí: bajar cientos de MB a escondidas dentro de un journey es sorpresa y rompe en
# máquinas sin red. Si falta, se dice cómo instalarlo (una vez por máquina) y se falla.
set -euo pipefail
cd "$(dirname "$0")/../frontend"
if [ ! -d node_modules/@playwright/test ]; then
  echo "FALLA: faltan las dependencias del frontend; corre 'npm ci' en frontend/"; exit 1
fi
chromium=$(node -e "console.log(require('@playwright/test').chromium.executablePath())" 2>/dev/null || true)
if [ -z "$chromium" ] || [ ! -x "$chromium" ]; then
  echo "FALLA: falta el navegador chromium de Playwright; instálalo una vez con: cd frontend && npx playwright install chromium"
  exit 1
fi
npx --no-install playwright test
