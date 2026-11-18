# Compatibilidad del conocimiento con Bonita 2026.2

Contraste entre lo que afirma el conocimiento heredado del piloto (destilado en Bonita 10.x y 11.x, comprobado en
Studio Community 2025.2-u0) y la documentación oficial 2026.2. Este repositorio construye sobre Community 2026.2-u0
(runtime 11.1.0) y el Studio Subscription 2026.2-u3 (ver `convenciones.md`).

**Regla de arbitraje**: ante discrepancia entre el conocimiento y la doc 2026.2, gana la doc; ante conflicto entre la
doc y el Studio o runtime real, **el real es el árbitro** (verificación empírica). Cada diferencia nueva se anota en
la tabla. Para leer la doc, usar el MCP `bonita-doc-index`; sin él, `[no verificado]`.

Marcas de `Comprobado en:` como en `patrones-bonita.md`. Las filas D-xx conservan la numeración del piloto porque
`convenciones.md` las cita.

## Contraste inicial con la documentación 2026.2

**Origen:** contraste del piloto contra la doc oficial (páginas `import-and-export-a-process`,
`define-and-deploy-the-bdm`, `expressions-and-scripts`, `events`).
**Comprobado en:** doc 2026.2 (lectura); 2025.2 en uso real. En este repositorio, 2026.2 solo lo que ejercen los
generadores y el e2e (`bom.xml`, Groovy, `.proc`).

| Afirmación | Página oficial 2026.2 | Veredicto |
|---|---|---|
| Se puede importar un `.bpmn` (BPMN 2.0) en el Studio | `import-and-export-a-process` | Confirmado |
| Los elementos no soportados al importar se degradan: tarea no reconocida a tarea abstracta, compuerta no soportada a AND, evento múltiple al primer elemento interpretable | Misma página | Confirmado |
| Estructura del `bom.xml` (`businessObjectModel`, `businessObjects`, `fields` con `type/nullable/length/collection`) | `define-and-deploy-the-bdm` | Confirmado |
| Las queries por defecto las genera Bonita; las de negocio se añaden a mano (solo SELECT; `countForQueryX` para paginar) | Misma página | Confirmado |
| Groovy es el lenguaje de las expresiones | `expressions-and-scripts` | Confirmado |
| Eventos: timer de frontera (interruptor y no interruptor), catch message (también de frontera), terminate end | `events` | Confirmado |

## Diferencias de modelado (D-01 a D-10)

**Origen:** contraste del piloto contra la doc 2026.2 (`diagram-tasks`, `event-subprocesses`, `events`, `gateways`,
`called-processes`, `execution-sequence-states-and-transactions`).
**Comprobado en:** doc 2026.2 (lectura); 2025.2 D-09 en un import real. Ninguna fila se ha reprobado aún con un
runtime 2026.2 en este repositorio: [pendiente 2026.2].

| # | Supuesto | Qué dice la doc 2026.2 | Impacto |
|---|---|---|---|
| D-01 | Existe subproceso embebido | Los tipos de tarea son human, service, **call activity**, script, abstract, send, receive. El único subproceso dentro del pool es el event subprocess | Un `<subProcess>` en un `.bpmn` generado no se importa tal cual. «Subproceso con N ramas» es un proceso llamado en pool aparte más una call activity |
| D-02 | El event subprocess puede no interrumpir | Al arrancar, **aborta el proceso padre** (estado ABORTING en las demás ramas activas) | No hay event subprocess no interruptor. Usarlo para cancelar ramas hermanas mata el resto del pool: la continuación se re-modela dentro de él |
| D-03 | Los timers de frontera valen para cualquier actividad | Un timer de frontera, interruptor o no, solo va sobre **tarea humana o call activity** | No aplican a `serviceTask`. Para dar plazo a una tarea automática: envolverla en una call activity o usar un boundary de error |
| D-04 | El orden de las condiciones de un XOR no importa | «Se usa la primera transición cuya condición sea verdadera» | El orden de las ramas es semántico: da precedencia entre reglas sin eventos de interrupción |
| D-05 | Se puede desviar un token de una rama de un fork | En un AND, «todas las entradas deben recibirse» | Un boundary interruptor o un fin sobre una rama que alimenta un join AND cuelga el caso |
| D-06 | Hay eventos de cancelación y compensación | La tabla de eventos solo trae none, message, timer, signal, error y terminate end | «Cancelar» se modela con error y event subprocess, terminate end, proceso llamado o por enrutamiento |
| D-07 | Un terminate end cierra solo una rama | Marca el fin de **todos** los flujos del proceso | Termina el caso completo; solo es seguro dentro de un proceso llamado (el flujo vuelve a la call activity) |
| D-08 | El start signal vale en un event subprocess | La doc es inconsistente: la definición lo permite; el paso «Define» exige message, timer o error | Start signal en event subprocess: **no confirmado**. Probar en el Studio antes de comprometerlo |
| D-09 | Existe `parallelGateway` en el import | Confirmado en el XSD embebido del Studio (`tParallelGateway`) y por import real | Plantilla AND válida; fork y join simétricos |
| D-10 | Un proceso llamado comparte datos con el padre | Mientras corre, el padre está pausado; los datos pasan por **mapeo** (se recomienda un contrato en el llamado) | No comparte variables de proceso (el BDM sí): exige contrato, mapeo y despliegue del segundo proceso |

## Importación, actores y datos (D-11 a D-13)

**Origen:** inspección del importador del Studio del piloto (`BPMNToProc`) y reimport real; lo que cierra los huecos
lo hace este repositorio generando el `.proc` directamente.
**Comprobado en:** 2025.2 (reimport sin error y validación limpia tras el parche). En 2026.2 este repositorio
**no importa BPMN**: genera el `.proc`, de modo que estas filas solo valen si algún día se vuelve a importar;
[pendiente 2026.2].

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-11 | El importador crea los actores del pool (`performer` de `process`) y las lanes (horizontales; las verticales dan aviso), pero **descarta** el actor por tarea y no asigna actor a las lanes | Tras un import hay «No actor defined»; la asignación actor a lane se cierra a mano o con un parche idempotente del `.proc` con el Studio cerrado |
| D-12 | Las variables de proceso **sí** se importan: `dataObject` más `itemDefinition` (`structureRef` xsd:string, boolean, integer, decimal, date...) | Toda variable de una `conditionExpression` debe existir como `dataObject` |
| D-13 | Los servicios síncronos de formulario no se pintan como `serviceTask`: el formulario llama a una fachada (external API a REST API extension), la respuesta viaja en el contrato y se persiste por operaciones (patrón 1.5 de `patrones-bonita.md`) | Menos tareas y compuertas; el diagrama deja de declarar pasos que no ejecuta. En macOS el workspace del Studio vive dentro del bundle: `<Studio>.app/Contents/Eclipse/workspace/<proyecto>/app/diagrams/<nombre>-<versión>.proc` |

## Conectores y Groovy generados (D-14, D-15)

**Origen:** verificación empírica contra la plataforma real en el piloto; reverificadas en este repositorio
(`tests/test_proc_conectores.py`, `tests/test_proc_flujo.py`, `tests/e2e/`).
**Comprobado en:** 2025.2 (piloto) y 2026.2 (este repositorio: `definitionMappings` y orden del conector, ver
`convenciones.md`). La versión del artefacto del conector REST se fija en `versiones/2026.2.json`.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-14 | El motor resuelve la implementación de un conector por `<definitionMappings type="CONNECTOR" definitionId=… implementationId=…/>`; `bonita2bar` compara el tipo con el literal **en mayúsculas**. Con minúsculas el `.impl` no entra al `.bar`, el proceso queda «unresolved» y el runtime aborta el arranque con «The connector … has no implementation». El conector REST **no viene** en el runtime: se declara como dependencia Maven y el plugin lo descubre por `bonita-dependencies.json`. Las versiones de definición no coinciden entre verbos (en 2025.2: `rest-get` 1.2.0, `rest-post` 1.3.0). `rest-get` no expone fail-on-status ni reintentos. La API REST de Bonita exige cookie de sesión | Se verifica por construcción: tipo en mayúsculas y dependencia declarada. Un login previo por tarea (`rest-post`) cuando un conector llama a la API de Bonita |
| D-15 | En Groovy `return x` cierra la sentencia: las líneas siguientes que empiezan por `+` son código muerto silencioso (el script compila y no hay error en ningún log; la URL viaja incompleta) | En scripts generados, una sentencia por línea y el operador al **final** de la línea anterior, o `StringBuilder`; nunca un operador al principio de línea |

