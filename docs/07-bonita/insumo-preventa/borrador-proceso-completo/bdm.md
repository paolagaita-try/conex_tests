---
actualizado: 2026-11-12
capa: 0
motor: Bonita
deriva_de: docs/07-bonita/insumo-preventa/Proceso_Preventa_Bonita.bpmn, docs/07-bonita/insumo-preventa/Documento Proceso Diseño de soluciones.docx, docs/08-construccion/fase-0-descubrimiento-hubspot.md, docs/00-parametros/catalogo-parametros.md
total_objetos: 3
---

# Capa 0 — BDM, organización y persistencia — Gestión de Preventa

> Fuente: el flujo de diseño de soluciones (preventa) entregado el 2026-11-12 (`insumo-preventa/`) y la Fase 0 de descubrimiento de HubSpot (propiedades reales del ticket). El insumo no trae un modelo de datos conceptual: los objetos de aquí son los datos mínimos que el flujo necesita para decidir (compuertas), asignar (round robin) y sincronizar el ticket. Lo que el insumo no define está en «Pendientes de definición».

## Convenciones

- **Paquete**: `co.trycore.preventa.model`. Un solo paquete.
- **Tipo**: tipo de atributo de Bonita (`bom.xsd` 1.2.2, Bonita 2026.2): `STRING`, `TEXT`, `INTEGER`, `BOOLEAN`…
- **Obligatorio / Múltiple**: las dos marcas que Bonita pide por atributo. Cambiarlas después de desplegar exige un *clean deploy* del BDM.
- **Enlaces, no ficheros**: los artefactos de la oferta (insumos, propuesta, estimación, presentación, carpeta) se guardan como enlaces (`STRING` 500) al repositorio de preventa; Bonita no almacena los ficheros.
- **Datos personales**: `descripcion`, `medpicc` y `comercialCreador` vienen del ticket de HubSpot y pueden contener datos de contacto del lead. No se copian más propiedades del ticket que las que el flujo usa.

## Trazabilidad entidad conceptual → objeto de negocio

| Entidad (modelo-datos.md) | Objeto de negocio | Notas |
|---|---|---|
| Caso de preventa (ticket de HubSpot) | `Preventa` | Agregado raíz; uno por caso de `GestionPreventa` y por ticket |
| Consultor elegible para la rotación | `ConsultorPreventa` | Catálogo: usuario de Bonita ↔ owner de HubSpot; lo lee el round robin |
| Turno del round robin | `TurnoAsignacion` | Contador persistente de la rotación (una fila) |

## Objetos de negocio

### `Preventa` (paquete `co.trycore.preventa.model`)

Traza a: ticket de preventa de HubSpot (pipeline «Mesa de preventa») y actividades `A03`–`A42` del insumo. Descripción: el caso de preventa, con los datos del ticket, el consultor asignado, las decisiones del flujo y los enlaces a los artefactos de la oferta.

