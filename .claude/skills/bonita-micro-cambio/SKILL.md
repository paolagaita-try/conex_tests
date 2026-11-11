---
name: bonita-micro-cambio
description: Carril ligero de micro-works del hub para mantenimiento que no es capacidad nueva en un proyecto Bonita — corregir un defecto contra un criterio o un camino ya escritos, un texto, una configuración, la documentación de construcción. Sin DoR, sin change OpenSpec ni gates; fases in_progress, pr y done con slice-ops.sh micro-fase. Sale del carril (micro-escalar) si el cambio toca el BDM o un contrato, añade una dependencia o una API, cambia un criterio, o necesita más de 3 ficheros de documentación (en un proyecto adoptado en modo existente, cambios documentados y confirmados sobre lo existente van por este carril: ver «Modo existente»). Úsala con /bonita:bugfix, /bonita:microwork o cuando un claim devuelva work_type micro_work.
---

# Micro-cambio — el carril de micro-works del hub

Un typo en el nombre de una tarea, un mensaje de un conector, un defecto que hace fallar un camino ya documentado o un
ajuste de `docs/08-construccion/` **no son una unidad**: forzarlos por las once fases de `bonita-construir-unidad` es
ceremonia. El hub tiene para eso un carril propio, el **micro-work**: trabajo acotado, con su propio lease, una máquina
de fases reducida (`in_progress` → `pr` → `done`) y **sin gates**. Los guardarraíles deterministas (hooks) siguen
igual.

Dos modos, un solo decision gate:

| Modo | Entrada | Para qué |
|---|---|---|
| **bugfix** | `/bonita:bugfix` | Un comportamiento observado **viola** algo ya escrito: un criterio de una tarea `T-*.md`, un camino de `docs/08-construccion/caminos.md` o una regla de `contratos.md` |
| **microwork** | `/bonita:microwork` | Mantenimiento sin defecto: textos, configuración, documentación de construcción, una versión de dependencia ya permitida |

## Paso 0 · El micro-work

El micro-work lo da de alta **una persona** (rol de proyecto DEVELOPER o superior) en la consola del hub, con título,
tipo (`fix`, `chore` o `docs`), los ficheros que puede tocar y las tres auto-declaraciones de límites. El agente no lo
crea: lo reclama.

```bash
bash .claude/hooks/bonita/slice-ops.sh claim
```

- La salida empieza por `micro-work:` → es tuyo: anota su id, la `rama`, los `ficheros` y los `límites`.
- Empieza por `unidad:` → el hub te dio una unidad, no un micro-work: sigue `bonita-construir-unidad`.
- `7` → no hay trabajo. Si la persona te pidió un cambio pequeño que aún no está en el hub, pídele que lo dé de alta
  como micro-work (título, tipo, ficheros, límites) y vuelve a reclamar. No hagas el cambio fuera del hub.
- `CHECKPOINT:` presente → continúa desde esa rama y ese commit; no reinicies.
- Códigos de salida (`5` sigue y avisa, `6` para y muestra la razón del hub, `9` registro):
  `../bonita-construir-unidad/references/ciclo-en-el-hub.md`. Aquí `4` significa «no hay micro-work reclamado».

## Paso 1 · Decision gate (obligatorio)

Es un micro-cambio solo si cumple **todo**:

- **No añade capacidad**: corrige, ajusta o mantiene algo que ya existe.
- **Alcance acotado**: una sola preocupación, dentro de los `ficheros` del micro-work.
- **El proyecto ya construye**: `U0` archivada (el bundle se construye y el journey corre). En modo existente: línea
  base creada y `tools/arnes.sh verificar` = 0.

### Límites duros — si el cambio cruza cualquiera, sale del carril

| Límite del hub | En un proyecto Bonita significa |
|---|---|
| `sin_dependencia_nueva` | ninguna dependencia nueva en un `pom.xml` (lo vigila `stack-guard.sh`) ni conector de un tipo nuevo |
| `sin_endpoint_publico_nuevo` | ningún contrato nuevo ni cambiado (inputs o constraints de `contratos.md`): el contrato es la interfaz pública del proceso; ninguna REST API extension, proceso, tarea humana ni formulario nuevos |
| `sin_cambio_de_dominio` | ningún cambio del BDM (`bdm.md`, `bom.xml`) ni de un criterio de una tarea `T-*.md`; ningún camino nuevo en `caminos.md` |

