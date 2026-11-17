---
name: "BUILD: Graph Sync"
description: Propone al hub el re-sync del grafo del proyecto desde los docs de discovery (epicas.md + HU-*.md). El hub calcula el delta y un humano lo aprueba en la consola; nada se aplica sin esa aprobación. Con --check no propone nada: solo consulta el veredicto de las propuestas ya enviadas. Adaptador delgado sobre slice-ops.sh graph-sync/graph-sync-status.
category: Workflow
tags: [build-harness, runtime, backlog, grafo, trycore]
---

# /build:graph-sync — re-sincronizar el grafo del hub con los docs (la aprobación es humana)

El grafo del hub se siembra una vez, con el **import de admin** de `/build:onboard`. A partir de
ahí discovery sigue escribiendo: épicas nuevas en `docs/03-backlog/epicas.md`, historias nuevas
en las `HU-*.md`. Sin este comando, nada de eso llega al hub — y el síntoma es concreto: **todos
los eventos de un slice cuya épica no está en el grafo rebotan** con «la épica no existe en el
grafo del proyecto».

**Regla dura**: el arnés **propone**, un humano **aprueba**. Este comando no muta el grafo; deja
una propuesta con su delta calculado, y hasta que alguien la apruebe en la consola del hub no
cambia ni una arista.

**Entrada (opcional):** `--check`. Sin argumento, el comando **propone** el re-sync.

## Despacho por argumento (léelo antes que nada)

- **Con `--check`** → ve directo al **§0** y luego **salta al §4**. `--check` es una consulta de
  **solo lectura**: no construyas ningún bundle y no propongas nada (§1–§3 no se ejecutan, ni
  siquiera "por si acaso"). Proponer aquí crearía una segunda propuesta del mismo grafo cada vez
  que alguien comprueba el estado.
- **Sin argumento** → §0 → §1 → §2 → §3. El §4 se recorre después, cuando el humano haya
  resuelto la propuesta en la consola (normalmente en otra invocación, con `--check`).

## 0. Precondición

```bash
bash .claude/hooks/build/slice-ops.sh mode
```

- `legacy` → **STOP**: el grafo vive en los documentos y no hay hub con el que sincronizarlo.
- `dual` → **STOP** para proponer, pero aquí **sí hay hub**: el fichero local es el primario y el
  grafo entra por el import de admin. No lo diagnostiques como un problema de conexión. El
  `--dry-run` del §2 sí funciona: úsalo para revisar el grafo antes del corte a `runtime`.
- `runtime` → sigue.

## 1. Construir el JSON de épicas desde los docs

Lee `docs/03-backlog/epicas.md` y las `HU-*.md` y escribe un fichero temporal con **todo** el
backlog vigente, no solo lo nuevo: el hub compara el bundle contra su grafo y calcula el delta,
así que mandar un subconjunto no borra nada pero tampoco describe el proyecto.

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

Es el **mismo formato** que la fase de grafo de `/build:onboard`: si ya lo generaste allí,
reutilízalo. A diferencia de las propuestas de épica, aquí el `code` **sí** viaja: el re-sync es
la puerta de lo que ya tiene identidad en los documentos.

**`docs_ref` por épica — no lo omitas.** Es la ruta (relativa al repo) al documento de discovery
donde vive esa épica, con ancla a su sección: `docs/03-backlog/epicas.md#ep-001` (el ancla es el
código en minúsculas; si cada épica tiene su propio fichero, apunta a ese fichero). El hub lo
guarda y lo enseña en la ficha de la épica; **sin él la consola muestra «La documentación de esta
épica no está disponible» y «Fuente del grafo: sin referencia»**. Además el delta del re-sync
compara `docs_ref`: si todas las épicas llegan sin él, añadirlo después **sí** es un cambio que el
hub detecta — pero omitirlo hoy hace que un re-sync que solo tocó docs responda «ya está al día».

**`acceptance_ref` por historia — mismo trato.** Es la ruta (relativa al repo) al documento con
los AC de esa HU: `docs/04-historias/HU-001.md`. El hub lo guarda y la ficha de la épica lo usa
para la columna de criterios; **sin él todas las historias salen con «Criterios —»** aunque tengan
sus AC en Given/When/Then. El delta del re-sync también lo compara, igual que `title`.

