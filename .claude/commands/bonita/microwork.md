---
name: "BONITA: Microwork"
description: Entrada directa al carril de micro-works en modo microwork — mantenimiento sin defecto (textos, configuración, documentación de construcción, una versión de dependencia ya permitida). Delega en la skill bonita-micro-cambio sin pasar por el router. Es ENTRADA, no política.
category: Workflow
tags: [bonita, microwork, micro-work, carril-ligero, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/microwork.md (adaptado a Bonita y a los micro-works del hub) -->

**Entrada directa al carril de micro-works, modo microwork.** Para el mantenimiento que **no es un defecto**: un
texto, un valor de configuración, `docs/08-construccion/`, una versión de dependencia ya permitida. No pasa por
`/bonita:work` ni abre unidad, change, DoR o gates. Si algo aquí contradice el bloque del arnés en `CLAUDE.md`, gana
`CLAUDE.md`.

**Entrada:** la descripción del cambio de mantenimiento.

## 1. Preflight

```bash
test -f .claude/.bonita-harness.json || echo "NOT_INSTALLED"
bash .claude/hooks/bonita/slice-ops.sh status
```

`NOT_INSTALLED` → `trycore-bonita init`. Salida `9` → la persona registra este árbol (`slice-ops.sh register`).

## 2. Unidad activa y compuerta por criterio

- Si hay una unidad activa en este árbol, el micro-work va en **otro worktree registrado**, en `chore/<slug>` o
  `fix/<slug>` desde `main`, nunca en la rama de la unidad.
- Si el comportamiento que vas a cambiar está **cubierto por un criterio, un camino o una regla** escritos, esto
  **no** es microwork: si el cambio lo hace cumplir, es `/bonita:bugfix`; si lo **contradice**, es un cambio de
  requisito del arnés de documentación y se escala. Sin nada que lo cubra (texto, configuración, documentación de
  construcción), sigue aquí.

## 3. Reclamar y delegar

```bash
bash .claude/hooks/bonita/slice-ops.sh claim
```

Salida `micro-work:` → es tuyo; `7` → pide a la persona que lo dé de alta en el hub (título, tipo, ficheros,
límites) y no hagas el cambio fuera de él.

Invoca la skill **`bonita-micro-cambio`** en **modo microwork**: cambio acotado en la fuente (y
`tools/arnes.sh generar` si toca), verificación, prueba solo si cambia comportamiento (validada por reversión),
`tools/arnes.sh verificar` = 0 y journey verde, PR a `main` indicando qué límite **no** cruza.

## 3b. Proyecto en modo existente

Si `.trycore-bonita.json` dice `modo: "existente"`, el cambio documentado sobre lo existente (BDM, contrato, tarea o
proceso nuevo) **no** escala por eso: sigue `skills/bonita-micro-cambio/references/modo-existente.md` (`mapa`, leer
`docs/07-bonita/cambios.md`, `cambios mostrar`, pedir a la persona que ejecute `tools/arnes.sh cambios confirmar` en su propia terminal, `generar`,
`verificar`, `mvn clean install`, `linea-base actualizar --micro-work <id>`). El agente nunca responde la confirmación.
Se cierra sin journey. Siguen escalando una dependencia nueva, un módulo de la plantilla ausente y un cambio que la
documentación no describe.

## 4. Señales de escalada

```bash
bash .claude/hooks/bonita/slice-ops.sh micro-escalar --motivo "<razón>" [--limite sin_dependencia_nueva|sin_endpoint_publico_nuevo|sin_cambio_de_dominio]
```

Sin `--limite` si lo que desborda es el alcance (más de 3 ficheros de documentación, varias preocupaciones).

## Guardrails

- **Solo entrada.** Solo `micro-fase`, `micro-checkpoint` y `micro-escalar`.
- **Comportamiento cubierto por un criterio, un camino o una regla ⇒ no es microwork.** No uses este carril para
  esquivar el ancla al requisito.