| Atributo | Tipo | Obligatorio | Múltiple | Longitud | Relación | Origen (atributo conceptual / actividad que lo crea) | `[PARAM]` |
|---|---|---|---|---|---|---|---|
| ticketId | STRING | sí | no | 50 | — | id del ticket / instanciación (`ticketId`) | — |
| estado | STRING | sí | no | 40 | — | estado del caso / instanciación (`recibida`) y las tareas que lo cambian (`contratos.md`) | — |
| asunto | STRING | no | no | 255 | — | `subject` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| descripcion | TEXT | no | no | — | — | `content` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| comercialCreador | STRING | no | no | 100 | — | `comercial_creador` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| tipoRequerimiento | STRING | no | no | 255 | — | `tipo_de_requerimiento` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| medpicc | TEXT | no | no | — | — | `medpicc` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| linkRepositorio | STRING | no | no | 500 | — | `link_repositorio_preventa` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| consultor | STRING | no | no | 100 | — | usuario del consultor asignado / `5_asignarConsultor` (`op_5_asignarConsultor.consultor`) | — |
| consultorOwnerId | STRING | no | no | 50 | — | owner de HubSpot del consultor / `5_asignarConsultor` (`op_5_asignarConsultor.consultorOwnerId`) | — |
| tipoAtencion | STRING | no | no | 30 | — | tipo de atención (`G01`) / `7_analizarRequerimiento` | — |
| productoDemo | STRING | no | no | 30 | — | producto del demo (`A08`) / `8_identificarProducto` | — |
| origenDocumentosDemo | STRING | no | no | 30 | — | documentos de la demo (`G02`, `G03`) / `8_identificarProducto` | — |
| observacionDemo | TEXT | no | no | — | — | resultado de la demo (`A12`) / `12_ejecutarDemo` | — |
| motivoDescarte | TEXT | no | no | — | — | motivo de no continuar (`A13`) / `13_registrarNoContinua` | — |
| preguntasAclaratorias | TEXT | no | no | — | — | preguntas de la licitación (`A33`) / `33_elaborarPreguntas` | — |
| respuestasEntidad | TEXT | no | no | — | — | respuestas de la entidad (`RT1`) / `34_esperarRespuestas` | — |
| supuestos | TEXT | no | no | — | — | supuestos de la propuesta (`A35`) / `35_definirSupuestos` | — |
| enlaceGrabacion | STRING | no | no | 500 | — | grabación y transcripción del levantamiento (`A14`) / `14_realizarLevantamiento` | — |
| conceptoViabilidad | TEXT | no | no | — | — | concepto de viabilidad técnica (`A38`) / `38_validarViabilidad` | — |
| enlaceInsumos | STRING | no | no | 500 | — | paquete de insumos para el agente IA (`A31`) / `31_prepararAnalisis` | — |
| enlacePropuesta | STRING | no | no | 500 | — | propuesta (`A16`, `A17`) / `16_generarArtefactos`, `17_revisarArtefactos` | — |
| enlaceEstimacion | STRING | no | no | 500 | — | estimación (`A16`, `A36`) / `16_generarArtefactos`, `36_revisarEstimacion` | — |
| enlacePresentacion | STRING | no | no | 500 | — | presentación (`A16`, `A17`) / `16_generarArtefactos`, `17_revisarArtefactos` | — |
| observacionAlcance | TEXT | no | no | — | — | ajustes pedidos por el cliente (`A21`) / `21_validarAlcance` | — |
| ajustesPropuesta | TEXT | no | no | — | — | ajustes realizados (`A22`) / `22_ajustarPropuesta` | — |
| motivoRechazo | TEXT | no | no | — | — | motivo del rechazo (`A26`) / `26_registrarRechazo` | — |
| enlaceCarpeta | STRING | no | no | 500 | — | carpeta «Prospectos de Preventa» (`A29`) / `29_entregarCarpeta` | — |

**Unique constraints**: `ticketId` (un ticket, un caso: idempotencia de la instanciación; genera la consulta `findByTicketId`).

**Consultas** (además de las que Bonita genera por defecto por cada atributo):

| Consulta | Parámetros | Devuelve | Quién la necesita (bandeja, tarea, página) |
|---|---|---|---|
| — | — | — | — |

**Índices**: `estado`; `consultor`.

### `ConsultorPreventa` (paquete `co.trycore.preventa.model`)

Traza a: carril «Consultor Preventa» y owners de HubSpot de la Fase 0. Descripción: un consultor elegible para la rotación del round robin, con su usuario de Bonita y su owner de HubSpot. El bot `88449388` («Trynion») no se carga en este catálogo.

| Atributo | Tipo | Obligatorio | Múltiple | Longitud | Relación | Origen (atributo conceptual / actividad que lo crea) | `[PARAM]` |
|---|---|---|---|---|---|---|---|
| usuario | STRING | sí | no | 100 | — | nombre de usuario de Bonita del consultor / carga del catálogo | — |
| ownerId | STRING | sí | no | 50 | — | `hubspot_owner_id` del consultor (Fase 0) / carga del catálogo | — |
| activo | BOOLEAN | sí | no | — | — | disponibilidad del consultor (`A04`) / carga del catálogo | — |

**Unique constraints**: `usuario`.

**Consultas** (además de las que Bonita genera por defecto por cada atributo):

| Consulta | Parámetros | Devuelve | Quién la necesita (bandeja, tarea, página) |
|---|---|---|---|
| `findActivos` | — | lista | `4_verificarDisponibilidad` y `5_asignarConsultor`: los consultores activos ordenados por usuario (JPQL en `docs/08-construccion/consultas.md`) |

**Índices**: `activo`.

### `TurnoAsignacion` (paquete `co.trycore.preventa.model`)

Traza a: actividad `A05` (asignar consultor). Descripción: el contador persistente del round robin (una sola fila, clave `preventa`). Se lee y se escribe sin bloqueo transaccional (decisión del proyecto: no hay Fase 2).

| Atributo | Tipo | Obligatorio | Múltiple | Longitud | Relación | Origen (atributo conceptual / actividad que lo crea) | `[PARAM]` |
|---|---|---|---|---|---|---|---|
| clave | STRING | sí | no | 50 | — | nombre de la rotación / carga inicial (`preventa`) | — |
| ultimoIndice | INTEGER | sí | no | — | — | posición del último consultor asignado / `5_asignarConsultor` (`op_5_asignarConsultor.ultimoIndice`) | — |

