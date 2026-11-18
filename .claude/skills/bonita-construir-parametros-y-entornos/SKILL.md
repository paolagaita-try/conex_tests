---
name: bonita-construir-parametros-y-entornos
description: Úsala cuando la unidad del claim construya parámetros (param_* del catálogo), en v1 dentro de U1 «Datos, organización y procesos». Los de negocio van al módulo de parámetros con su semilla (desde docs/00-parametros/catalogo-parametros.md); los técnicos, a parámetros de proceso con sus valores por entorno (Local, Qualification, Production). Lee bdm.md › Parámetros, genera la semilla, el .conf y los valores embebidos en el .proc, y los prueba con el journey y con el build de cada entorno.
---

# Construir parámetros y entornos

Componente del loop (`bonita-construir-unidad`). Regla de fondo: **negocio en el módulo, técnico en el `.conf`**.

| Representación (columna del catálogo y de `bdm.md`) | Qué es | Dónde vive |
|---|---|---|
| «módulo de parámetros» | valor que negocio administra: tramos, topes, listas, plazos, textos | el módulo (`parametros-core` + `parametros-api-extension`) con su **semilla** `bonita-project/parametros/semillas/<proceso>.json`, que `generar` escribe desde `docs/00-parametros/catalogo-parametros.md` |
| «parámetro de proceso» | valor técnico por entorno: URL de un servicio, duración de un timer | el pool: `.conf` (Local) y `configurations` del `.proc` (Qualification y Production) |

Los formularios **nunca** usan `processParameter` para valores de negocio: leen `GET …/API/extension/parametros/valores`
(`bonita-construir-formularios`) con el id de su tarea o, en el formulario de instanciación, con
`instanciacion=<id de la definición del proceso>` (el servidor deduce el proceso y la familia del iniciador). El `.proc` lee los de negocio con los helpers de `parametros-core`
(`ParametrosDeProceso`), no por REST. Lo que sigue de este documento se refiere, salvo que se diga lo contrario, a los
parámetros **de proceso**.

**Lectura desde el proceso (R-13).** La interfaz es una sola: `ParametrosDeProceso.usar(apiAccessor,
processDefinitionId, activityInstanceId, rootProcessInstanceId, "<definición>", "<campo o regla>", padre = "*",
tipo = null)` (y `usarConFoto`, igual más el ámbito y la versión del valor que ganó). El proceso y la actividad los saca
del motor; la resolución va actividad → proceso → global y gana el más específico. **`padre = "*"` es el comodín**: el
valor que no cuelga de ninguna opción de una lista padre (las filas con `codigoPadre = "*"`); es el equivalente de un
`resolverTramo` con las dimensiones vacías. Con `padre = "<código>"`, el valor de esa opción del padre (un
`tramo-cascada`). Sirve igual desde scripts, filtros, helpers y conectores del proyecto: no hay fachada con otros nombres
(`obtenerValor`, `listarOpciones`…).

**`ParametroAplicado` es condicional.** Solo hace falta si el proceso debe **congelar** los valores vigentes al abrir el
caso (que un cambio posterior en la app de parámetros no afecte a los casos abiertos): entonces es un objeto del dominio
que **declara `bdm.md`** (sin esa declaración `check_inventario` no lo ve) y lo escribe una operación con lo que devuelve
`usarConFoto`. Si el proceso lee el valor vigente en cada uso, `ParametrosDeProceso.usar(…, padre = "*")` funciona sin
él y `bdm.md` no lo declara. La app de administración de parámetros se genera igual (U23).

Un parámetro de proceso de Bonita es **del pool**: vive en su `.proc` (los
valores de Qualification y Production, embebidos como `configurations`) y en su `.conf` (los de Local). No existe sin el
proceso: entra con la generación que escribe los `.proc` (ver
`../bonita-construir-unidad/references/generacion-de-una-pasada.md`). Todo lo que produce es **generado**.

**Dónde corre (v1):** dentro de `U1` «Datos, organización y procesos», la unidad que genera; `generar` es de una pasada y escribe a la vez BDM, organización, perfiles y todos los procesos. `U2` y `S-<subproceso>` están reservadas (no se proponen).

## Lo que lees

