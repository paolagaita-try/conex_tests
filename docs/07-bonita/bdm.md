---
actualizado: 2026-11-24
capa: 0
motor: Bonita
deriva_de: docs/07-bonita/insumo-preventa/reunion-socializacion.md, docs/07-bonita/insumo-preventa/Proceso_Preventa_Bonita.bpmn, docs/08-construccion/fase-0-descubrimiento-hubspot.md, docs/00-parametros/catalogo-parametros.md
total_objetos: 1
---

# Capa 0 — BDM, organización y persistencia — Gestión de Preventa

> Fuente: la reunión de socialización del proceso (`insumo-preventa/reunion-socializacion.md`), la Fase 0 de HubSpot y la decisión del 2026-11-24 «Bonita-first» (`docs/08-construccion/plan-v2-bonita-first.md`): el equipo de Preventa trabaja en Bonita (validar la solicitud y diseñar la propuesta) y HubSpot solo se alimenta. Los objetos de aquí son lo que la asignación y esas dos tareas necesitan guardar en el caso.

## Convenciones

- **Paquete**: `co.trycore.preventa.model`. Un solo paquete.
- **Tipo**: tipo de atributo de Bonita (`bom.xsd` 1.2.2, Bonita 2026.2): `STRING`, `BOOLEAN`…
- **Obligatorio / Múltiple**: las dos marcas que Bonita pide por atributo. Cambiarlas después de desplegar exige un *clean deploy* del BDM.
- **Datos personales**: del ticket solo se copian el asunto y el identificador del Negocio asociado. El MEDDPICC, la descripción, la empresa y los contactos **no** se copian al BDM: los formularios los leen en vivo de HubSpot por la REST API extension `preventaContexto` (solo lectura, token del lado servidor).

## Trazabilidad entidad conceptual → objeto de negocio

| Entidad (modelo-datos.md) | Objeto de negocio | Notas |
|---|---|---|
| Caso de preventa (ticket de HubSpot) | `Preventa` | Agregado raíz; uno por caso de `GestionPreventa` y por ticket |

## Objetos de negocio

### `Preventa` (paquete `co.trycore.preventa.model`)

Traza a: ticket del pipeline «Mesa de preventa», actividades `A03`–`A06` y `A40` del insumo, y las tareas `10_validarSolicitud` y `20_disenarPropuesta` (v2, 2026-11-24). Descripción: el caso de preventa: qué ticket y Negocio es, a quién se asignó, qué concluyó la validación, qué artefactos entregó el diseño y cuándo pasó cada etapa.