**Unique constraints**: `clave`.

**Consultas** (además de las que Bonita genera por defecto por cada atributo):

| Consulta | Parámetros | Devuelve | Quién la necesita (bandeja, tarea, página) |
|---|---|---|---|
| — | — | — | — |

**Índices**: — (ninguno).

## Parámetros (del catálogo) con representación en Bonita

| `param_*` | Tipo en el catálogo | Representación | Módulo / parámetro de proceso | Quién lo administra en producción |
|---|---|---|---|---|
| `param_hubspotUrlBase` | String | parámetro de proceso | `GestionPreventa` › `param_hubspotUrlBase` | Equipo de operación (configuración del entorno) |
| `param_hubspotRutaTickets` | String | parámetro de proceso | `GestionPreventa` › `param_hubspotRutaTickets` | Equipo de operación (configuración del entorno) |
| `param_stageEnValidacion` | String | parámetro de proceso | `GestionPreventa` › `param_stageEnValidacion` | Equipo de operación (configuración del entorno) |
| `param_stageEnDiseno` | String | parámetro de proceso | `GestionPreventa` › `param_stageEnDiseno` | Equipo de operación (configuración del entorno) |
| `param_stageEnEspera` | String | parámetro de proceso | `GestionPreventa` › `param_stageEnEspera` | Equipo de operación (configuración del entorno) |
| `param_stageEntregado` | String | parámetro de proceso | `GestionPreventa` › `param_stageEntregado` | Equipo de operación (configuración del entorno) |
| `param_stageCerrado` | String | parámetro de proceso | `GestionPreventa` › `param_stageCerrado` | Equipo de operación (configuración del entorno) |
| `param_urlAgenteIA` | String | parámetro de proceso | `GestionPreventa` › `param_urlAgenteIA` | Equipo de operación (configuración del entorno) |
| `param_plazoRespuestasMs` | Integer | parámetro de proceso | `GestionPreventa` › `param_plazoRespuestasMs` | Equipo de operación (configuración del entorno) |

**Representación**: todos son **técnicos por entorno** (parámetros de proceso). El token de la Private App de HubSpot **no es un parámetro**: vive solo en la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN` del servidor.

Valores por entorno (Local apunta al doble de pruebas `mock.json`; los `stageId` son los reales de la Fase 0, pipeline «Mesa de preventa» id `0`):

| `param_*` | Local | Qualification | Production |
|---|---|---|---|
| `param_hubspotUrlBase` | `http://localhost:8099/hubspot` | `https://api.hubapi.com` | `https://api.hubapi.com` |
| `param_hubspotRutaTickets` | `/crm/v3/objects/tickets` | `/crm/v3/objects/tickets` | `/crm/v3/objects/tickets` |
| `param_stageEnValidacion` | `2` | `2` | `2` |
| `param_stageEnDiseno` | `3` | `3` | `3` |
| `param_stageEnEspera` | `1425810257` | `1425810257` | `1425810257` |
| `param_stageEntregado` | `1425810258` | `1425810258` | `1425810258` |
| `param_stageCerrado` | `4` | `4` | `4` |
| `param_urlAgenteIA` | `http://localhost:8099/agente-ia` | `http://localhost:8099/agente-ia` | `http://localhost:8099/agente-ia` |
| `param_plazoRespuestasMs` | `20000` | `432000000` | `432000000` |

## Organización

**Grupos** (6): `/trycore`, `/trycore/comercial`, `/trycore/preventa`, `/trycore/tecnologia`, `/trycore/operaciones`, `/trycore/integracion`.

**Roles** (5): `comercial`, `consultor`, `liderTecnico`, `procesos`, `integracion`.

| Actor (actores-proceso.md) | Grupo | Rol | Membresía de prueba (usuarios de ejemplo) | Actor filter necesario |
|---|---|---|---|---|
| Comercial | `/trycore/comercial` | `comercial` | `comercial.uno`, `comercial.dos` | — |
| ConsultorPreventa | `/trycore/preventa` | `consultor` | `consultor.uno`, `consultor.dos`, `consultor.tres` | `filtroConsultorDelCaso` |
| LiderTecnico | `/trycore/tecnologia` | `liderTecnico` | `lider.uno` | — |
| EquipoInterno | `/trycore/operaciones` | `procesos` | `procesos.uno` | — |
| Orquestador | `/trycore/integracion` | `integracion` | `ofelia.bot` | — |
| Sistema | — | — | — | No aplica |

