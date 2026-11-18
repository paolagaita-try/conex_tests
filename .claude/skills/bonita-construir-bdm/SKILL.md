---
name: bonita-construir-bdm
description: Úsala cuando la unidad del claim construya el Business Data Model (en v1, dentro de U1 «Datos, organización y procesos», la unidad que genera). Lee bdm.md (objetos, atributos, relaciones, unique constraints, consultas, índices, decisión de persistencia), escribe la JPQL en docs/08-construccion/consultas.md, genera bom.xml con tools/arnes.sh generar y lo prueba con check_inventario, check_generados y el journey.
---

# Construir el BDM

Componente del loop (`bonita-construir-unidad`). Produce `bonita-project/bdm/bom.xml` desde `docs/07-bonita/bdm.md`;
el `bom.xml` es **generado**: nunca se edita, se cambia la fuente y se regenera. Antes de la primera `green`, lee
`../bonita-construir-unidad/references/generacion-de-una-pasada.md`: `generar` escribe el BDM junto con todo lo demás.

**Dónde corre (v1):** dentro de `U1` «Datos, organización y procesos», la unidad que genera; `generar` es de una pasada y escribe a la vez BDM, organización, perfiles y todos los procesos. `U2` y `S-<subproceso>` están reservadas (no se proponen).

## Lo que lees

`docs/07-bonita/bdm.md` (plantilla `bdm-bonita.template.md` v0.8.0 del arnés de documentación):

| Sección | Qué toma el generador |
|---|---|
| «Convenciones» | la línea **Paquete** con un paquete Java válido entre comillas invertidas; el título de cada objeto no puede decir otro |
| «Objetos de negocio» | una subsección por objeto titulada «`Objeto` (paquete `x.y.z`)»; su tabla de atributos (columnas Atributo, Tipo, Obligatorio, Múltiple, Longitud, Relación); las líneas **Unique constraints** e **Índices** («;» separa entradas, «,» combina atributos, lo que va entre paréntesis se ignora salvo «(nombre `X`)»); la tabla de consultas (Consulta, Parámetros, Devuelve) |
| «Decisión de persistencia» | filas «Business variables del pool» (`solicitud: Solicitud`, una por agregado raíz) y «Plantilla de persistencia» (`asignacion-directa`) |
| «Impacto de objetos añadidos tras el cierre» | si la capa se reabrió: qué objetos entraron después (solo cambios aditivos) |

`docs/07-bonita/handoff.md` § «Insumos de construcción…»: «Decisión de persistencia» y «Plantilla de persistencia» en
`fijado` (lo exige el DoR). «Organización», «Parámetros» y «Acceso al BDM › Perfiles previstos» son de
`bonita-construir-organizacion` y `bonita-construir-parametros-y-entornos`.

Reglas del lector que conviene saber (fallan con 2 en `generar`, nombrando la fila):

- **Tipos** admitidos: `STRING`, `TEXT`, `INTEGER`, `DOUBLE`, `LONG`, `FLOAT`, `DATE`, `BOOLEAN`, `BYTE`, `SHORT`,
  `CHAR`, `LOCALDATETIME`, `LOCALDATE`, `OFFSETDATETIME`, o el nombre de otro objeto con su relación. La plantilla
  v0.8.0 marca `[no verificado]` los tipos distintos de `STRING`, `TEXT`, `BOOLEAN`, `DATE`, `DOUBLE`; el arnés los
  comprobó contra `bom.xsd` 1.2.2 de Bonita 2026.2 (el ejemplo `vacaciones` los usa).
- **Longitud** solo en `STRING`. **Obligatorio** y **Múltiple**: `sí` o `no`.
- **Relación**: empieza por `composición` o `agregación`; si trae cardinalidad (`0..n`, `1..1`), debe coincidir con
  Múltiple y Obligatorio.
