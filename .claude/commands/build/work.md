---
name: "BUILD: Work"
description: Router de entrada (classify-and-act) del arnés. Clasifica el trabajo entrante y enruta a la skill correcta — building-a-micro-change (mantenimiento), building-a-slice (épica/producto nuevo) o releasing-a-version (Release Gate) — codificando los límites duros del micro-change y el default del Release Gate. Es RUTEO, no política: no ejecuta el pipeline, no toca el estado ni crea ramas.
category: Workflow
tags: [build-harness, router, classify-and-act, trycore]
---

**Router puro.** Decide *qué carril* aplica y **delega** en la skill correspondiente. NO ejecuta el pipeline,
NO transiciona el estado del slice, NO crea ramas. Codifica como **ruteo** (no política nueva) el *decision gate*
del micro-change y el default del Release Gate de `METODOLOGIA.md` (§2, §4). Si algo contradice la metodología,
**gana la metodología**.

**Entrada:** una descripción del trabajo a hacer.

---

## 1. Preflight

```bash
test -f .claude/.build-harness-version || echo "NOT_INSTALLED"
```

Si `NOT_INSTALLED` → ejecuta `trycore-build init` y vuelve.

---

## 2. Clasificar (decision gate)

Aplica las reglas en orden:

0. **¿Greenfield sin caparazón construido?** — consulta los hechos de proyecto. En `legacy`/`dual`
   se leen de `.claude/state/build-state.json`:
   ```bash
   python3 -c "import json;d=json.load(open('.claude/state/build-state.json'));print(d.get('project_kind'),d.get('foundation',{}).get('completed_at'))"
   ```
   En `runtime`, de la línea `hechos:` que imprime `bash .claude/hooks/build/slice-ops.sh status`
   (`project_kind`, `foundation_done`). Si `project_kind` es
   `greenfield` y la caparazón no está completada → **enruta directo a construir la épica caparazón**
   por el carril **`building-a-slice`**. `status` no trae **cuál** es esa épica (`foundation.epic`
   vive hoy en el fichero legacy, leído directo por `dor-dod-gatekeeper`); si no la encuentras o
   está sin definir, enruta a `/build:onboard` (Fase 2c) o a discovery para definirla — **salvo en
   modo `runtime`**, donde `foundation.epic` sin definir puede ser una propuesta **pendiente de
   aprobación del hub**, no un olvido: consulta antes `slice-ops.sh epic-status` (o
   `/build:epic --check`) y, si ya hay una propuesta `PROPOSED`, el destino es **esperar la
   aprobación**, no re-onboardear (re-correr la Fase 2c propondría una segunda vez la misma épica
   caparazón, issue #62). Ninguna épica de negocio pasa por delante. Brownfield, o caparazón no requerida (`foundation_done` ya `true`) →
   esta regla es N/A.
   Esta regla gatea **aperturas de slice** (épicas): el carril de **mantenimiento**
   (`building-a-micro-change`, reglas 1a/1b) no se bloquea — un bugfix o un typo/copy/config fix
   sigue su carril normal aun sin caparazón construida.
1. **¿Mantenimiento sin capacidad nueva?** — carril **`building-a-micro-change`**, que tiene **dos
   modos** y entrada propia (no hace falta volver por este router):
   - **1a. ¿Bug reportado (un AC que ya existe no se cumple)?** — el comportamiento observado
     **viola** un criterio de aceptación ya escrito → **modo bugfix** (**`/build:bugfix`**): anclar
     al AC → reproducir ejecutando → arreglar → re-ejecutar → test de regresión validado por
     reversión → PR, **sin** abrir `active_slice`. Si no hay AC citable que el comportamiento viole,
     la ausencia de AC **es** la señal → **discovery** (ver paso 3).
   - **1b. ¿Mantenimiento sin bug?** — typo, ajuste de copy/config/docs, bump de dependencia **ya
     permitida**, infra: comportamiento **no** cubierto por un AC **Y** sin ninguno de los límites
     duros del paso 3 → **modo microwork** (**`/build:microwork`**): `fix/*`|`chore/*` → PR, **sin**
     abrir `active_slice`.
2. **¿Producto nuevo / una épica?** — capacidad nueva, o **señal de forma** (dependencia nueva,
   endpoint/API pública nueva, alcance desbordado — §3) → carril **`building-a-slice`** (una épica `EP-XXX` = un slice = un change = una rama
   = un PR). Si no hay épica aún, el trabajo vuelve a discovery para crearla; si lo que aparece es
   una **señal de requisito** (límite 3), el destino es **discovery**, no este carril.
3. **¿Toca correr el Release Gate?** — la épica recién archivada **cierra una línea de release** del Story Map,
   o hay **≥ 2 épicas archivadas** desde el último entry de `releases[]` → sugiere el carril
   **`releasing-a-version`** (outer loop). (El destino es la skill existente; este router no depende de
   `/build:release`.)

---

## 3. Límites duros del micro-change (sacan el trabajo del carril)

Si el cambio **añade una dependencia nueva**, **crea un endpoint/API nuevo** o **desborda el alcance
acotado** → **deja de ser micro-change** y se enruta a **`building-a-slice`** (épica).

Y, **en cuanto al límite 3**, el arreglo solo sale del carril si **cambia el comportamiento
especificado**: un AC de una HU deja de ser cierto, hace falta un AC nuevo, o exige migración del
modelo de datos. Corregir código para que cumpla un AC que ya existe no es cambiar el dominio: es
cumplirlo.

**Escalada por señales, no por duda.** Sin señal, el carril no escala. Señal de **forma**
(dependencia nueva, endpoint/API pública nueva, migración del modelo de datos) →
`building-a-slice`. Señal de **requisito** (un AC deja de ser cierto, hace falta un AC nuevo, la HU
nunca se cableó) → discovery.

---

## 4. Actuar (delegar) — con degradación headless

- **Con TTY**: si la clasificación es **clara** (una sola regla dispara), invoca la skill directamente —
  la pregunta sobra. Usa **una sola** `AskUserQuestion` **solo si la clasificación es ambigua**
  (ninguna regla dispara, o disparan dos), ofreciendo el carril propuesto como primera opción
  "(Recomendado)".
- **Sin TTY / headless / entrada ausente**: **no bloquees**. Clasifica determinísticamente y emite por stdout
  `{clasificación, skill recomendada, criterio que disparó la rama}`. Si es **ambiguo**, decide por señales:
  **sin señal, carril micro; con señal de forma, slice; con señal de requisito, discovery**,
  declarándolo explícitamente.

---

## Guardrails

- **Solo ruteo.** No corres el pipeline, no transicionas el estado (ni por `slice-ops.sh` ni por el
  fichero), no creas ramas: eso es de las skills destino.
- **Sin señal, carril micro.** Nunca degrades un cambio con señal de forma a micro-change ni
  resuelvas una señal de requisito en el carril.
- **No dupliques gates** ni saltes el orden: las skills destino los gobiernan.
- **Agnóstico**: vocabulario genérico del arnés; lo específico del dominio entra por `/build:onboard`.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
