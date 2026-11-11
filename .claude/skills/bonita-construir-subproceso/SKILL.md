---
name: bonita-construir-subproceso
description: Úsala cuando la documentación tenga un pool llamado por una call activity (un «subproceso»): en v1 se construye dentro de U1 con su padre (S-<subproceso> está reservada). Lee la subsección del pool llamado en bpmn.md y contratos.md y la call activity del padre, genera su .proc en la misma pasada que el padre con tools/arnes.sh generar y lo prueba con su gate de proceso más el journey del padre que lo llama.
---

# Construir un subproceso (dentro de `U1`)

Componente del loop (`bonita-construir-unidad`). En Bonita no hay subproceso embebido: un «subproceso» es **otro
pool** (su propio `<Subproceso>-<versión>.proc` y su `.conf`) que el padre llama con una **call activity**; mientras
corre, el padre espera, y no comparten process variables (los datos pasan por el contrato de instanciación del
llamado). Todo lo que construye es generado, en la misma pasada que el padre:
`../bonita-construir-unidad/references/generacion-de-una-pasada.md`.

**Dónde corre (v1):** su `.proc` y su `.conf` se generan en `U1` junto con el padre; la unidad `S-<subproceso>` está
reservada (no se propone) mientras no haya generación por alcance. Su gate es el de `U1`: el del proceso más el
journey del padre que lo llama.

Esta skill añade lo propio del pool llamado; el trabajo de cada sección es el de `bonita-construir-proceso` y, para
sus contratos, `bonita-construir-contratos-y-operaciones`.

## Lo que lees

| Fuente | Qué toma el generador |
|---|---|
| `bpmn.md`, en **cada** sección | la subsección «`<Subproceso>` versión» (pool y lanes, inventario, compuertas, eventos, transiciones, conectores, process variables, documentos) |
| `bpmn.md` § «Pool y lanes» › subproceso | **Iniciador**: «—» (lo instancia la call activity) |
| `bpmn.md` § «Inventario de tareas» › padre, fila de la call activity | Tipo `call activity`; **Notas** con «Llama a `<Subproceso>` <versión>»; **Operaciones previstas** con un «`Objeto.atributo` → `input`» (o «`pv variable` → `input`») por input del llamado |
| `contratos.md` § «Contrato de instanciación» › subproceso | los inputs que recibe y a qué process variable van (`pv numero`); su línea «Operaciones al instanciar:» |
| `contratos.md` § «Contratos de tarea humana» | los `ctr_<tarea>` de sus tareas; si un ID de tarea se repite en dos pools, la línea **Tarea** lleva «(pool `<Subproceso>`)» |
| `matriz-formularios.md` (solo para cruzar) | su formulario de instanciación es «No form» (ningún usuario lo abre) |

## Lo que hace el generador

- Una call activity con `calledActivityName` y `calledActivityVersion` del llamado y un `inputMapping` de tipo
  `ContractInput` por input: el origen tiene que ser **del mismo tipo** que el input (2 si no) y todo input obligatorio
  del llamado tiene que recibir valor.
- El pool llamado **no tiene business variables** (son del pool principal): no escribe el BDM por variable; guarda lo
  que recibe en process variables.
- No hay mapeo de salida: el llamado no devuelve datos al padre.
- Un timer de borde puede colgar de la call activity (sí de ella, no de una tarea de servicio).
- Comprobado en Community 2026.2-u0 con el ejemplo `vacaciones`: el mapeo `ContractInput` y la tarea del llamado vista
  desde el caso raíz del padre.

## Lo que escribes en `docs/08-construccion/`

- `expresiones.md`: las condiciones de sus compuertas, sus constraints y sus scripts (formato de `bonita-construir-proceso`).
- `caminos.md`: los caminos son **del pool principal**. El subproceso se recorre dentro de los caminos del padre que
  pasan por la call activity, con sus tareas humanas como pasos (en el ejemplo, `1_leerNotificacion` como paso 3 del
  camino `aprobada`). Su evento de fin no es un «Fin esperado»: el del camino es el del padre.

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Subsecciones del llamado completas en `expresiones.md` y los pasos de sus tareas en los caminos del padre; `tools/arnes.sh verificar` = 1 | `[check_inventario] <Subproceso>: falta en el .proc el pool que describe bpmn.md` y `[check_generados] …/<Subproceso>-<versión>.proc: falta…` |
| `green` | Cobertura de `ficheros` (pasada única: el `.proc` **y su `.conf`**); `generar` = 0; `verificar` = 0 | custodios en verde |
| `smoke` | `tools/arnes.sh journey`: todos los caminos, y en especial los del padre que pasan por la call activity | requests, assertions, fallos; las tareas del llamado completadas |
| `api` | El contrato de instanciación del llamado lo ejerce la call activity (no hay llamada REST directa); los de sus tareas, como en `bonita-construir-contratos-y-operaciones` | los pasos del journey en el llamado y un rechazo por constraint |
| `data` | Verificador de datos: cada input del llamado recibe el origen que dice el inventario del padre | su informe |

## Wiring

Además de los items del pool llamado (caminos que lo atraviesan, reglas de sus compuertas y contratos), uno por mapeo
de la call activity:

```json
[{"item_id": "INT-4b_notificar-NotificarDecision", "kind": "integracion", "ref": "docs/07-bonita/bpmn.md#inventario-de-tareas"},
 {"item_id": "CAM-aprobada", "kind": "camino", "ref": "docs/08-construccion/caminos.md#camino-aprobada"}]
```

`INT-…` pasa con el camino del padre que llega a una tarea del llamado (prueba que se instanció con el contrato) y la
termina.

## Trampas

- **`check_caminos` solo mira el pool principal**: las salidas de las compuertas del llamado y sus fines no se
  comprueban solos. Si el llamado tiene compuertas, cada salida debe aparecer en algún camino del padre; dilo en la
  evidencia y el verificador adversarial lo revisa.
- **Versión**: si cambia el llamado, sube su versión **y** la de «Llama a `<Subproceso>` <versión>» del padre (y la del
  padre, porque cambia su `.proc`).
- Un *terminate end* no lo genera el arnés; recuerda que en Bonita terminaría todo el caso, y solo en un llamado devuelve el control al padre.
- IDs de nodo: únicos por pool; un nombre de tarea repetido en dos pools confunde la búsqueda del journey por nombre.

## Subscription

Nada del subproceso es solo Subscription.

## Lo que el arnés no soporta (hueco, no se rodea)

Inputs `COMPLEX` o `FILE` en el contrato del llamado (no hay origen del mismo tipo que mapear), **mapeo de salida**
hacia el padre, business variables o escritura del BDM en el llamado, event subprocess y lo que no soporta
`bonita-construir-proceso`. Sigue `../bonita-construir-unidad/references/huecos-del-arnes.md`.