## Módulo de parámetros y formularios Svelte (D-16 a D-22)

**Origen:** Plan 4: spike del módulo de parámetros en 2026.2 (tareas 1 a 5) y journey de «hola» con su formulario (tarea 11).
**Comprobado en:** 2026.2 (runtime 11.1.0, bundle Community 2026.2-u0): lo marcado como medido. PostgreSQL no se midió.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-16 | El módulo de parámetros (`parametros-core`, `parametros-api-extension`) funciona en 2026.2 **sin cambios de versión** (Groovy 3.0.25, Spock 2.3-groovy-3.0, byte-buddy 1.14.5, H2 1.4.200, servlet 4.0.1); `GET parametros/definiciones` responde 200 con un usuario de la familia interna | No hay rama de versión para el módulo; se copia tal cual |
| D-17 | El usuario técnico `install` recibe **500** en el módulo: falta la query `getUserMembershipsWithRole` en 11.1.0. Con la guarda `if (idUsuario < 0) return []` (`MembresiasBonita`) pasa a **403**, por diseño | Las comprobaciones usan un usuario con el rol `superAdministradorParametros` (`generar` lo da a los usuarios de «Quién administra») mapeado al perfil `User` por `tools/arnes.sh perfiles` tras el despliegue, nunca `install` |
| D-18 | Sin la línea `profile\|User=[parametros_lectura, parametros_escritura, consultas_lectura]` en `custom-permissions-mapping.properties` el filtro de autorización REST responde **403** aunque el usuario sea de la familia correcta | Una sola línea por perfil (los permisos de cada extensión se fusionan en ella); el fichero entra al bundle y también a Docker QA (`runtime/Dockerfile`). La línea vale para quien está en el perfil `User`, y ese mapeo no viaja en un artefacto Community: lo hace `tools/arnes.sh perfiles` tras cada despliegue |
| D-19 | `/API/bpm/formMapping` responde 403 o 404; el recurso que sirve es **`/API/form/mapping`** (`?f=processDefinitionId=…&f=type=TASK`) | El journey y cualquier comprobación de mapping usan `form/mapping` |
| D-20 | `formMapping type="URL"` hacia `/bonita/portal/resource/app/<app>/<token de página>/content/` y el recurso `custompage_<token>` con token alfanumérico funcionan en 2026.2 (medido en «hola»); los zips viajan por `app/pom.xml` a `target/pages`, nunca por `web_page/` | Regla de nombre, copia y mapping verificadas en 2026.2 (eran [no verificado] tras 2025.2) |
| D-21 | Sin `frontend/dist-zips/` Maven solo dice «skip non existing resourceDirectory» y termina en verde, sin las páginas | `run-journey.sh` construye el frontend antes y falla si falta el zip de un formulario de negocio |
| D-22 | La forma de la respuesta de `POST /API/formFileUpload` y su permiso **no se han verificado** en un runtime 2026.2 (el ejemplo de vacaciones no tiene campos `FILE`) | El formulario envía `{filename, tempPath, contentType}`: [no verificado] en 2026.2; probar con el primer proceso que tenga un `FILE` |
| D-23 | Una Living Application cuyo `profile` no existe en el runtime **aborta la instalación entera** (`LIVING_APP_REFERENCES_UNKNOWN_PROFILE`, «At least one application failed to be installed»: el bundle no arranca). Medido en Community 2026.2-u0 con `profile="AdministracionParametros"`; Community no admite perfiles propios (`include.profiles` y crear perfiles son de Subscription) | La app `parametros` de la plantilla va con el perfil `User` y administra quien tiene el rol `superAdministradorParametros`; `tools/arnes.sh perfiles` mapea los perfiles propios solo si el runtime los tiene |

## El proyecto en el Bonita Studio (D-24 a D-29)

**Origen:** prueba visual del ejemplo vacaciones en el Studio Subscription 2026.2-u3 (5 de noviembre de 2026), que dio
`tools/arnes.sh studio` (`plantilla/tools/studio.py`) y `default_profile.xml`.
**Comprobado en:** Studio Subscription 2026.2-u3 (motor 11.1.0, H2 1.4.200).

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-24 | El Studio solo clona un repositorio cuyo **proyecto Bonita está en la raíz** («The Git repository content must include a Bonita project»); un proyecto del arnés lo tiene en `bonita-project/` | `tools/arnes.sh studio` mantiene una copia espejo (`../<nombre>-studio`, git local) con `bonita-project/` en la raíz y `frontend/` dentro; `app/pom.xml` busca los zips en `../../frontend/dist-zips` y en `../frontend/dist-zips` |
| D-25 | Dos proyectos con el mismo id no conviven en el workspace del Studio: «A project with id <nombre> already exists in the workspace» | Para tener dos versiones abiertas, la segunda se genera con otro `--nombre` |
| D-26 | El Deploy del Studio entra con su «Default user name», `walter.bates` por defecto, y falla si la organización no lo tiene («Unable to retrieve the password of walter.bates in the active organization») | Toda organización generada trae a `walter.bates` con el rol `administrador` (`con_administrador_studio`) |
| D-27 | Sin `app/profiles/default_profile.xml` el Studio crea uno que mapea los perfiles al rol `member` de su organización de ejemplo; al reiniciar el servidor ningún usuario del proyecto tiene perfil («No profile has been set up for this user») | El arnés genera siempre `default_profile.xml`: User a todos los roles, Administrator y Process manager al rol `administrador`. Un reinicio o un Deploy del Studio borra además los mapeos hechos por REST: `tools/arnes.sh studio` los repone |
| D-28 | El Deploy del Studio **no** despliega lo que el arnés mete en el artefacto con Maven: REST API, páginas Svelte (`pages/` del artefacto) y aplicaciones; el formulario de inicio da 404. Subidas por REST (`portal/pageUpload` + `API/portal/page`, `portal/applicationsUpload` + `services/application/import`), funcionan (el motor avisa de que la subida de páginas está «deprecated») | `tools/arnes.sh studio` las sube en orden: REST API, páginas y aplicaciones. Con otro orden, la página declara recursos que el motor aún no conoce («Unknown resource … defined in page.properties») y se queda sin sus permisos |
| D-29 | El motor del Studio no recibe `app/permisos/custom-permissions-mapping.properties` (D-18): la REST API de parámetros responde 403. Su configuración está en la tabla `configuration` de su H2 (`AUTO_SERVER=TRUE`, admite un segundo proceso) y el motor la lee al arrancar | `tools/arnes.sh studio` fusiona las líneas del proyecto en esa fila y pide reiniciar el servidor del Studio una vez |

## Plan 5 — `organizacion`

Mediciones D-30…D-39.

