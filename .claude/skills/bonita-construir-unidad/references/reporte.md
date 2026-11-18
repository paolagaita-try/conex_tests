# Reportar: evidencia, bitácora y cierre

Tres destinatarios, tres formatos: el **hub** recibe la evidencia de cada gate y la bitácora; la **persona** recibe el
reporte de cierre o de parada; el **PR** lleva el resumen de gates (plantilla en `gitflow.md`).

## Evidencia de un gate (`evidencia/<unidad>/<gate>.md`)

`evidencia/` está fuera de git (lo ignora la plantilla): el fichero viaja al hub con
`slice-ops.sh gate <gate> pass --evidence-file …`, que lo recorta a unos 2000 caracteres. Escribe un resumen
verificable, no un volcado:

```markdown
gate: journey_smoke · unidad U1 · rama feature/u1-datos-organizacion-y-procesos @ <sha corto>
- tools/arnes.sh verificar → 0 (check_inventario, check_expresiones, check_caminos, check_generados: verde)
- tools/arnes.sh journey → 0 · requests 42 · assertions 118 · fallos 0 · caminos: aprobada, rechazada, sin-saldo
- pendiente de prueba en Subscription: nada
- log completo: evidencia/U1/journey.txt
```

- Cada línea dice **qué comando, con qué resultado** (código de salida y cifras con su significado).
- `tdd` lleva las **dos** salidas, la roja y la verde, de los mismos casos y custodios.
- Un gate que no aplica: `no aplica: unidad sin formularios` (o sin contratos, o sin BDM) y por qué.
- Lo que solo se prueba en Subscription: la línea `pendiente de prueba en Subscription: …` (en `SUB`, items de wiring).
- Lo probado solo contra un doble (el mock de `mock.json`, el stub del hub) se dice como tal.

## Bitácora en el hub

- `slice-ops.sh progress «fase red cerrada: 3 caminos, 12 hallazgos esperados en verificar»` al cerrar cada fase o al
  encontrar algo que otro agente necesite saber.
- `slice-ops.sh checkpoint --note «green: generar = 0, faltan 2 caminos en el journey»` tras cada commit y antes de
  parar. Es lo que lee quien retome la unidad (`/bonita:resume`).

## A la persona

Manda el bloque «Cómo reportar» del `CLAUDE.md` (gana sobre cualquier otro formato). Lo propio de una unidad:

- **Al cerrar** (tras `archive`), sin decisión pendiente y todo verificado: dos líneas («Unidad U1 construida y en PR
  <url>: BDM y organización desplegados, journey verde. No necesito nada de ti.»). El merge lo decide la persona.
- **En cualquier otro caso** (parada, escalada, hueco del arnés, algo sin verificar), los seis puntos en su orden:
  1. **Lo que necesito de ti**: la decisión, con 2-3 opciones, su coste y tu recomendación (p. ej. ante un hueco:
     arreglar el arnés o cambiar la documentación).
  2. **Resumen**: qué unidad, hasta qué fase, si salió bien o mal.
  3. **Qué significa** para el proceso que se construye, sin jerga.
  4. **Riesgo ahora mismo**: ¿hay algo roto en `main` o desplegado? (en una rama abierta, normalmente no).
  5. **Qué cambió en disco**: rama, commits, si hay PR, y cómo se deshace (cerrar el PR y borrar la rama).
  6. **Pendiente o no verificado**: lo de Subscription, lo probado solo contra mocks o el stub, las pasadas del
     verificador usadas (1 o 2 de 2) y los huecos abiertos.
- La primera vez que uses un término interno (unidad, gate, DoR, wiring, journey), explícalo en media frase.
