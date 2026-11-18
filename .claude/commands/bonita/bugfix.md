---
name: "BONITA: Bugfix"
description: Entrada directa al carril de micro-works en modo bugfix — un comportamiento observado viola algo ya escrito (un criterio de una tarea T-*.md, un camino de caminos.md o una regla de contratos.md). Delega en la skill bonita-micro-cambio sin pasar por el router. Es ENTRADA, no política.
category: Workflow
tags: [bonita, bugfix, micro-work, carril-ligero, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/bugfix.md (adaptado a Bonita y a los micro-works del hub) -->

**Entrada directa al carril de micro-works, modo bugfix.** Para cuando lo reportado es un **defecto**: el
comportamiento observado **viola** un criterio, un camino o una regla que ya existen en la documentación. No pasa por
`/bonita:work`, no abre unidad, ni change, ni DoR, ni gates. Si algo aquí contradice el bloque del arnés en
`CLAUDE.md`, gana `CLAUDE.md`.

**Entrada:** la descripción del fallo observado (qué se esperaba, qué ocurre).

## 1. Preflight

```bash
test -f .claude/.bonita-harness.json || echo "NOT_INSTALLED"
bash .claude/hooks/bonita/slice-ops.sh status
```

`NOT_INSTALLED` → `trycore-bonita init` y vuelve. Salida `9` → la persona registra este árbol con
`slice-ops.sh register`.

## 2. ¿Hay una unidad activa? (solo para saberlo)

`status` lo dice. Si la hay, el bugfix va en **otro worktree registrado con su propio token**, en `fix/<slug>` desde
`main`, nunca en la rama de la unidad; la unidad queda en pausa sin tocar su estado.

## 3. Reclamar el micro-work y delegar

El micro-work lo da de alta una **persona** en el hub (título, tipo, ficheros, límites); el agente lo reclama:

```bash
bash .claude/hooks/bonita/slice-ops.sh claim
```

Salida `micro-work:` → es tuyo. `7` → no hay: pídele a la persona que lo dé de alta (no hagas el cambio fuera del
hub). Empieza por `unidad:` → no es esto: `bonita-construir-unidad`.

Invoca la skill **`bonita-micro-cambio`** en **modo bugfix** y sigue sus pasos (anclar → reproducir ejecutando →
arreglar → re-ejecutar → prueba de regresión validada por reversión → PR). **No pases por `/bonita:work`**: la
clasificación ya está hecha. Sin ancla citable (`T-xx criterio n`, camino o regla) no hay bugfix: la ausencia de
criterio es la señal, y se escala.

## 4. Señales de escalada

Sin señal, el carril no escala. Si el cambio cruza un límite (BDM, contrato, dependencia, API, criterio, > 3
ficheros de documentación):

```bash
bash .claude/hooks/bonita/slice-ops.sh micro-escalar --motivo "<razón>" --limite sin_cambio_de_dominio
```

El hub crea una propuesta de unidad que decide una persona. Para y repórtalo.

## Guardrails

- **Solo entrada.** Con un micro-work solo valen `micro-fase`, `micro-checkpoint` y `micro-escalar`; `phase`, `gate`,
  `submit` y `archive` son de unidades.
- **Sin ancla no hay bugfix**; no inventes el criterio.
- **La prueba de regresión vale si cae sin el fix.**