**Origen:** hilo `organizacion` del Plan 5 (5 de noviembre de 2026): copia de `ejemplos/vacaciones` con grupos en
jerarquía (`/empresa/rrhh/nomina`), un actor con dos roles, tabla de usuarios con *manager* y correo, Actor Bonita
distinto del de negocio, la lane `Sistema` sin actor, un actor de tarea (`aprobador`, rol `JefeArea`) en
`2_revisarJefe`, `fin_rechazada` terminate y las consultas `findByEmpleado` (por defecto), `findMisSolicitudes` (lista
paginada) y `countForFindMisSolicitudes` (conteo). `generar` 0, `verificar` 0 y `tools/run-journey.sh` verde (89
requests, 115 assertions, 0 fallos), después consultas a la API REST con el runtime vivo.
**Comprobado en:** bundle Community 2026.2-u0 (`-Pbundle`, H2). Lo de Subscription y del Studio, no (ver D-37, D-38).

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-30 | El XML con `group name="nomina" parentPath="/empresa/rrhh"`, `<manager>` tras `jobTitle`, `<professionalData><email>` y `<groupParentPath>` en `membership` importa: `API/identity/group?f=parent_path=/empresa/rrhh` devuelve `nomina`; `API/identity/user?f=userName=ana` da `manager_id` = id de `carla`; `professionalcontactdata` trae el correo; las membresías extra de la tabla de usuarios existen | R-01 verificado (O-1) |
| D-31 | Un `actorMapping` por **membresía** incluye los **subgrupos**: `/empresa` + `empleado` da `actorMember` en `/empresa`, `/empresa/rrhh` y `/empresa/rrhh/nomina`, y `API/bpm/process?f=user_id=` lista el proceso para un `empleado` de `/empresa/rrhh` | `candidato()` (y la validación de caminos) cuentan los subgrupos (`en_grupo`) |
| D-32 | Un `actorMapping` con dos `membership` (mismo grupo, roles `jefe` y `JefeArea`) lo aceptan bonita2bar y el motor: `actorMember` de tipo MEMBERSHIP con las dos | Una membresía por rol del actor en el `.conf` (O-2) |
| D-33 | Una `process:Lane` sin `actor` con solo tareas automáticas (service, script, call activity, compuertas y fines) construye con `-Pbundle` y el camino `aprobada` pasa por ella | R-02: lane sin actor verificada (O-3) |
| D-34 | `overrideActorsOfTheLane="true"` + `actor` en una `process:Task`: con el actor de tarea mapeado al rol `JefeArea`, la tarea está en `humanTask?f=user_id=` de `jefe.area` y **no** en la de `carla` (rol `jefe`, actor de la lane) | Actor de tarea verificado (O-4) |
| D-35 | `returnType="java.lang.Long"` de `countForFindMisSolicitudes`: `API/bdm/businessData/<clase>?q=countForFindMisSolicitudes&f=empleado=ana` responde `{ "value": 4 }`; la lista paginada `findMisSolicitudes` con `c=2` da `Content-Range: 0-2/4` | R-05 conteo y paginada verificados (O-6) |
| D-36 | Las consultas por defecto responden sin estar en `bom.xml`: `findByEmpleado` (atributo simple, lista), `findByNumero` (unique constraint, un objeto), `find` (todas), `findByPersistenceId` y `countForFindByEmpleado`. Un nombre que Bonita no genera (`findByNada`) da 500 | «(por defecto)» admite `find`, `findByPersistenceId`, `findBy<Atributo>` y `findBy<A>And<B>` (O-7). `[no verificado: el nombre exacto con una unique constraint de dos atributos]` |
| D-37 | Usuario con punto (`jefe.area`) y rol con mayúsculas (`JefeArea`) importan, inician sesión y ejecutan tareas. El perfil «Jefes de Área» se escribe en `app/profiles/jefes-de-area.xml` y el build pasa; Community no despliega perfiles propios (`tools/perfiles.py` lo omite) | O-8 parcial: `[no verificado: perfil con espacio en el import de Subscription (Studio 2026.2-u3)]` |
| D-38 | `process:EndTerminatedEvent` (vista 3062/5090) despliega, el camino `rechazada` termina en él y la evidencia de fin del journey lo reconoce (`el caso termina en fin_rechazada`) | O-5 en el bundle. `[no verificado: abrir y guardar el .proc en el Studio sin diff]` |

## Plan 5 — `extensiones`

Mediciones D-40…D-49.

**Origen:** hilo `extensiones` del Plan 5 (5 de noviembre de 2026): proyecto `compras` generado con los docs de
vacaciones, los módulos `compras-filtros` y `compras-correo` de `ejemplos/compras` registrados con
`herramientas/registrar_extension.py`, un filtro en la lane `Jefe` y dos invocaciones de `conn_correo` (propio
`correo-smtp`, `IGNORE`) al entrar en `2_revisarJefe`; `mvn install -Pbundle` y casos por la API REST contra un SMTP
sumidero. Lo estático, con `javap` sobre `org.bonitasoft.bonita2bar` 9.0.10 y las fuentes de `bonita-common` 11.1.0.
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0), bonita2bar 9.0.10. El Studio no se abrió.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-40 | `definitionMappings type="ACTOR_FILTER"` es el literal de bonita2bar para un filtro (`ConnectorImplementationArtifactProvider`, junto a `CONNECTOR`): con él, el `.impl` del filtro entra al `.bar` en `userFilters/<impl>-<versión>.impl` (el de un conector, en `connector/`) | `generar_conf` escribe `ACTOR_FILTER` para los filtros y `CONNECTOR` para los conectores |
| D-41 | Un módulo de `extensions/` declarado como dependencia de `app/pom.xml` (patrón de `parametros-adaptador`) entra en `bonita-dependencies.json` y su jar va al classpath de la aplicación junto a `bonita-connector-rest`; el `.bar` es *jarless*. Basta con que el `.impl` nombre su jar en `jarDependencies` (`${project.artifactId}-${project.version}.jar`, filtrado por Maven): el motor carga la clase del filtro y la del conector | `herramientas/registrar_extension.py <proyecto> <módulo>` añade el módulo al pom de extensiones y la dependencia a `app/pom.xml`; el `.def`/`.impl` van en `src/main/resources-filtered/` con `filtering` |
| D-42 | bonita2bar toma el **primer** filtro de la tarea; si la tarea no tiene, el de su lane, con `overrideActorsOfTheLane` o sin él (`EngineFlowElementBuilder.caseTask`). Un `filters` escrito en la tarea antes de `formMapping` construye y corre. Que el Studio abra y guarde el `.proc` sin diff (X-1) **[no verificado]**: el orden EMF de `Task` pone `filters` (Assignable) después de `formMapping` (PageFlow) y antes de `contract`, y el generador ya escribe `operations` en otro orden que el Studio | El generador escribe el filtro efectivo (actor de tarea o lane) en cada tarea humana y nunca en la lane |
| D-43 | Con **un** candidato, la tarea queda asignada a él (`AbstractUserFilter.shouldAutoAssignTaskIfSingleResult()` = true en las fuentes; medido: `assigned_id` del usuario). Con la lista **vacía**, la tarea pasa a **failed** («No user id returned by the user filter», `StateBehaviors.mapUsingUserFilters`) y los conectores «on enter» de la tarea no llegan a correr | Un filtro cuyo dato puede faltar (p. ej. `Solicitud.comprador` sin valor) da un respaldo en su Groovy de entrada (el iniciador, un usuario por defecto) o la tarea queda en fallo, visible y reintentable desde la administración |
| D-44 | Las expresiones de entrada de un filtro ven las business variables del caso (`solicitud.empleado`, referencia `TYPE_BUSINESS_DATA` en la definición del filtro) | Las entradas `flt_<filtro>.<entrada>` de `expresiones.md` leen el BDM como cualquier script |
| D-45 | `ignoreErrors="true"` con el SMTP caído: cada invocación falla («Connection refused», aviso del motor) y la tarea sigue a `ready`; el caso continúa (`connectivity-overview.adoc`: «IGNORE … the task is completed normally») | «Manejo de fallo» con `IGNORE` → `ignoreErrors="true"`; cualquier otro texto → fallo visible (`false`) |
| D-46 | Dos invocaciones del mismo conector en una tarea se ejecutan en el orden en que aparecen en el `.proc` (correos «uno …» y «dos …» en ese orden); el motor las nombra por su `name` (`conn_correo_1`, `conn_correo_2` en los logs) | Una fila de `bpmn.md` por invocación; el generador escribe primero las de `entrada` y luego las de `salida`, cada grupo por `orden`, con nombre `<ID>` o `<ID>_<n>` |
| D-47 | Un `.def` lo pueden usar varios filtros con nombres distintos: bonita2bar pasa a `addUserFilter(nombre, definitionId, versión)` el nombre del `ActorFilter` de cada tarea, y el `.conf` lleva un solo mapeo por definición. En el motor, con dos nombres a la vez, **[no verificado]** (la medición usó un filtro) | Varios filtros (`filtroCompradorDelCaso`, …) comparten `usuario-del-caso`; cada uno es una fila de la tabla «Actor filter» |

