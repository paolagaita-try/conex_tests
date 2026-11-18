---
name: "BONITA: Work"
description: Router de entrada del arnés Bonita. Clasifica el trabajo (una unidad del plan o un micro-work) y lo enruta a la skill correcta — bonita-construir-unidad o bonita-micro-cambio. Es RUTEO, no política: no ejecuta fases ni gates ni crea ramas.
category: Workflow
tags: [bonita, router, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/work.md (adaptado a Bonita y al modo servidor) -->

**Router puro.** Decide *qué carril* aplica y **delega**. NO ejecuta el loop, NO transiciona fases ni gates, NO crea
ramas: eso es de las skills destino. Si algo aquí contradice el bloque del arnés en `CLAUDE.md`, gana `CLAUDE.md`.

**Entrada:** una descripción del trabajo, o nada (entonces manda el hub: lo siguiente reclamable).

## 1. Preflight

```bash
test -f .claude/.bonita-harness.json || echo "NOT_INSTALLED"
bash .claude/hooks/bonita/slice-ops.sh status
```

- `NOT_INSTALLED` → `trycore-bonita init` en este directorio y vuelve.
- Salida `9` (árbol sin registrar) → pide a la persona que ejecute `slice-ops.sh register` con su token (por stdin o
  `TRYCORE_REGISTER_TOKEN`, nunca por argv).
- `status` no muestra proyecto ni grafo, o el bloque de dominio de `CLAUDE.md` sigue con `{{…}}` → el proyecto no
  está preparado: `/bonita:onboard`.

## 2. Clasificar

Aplica en orden y para en la primera que dispare:

1. **¿Ya hay trabajo reclamado en este árbol?** (`status` muestra unidad o micro-work) → retómalo: `/bonita:resume`.
2. **¿Es mantenimiento sin capacidad nueva?** — un defecto contra un criterio, un camino o una regla ya escritos;
   un texto, una configuración o la documentación de construcción; sin tocar BDM, contratos, dependencias ni APIs, y
   en ≤ 3 ficheros de documentación → carril de micro-works, skill **`bonita-micro-cambio`**:
   - viola algo ya escrito → `/bonita:bugfix`;
   - mantenimiento sin defecto → `/bonita:microwork`.
   El micro-work lo da de alta una persona en el hub; el agente lo reclama.
3. **¿Es construir lo que dice `docs/07-bonita/`?** (una unidad del plan, o una capacidad nueva) → `/bonita:unidad`,
   skill **`bonita-construir-unidad`**. Si el trabajo no está en `docs/08-construccion/plan.md`, no se improvisa una
   unidad: vuelve a `/bonita:onboard` (el plan lo aprueba una persona y lo importa el ADMIN del hub).
4. **Un cambio de requisito** (un criterio deja de ser cierto o falta uno, un proceso nuevo, un contrato distinto) no
   es de este arnés: es del arnés de documentación (`docs/`). Dilo y para.

**Escalada por señales, no por duda.** Sin señal, el carril no escala: sin señal de forma, micro-cambio; señal de
forma (dependencia, contrato, API, BDM), unidad; señal de requisito, documentación.

## 3. Actuar

- Clasificación clara (una sola regla dispara) → invoca la skill destino sin preguntar.
- Ambigua (ninguna regla o dos) → **una** pregunta con el carril propuesto como primera opción «(Recomendado)».
- Sin TTY o sin entrada → no bloquees: imprime `{clasificación, skill recomendada, regla que disparó}` y, si es
  ambiguo, decide por señales y dilo.

## Guardrails

- **Solo ruteo.** Nada de `phase`, `gate`, `submit` ni `archive` aquí.
- **Una unidad activa a la vez** y un micro-work no se mezcla en su rama: va en otro worktree registrado.
- El hub manda: no inventes unidades ni micro-works que no estén en él.