| Fuente | Qué toma el generador |
|---|---|
| `bdm.md` § «Parámetros (del catálogo) con representación en Bonita», primera tabla `param_*` | por fila: **Tipo en el catálogo** (`String`, `Integer`, `Boolean` o `Double`), **Representación** (exactamente «parámetro de proceso»), **Objeto / parámetro de proceso** («`<Pool>` › `param_x`») |
| `bdm.md` § «Parámetros», tabla de valores por entorno (columnas `param_*`, Local, Qualification, Production) | un valor por entorno; los de Integer, Double y Boolean se validan |
| `docs/00-parametros/catalogo-parametros.md` | solo para cruzar: cada `param_*` del catálogo con representación en Bonita tiene su fila |
| `bpmn.md` § «Eventos» y § «Conectores por tarea» | dónde se usa cada parámetro (duración de un timer, URL de un conector) |

La **tabla de valores por entorno no está en la plantilla `bdm-bonita.template.md` v0.8.0**; el lector la exige si hay
algún parámetro (`generar` sale 2 «falta la tabla de valores por entorno»). Añadirla es editar `docs/07-bonita/`:
para y pregunta, y regístralo como hueco del arnés
(`../bonita-construir-unidad/references/huecos-del-arnes.md`): formato de la plantilla distinto del lector.

## Lo que hace el generador

- **Local** → `process_configurations/<id del pool>.conf`. **Qualification y Production** → `configurations` dentro del
  `.proc`, con su actor mapping, sus `definitionMappings` y sus parámetros: sin ellas el build de Qualification avisa
  «configuration not found» y «No actor mapping found».
- Los ficheros `environements/Qualification.xml` y `Production.xml` son de la plantilla (no se editan).
- Un timer cuya duración es un `param_*` Integer se genera como script `as Long` sobre el parámetro.
- Los valores **no** van en el `.bar`: viajan en el `.bconf` que acompaña al zip de la aplicación (el bundle del journey
  lo aplica; un despliegue a QA o Producción debe entregar los dos).
- Un formulario no lee `processParameter` para nada de negocio (ni directamente ni por `/API/bpm/processParameter`): lee
  el módulo (arriba). Un parámetro técnico no llega al formulario.

## Parámetros de negocio: módulo y semilla (U23)

- **Qué lee `generar`:** cada fila del catálogo con Representación «módulo de parámetros» (clases `valor`, `tramo`,
  `lista`, `tramo-cascada`) -> definición y valores de la semilla; escribe además el bloque `familia.interna.actores` de
  `bonita-project/parametros/configuration.properties` (solo ese bloque es generado) y el equivalente de la extensión de
  consultas, con el **Actor Bonita** de cada lane que tiene actor y los actores de tarea (el módulo compara con el actor
  de la tarea del `.proc`). Un `tramo-cascada` nombra su lista padre con «depende de `param_x`» (obligatoria si trae
  «opción: valor»; sin parejas, un valor solo o pendiente, puede ir sin padre). Una fila sin valor (`[PENDIENTE]`) queda
  como TEXTO con fallback: complétala en el catálogo, no en la semilla.
- **Formas de «Valor(es)» (contrato §2.18) y cómo se leen:**

  | En el catálogo | En el módulo | Desde el proceso / el formulario |
  |---|---|---|
  | lista `` `1` Política; `2` Productividad `` | LISTA con código `1` y etiqueta «Política» (sin clave: código = slug de la etiqueta) | `usar(…, "<lista>", …)` → `opciones[].codigo/etiqueta`; `GET …/valores?definicion=<lista>` |
  | `` `2` Abierto: estadoVisible=Registrada, activa=true `` | un PARAMETRO por campo, `<lista>.estado_visible` y `<lista>.activa` (BOOLEANO), que dependen de la lista; INTERNA | `usar(…, "<lista>.estado_visible", …, padre = "2")` |
  | tramo-cascada `` `1`: supervisor1=`ana`, directora=`luis` `` | `<tramo>.supervisor1`, `<tramo>.directora`, dependientes de la lista padre; **no** hay `<tramo>` | `usar(…, "<tramo>.supervisor1", …, padre = "1")` |
  | `tramo-cascada (depende de `param_empresas`; niveles `area`, `puesto`)` con `` `1` › `a1` Área uno › `p1` Puesto uno `` | una LISTA por nivel: `<tramo>.area` (depende de la lista padre), `<tramo>.puesto` (depende de `<tramo>.area`); CLIENTE | `GET …/valores?definicion=<tramo>.puesto&padre=a1`; `usar(…, "<tramo>.puesto", …, padre = "a1")` |

  Las claves se guardan en minúsculas (el módulo normaliza los códigos): `padre = "correosyp"`, no `"CorreoSYP"`. Lo que no
  se puede sembrar sin perder información (opción repetida, clave inválida, campo mal escrito, opción que no es del padre,
  parejas sin lista padre, una clave en dos padres del mismo nivel…) es un error de `generar` con su fila del catálogo:
  se corrige la documentación (medido en el bundle: D-110, D-111).