## Plan 5 — `contratos-documentos`

Mediciones D-50…D-59.

**Origen:** proyecto de medición (vacaciones + `cotizacionInput` FILE → documento `cotizacion`, `lineasInput` COMPLEX
múltiple con FILE `adjunto` → lista `adjuntosLinea`, `catalogoInput` anidado de solo lectura leído por la constraint
`tope_valido`, y en `2_revisarJefe` `soportesInput` FILE múltiple → lista `soportes`, `cotizacionNueva` → `cotizacion` y
un script que guarda el ID en `Solicitud.cotizacionId`), `generar` + `tools/run-journey.sh --mantener` (bundle en 8103)
y llamadas REST (5 de noviembre de 2026; D-57 en una segunda corrida). Antes, lectura del convertidor (bonita2bar 9.0.10:
`Single/MultipleDocumentEngineDefinitionBuilder`, `DocumentGroovyScriptExpressionFactory`, `EngineExpressionUtil`) y
del motor (`bonita-server-11.1.0.jar`: `DocumentLeftOperandHandler`, `DocumentHelper`).
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0), bonita2bar 9.0.10.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-50 | Un COMPLEX con un hijo COMPLEX múltiple (dos niveles: `catalogoInput.topes[].maximo`) y un hijo simple múltiple (`categorias`) los construye bonita2bar y los acepta el motor por `POST …/instantiation` (C-1) | Hijos anidados con «[…]»; más de dos niveles, `[no verificado]` |
| D-51 | `mandatory_<ruta>` con la semántica «si llega el padre»: `catalogoInput` nulo → 200; `topes[0].maximo` nulo → 400 «catalogoInput.topes.maximo es obligatorio»; en un padre múltiple (`lineasInput[].nombre`), igual. Una constraint propia rechaza por REST con su mensaje de `contratos.md` («Los topes no pueden ser negativos») (C-2) | Obligatoriedad propia por hijo; aceptación de R-06 |
| D-52 | El motor exige en el cuerpo **todos** los inputs del contrato: sin los opcionales, 400 «Error while validating expected inputs: Expected input [cotizacionInput] is missing…». El valor de un FILE es la referencia que devuelve `POST API/formFileUpload` (multipart, campo `file`): `{"filename", "tempPath", "contentType"}` | El formulario generado los manda a `null`; un payload de journey escrito a mano también debe |
| D-53 | `process:Document` con `documentType="CONTRACT"` y `contractInput` inicializa el documento al instanciar desde un FILE (C-4); desde un FILE hijo de un COMPLEX múltiple, una lista con un documento por elemento (índices 0, 1…); el elemento que llega con el FILE nulo no crea documento (C-6) | Bonita no tiene operaciones de instanciación: el documento se inicializa desde el contrato |
| D-54 | Operación con operando izquierdo `DOCUMENT_REF_TYPE` (el `Document` en `referencedElements`) y operador `DOCUMENT_CREATE_UPDATE` crea la versión 2 del documento con el **mismo** id; con `DOCUMENT_LIST_SET`, la lista (C-5). bonita2bar traduce ambos a `ASSIGNMENT` sobre `DOCUMENT`/`DOCUMENT_LIST` | Operaciones de documento antes de las demás. Abrir y guardar el `.proc` en el Studio sin diff: `[no verificado]` |
| D-55 | Con valor `null`, el motor **borra** el documento (`DocumentLeftOperandHandler.update`); un `DocumentValue(id)` sin cambios lo deja. La operación generada devuelve el vigente si el FILE llega nulo: medido, la versión 1 de `cotizacion` sigue tras ejecutar con `cotizacionNueva: null` (C-7) | FILE nulo conserva el vigente. En una lista ya existente, la misma lógica (`getDocumentList` → `DocumentValue(id)`) queda `[no verificado]` en el motor |
| D-56 | Una operación posterior de la misma tarea lee el ID del documento recién escrito (`getLastDocument(processInstanceId, 'cotizacion').id` → `Solicitud.cotizacionId` = 11, id estable entre versiones) (C-8) | Guardar el ID en el BDM lo hace una operación del proyecto (script o helper), no el arnés |
| D-57 | En la **instanciación**, el valor inicial de la business variable (donde van las operaciones de instanciación, incluida la entera de `persistencia`) **no ve** el documento que inicializa el contrato: `getLastDocument(processInstanceId, 'cotizacion')` falla y `Solicitud.cotizacionId` queda nulo aunque el caso sí tiene el documento (el motor crea los documentos después de los datos) | Guardar el ID de un documento aportado en la instanciación lo hace una operación de la primera tarea (o una tarea script previa), no la instanciación; en una tarea sí funciona (D-56) |
| D-58 | Contrato vacío en la instanciación: `generar` escribe un `process:Contract` sin inputs (como el de una tarea sin inputs, que corre en el journey de vacaciones) | En el motor, `[no verificado]` (C-3): el proyecto de medición no tenía un pool con instanciación sin inputs |
| D-59 | Un `\|` dentro del Groovy de una celda de `expresiones.md` (p. ej. `\|\|`) parte la fila de la tabla: el Groovy queda cortado y el motor falla al evaluar («Unexpected character: '`'»), sin que `generar` ni `check_expresiones` lo vean | Escribir el Groovy sin `\|` (`!(… ?.any { … })`) o escaparlo; petición al coordinador para que el lector lo detecte |

## Plan 5 — `persistencia`

Mediciones D-60…D-69 (R-07 operación sobre la business variable entera y plantilla por helpers; R-08 business
variables múltiples y varias creadas al instanciar).

