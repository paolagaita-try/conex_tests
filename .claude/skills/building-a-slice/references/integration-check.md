# Runner de integración fuera-de-chat (`integration-check`)

Gate determinista que cierra `journey_smoke` **ejecutando**, no por inspección. Lleva el patrón del
gate fuera-de-chat (como `tools/loop/gateway-check.sh` de un consumidor) al **inner-loop manual**, no
solo al autónomo. **No crea ningún gate nuevo**: alimenta el `journey_smoke` existente del slice. El
gate `integration` con dependencias reales sigue siendo del **Release Gate** (outer loop).

## Por qué fuera de chat y en contexto virgen
- El cableado end-to-end **se ejecuta** (build + suite + journey), no se "razona". Un script lo hace
  reproducible y barato en contexto.
- Quien escribió el código **no es buen juez** de su propio cableado: corre el runner en una
  **sesión/contexto virgen** (o como paso de CI) y entra al **fix-loop** (corre → lee el reporte →
  arregla → repite) hasta verde.

## Cómo adoptarlo
1. Copia `templates/integration-check.sh.template` a tu repo (p.ej. `tools/loop/integration-check.sh`)
   y hazlo ejecutable (`chmod +x`).
2. **Adapta** los comandos marcados `# ADAPTA` a tu stack (build, suite, e2e). El arnés es agnóstico:
   el template trae defaults de Node como punto de partida.
3. Córrelo en la fase `smoke`. Salida **0 = verde** (puedes marcar `journey_smoke: true`), **≠0 = rojo**.
   El reporte queda en `.claude/state/integration-report.txt`.
4. Mientras la suite no esté verde y el journey no camine end-to-end, `journey_smoke` queda `false`.

## Relación con el cableado fino
Cada paso verde del runner es la **evidence** que permite pasar items de `wiring_checklist[]` de
`failing` a `passing` (ver `state-protocol.md`). El `wiring-adversarial-verifier` (fase `dod`) revisará
después que esa evidencia sea real.