Y dos del arnés:

- **≤ 3 ficheros de documentación** tocados entre `docs/07-bonita/` y `docs/08-construccion/`. Más es una unidad.
- **Journey verde al cerrar**: `tools/arnes.sh verificar` = 0 y `tools/arnes.sh journey` verde.

Si cruzas un límite (o lo descubres a mitad):

```bash
bash .claude/hooks/bonita/slice-ops.sh micro-escalar --motivo "contratos.md: hace falta un input nuevo en 2_revisar" --limite sin_endpoint_publico_nuevo
```

El micro-work queda terminal y el hub crea una **propuesta de unidad** que decide una persona. Para y repórtalo. Sin
`--limite` si lo que desborda es el alcance (más ficheros, varias preocupaciones). **Sin señal, es micro-cambio; con
señal de forma (dependencia, contrato, API), unidad; con señal de requisito (un criterio deja de ser cierto o falta
uno), documentación**: escala con `--limite sin_cambio_de_dominio` y di que el cambio lo decide el arnés de
documentación.

## Modo existente

Si `.trycore-bonita.json` dice `modo: "existente"` (proyecto adoptado con `trycore-bonita init --existente`), cada
cambio **documentado** sobre lo que el proyecto ya tenía va por este carril, con los límites ajustados:

- cambiar el BDM, un contrato, agregar una tarea o un proceso **no** obliga a escalar, siempre que el cambio esté en
  `docs/07-bonita/` (`cambios.md`) y confirmado por una persona en `docs/08-construccion/cambios-confirmados.md`;
- el cierre exige, en lugar de «journey verde»: `cambios-confirmados.md` vigente, `tools/arnes.sh verificar` = 0 y
  `mvn clean install` en verde (no `-Pbundle`); el arnés no corre el journey en este modo;
- **siguen escalando**: una dependencia nueva en un `pom.xml`, un módulo de la plantilla que el proyecto no tiene
  (`parametros-*`, `consultas-api-extension`, formularios Svelte generados) y un cambio que la documentación no
  describe;
- la confirmación la responde **una persona** en su propia terminal, fuera de la sesión (`tools/arnes.sh cambios
  confirmar`, no con `!`); el agente no la ejecuta ni la responde (el hook lo deniega de buena fe; `respondido_por` y
  `fecha` del registro se revisan en el PR). Los micro-cambios sobre lo existente van en serie. Un fichero de la línea base no se edita a mano nunca: solo cambia `generar` con lo confirmado.

El recorrido completo (claim → `mapa` → `cambios.md` → `cambios mostrar` → confirmación → `generar` → `verificar` →
`mvn clean install` → `linea-base actualizar` → `micro-fase done`) está en `references/modo-existente.md`. Lo que el
generador no soporta sobre lo existente es un hueco del arnés (`../bonita-construir-unidad/references/huecos-del-arnes.md`).

## Modo bugfix — cinco pasos

Al empezar: si la `fase` del claim es `claimed`, `slice-ops.sh micro-fase in_progress` y `git switch -c <rama del claim>
main`. Si ya es `in_progress` o `pr` (retomas un micro-work), no repitas la fase (el hub la rechazaría con `6`):
`git switch <rama del claim>` y sigue desde el paso en que quedó (el checkpoint lo dice).

| Paso | Qué | Línea para el PR |
|---|---|---|
| **0 · Anclar** | Localiza lo que el comportamiento **viola**: un criterio Given/When/Then de `docs/04-tareas-proceso/T-*.md`, un camino de `caminos.md` o una regla de `contratos.md`. (a) Lo viola → bugfix, sigue. (b) Coincide con lo escrito → no es un defecto, es un cambio de requisito: escala. (c) Nada lo cubre → si es comportamiento del proceso, falta un criterio: escala; si es texto o configuración, modo microwork | `Cumple: T-xx criterio n` (o `camino <nombre>`, `regla <nombre>`) |
| **1 · Reproducir ejecutando** | Lo más barato que muestre el fallo: el journey de ese camino, una prueba Spock, una llamada a la API del runtime. Guarda la salida. Sin esto no se toca nada | `Reproducción: <comando> → <≤ 5 líneas>` |
| **2 · Arreglar** | El cambio mínimo **en la fuente**: `docs/08-construccion/`, el código propio, o `docs/07-bonita/` (pregunta antes: es la fuente aprobada). Después `tools/arnes.sh generar`. Un generado nunca se edita a mano. Si cambia un proceso, sube la versión del pool | `Cambio: <una frase>` |
| **3 · Re-ejecutar** | La misma ejecución del paso 1 ya no falla | `→ ok tras el fix` |
| **4 · Prueba de regresión** | Si lo anclado ya tenía prueba (un paso del journey, un custodio, un Spock), corrígela para que caiga sin el fix; si no, escríbela. **Valida por reversión**: sin el fix, rojo; con el fix, verde (usa un commit WIP, no `git stash pop` a ciegas). Si pasa igual sin el fix, el carril no cierra | `Cae sin el fix: sí (<comando>)` |
| **5 · PR** | Abajo | — |

