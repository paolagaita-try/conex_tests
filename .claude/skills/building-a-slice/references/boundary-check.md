# Frontera verificada antes de construir — items `BND-*` (inner loop, `change`/`tdd`)

> **Si una regla aquí contradice METODOLOGIA.md, gana la metodología.**

Un slice puede cerrar con la suite verde, la mutación al 100 % y el journey recorrido, y contener
código que **no puede funcionar**: toda la evidencia se produjo contra dobles que escribió el mismo
agente que escribió el adaptador. La mutación prueba que los tests son **sensibles**, no que la
premisa sea **cierta**. Esta reference fija cómo se cierra ese hueco **sin gate ni fase nuevos**:
con items de `wiring_checklist[]` con el prefijo `BND-`, y memoria por proyecto en
`config/build-config.json#boundaries[]`.

## 1. Qué es una frontera y dónde se declara

Una **frontera** es todo sistema cuyo contrato el proyecto **no controla y no puede inventar**:
servicio de terceros, motor de datos, cola, SDK, formato de documento a interpretar. Se declaran
**una vez por proyecto** en `config/build-config.json#boundaries[]` durante `/build:onboard`
(Fase 2d), derivadas del PRD técnico y de un `grep` de adaptadores; el humano **confirma**, no
redefine (una divergencia con el PRD se registra en el PRD o en un ADR, METODOLOGIA §9.2).

`boundaries` es **una clave más** del `build-config.json` del consumidor, que ya trae `context` y
`runtime`: se **fusiona** con lo que haya, nunca se reescribe el fichero entero. Este es el
**fragmento** (ejemplo neutro), no el documento completo:

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

**Cómo se lee.** `config_get` (clave punteada) **no lee arrays**: con `boundaries` devuelve el
`repr` de Python y con `boundaries.0.id` lanza y cae al default, en silencio. Quien necesite el
catálogo —el orquestador— **lee el JSON completo con `python3`** (`json.load`) y navega el array en
memoria. Cómo se escribe sin pisar `context` ni `runtime`: punto 5.

| Campo | ¿Obligatorio? | Qué es |
|---|---|---|
| `id` | sí | Slug estable en inglés. Es la clave de los items y de la memoria: no se renombra a la ligera. |
| `name` | sí | Nombre legible para humanos (lo puede citar una HU). |
| `source` | sí | Dónde está declarada: sección del PRD técnico o ADR. |
| `paths[]` | sí | Globs del adaptador que habla con la frontera. **Sostienen el join** del punto 2. |
| `credential_env` | no | Nombre de la variable de entorno con la credencial. Solo si está declarado existe el `na: no_credentials`. |
| `message_kinds[]` | no | Acota el catálogo de formas si el PRD las nombra. Sin él, las deriva el orquestador. |
| `na` | no | `{code, detail}` con `code ∈ {prod_only, destructive, cost}`: decisión **humana** del onboard. |
| `verified[]` | sí (puede ir vacío) | Memoria del proyecto. Entradas `{message_kind, status: ok\|na, at, request_hash?, reason_code?, detail?}`. |

**Forma de mensaje** (`message_kind`) es cada **intercambio con contrato propio**: una operación, un
endpoint, un tipo de evento, una variante de payload con esquema distinto. `extract-document` y
`get-status` son **dos** formas; llamar dos veces a `extract-document` con parámetros distintos sigue
siendo **una**.

## 2. Qué fronteras toca el slice: join determinista

```
tocadas = { b ∈ boundaries | glob(b.paths) ∩ files_scope ≠ ∅  ∨  alguna HU de hus[] cita b.id o b.name }
```

- **Se computa, no se pregunta.** El orquestador no abre un HITL por esto: en headless el resultado
  es idéntico al interactivo.
- `files_scope` son las rutas que el slice declara tocar (alcance del change / DoR); el glob de
  `paths[]` se evalúa contra ellas.
