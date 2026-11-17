---
name: "BUILD: Prototype"
description: Genera o amplía el prototipo HTML de referencia (la fuente de diseño / DESIGN_SOURCE) en docs/05-prototipo/. Dos modos — greenfield (prototipo inicial desde los docs de discovery + dirección estética elegida por el humano) y feature (pantallas de una épica nueva extraídas en vivo del UI ya implementado). Delega en la skill prototyping-screens. La confirmación de design_source sigue siendo humana.
category: Workflow
tags: [build-harness, outer-loop, prototipo, design-source, trycore]
---

# /build:prototype — Prototipo HTML de referencia

Delega en la skill **prototyping-screens**. Uso:

- `/build:prototype` — modo **greenfield** (o detección automática): prototipo inicial completo.
  Inventario de pantallas desde PRD/mapa/historias → confirmación humana → dirección estética
  (manual de marca o 2-3 variantes a elección humana) → generación por lotes con auto-verificación.
- `/build:prototype <épica>` — modo **feature**: pantallas nuevas de esa épica, coherentes con el
  UX/UI ya implementado. **Precondición dura**: app corriendo + MCP de inspección de UI (p.ej.
  chrome-devtools); sin ellos hace STOP (la extracción viva de CSS computado no se degrada).

Es **outer-loop**: córrelo antes de abrir slices (como `/build:architect`). Produce
`docs/05-prototipo/` (DESIGN.md, tokens.css, manifest.json, pantallas/) y, en greenfield con
aprobación humana, reporta el hecho `design_source` al runtime
(`slice-ops.sh fact design-source …`). **La skill genera; el humano aprueba**: la confirmación de la
fuente de diseño y el `estado: "aprobada"` del manifest nunca se auto-marcan.