| Actor filter | Tarea que asigna | Qué lee | Definición | Entradas |
|---|---|---|---|---|
| `filtroConsultorDelCaso` | `7_analizarRequerimiento`, `8_identificarProducto`, `9_prepararDemoCliente`, `10_prepararDemoGuia`, `11_construirDocumentosEjemplo`, `12_ejecutarDemo`, `32_analizarLicitacion`, `33_elaborarPreguntas`, `34_esperarRespuestas`, `35_definirSupuestos`, `14_realizarLevantamiento`, `42_analizarDocumentos`, `39_notificarNoViabilidad`, `31_prepararAnalisis`, `15_cargarInsumos`, `17_revisarArtefactos`, `18_cargarArtefactos`, `19_socializarPropuesta`, `41_presentarPropuestaTecnica`, `22_ajustarPropuesta`, `28_presentarAlcanceTraspaso`, `29_entregarCarpeta` | `Preventa.consultor` | `usuario-del-caso` | `usuario` ← `el consultor asignado al caso` (`flt_filtroConsultorDelCaso.usuario`) |

La definición `usuario-del-caso` y su implementación van en `bonita-project/extensions/preventa-filtros/`: devuelve el usuario cuyo nombre recibe en `usuario`. Es lo que hace efectivo el round robin: las tareas del carril Consultor Preventa llegan solo al consultor que eligió `5_asignarConsultor`.

`ofelia.bot` es el usuario técnico con el que el middleware instancia el caso. Los usuarios de ejemplo son de prueba: los consultores reales (owners de HubSpot) se cargan en el catálogo `ConsultorPreventa`, no en el repositorio.

**Contraseña de prueba**: `bpm` (todos los usuarios de ejemplo; solo entornos de prueba).

## Decisión de persistencia (insumo de construcción, con costo de cambio)

| Decisión | Valor | Costo de cambio (artefactos que se tocan si cambia un dato) | Responsable |
|---|---|---|---|
| Business variables del pool | `preventa: Preventa`; `turno: TurnoAsignacion` (se carga por consulta en la tarea 5_asignarConsultor) | `bpmn.md` (compuertas y conectores que leen `preventa`), `contratos.md`, `expresiones.md` | Equipo de construcción |
| Agregado(s) raíz | `Preventa` | `ConsultorPreventa` y `TurnoAsignacion` son catálogos independientes del caso | Equipo de construcción |
| Vía de escritura al BDM | solo por operaciones desde contratos, scripts y salidas de conector | `contratos.md` (operaciones) y `bpmn.md` (conectores) | Equipo de construcción |
| Plantilla de persistencia | `asignacion-directa` | Cada operación de la capa 2 es igual a esta plantilla salvo literales: una operación por atributo destino (input del contrato, literal o Groovy de `expresiones.md`); sin helpers compartidos | Equipo de construcción |
| Snapshot o traza por actividad | no (la traza de negocio es `Preventa.estado` y el histórico del ticket en HubSpot) | — | Equipo de construcción |

## Galería de componentes de interfaz (insumo de construcción, se consume en la capa 3)

| Componente | Para qué campos o formularios | Interfaz fijada (propiedades, eventos) | Estado |
|---|---|---|---|
| — | — | — | — |

Solo widgets estándar; sin componentes propios.

## Acceso al BDM (decisión previa a los formularios)

- **Mecanismo**: REST API extension (`consultas/caso`, la lectura del caso que usan los formularios; nada de `/API/bdm` desde un formulario).
- **Perfiles previstos**: `Preventa` (roles `consultor`, `liderTecnico`); `Comerciales` (rol `comercial`).

## Impacto de objetos añadidos tras el cierre (solo si la capa se reabrió)

| Objeto añadido | Fecha | Tareas cuyas operaciones lo leen o escriben | Formularios afectados |
|---|---|---|---|
| — | — | — | — |

## Pendientes de definición

- **Carga del catálogo `ConsultorPreventa`** (usuario de Bonita ↔ `hubspot_owner_id`, y quién es elegible): es decisión de negocio (Fase 0: «qué owners entran en la rotación»). Falta la lista y quién la administra. Sin ella el round robin no tiene a quién asignar.
- **Carga inicial de `TurnoAsignacion`** (fila `preventa`, `ultimoIndice` = `-1`).
- **Usuarios reales y su mapeo a grupos y roles**: aquí solo hay usuarios de prueba.
- **`param_urlAgenteIA` en Qualification y Production**: no hay servicio definido para el Agente IA; hoy apunta al doble de pruebas en los tres entornos. `[no verificado]`
- **`param_plazoRespuestasMs`**: 20 s en Local para probar el vencimiento; 5 días en los otros entornos es un valor provisional. `[no verificado]`
- **Modelo de datos conceptual**: el insumo no lo trae; los atributos son los mínimos que el flujo usa. Si negocio necesita más datos del ticket en Bonita, se reabre esta capa.