**Origen:** proyecto de medición `compras` (grupo `com.empresa.compras`, Community) escrito con `escribir_proyecto`
desde una spec a mano con el BDM de `ejemplos/compras` (`Solicitud` con `lineas` en composición, `Evento` con
`solicitud` en agregación obligatoria y la consulta `findBySolicitud`), las business variables `solicitud`,
`eventos` (múltiple) y `otra: Solicitud` (sin valor por defecto), y el módulo `extensions/compras-helpers` del fixture
añadido a mano al pom de extensiones y a `app/pom.xml`. Build `mvn clean install -Pbundle`, bundle en el puerto 8104
y un caso por REST (instanciación → script `1_crearOtra` → tarea humana `2_revisar` → fin) (5 de noviembre de 2026).
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0, H2), bonita2bar del perfil `bundle`.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-60 | Una business variable con `multiple="true"` en su `BusinessObjectData` (orden de features de `Data`: `name`, `multiple`, `dataType`, `className`), con valor por defecto y operaciones `ASSIGNMENT` cuyo `leftOperand` y `rightOperand` tienen `returnType="java.util.List"`, construye y corre: `API/bdm/businessDataReference?f=caseId=` la da con `storageIds` `[3, 5]` y crece en cada operación (P-1) | El escritor usa `java.util.List` para la variable múltiple (valor por defecto, operación y `multiple="true"` en las referencias) |
| D-61 | Dos business variables inicializadas en la instanciación, la segunda referenciando a la primera (`eventos` ← `eventoNuevo(solicitud, …)`, `Evento.solicitud` en agregación obligatoria): el motor evalúa los valores por defecto en el orden de los `data` del pool y persiste los dos; `Evento/3/solicitud` es la `Solicitud` 1 del caso (P-2). Una variable sin operación de instanciación (`otra`) queda con `storageId` null hasta su operación | Las business variables se escriben en el orden de `bdm.md`: la referenciada va antes. Sin valor por defecto si no hay operación de instanciación (como antes) |
| D-62 | Un `referencedElements` `TYPE_BUSINESS_OBJECT_DAO` con `name`=`content`=`solicitudDAO` y `returnType` la interfaz `com.empresa.compras.model.SolicitudDAO` pone en el script el DAO de servidor (`…model.server.SolicitudDAOImpl`, `BusinessObjectDAOExpressionStrategy` de bonita-server 11.1.0 lee el `returnType`). El `newInstance` del DAO generado **no** es sin argumentos: recibe los atributos obligatorios en el orden del BDM (`newInstance(String, String, Double, String, OffsetDateTime)`); `solicitudDAO.newInstance()` falla con `MissingMethodException` | El escritor declara `<objeto>DAO` de los objetos con business variable en el pool si el script lo usa. La skill lo advierte: para crear con el DAO, los obligatorios van como argumentos; si no, `new <paquete>.<Objeto>()` |
| D-63 | Acceso a DAO desde la biblioteca de helpers (P-3): el script pasa `eventoDAO` a `Persistencia.eventosDe(eventoDAO, solicitud)`, que llama a `findBySolicitud(Long, int, int)` sin conocer la clase; devuelve la fila persistida. El helper crea entidades del BDM por nombre con el cargador del hilo (`registrarSolicitud`, en el valor por defecto de la instanciación) o con el del objeto recibido (`eventoNuevo`), y usa `apiAccessor` de forma dinámica: con el jar en `WEB-INF/lib` (padre del cargador del BDM) funciona | La biblioteca de helpers no nombra clases del BDM de forma estática ni depende de bonita-common; recibe el DAO del script |
| D-64 | Persistir un agregado nuevo y quien lo referencia en la misma tarea (P-4): en el script `1_crearOtra`, `bv otra` ← `solicitudDAO.newInstance(…)` y después `bv eventos` ← `eventoNuevo(otra, …)`; la segunda operación ve el valor nuevo de `otra` y al terminar la tarea los dos están persistidos (`Solicitud` 4, `Evento` 5 con `solicitud` = 4) | Las operaciones de una tarea se escriben en el orden de la línea de `contratos.md`: la que crea el agregado va antes que la que lo referencia |
| D-65 | En la instanciación, una operación por atributo (`telefono` ← `compraInput.telefono`, de la tabla del contrato) aplicada después de la entera (`bv solicitud` ← `registrarSolicitud(…)`) queda en el objeto persistido (`telefono` = `300`); `registrarSolicitud` ve `processInstanceId` y `apiAccessor` (solicitante = `ana`, iniciador del caso) y crea las `Linea` en composición | El valor por defecto es «entera primero, atributos después», en cualquier orden de la documentación |
| D-66 | El valor por defecto de `eventos` cuyo Groovy nombra `eventos` (`eventoNuevo(solicitud, "registrada", eventos)`, como `op_instanciacion.eventos` de compras) corre con la línea `def eventos = null` delante | El escritor la antepone cuando el Groovy nombra la propia variable. Que sin ella fallaría (`MissingPropertyException`: la variable no está en el binding) es semántica de Groovy, `[no verificado]` en el motor |

`[no verificado]`: abrir y guardar en el Studio un `.proc` con business variable múltiple y referencias DAO sin diff;
el valor de `cotizacion`/`soportes` desde los documentos (lo mide `contratos-documentos`, C-8, con estos helpers).

## Plan 5 — `acceso`

Mediciones D-70…D-79. Reglas dinámicas escritas a mano (R-14).

**Origen:** hilo `acceso` del Plan 5 (5 de noviembre de 2026): `unzip -l` del bundle Community
(`bundle-tomcat-11.1.0.zip`, `BonitaCommunity-2026.2-u0`) y de `platform-resources(-sp)-11.1.3.jar` del Studio
Subscription 2026.2-u3; un bundle `-Pbundle` de un proyecto `nuevo` arrancado en el puerto 8105 con
`tools/run-journey.sh --mantener`, con una regla que deniega todo (`DenegarTodo`) y la línea
`GET|identity/group=[check|DenegarTodo]`, copiadas con `tools/reglas.py` y el arranque con
`BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=true`.
**Comprobado en:** bundle Community 2026.2-u0 (motor 11.1.0) y recursos del Studio Subscription 2026.2-u3 (11.1.3).

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-70 | (A-2) El bundle Community **no trae** `dynamic-permissions-checks*.properties` ni `tenant_security_scripts/` en `setup/platform_conf/initial/`. Los recursos de Subscription (`platform-resources-sp`) sí: `tenant_portal/dynamic-permissions-checks-custom.properties`, `tenant_portal/dynamic-permissions-checks.properties` (las reglas predefinidas) y `tenant_security_scripts/` (con `SamplePermissionRule.groovy.sample`) | `tools/reglas.py` copia el properties a `tenant_portal/` y las `.groovy` a `tenant_security_scripts/`, los sitios de `rest-api-authorization.adoc` |
| D-71 | (A-1) Community 2026.2 **ignora** las comprobaciones propias: con el properties y la regla copiados al bundle antes del primer arranque y la variable en `true` (el log dice «Dynamic permissions enabled»), `GET API/identity/group` por `walter.bates` responde 200 y la regla no se evalúa (ni traza en `bonita.log`). Medido con un solo recurso (`identity/group`) | Consistente con la doc: «custom configuration and rules extensibility are only available in Teamwork, Efficiency, Performance and Enterprise editions». Con `edicion_destino` `community`, `generar` las escribe y el despliegue las omite con un aviso; la protección va en la REST API extension |
| D-72 | (A-4) Arrancar el bundle Community con `BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=true` no rompe el journey de `hola`: Newman 30 aserciones, 0 fallos, y Playwright 2 de 2 | `run-journey.sh` arranca con `true` solo si `tools/reglas.py` desplegó reglas (Subscription); sin reglas, `false` como siempre. El journey de vacaciones con `true` queda **[no verificado]** (su e2e necesita el puerto 8099 del mock, fuera de lo permitido en este hilo); vacaciones no tiene reglas, así que no cambia |
| D-73 | (A-3) El motor del Studio guarda sus configuraciones en la tabla `configuration` (`tenant_id`, `content_type`, `resource_name`, `resource_content`); el tipo `TENANT_SECURITY_SCRIPTS` existe en los recursos de Subscription 11.1.3. `tools/studio.py` escribe ahí cada regla (`TENANT_SECURITY_SCRIPTS`/`<Regla>.groovy`) y fusiona las líneas dinámicas en la fila `TENANT_PORTAL`/`dynamic-permissions-checks-custom.properties` | Probado con una H2 real simulada y con una Bonita falsa en `tests/test_acceso.py`. **[no verificado]** contra el Studio abierto: no se tocó el motor del Studio (8080) en este hilo; pendiente `tools/arnes.sh studio --sin-construir` con un proyecto Subscription que tenga reglas (hay que reiniciar el servidor del Studio, como con los permisos) |
| D-74 | El **BDM access control** (`bdm_access_control.xml`) sigue fuera de alcance: es solo Subscription y el generador no lo produce | Sigue como hueco del arnés / item `subscription` de `SUB` |
| D-75 | (A-4, integración, 5 de noviembre de 2026; bundle Community 2026.2-u0 en el 8107) Con `BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=true` (forzado en la copia de `run-journey.sh`, sin reglas propias) corren las comprobaciones dinámicas **por defecto** de Community (D-71 solo vio ignoradas las propias): `GET API/bpm/process?f=name=…&f=version=…` y `GET API/bpm/humanTask?f=rootCaseId=…` como usuario no administrador dan **403** (`ProcessPermissionRule`, `TaskPermissionRule` de `bonita-server-11.1.0.jar`: la búsqueda exige `f=user_id`, `assigned_id` o `supervisor_id` del usuario de la sesión). Con esos filtros el journey de vacaciones pasa entero con el check activo: Newman 87 peticiones / 113 aserciones, 0 fallos; Playwright 5 de 5 | El journey generado busca el proceso y las tareas con `f=user_id` del usuario del paso (el timer lo sondea un candidato de la tarea anfitriona) y las pruebas Playwright de `ejemplos/vacaciones` también. Los pasos «(no ve)» siguen listando todas las tareas del caso: con el check activo, **[no verificado]** (compras no los ejercita con el check: en Community `run-journey.sh` arranca con `false`) |

