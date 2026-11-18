# Dirección estética (modo greenfield)

Protocolo para fijar la identidad visual **antes** de generar pantallas, cuando discovery solo
entrega docs de texto. La decisión estética es **humana**; la skill produce opciones y destila.

## 1. ¿Hay manual de marca?

Pregunta primero si el consumidor tiene manual de marca / brand guidelines / design system previo.

- **Sí** → destila los tokens directamente de ese insumo (paleta exacta, tipografías, reglas de
  uso) a `DESIGN.md` + `tokens.css`, con **Procedencia: manual de marca**. **No** generes
  variantes: la identidad ya está decidida. Salta al paso 4.
- **No** → continúa con variantes (pasos 2-3).

## 2. Elegir la pantalla clave

Una sola pantalla para el ejercicio: la más **representativa del journey** (la que un usuario ve
más tiempo o la que concentra más componentes distintos — típicamente la pantalla principal de
trabajo tras entrar). Evita pantallas triviales: no discriminan entre direcciones.

## 3. Generar 2-3 direcciones y someterlas a elección humana

1. Genera la pantalla clave en **2-3 direcciones visuales genuinamente distintas** — que difieran
   en paleta, tipografía y densidad/tono (p.ej. sobria-densa · aireada-amable · contrastada-enérgica),
   no tres matices del mismo gris. Cada dirección respeta el mismo contenido y la misma HU.
2. Móntalas **lado a lado en un único HTML comparador** autocontenido (una columna por dirección,
   con nombre y rasgos clave de cada una) y ábrelo en el navegador del usuario.
3. El humano elige. Se permite **mezclar** ("la paleta de A con la tipografía de B") si lo pide.
4. El comparador es un artefacto de trabajo: puede guardarse en `docs/05-prototipo/` como
   `_direcciones.html` para la trazabilidad de la decisión, pero **no** entra al manifest.

## 4. Destilar `DESIGN.md` + `tokens.css`

De la dirección elegida (o del manual de marca):
- `tokens.css` — custom properties: paleta completa (con variantes de énfasis/estado), familias y
  escala tipográfica, spacing scale, radios, sombras.
- `DESIGN.md` (`assets/DESIGN.md.template`) — la prosa: identidad y por qué se eligió, tablas de
  tokens con uso, reglas de componentes, **Don'ts** explícitos y **Procedencia** (dirección elegida
  + fecha).

A partir de aquí, **toda** pantalla del prototipo importa `tokens.css` y no introduce valores
fuera de tokens; el self-check (`self-check.md`) lo verifica.
