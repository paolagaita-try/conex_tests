#!/usr/bin/env bash
# Espera hasta que la REST API de Bonita acepte el login técnico. Uso: tools/esperar-api.sh [base] [segundos]
set -uo pipefail
BASE="${1:-http://localhost:8095/bonita}"; MAX="${2:-600}"
for ((t = 0; t < MAX; t += 5)); do
  codigo=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/loginservice" -d 'username=install&password=install&redirect=false' || true)
  if [ "$codigo" = "204" ]; then echo "REST API lista tras ${t} s"; exit 0; fi
  sleep 5
done
echo "FALLA: la REST API no respondió en ${MAX} s"; exit 1