**No inventes ninguna épica ni ninguna capa.** Si un dato falta en los docs, falta en el grafo:
se corrige en discovery, no aquí.

## 2. Revisar antes de proponer (`--dry-run`)

```bash
bash .claude/hooks/build/slice-ops.sh graph-sync \
  --file /tmp/epics.json --from-docs docs/03-backlog/epicas.md --dry-run
```

**Pasa siempre `--from-docs`**: relee el campo `**Depende de**` de cada sección de épica y une
ese grafo al del JSON. Es la única lectura fiable de las dependencias, que la metodología escribe
como prosa; sin él, un backlog lleno de dependencias sale con `depends_on: []` y el Lienzo del
hub queda sin una sola arista.

`--dry-run` imprime el bundle ya proyectado al contrato del hub y **no envía nada**. Revísalo con
el usuario: número de épicas, capas, aristas.

Un `rc 2` aquí no es un fallo del comando: es el bundle incumpliendo el contrato del hub, con un
motivo por línea que nombra la épica y el campo (`layer` ausente, historia sin `code`, techos
excedidos). Corrígelo **en los docs de discovery** y repite. El hub rechaza el grafo entero ante
una sola épica mal formada, así que estas comprobaciones se hacen aquí para no gastar un viaje.

## 3. Proponer

```bash
bash .claude/hooks/build/slice-ops.sh graph-sync \
  --file /tmp/epics.json --from-docs docs/03-backlog/epicas.md
```

| rc | Significado | Qué haces |
|---|---|---|
| `0` | Propuesta creada (el comando enseña el `id` y el delta), **o** el grafo ya estaba al día | Si hay `id`, dile al usuario que queda **pendiente de aprobación humana** en la consola. Si dice «ya está al día», no hay nada que hacer |
| `5` | Encolada, aún sin entregar (sin conexión, o el daemon estaba drenando la cola) | Avisa de que se despachará sola y de que `--check` la sigue |
| `6` | El hub la rechazó (422 con el motivo, 404, o falta `project_id`) | Muestra la razón; **no** reintentes en bucle |
| `2` | El bundle no cumple el contrato, o falta `--file` | Corrige lo que indique el mensaje, en los docs |
| `3` | `legacy`/`dual` | Vuelve al paso 0 |

Un **409 de grafo rancio** no lo verás como error: el comando refresca el contexto y reintenta
una vez con el mismo identificador, para que el hub deduplique en vez de crear una segunda
propuesta del mismo grafo.

## 4. Después de la decisión — `/build:graph-sync --check`

**Aquí aterriza `--check`.** Es mecánico y de solo lectura:

```bash
bash .claude/hooks/build/slice-ops.sh graph-sync-status
```

- `APPROVED` (con la versión de grafo aplicada) → **no hay nada más que hacer**. Las historias
  nuevas entran solas al reparto del claim: no hay que reclamar de otra forma ni tocar el estado.
- `REJECTED` (con el motivo que escribió el ADMIN) → **léeselo al usuario**. El motivo existe
  precisamente para que esta terminal lo lea. Corrige en discovery y vuelve a proponer.
- `PROPOSED` → sigue esperando decisión humana. No propongas otra vez.
- `QUEUED` → aún sin despachar; el daemon de heartbeat la lleva.

## Guardrails

- El arnés **propone**; la aprobación es humana (gobierno, METODOLOGIA §10 regla 8). Ni el
  modelo ni el arnés aprueban un cambio de grafo.
- **No edites `docs/03-backlog/epicas.md` para «arreglar» el bundle.** El fichero es la fuente;
  si el bundle no cumple, lo que está mal es la fuente, y se corrige con el usuario delante.
- **No propongas dos veces sin mirar `--check`.** Dos propuestas del mismo grafo esperando
  aprobación es exactamente el ruido que este carril evita.
- Un `REJECTED` **no** se resuelve reintentando: se resuelve leyendo el motivo.