## Modo microwork

Al empezar: igual que en bugfix (`micro-fase in_progress` solo si la fase del claim es `claimed`; si no, sigue desde
la fase actual en la rama del claim).

1. Aplica el cambio acotado en la fuente y regenera si toca (`tools/arnes.sh generar`). Si aparece una señal, para y
   escala.
2. Verifica que hace lo que dice (el comando, el journey, la pantalla).
3. **Prueba de regresión solo si cambia comportamiento**, validada por reversión. Un texto o un comentario no la
   necesitan.
4. Si el comportamiento que cambias está cubierto por un criterio o un camino, no es microwork: es **bugfix** si lo hace
   cumplir y una **escalada** si lo contradice.

## Cierre (los dos modos)

1. `tools/arnes.sh verificar` = 0 y `tools/arnes.sh journey` verde. En modo existente: `cambios-confirmados.md` vigente,
   `verificar` = 0, `mvn clean install` en verde y `tools/arnes.sh linea-base actualizar --micro-work <id>` (sin
   journey).
2. Commit (Conventional Commits en español) y `slice-ops.sh micro-checkpoint` (toma rama y commit de git).
3. Push, `gh pr create --base main` con este cuerpo:

   ```markdown
   ## Micro-work <id> — <título> (<tipo>)
   Cumple: <T-xx criterio n | camino <c> | regla <r>>            (solo bugfix)
   Reproducción: <comando> → <≤ 5 líneas> → ok tras el fix        (solo bugfix)
   Cambio: <una frase>
   Cae sin el fix: sí (<comando>)                                 (si cambia comportamiento)
   Límites: sin dependencia nueva · sin contrato ni API nuevos · sin cambio de dominio · <n> de 3 ficheros de documentación
   Journey: tools/arnes.sh verificar = 0 · tools/arnes.sh journey → 0 (<requests>/<assertions>/<fallos>)
   ```

4. `slice-ops.sh micro-fase pr`. Cuando una persona mergea el PR, `slice-ops.sh micro-fase done` (si el merge llega en
   otra sesión, lo hace `/bonita:resume`). El orden de fases es estricto.
5. Reporta con el formato del bloque del arnés en `CLAUDE.md` (lo corto si no hay nada pendiente).

## Qué se mantiene y qué se salta

| Se mantiene (hooks deterministas) | Se salta (por diseño) |
|---|---|
| `gitflow-guard.sh` (rama `fix/` o `chore/` y PR) | DoR, change OpenSpec y `## Trazabilidad` |
| `guard-generados.sh` (nada generado a mano) | gates, wiring y verificador adversarial |
| `stack-guard.sh` y `lint-bonita.sh` | fases de unidad (`phase`, `gate`, `archive` no aplican) |
| journey verde y `verificar` = 0 (en modo existente: `verificar` = 0 y `mvn clean install`) | reflexión post-unidad |

## Reglas duras

- **El decision gate es obligatorio** y decide por señales, no por duda. Cruzar un límite es `micro-escalar`, no una
  excepción.
- **Solo `micro-fase`, `micro-checkpoint` y `micro-escalar`** con un micro-work: `phase`, `gate`, `submit` y `archive`
  son de unidades.
- **En bugfix, sin ancla no hay bugfix.** La línea `Cumple:` es obligatoria; no inventes un criterio.
- **La prueba de regresión vale si cae sin el fix.**
- **Si hay una unidad activa en este árbol**, el micro-cambio va en otro worktree registrado con su propio token
  (`slice-ops.sh register`); no se mezcla en la rama de la unidad.
