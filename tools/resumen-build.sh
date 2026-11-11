#!/usr/bin/env bash
# Resumen de un build Maven para la evidencia (lo escriben tools/construir.sh y tools/run-journey.sh en
# evidencia/ultimo-build.txt): comando, código de salida, línea BUILD SUCCESS/FAILURE, tiempo, artefactos de
# bonita-project/app/target con su tamaño y dónde está el log completo. Nunca sale vacío: es la evidencia del item de
# wiring del build y el hub rechaza una evidencia vacía.
# Uso: tools/resumen-build.sh <código de salida> <log> <comando…>   (desde la raíz del proyecto; escribe en stdout)
set -uo pipefail
[ $# -ge 3 ] || { echo "uso: tools/resumen-build.sh <código> <log> <comando…>" >&2; exit 2; }
codigo="$1"; log="$2"; shift 2
echo "# Build Maven"
echo "comando: $*"
echo "código de salida: $codigo"
linea="$(grep -m1 -E 'BUILD (SUCCESS|FAILURE)' "$log" 2>/dev/null || true)"
echo "resultado: ${linea:-sin línea BUILD SUCCESS/FAILURE en el log}"
tiempo="$(grep -m1 -E 'Total time:' "$log" 2>/dev/null || true)"
[ -n "$tiempo" ] && echo "tiempo: $tiempo"
echo "artefactos (bonita-project/app/target):"
shopt -s nullglob
zips=(bonita-project/app/target/*.zip)
if [ "${#zips[@]}" -eq 0 ]; then
  echo "  (ninguno)"
else
  for z in "${zips[@]}"; do echo "  - $(basename "$z") ($(du -k "$z" | cut -f1) KB)"; done
fi
echo "log completo: $log ($( [ -f "$log" ] && wc -l < "$log" | tr -d ' ' || echo 0) líneas)"
