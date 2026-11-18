# Convenciones de Bonita que el agente respeta

Cada fila es una convención de Bonita 2026.2, con su origen y lo que la vigila en este repositorio. La celda
**Versión** dice dónde se comprobó: `2026.2` es Community 2026.2-u0 (runtime 11.1.0); las filas del Studio dicen
«Studio Subscription 2026.2-u3». Las notas de alcance están en la propia celda de la convención. Si una convención no tiene vigilante, no entra aquí.

- **Origen**: commit de este repositorio, commit del laboratorio de pruebas previas (`lab`, Plan 1) o página de la
  documentación oficial con línea. `D-xx` es una fila de `compatibilidad-2026.2.md` del piloto, incluida solo
  porque este repositorio ya la prueba o la custodia en 2026.2.
- **Vigilada por**: una prueba (`tests/test_x.py::Clase::test_y`), un custodio (`custodios/check_x.py`) o el e2e
  (`tests/e2e/…`). `tests/test_convenciones.py` comprueba que cada uno existe.
- Se actualiza al cambiar `versiones/<versión>.json`: una convención se vuelve a comprobar en cada versión nueva.

Conocimiento de diseño que complementa estas convenciones: `patrones-bonita.md` (patrones de proceso),
`bonita-rest-api.md` (API REST) y `compatibilidad-2026.2.md` (diferencias D-xx contra la doc 2026.2). Cada sección
dice dónde se comprobó; lo marcado `[pendiente 2026.2]` no está probado aquí.

## Proyecto y construcción

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **`mvn install`, no solo `package`**: el sub-build de cada proceso resuelve el modelo del BDM desde el repositorio local. | Plan 1, aprendizaje 3 (lab `77d212f`); 854d2b2 | 2026.2 | `tests/e2e/ciclo.sh` |
| **JDK 17 forzado** (`BONITA_JAVA_HOME`): con el JDK por defecto del Maven de Homebrew el plugin Groovy falla con «Unsupported class file major version». | Plan 1, aprendizaje 4 (lab `77d212f`); 854d2b2 | 2026.2 | `tests/e2e/ciclo.sh` |
| **Incluir la User Application** (`bonita-user-application`, zip, classifier `application`): sin una aplicación mapeada al perfil User, la REST API responde 403. | Plan 1, aprendizaje 5 (lab `77d212f`); 854d2b2 | 2026.2 | `tests/e2e/e2e_hola.sh` |
| **Subir la versión de la aplicación en cada despliegue**: el instalador solo reinstala si sube (`application.properties`). Se apoya en la doc (`run-application.adoc:50`) y en el caso positivo del lab (Plan 1); ningún test automatizado vigila el caso negativo (versión sin subir), y `e2e_hola.sh` nunca la sube: solo prueba que la aplicación se instala y corre. | doc `build-run/pages/run-application.adoc:50`; Plan 1, aprendizaje 7 (lab `7f06ebe`) | 2026.2 | `tests/e2e/e2e_hola.sh` |
| **`.project` de Eclipse obligatorios** en la raíz, `app`, `bdm`, `bdm/model` y `bdm/dao-client`: sin ellos el clone del Studio no crea el proyecto. | Paso del Studio Subscription 2026.2-u3 (lab copia-studio `2471446`); 854d2b2 | Studio Subscription 2026.2-u3 | `tests/test_plantilla.py::TestNuevoProyecto::test_sin_placeholders_y_con_project` |
| **`h2_database/` ignorado** en `.gitignore`: lo crea el Studio y no se versiona. | Plan 1, paso del Studio (lab `2471446`); 854d2b2 | Studio Subscription 2026.2-u3 | `tests/test_plantilla.py::TestNuevoProyecto::test_sin_placeholders_y_con_project` |
| **Finales de línea LF** en todo lo generado (el Studio reescribe `app/pom.xml` con CRLF al migrar). | Plan 1, paso del Studio (lab `2471446`); 512d560 | Studio Subscription 2026.2-u3 | `tests/test_xmlutil.py::TestXmlUtil::test_declaracion_con_comillas_dobles_y_lf` |
| **Subir la versión del pool en cada cambio de proceso**: si la tarea cambia con la misma versión, el runtime sigue con la definición vieja (`PROCESS_DEPLOYMENT_SKIP_INSTALL`). El pool lleva versión y `bonitaModelVersion="9"`. El test solo comprueba los atributos del pool; el comportamiento (versión sin subir = definición vieja) lo probó `tests/test_redespliegue.sh` del lab, no este repo. | Plan 1, `test_redespliegue` (lab `77d212f`); f0d590c | 2026.2 | `tests/test_proc_flujo.py::TestFlujo::test_un_pool_con_version_y_modelo_9` |
| **Cada usuario de la organización recibe el perfil User** tras el despliegue: lo asigna `tools/arnes.sh perfiles` (`tools/perfiles.py`, idempotente; `run-journey.sh` lo corre antes de Newman y el journey solo lo comprueba). Un artefacto Community no puede llevar el mapeo; `GET API/portal/profileMember` exige `f=member_type=user` en minúscula y un duplicado responde 403 «already exists», no 409. | Plan 1, aprendizaje 6 (lab `77d212f`); a7a471f; Plan 4, tarea 13 | 2026.2 | `tests/test_perfiles_despliegue.py::TestPerfilesDespliegue::test_es_idempotente` |
| **Los valores de parámetros viajan en el `.bconf`**, no en el `.bar` (`includeParameters=false` por defecto); el bundle los aplica. **Todo despliegue a QA o Producción entrega el `.bconf` junto con el zip de la aplicación**: sin él los parámetros llegan sin valor. Vigilancia indirecta, por el camino vencida del e2e (el timer lee el parámetro, en Local); la entrega de QA/Producción no la prueba ningún runtime de este repo. | Task 10 del Plan 2; `tests/e2e/evidencia/aceptacion-plan-2.txt` | 2026.2 | `tests/e2e/e2e_vacaciones.sh` |

