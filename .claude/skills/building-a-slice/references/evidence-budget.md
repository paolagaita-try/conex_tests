# Presupuesto de mutación y clases de evidencia — inner loop (fase tdd→dod)

> **Si una regla aquí contradice la metodología Trycore (`METODOLOGIA.md`), gana la metodología.**

Estas reglas acotan **dónde rinde el rigor** del inner loop sin bajarlo donde importa. Aplican a la
construcción de slices (fase tdd→dod de `building-a-slice`). El carril `building-a-micro-change`
está **exento** (ver su SKILL.md): allí la única mutación es la reversión del fix (modo bugfix) y
ninguna en microwork sin cambio de comportamiento; suite del módulo tocado en verde.

## Presupuesto de mutación

La regla «un test no vale hasta que su mutación lo tumba» nació de un patrón real (tests-teatro:
fixtures irreales, comparaciones vacuas, skips que siempre saltan) y **no se elimina — se acota**:

- **Obligatoria** para los tests que sostienen un item de `wiring_checklist[]` (escenarios AC de HU,
  puntos de integración entre capas): son los que **compran el veredicto del gate**. La evidencia de
  un item del checklist sigue exigiendo la mutación que lo demuestra — manual o por reporte
  automatizado.
- **Opcional** para tests auxiliares de helpers/unidades internas. Recomendada solo si ese test es
  la **única defensa de un invariante**; en el resto, la suite en verde basta.

### Vía automatizada (alternativa al ciclo manual)

El ciclo manual — editar producción → correr la suite → revertir, N veces — puede sustituirse por
**una corrida de testing por mutación acotada a los ficheros cambiados del slice** (la herramienta
la aporta el stack del consumidor; p. ej. Stryker en stacks JS/TS, con `--mutate` restringido al
diff). El **reporte** de esa corrida es la evidencia: cada mutante sobreviviente en un fichero que
sostiene un item del checklist es un hueco a cerrar. El arnés no impone ni configura la herramienta;
si el stack no tiene una, el ciclo manual sigue valiendo — pero solo dentro del presupuesto de
arriba.

## Dos clases de evidencia y su anclaje

Todo artefacto de evidencia declara `{sha, hora, rama}`. Lo que cambia entre clases es **a qué sha
se ancla** y **cuándo caduca**:

| Clase | Qué es | Ancla | Caduca cuando |
|---|---|---|---|
| **Determinista** | Runners sin LLM: suites, smoke, contratos | **HEAD** (se re-ancla siempre) | HEAD se mueve (regenerar cuesta segundos) |
| **Viva** | Corridas contra el **LLM real del proyecto** | **Último commit que tocó el módulo bajo medición** | Cambió el código que mide — y solo entonces |

Para la evidencia **viva**:

- El ancla se obtiene con `git log -1 --format=%H -- <rutas del módulo>`. Un commit de docs, de
  estado o de **otro** módulo **no la invalida**.
- El artefacto declara ambos valores:
  - `anchored_at.sha` — el sha del módulo (**normativo**: contra este se valida el anclaje).
  - `head_at_run` — HEAD al momento de la corrida (**informativo**).
- **Regenerar solo cuando cambió el código que mide** (el sha del módulo se movió). Re-anclar por
  commits ajenos al módulo es la cinta de correr que esta regla elimina: cada regeneración mueve
  HEAD y fabrica el "hallazgo" de la pasada siguiente.