| Atributo | Tipo | Obligatorio | Múltiple | Longitud | Relación | Origen (atributo conceptual / actividad que lo crea) | `[PARAM]` |
|---|---|---|---|---|---|---|---|
| ticketId | STRING | sí | no | 50 | — | id del ticket / instanciación (`ticketId`) | — |
| estado | STRING | sí | no | 40 | — | estado del caso / instanciación (`recibida`), `5_asignarConsultor` (`asignada`), `10_validarSolicitud` (`op_10_validarSolicitud.estado`: `validada`, `bloqueada` o `noViable`), `20_disenarPropuesta` (`propuestaDisenada`), `40_entregarAVentas` (`entregadaAVentas`) | — |
| asunto | STRING | no | no | 255 | — | `subject` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| consultor | STRING | no | no | 100 | — | nombre del consultor asignado, tomado de `param_consultores` / `5_asignarConsultor` (`op_5_asignarConsultor.consultor`) | — |
| consultorOwnerId | STRING | no | no | 50 | — | owner de HubSpot del consultor asignado / `5_asignarConsultor` (`op_5_asignarConsultor.consultorOwnerId`) | — |
| dealId | STRING | no | no | 50 | — | id del Negocio asociado al ticket / `3_consultarTicket` (`conn_hubspotLeer`, salida `dealId`); primer Negocio asociado, vacío si no hay | — |
| resultadoValidacion | STRING | no | no | 20 | — | resultado de la validación (`viable`, `bloqueado`, `no_viable`) / `10_validarSolicitud` (input `resultado`) | — |
| conceptoViabilidad | TEXT | no | no | — | — | propiedad `concepto_viabilidad` del Negocio / `10_validarSolicitud` (input `conceptoViabilidad`) | — |
| notaValidacion | TEXT | no | no | — | — | nota de la validación / `10_validarSolicitud` (input `notaValidacion`) | — |
| supuestos | TEXT | no | no | — | — | supuestos de la validación / `10_validarSolicitud` (input `supuestos`) | — |
| valoracionOperaciones | TEXT | no | no | — | — | propiedad `valoracion_operaciones` del Negocio / `20_disenarPropuesta` (input `valoracionOperaciones`) | — |
| urlPptaPreventa | STRING | no | no | 1000 | — | propiedad `url_ppta_preventa` del Negocio / `20_disenarPropuesta` (input `urlPptaPreventa`) | — |
| linkRepoPreventa | STRING | no | no | 1000 | — | propiedad `link_repo_preventa` del Negocio / `20_disenarPropuesta` (input `linkRepoPreventa`) | — |
| notaPropuesta | TEXT | no | no | — | — | nota de la propuesta / `20_disenarPropuesta` (input `notaPropuesta`) | — |
| cantidadAdjuntos | INTEGER | no | no | — | — | número de adjuntos de la propuesta / `20_disenarPropuesta` (`op_20_disenarPropuesta.cantidadAdjuntos`); lo lee `gwXor_2` | — |
| fechaRecepcion | OFFSETDATETIME | no | no | — | — | inicio del caso / instanciación (`op_instanciacion.fechaRecepcion`) | — |
| fechaAsignacion | OFFSETDATETIME | no | no | — | — | asignación / `5_asignarConsultor` (`op_5_asignarConsultor.fechaAsignacion`) | — |
| fechaValidacion | OFFSETDATETIME | no | no | — | — | última validación / `10_validarSolicitud` (`op_10_validarSolicitud.fechaValidacion`) | — |
| fechaPropuesta | OFFSETDATETIME | no | no | — | — | propuesta diseñada / `20_disenarPropuesta` (`op_20_disenarPropuesta.fechaPropuesta`) | — |
| fechaEntrega | OFFSETDATETIME | no | no | — | — | entrega a ventas / `40_entregarAVentas` (`op_40_entregarAVentas.fechaEntrega`) | — |

**Unique constraints**: `ticketId` (un ticket, un caso: es la base de la idempotencia esperada de la instanciación, `[no verificado]` en ejecución; genera la consulta `findByTicketId`).

**Consultas** (además de las que Bonita genera por defecto por cada atributo):

| Consulta | Parámetros | Devuelve | Quién la necesita (bandeja, tarea, página) |
|---|---|---|---|
| `findAsignadasRecientes` | — | lista | `4_verificarDisponibilidad`: los casos que ya tienen consultor, por `persistenceId` descendente (orden de creación del caso, que se toma como orden de asignación); el primero dice quién fue el último asignado, para el desempate (JPQL en `docs/08-construccion/consultas.md`) |

**Índices**: `estado`; `consultorOwnerId` (lo usa `findAsignadasRecientes`).

## Parámetros (del catálogo) con representación en Bonita

| `param_*` | Tipo en el catálogo | Representación | Módulo / parámetro de proceso | Quién lo administra en producción |
|---|---|---|---|---|
| `param_hubspotUrlBase` | String | parámetro de proceso | `GestionPreventa` › `param_hubspotUrlBase` | Equipo de operación (configuración del entorno) |
| `param_hubspotRutaTickets` | String | parámetro de proceso | `GestionPreventa` › `param_hubspotRutaTickets` | Equipo de operación (configuración del entorno) |
| `param_stageEnValidacion` | String | parámetro de proceso | `GestionPreventa` › `param_stageEnValidacion` | Equipo de operación (configuración del entorno) |
| `param_stageEnDiseno` | String | parámetro de proceso | `GestionPreventa` › `param_stageEnDiseno` | Equipo de operación (configuración del entorno) |
| `param_stageEntregado` | String | parámetro de proceso | `GestionPreventa` › `param_stageEntregado` | Equipo de operación (configuración del entorno) |
| `param_stageEnEspera` | String | parámetro de proceso | `GestionPreventa` › `param_stageEnEspera` | Equipo de operación (configuración del entorno) |
| `param_stageCerrado` | String | parámetro de proceso | `GestionPreventa` › `param_stageCerrado` | Equipo de operación (configuración del entorno) |
| `param_consultores` | String | parámetro de proceso | `GestionPreventa` › `param_consultores` | Equipo de operación (configuración del entorno) |
| `param_pipelineTickets` | String | parámetro de proceso | `GestionPreventa` › `param_pipelineTickets` | Equipo de operación (configuración del entorno) |