- La cita en la HU vale con el `id` o con el `name` literal de la frontera.
- Una frontera fuera del join **no siembra nada** en este slice. No se re-paga lo que el slice no toca.

## 3. Siembra de los items `BND-*`

Al sembrar `wiring_checklist[]` (entrada a `change`/`tdd`, el momento que ya existe), por cada
frontera tocada y cada forma de mensaje que el slice usa contra ella (derivada de las HU/AC, del
change y del adaptador), siembra un item **solo si** esa forma **no** está ya en `b.verified[]` con
`status: ok` ni cubierta por un `na` **estable**. Estables son **solo** los tres códigos humanos de
`boundaries[].na` (`prod_only`, `destructive`, `cost`): son imposibilidades por naturaleza.
`no_credentials` y `unreachable` son **transitorios** y se recomputan en cada slice (punto 6): un
`na` transitorio en el `verified[]` **no** suprime la siembra.

| Campo del item | Valor |
|---|---|
| `id` | `BND-<boundary.id>-<message_kind>` |
| `kind` | `integration_point` |
| `ref` | `boundary:<boundary.id>#<message_kind>` |
| `status` | `failing` — **nacen así**, siempre |

Ejemplo: `BND-doc-extraction-api-extract-document`, con
`ref: boundary:doc-extraction-api#extract-document`.

**Una interacción por forma, no una suite.** El item mata **la duda del camino** (¿existe este
intercambio? ¿con este contrato?), no cubre casos: un intercambio real por forma basta. Los casos
límite, los errores y los contratos de esquema siguen siendo trabajo de `tdd`, `data` y `api`.

**Antes del primer test contra esa forma.** El orden importa: primero el intercambio real, después el
código que lo asume. Y **`tdd` no cierra con un `BND-*` en `failing`** (`dod.md`, gate `tdd`).

## 4. Qué cuenta como evidencia — y qué no

La `evidence` del item es un **resumen hasheado del intercambio real**. Nunca el cuerpo crudo, nunca
las cabeceras:

```
HTTP 200 · req sha256:ab12… · res sha256:cd34… · campos: id,status,pages · 2026-09-22T16:00Z
```

- `status_code` — el que **devolvió el sistema externo**. Es el corazón del resumen: sin código de
  estado no hay intercambio que enseñar. Un `422` es un **hallazgo** (contrato equivocado), no un
  verde: corrige el contrato y vuelve a intercambiar.
- `request_hash` — `sha256` del cuerpo enviado. Es el **ancla del contrato** (punto 5).
- `response_hash` — `sha256` del cuerpo recibido.
- Hasta **3 campos estructurales** de la respuesta: sus **nombres**, no sus valores.
- `at` — hora del intercambio.

**Qué NO cuenta.** Un mock, un stub, un fixture, una grabación (cassette/VCR) o una respuesta
fabricada por código del propio repo **no es evidencia** de un `BND-*`. La regla en una línea: *la
respuesta la produjo el sistema externo, con su código de estado*. Marcar `passing` con cualquiera de
esas cosas es exactamente el hueco que caza el `wiring-adversarial-verifier` (punto 7 de «Qué
cazar»), que lo devuelve a `failing`.

## 5. Memoria por proyecto: `verified[]`

Al pasar un `BND-*` a `passing`, el `build-orchestrator` añade a `boundaries[].verified[]`:

```json
{ "message_kind": "extract-document", "status": "ok", "at": "2026-09-22T16:00:00Z", "request_hash": "sha256:ab12…" }
```

Un slice posterior que use **esa misma forma** contra **esa misma frontera** ya **no siembra item**:
la frontera se verifica **una vez por proyecto**, no una vez por slice.

**Cómo se escribe: lee-modifica-escribe, nunca reemplaza.** `build-config.json` trae también
`context` y `runtime`; pisarlos deja el proyecto sin modo de runtime y con los umbrales del context
engine por defecto, **en silencio** (`config_get` devuelve el default sin avisar). El patrón es leer
el JSON entero, mutar solo la entrada de la frontera y escribir **atómico** (como hace
`state_atomic_patch` en `hooks/build/lib/state-io.sh`):