## El `.proc` y su configuración

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **El diagrama (`notation:Diagram`) es obligatorio, con una vista por elemento**: sin él el build falla con «No Diagram found» o «No view found for Pool». | Plan 1, aprendizaje 1 (lab `77d212f`); 1769209 | 2026.2 | `tests/test_ids_visuales.py::TestIdsVisuales::test_valores_medidos_en_el_plan_1` |
| **Los namespaces que solo aparecen dentro de valores** (`expression`, `decision` y los de parámetros y conectores) **se declaran en la raíz**; si no, EMF falla con «Class 'Expression' is not found». | Plan 1, aprendizaje 2 (lab `77d212f`); f0d590c, 84caabd, 863ee57 | 2026.2 | `tests/test_proc_flujo.py::TestFlujo::test_namespaces_de_valores_en_la_raiz` |
| **Configuración por entorno embebida en el `.proc`** (`configurations` con actor mapping, `definitionMappings` y parámetros por entorno distinto de Local): el `.conf` externo no la lleva y sin ella el build de Qualification avisa «configuration not found». Solo build: el runtime Subscription no está verificado. | Task 12 del Plan 2 (595c333); doc `build-application.adoc:145-179` | 2026.2 | `tests/test_proc_configuraciones.py::TestConfiguracionesEmbebidas::test_configuracion_por_entorno_embebida` |
| **`definitionMappings type="CONNECTOR"` en mayúsculas**: bonita2bar compara el literal, y con minúsculas el `.bar` sale sin la implementación del conector. Se declara el conector REST como dependencia Maven. Pilot D-14. | Task 11 del Plan 2 (84caabd) | 2026.2 | `tests/test_proc_conectores.py::TestConf::test_definition_mapping_en_mayusculas` |
| **Un conector de entrada de una tarea de servicio escribe sus salidas antes de las operaciones de la tarea**: una operación puede leer la salida del conector. | Task 11 del Plan 2, prueba manual en el bundle (84caabd) | 2026.2 | `tests/test_proc_conectores.py::TestConectorRestGet::test_conector_antes_de_las_operaciones` |
| **Groovy: una sentencia por línea y ninguna línea empieza por operador**: `return x` cierra la sentencia y la línea que sigue con `+` o `&&` es código muerto silencioso. Pilot D-15. | Task 6 del Plan 2 (f0d590c) | 2026.2 | `tests/test_proc_flujo.py::TestFlujo::test_groovy_con_operador_al_principio_de_linea_falla` |
| **Los inputs obligatorios de un contrato se vuelven constraints `mandatory_<ruta>`**; una constraint con ese nombre reservado se rechaza. | Task 9 del Plan 2 (ef19c75); doc `data/contracts-and-contexts.adoc` | 2026.2 | `tests/test_proc_datos.py::TestContratos::test_inputs_obligatorios_como_constraints`; `tests/test_proc_datos.py::TestContratos::test_constraint_con_nombre_de_obligatoria_falla` |
| **La membresía del actor mapping lleva grupo y rol** (`<membership><group>…</group><role>…</role></membership>`), con la ruta del grupo con «/» inicial. | Task 8 del Plan 2 (99e81ae); modelo EMF `ActorMapping.ecore` | 2026.2 | `tests/test_conf.py::TestConf::test_actor_por_rol` |
| **La duración de un timer es un script `as Long` sobre un parámetro Integer**: la doc 2026.2 solo admite texto, Boolean, Integer y Double en parámetros. | Task 5 y Task 13 del Plan 2 (863ee57) | 2026.2 | `tests/test_proc_eventos.py::TestTimerDeBorde::test_timer_borde_anclado_a_su_tarea` |
| **Documentación de cada elemento BPMN de 255 caracteres como máximo.** | Plan 1, revisión de la prueba 1 (lab `77d212f`); f0d590c | 2026.2 | `tests/test_proc_flujo.py::TestFlujo::test_documentacion_maxima_255` |

