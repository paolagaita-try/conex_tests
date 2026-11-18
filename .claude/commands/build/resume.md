---
name: "BUILD: Resume"
description: Rehidrata el slice activo tras un reinicio de contexto — refresca la proyección desde el runtime (o reconcilia el fichero en modo legacy), muestra la continuidad y la siguiente acción determinista.
category: Workflow
tags: [build-harness, resume, rehydrate, trycore]
---

# /build:resume — Retomar sin pérdida

Objetivo: reconstruir el contexto de construcción **desde fuera de la conversación** — del
runtime en `dual`/`runtime`, del disco en `legacy`.

## Pasos

1. **Averigua el modo y refresca**:

   ```bash
   MODE="$(bash .claude/hooks/build/slice-ops.sh mode)"
   bash .claude/hooks/build/slice-ops.sh status
   ```

   - `legacy` → reconcilia el fichero como en v0.8.5: `python3 .claude/hooks/build/reconcile-build-state.py .claude/state/build-state.json`
     (degrada wiring sin evidencia; anota branch drift; fail-open) y sigue
     `building-a-slice/references/state-protocol.md`.
   - `dual|runtime` → `status` ya trae slice, fase, gates, wiring `failing`, contexto, lease y
     cola pendiente.

2. **Determina la siguiente acción**:

   ```bash
   bash .claude/hooks/build/slice-ops.sh next-step
   ```

   La prioridad es determinista y la calcula el cliente: `resume_hint` → items de wiring en
   `failing` → sub-slice pendiente → primer gate abierto por fase. **Ejecútala.**

3. **Si el `status` muestra `⚠ lease` (lease perdido)**: haz `slice-ops.sh checkpoint --note …`,
   **detén** el trabajo y vuelve a reclamar (`slice-ops.sh claim`) antes de cerrar nada más.

4. **Si el `status` muestra la proyección `⚠ stale`** (sin refrescar) y el runtime no responde:
   sigue trabajando con lo que hay — offline nunca bloquea — y no cierres gates a ciegas.

5. **Front paralelo**: si este worktree pertenece a un front, delega en la skill
   `managing-parallel-front`.

6. Deja el hito: `bash .claude/hooks/build/slice-ops.sh progress "retomado por /build:resume: <qué sigue>"`.

**Regla dura:** mientras quede un item `failing`, el slice NO está terminado. Nunca marques
`passing` sin evidencia de ejecución real (`--evidence-file`).