## Plan 5 — `journey`

Mediciones D-80…D-89.

**Origen:** hilo `journey` del Plan 5 (R-15): journey de vacaciones con un paso «(no ve …)», «Correos esperados:
ninguno» y una consulta esperada (`tools/run-journey.sh` con `PORT=8106`, SMTP de prueba en 2526/8026), más peticiones
sueltas con curl y con colecciones Newman escritas por `generadores/escribir/journey.py` contra el mismo bundle vivo.
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0), Newman 6.2.3, 2026-11-05.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-80 | `POST API/formFileUpload` (multipart, campo `file`) responde 200 con `{"filename":"cotizacion.pdf","tempPath":"<uuid>.pdf","contentType":"application/pdf"}` aunque el `Content-Type` de la respuesta es `text/plain;charset=UTF-8`; sin la cabecera `X-Bonita-API-Token` responde 401. Un cuerpo multipart escrito como `raw` en la colección funciona en Newman (sin ficheros en disco) | La subida va con el token y el journey lee la respuesta con `pm.response.json()` (y, si no es JSON, el texto entero como `tempPath`). Que el contrato consuma ese objeto en un input FILE lo mide `contratos-documentos` (C-4, C-6) |
| D-81 | `GET API/bpm/humanTask?f=rootCaseId=…&f=user_id=<id>` como un usuario que no es candidato devuelve la lista sin la tarea (200); el paso «(no ve …)» del journey pasa en el camino `rechazada` de vacaciones (`ana` no ve `2_revisarJefe`) | El negativo de visibilidad se mide con el mismo filtro que el positivo. Con actor filter (`compra.dos` y `3_revisarCompra` de compras) queda `[no verificado]` hasta la integración con `extensiones` |
| D-82 | En Community, con `BONITA_RUNTIME_AUTHORIZATION_DYNAMICCHECK_ENABLED=false` (el de `run-journey.sh`), `luis` lee el objeto BDM (`GET API/bdm/businessData/…Solicitud/<id>`) y el contexto (`GET API/bpm/case/<id>/context`) del caso de `ana`: **200**; `DELETE API/bpm/case/<id>` de `luis`: **403** (el caso sigue vivo); un `storageId` inexistente: **404**. El contexto del caso vivo lo lee quien lo instancia (200; 404 cuando el caso ya terminó) | Las protecciones de fila de un caso son de Subscription o de una REST API extension: esos pasos llevan « [subscription]». El código en Subscription (J-4) queda `[no verificado]` |
| D-83 | `pm.execution.skipRequest()` en un script previo omite la petición (no sale al servidor; Newman 6.2.3) y las variables de colección con punto (`userId_ana.perez`) se resuelven en URL y query (`f=user_id={{userId_ana.perez}}` → `f=user_id=42`) | El paso omitido en Community no hace ninguna petición; los usuarios con punto (R-16) no necesitan otro nombre de variable |
| D-84 | `GET API/bdm/businessData/<clase>?q=findPendientesPorEmpleado&p=0&c=100&f=empleado=ana` devuelve la lista de objetos (200), con los atributos simples y `links` para las relaciones | Forma de la consulta esperada del journey (`_consulta`) |
| D-85 | `GET API/bpm/userTask/<id>/context` del usuario asignado, con la tarea lista, da `<bv>_ref` de cada business variable del proceso: una simple `{"name","type","link":"API/bdm/businessData/<clase>/<id>","storageId":1,"storageId_string":"1"}`; una **múltiple** `{"name","type","link":"API/bdm/businessData/<clase>/findByIds?ids=4,5","storageIds":[4,5],"storageIds_string":["4","5"]}`, con los ids en el orden de la lista (en `6_pagar` de compras, `eventos` = [registrada, asignada]: `{eventos[2]}` es el evento «asignada»). Medido en el camino `pagada` de `ejemplos/compras` (hilo `huecos-update-journey`, `PORT=8122`, SMTP 2532/8032, Newman `--verbose`) | Una fila del payload (`{bv}`, `{bv[n]}`, contrato §2.14) se resuelve con el contexto de la tarea, como lo haría su formulario, antes de ejecutarla: `storageId_string` o el n-ésimo de `storageIds_string` |
| D-86 | `GET API/bdm/businessData/<clase>/<id>/<relación>` sobre una composición múltiple **no** `LAZY` (`Solicitud.lineas` de compras) responde 200 con la lista de hijos en el orden de la lista (`[{"persistenceId":2,…,"producto":"Silla ergonómica"},{"persistenceId":3,…,"producto":"Escritorio auxiliar"}]`), igual que la `lazyRef` de una relación `LAZY`. El helper de `6_pagar`, que busca la fila por ese `persistenceId_string`, escribe `PAGO-0001 · Escritorio auxiliar · asignada` | `{bv.relacion[n]}` usa esa ruta para composición y agregación, `LAZY` o no. Una relación simple (`{bv.relacion}`, el objeto) y una agregación múltiple quedan `[no verificado]`: no hay ninguna en un payload de compras |

## Plan 5 — `formato-doc`

Mediciones D-90…D-99.

**Origen:** pendiente: lo escribe el hilo al medir en el bundle.
**Comprobado en:** [no verificado]

## Plan 5 — `huecos-generador`

Mediciones D-100…D-102 (rango propuesto por el hilo: el A0.8 no le asignó uno).

**Origen:** huecos del MVP «Política corta» con la 0.11.0. El validador del BDM medido con un programa Java contra los
jar del repositorio Maven local (`bonita-common` 11.1.0 y 11.1.3, `bonita-business-object-model` 1.2.2) y con
`mvn -o -pl bdm/model -am generate-sources` (`bonita-project-maven-plugin` 2.1.4) sobre `ejemplos/vacaciones` mutado;
despliegue en el bundle con `tools/run-journey.sh` (`PORT=8121`), consultas por REST y la H2 del bundle con
`org.h2.tools.Shell` (h2 1.4.200) con el bundle parado.
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0), JDK 17, 2026-11-05.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-100 | El nombre de un índice o de una unique constraint lo valida `SQLNameValidator(25)` (`IndexValidationRule`, `UniqueConstraintValidationRule`, iguales en 11.1.0 y 11.1.3): `[a-zA-Z][\d\w#@]{0,25}$` (ASCII) y no una palabra de `blocked_db_keywords` (las de `*_permissive_keywords`, como `INDEX`, solo avisan). Con 26 caracteres `generate-bdm-model` pasa; con 27 falla «IX_ABCDEFGHIJKLMNOPQRSTUVWX is not a valid SQL identifier», como el MVP con `IX_MODIFICACION_SOLICITUD_FECHARESPUESTA`. El validador no exige nombres distintos entre objetos (`UniqueNameValidationRule` no está en `BusinessObjectModelValidator`), pero la H2 del bundle sí: un segundo `CREATE INDEX IX_MISMO` en otra tabla da «Index "IX_MISMO" already exists». El nombre generado `IX_SOLICITUD_EMPLEA_8B1F2C` despliega y aparece en `INFORMATION_SCHEMA.INDEXES` de `business_data.db` | `escribir/bom.py::nombre_restriccion` trunca a 19 + `_` + 6 hexadecimales del sha1 lo que no cabe; `validar/huecos_generador.py` rechaza un nombre explícito inválido y cualquier nombre repetido en el BDM (incluidos los `Kp*`). En PostgreSQL, **[no verificado]** |
| D-101 | Una consulta con el mismo nombre en dos objetos (`findRecientes` y `countForFindRecientes` en `Solicitud` y en `Evento`) pasa el validador (solo rechaza «The query named "x" already exists for <objeto>» dentro del mismo objeto), `generate-bdm-model` genera `@NamedQuery(name = "Evento.findRecientes", …)` y `@NamedQuery(name = "Solicitud.findRecientes", …)`, el BDM se instala y `GET API/bdm/businessData/<clase>?q=findRecientes&…` responde 200 en los dos objetos (y `countFor…`, `{ "value": 0 }`) | `consultas.md` va por (Objeto, Consulta) (contrato §2.6.1) |
| D-102 | La pantalla Svelte de solo acción (contrato sin inputs: `frm_instanciacion` con la instanciación vacía y `frm_1_leerNotificacion` sin campos) pasa `npm run check` (svelte-check, 0 errores) y su `pantalla.test.ts` (vitest, 3 de 3 cada una) | El esqueleto envía `{}` por `instanciarProceso`/`ejecutarTarea`. La instanciación real desde la página en el bundle queda **[no verificado]** (el contrato vacío ya lo cubría el journey) |

