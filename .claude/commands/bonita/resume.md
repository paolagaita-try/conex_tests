---
name: "BONITA: Resume"
description: Retoma el trabajo tras un reinicio de contexto — refresca la proyección desde el hub, cierra con micro-fase done un micro-work cuyo PR ya se mergeó, calcula la siguiente acción determinista (next-step) y la ejecuta, y deja un checkpoint.
category: Workflow
tags: [bonita, resume, rehydrate, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/resume.md (adaptado a Bonita y al modo servidor) -->

# /bonita:resume — Retomar sin pérdida

Reconstruye el contexto **desde fuera de la conversación**: el hub (o su caché local si no responde) y git.

## Pasos

1. **Refresca la proyección**:

   ```bash
   bash .claude/hooks/bonita/slice-ops.sh status
   ```

   Trae unidad o micro-work reclamado, fase, gates, wiring en `failing`, contexto, lease y cola pendiente. Salida
   `9` → este árbol no está registrado: la persona ejecuta `slice-ops.sh register` y vuelves.

2. **Si lo reclamado es un micro-work** (la salida empieza por `micro-work:`) y su fase es `pr`: mira si el PR ya se
   mergeó y, si sí, ciérralo.

   ```bash
   gh pr view <rama del micro-work> --json state,mergedAt,url
   bash .claude/hooks/bonita/slice-ops.sh micro-fase done      # solo si state = MERGED
   ```

   Si el PR sigue abierto, no cierres nada: dilo y espera al merge (lo decide una persona). Con un micro-work en
   otra fase (`claimed`, `in_progress`), continúa con su skill, `bonita-micro-cambio`, desde la rama y el checkpoint.

3. **Determina la siguiente acción** (para una unidad):

   ```bash
   bash .claude/hooks/bonita/slice-ops.sh next-step
   ```

   La prioridad es determinista y la calcula el cliente: pista de reanudación (`resume_hint`), items de wiring en
   `failing`, primer gate abierto por fase. **Ejecútala** siguiendo la skill `bonita-construir-unidad`. Antes,
   `git switch` a la rama del checkpoint y comprueba que `HEAD` es su commit o lo contiene.

4. **Lease perdido** (`⚠ lease`): `slice-ops.sh checkpoint --note …`, **detén** el trabajo y reclama de nuevo
   (`slice-ops.sh claim`) antes de cerrar nada más.

5. **Proyección `⚠ stale`** con el hub sin responder: sigue con lo que hay (sin conexión nunca bloquea) y no cierres
   gates a ciegas. Los códigos `5` y `6`: `skills/bonita-construir-unidad/references/ciclo-en-el-hub.md`.

6. **Deja el hito**:

   ```bash
   bash .claude/hooks/bonita/slice-ops.sh progress "retomado por /bonita:resume: <qué sigue>"
   ```

**Regla dura:** mientras quede un item de wiring en `failing`, la unidad no está terminada. Nunca marques `passing`
sin evidencia de una ejecución real (`--evidence-file`).
