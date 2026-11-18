# Usabilidad según Steve Krug ("Don't Make Me Think")

Heurísticas que aplica `ux-krug-reviewer` a slices con UI. Objetivo: que el usuario operador del producto opere
sin fricción cognitiva.

## Las leyes de Krug
1. **Primera ley — "No me hagas pensar".** Todo lo autoevidente; si no, autoexplicativo. Cero acertijos.
2. **No usamos la web, la escaneamos.** Diseña para el vistazo: jerarquía visual, encabezados,
   fragmentos cortos, lo importante arriba/grande.
3. **Elegimos la primera opción razonable (satisficing).** No obligues a comparar; ofrece caminos obvios.
4. **"Omite las palabras innecesarias".** Recorta el ruido textual a la mitad; luego otra vez.
5. **Convención sobre creatividad.** Botones que parecen botones, enlaces que parecen enlaces,
   navegación donde se espera.
6. **Haz obvio lo clicable** y da feedback inmediato (hover, loading, disabled, foco).

## Aplicado a decisiones de alto impacto
- La **decisión de alto impacto del dominio** (ejemplo concreto en el domain-pack del consumidor) y su **resultado con su banda/clasificación** deben leerse de un vistazo.
- Los **drivers o factores que justifican el resultado**: visibles y comprensibles sin abrir documentación.
- Las **inconsistencias o discrepancias detectadas**: resaltadas y atribuidas a su origen correcto, sin ambigüedad.
- Estados explícitos: **cargando, vacío, error, sin permisos**; nunca una pantalla muda.
- Recuperación de error con mensaje accionable (qué pasó y qué hacer), sin filtrar datos sensibles / PII regulados ni stack traces.

## Medir, no opinar (cuando la app corre)
Usa el MCP **chrome-devtools**:
- `take_snapshot` → inspecciona el árbol de accesibilidad (roles, labels, foco).
- `lighthouse_audit` → puntuaciones de Accessibility / Best Practices; adjunta fallos concretos.
Reporta hallazgos como BLOQUEANTE / RECOMENDADO / NIT con la pantalla y el fix.
