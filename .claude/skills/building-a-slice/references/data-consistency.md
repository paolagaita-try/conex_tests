# Consistencia de datos — frontera externa + capa de decisión

Guía que aplica `data-consistency-checker`. Dos dominios de datos: el **JSON de esquema fijo** que
devuelve el servicio externo/IA de la frontera (la "capa de servicios externos") y el **cálculo
determinista de la capa de decisión del dominio**.

Los nombres concretos de campos, las decisiones de alto impacto, los umbrales y los casos borde se
leen del bloque de dominio del CLAUDE.md del consumidor / del PRD del consumidor (ruta declarada en
`stack-allowlist.json#source`). Esta guía describe los **patrones de invariante**, no valores de un
dominio específico. (Para una instanciación concreta de referencia, ver
`docs/examples/reference/data-consistency.example.md`.)

## Esquema de la frontera (servicio externo/IA → JSON de esquema fijo)
- **Validación dura contra esquema** (p. ej. zod) a la salida del servicio: trata toda salida externa/IA como **entrada no confiable**. Malformado = rechazo controlado, no propagación a la capa de decisión.
- **Tipos/unidades** consistentes (montos numéricos, fechas ISO 8601, identificadores normalizados), según las reglas del dominio del consumidor.
- **Campos ausentes** explícitos (`null`/opcional) — nunca valores fantasma o defaults silenciosos.
- **Idempotencia**: re-procesar la misma entrada produce el mismo JSON (salvo cambios de prompt/contrato versionados).

## Capa de decisión del dominio (determinista, sin IA)
- **Determinismo**: misma entrada → mismo resultado y misma clasificación, ejecutado N veces. Sin `Math.random`, sin reloj, sin IA en el cálculo.
- **Rango y constantes versionadas**: el resultado está acotado y la clasificación pertenece al conjunto de **las decisiones de alto impacto del dominio** (ejemplo concreto en el domain-pack del consumidor), según **umbrales versionados** (config, no literales dispersos en el código).
- **Explicabilidad**: Σ(drivers por factor) reconstruye exactamente el total (cuadra al céntimo/punto); el resultado es trazable a sus contribuyentes.
- **Consistencia cruzada**: las comparaciones entre fuentes/registros (campos de identidad u otros declarados por el consumidor) son consistentes y las discrepancias se atribuyen a la fuente correcta.

## Tipos de prueba a exigir
1. **Schema tests**: fixtures válidos pasan; inválidos (campo faltante, tipo erróneo, valor negativo donde no aplica) fallan con error claro.
2. **Determinismo**: ejecutar la capa de decisión K veces sobre el mismo input → resultado idéntico.
3. **Property-based** (recomendado): para inputs generados, el resultado permanece en rango y la suma de drivers cuadra.
4. **Casos límite**: entradas vacías, valores negativos donde no deberían existir, variantes de texto con acentos/typos, valores en cero, entradas ilegibles. Los casos concretos se derivan del PRD/CLAUDE.md del consumidor.
5. **No-persistencia de datos regulados/PII**: verificar que el cálculo no escribe datos sensibles / PII regulados crudos (los que el consumidor declara en el bloque de dominio de su CLAUDE.md o su PRD) a la capa de persistencia/`localStorage`/logs.

## Veredicto → gate
Todas las invariantes ✓ con evidencia (test/`archivo:línea`) → `gates.data: true`. Alguna ✗ →
`false` + el test o fix faltante.
