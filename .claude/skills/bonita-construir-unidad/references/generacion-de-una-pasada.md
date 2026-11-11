# Generación de una pasada: qué lee y qué escribe `tools/arnes.sh generar`

El generador de esta versión del arnés **no genera por unidad**. Lo cargan las skills de componente
(`bonita-construir-bdm`, `bonita-construir-organizacion`, `bonita-construir-parametros-y-entornos`,
`bonita-construir-proceso`, `bonita-construir-subproceso`, `bonita-construir-contratos-y-operaciones`,
`bonita-construir-conectores`) antes de su primera fase `green`.

## Lo que lee (todo o nada)

`tools/arnes.sh generar` construye una sola spec con:

- `docs/07-bonita/bdm.md`, `bpmn.md`, `contratos.md` y `handoff.md` (este en `estado: listo-para-construccion`, con
  sus cinco gates en `pasa`, igual que `gates.bonita` de `docs/.flow-state.json`);
- `docs/08-construccion/expresiones.md`, `consultas.md` y `caminos.md` (al menos un «Camino `<id>`»);
- `.trycore-bonita.json` (nombre, grupo, versión, edición de destino).

Si falta un fichero, una expresión que la documentación pide, la JPQL de una consulta o un camino, sale **2**, lista
cada error (`fichero › sección › fila`) y **no escribe nada**. `matriz-formularios.md` no lo lee: los formularios son
de la unidad 4 y de las familias.

## Lo que escribe (siempre todo a la vez)

`bonita-project/bdm/bom.xml`; `bonita-project/app/organizations/<nombre>.xml` (y borra `hola.xml`);
`bonita-project/app/profiles/<perfil>.xml`; un `bonita-project/app/diagrams/<Pool>-<versión>.proc` y un
`bonita-project/app/process_configurations/<id del pool>.conf` por pool (y borra los de `hola`);
`journey/<nombre>.postman_collection.json`; `build/generados.json` y `build/spec.json`. La lista exacta de lo que
cuenta como generado está en `tools/arnes/generadores/generados.py`. En el ejemplo `vacaciones`, la primera pasada
escribe 2 `.proc`, 2 `.conf`, la organización, un perfil, el BDM y el journey de 4 caminos.

## Qué devuelve `tools/arnes.sh verificar` en cada estado

| Estado del proyecto | Salida |
|---|---|
| Sin ningún fichero en `docs/07-bonita/` (plantilla sola) | 0: solo vigila `hola` |
| Con `docs/07-bonita/` y sin los tres ficheros de `docs/08-construccion/` | 2: «no se puede verificar: falta docs/08-construccion/…» (no es un rojo válido) |
| Con toda la documentación y sin generar | 1: `check_inventario` nombra objetos y pools que faltan; `check_generados`, ficheros que faltan |
| Generado y sin tocar | 0 |

Por eso, antes de pedir un rojo, crea los tres ficheros de `docs/08-construccion/` (aunque sea solo con su cabecera):
así `verificar` pasa de 2 a 1 y nombra lo que falta.

## Consecuencia para las unidades (v1)

Como `generar` no tiene alcance, en v1 **la unidad que genera es `U1` «Datos, organización y procesos»**: su fila del
plan lleva en **Ficheros** todo lo de arriba (subprocesos incluidos, y `mock.json` si hay conectores) y en **Entrada**
`bdm.md`, `bpmn.md` y `contratos.md` (`plan-de-unidades.md`). Dentro de `U1` corren todas las skills de componente
salvo `bonita-construir-plantilla`, que es de `U0`. `U2` y `S-<subproceso>` están **reservadas**: no se proponen
mientras no haya generación por alcance. `U1` necesita `docs/08-construccion/` **completo** (consultas, expresiones de
compuertas, constraints, operaciones y conectores, y los caminos); esa carpeta siempre se puede escribir.

Antes de la primera `generar` de la unidad, compara la lista de arriba con la línea `ficheros:` del claim:

- **La cubre** (`U1` de un plan v1, o una unidad posterior: `generar` reescribe los mismos ficheros y solo cambian los
  que tocan las fuentes de la unidad; el diff lo dice) → sigue.
- **No la cubre** (un plan anterior a v1 que reparte BDM y procesos entre `U1`, `U2` y `S-…`) → es el hueco conocido
  **«generación por alcance»** (abajo). No generes ni commitees los ficheros de otra unidad: anota, escala y para
  (`huecos-del-arnes.md`), con dos salidas para la persona: (1) **ajustar el plan** a la forma v1 (recomendada; se
  propone con `slice-ops.sh graph-sync` y lo aprueba el ADMIN); (2) esperar un arnés con generación por alcance
  (`trycore-bonita update`).

## Hueco conocido: generación por alcance

| Elemento | Salida del arnés | Estado |
|---|---|---|
| Generar solo una parte de la documentación (el BDM sin los procesos, un pool sin los demás) | no hay opción: `generar` lee todo y escribe todo; sin las piezas de otra unidad sale 2 | abierto; mientras tanto, la forma v1 del plan (`U1` genera todo) |