- **«Quién administra»:** cada rol que nombra el catálogo debe **existir** en la organización del proceso
  (`bonita-construir-organizacion`); `generar` los reúne en el perfil `AdministracionParametros` (solo Subscription) y da a cada usuario de esos roles una
  membership más con el rol `superAdministradorParametros`, el único que reconoce el módulo para escribir (la app
  `parametros` va con el perfil `User`). Un rol que
  no existe es un error de `generar` (no inventa roles): se corrige la documentación, no el generado.
- **Doble control:** por cada rol con doble control se siembran **dos usuarios de prueba** (`<rol>1` y `<rol>2`), para que el journey pruebe
  proponer y aprobar con personas distintas.
- **Adaptador por proceso** (`extensions/parametros-adaptador`, de `U3`): la plantilla trae su esqueleto; la clave
  `usos.conteo.clase` de `configuration.properties` apunta a su `ConteoDeOpciones` (quita el `#` al añadir la clase).
- **Semilla aplicada:** la aplican la API en su primera llamada y `ParametrosDeProceso.usar` en el primer uso (D-113);
  a demanda, `POST …/API/extension/parametros/semilla/aplicar`.
  `GET …/parametros/valores` debe responderla antes de abrir una unidad de formularios.
- Un usuario con el rol `superAdministradorParametros` (los de «Quién administra» lo reciben al generar) mapeado al
  perfil `User` lee y escribe; el usuario técnico `install` recibe 403 por diseño. El mapeo al perfil `User` no viaja en
  el artefacto Community: lo hace `tools/arnes.sh perfiles [--url …]` tras cada despliegue (y `run-journey.sh` antes
  de Newman).

## Fase a fase

| Fase | Trabajo | Evidencia |
|---|---|---|
| `red` | Con toda la documentación y sin generar: `tools/arnes.sh verificar` = 1 | `[check_generados] bonita-project/app/process_configurations/<id>.conf: falta…` (y el `.proc` del pool) |
| `green` | Cobertura de `ficheros` (pasada única); `generar` = 0; `verificar` = 0; build de Qualification y de Production (abajo) | las mismas líneas en verde; `BUILD SUCCESS` sin los dos avisos |
| `smoke` | `tools/arnes.sh journey`: cada camino que pasa por un parámetro lo usa con el valor Local (en el ejemplo, `vencida` espera el timer de `param_plazoRevisionMs` y `aprobada` llama al mock por `param_urlSaldo`) | requests, assertions y fallos de esos caminos |
| `api` | En `U1` lo cierra `bonita-construir-contratos-y-operaciones` | — |
| `data` | En `U1`, el informe del verificador de datos de toda la unidad | — |

Build de cada entorno (no lo hace `tools/arnes.sh`; es Maven directo, con JDK 17):

```bash
export JAVA_HOME="${BONITA_JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
for e in Qualification Production; do
  mvn -f bonita-project/pom.xml -B clean install -Dbonita.environment=$e > evidencia/<unidad>/build-$e.txt 2>&1 \
    && ! grep -E "configuration not found|No actor mapping" evidencia/<unidad>/build-$e.txt \
    && echo "$e: verde"
done
```

La línea `[INFO] Skipped. …/.bcd_configurations/parameters-<entorno>.yml parameters file not found` es informativa (un
override externo opcional): no es un aviso.

## Wiring

Un parámetro usado por una regla o un conector ya tiene su item en el wiring de la unidad del proceso (`kind: regla` o
`integracion`). Aquí, un item `kind: salida` por entorno y uno por parámetro sin otro uso:

```json
[{"item_id": "SAL-parametros-local", "kind": "salida", "ref": "docs/07-bonita/bdm.md#parámetros-del-catálogo-con-representación-en-bonita"},
 {"item_id": "SAL-entorno-qualification", "kind": "salida", "ref": "evidencia/<unidad>/build-Qualification.txt"},
 {"item_id": "SAL-entorno-production", "kind": "salida", "ref": "evidencia/<unidad>/build-Production.txt"}]
```

## Trampas

- **La semilla se aplica en la primera llamada a la API de parámetros o en el primer `usar`, no al desplegar** (D-112,
  D-113): hasta la 0.11.0 solo la aplicaba la API, y un script que llamaba a `usar` antes de que un formulario o el
  journey llamara a `…/API/extension/parametros/…` recibía `ParametroNoDisponible` y la tarea quedaba `failed`. Ahora
  `ParametrosDeProceso.usar`/`usarConFoto` aplican antes la semilla pendiente que viaja en el classpath del proceso
  (`semillas/*.json` del jar del adaptador), con la misma operación idempotente que la API. No hace falta ningún paso
  de despliegue. **El módulo `parametros-adaptador` en `app/pom.xml` es lo que lleva la semilla al proceso** (D-113):
  no lo quites. Sin él, el proceso no ve `semillas/*.json` y vuelve el fallo de D-112; `verificar` (custodio de
  inventario) avisa si falta la dependencia. El mismo jar da a `Fallbacks` las semillas con su nombre real
  (`semillas/<proyecto>.json`).

- **Tipos de parámetro** de Bonita 2026.2 (doc `data/parameters.adoc`): texto, Boolean, integer y double. Un plazo en
  milisegundos cabe en Integer hasta 2 147 483 647 (unos 24 días); Long no es un tipo de parámetro y la duración del
  timer es el parámetro tal cual (sin Groovy propio): un plazo mayor es un hueco del arnés.
- La URL de un servicio externo siempre en un parámetro, nunca literal en el Groovy: así Local apunta al mock
  (`http://localhost:8099/...`) y QA al servicio real sin recompilar.
- Cambiar un valor Local cambia el `.conf`; cambiar el de otro entorno cambia el `.proc`: **sube la versión del pool**
  en `bpmn.md` si la definición cambia, o el runtime sigue con la vieja.

## Subscription

**Los entornos distintos de Local son solo Subscription** (doc 2026.2 `ROOT/key-concepts.adoc:56`,
`process/configuring-a-process.adoc:9`). Aquí se prueba que **construyen** (Maven con `-Dbonita.environment`), no que
corran: la evidencia dice «pendiente de prueba en Subscription: entornos Qualification y Production en runtime». En
`SUB`, un item `kind: subscription` por entorno.

## Lo que el arnés no soporta (hueco, no se rodea)

- **Un `tramo` (sin cascada) con «clave: valor»** se siembra como un solo texto (así lo usa `ejemplos/compras`): si las
  claves son opciones de una lista, decláralo `tramo-cascada (depende de `param_x`)`.
- **Representaciones distintas de «módulo de parámetros» y «parámetro de proceso»** (p. ej. «objeto de negocio de
  catálogo»): `generar` sale 2 «no soportada».
- **Parámetro de negocio con fila en la tabla de valores por entorno:** la fila se ignora en silencio; el valor vive en
  el catálogo.
- **«Quién administra» en texto libre:** el generador parte la celda por «,», «/», «;» y « y » (un rol como «Gerencia y Riesgos» se parte); usa los nombres de rol tal cual
  están en la organización.
- **Administradores por parámetro:** cada rol de «Quién administra» se vuelve **superadministrador de todo el módulo**
  (`superAdministradorParametros` edita todos los parámetros, no solo los de su fila). Si la documentación pide que un
  rol administre solo algunos parámetros, es un hueco: anótalo.
- **Otro tipo de parámetro** que `String`, `Integer`, `Boolean` o `Double`: sale 2.
- **Un entorno adicional** (otra columna en la tabla de valores): el lector solo lee Local, Qualification y Production
  y **la ignora sin error**. Si la documentación la trae, es un hueco aunque `generar` salga 0: anótalo.
- El «kit de parámetros» por entorno para operación (un `.bconf` versionado por entorno) no lo genera el arnés: el
  `.bconf` sale del build.