## Flujo y comportamiento en ejecución

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Un boundary timer solo cuelga de una tarea humana o de una call activity.** Pilot D-03. | Task 13 del Plan 2 (863ee57); doc `process/events` | 2026.2 | `tests/test_proc_eventos.py::TestTimerDeBorde::test_borde_solo_en_humana_o_call_activity` |
| **Orden de salidas de una compuerta XOR: gana la primera condición verdadera y la salida por defecto va al final**; el orden de la documentación es el del `.proc`. Pilot D-04. Es regla de la doc (D-04), no probada en runtime aquí: el test vigila que el generador respete el orden. | Task 6 del Plan 2 (f0d590c); doc `process/gateways` | 2026.2 | `tests/test_proc_flujo.py::TestFlujo::test_orden_de_salidas_xor` |
| **Un join AND espera todas sus entradas**: la spec rechaza un borde interruptor sobre una rama que lo alimenta, porque el caso se cuelga. Pilot D-05. Es regla de la doc/piloto (D-05), no probada en runtime aquí: se vigila que el validador la respete. | Task 6 y Task 13 del Plan 2 (f0d590c, a7a471f); doc `process/gateways` | 2026.2 | `tests/test_proc_flujo.py::TestFlujo::test_and_fork_join`; `tests/test_spec.py::TestErroresSpec::test_borde_interruptor_en_rama_de_un_join_and_falla` |
| **Los eventos de fin no se archivan en 11.1.0 y `archivedFlowNode` solo acepta `f=caseId`**: el fin se deduce del nodo previo completado y de que ningún otro fin case; el estado distinto por camino es la segunda prueba. | Task 13 del Plan 2 (a7a471f), `javap` de `DefaultArchivingStrategy` | 2026.2 | `tests/test_journey.py::TestJourney::test_evidencia_del_fin` |

## Lo versionado es lo generado

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Lo versionado es exactamente lo que produce el generador**: el build compila los ficheros versionados, no los regenerados; un `.proc` o `.conf` editado a mano, huérfano o ausente invalida el proyecto. | Plan 1, corrección `77d212f` (lab); f68cdfc | 2026.2 | `custodios/check_generados.py` |
| **El inventario del `.proc` y del BDM coincide con la documentación** (tareas, transiciones, tipos de nodo, nombres únicos, constraints `mandatory_`). | Task 14 del Plan 2 (f68cdfc, 6d87d42) | 2026.2 | `custodios/check_inventario.py` |
| **Cada expresión Groovy de la documentación tiene su huella y su uso**; si la huella cambia, se regenera. | Task 14 del Plan 2 (f68cdfc) | 2026.2 | `custodios/check_expresiones.py` |
| **Cada salida de compuerta y cada fin tienen un camino que los recorre.** | Task 14 del Plan 2 (f68cdfc) | 2026.2 | `custodios/check_caminos.py` |

