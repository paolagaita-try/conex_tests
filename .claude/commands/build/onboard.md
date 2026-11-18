---
name: "BUILD: Onboard"
description: Parametriza el dominio del build harness — capa de servicios externos/IA, lógica determinista, PII, secretos, decisiones de alto impacto y fuente de diseño (DESIGN_SOURCE). Rellena el bloque marcado de CLAUDE.md y escribe auto-memory. Complementa al CLI trycore-build init (que ya sembró los archivos y el stack mecánico).
category: Workflow
tags: [onboarding, parametrizacion, build-harness, trycore]
---

Parametriza el **dominio** de un proyecto donde ya se instaló el arnés con `trycore-build init`. El CLI ya sembró los archivos, el `stack-allowlist.json` y el bloque marcado de CLAUDE.md con `{{placeholders}}`. Tu trabajo es resolver esos placeholders (que requieren leer e interpretar el PRD) y escribir la memoria — **cosas que el binario Node no puede hacer**.

---

## Preflight

```bash
test -f .claude/.build-harness-version || echo "NOT_INSTALLED"
```

**Si no instalado:**

> Este proyecto no tiene el arnés de construcción instalado. Ejecuta primero:
> ```
> npm install -g @trycore-co/spec-build-harness   # si aún no tienes el CLI
> trycore-build init                            # en este directorio
> ```
> Luego vuelve a `/build:onboard`.

Stop aquí si no está instalado.

---

## Fase 1: Bienvenida

```
## Onboarding del arnés de construcción

El CLI ya instaló agentes, comandos /opsx:*, hooks y el estado. Ahora voy a parametrizar el
DOMINIO del arnés (2-3 min) — los puntos de extensión que leen los agentes de calidad
(security-reviewer, stack-guardian, data-consistency-checker, ux-krug-reviewer, simple-design-reviewer, ux-fidelity-reviewer).

Voy a leer tu PRD/openspec para proponer valores y confirmar contigo:
1. Ruta#ancla del PRD técnico (fuente del stack)
2. Capa de servicios externos / IA (la frontera)
3. Lógica que debe ser determinista (no delegable a IA)
4. Categorías de datos sensibles / PII reguladas
5. Secretos server-side
6. Decisiones de alto impacto que exigen explicabilidad en UX
7. Fuente de diseño / referencia visual (prototipo/export) y pantallas — o "N/A" si no hay UI
8. Capa de cada épica del backlog: **fundacional** (cimiento) vs **negocio**
9. (Solo proyecto nuevo) Contrato del caparazón: checklist de la épica fundacional de app shell
```

---

## Fase 2: Leer el PRD y recopilar

1. Localiza y lee el PRD técnico del consumidor y/o `openspec/project.md` si existen
   (típico: `docs/01-prd/*.md`, sección de requisitos técnicos). Si no hay PRD, opera solo con
   las respuestas del usuario.