**Representación**: todos son **técnicos por entorno** (parámetros de proceso). El token de la Private App de HubSpot **no es un parámetro**: vive solo en la variable de entorno `HUBSPOT_PRIVATE_APP_TOKEN` del servidor.

Valores por entorno (Local apunta al doble de pruebas `mock.json`; los `stageId` son los reales de la Fase 0, pipeline «Mesa de preventa» id `0`):

| `param_*` | Local | Qualification | Production |
|---|---|---|---|
| `param_hubspotUrlBase` | `http://localhost:8099/hubspot` | `https://api.hubapi.com` | `https://api.hubapi.com` |
| `param_hubspotRutaTickets` | `/crm/v3/objects/tickets` | `/crm/v3/objects/tickets` | `/crm/v3/objects/tickets` |
| `param_stageEnValidacion` | `2` | `2` | `2` |
| `param_stageEnDiseno` | `3` | `3` | `3` |
| `param_stageEntregado` | `1425810258` | `1425810258` | `1425810258` |
| `param_stageEnEspera` | `1425810257` | `1425810257` | `1425810257` |
| `param_stageCerrado` | `4` | `4` | `4` |
| `param_consultores` | `89450376:Linda:linda.lozano;89450377:Viviana:viviana.velasquez` | `89450376:Linda:linda.lozano;89450377:Viviana:viviana.velasquez` | `89450376:Linda:linda.lozano;89450377:Viviana:viviana.velasquez` |
| `param_pipelineTickets` | `0` | `0` | `0` |

`param_consultores` es la lista de quienes entran en el reparto, en orden: tríos «owner de HubSpot:nombre:usuario de Bonita» separados por «;» (v2, 2026-11-24: se añade el usuario de Bonita, que el actor filter `filtroConsultoraDelCaso` usa para que la tarea llegue solo a la consultora elegida). Un par antiguo sin usuario sigue sirviendo para el reparto, pero la tarea humana quedaría en fallo al asignarse. Quitar a alguien del reparto (vacaciones, incapacidad) es quitar su par. El bot `88449388` («Trynion») nunca va en la lista.

## Organización

**Grupos** (3): `/trycore`, `/trycore/integracion`, `/trycore/preventa`.

**Roles** (2): `integracion`, `consultora`.

| Actor (actores-proceso.md) | Grupo | Rol | Membresía de prueba (usuarios de ejemplo) | Actor filter necesario |
|---|---|---|---|---|
| Orquestador | `/trycore/integracion` | `integracion` | `ofelia.bot` | — |
| Consultora | `/trycore/preventa` | `consultora` | `linda.lozano`, `viviana.velasquez` | `filtroConsultoraDelCaso` |

| Usuario | Grupo / rol | Manager | Correo |
|---|---|---|---|
| `ofelia.bot` | `/trycore/integracion` / `integracion` | — | — |
| `linda.lozano` | `/trycore/preventa` / `consultora` | — | — |
| `viviana.velasquez` | `/trycore/preventa` / `consultora` | — | — |

| Actor filter | Tarea que asigna | Definición | Entradas |
|---|---|---|---|
| `filtroConsultoraDelCaso` | `10_validarSolicitud`, `20_disenarPropuesta` | `usuario-por-nombre` | `usuario` ← `el usuario de Bonita que param_consultores da al owner de HubSpot del consultor asignado` (`flt_filtroConsultoraDelCaso.usuario`) |

