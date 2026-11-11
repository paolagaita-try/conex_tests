# Contratos anidados, destinos nuevos y documentos de proceso

Referencia de `bonita-construir-contratos-y-operaciones` para R-06 (contratos) y R-09 (documentos e inputs FILE) del
Plan 5. Formato: `docs/plan-5/contrato-de-formato.md` §2.0, §2.7 y §2.10. Mediciones: `conocimiento/compatibilidad-2026.2.md`
(D-50 a D-58).

## Hijos de un COMPLEX (`contratos.md`, columna «Hijos (si COMPLEX)»)

```
HIJOS := HIJO («; » HIJO)*
HIJO  := nombre «(» TIPO [«, » sí|no [«, múltiple»]] «)» [«[» HIJOS «]»]
```

- **Forma vieja** `dias (INTEGER)`: hereda la obligatoriedad del padre, no es múltiple y su constraint es la de
  siempre (`mandatory_solicitudInput_dias`: `solicitudInput?.dias != null`).
- **Forma nueva** `telefono (TEXT, no)`, `categorias (TEXT, sí, múltiple)`: obligatoriedad **propia**. La constraint
  `mandatory_<ruta con _>` dice «si llega el padre, el hijo no es nulo» (`padre == null || padre.hijo != null`, en cada
  elemento de un padre múltiple y a cualquier profundidad). Un padre opcional nulo se acepta; un hijo obligatorio nulo
  con el padre presente da 400 con el mensaje `<ruta> es obligatorio` (D-51).
- `[…]` solo tras `COMPLEX`, y un hijo `COMPLEX` siempre los lleva: `topes (COMPLEX, sí, múltiple) [categoria (TEXT, sí);
  maximo (DECIMAL, sí)]`. Dos niveles medidos en el motor (D-50); más, `[no verificado]`.

## Destino (columna «Destino»)

| Forma | Qué hace el generador |
|---|---|
| `` `Objeto.atributo` ``, `` `pv x` `` | operación por input (como siempre) |
| ``doc. `documento` `` | solo inputs FILE: inicializa el documento (instanciación) u operación de documento (tarea) |
| ``op. `op_<ctx>.<bv>` `` | ninguna operación por input: lo consume la operación de variable completa (hilo `persistencia`) |
| `— (solo lectura…)` | ninguna: el input lo lee una constraint o una operación del mismo contexto |

- Un input COMPLEX lleva un destino **entero** (`op.` o solo lectura) o «hijo → destino» por cada hijo; si tiene hijos
  COMPLEX, solo el entero.
- `— (solo lectura)` es error si ni una constraint del contrato ni una operación Groovy del contexto nombran el input
  (o su raíz). Un «—» a secas, o «— (otra explicación)», sigue siendo «input sin destino».
- El motor exige **todos** los inputs del contrato en el cuerpo (los opcionales a `null`): sin ellos, 400 «Expected input
  [x] is missing» (D-52). El formulario generado los manda siempre; un journey escrito a mano también debe.

## Contrato vacío

Sin tabla de inputs o con la fila de relleno «— | — | …»; la línea «Operaciones al instanciar:» sigue siendo
obligatoria. `generar` escribe un `process:Contract` sin inputs (igual que el de una tarea sin inputs, que sí corre en
el journey de vacaciones); en la instanciación, `[no verificado]` en el motor (D-58).

## Documentos del proceso (`bpmn.md › Documentos del proceso › `Pool` versión`)

| Documento | Múltiple | Atributo del BDM | Tarea que lo aporta | Tareas que lo leen | Fuente en §12 |
|---|---|---|---|---|---|
| `cotizacion` | no | `Solicitud.cotizacionId` | (instanciación); `2_revisarJefe` | — | T-1 |
| `soportes` | sí | — | `2_revisarJefe` | — | T-2 |

- «Tarea que lo aporta» debe ser **exactamente** el conjunto de contextos cuyos inputs FILE llevan ``doc. `<documento>` ``.
- Un FILE que da varios archivos (FILE múltiple, o hijo de un COMPLEX múltiple) va a un documento `sí`; uno simple, a
  uno `no`. Un documento recibe como mucho un input por contexto.