2. **Propón** valores derivados del PRD y confírmalos vía **AskUserQuestion** (un ítem por punto;
   ofrece tu propuesta como primera opción "(Recomendado)"):
   - **PRD técnico** (`PRD_TECH_PATH`): ruta#ancla de la sección de requisitos técnicos.
   - **Capa de servicios externos / IA** (`EXTERNAL_SERVICE_LAYER`): ¿hay un servicio externo/IA?,
     ¿cuál es su frontera/aislamiento? (ej. "capa de extracción documental"). Y en sentido amplio:
     **¿hay fronteras** (servicio de terceros, motor de datos, cola, SDK, documento a interpretar)?
     Para **cada una**, recoge **en este mismo ítem** (no abras una pregunta por frontera): id corto
     (kebab-case), nombre, ancla del PRD técnico, rutas del adaptador (`paths[]`), variable de
     credencial, formas de mensaje conocidas, y si la interacción real es **imposible por naturaleza**
     (`prod_only` | `destructive` | `cost`). **Esta es la única recogida**: la Fase 2d no vuelve a
     preguntar, solo escribe lo recogido aquí tras **una** confirmación del bloque entero. El texto
     del CLAUDE.md sigue siendo la prosa de siempre.
   - **Lógica determinista** (`DETERMINISTIC_LAYER`): ¿qué lógica NO puede delegarse a un servicio no determinista? (ej. "motor de decisión/reglas").
   - **Datos sensibles / PII** (`SENSITIVE_DATA_CATEGORIES`): categorías reguladas del dominio.
   - **Secretos server-side** (`SERVER_SIDE_SECRETS`): claves/tokens que jamás van al cliente.
   - **Decisiones de alto impacto** (`HIGH_STAKES_DECISIONS`): decisiones que exigen explicabilidad/justificación en la UI.
   - **Fuente de diseño** (`DESIGN_SOURCE`): ¿el producto tiene UI? Si sí, ruta/URL de la fuente
     visual de verdad (prototipo, export de diseño o mockups) y cómo localizar cada pantalla; si no,
     "N/A". Si hay UI pero **no existe** fuente aún, indica que `/build:prototype` puede generarla
     tras el onboarding (prototipo HTML de referencia en `docs/05-prototipo/`; la confirmación
     sigue siendo humana). (El reporte del hecho `design_source` se hace en la Fase 3c.)
   - **Auto-checkpoint de contexto** (`context.auto_checkpoint`, no toca el CLAUDE.md, va a
     `build-config.json`): ofrécelo **una sola vez, aquí**, dentro de esta misma confirmación —
     no abras una fase ni una pregunta aparte. En una frase: al llegar a contexto crítico, el
     arnés puede avisar y esperar (default), o continuar solo en sesión fresca si el equipo lo
     confirma. El default sigue siendo `false`; solo se fusiona `true` en
     `.claude/config/build-config.json` (mismo patrón lee-modifica-escribe atómico de la Fase 2d)
     si el equipo lo pide explícitamente.
3. Si un punto no aplica al proyecto, registra explícitamente "no aplica" (no lo dejes como `{{...}}`).

---

## Fase 2b: Clasificar la capa de las épicas (cimiento vs negocio)

**Primero, resuelve `project_kind`** (léelo de `bash .claude/hooks/build/slice-ops.sh status`):
- `"brownfield"` → el mecanismo del caparazón es **N/A**: no preguntes ni exijas nada de la
  Fase 2c; clasifica capas como siempre y sigue.
- `null` / ausente (detección ambigua del CLI) → pregunta **una sola vez** vía AskUserQuestion:
  *"¿Este proyecto es una app nueva (greenfield: el caparazón — menús, layout, homepage, login,
  redirecciones — aún no existe) o ya construida (brownfield)?"*. Repórtalo:
  `bash .claude/hooks/build/slice-ops.sh fact project-kind <greenfield|brownfield> --source human`
  (rc 3 = modo legacy: escríbelo en el fichero con su protocolo).
- `"greenfield"` → tras clasificar capas (abajo), continúa a la **Fase 2c**.

El factor que más reduce el consumo de contexto por slice es que el **cimiento** ya esté construido y
abstraído antes de que el loop tome historias de negocio. Para habilitar el gate de DoR "Cimiento
construido":
1. Lee el backlog/Story Map del proyecto (`docs/03-backlog/epicas.md`, `docs/02-user-story-map/`).
2. Propón, vía **AskUserQuestion**, qué épicas son **`layer: foundational`** (autenticación, acceso a
   datos, arquitectura base, design-system/componentes base del prototipo) y cuáles **`layer: business`**.
3. Escribe el tag en el **frontmatter de cada épica** en `docs/03-backlog/epicas.md` (artefacto de
   discovery; coordina con `@trycore/spec-product-flow` si ese paquete ya lo gobierna — el build-harness
   solo necesita poder **leer** `layer`). El DoR rechazará abrir una épica de negocio que arrastre
   cimiento `foundational` aún no archivado.

No inventes la clasificación: derívala del PRD/Story Map y confírmala con el usuario.

---

## Fase 2c: (Solo greenfield) Contrato del caparazón y su épica

Contrato completo en `.claude/skills/building-a-slice/references/foundation-contract.md`.
Si `project_kind !== "greenfield"`, salta esta fase (N/A total).