## Plan 5 — `huecos-parametros`

Mediciones D-110…D-119.

**Origen:** hilo `huecos-parametros` (huecos 3 y 5 del MVP «Política corta» con la 0.11.0). Proyecto de medición: `nuevo`
+ la documentación de `ejemplos/vacaciones` con tres parámetros de negocio más en el catálogo (`param_tiposDocumento`:
lista con clave y campos `tramite`, `activo`; `param_revisoresPorTipo`: tramo-cascada de dos campos; `param_estructura`:
cascada de cuatro niveles) y `op_2_revisarJefe.estado` que llama a `ParametrosDeProceso.usar` y escribe el resultado en
el log. `tools/run-journey.sh --mantener` con `PORT=8123`, caminos `preparación` y `rechazada`; `curl` como `ana`
(Empleado, familia interna) y `jefe1`.
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0), H2, 2026-11-05.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-110 | La semilla con las formas de §2.18 se aplica entera (el modelo del módulo no cambia). `GET …/API/extension/parametros/valores?definicion=…&instanciacion=<id de la definición>[&padre=…]` devuelve: `tipos_documento` → `opciones` `[{codigo: "1", etiqueta: "Política"}, {codigo: "2", etiqueta: "Instructivo"}]`; `tipos_documento.tramite&padre=1` → `valor` `ciclo_documental` (TEXTO); `tipos_documento.activo&padre=2` → `false` (BOOLEANO); `revisores_por_tipo.revisor2&padre=1` → `ana`; `estructura.area&padre=1` → `a1` «Área uno», `estructura.direccion&padre=a1` → `d1`, `estructura.departamento&padre=d1` → `dp1`, `estructura.puesto&padre=dp1` → `p1` «Puesto uno» y `p2` «Puesto dos»; `revisores_por_tipo&padre=1` → `{"motivo": "NO_EXISTE"}` (no hay definición base). `GET …/parametros/administracion/valores?definicion=estructura.puesto` (superadministrador) devuelve la definición derivada (`dependeDe` `estructura.departamento`, nombre «… › puesto») con sus filas | Las definiciones derivadas (`<lista>.<campo>`, `<tramo>.<campo>`, `<tramo>.<nivel>`) son las que leen formularios y scripts. Que la **página** de administración las pinte y edite bien en el navegador queda `[no verificado]` (solo se midió su API) |
| D-111 | `ParametrosDeProceso.usar(apiAccessor, processDefinitionId, activityInstanceId, rootProcessInstanceId, …)` en una operación de la tarea humana `2_revisarJefe` (la clase por su nombre completo) resuelve: `revisores_por_tipo.revisor1` con `padre = "1"` → `[valor: luis, origen: VALOR]`; `tipos_documento.activo` con `"2"` → `[valor: false, origen: VALOR]`; `tipos_documento` → `opciones` con clave y etiqueta; `estructura.puesto` con `"dp1"` → las dos opciones del nivel. Newman `rechazada`: 34 aserciones, 0 fallos | `usar` lee los campos y los niveles igual que la API, con la clave de la opción como `padre` |
| D-112 | Con el bundle recién desplegado y sin ninguna llamada a `…/API/extension/parametros/…`, la misma operación lanza `ParametroNoDisponible: la definición «revisores_por_tipo.revisor1» no existe y no hay fallback que usar` y `Revisar solicitud` queda `failed` (primera corrida; el journey de vacaciones sin Playwright no llama a la API antes). Tras un `GET …/parametros/valores` la semilla está aplicada y la segunda corrida pasa | La semilla la aplica la API (`Kit.asegurarSemillas`) en su primera invocación, no el despliegue: un proceso que lee parámetros por script antes que cualquier formulario necesita que algo llame antes a la API. Probable causa del `Solicitud.encargado` nulo del MVP (`[no verificado]` en el MVP). **Resuelto en D-113** |
| D-113 | (Integración.) Con `ParametrosDeProceso.usar`/`usarConFoto` aplicando antes la semilla pendiente del classpath del proceso (`SemillasDelClasspath`: `getResources("semillas")` del cargador del script y del de la clase, `jar:` y `file:`; en el .bar la trae el jar de `parametros-adaptador`), `ejemplos/compras` con `op_2_asignarComprador.eventos` cambiado para llamar a `usar(…, "topes_por_categoria", "tope")` en `2_asignarComprador` —el primer paso, automático, tras la instanciación— y **sin ninguna llamada** a `…/API/extension/parametros/…` (la colección de Newman no la tiene; `tools/perfiles.py` tampoco): el log del bundle da `D-113 usar en 2_asignarComprador -> {valor=Papelería: 500000; …, origen=VALOR}` en la instanciación; en `business_data.db`, una sola traza `SEMILLA` (usuario `sistema`, «Semilla de SolicitudCompra, versión 1.0»), la definición `topes_por_categoria` con origen `SEMILLA` y un `KpUsoParametro` (`Asignar el comprador`, `VALOR`). `tests/e2e/e2e_compras.sh` con esa copia (`COMPRAS_EJEMPLO`, `PORT=8124`): 165 aserciones, 0 fallos. El mismo proyecto con el `ParametrosDeProceso` anterior: el caso se queda en `2_asignarComprador` («tarea 3_revisarCompra lista: expected 0 to deeply equal 1»), como D-112. La suite de `parametros-core` contra el esquema H2 que creó el motor en esa corrida (`-Dkit.h2.url`): 860 tests, 0 fallos (231 saltados, los de PostgreSQL), `SemillaAlUsarH2Spec` 4 de 4 | El proceso no depende de que alguien llame antes a la API, en cualquier despliegue y sin paso de despliegue propio (`run-journey.sh` y `tools/studio.py` no cambian). Si la API y un proceso la aplican a la vez, queda una sola (`AplicarSemillaCasos` «dos primeras invocaciones a la vez aplican la semilla una sola vez», verde en esa H2). En PostgreSQL y Subscription, **[no verificado]** |


## Plan 5 — integración: huecos 8 y 9 del MVP

Mediciones D-114…D-119.

