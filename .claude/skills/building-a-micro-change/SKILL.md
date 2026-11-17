---
name: building-a-micro-change
description: Use for maintenance that is NOT new product capability — typo, copy, config, docs, infra, an allowlisted dependency bump, or a bug fix that makes code comply with an existing acceptance criterion. Lightweight lane (fix/*|chore/* → PR), no active_slice or epic. Escalates if the change adds a new dependency, creates a new public API/endpoint, or changes specified behaviour (an existing AC stops being true / needs a new AC) or the data model. Entries: /build:bugfix, /build:microwork.
---

# Micro-change (mantenimiento) — carril ligero

Carril para **mantenimiento que no es construcción de producto nueva**. Espeja la filosofía del
arnés: la épica es la unidad de **construcción**, pero un typo, un bump de dependencia o un bug que
impide cumplir un criterio ya escrito **no son construcción** — forzarlos por las 8 fases de
`building-a-slice` es ceremonia desproporcionada. Este carril les da una vía corta **sin** diluir los
guardarraíles deterministas.

Tiene **dos modos**, un solo decision gate:

| Modo | Entrada | Para qué |
|---|---|---|
| **bugfix** | `/build:bugfix` | Un comportamiento observado **viola** un AC que ya existe. Cinco pasos: anclar → reproducir ejecutando → arreglar → re-ejecutar → test de regresión. |
| **microwork** | `/build:microwork` | Mantenimiento sin bug: copy, config, docs, bump de dependencia ya permitida, infra. |

> **Si una regla aquí contradice la metodología Trycore (`METODOLOGIA.md`), gana la metodología.**

## Paso 0 · Decision gate (obligatorio) — ¿es esto un micro-change?

Un cambio califica como micro-change **solo si cumple TODO**:

- **No añade capacidad de producto nueva.** Corrige, ajusta o mantiene algo que ya existe.
- **Alcance acotado:** pocas líneas / una sola preocupación. No toca múltiples módulos a la vez.
- **Proyecto en fase `active`** (el scaffold runnable ya existe y está confirmado). El carril **no**
  es para arrancar proyectos (eso es la Fase 0 de `building-a-slice`).

Ejemplos típicos (neutros): corregir un typo o un texto visible; ajustar un valor de configuración;
actualizar la versión de una dependencia **ya presente en la allowlist**; cambios de docs; reparar
un comportamiento que incumple un criterio de aceptación ya escrito.

### Límites DUROS — si el cambio cruza **cualquiera**, STOP: sale del carril

1. **Añade una dependencia nueva** (fuera de `stack-allowlist.json`). *Lo bloquea además
   `stack-guard.sh` de forma determinista.* → `building-a-slice`.
2. **Crea un endpoint o una API pública nueva.** → `building-a-slice`.
3. Escala fuera del carril solo si el arreglo **cambia el comportamiento especificado**: un AC de
   una HU deja de ser cierto, hace falta un AC nuevo, o exige migración del modelo de datos.
   Corregir código para que cumpla un AC que ya existe no es cambiar el dominio: es cumplirlo.
   *(Vivir en lógica del dominio no es, por sí solo, señal de escalada.)*
4. **Desborda el alcance acotado** (introduce capacidad, toca muchos archivos, mezcla preocupaciones).
   → `building-a-slice`.

**Sin señal, es micro-change; con señal de forma, slice; con señal de requisito, discovery.** El
carril nunca es un atajo para esquivar gates de producto — pero tampoco una puerta que expulse un
bug legítimo.

## Modo bugfix (`/build:bugfix`) — cinco pasos

Un bug es un comportamiento que **viola un AC que ya existe**. Los cinco pasos son disciplina
barata, no gates: cuestan minutos y no producen artefactos nuevos más allá de cuatro líneas en el PR.

| Paso | Qué | Línea que va al PR |
|---|---|---|
| **0 · Anclar** | Localiza la `HU-XXX` y el escenario AC (G/W/T) que el comportamiento observado **viola** (`grep` en `docs/04-historias/`). Tres salidas deterministas: (a) hay AC y el comportamiento lo **viola** → es bugfix, sigue; (b) hay AC y el comportamiento **coincide** con él → no es un bug, es un cambio de requisito → **discovery, STOP**; (c) **no hay AC** que lo cubra → si es comportamiento especificable (dominio) → **discovery** (hace falta un AC nuevo); si no es comportamiento especificado (config, copy, infra) → **modo microwork**. | `Cumple: HU-XXX / AC n` |
| **1 · Reproducir ejecutando** | Lo **más barato que evidencie el fallo**: un test rojo, un comando, un `curl` o la app corriendo (con su log/traza si el fallo solo vive ahí). Captura la salida. **No se toca código sin esto.** | `Reproducción: <comando> → <≤ 5 líneas o enlace>` |
| **2 · Arreglar** | Cambio mínimo, dentro de los límites duros. Rama `fix/<slug>` **desde `main`**. | `Cambio: <una frase>` |
| **3 · Re-ejecutar** | La **misma** ejecución del paso 1 ya no falla. | (misma línea, «→ ok tras el fix») |
| **4 · Test de regresión** | Si el AC anclado **ya tenía test**, corrígelo para que caiga sin el fix (**no** añadas uno paralelo); si no lo tenía, escríbelo — el ciclo del test delega en `superpowers:test-driven-development`. **Validar por reversión**: sin el fix, rojo; con el fix, verde. Si pasa igual sin el fix, el carril **no cierra**. Suite del módulo tocado en verde. | `Cae sin el fix: sí (<comando>)` |
| **5 · PR** | A `main`, con las cuatro líneas de `assets/pr-evidence.template.md`. | — |

> **Reversión segura (paso 4).** El stash está compartido entre árboles de trabajo: nunca uses
> `git stash pop` a ciegas. Prefiere un **commit WIP** que luego reordenas, o
> `git stash push -u -m "<tag-único>"` → captura el sha con `git stash list --format='%H %gs'` →
> restaura con `git stash apply <sha>` → elimina la entrada por su tag.

Si el paso 0 no encuentra AC citable, **no inventes uno**: la ausencia de AC **es** la señal. No hay
pregunta al humano que la sustituya.

## Modo microwork (`/build:microwork`)

El carril de siempre, con el test **después** del cambio:

1. **Rama tipada.** `fix/<slug>` (corrección) o `chore/<slug>` (infra/config/docs/bump), **desde
   `main`**. `gitflow-guard.sh` ya exige rama tipada y prohíbe commit/push directo.
2. **Aplica el cambio acotado.** Si al implementar aparece una señal, detente y escala (ver abajo).
3. **Verifica** que el cambio hace lo que dice (el comando, la pantalla, el arranque).
4. **Test de regresión — solo si cambia comportamiento.** Si lo cambia, añade/ajusta un test y
   **valídalo por reversión** (sin el cambio, rojo). Para cambios **no conductuales** (typo en copy,
   docs, config) **no** se exige test. Suite del módulo tocado en verde si hubo test.
5. **PR a `main`**, indicando que es mantenimiento y qué límite **no** cruza.

**Compuerta de microwork:** si el comportamiento que cambias está **cubierto por un AC**, no es
microwork — es **bugfix** si el cambio hace que el AC se cumpla, y **discovery** si lo contradice.

## Escalada por señales, no por duda

**Sin señal, el carril no escala.** Señal de **forma** (dependencia nueva, endpoint/API pública
nueva, migración del modelo de datos) → `building-a-slice`. Señal de **requisito** (un AC deja de
ser cierto, hace falta un AC nuevo, la HU nunca se cableó) → discovery.

- **Señal de requisito → discovery (`/trycore:*`).** El PR del bugfix **se cierra sin merge**
  dejando el hallazgo escrito (qué AC falta o cuál dejó de ser cierto).
- **HU nunca cableada.** No es un defecto sobre algo que funcionaba: es un **hueco de cableado**.
  Deja además la **nota del falso verde** en el PR (qué evidencia daba por hecha una HU que nunca se
  cableó) y lanza `/build:reflect` si procede.
- **En modo `dual`/`runtime`**, registra la escalada con
  `bash .claude/hooks/build/slice-ops.sh escalate "<razón>"`. En `legacy` basta el PR cerrado con el
  hallazgo.
- **Orientación sin cifra:** si llevas mucho más de una hora, revisa las señales; el tiempo por sí
  solo no escala.

## Qué se mantiene y qué se salta

| Se mantiene (gratis, vía hooks deterministas) | Se salta (por diseño) |
|---|---|
| `gitflow-guard` (rama tipada + PR) | DoR formal (escenarios G/W/T, INVEST) |
| `stack-guard` (no dependencia nueva) | OpenSpec change + bloque `## Trazabilidad` |
| `lint-typecheck` (estilo + typecheck incremental) | `journey_smoke`, `api`, `data`, DoD reducido |
| | Apertura de `active_slice` / decisión de Release Gate |

`scaffold-guard` no aplica: no hay slice activo y el carril exige proyecto en fase `active` (scaffold
ya confirmado).

## Ámbito de las reglas pesadas — este carril está EXENTO

Las reglas de **mutación obligatoria por test**, **evidencia anclada a sha** y **regresión con
worktree/baseline** aplican al **inner loop de slices** (fase tdd→dod de `building-a-slice`; ver
`../building-a-slice/references/evidence-budget.md`), **no** a este carril. Aquí la mutación es
exactamente **una** en modo bugfix —la **reversión del fix** del paso 4— y **ninguna** en modo
microwork sin cambio de comportamiento. Añadido a eso, solo se exige **la suite del módulo tocado en
verde**.

Nada más. Un micro-change típico debe poder cerrarse en una sesión corta de terminal; si el ritual lo
desborda sistemáticamente, sobra ritual, no carril. Esta exención **no relaja los límites duros del
Paso 0**: dependencia nueva, endpoint/API nueva o cambio del comportamiento especificado siguen
sacando el trabajo del carril.

## Estado y trazabilidad

El micro-change **no transiciona el estado del slice** — ni reclama, ni reporta gates, ni archiva:
es mantenimiento fuera de banda, trazado por el historial de git y el PR (ni por `slice-ops.sh`, ni,
en modo `legacy`, por `.claude/state/build-state.json`). No entra al histórico de épicas, así que
`reflect-nudge.sh` **no** sugiere reflexionar por él (no hay aprendizaje de épica que capturar en un
typo).

**Coexistencia con un slice activo.** El bugfix corre en `fix/<slug>` **desde `main`**, nunca desde
la rama del slice; si hay un slice activo, queda **en pausa sin tocar su estado** (los hooks
distinguen la rama de mantenimiento y avisan de la pausa, no de «no abras PR»). **Prefiere un
worktree** para no arrastrar el árbol del slice.

## Reglas duras

- **El decision gate es obligatorio**, y decide por **señales, no por duda**: sin señal, es
  micro-change; con señal de forma, `building-a-slice`; con señal de requisito, discovery.
- **Límites duros = STOP, no excepción.** Cruzar un límite obliga a salir del carril; jamás se
  "fuerza" un micro-change para evitar el DoR.
- **En modo bugfix, sin AC anclado no hay bugfix.** `Cumple: HU-XXX / AC n` es obligatorio en el PR.
- **El test de regresión vale si cae sin el fix.** Un test que pasa igual sin el arreglo no cierra el
  carril.
- **Integración solo por PR** a `main` (lo respalda `gitflow-guard.sh`).
- Si una regla aquí contradice `METODOLOGIA.md`, **gana la metodología**.
