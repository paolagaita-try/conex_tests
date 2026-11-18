# Extracción viva del UX/UI implementado (modo feature)

Protocolo para capturar el **contexto rico real** de la app implementada antes de generar
pantallas nuevas. La lección de fondo: la fidelidad no sale de "mirar un screenshot", sale de
**CSS computado real + capturas multi-viewport + estructura**. Todo esto exige la app corriendo
y un MCP de inspección de UI habilitado (p.ej. chrome-devtools para web); sin ellos, la skill
ya hizo STOP antes de llegar aquí.

## 1. Elegir pantallas representativas (2-3)

Criterio: cubrir los patrones que la pantalla nueva va a necesitar —
- la pantalla de **navegación/layout principal** (caparazón: menús, cabecera, panel central);
- una pantalla del **mismo tipo** que la que se va a generar (listado si va a haber listado,
  formulario si va a haber formulario, detalle si detalle);
- si existe, una pantalla ya validada como fiel (`gates.fidelity: true` en `history[]`).

## 2. Capturar por cada pantalla

1. **Screenshots en 3 viewports** — desktop, tablet y mobile (redimensionar la página antes de
   cada captura). Guardan la referencia de composición y densidad.
2. **CSS computado de elementos clave** — vía el MCP (evaluar `getComputedStyle` sobre):
   - tipografía real: `font-family`, `font-size`, `font-weight`, `line-height` de titular
     principal, titular secundario, cuerpo y etiquetas;
   - color real: `color`, `background-color`, `border-color` de superficie, texto, acción
     primaria, acción secundaria y estados de énfasis;
   - espaciado real: `padding`/`margin`/`gap` de los contenedores estructurales y de los
     componentes repetidos (tarjetas, filas, campos);
   - `border-radius` y `box-shadow` de los componentes elevados.
3. **Árbol estructural** — snapshot del árbol accesible/DOM de la pantalla: número y disposición
   de paneles, orden de secciones, jerarquía. Es la referencia de **composición** (estructura >
   píxeles).

## 3. Destilar y reconciliar tokens

1. Consolida lo capturado en un conjunto de tokens (paleta, tipografía, spacing scale, radios,
   sombras). Los valores repetidos entre pantallas son los tokens; los valores únicos son ruido.
2. **Si `docs/05-prototipo/tokens.css` ya existe → reconciliar**:
   - **La app real gana** sobre lo declarado: si el token declarado dice un valor y el CSS
     computado dice otro de forma consistente, actualiza el token al valor real.
   - Cada divergencia se **reporta al humano como drift** (tabla token → declarado → real →
     pantallas donde se observó). El drift es señal de que prototipo viejo y app se separaron:
     el humano decide si además hay que corregir la app (fuera del alcance de esta skill).
3. Si no existe `tokens.css`, créalo desde lo extraído y genera/actualiza `DESIGN.md`
   (`assets/DESIGN.md.template`) con **Procedencia: extracción viva** y la fecha.

## 4. Empaquetar el contexto para la generación

Antes de generar, deja explícito el paquete de referencia que usará la pantalla nueva:
- `tokens.css` reconciliado;
- screenshots de referencia (composición/densidad) de las pantallas capturadas;
- el árbol estructural del layout principal (dónde vive el contenido en el caparazón);
- las reglas de componentes observadas (densidad de tablas, anatomía de formularios, etc.),
  anotadas en `DESIGN.md` si no estaban.

La generación no "interpreta" este paquete: **copia valores exactos**. Toda desviación deliberada
se anota como desviación intencional en `notas` del manifest para que `ux-fidelity-reviewer` no
la penalice después.