**Origen:** integración (huecos 8 y 9 de la segunda pasada del MVP «Política corta» con la 0.11.0). Lectura con `javap` de
`bonita-server-11.1.0.jar` (`OperationServiceImpl`, `StateBehaviors.executeOperations`, `DocumentLeftOperandHandler`,
`DocumentListLeftOperandHandler`, `DocumentHelper`) y de la página «Execution sequence, states and transactions» de la
documentación 2026.2. Medido con `tests/e2e/e2e_compras.sh` (`PORT=8125`; `ejemplos/compras` con el documento simple
`informeRevision` nuevo en `3_revisarCompra` y el helper de `op_3_revisarCompra.solicitud` que falla si no ve
`informeRevision` ni `soportes`) y con la copia del MVP `/tmp/mvp-medicion2` (`update`, `generar`, `PORT=8125
tools/arnes.sh journey --mantener`).
**Comprobado en:** bundle Community 2026.2-u0 (runtime 11.1.0), H2, 2026-11-05.

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-114 | Las operaciones de una tarea son **una** llamada a `OperationService.execute(lista)`: primero evalúa los operandos derechos de todas, en orden (`executeOperators`, que deja cada valor nuevo en el contexto), y después persiste los izquierdos (`updateLeftOperands`); los documentos se crean ahí, al final. Una operación posterior de la misma tarea que lee por la API un documento que la tarea **crea** no lo encuentra: en el MVP, `DocumentNotFoundException … adjuntoSolicitud` 6 ms antes de que el motor cree el documento (`1_registrarSolicitud`) y `PropertyValueException … DocumentoSolicitud.archivoDocumento` en `4_realizarRequerimiento` (lista `documentosSolicitud`); en `ejemplos/compras` con el escritor anterior, `Revisar la compra/failed` (el helper no ve `soportes`). D-56 lo veía porque `cotizacion` ya existía (versión 1 de la instanciación) y el ID no cambia entre versiones. El orden de las operaciones en el `.proc` (documentos primero) no basta | La operación de documento escribe el documento ella misma (D-115). Las operaciones «on finish» de un conector sí van después (la documentación: operaciones de la tarea → conectores «on finish»), pero el arnés no las usa para esto |
| D-115 | El script de la operación de documento escribe por la API al evaluarse: simple, `addDocument(processInstanceId, '<doc>', '', DocumentValue(content, contentType, fileName))` si no existe y `updateDocument(<id vigente>, …)` si existe; lista, `setDocumentList` con cada FILE convertido como `DocumentHelper.toDocumentValue`; y devuelve `DocumentValue(id)` sin cambios (`DocumentLeftOperandHandler.update` no hace nada con un `DocumentValue` con id y `hasChanged` falso; la lista se vuelve a fijar con los mismos ids). `ejemplos/compras`: 105 peticiones, 167 aserciones, 0 fallos (`informeRevision` nuevo en la tarea y `soportes` vistos por el helper). Copia del MVP: los cuatro caminos (`feliz`, `gerente_pide_modificacion`, `directora_pide_modificacion`, `vp_no_aprueba`), 324 peticiones, 478 aserciones, 0 fallos; en el log del bundle, cero `DocumentNotFoundException`, `PropertyValueException` y `ParametroNoDisponible`; `Solicitud.adjuntoSolicitud` = 1 = id del documento `adjuntoSolicitud` (`solicitud.pdf`, versión 1, una sola) y `DocumentoSolicitud.archivoDocumento` = 2 = id de `documentosSolicitud[0]` (`politica.pdf`) | Una operación posterior de la tarea (la de la business variable entera incluida) ve el documento que la tarea crea o versiona. Un FILE nulo sigue conservando el vigente (D-55); un FILE con `id` y sin contenido va al motor tal cual, como antes |
| D-116 | El documento escrito por la API desde el script queda con `author`/`submittedBy` = `-1` (la sesión del script es la del sistema); el que escribía el motor llevaba al asignado de la tarea (`AbstractDocumentLeftOperandHandler.getAuthorId`) | Quien subió un documento no se lee del documento: si el proceso lo necesita, que lo guarde el BDM (p. ej. el helper, con el usuario de la tarea). Que algún formulario o informe del proyecto lo use: `[no verificado]` |
| D-117 | `update` con un proyecto cuyos módulos del arnés tienen el código de 0.10.0 pero cuyo manifiesto ya es de 0.11.0 (lo dejó un `update` anterior a este cambio, como el repo del MVP): la copia `tools/arnes/plantilla/` es la nueva, así que `ParametrosDeProceso.groovy` y `UsoCasos.groovy` salen como «plantilla con cambios propios» (medido en una copia del repo del MVP en `/tmp`) | Con módulos sin editar, `update --forzar`; un proyecto que pasa de 0.10.0 a esta versión de una vez no lo necesita (compara con la copia de 0.10.0) |

## Proyectos existentes — versión superior y `quita` del BDM

Decisiones D-120 y D-121.

**Origen:** diseño del modo «proyecto existente» (spec §6.6 y §6.11): se decidió sin medir, por la regla de no probar
contra Bonita real ni contra proyectos reales en esta entrega. Nada de esto se ha ejecutado en el Studio, en el motor ni
sobre un proyecto de producción.
**Comprobado en:** [no verificado] (solo pruebas automáticas del repositorio, sobre fixtures; sin Studio, sin motor).

| # | Hallazgo | Consecuencia |
|---|---|---|
| D-120 | **[no verificado]** Forma de la versión superior de un proceso existente: el `.proc` nuevo es una copia del existente con **todos los `xmi:id` reasignados** de forma determinista (incluidas las referencias de la notación, de los `.conf` y de las expresiones que los nombran), la versión subida en el pool y en el `MainProcess`, el fichero llamado `<MainProcess>-<versión>.proc`, el `.conf` llamado como el `xmi:id` **nuevo** del pool y **un solo pool** por copia. El nombre del fichero no sigue la versión del pool en un proyecto real (un `.proc` `…-1.0.proc` puede contener un pool en `3.0`), y el diseño no lo supone. El `.proc` de la línea base queda intacto y se despliega con la versión anterior para que los casos en curso terminen con ella | Hasta medirlo en el Studio (importar el `.proc` copiado, abrirlo, desplegarlo junto a la versión anterior), es una decisión conservadora: si el Studio o el motor rechazan la copia, cambia el generador de la versión superior, no los proyectos |
| D-121 | **[no verificado]** `quita` de un objeto o atributo del BDM: sin medir qué hace el motor con la tabla o la columna y sus datos al desplegar un `bom.xml` sin ese elemento (migración, conservación o fallo del despliegue) | Desactivado: `cambios mostrar` lo marca «no soportado» y `generar` no lo escribe (hueco en `huecos-del-arnes.md`). Se activará cuando se mida en un motor con datos |

## Otras versiones de Bonita admitidas

**Origen:** matrices `versiones/2025.1.json`, `2025.2.json` y `2026.1.json`; este conocimiento se midió sobre 2026.2 y
no se repite versión por versión.
**Comprobado en:** 2025.1-u0, 2025.2-u5 y 2026.1-u0 (runtimes 10.3.0, 10.4.5 y 11.0.0): plantilla, generadores,
custodios, conector REST y formularios con `tests/e2e/e2e_vacaciones.sh` y `e2e_compras.sh` (`VERSION_BONITA=<v>`) sobre
el bundle Community. Sin medir en esas versiones: el import en el Studio, la imagen Docker y el conector de email.

Los generadores usan `ids-visuales-2026.2.json` en todas las versiones. En un `.proc` real de 10.4.0 los 9 tipos de nodo
presentes (Pool, Lane, Task, ServiceTask, StartEvent, EndEvent, XOR, AND y SequenceFlow) llevan los mismos ids visuales
que en 11.1.0, y `bonitaModelVersion` es 9 en ambos. No se ha comparado el resto de tipos ni 2025.1 o 2026.1 [no verificado].

**2024.3 (runtime 10.2.0) no se admite**, medido el 2026-11-06. Dos diferencias: el bundle trae
`setup/platform_conf/initial/tenant_template_portal` en vez de `tenant_portal`, y el parent 10.2.0
(`bonita-project-maven-plugin` 1.0.0) excluye los conectores del classpath de la webapp porque los espera dentro del
`.bar`, pero el `.bar` que resulta no los lleva: la tarea queda `failed` con `GetConnectorImpl can not be found`.
Admitirla exige más que una matriz; lo que haya detrás de esas dos diferencias está sin medir.