- **Consulta** (R-05): «`nombre`» (propia, JPQL en `consultas.md`) o «`nombre` (por defecto…)» (la genera Bonita: sin
  JPQL, no va a `bom.xml`; su nombre debe ser `find`, `findByPersistenceId`, `findBy<Atributo>` de un atributo simple o
  `findBy<A>And<B>` de una unique constraint, y si está en `consultas.md` es error). Parámetros «`nombre` (TIPO)»
  separados por «, ». Devuelve `lista`, `lista paginada`, `uno` o `conteo`, con paréntesis explicativo opcional:
  `conteo` → `returnType="java.lang.Long"`; `lista paginada` es una `lista` que exige en el mismo objeto
  `countFor<Nombre>` (mayúscula inicial) con Devuelve `conteo` y los mismos parámetros (doc 2026.2
  `define-and-deploy-the-bdm.adoc`: «for a query named `query1`, the count query must be named `countForQuery1`»; la
  de una consulta por defecto la crea Bonita). `lista` a secas no la exige.

```markdown
| Consulta | Parámetros | Devuelve | Quién la necesita (bandeja, tarea, página) |
|---|---|---|---|
| `findBySolicitante` (por defecto, atributo simple) | `solicitante` (STRING) | lista | … |
| `findMisSolicitudes` | `solicitante` (STRING) | lista paginada | bandeja |
| `countForFindMisSolicitudes` | `solicitante` (STRING) | conteo | paginación de la anterior |
```

Medido en Community 2026.2-u0 (D-35, D-36): `countFor…` con `java.lang.Long` responde `{ "value": n }` por REST; las por
defecto `findBy<Atributo>`, `findBy<UniqueConstraint>`, `find`, `findByPersistenceId` y `countForFindBy<Atributo>`
responden sin estar en `bom.xml`; una lista paginada da `Content-Range: 0-2/<total>`. Un nombre que Bonita no genera
responde 500.

## Lo que escribes: `docs/08-construccion/consultas.md`

Una fila por consulta propia de `bdm.md`, con su mismo Devuelve (`lista paginada` incluido) y sus mismos parámetros
(las «(por defecto)» las genera Bonita: no van aquí). Formato (el del ejemplo `vacaciones`):

```markdown
# Construcción — consultas JPQL de <proceso>

| Consulta | Objeto | Parámetros | Devuelve | JPQL |
|---|---|---|---|---|
| `findPendientesPorEmpleado` | `Solicitud` | `empleado` (STRING) | lista | `SELECT s FROM Solicitud s WHERE s.empleado = :empleado AND s.estado = 'pendiente' ORDER BY s.persistenceId ASC` |
```

Una consulta con el **mismo nombre en varios objetos** (`findBySolicitud` en `DecisionActividad` y en `Modificacion`)
va en una fila por objeto: la clave de `consultas.md` es (Objeto, Consulta) y Bonita acota el nombre a su objeto
(D-101: el validador del BDM solo la rechaza repetida en el mismo objeto y genera `@NamedQuery(name =
"<Objeto>.<consulta>")`). Repetir el par sí es error.

Solo `SELECT`; cada `:parámetro` es un parámetro de la fila; Bonita añade `startIndex` y `maxResults` a las de
`lista`. Un error de JPQL no lo detecta `generar` (no la analiza): aparece al construir o desplegar el BDM
[no verificado]. Por eso el `smoke` es obligatorio aunque `verificar` esté verde.

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | `consultas.md` completa; los tres ficheros de `docs/08-construccion/` existen; `tools/arnes.sh verificar` = 1 | `[check_inventario] bom.xml: falta el objeto «X» que declara bdm.md` por objeto y `[check_generados] bonita-project/bdm/bom.xml: distinto…` |
| `green` | Comprobar la cobertura de `ficheros` (pasada única); `tools/arnes.sh generar` = 0; `tools/arnes.sh verificar` = 0 | las mismas líneas, ahora `[check_inventario] verde` y `[check_generados] verde` |
| `refactor` | Ordenar `consultas.md` sin cambiar ninguna JPQL; `generar` no produce diff | `git diff --stat` vacío en lo generado |
| `smoke` | `tools/arnes.sh journey`: el BDM se despliega con el bundle y cada camino lee su objeto de la REST API | requests, assertions y fallos |
| `api` | En `U1` lo cierra `bonita-construir-contratos-y-operaciones` para toda la unidad | — |
| `data` | Agente `bonita-verificador-datos` contra `bdm.md` y `consultas.md` | su informe |