`ofelia.bot` es el usuario técnico con el que el middleware instancia el caso. Las consultoras (`linda.lozano` = owner HubSpot `89450376`, `viviana.velasquez` = owner `89450377`) son usuarias de Bonita desde la v2: trabajan sus tareas en formularios de Bonita. El actor filter `usuario-por-nombre` (módulo propio `bonita-project/extensions/preventa-filtros`) entrega cada tarea humana **solo** a la consultora que eligió el reparto y se la asigna directamente; si el usuario no existe, la tarea queda en fallo en lugar de llegar a otra persona. El enlace owner → usuario vive en `param_consultores`.

**Contraseña de prueba**: `bpm` (solo entornos de prueba).

## Decisión de persistencia (insumo de construcción, con costo de cambio)

| Decisión | Valor | Costo de cambio (artefactos que se tocan si cambia un dato) | Responsable |
|---|---|---|---|
| Business variables del pool | `preventa: Preventa` | `bpmn.md` (conectores que leen `preventa`), `contratos.md`, `expresiones.md` | Equipo de construcción |
| Agregado(s) raíz | `Preventa` | Es el único objeto; el último asignado se lee de los casos anteriores, no se guarda aparte | Equipo de construcción |
| Vía de escritura al BDM | solo por operaciones desde contratos, scripts y salidas de conector | `contratos.md` (operaciones) y `bpmn.md` (conectores) | Equipo de construcción |
| Plantilla de persistencia | `asignacion-directa` | Cada operación de la capa 2 es igual a esta plantilla salvo literales: una operación por atributo destino (input del contrato, literal o Groovy de `expresiones.md`); sin helpers compartidos | Equipo de construcción |
| Snapshot o traza por actividad | no (la traza de negocio es `Preventa.estado` y el histórico del ticket en HubSpot) | — | Equipo de construcción |

## Galería de componentes de interfaz (insumo de construcción, se consume en la capa 3)

| Componente | Para qué campos o formularios | Interfaz fijada (propiedades, eventos) | Estado |
|---|---|---|---|
| — | — | — | — |

No hay componentes propios: `frm_10_validarSolicitud`, `frm_20_disenarPropuesta` y `frm_overview` usan los widgets de la plantilla Svelte (ver `matriz-formularios.md`).

## Acceso al BDM (decisión previa a los formularios)

- **Mecanismo**: REST API extension. Lo del caso (`Preventa`) se lee por la extensión de consultas; lo del CRM (ticket, Negocio, empresa, contactos, owner) por la REST API extension **`preventaContexto`** (`GET …/API/extension/preventa/contexto?ticketId=`), que llama a HubSpot del lado servidor con `HUBSPOT_PRIVATE_APP_TOKEN` y devuelve un JSON de solo lectura. El token nunca llega al navegador. La implementa otra unidad de trabajo (agente B); aquí solo se referencia.
- **Perfiles previstos**: `User` (rol `consultora`)

## Impacto de objetos añadidos tras el cierre (solo si la capa se reabrió)

| Objeto añadido | Fecha | Tareas cuyas operaciones lo leen o escriben | Formularios afectados |
|---|---|---|---|
| — | — | — | — |

## Pendientes de definición

- **Dónde vive la lista de consultoras**: se documenta como parámetro de proceso (`param_consultores`). En Bonita Community cambiarlo exige volver a desplegar el proceso; en Subscription se edita en caliente. La alternativa (un catálogo en el BDM) necesitaría además una pantalla o un proceso para mantenerlo, que nadie pidió. Requiere confirmación.
- **Tipo de `concepto_viabilidad` y `valoracion_operaciones` en HubSpot**: verificado por GET al esquema el 2026-11-25. `concepto_viabilidad` es una enumeración (select, valor interno = etiqueta) de cuatro opciones y `valoracion_operaciones` una URL. En el BDM siguen como `TEXT`; las opciones y el formato los exige el contrato (`contratos.md`, versión 1.3).
- **Escritura real en HubSpot** (`PATCH` del ticket): nunca ejecutada. La lectura y la búsqueda sí se verificaron en vivo el 2026-11-12. `[no verificado]`