## Paquete y hub (Plan 3)

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **npm nunca empaqueta un `.gitignore`**: la plantilla lo guarda como `plantilla/gitignore` y `nuevo_proyecto` le devuelve el punto al montar; sin eso un proyecto creado con el paquete publicado versionaba `target/`, `evidencia/` y `h2_database/`. | f54e802 (aceptación desde el tarball, tarea 17) | 2026.2 (paquete 0.9.0) | `tests/test_plantilla.py::TestNuevoProyecto::test_nuevo_escribe_el_gitignore_de_la_plantilla` |
| **Nunca se escribe bytecode dentro de `tools/arnes/`**: `arnes.sh` fija `PYTHONDONTWRITEBYTECODE=1` y el hook de generados corre `python3 -B`; un `__pycache__` fuera del manifiesto no lo quitaba `uninstall`. | f54e802 (tarea 17) | 2026.2 (paquete 0.9.0) | `tests/test_guard_generados.py::PruebasGuardGenerados::test_no_deja_pycache_en_tools_arnes` |
| **El hub rechaza una evidencia vacía**: el build deja un resumen nunca vacío (`evidencia/ultimo-build.txt`: comando, código de salida, línea `BUILD`, tiempo, artefactos) y `slice-ops.sh gate` / `wiring update` salen 2 en local si el fichero de `--evidence-file` no existe o no tiene texto. | af04298 (tarea 17, ronda 1) | 2026.2 (paquete 0.9.0) | `tests/e2e/e2e_paquete.sh` |
| **La cadena de fases del hub es exacta, sin saltos**: `phase` emite los eslabones que falten hasta la fase pedida y, tras drenar la cola, no re-emite los que el hub ya confirmó (`phase-acks.json`). | af04298; hub `60aa2dfc` (mismas `PHASES`/`GATES`) | 2026.2 (paquete 0.9.0) | `tests/e2e/e2e_paquete.sh` |
| **Los assets del hub solo se aceptan bajo `context/` y `docs/`** y se materializan en `.claude/hub-context/<ruta>` (caché ignorada por git), nunca en el `docs/` del proyecto; las rutas con `~`, `\`, NUL o enlaces simbólicos que escapen se rechazan. | 39c2b6f (contexto del hub en `.claude/hub-context/`) | 2026.2 (paquete 0.9.0) | `tests/e2e/e2e_paquete.sh` |

## Plan 5 — `organizacion`

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Un grupo es una ruta sin barra inicial** en la spec (`empresa/compras/nacional`); `grupos` lleva los intermedios, padres antes que hijos. El XML escribe el último tramo con `parentPath` y las membresías con `groupParentPath`; el `.conf`, la ruta con barra. | R-01; `ACME.xml` del Studio 2026.2-u3; D-30 | 2026.2 | `tests/test_organizacion_plan5.py::TestXmlOrganizacion::test_grupo_con_parent_path`; `tests/test_inventario_organizacion.py::PruebasInventarioOrganizacion::test_grupo_de_menos_en_la_organizacion` |
| **Las claves nuevas de organización solo aparecen cuando no valen su defecto** (`actores[a].roles` con más de un rol, `usuarios[i].manager`/`correo`, `membresias`, `lanes[i].actor_bonita`/`sin_actor`/`filtro`, `actores_tarea`, `nodos[i].terminar`, `consultas[i].paginada`/`por_defecto`): la spec de vacaciones no cambia. | G-5 del contrato del Plan 5 | 2026.2 | `tests/test_vacaciones_dorado.py::PruebaDoradaVacaciones::test_vacaciones_genera_byte_a_byte_lo_mismo` |
| **Quién puede ejecutar una tarea lo decide `candidato()`** (`generadores/escribir/organizacion.py`): actor de tarea si lo hay, si no el actor de negocio de la lane; varios roles, membresías extra y subgrupos (D-31). Los caminos y el journey lo llaman; nadie compara grupo y rol en línea. | A0.9; D-31, D-34 | 2026.2 | `tests/test_organizacion_plan5.py::TestCandidato::test_subgrupo_es_candidato` |
| **El actor Bonita iniciador es el de la lane del evento de inicio**; una lane sin actor no puede tener tareas humanas. | R-02; D-33 | 2026.2 | `tests/test_lanes_actores_plan5.py::TestErroresLanes::test_tarea_humana_en_lane_sin_actor` |
| **Una consulta «(por defecto)» no va a `bom.xml` ni a `consultas.md`**; una «lista paginada» propia exige su `countFor<Nombre>` de conteo (`java.lang.Long`). | R-05; D-35, D-36 | 2026.2 | `tests/test_terminate_consultas_plan5.py::TestConsultas::test_paginada_sin_su_conteo` |
| **El fichero de un perfil es su slug** (`Equipo Compras` → `equipo-compras.xml`); para los nombres `\w+` de antes, el nombre en minúsculas. | R-16 | 2026.2 | `tests/test_organizacion_plan5.py::TestPerfiles::test_slug_de_fichero` |

## Plan 5 — `extensiones`

- **Filtros y conectores propios son código del proyecto**: un módulo por familia en
  `bonita-project/extensions/<modulo>/` (arquetipo de Bonita: `.def` y `.impl` en `src/main/resources-filtered/`
  con `${…}` de las `<properties>` del pom, clases en `src/main/groovy`), registrado con
  `python3 herramientas/registrar_extension.py <proyecto> <modulo>`. El arnés lee el `.def` (id, versión, entradas y
  salidas) y el `.impl` (implementación); no los genera. `generar` sale 2 si falta la definición que nombra la
  documentación. Un `.def` sirve para varios filtros o invocaciones (D-47).
- **Una fila por invocación** en `bpmn.md › Conectores por tarea`: el mismo conector en varias tareas y varias
  veces por tarea, en el orden de ejecución. IDs de entrada `<conector>.<tarea>.<entrada>` y, si la tarea lo invoca
  más de una vez, `<conector>.<tarea>.<n>.<entrada>`; en el `.proc` la invocación se llama `<ID>` o `<ID>_<n>`.
- **Modo `síncrono` siempre**; «el caso no se detiene por el correo» se escribe `IGNORE` en «Manejo de fallo»
  (`ignoreErrors="true"`, D-45). Reintentos, activación por código o bitácora de envíos son lógica del conector del
  proyecto. El servidor SMTP son parámetros de proceso técnicos por entorno (`param_smtpHost`, `param_smtpPuerto`).
- **Filtro efectivo** de una tarea humana: el de su actor de tarea si lo tiene; si no, el de su lane. Se escribe en
  la tarea. Un filtro que devuelve la lista vacía deja la tarea en fallo (D-43): su Groovy de entrada da un respaldo
  cuando el dato puede faltar.

## Plan 5 — `contratos-documentos`

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Un hijo con «sí\|no» tiene obligatoriedad propia** («si llega el padre, el hijo no es nulo»); la forma vieja «nombre (TIPO)» hereda la del padre y conserva su constraint. | Plan 5, R-06 (D-51) | 2026.2 | `tests/test_contratos_documentos.py::TestObligatorias::test_propia_y_anidada` |
| **«— (solo lectura)» exige un lector**: una constraint del contrato o una operación Groovy del mismo contexto nombra el input; «—» a secas sigue siendo error. | Plan 5, veredicto R-06 | 2026.2 | `tests/test_contratos_documentos.py::TestSoloLectura::test_solo_lectura_sin_lector_es_error` |
| **«Tarea que lo aporta» de un documento = los contextos cuyos FILE van a «doc. `…`»**, y la multiplicidad del documento sale de la del FILE (múltiple o hijo de un COMPLEX múltiple → lista). | Plan 5, R-09 | 2026.2 | `tests/test_contratos_documentos.py::TestSpecDocumentos::test_aporta_distinto_de_los_inputs`; `custodios/check_inventario.py` |
| **Un FILE nulo nunca borra el documento vigente**: la operación generada devuelve el vigente (el motor borra con `null`). | Plan 5, R-09 (D-55) | 2026.2 | `tests/test_contratos_documentos.py::TestProcDocumentos::test_operaciones_de_documento_antes_que_las_demas` |
| **Una operación de instanciación no lee un documento del contrato de instanciación**: el motor crea los documentos después de los datos (D-57); su ID lo guarda la primera tarea o una tarea script posterior. `generar` da error si el Groovy nombra el documento. | Plan 5, integración (D-57) | 2026.2 | `tests/test_documento_en_instanciacion.py::TestDocumentoEnInstanciacion::test_cadena_con_el_nombre_del_documento_es_error` |
| **Un «\|» dentro del Groovy de `expresiones.md` se escribe `\|`** (`a \|\| b`): sin escapar parte la fila; el lector común de tablas guarda las celdas que sobran y `generar` lo da como error. | Plan 5, integración (D-59) | 2026.2 | `tests/test_expresiones_pipe.py::TestPipeEnGroovy::test_pipe_sin_escapar_es_error` |

## Plan 5 — `persistencia`

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Operación sobre la business variable entera** (R-07): «`bv nombre` ← `texto` (`op_<ctx>.nombre`)» es un `ASSIGNMENT` a la variable con el Groovy de `expresiones.md` tal cual (devuelve el objeto, o la lista si es múltiple), sin `set_<atributo>`; solo admite un script, una por variable y contexto. En la instanciación es el valor por defecto («entera primero, atributos después»; si el Groovy nombra la propia variable, vale `null`). | Plan 5, hilo `persistencia`; D-60, D-65, D-66 | 2026.2 | `tests/test_persistencia.py::TestEscribir::test_operacion_entera_en_una_tarea`; `tests/test_persistencia.py::TestEscribir::test_instanciacion_atributo_antes_que_la_entera`; `tests/test_persistencia.py::TestValidar::test_variable_entera_solo_con_script` |
| **Familia de plantillas de persistencia**: la fila «Plantilla de persistencia» de `bdm.md` puede nombrar varias (`persistirDesdeContrato`; `persistirDesdeServicio`); cada bloque de operaciones nombra una de ellas. `asignacion-directa` es la única que el arnés conoce y **no admite** destinos `bv`; cualquier otra es del proyecto y sus helpers son código escrito a mano en `bonita-project/extensions/` (dependencia de `app/pom.xml`, como `parametros-adaptador`): el arnés no los genera ni los lee. | Plan 5 (veredicto R-07: versión mínima, sin leer literales) | 2026.2 | `tests/test_persistencia.py::TestSpecFamilia::test_asignacion_directa_no_admite_variable_entera`; `tests/test_persistencia.py::TestSpecFamilia::test_plantilla_fuera_de_la_familia` |
| **La biblioteca de helpers no nombra clases del BDM de forma estática**: crea entidades por nombre con el cargador del objeto recibido o el del hilo y recibe el DAO del script (`<objeto>DAO`, declarado como `TYPE_BUSINESS_OBJECT_DAO` si el script lo usa). El `newInstance` del DAO generado recibe los atributos obligatorios. | D-62, D-63 (bundle Community 2026.2-u0) | 2026.2 | `tests/test_persistencia.py::TestEscribir::test_dos_variables_creadas_en_la_instanciacion`; `tests/test_persistencia.py::TestEscribir::test_sin_dao_si_no_se_usa` |
| **Business variable múltiple** (R-08): «`nombre: Objeto` (múltiple)» → `multiple="true"` en su `BusinessObjectData` y en sus referencias, valor `java.util.List`; solo admite operaciones enteras. Sin operación de instanciación no tiene valor por defecto; varias operaciones `bv` en la instanciación inicializan varias variables en el orden de `bdm.md`. Los nombres de business y process variables de un pool no coinciden. | D-60, D-61 | 2026.2 | `tests/test_persistencia.py::TestEscribir::test_business_variable_multiple`; `tests/test_persistencia.py::TestValidar::test_multiple_solo_admite_la_variable_entera`; `custodios/check_inventario.py` |
| **«Escribe» de servicio y script con operación entera**: lo que pertenece al objeto de una business variable con operación entera es informativo (se admite el objeto solo, `` `Solicitud` ``); lo que escriben las operaciones por atributo y los conectores sigue siendo exacto. Una celda de Operaciones vacía («— (sin escritura)») no nombra plantilla. | Plan 5, contrato §2.8 | 2026.2 | `tests/test_persistencia.py::TestSpecFamilia::test_escribe_de_servicio_informativo_con_variable_entera`; `tests/test_persistencia.py::TestLeerOperaciones::test_servicio_sin_operaciones_no_nombra_plantilla` |

## Plan 5 — `acceso`

- **Reglas dinámicas escritas a mano son una función de Subscription (R-14).** La clase Groovy
  (`app/permisos/reglas/<Regla>.groovy`, sin `package`, `implements PermissionRule`) la escribe el proyecto; el arnés solo
  genera sus líneas en un bloque entre marcadores de `dynamic-permissions-checks-custom.properties` (fichero mixto: lo
  demás es del proyecto). Con `edicion_destino` `community`, `generar` escribe igual y el despliegue (`tools/reglas.py`,
  `tools/studio.py`) las omite con un aviso, sin fallar; nunca bloquean Community. El BDM access control sigue fuera de
  alcance.
- **Patrón de Community: autorización antes que existencia, en la REST API extension.** Sin reglas propias, la
  protección de datos vive en la extensión que lee: primero decide quién es el que pide (familia de actores,
  pertenencia al caso o a la fila) y responde 403 al no autorizado exista o no el dato; el 404 es solo para autorizados
  (si no, la diferencia 403/404 revela qué existe). Los formularios leen solo por la extensión, nunca por
  `/API/bdm/businessData`. Una regla dinámica de Subscription es un cinturón adicional sobre esa misma decisión, no su
  sustituto: el código de la extensión sigue siendo la fuente de verdad que corre en Community.

## Plan 5 — `journey`

Formato en `docs/08-construccion/caminos.md` (contrato del Plan 5, §2.14); ejemplo completo en
`ejemplos/compras/docs/08-construccion/caminos.md`.

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Un input FILE del payload se escribe `{"$archivo": "<nombre.ext>"}`** (en un FILE múltiple, una lista): el journey sube antes un fichero sintético por `API/formFileUpload` (multipart escrito en la colección, con el token CSRF) y pone en su sitio `{filename, tempPath, contentType}`, `contentType` por extensión con una tabla fija. `$archivo` fuera de un input FILE es error de `generar`. | Plan 5, R-15 (D-80) | 2026.2 | `tests/test_validar_journey.py::TestArchivos::test_errores`; `tests/test_journey_r15.py::TestArchivos::test_el_payload_lleva_el_resultado_de_la_subida` |
| **«(no ve `<tarea>`)»** espera la tarea lista en el caso y comprueba que no está entre las pendientes del usuario (`f=user_id`). Solo tiene sentido si un paso posterior la ejecuta (o un timer que el camino espera la interrumpe) y si el usuario no es candidato del actor o la tarea tiene actor filter; si no, `generar` da error. | Plan 5, R-15 (D-81) | 2026.2 | `tests/test_validar_journey.py::TestNoVe::test_candidato_sin_filtro_es_error`; `tests/test_journey_r15.py::TestNoVe::test_script` |
| **«(denegado `MÉTODO ruta`)»** con los códigos aceptados en Payload (`[403, 404]`); huecos `{caso}` y `{<business variable>}` (su `storageId`, leído del contexto del caso vivo por quien instancia). Lo que solo protege Subscription (reglas dinámicas, BDM access control) lleva « [subscription]»: con un bundle de desarrollo Community (`edicion_desarrollo`, la de siempre: también en un proyecto con `edicion_destino` `subscription`, que se prueba en local en Community) el journey lo omite con un aviso, nunca falla; `tools/reglas.py --desarrollo` decide igual si se despliegan las reglas. En Community un usuario cualquiera **lee** el objeto BDM de un caso ajeno (200): sin la marca, ese paso fallaría siempre. | Plan 5, R-15 (D-82) | 2026.2 (bundle Community 2026.2-u0) | `tests/test_journey_r15.py::TestDenegado::test_subscription_en_community_se_omite_con_aviso`; `tests/test_validar_journey.py::TestDenegado::test_errores` |
| **Correos esperados contra el SMTP de prueba** (`herramientas/smtp_prueba.py`, solo biblioteca estándar): «—» o sin línea = no se comprueba; «ninguno» = cero; tabla = tantos mensajes como filas y cada fila casa con uno distinto (asunto contiene; Para y CC como conjuntos de direcciones de las cabeceras). `run-journey.sh` lo levanta solo si la colección declara `smtpUrl` (SMTP en `SMTP_PUERTO`, 2525 = `param_smtpPuerto` de Local; HTTP en `SMTP_HTTP_PUERTO`, 8025) y el journey lo vacía al empezar cada camino. | Plan 5, R-15 (D-83) | 2026.2 | `tests/test_smtp_prueba.py::TestSmtpPrueba::test_guarda_asunto_para_y_cc`; `tests/test_journey_r15.py::TestCorreos::test_aserciones`; `tests/test_run_journey_smtp.py::TestRunJourneySmtp::test_arranca_antes_de_newman_y_pasa_smtp_url` |
| **Lectura de filas múltiples** con la tabla «Consulta \| Parámetros \| Filas \| Valores (en orden)»: `API/bdm/businessData/<clase>?q=<consulta>&p=0&c=…&f=<param>=<valor>` tras el caso archivado; número exacto de filas y valores en el orden de la consulta (que el JPQL lleve `ORDER BY`). Solo consultas que devuelven `lista`. | Plan 5, R-15 (D-84) | 2026.2 | `tests/test_validar_journey.py::TestCorreosYConsultas::test_consultas_mal_escritas`; `tests/test_journey_r15.py::TestConsultas::test_consulta_tras_el_contexto_y_antes_del_logout` |
| **Una fila del caso se nombra en un texto del payload** de una tarea humana: `{<bv>}` (simple), `{<bv>[n]}` (n-ésima fila, desde 1, de una business variable múltiple), `{<bv>.<relación>}` / `{<bv>.<relación>[n]}` (objeto o n-ésima fila de una relación del objeto de `<bv>`), `{<bv>[n].<relación>[m]}` y `{caso}`. El journey las resuelve con la tarea ya asignada, antes de ejecutarla, como su formulario: `GET API/bpm/userTask/<id>/context` (`storageId_string` / `storageIds_string`, en el orden de la lista) y, con relación, `GET API/bdm/businessData/<clase>/<id>/<relación>`; pone el `persistenceId` como texto. Índice mal puesto, relación que no existe, una referencia en la instanciación o un texto entero `{x}` cuya `x` no es `caso` ni una business variable: error de `generar`. | Hueco 6 del MVP «Política corta» (0.11.0; D-85, D-86) | 2026.2 | `tests/test_journey_filas.py::TestEscritor::test_relacion_multiple_de_una_bv_simple`; `tests/test_journey_filas.py::TestValidacion::test_indices_y_relaciones`; `tests/e2e/e2e_compras.sh` |
| **El payload de cada paso lleva todos los inputs del contrato**: el journey pone a `null` los que `caminos.md` no trae (también los hijos de un COMPLEX y de cada elemento de un COMPLEX múltiple); lo que el payload trae no cambia. El motor rechaza con 400 un cuerpo sin un input opcional. | Plan 5, integración (D-52) | 2026.2 | `tests/test_journey_d52.py::TestJourneyConOpcionales::test_la_instanciacion_lleva_todos_los_inputs` |

## Plan 5 — `formato-doc`

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **Un solo formato entre las plantillas de `trycore-spec-product-flow` y los lectores**: lo que un consultor obtiene al rellenar las plantillas del perfil Bonita se lee sin errores; el arnés guarda una copia fijada de las plantillas (`tests/fixtures/plantillas-flow/`, versión en `origen.json`) y, si `TRYCORE_FLOW_PLANTILLAS` apunta a otra copia, avisa cuando difiere. Las variantes de los formatos nuevos del Plan 5 se activan al integrar su hilo. | Plan 5, contrato de formato §2.1 y §4.7 | 2026.2 | `tests/test_contrato_plantillas.py::TestBase::test_plantillas_rellenas_sin_errores`; `tests/test_contrato_plantillas.py::TestFormatoUnico::test_conectores_sincronos_con_ignore` |

## Plan 5 — `huecos-generador`

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **`consultas.md` va por (Objeto, Consulta)**: una consulta con el mismo nombre en varios objetos lleva una fila por objeto; solo es «repetida» si se repite el par. | Hueco del MVP «Política corta» (0.11.0); D-101 | 2026.2 | `tests/test_huecos_generador.py::TestConsultasHomonimas::test_la_misma_consulta_en_dos_objetos_no_es_error` |
| **Un nombre de índice o de unique constraint tiene como mucho 26 caracteres** (una letra y luego letras ASCII, dígitos, `_`, `#`, `@`) y no es una palabra bloqueada de SQL. El generado que no cabe se trunca a 19 caracteres + `_` + 6 hexadecimales del sha1 del nombre completo; los que ya cabían no cambian. Un nombre explícito «(nombre `X`)» inválido o repetido en el BDM es error. | Hueco del MVP (build roto en `generate-bdm-model`); D-100 | 2026.2 | `tests/test_huecos_generador.py::TestNombresDeIndice::test_los_largos_del_mvp_salen_validos_estables_y_distintos`; `tests/test_huecos_generador.py::TestNombresDeIndice::test_nombre_explicito_invalido_es_error` |
| **Un formulario cuyo contrato no tiene inputs va sin tabla de campos** en la matriz y su esqueleto Svelte es de solo acción (envía el cuerpo vacío); con inputs, la tabla sigue siendo obligatoria. | Hueco del MVP (`frm_instanciacion`); D-102 | 2026.2 | `tests/test_huecos_generador.py::TestFormularioSinCampos::test_sin_tabla_y_contrato_sin_inputs_no_es_error`; `tests/test_huecos_generador.py::TestFrontendSoloInstancia::test_la_pantalla_solo_instancia` |