```python
import json, os, tempfile
p = ".claude/config/build-config.json"
d = json.load(open(p))                                  # conserva context, runtime y todo lo demás
b = next(x for x in d["boundaries"] if x["id"] == "doc-extraction-api")
v = b.setdefault("verified", [])
entry = {"message_kind": "extract-document", "status": "ok",
         "at": "2026-09-22T16:00:00Z", "request_hash": "sha256:ab12…"}
v[:] = [e for e in v if e["message_kind"] != entry["message_kind"]] + [entry]  # append por forma
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p) or ".", prefix=".build-config.", suffix=".tmp")
with os.fdopen(fd, "w") as out:
    json.dump(d, out, indent=2, ensure_ascii=False)
os.replace(tmp, p)                                       # reemplazo atómico
```

`verified[]` es **append por `message_kind`** (una entrada por forma; la nueva sustituye a la vieja
de esa misma forma). El fichero está **versionado** y con front paralelo (METODOLOGIA §5-bis) dos
árboles pueden escribirlo en ramas distintas: ante un conflicto de merge **gana la unión** —
conservar de más solo cuesta no re-sembrar un item ya verificado; perder una entrada re-siembra, que
es lo barato.

**El ancla es el contrato, no el sha.** `request_hash` ancla por forma de mensaje: la memoria caduca
solo cuando aparece una **forma nueva** — y entonces nace su item. **No hay caducidad por commit**.
Esto **no** es evidencia de la clase «viva» de [`evidence-budget.md`](evidence-budget.md): aquella
mide **nuestra** salida contra el LLM del proyecto y por eso se ancla al sha del módulo; esta mide al
**proveedor**, que no cambia de contrato porque nosotros hagamos commit.

## 6. El escape honesto: catálogo cerrado de `na`

Un `na` **no siembra item**: escribe `{message_kind, status: "na", reason_code, detail, at}` en
`verified[]`, deja un hito en `progress_log[]` y el PR lleva **una línea** por cada `na`.

| `reason_code` | Cuándo aplica | Quién lo decide |
|---|---|---|
| `no_credentials` | `credential_env` está **declarado** y la variable está **ausente** del entorno | Determinista. **Se recomputa en cada slice**: en cuanto aparece la credencial, se siembra el item. |
| `prod_only` | El intercambio solo existe contra producción | Humano, en `/build:onboard` (`boundaries[].na`) |
| `destructive` | El intercambio es irreversible o deja efectos colaterales reales | Humano, en `/build:onboard` (`boundaries[].na`) |
| `cost` | Cada intercambio tiene un coste material que no se paga por slice | Humano, en `/build:onboard` (`boundaries[].na`) |
| `unreachable` | El sistema no responde; el `detail` registra el **exit code o el HTTP code** obtenido | Determinista, en el intento. **Se recomputa en cada slice**: es un fallo **transitorio** (una caída de red de 30 s no declara una frontera imposible), nunca memoria estable. |

**Solo los tres `na` humanos suprimen la siembra de forma permanente** (`prod_only`, `destructive`,
`cost`, decididos en onboard y escritos en `boundaries[].na`). Los dos deterministas
(`no_credentials`, `unreachable`) son transitorios: quedan registrados en `verified[]` para que
`integration` los enumere, pero el siguiente slice **vuelve a intentar** el intercambio.

Fuera de ese catálogo **no hay `na`**: «no me dio tiempo» y «ya lo probaré luego» no son razones.
Y ningún `na` es un verde silencioso — la **custodia está en los datos**: el gate `integration` del
Release Gate (`releasing-a-version`, `release-dod.md`) enumera
`boundaries[].verified[?status == "na"]` y exige que cada uno quede cubierto por el journey con
dependencias reales o declarado como **riesgo de la release**.

