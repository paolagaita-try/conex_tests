---
name: "BUILD: Microwork"
description: Entrada directa al carril ligero en modo microwork — mantenimiento sin bug: copy, config, docs, bump de dependencia ya permitida, infra. Invoca building-a-micro-change sin pasar por el router: rama tipada, cambio acotado, verificación, test solo si cambia comportamiento y PR. Es ENTRADA, no política: no ejecuta gates, no toca el estado ni crea ramas por su cuenta.
category: Workflow
tags: [build-harness, microwork, micro-change, carril-ligero, trycore]
---

**Entrada directa al carril ligero, modo microwork.** Para el mantenimiento que **no es un bug**:
typo o copy, valor de configuración, docs, bump de una dependencia **ya permitida**, infra. No pasa
por `/build:work` y no abre `active_slice`, ni épica, ni change. Si algo contradice
`METODOLOGIA.md`, **gana la metodología**.

**Entrada:** la descripción del cambio de mantenimiento.

---

## 1. Preflight

```bash
test -f .claude/.build-harness-version || echo "NOT_INSTALLED"
```

Si `NOT_INSTALLED` → ejecuta `trycore-build init` y vuelve.

---

## 2. ¿Hay un slice activo? (solo para saberlo)

```bash
STATE_LEGACY=.claude/state/build-state.json   # modo legacy (default): es la fuente de verdad
python3 -c "import json,sys;s=json.load(open(sys.argv[1])).get('active_slice');print(s.get('epica'),s.get('branch')) if s else print('ninguno')" "$STATE_LEGACY" 2>/dev/null || echo ninguno
# En `dual`/`runtime`, la proyección del servidor: bash .claude/hooks/build/slice-ops.sh status
```

Imprime `<épica> <rama>` o `ninguno`. Se consulta **solo** para saber si hay un slice reclamado.
**No** se transiciona nada.

Si lo hay, aplica **Coexistencia**:

- El mantenimiento corre en `fix/<slug>`|`chore/<slug>` **desde `main`**, nunca desde la rama del
  slice.
- El slice queda **en pausa sin tocar su estado**: los hooks reconocen la rama de mantenimiento y
  avisan de la pausa, no de «no abras PR».
- **Worktree recomendado**, para no arrastrar el árbol de trabajo del slice.

---

## 3. Compuerta por AC (antes de delegar)

Si el comportamiento que vas a cambiar está **cubierto por un AC**, esto **no** es microwork:

- el cambio hace que el AC **se cumpla** → es un **bugfix** (`/build:bugfix`);
- el cambio **contradice** el AC → es un cambio de requisito → **discovery**, STOP.

Sin AC que cubra el comportamiento (config, copy, docs, infra), sigue aquí.

---

## 4. Delegar en la skill

Invoca la skill **`building-a-micro-change`** en **modo microwork** y sigue su pipeline: rama
`fix/*`|`chore/*` → cambio acotado → verificar → **test solo si cambia comportamiento** (validado
por reversión si hay test) → PR a `main` indicando qué límite **no** cruza. **No pases por
`/build:work`**: la clasificación ya está hecha al invocar este comando.

---

## 5. Señales de escalada (y sus destinos)

Sin señal, el carril no escala. Señal de **forma** (dependencia nueva, endpoint/API pública nueva,
migración del modelo de datos) → `building-a-slice`. Señal de **requisito** (un AC deja de ser
cierto, hace falta un AC nuevo, la HU nunca se cableó) → discovery.

En señal de requisito, el PR se cierra **sin merge** dejando el hallazgo escrito; en modo
`dual`/`runtime`, registra la escalada con
`bash .claude/hooks/build/slice-ops.sh escalate "<razón>"`.

---

## Guardrails

- **Solo entrada.** No corres gates, no transicionas el estado, no archivas: el pipeline es de la
  skill.
- **Comportamiento cubierto por un AC ⇒ no es microwork.** No uses este carril para esquivar el
  ancla al requisito.
- **Agnóstico**: vocabulario genérico del arnés; lo específico del dominio entra por `/build:onboard`.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
