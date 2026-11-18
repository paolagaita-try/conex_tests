---
name: "BUILD: Architect"
description: Capa de arquitectura previa a construcción. Genera los ADRs del proyecto con el método ADD (Attribute-Driven Design, Len Bass) leyendo docs/ (PRD + user story map + epicas + HUs) de solo lectura, y puebla stack-allowlist.json. Corre autónomo y propone al máximo; una sola revisión humana al final. Adaptador delgado: delega en la skill setup-architecture. Sus ADRs se vuelven criterios que el DoR y el gate stack_arch exigen.
category: Workflow
tags: [build-harness, architecture, add, adr, trycore]
---

Genera la **capa de arquitectura** del proyecto **antes** del primer slice: decide estilo, tácticas y
stack, y los deja como ADRs que el build ya exige. Este comando es un **adaptador delgado**: no
reimplementa nada — **delega** en la skill `setup-architecture` (método ADD). Si algo aquí contradice
`METODOLOGIA.md`, **gana la metodología**.

**Entrada (opcional):** un foco de iteración (`"fase 2"`, `"observabilidad"`, `EP-XXX`). Si viene vacío,
la skill corre el flujo completo desde el catálogo de drivers. La IA **propone al máximo**; no pregunta
campo por campo.

---

## 1. Preflight

```bash
test -f .claude/.build-harness-version || echo "NOT_INSTALLED"
command -v python3 >/dev/null 2>&1 || echo "NO_PYTHON3"
# Discovery debe estar listo (entrada de solo lectura de la capa):
test -d docs/03-backlog && ls docs/04-historias/HU-*.md >/dev/null 2>&1 || echo "NO_DISCOVERY"
```

- **`NOT_INSTALLED`** → ejecuta `trycore-build init` y vuelve. Stop si falta `python3`.
- **`NO_DISCOVERY`** → no hay historias que leer: la capa de arquitectura corre **después** de discovery.
  Remite a `@trycore/spec-product-flow` (`/trycore:*`) y detente. No escribas nada.

---

## 2. Conducir el flujo (delegar)

Invoca la skill **`setup-architecture`**. La skill:

1. Extrae el catálogo de drivers/ASRs → `docs/adr/0000-drivers-y-asrs.md` (delega en `asr-extractor`).
2. Itera ADD (una ronda por fase/release): tácticas → estilos → vistas → ADR `docs/adr/000N-*.md`.
3. Evalúa cada ADR (ATAM-lite, `architecture-evaluator`) y mantiene `docs/adr/_backlog-arquitectonico.md`.
4. Hace **una** revisión final: escala solo trade-offs de negocio, promueve `proposed → accepted` y
   consolida el stack en `.claude/config/stack-allowlist.json`.

- **No** edites artefactos de discovery (`docs/01-prd/`…`docs/04-historias/`): la única salida en `docs/`
  es `docs/adr/`.
- **No** publiques: los ADRs se **proponen** (`proposed`/`living-document`); el humano promueve a `accepted`.
- **No** abras un slice ni transiciones el estado del slice: esta fase es **pre-build**.

---

## 3. Resumen

Al terminar, resume: nº de drivers por tipo, nº de ADRs generados, estilo(s) y stack propuestos, riesgos
abiertos del backlog, y el siguiente paso: `/build:work` o `/build:slice` (ahora el DoR ya puede exigir
cobertura de ADR y `stack-guard` hace cumplir el stack).

---

## Guardrails

- **Solo lectura sobre discovery**; la única escritura en `docs/` es `docs/adr/`.
- **Propón, no publiques**: la promoción a `accepted` es del humano (revisión única).
- **Mínimo HITL**: autónomo; se detiene como máximo en una `AskUserQuestion` de trade-offs de negocio.
- **Incremental**: re-correr añade iteraciones; no regenera ADRs `accepted`.
- **Agnóstico**: no asume dominio; entra por `docs/`.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