## Plan 5 — `huecos-parametros`

Formato en `catalogo-parametros.md` § Catálogo (contrato del Plan 5, §2.18): huecos del MVP «Política corta» con la 0.11.0.

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **`familia.interna.actores` lleva el nombre del actor del `.proc`**: el Actor Bonita de cada lane que tiene actor (el actor de negocio si la lane no declara otro) y los actores de tarea; la lane sin actor no cuenta. Con visibilidad por familia, el actor de negocio que nombra la matriz se traduce a su Actor Bonita. El módulo compara con el actor de la tarea que da el motor. | MVP 0.11.0, hueco 3 | 2026.2 | `tests/test_escribir_parametros.py::TestBloqueActores::test_actores_bonita_de_las_lanes_y_de_tarea_sin_la_lane_sin_actor` |
| **La semilla no aplana nada**: lista con clave (`` `1` Política `` → código `1`, etiqueta «Política»); campo de una opción → PARAMETRO `<lista>.<campo>` que depende de la lista (INTERNA); tramo-cascada con campos → un PARAMETRO `<tramo>.<campo>` por campo, sin definición `<tramo>`; cascada de `niveles` → una LISTA `<tramo>.<nivel>` por nivel, encadenadas (CLIENTE). Lo que no se puede sembrar es error de `generar` con su ubicación (`generadores/validar/parametros.py`). El proceso lee un campo con `usar(…, "<lista>.<campo>", …, padre = "<clave>")`. | MVP 0.11.0, hueco 5 (D-110, D-111) | 2026.2 | `tests/test_parametros_ricos.py::TestListas::test_lista_con_campos_siembra_un_parametro_por_campo`; `tests/test_parametros_ricos.py::TestCascadaDeNiveles::test_cuatro_niveles_son_cuatro_listas_encadenadas` |
| **La semilla se aplica en la primera llamada a la API de parámetros o en el primer `ParametrosDeProceso.usar`**, no al desplegar: `usar`/`usarConFoto` aplican antes la semilla pendiente que viaja en el classpath del proceso (`semillas/*.json` del jar de `parametros-adaptador`), con la misma operación idempotente que la API (`ServicioDeSemillas.asegurar`), una vez por carga del proceso; un fallo al aplicarla no cambia la lectura. Ningún paso de despliegue la aplica. Lo prueban las specs de Spock de `parametros-core` `SemillaAlUsarCasos` (H2/PostgreSQL), `ParametrosDeProcesoSemillaSpec` y `SemillasDelClasspathSpec`. | Plan 5, `huecos-parametros` (D-112) e integración (D-113) | 2026.2 (bundle Community 2026.2-u0) | `tests/test_parametros_ricos.py::TestSemillaAlUsar::test_usar_asegura_la_semilla_antes_de_leer`; `tests/test_parametros_ricos.py::TestDocumentacion::test_la_skill_avisa_de_la_semilla_en_la_primera_llamada` |
| **El «Catálogo `param_*`» de la matriz nombra una definición que la semilla siembra**: `param_x` para un valor, una lista o un tramo-cascada de un valor; `param_T.<nivel>` para un nivel de una cascada (lista del campo); `param_T.<campo>` o `param_L.<campo>` para un campo (camelCase o snake_case; se lee como un valor). `param_T` de una cascada o de un tramo-cascada con campos, o un sufijo que no existe, es error de `generar` con los nombres correctos. | Plan 5, integración (petición 1 de `huecos-parametros`) | 2026.2 | `tests/test_catalogo_derivado.py::TestReferenciaQueLaSemillaNoSiembra::test_la_cascada_sin_nivel_es_error_y_sugiere_los_niveles`; `tests/test_catalogo_derivado.py::TestFrontend::test_un_nivel_es_la_lista_del_campo` |