- **Spock**: la plantilla `asignacion-directa` no tiene librería de persistencia (una operación por atributo, sin
  helpers compartidos): el criterio «pruebas de la librería de persistencia verdes» va como «no aplica: plantilla
  `asignacion-directa`, sin código propio». Una plantilla del proyecto (persistencia por helpers, R-07): las pruebas
  de su biblioteca de helpers (Spock del módulo de `extensions/`, p. ej. `ejemplos/compras/…/compras-helpers`) van en
  el criterio.
- **Nombres de índices y unique constraints** (D-100): los pone el arnés, `IX_<OBJETO>_<ATRIBUTOS>` /
  `UK_<OBJETO>_<ATRIBUTOS>`. Bonita admite una letra y hasta 25 letras ASCII, dígitos, `_`, `#` o `@` (26 caracteres)
  y no una palabra bloqueada de SQL; si el nombre completo no cabe, el arnés lo trunca con una huella estable
  (`IX_MODIFICACION_SOL_1F9EBD`). Para fijarlo a mano, «(nombre `IX_MOD_SOL_FRESP`)» detrás de la entrada
  (`` `solicitud`, `fechaRespuesta` (nombre `IX_MOD_SOL_FRESP`; lo pide la bandeja) ``); un nombre explícito inválido o
  repetido en el BDM (también frente a los `IX_KP_*`/`UK_KP_*` del módulo de parámetros) es error de `generar`.
- **Qué vigila cada custodio**: `check_inventario` compara objetos y atributos de `bdm.md` con `bom.xml` (no tipos ni
  longitudes); `check_generados` exige que `bom.xml` sea byte a byte lo que genera la documentación, que es lo que
  fija tipos, longitudes, obligatoriedad, unique constraints (`UK_…`), índices (`IX_…`) y consultas. Los dos juntos
  son el «inventario 1:1 con tipos y longitudes fijados».

## Wiring

Además de los caminos, reglas e integraciones de `U1`, un item `kind: salida` por criterio del BDM en su gate de salida:

```json
[{"item_id": "SAL-U1-inventario-bdm", "kind": "salida", "ref": "docs/07-bonita/bdm.md#objetos-de-negocio"},
 {"item_id": "SAL-U1-bdm-desplegado", "kind": "salida", "ref": "evidencia/U1/journey.txt"},
 {"item_id": "SAL-U1-persistencia", "kind": "salida", "ref": "docs/07-bonita/bdm.md#decisión-de-persistencia"}]
```

| Gate | Evidencia |
|---|---|
| `tdd` | rojo: `verificar` → 1 con las líneas de objetos que faltan; verde: `generar` → 0 y `verificar` → 0 |
| `data` | informe del verificador: cada objeto, atributo, tipo, longitud, relación, unique constraint, índice y consulta de `bdm.md` contra `bom.xml` y `consultas.md` |

## Trampas

- **Cambios del BDM solo aditivos** una vez desplegado fuera del bundle: cambiar Obligatorio o Múltiple exige un *clean
  deploy* del BDM. El bundle del journey se extrae limpio en cada corrida y no lo detecta: si el cambio no es aditivo,
  dilo en la evidencia (riesgo para QA y Producción).
- La primera generación reemplaza el `Saludo` de `hola`; con él se van el `.proc` de `hola` y su `.conf`.
- Un solo paquete por proceso; el título de cada objeto repite el de «Convenciones».
- Los nombres `UK_…` e `IX_…` no tienen límite de longitud en el generador: un nombre de objeto y atributos muy largo
  puede chocar con el límite de la base de datos de QA [no verificado].

## Subscription

- **BDM access control** (`bdm.md › Acceso al BDM › Mecanismo` = «BDM access control por perfil») es solo
  Subscription (doc 2026.2 `build-run/build-application.adoc:20`) y **el generador no lo produce** (no lee
  «Mecanismo»). Si el documento lo elige: hueco del arnés y, en la evidencia, «pendiente de prueba en Subscription:
  BDM access control»; en `SUB`, un item de wiring `kind: subscription`.
- Con consultas directas o REST API extensions (unidad 3): nada pendiente en el BDM.
