---
name: "BONITA: Unidad"
description: Punto de entrada del loop de la unidad. Reclama (con preferencia si das un código como U1) o continúa una unidad del plan de construcción Bonita y delega en la skill bonita-construir-unidad el recorrido dor, change, red, green, refactor, smoke, api, data, dod, pr, archived. No reimplementa el loop.
category: Workflow
tags: [bonita, unidad, inner-loop, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/slice.md (adaptado a Bonita y al modo servidor) -->

Adaptador delgado: **no reimplementa** el loop. Lo conduce la skill **`bonita-construir-unidad`**; los changes, los
comandos `/opsx:*`; los veredictos independientes, los agentes `bonita-*`. Si algo aquí contradice el bloque del
arnés en `CLAUDE.md`, gana `CLAUDE.md`.

**Entrada:** opcional, el código de una unidad (`U0`…`U4`, `E-<familia>`, `S-<subproceso>`, `SUB`). Con código, es una
**preferencia**: el hub la honra si la unidad está lista; si entrega otra, dice por qué y se trabaja la entregada.

## 1. Preflight

```bash
test -f .claude/.bonita-harness.json || echo "NOT_INSTALLED"
trycore-bonita doctor
bash .claude/hooks/bonita/slice-ops.sh status
```

- `NOT_INSTALLED` → `trycore-bonita init` y vuelve. `doctor` en 1 → arregla lo que diga o para y pregunta.
- Salida `9` → el árbol no está registrado: lo hace la persona con `slice-ops.sh register`.
- Sin proyecto o sin grafo en `status`, o el plan `docs/08-construccion/plan.md` no existe → `/bonita:onboard`.

## 2. Reclamar o continuar

```bash
bash .claude/hooks/bonita/slice-ops.sh claim                  # la siguiente unidad lista
bash .claude/hooks/bonita/slice-ops.sh claim --unidad U1      # con preferencia, si se dio código
bash .claude/hooks/bonita/slice-ops.sh next-step              # si ya hay una unidad activa
```

- Ya hay una unidad reclamada en este árbol → no reclames otra (una unidad activa a la vez): continúa con
  `next-step` o `/bonita:resume`.
- `7` → no hay trabajo: dilo en una línea y termina limpio.
- La salida empieza por `micro-work:` → no es una unidad: sigue `bonita-micro-cambio`.
- `CHECKPOINT:` presente → continúa desde esa rama y ese commit; jamás reinicies.
- Los códigos `5`, `6` y `9` y el lease: `skills/bonita-construir-unidad/references/ciclo-en-el-hub.md`.

## 3. Conducir el loop (delegar)

Invoca la skill **`bonita-construir-unidad`** desde el Paso 2 (rama y componentes). El orden de fases es estricto y un
gate no se salta; la verificación independiente (hasta 2 pasadas) y el DoD los dan los agentes `bonita-*`. Para
trabajo multi-unidad en una sola sesión, el agente `bonita-orquestador`.

## 4. Resumen

Reporta con el formato «Cómo reportar» del bloque del arnés en `CLAUDE.md`: fase actual, gates cerrados y abiertos,
lo no verificado (incluido lo «pendiente de prueba en Subscription») y la siguiente acción. El merge del PR lo decide
una persona.

## Guardrails

- **Una unidad activa.** Un gate no se salta. El journey nunca queda en rojo al cerrar una fase.
- **Todo cambio de estado va por `slice-ops.sh`**, nunca a mano; `.claude/state/` y `.claude/hub-context/` no se editan.
- **Producto completo**: recortar o diferir alcance es `slice-ops.sh escalate`, nunca una decisión del modelo.
