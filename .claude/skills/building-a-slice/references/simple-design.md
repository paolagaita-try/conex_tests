# Diseño simple (Kent Beck) + code smells

Guía que aplica `simple-design-reviewer` sobre código **que ya pasa los tests**.

## Las 4 reglas de diseño simple (orden de prioridad de Beck)
1. **Pasa los tests.** Correcto antes que bonito.
2. **Revela la intención.** Nombres y estructura cuentan la historia; un lector entiende sin adivinar.
3. **No tiene duplicación.** DRY de *conocimiento* (no de texto casual). Regla de tres antes de extraer.
4. **Menos elementos.** Lo mínimo que cumpla 1–3. YAGNI: nada especulativo.

Conflictos: 1 manda siempre; entre 2 y 3, prioriza eliminar duplicación; entre 4 y 2/3, prioriza
revelar intención y no duplicar (la concisión no justifica oscuridad).

## Smells frecuentes (y su refactor)
| Smell | Señal | Refactor |
|---|---|---|
| Función larga | hace muchas cosas | Extract Function; una responsabilidad |
| Lista de parámetros larga | 4+ params | Introduce Parameter Object |
| Números/strings mágicos | literales sueltos | Constante con nombre / config versionada |
| Duplicación | misma lógica en 2+ sitios | Extraer función/módulo compartido |
| Feature envy | un módulo usa más datos de otro | Mover el comportamiento a donde viven los datos |
| Componente "Dios" | UI + estado + lógica de negocio | Separar la capa de decisión del dominio de la vista |
| `any` / casts | tipos perdidos | Tipar con interfaces/zod |
| Comentario-muleta | explica código confuso | Renombrar/extraer hasta que sobre el comentario |
| Código muerto | no se referencia | Borrar |

## Específico del dominio
- La **capa de decisión determinista del dominio** vive en su propio módulo puro (testeable, sin UI, sin IA): mismas entradas → misma salida, explicable.
- **Parámetros de decisión** (umbrales, pesos, bandas) = configuración versionada, jamás literales repartidos por el código.
- La **capa de servicios externos** (el servicio externo/IA de la frontera declarada por el consumidor) queda aislada detrás de una interfaz; el resto del código no la conoce.
- La salida de cualquier servicio externo/IA se trata como **input no confiable**: validación contra un esquema fijo centralizada (un solo esquema reutilizado) antes de alimentar la capa de decisión.

Clasifica hallazgos en BLOQUEANTE / RECOMENDADO / NIT. Solo los BLOQUEANTES impiden `gates.smell`.