## 7. Ausente ≠ vacío

- **`boundaries` ausente** de la configuración → el proyecto nunca declaró sus fronteras. **No
  siembres** el checklist: deja el slice en `change`, con un hito en `progress_log[]` y este mensaje
  único: «fronteras sin declarar: corre `/build:onboard` (Fase 2d) o añade `"boundaries": []` a
  `config/build-config.json`».
- **`boundaries: []` explícito** → el proyecto declaró que **no tiene** fronteras. N/A legítimo: el
  checklist se siembra con normalidad, sin ningún `BND-*`.

Por eso la plantilla de configuración **no** trae el bloque: la ausencia **es** la señal de migración
para consumidores ya onboardeados.

## 8. Sub-slices

Una forma de mensaje que aparece al construir un sub-slice tardío **se añade** al checklist (append)
y se cierra **antes del primer test contra esa forma**. Añadir un `BND-*` **no es retroceso de
gate**: no reabre gates ya cerrados de la épica; el item nuevo mantiene `tdd` abierto mientras se
construye el sub-slice en curso, que es donde vive la forma nueva.

## 9. Cuerpos crudos: opcionales y fuera de git

El estado solo lleva **hashes**. Si el consumidor quiere conservar los cuerpos para depurar, van a
`.claude/state/happy-path/` — el bloque `.gitignore` que siembra `trycore-build init` ya lo excluye —
y **nunca** al estado, al PR ni a la `evidence` del item. Antes de escribirlos, **redacta** según las
categorías declaradas en `SENSITIVE_DATA_CATEGORIES` (CLAUDE.md del consumidor, sembrado en la Fase 2
del onboard): un cuerpo con datos regulados no se guarda, se resume.

## 10. Modos: `legacy`, `dual` y `runtime`

Un `BND-*` es un item de `wiring_checklist[]` **como cualquier otro**: no tiene protocolo propio.
Lo que cambia por modo es **dónde** se escribe.

- **`legacy`** (default): los items y el hito viven en el fichero local de estado
  (`.claude/state/build-state.json`, protocolo del modo `legacy`), con su patrón de escritura de
  siempre.
- **`dual` / `runtime`**: los items viajan por el cliente, nunca a mano —
  `bash .claude/hooks/build/slice-ops.sh wiring seed --file items.json` al sembrar y
  `bash .claude/hooks/build/slice-ops.sh wiring update BND-… passing --kind integration_point --ref boundary:<id>#<forma> --evidence-file f`
  al cerrar; el hito es `bash .claude/hooks/build/slice-ops.sh progress «…»`. La caché de
  proyección es una **lectura**: no se siembran items en ella a mano.
- **`boundaries[].verified[]` se escribe SIEMPRE en el `config/build-config.json` local**, en los
  tres modos: es configuración del proyecto (como `context` o `runtime`), no estado del slice, y el
  hub no la conoce.

**Recuperar `(frontera, forma)` sin `ref`.** La caché de proyección normaliza cada item a
`{item_id, kind}` y **descarta `ref`**. Como el `id` es `BND-<boundary.id>-<message_kind>` y ambas
partes llevan guiones, **no partas por el primer guion**: quita el prefijo `BND-` y busca entre los
`boundaries[].id` de la config el que sea **prefijo más largo** del resto; lo que sigue a ese
`<id>-` es la forma de mensaje. Los ids son únicos y los conoce la config, así que el emparejamiento
es unívoco. Ejemplo: `BND-doc-extraction-api-extract-document` con la frontera
`doc-extraction-api` → forma `extract-document`.

## Delimitación rápida

`BND-*` prueba que **el camino contra la frontera existe**. No prueba que la salida cumpla el esquema
(eso es `data`), ni que nuestras capas estén cableadas entre sí (eso es el `integration_point` propio
en `dod`), ni que el journey completo corra con dependencias reales (eso es `integration`, en el
Release Gate). La tabla completa está en [`dod.md`](dod.md).
