# Auto-verificación visual del prototipo (ambos modos)

El prototipo no se da por bueno porque "se escribió bien": se **renderiza de verdad y se observa
la salida real** antes de presentarlo al humano. Misma filosofía que el gate `fidelity`
(verificación visual real, no best-effort), aplicada en dirección inversa: aquí lo verificado es
el prototipo recién generado.

## Protocolo por pantalla generada

1. **Renderizar**: abrir el HTML vía `file://` con el MCP de inspección de UI (nueva página).
   Si el archivo no renderiza limpio (recursos rotos, consola con errores), corregir antes de
   comparar nada.
2. **Capturar**: screenshot en **3 viewports** (desktop, tablet, mobile) + snapshot del árbol
   accesible/DOM.
3. **Comparar** según el modo:
   - **Feature** — contra el paquete de extracción (`extraction.md`): ¿la tipografía computada
     coincide token a token? ¿la paleta usada es la reconciliada, sin colores fuera? ¿la densidad
     (spacing computado) y el patrón de layout replican los de las pantallas capturadas? ¿la
     pantalla "parece una más" de la app?
   - **Greenfield** — contra `DESIGN.md`/`tokens.css`: **cero valores visuales fuera de tokens**
     (inspeccionar computed styles de los elementos clave); y **consistencia del lote**: mismas
     resoluciones de componente (el mismo tipo de elemento se ve igual) entre las pantallas
     generadas en esta tanda.
4. **Corregir y re-renderizar** cada divergencia encontrada. **Máximo 3 iteraciones** por
   pantalla; si a la tercera no converge, **parar y reportar al humano** el delta restante
   (qué difiere, dónde, valor esperado vs observado) — nunca presentar como buena una pantalla
   que no pasó su self-check.
5. **Registrar**: anotar en `manifest.json` los `viewports_verificados` de la pantalla. El
   `estado` sigue siendo `borrador`: el self-check **no aprueba** — aprobar es del humano.

## Reglas

- **Sin pixel-diff**: la comparación es estructural/semántica (composición, tokens computados,
  densidad, jerarquía), igual que `ux-fidelity-reviewer`. El pixel-diff es frágil y no discrimina
  desviaciones que importan de ruido de render.
- **Estructura > píxeles**: una columna de más o un panel ausente pesa más que 2px de padding.
- Las **variantes de estado** (`<slug>--<estado>.html`) pasan el mismo protocolo (suelen ser más
  baratas: heredan la composición de la base).
- El self-check corre **por lote** en greenfield (tras generar cada tanda) y **por pantalla** en
  feature (pocas pantallas, más exigencia de encaje con la app).
