---
name: prototyping-screens
description: Use when generating or extending the HTML reference prototype (the DESIGN_SOURCE) — the visual source of truth screens are built against. Two modes — greenfield (full initial prototype from discovery docs + human-chosen aesthetic direction) and feature (new-epic screens extracted live from the already-implemented UI so they look native to the app). Self-verifies visually; human approval gates everything.
---

# Prototipar pantallas de referencia (outer-loop)

Genera el **prototipo HTML de referencia** del consumidor: la fuente de verdad visual
(`DESIGN_SOURCE`) contra la que después se construyen y verifican los slices con UI
(gate `fidelity`, `ux-fidelity-reviewer`). Si algo aquí contradice `METODOLOGIA.md`,
**gana la metodología**.

**Invariantes:**
- La skill **genera**; el humano **aprueba**. `design_source.confirmed` y el `estado: "aprobada"`
  del manifest son **siempre** decisiones humanas — esta skill jamás los auto-marca.
- Es **outer-loop**: se corre antes de abrir slices (como `/build:architect`), nunca dentro del
  inner loop de una épica.
- Escribe **solo** en `docs/05-prototipo/` (carve-out §9.2 de METODOLOGIA) y, con aprobación
  humana, reporta el hecho `design_source` (`slice-ops.sh fact design-source …`; protocolo en
  `building-a-slice/references/runtime-protocol.md`).

## Artefactos que produce (repo del consumidor)

```
docs/05-prototipo/
├── DESIGN.md          ← tokens + reglas visuales en prosa (assets/DESIGN.md.template)
├── tokens.css         ← los mismos tokens como CSS custom properties (fuente única)
├── manifest.json      ← pantalla ↔ épica/HU ↔ archivo ↔ estado (assets/manifest.schema.json)
└── pantallas/
    └── <slug>.html    ← un HTML autocontenido por pantalla (assets/screen.template.html)
```

**Reglas duras del artefacto:**
- HTML **autocontenido**: cero dependencias externas (sin CDNs, frameworks, fetch ni JS); única
  importación permitida: `tokens.css`; renderiza en `file://` indefinidamente; datos ilustrativos
  estáticos.
- Cero valores visuales fuera de tokens (color/fuente/spacing/radio/sombra → `var(--token)`).
- Estados relevantes (vacío, error, cargando…) que la HU exija → **variantes de pantalla**
  (`<slug>--<estado>.html`, campo `variante_de` en el manifest), no interacciones.
- Solo pantallas `estado: "aprobada"` son fuente de verdad (las lee `ux-fidelity-reviewer`); el
  resto son `borrador`.

## Detección de modo

1. No existe `docs/05-prototipo/` ni hay `design_source.confirmed` → **greenfield**.
2. Se pide pantallas para una épica y existe app implementada (o prototipo previo) → **feature**.
3. Ambigüedad → pregunta al humano antes de tocar nada.

## Modo greenfield — prototipo inicial completo

1. **Inventario de pantallas**: lee PRD, user story map/flows e historias de discovery; deriva la
   lista pantalla ↔ épica/HU (esqueleto del `manifest.json`) y **preséntala para confirmación
   humana** antes de generar nada.
2. **Dirección estética**: sigue `references/aesthetic-directions.md` (¿manual de marca? → destilar
   tokens; si no → 2-3 direcciones visuales de una pantalla clave, elección humana en navegador).
   Salida: `DESIGN.md` + `tokens.css`.
3. **Generación por lotes**: pantallas en orden de flow, cada una desde su HU + tokens, sobre
   `assets/screen.template.html`. Tras cada lote: auto-verificación (`references/self-check.md`)
   y **pausa** para revisión humana en navegador. Registra cada pantalla en el manifest como
   `borrador`.

## Modo feature — pantallas de una épica nueva (el caso brownfield)

1. **Precondición dura**: la app implementada **corriendo** + un MCP de inspección de UI habilitado
   (p.ej. chrome-devtools para web). Si falta cualquiera → **STOP** con instrucciones (levantar la
   app / habilitar el MCP). **Sin degradación a extracción estática**: el CSS computado real es el
   factor decisivo de fidelidad (misma postura que el gate `fidelity`, donde INCONCLUSO bloquea).
2. **Extracción viva**: sigue `references/extraction.md` (CSS computado + screenshots en 3 viewports
   + árbol de componentes de 2-3 pantallas representativas; reconciliación de `tokens.css`: la app
   real gana, las divergencias se reportan como drift).
3. **Generación**: las pantallas nuevas de la épica usan los tokens reconciliados y los screenshots
   de la app como referencia de composición. Criterio de éxito: la pantalla nueva parece
   **"una pantalla más"** de la app existente.
4. **Registro**: entradas nuevas en `manifest.json` como `borrador` (con `epica`/`historias`).

## Auto-verificación (ambos modos)

Sigue `references/self-check.md`: renderizado real de cada HTML (`file://`), screenshot en
3 viewports + snapshot estructural, comparación (feature → contra lo extraído de la app;
greenfield → contra tokens + consistencia del lote), corrección y re-render con **máximo
3 iteraciones**; si no converge, reporte al humano con el delta. Sin pixel-diff.

## Aprobación humana → estado

1. Abre las pantallas en el navegador del usuario y pide aprobación explícita (por pantalla o por
   lote). Aprobada → `manifest.json` pasa esa entrada a `"aprobada"`.
2. **Greenfield** con ≥1 pantalla aprobada: ofrece registrar la fuente. Solo con el **sí** explícito
   del humano:

   ```bash
   bash .claude/hooks/build/slice-ops.sh fact design-source \
     --applies true --source "docs/05-prototipo/" --confirmed true --by "<quién aprobó>"
   ```
3. **Feature**: `design_source` ya está confirmado; solo se amplía el manifest.

## Qué NO hace esta skill

- **No** hace pixel-diff (comparación estructural/semántica, como el resto del arnés).
- **No** genera código de producción: eso es el slice normal (`building-a-slice`) con su gate
  `fidelity`; el prototipo es su entrada, no su salida.
- **No** prototipa interacciones/animaciones (HTML estático; estados como variantes).
- **No** integra plataformas de diseño externas (exports no navegables ya tienen su rama en
  `ux-fidelity-reviewer`).
- **No** escribe en `docs/01-…04-…` ni toca otros campos del estado.