1. **Podar la checklist** vía AskUserQuestion (multiSelect) partiendo de los 5 ítems canónicos
   (`navegacion-menus`, `layout-panel-central`, `homepage`, `login-authn`,
   `redirecciones-guards`) según el tipo de app (una API sin UI poda los de UI y conserva
   `login-authn`). Ítem podado = `applies: false` (se conserva como decisión, no se borra).
   El usuario puede añadir ítems propios (id kebab-case). Si el humano poda **todos** los ítems
   (ningún `applies: true`), no hay caparazón exigible: escribe `foundation.required: false` y el
   mecanismo queda N/A (el DoR no bloqueará por caparazón).
2. **Identificar la épica caparazón** en `docs/03-backlog/epicas.md`: una épica
   `layer: foundational` cuyo alcance cubra los ítems `applies: true`.
   - **Existe** → propónla al usuario y fija `foundation.epic`.
   - **No existe** → **borrador híbrido**: redacta la épica caparazón (título, objetivo, una HU
     por ítem `applies: true` con AC en Given/When/Then) y preséntala vía AskUserQuestion.
     - **Aprueba**, y `slice-ops.sh mode` dice `legacy`/`dual` → escríbela en
       `docs/03-backlog/epicas.md` con frontmatter `layer: foundational` y
       `origin: harness-draft`, y fija `foundation.epic`. **Este es el ÚNICO caso en que el
       arnés escribe una épica por decisión propia** (carve-out de METODOLOGIA §9.2: solo la
       épica caparazón, solo con aprobación explícita).
     - **Aprueba**, y el modo es `runtime` → **no escribas el fichero**: propón la épica al hub
       (la identidad la asigna él, issue #62) y deja `foundation.epic: null` hasta que vuelva
       con código:

       ```bash
       bash .claude/hooks/build/slice-ops.sh propose-epic --file /tmp/epica-caparazon.json
       ```

       Explica al usuario que la épica queda **pendiente de aprobación humana** en la consola
       del hub y que, una vez aprobada, `/build:epic --check` la escribe en `epicas.md` con su
       `EP-XXX`. El hecho de fundación se reporta igual en el paso 3 (`--epic` no viaja al hub).
     - **Rechaza** → **STOP** de la fase: deja `foundation.epic: null`, instruye crearla en
       discovery (`/trycore:*`) con la checklist como alcance. El gate del DoR bloqueará las
       épicas de negocio igual hasta que exista y se archive.
3. **Reportar el hecho**: escribe la checklist podada en un fichero temporal
   (`[{"item","applies","evidence":""}, …]` — la clave es `item`, no `id`: así lo exige
   `foundation.checklist[]` del schema del estado, `additionalProperties: false`) y repórtala en
   una sola transición. El valor de `--epic` depende de si ya tienes un `EP-XXX` real:

   - **Existe / `legacy`/`dual` con épica ya escrita** → pasa el código real:

     ```bash
     bash .claude/hooks/build/slice-ops.sh fact foundation \
       --required true --epic EP-XXX --checklist-file /tmp/foundation-checklist.json
     ```

   - **`runtime` con la propuesta aún sin aprobar** (`foundation.epic: null`) → **omite `--epic`
     por completo**. No inventes un `EP-XXX` de relleno: el flag ni se valida ni viaja al hub
     (`_fact_foundation` en `slice-ops.sh` lo acepta solo por compat local; el hub solo recibe
     `--required`), así que no hay coste mecánico en omitirlo — y sí lo hay en escribir uno falso.

     ```bash
     bash .claude/hooks/build/slice-ops.sh fact foundation \
       --required true --checklist-file /tmp/foundation-checklist.json
     ```

   `--required false` cuando el humano podó todos los ítems (no hay caparazón exigible).
   En modo legacy (rc 3) se escribe en el fichero con su protocolo.

---

## Fase 2d: Declarar las fronteras en `config/build-config.json`

La prosa del CLAUDE.md no la lee una máquina. Las fronteras recogidas en la Fase 2 se declaran
**una vez por proyecto** en el bloque `boundaries[]` de `.claude/config/build-config.json`: de ahí
salen los items `BND-*` del `wiring_checklist[]` de cada slice y ahí vive la memoria de lo ya
verificado. Contrato completo en
`.claude/skills/building-a-slice/references/boundary-check.md`.

1. **Propón, no interrogues.** Deriva el borrador de dos fuentes, sin inventar:
   - el **PRD técnico** (`PRD_TECH_PATH`, sección de servicios externos): nombre, ancla y credencial;
   - un `grep` de adaptadores en el código (`rg -l "http|client|sdk|adapter" src/` o equivalente del
     stack) para las `paths[]` reales.
2. **Una sola confirmación, del bloque entero.** Los datos ya se recogieron en la Fase 2
   (`EXTERNAL_SERVICE_LAYER`): **no vuelvas a preguntar frontera por frontera**. Combina el borrador
   derivado del PRD con lo que el humano dijo allí, muéstralo completo y pide **una** confirmación
   vía **AskUserQuestion** (un solo ítem: "¿confirmas este bloque de fronteras?", con el borrador
   como primera opción "(Recomendado)"). Si el humano describe algo que el PRD no dice, la
   divergencia se registra en el PRD o en un ADR (METODOLOGIA §9.2) — no se "arregla" en silencio
   aquí.
3. **Fusiona la clave `boundaries`** en `.claude/config/build-config.json`. El fichero **ya existe**
   y trae `context` y `runtime`: **no lo reescribas**, añade la clave (forma canónica, ejemplo
   neutro — esto es un **fragmento**, no el documento completo):

```json
"boundaries": [
  {
    "id": "doc-extraction-api",
    "name": "API de extracción documental",
    "source": "docs/01-prd/prd-tecnico.md#servicios-externos",
    "paths": ["src/adapters/extraction/**"],
    "credential_env": "EXTRACTION_API_KEY",
    "message_kinds": ["extract-document", "get-status"],
    "na": null,
    "verified": []
  }
]
```

   Escríbelo con el patrón **lee-modifica-escribe atómico** (el mismo de `state_atomic_patch` en
   `hooks/build/lib/state-io.sh`), sustituyendo la lista por la confirmada:

```bash
python3 - <<'PY'
import json, os, tempfile
p = ".claude/config/build-config.json"
d = json.load(open(p))                       # conserva context, runtime y cualquier otra clave
d["boundaries"] = [                          # ← la lista confirmada (o [] si no hay fronteras)
  {"id": "doc-extraction-api", "name": "API de extracción documental",
   "source": "docs/01-prd/prd-tecnico.md#servicios-externos",
   "paths": ["src/adapters/extraction/**"], "credential_env": "EXTRACTION_API_KEY",
   "message_kinds": ["extract-document", "get-status"], "na": None, "verified": []}
]
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p) or ".", prefix=".build-config.", suffix=".tmp")
with os.fdopen(fd, "w") as out:
    json.dump(d, out, indent=2, ensure_ascii=False)
os.replace(tmp, p)                           # reemplazo atómico
PY
```

   Pisar el fichero con un documento que solo tenga `boundaries` deja al proyecto **sin**
   `runtime.mode` y sin los umbrales del context engine, y el fallo es **silencioso**: `config_get`
   devuelve el default sin avisar. Nota: `config_get` (clave punteada) **no lee arrays** — quien
   necesite `boundaries[]` lee el JSON completo con `python3`.

   - `id` · `name` · `source`: identificador corto, nombre legible y ruta#ancla del PRD técnico.
   - `paths[]`: globs del adaptador. Son el **join determinista** con el `files_scope` del slice: si
     no apuntan al código real, ningún slice tocará la frontera y no se sembrará nada.
   - `credential_env` (opcional): variable de entorno de la credencial. Solo con ella declarada se
     puede razonar `na: no_credentials` (se recomputa por slice: si la variable aparece, se siembra
     el item).
   - `message_kinds[]` (opcional): acota el catálogo de formas de mensaje si el PRD las nombra.
   - `na` (opcional): `{ "code": "prod_only" | "destructive" | "cost", "detail": "…" }` **solo**
     cuando la interacción real es imposible por naturaleza. Es la única decisión humana del bloque,
     y la toma aquí, una vez — nunca slice a slice. `no_credentials` y `unreachable` los computa el
     pipeline y son **transitorios** (se recomputan en cada slice); no se escriben a mano en onboard.
   - `verified: []` siempre al declarar: la memoria de intercambios reales la escribe el
     `build-orchestrator` al cerrar cada item `BND-*`, no tú.

4. **Proyecto sin fronteras** → fusiona `"boundaries": []` **explícito** (mismo patrón del paso 3,
   con la lista vacía). No lo dejes fuera.

> **Ausente ≠ vacío.** Sin la clave `boundaries` en la config, el pipeline no puede distinguir
> "este proyecto no habla con nadie" de "aquí nunca se corrió el onboard": el orquestador deja de
> sembrar el checklist y pide correr esta fase. `[]` es una declaración; la ausencia es una señal
> de migración. Por eso el template del paquete no trae el bloque.

---

## Fase 3: Resolver el bloque de CLAUDE.md

Lee `CLAUDE.md`. Encuentra el bloque entre `<!-- BEGIN trycore-build-harness` y `<!-- END trycore-build-harness -->`.

**Guardarraíl de markers (antes de escribir):** verifica que exista **exactamente un** par
`BEGIN`/`END trycore-build-harness`:

```bash
b=$(grep -c 'BEGIN trycore-build-harness' CLAUDE.md 2>/dev/null || echo 0)
e=$(grep -c 'END trycore-build-harness' CLAUDE.md 2>/dev/null || echo 0)
[ "$b" = 1 ] && [ "$e" = 1 ] || echo "MARKERS_BAD ($b BEGIN / $e END)"
```

Si imprime `MARKERS_BAD` (0 ó >1 pares) → **STOP**: pide correr `trycore-build update` y **no** edites el bloque.

Reemplaza dentro del bloque los placeholders `{{PRD_TECH_PATH}}`, `{{EXTERNAL_SERVICE_LAYER}}`,
`{{DETERMINISTIC_LAYER}}`, `{{SENSITIVE_DATA_CATEGORIES}}`, `{{SERVER_SIDE_SECRETS}}`,
`{{HIGH_STAKES_DECISIONS}}`, `{{DESIGN_SOURCE}}` por los valores confirmados.

**NO toques nada fuera de los markers.**

---

## Fase 3b: (Opcional) Poblar el stack-allowlist

Si el usuario lo desea y existe `package.json` en el proyecto:
- Lee las dependencias presentes y propón cuáles entran al `allow[]` de
  `.claude/config/stack-allowlist.json` (contrástalo con el PRD técnico).
- Setea `source` a la ruta del PRD técnico (`PRD_TECH_PATH`).
- No incluyas dependencias que el PRD no justifique.

---

## Fase 3c: (Si hay UI) Fijar que la fuente de diseño aplica, y confirmarla

Son **dos hechos distintos con dueños distintos** — no los confundas:

- **`design_source_applies`** («¿el proyecto tiene UI?») es un hecho **MÁQUINA**: lo fijas **tú**
  aquí, derivándolo de discovery (como `project_kind`). Es lo que arma el `design-source-guard`;
  sin él, en runtime el guard queda **inerte** (siempre lee `false`) y se puede escribir código de
  UI sin que avise. Repórtalo con el subcomando propio (viaja al hub como `project_fact_updated`):

  ```bash
  bash .claude/hooks/build/slice-ops.sh fact design-source-applies true    # sin UI: false
  ```

- **`design_source_confirmed`** (la fuente existe y queda confirmada, con `source`/`by`) es un
  hecho **HUMANO** de gobierno: en runtime/dual **no lo fija el agente** — lo confirma el ADMIN en
  la consola del hub (`PATCH /orchestrator/projects/{project_id}`). El prototipo puede generarse
  con `/build:prototype` (skill `prototyping-screens`); confirmar sigue siendo humano. En **legacy**
  se escribe en el fichero local junto con `applies`:

  ```bash
  # SOLO legacy (en runtime esto rebota como hecho humano y `applies` NO viaja):
  bash .claude/hooks/build/slice-ops.sh fact design-source \
    --applies true --source "<ruta/URL confirmada>" --confirmed true --by "<quién confirmó>"
  ```

Sin UI: `fact design-source-applies false` (el mecanismo de fidelidad queda N/A). Guardarraíl:
**una transición = una llamada**; confirmar es acto humano (`--by` obligatorio en legacy).

---

## Fase 4: Guardar en auto-memory

Crear/actualizar memorias **tipo `project`** (los valores cambian por proyecto):

- `build_prd_tech_path.md` → ruta#ancla del PRD técnico
- `build_external_service_layer.md` → capa de servicios externos/IA
- `build_deterministic_layer.md` → lógica determinista
- `build_sensitive_data.md` → categorías PII/datos regulados
- `build_server_side_secrets.md` → secretos server-side
- `build_high_stakes_decisions.md` → decisiones de alto impacto
- `build_design_source.md` → fuente de diseño / referencia visual

Cada memoria con frontmatter `type: project`. Agrega entradas a `MEMORY.md`.

---

## Fase 5: (Con runtime) Preparar el bundle de grafo para el ADMIN

El grafo del backlog (épicas, capas, `files_scope`, dependencias, historias, líneas de release) vive
en el runtime. **Importarlo es un acto de gobierno**: la superficie exige sesión de ADMIN y rechaza
el token de agente. El arnés **prepara y valida**; una persona sube.

1. Extrae el grafo de los artefactos de discovery ya leídos (`docs/03-backlog/epicas.md`,
   `docs/02-user-story-map/`, `docs/04-historias/`) a un JSON. **Las dependencias las extrae
   el script, no tú** (paso 2): puebla `depends_on` con lo que veas, pero **nunca lo dejes
   vacío por defecto** — un grafo sin aristas no falla, solo empobrece el Lienzo en silencio
   (issue #56: 41/41 épicas llegaron al hub con `depends_on: []`).

   **Rellena `docs_ref` en cada épica** con la ruta (relativa al repo) a su sección en los docs
   de discovery, con ancla: `docs/03-backlog/epicas.md#ep-001` (el ancla es el código en
   minúsculas; si cada épica tiene su propio fichero, apunta a ese fichero). El hub lo persiste y
   lo muestra en la ficha de la épica — **sin él la consola enseña «La documentación de esta épica
   no está disponible» y «Fuente del grafo: sin referencia»**, y un re-sync posterior que solo
   tocó docs no detecta cambio.

   **Rellena también `acceptance_ref` en cada historia** con la ruta a su documento de AC
   (`docs/04-historias/HU-001.md`). El hub lo persiste y la ficha de la épica lo usa para la
   columna de criterios — **sin él todas las historias salen con «Criterios —»** aunque tengan
   sus AC en Given/When/Then.

   ```json
   {"project_ref": "<nombre del proyecto>",
    "epics": [{"code": "EP-001", "title": "…", "layer": "foundational",
               "files_scope": ["src/core/**"], "depends_on": [],
               "docs_ref": "docs/03-backlog/epicas.md#ep-001",
               "stories": [{"id": "HU-001", "title": "…", "acceptance_ref": "docs/04-historias/HU-001.md"}]},
              {"code": "EP-002", "title": "…", "layer": "business",
               "files_scope": ["src/pagos/**"], "depends_on": ["EP-001"],
               "docs_ref": "docs/03-backlog/epicas.md#ep-002",
               "stories": [{"id": "HU-011", "title": "…", "acceptance_ref": "docs/04-historias/HU-011.md"}]}],
    "release_lines": [{"id": "R1-mvp", "epics": ["EP-001", "EP-002"]}]}
   ```

2. Normalízalo y valídalo (determinista, nunca sube nada). **Pasa siempre `--from-docs`**: el
   script relee el campo `**Depende de**` de cada sección de épica y **une** ese grafo al del
   JSON — es la única lectura fiable de las dependencias, que la metodología escribe como
   prosa. La salida va a `.claude/state/graph-bundle.json` para que `trycore-build migrate` la
   encuentre sola:

   ```bash
   python3 .claude/scripts/lib/graph-bundle.py --from-docs docs/03-backlog/epicas.md \
     < /tmp/epics.json > .claude/state/graph-bundle.json
   ```

   Para inspeccionar solo lo extraído (sin armar el bundle):
   `python3 .claude/scripts/lib/graph-bundle.py --print-deps docs/03-backlog/epicas.md`.
   Si una épica declara el campo estructurado `depende_de: [EP-001]`, ese gana sobre la prosa.

   El script emite las épicas en el **formato exacto del hub**: `layer` en MAYÚSCULA
   (`FOUNDATIONAL`|`BUSINESS` — un layer inválido rechaza el grafo ENTERO), historias con
   `code`, y `release_line` (string) por épica.

3. **Lee los avisos** (`warnings` del bundle y stderr): capa ausente, dependencia inexistente,
   ciclo, línea de release que referencia una épica desconocida, épica que está en los docs pero
   no en tu JSON, épica sin campo `Depende de`. Contrasta la línea `info: … N aristas en el
   grafo` con lo que declara el backlog: **0 aristas en un backlog con dependencias es el
   síntoma de #56**. Corrígelos en discovery — el arnés **no inventa** el grafo ni edita
   `epicas.md` (salvo el carve-out de la épica caparazón, Fase 2c).

4. **Entrega al ADMIN un solo fichero.** Si vas a migrar historial, corre `trycore-build migrate`:
   embebe el grafo como sección `graph` del bundle de estado (un único fichero para la pantalla de
   import del proyecto). Sin historial que migrar, entrega `graph-bundle.json` con esta instrucción
   literal: *«súbelo en la consola del hub, pantalla de import del proyecto»*. El import es
   idempotente y **reanuda** si falló a medias.

   Si el proyecto tiene épicas construidas **antes** de instalar el arnés (sin slice en el
   historial del estado local), decláralas en un fichero que **el humano confirme** y pásalo con
   `--pre-harness <fichero>` (`{"epics": [{"code": "EP-001", "note": "…opcional…"}]}`): se
   importan archivadas **sin declarar gates**, con un acta de migración honesta — sin esto
   quedan «sin empezar» en el hub y `claim_next` las reparte como trabajo nuevo. `migrate`
   avisa de las épicas del grafo sin slice ni declaración pre-arnés, pero **nunca** las
   añade por su cuenta.

5. Modo `legacy` o sin credenciales: salta esta fase; el grafo sigue viviendo en los documentos.

---

## Fase 6: Confirmación

```
## ✓ Dominio del arnés parametrizado

PRD técnico:        <ruta#ancla>
Servicios externos: <...>
Determinista:       <...>
PII/datos:          <...>
Secretos:           <...>
Decisiones clave:   <...>
Fuente diseño:      <...>
Caparazón:          <N/A (brownfield) | EP-XXX con N ítems aplicables | pendiente en discovery>

CLAUDE.md actualizado. Auto-memory escrita. Los agentes de calidad ya leen tu dominio.

## Próximos pasos

| Acción | Para qué |
|---|---|
| `/build:work <descripción>` | Router: enruta a micro-change / slice / release según el cambio |
| `/build:slice [EP-XXX]` | Abrir un slice (épica EP-XXX) e iniciar el inner loop |
| `/build:release [release]` | Correr el Release Gate (outer loop) sobre el diff acumulado |
| `/opsx:new` | Crear un OpenSpec change |
| `trycore-build doctor` | Verificar openspec/python3/hooks |
```

---

## Guardrails

- No avances sin confirmar los 9 puntos. Si el usuario omite alguno, repregunta o marca "no aplica".
- La pantalla de Fase 6 es un formato de pantalla específico de este comando (estado fijo del
  onboarding), no contradice `### Cómo reportar` del CLAUDE.md y queda subordinada a él.
- Si CLAUDE.md no tiene el bloque marcado (caso raro post-install), pide correr `trycore-build init` (o `update`) antes de seguir.
- No inventes valores de dominio que no estén en el PRD ni confirmados por el usuario.
- Si un valor ya existe en memory y cambió, sobrescríbelo (los proyectos evolucionan).
- Esto es parametrización **semántica**: NO modifiques agentes/skills/hooks del paquete.
