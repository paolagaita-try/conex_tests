# El plan de unidades (`docs/08-construccion/plan.md`)

El plan es la lista de unidades de construcción del proyecto. Cada fila es una unidad y, en el hub, una épica del grafo.
Lo **propone** `/bonita:onboard` a partir de `docs/07-bonita/handoff.md` y de las familias de `matriz-formularios.md`,
y se escribe **solo con la aprobación de una persona**. Si `docs/03-backlog/epicas.md` ya trae unidades por familia, el
plan las enlaza en vez de inventar otras.

## Formato (lo lee `trycore-bonita grafo`; no admite variantes)

Una tabla Markdown con **exactamente** esta cabecera, en este orden:

```markdown
| Unidad | Tipo | Título | Depende de | Ficheros | Entrada | Tareas | Estado |
|---|---|---|---|---|---|---|---|
| `U0` | cimiento | Plantilla configurada | — | `.trycore-bonita.json`, `.gitignore`, `.gitattributes`, `bonita-project/**`, `runtime/**`, `hola/**`, `tools/*.sh`, `tools/arnes/**`, `.claude/**`, `CLAUDE.md`, `build/**` | `docs/07-bonita/handoff.md` | — | pendiente |
| `U1` | cimiento | Datos, organización y procesos | `U0` | `bonita-project/bdm/bom.xml`, `bonita-project/app/organizations/*.xml`, `bonita-project/app/profiles/*.xml`, `bonita-project/app/environements/*.xml`, `bonita-project/app/diagrams/*.proc`, `bonita-project/app/process_configurations/*.conf`, `journey/*.postman_collection.json`, `build/**`, `mock.json` | `docs/07-bonita/bdm.md`, `docs/07-bonita/bpmn.md`, `docs/07-bonita/contratos.md` | `T-01`, `T-02` | pendiente |
```

La tabla empieza en la línea de esa cabecera y termina en la primera línea que no empieza por `|`; cada fila tiene las
8 celdas. Encima puede ir un título y una nota de una línea; nada más se lee.

| Columna | Qué lleva | Reglas |
|---|---|---|
| **Unidad** | código, entre comillas invertidas o sin ellas | `U0`…`U4`, `E-<familia>`, `S-<subproceso>` o `SUB` (letras, cifras y guiones); único; ≤ 50 caracteres |
| **Tipo** | `cimiento`, `etapa`, `subproceso` o `subscription` | `U0`…`U4`: `cimiento` o `etapa`; `E-…`: `etapa`; `S-…`: `subproceso`; `SUB`: `subscription` |
| **Título** | texto | obligatorio; ≤ 300 caracteres |
| **Depende de** | códigos de otras unidades separados por «, » | `—` si ninguna; deben existir en el plan; sin ciclos ni dependencia de sí misma; ≤ 50; **`U1` depende de `U0`** |
| **Ficheros** | globs del proyecto que la unidad puede tocar, separados por «, » | **obligatorio** (sin él el hub serializaría toda la cola con `**`); ≤ 200, cada uno ≤ 500 caracteres. No hace falta listar lo que toda unidad escribe siempre: la carpeta de su change OpenSpec, `docs/08-construccion/` y `evidencia/<unidad>/` |
| **Entrada** | rutas de `docs/07-bonita/` de las que deriva | viajan juntas como `docs_ref` (≤ 500 caracteres); el gate `coherence_link` las contrasta con el change |
| **Tareas** | códigos `T-*` de `docs/04-tareas-proceso/` | `—` si ninguna; cada una se vuelve una historia de la épica en el hub, con el título de la primera línea `# ` de su fichero; ≤ 100 |
| **Estado** | texto libre para quien lee | **no viaja al hub**: el estado real de cada unidad está en el hub (`slice-ops.sh status`) |

Lo que deriva `trycore-bonita grafo` de cada fila: `layer` = `FOUNDATIONAL` para `U0`…`U4` (o tipo `cimiento`) y
`BUSINESS` para el resto; `openspec_change` = `<código en minúsculas>-<título en kebab-case>` (el nombre del change y
de la rama de la unidad). El import del ADMIN (`EpicIn`) no guarda `openspec_change` y el claim lo trae null: el cliente
lo deriva igual, de la rama de trabajo que da el hub (`feature/<código>-<slug del título>`), y lo marca como derivado.

## Qué unidades se proponen en v1

`tools/arnes.sh generar` es de una pasada (`generacion-de-una-pasada.md`): escribe a la vez el BDM, la organización, los
perfiles y todos los procesos. Por eso, en v1:

| Unidad | Se propone | Ficheros y entrada |
|---|---|---|
| `U0` | siempre | la plantilla y el arnés instalado: `.trycore-bonita.json`, `.gitignore`, `.gitattributes`, `bonita-project/**` (poms y `hola`), `runtime/**`, `hola/**`, `tools/*.sh`, `tools/arnes/**`, `.claude/**`, `CLAUDE.md`, `build/**`; Entrada `handoff.md`; **sin** organización. Después, `trycore-bonita update` cambia el arnés instalado en su propio micro-cambio o unidad |
| `U1` | siempre; es la unidad que genera | **todo lo que escribe `generar`**: `bonita-project/bdm/bom.xml`, `bonita-project/app/organizations/*.xml`, `bonita-project/app/profiles/*.xml`, `bonita-project/app/environements/*.xml`, `bonita-project/app/diagrams/*.proc` (subprocesos incluidos), `bonita-project/app/process_configurations/*.conf`, `journey/*.postman_collection.json`, `build/**`, y `mock.json` si hay conectores; Entrada `bdm.md`, `bpmn.md`, `contratos.md`; Tareas: las `T-*.md` de las tareas humanas |
| `U2`, `S-<subproceso>` | **no** (reservadas hasta que haya generación por alcance; el código sigue siendo válido para el grafo) | — |
| `U3` | se propone si el proceso lee parámetros o el caso desde formularios o llama a servicios: el **adaptador de parámetros** del proceso (`extensions/parametros-adaptador`), su **extensión de consultas** del caso (`extensions/consultas-api-extension`: lo que la matriz dice que carga cada formulario) y los conectores; Depende de `U1` | `bonita-project/extensions/parametros-adaptador/**`, `bonita-project/extensions/consultas-api-extension/**`, `bonita-project/parametros/**` y lo de conectores; Entrada `contratos.md`, `bpmn.md` e interfaces en `docs/02-flujo-proceso/` |
| `U4` | caparazón: **una Living App por familia de actores** (layout, tema, menús, bandejas, overview de caso; descriptores y esqueletos los genera `generar` desde la sección «Aplicación» de la matriz) y la galería cerrada; Depende de `U1` (y `U3`) | `bonita-project/app/applications/*.xml`, `frontend/src/lib/**`, `frontend/src/forms/_muestra/**`; Entrada `matriz-formularios.md` |
| `E-<familia>` | una por **familia de formularios** de la matriz (sección «Familias y unidades de trabajo», umbral `umbral_campos_unidad_propia`): completa los formularios de la familia sobre su esqueleto; Depende de `U1`, `U3` y `U4` | `frontend/src/forms/<token>/**` de sus formularios (sin `generado/`); Entrada `matriz-formularios.md`, `contratos.md` |
| `SUB` | como en el §6.2 del diseño, con `U1` entre sus dependencias | — |

Dos sentidos de «familia»: la *familia de formularios* da la unidad `E-<familia>`; la *familia de actores* da la app de
`U4`. Un formulario pertenece a las dos (`bonita-construir-formularios`). Parámetros antes que formularios: `U1` (semilla)
y `U3` (adaptador y consultas) van antes de `U4` y de toda `E-<familia>`.

`docs/08-construccion/` no va en Ficheros: toda unidad la escribe. La lista de patrones generados está en
`tools/arnes/generadores/generados.py`; si una versión del arnés la amplía, la fila de `U1` también.

## Del plan al hub

```bash
trycore-bonita grafo                           # valida y escribe el bundle en stdout
trycore-bonita grafo --salida grafo.json       # o en un fichero para el ADMIN
```

Salida: `0` bundle generado; `1` el plan no cumple las reglas (un motivo por línea); `2` no hay plan legible.

- **La primera vez, el grafo lo importa el ADMIN** del hub (consola del proyecto), junto con crear el proyecto
  (`gitflow_policy: github-flow`, `cycle_budget: 2`) y emitir un token por agente. El agente no importa nada:
  entrega el bundle y la lista de pasos, y después comprueba con `slice-ops.sh status` que el grafo está (línea
  `grafo:`).
- **Después, un cambio del plan** (unidad nueva, dependencia, ficheros) se propone, no se impone: edita el plan con
  aprobación, `trycore-bonita grafo --salida grafo.json`, `slice-ops.sh graph-sync --file grafo.json --dry-run` para ver
  la proyección, `slice-ops.sh graph-sync --file grafo.json` para proponerlo y `slice-ops.sh graph-sync-status` para el
  veredicto del ADMIN. Hasta que lo aprueba, el hub sigue con el grafo anterior.
- **Una sola unidad nueva** también puede proponerse con `slice-ops.sh propose-epic --file borrador.json` (el código lo
  asigna el hub al aprobar) y seguirse con `slice-ops.sh epic-status`.
