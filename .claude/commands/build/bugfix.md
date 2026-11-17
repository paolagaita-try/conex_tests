---
name: "BUILD: Bugfix"
description: Entrada directa al carril ligero en modo bugfix — un comportamiento observado viola un AC que ya existe. Invoca building-a-micro-change sin pasar por el router: anclar al AC, reproducir ejecutando, arreglar, re-ejecutar y test de regresión validado por reversión. Es ENTRADA, no política: no ejecuta gates, no toca el estado ni crea ramas por su cuenta.
category: Workflow
tags: [build-harness, bugfix, micro-change, carril-ligero, trycore]
---

**Entrada directa al carril ligero, modo bugfix.** Para cuando lo reportado es un **bug**: el
comportamiento observado **viola un criterio de aceptación que ya existe**. No pasa por
`/build:work` y no abre `active_slice`, ni épica, ni change. Si algo contradice `METODOLOGIA.md`,
**gana la metodología**.

**Entrada:** la descripción del fallo observado (qué se esperaba, qué ocurre).

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

- El bugfix corre en `fix/<slug>` **desde `main`**, nunca desde la rama del slice.
- El slice queda **en pausa sin tocar su estado**: los hooks reconocen la rama de mantenimiento y
  avisan de la pausa, no de «no abras PR».
- **Worktree recomendado**, para no arrastrar el árbol de trabajo del slice.

---

## 3. Delegar en la skill

Invoca la skill **`building-a-micro-change`** en **modo bugfix** y sigue sus **cinco pasos**
(anclar al AC → reproducir ejecutando → arreglar → re-ejecutar → test de regresión validado por
reversión → PR con las cuatro líneas de
`.claude/skills/building-a-micro-change/assets/pr-evidence.template.md`). **No pases por
`/build:work`**: la clasificación ya está hecha al invocar este comando.

Recordatorio del paso 0: si no hay un `HU-XXX / AC n` citable que el comportamiento viole, **no es
un bugfix** — la ausencia de AC es la señal (ver §4).

---

## 4. Señales de escalada (y sus destinos)

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
- **Sin AC anclado no hay bugfix.** No inventes el criterio ni preguntes para suplirlo.
- **El test de regresión vale si cae sin el fix.** Si pasa igual sin el arreglo, el carril no cierra.
- **Agnóstico**: vocabulario genérico del arnés; lo específico del dominio entra por `/build:onboard`.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