- «Atributo del BDM» es informativa: se comprueba que existe y es `LONG`. Escribir en él el ID del documento no lo hace
  el arnés: lo hace una operación (script o helper de `persistencia`, también la de la business variable entera)
  **posterior** de la misma tarea, que ya ve el documento
  (`apiAccessor.processAPI.getLastDocument(processInstanceId, 'cotizacion').id`; en una lista, `getDocumentList`). Lo
  ve aunque la tarea lo cree por primera vez porque la operación de documento generada lo escribe por la API al
  evaluarse (ver abajo, D-114, D-115). El ID no cambia entre versiones del documento (D-56).
- **En la instanciación no**: las operaciones de instanciación (valor inicial de la business variable) no ven el
  documento que inicializa el contrato (D-57). El ID de un documento aportado al instanciar se guarda en la primera
  tarea o en una tarea script posterior a la instanciación (en `ejemplos/compras`, `2_asignarComprador`). Si el Groovy
  de una operación de instanciación nombra ese documento (identificador o cadena), `generar` sale 2 con un error que
  cita D-57; lo que lea un helper por dentro no se ve desde la documentación: es responsabilidad del helper.

## Lo que genera (`generadores/escribir/proc/documentos.py`)

- `process:Document` por fila, en el pool (`multiple="true"` en las listas).
- **Instanciación** (Bonita no tiene operaciones de instanciación): `documentType="CONTRACT"` y `contractInput` = el
  `ContractInput` del FILE, también si es hijo de un COMPLEX (y de un COMPLEX múltiple: lista con un documento por
  elemento que trae archivo; el que llega sin archivo no crea documento) (D-53).
- **Tarea humana**: una operación por documento **antes** de las demás: operando izquierdo `DOCUMENT_REF_TYPE` y
  operador `DOCUMENT_CREATE_UPDATE` (simple: nueva versión del mismo documento) o `DOCUMENT_LIST_SET` (lista) (D-54).
- **El documento se escribe al evaluar su operación**, no al final. El motor evalúa primero los operandos derechos de
  todas las operaciones de la tarea, en orden, y solo después persiste los izquierdos (`OperationServiceImpl.execute`:
  `executeOperators` → `updateLeftOperands`); sin más, un documento nuevo de la tarea no existe todavía cuando se
  evalúa la operación siguiente (D-114: `DocumentNotFoundException` en el helper, 6 ms antes de que el motor cree el
  documento). Por eso el script de la operación de documento lo escribe por la API del caso (`addDocument` si no
  existe, `updateDocument` si existe; `setDocumentList` en una lista, con cada FILE convertido como lo hace el motor) y
  devuelve al motor el documento ya escrito sin cambios (`DocumentValue(id)`), que el motor deja como está (D-55,
  D-115). Un FILE con `id` y sin contenido (el formulario reenvía el vigente) va al motor tal cual, como antes.
  Consecuencia: el documento queda con autor `-1` (la sesión del script); quién lo subió, si importa, va al BDM
  (D-116).
- **FILE nulo**: el motor **borra** el documento si la operación devuelve `null`; la operación generada devuelve en
  su lugar el documento vigente (`DocumentValue(id)` sin cambios), así que un FILE nulo conserva lo que había (D-55,
  medido en el simple; en la lista, misma lógica `[no verificado]` en el motor).
- `check_inventario` compara documentos, multiplicidad y `documentType` con `bpmn.md`, e inputs por ruta a cualquier
  profundidad.

## Formulario generado

`contrato.ts` y `esquema.ts` recorren los hijos a cualquier profundidad (una interfaz por COMPLEX anidado,
`EntradaCatalogoInputTopes`), un campo de la matriz puede escribir `a.b.c` y un FILE dentro de un COMPLEX múltiple viaja
como su referencia subida (`API/formFileUpload`, D-52). Un input de solo lectura que ningún campo escribe llega por el
tercer parámetro `externos` de `cuerpoDelContrato` (la pantalla lo rellena, p. ej. desde el módulo de parámetros). Un
hijo obligatorio de un COMPLEX opcional no exige campo. Límite: un FILE múltiple de un campo sube un archivo (lista de
uno).