## Parche 0.11.1 — familia interna y etiquetas del detalle

Formato en `docs/plan-5/contrato-de-formato.md` §2.19 (hallado con el MVP «Política corta»).

| Convención | Origen | Versión | Vigilada por |
|---|---|---|---|
| **La familia interna la declara la matriz**: «- **Familia interna**: `<familia>`» en Convenciones de `matriz-formularios.md`; sin la línea, la interna se llama `interna`. Una interna declarada que no es la «Familia visible» de ningún formulario Svelte es error de `generar`. El valor de «Familia visible» empieza por el nombre de una sola familia; lo que sigue es explicación. | MVP «Política corta» con la 0.11.0 (`equipo_syp` / `solicitante`) | 2026.2 | `tests/test_leer_matriz.py::TestFamiliaInterna::test_linea_declarada_llega_a_la_spec`; `tests/test_leer_matriz.py::TestFamiliaInterna::test_declarada_que_no_es_de_ningun_formulario_es_error`; `tests/test_escribir_parametros.py::TestFamiliaInternaDeclarada::test_la_declarada_es_la_interna`; `tests/test_leer_matriz.py::TestValorFamiliaVisible::test_varias_familias_es_error` |
| **Una etiqueta del detalle de un formulario parecida a una que se lee no se ignora en silencio**: casi igual a «Form mapping», «Familia visible» o «Acciones» es error con la correcta; dudosa, aviso por stderr. | MVP «Política corta» («Familia de visibilidad» daba una sola aplicación) | 2026.2 | `tests/test_leer_matriz.py::TestEtiquetasDelDetalle::test_etiqueta_casi_conocida_es_error_con_la_correcta`; `tests/test_leer_matriz.py::TestEtiquetasDelDetalle::test_etiquetas_legitimas_sin_error_ni_aviso` |
| **El actor de un formulario con familia sale del BPMN si la columna Actor no es un actor**: actor de tarea o lane de su tarea; instanciación sin tarea, el iniciador; un case overview sin actor no aporta ninguno. | MVP «Política corta» (columna «Analista · `filtroDelCaso`») | 2026.2 | `tests/test_escribir_parametros.py::TestFamiliaInternaDeclarada::test_el_actor_sale_del_bpmn_si_la_columna_no_es_un_actor` |
