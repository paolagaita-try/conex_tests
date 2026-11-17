---
actualizado: 2026-11-12
capa: 0
motor: Bonita
deriva_de: docs/07-bonita/insumo-preventa/reunion-socializacion.md, docs/07-bonita/insumo-preventa/Proceso_Preventa_Bonita.bpmn, docs/08-construccion/fase-0-descubrimiento-hubspot.md, docs/00-parametros/catalogo-parametros.md
total_objetos: 1
---

# Capa 0 — BDM, organización y persistencia — Gestión de Preventa

> Fuente: la reunión de socialización del proceso (`insumo-preventa/reunion-socializacion.md`), el carril «Orquestador Ofelia + HubSpot» del BPMN del insumo y la Fase 0 de HubSpot. Bonita automatiza solo ese carril: asignar el ticket por balance de carga y reflejar dos cambios de estado. El resto del proceso es manual en HubSpot. Los objetos de aquí son los datos mínimos que esa automatización necesita.

## Convenciones

- **Paquete**: `co.trycore.preventa.model`. Un solo paquete.
- **Tipo**: tipo de atributo de Bonita (`bom.xsd` 1.2.2, Bonita 2026.2): `STRING`, `BOOLEAN`…
- **Obligatorio / Múltiple**: las dos marcas que Bonita pide por atributo. Cambiarlas después de desplegar exige un *clean deploy* del BDM.
- **Datos personales**: del ticket solo se copia el asunto (para reconocer el caso al administrarlo). No se copian el MEDDPICC, la descripción, el comercial ni datos de contacto del lead.

## Trazabilidad entidad conceptual → objeto de negocio

| Entidad (modelo-datos.md) | Objeto de negocio | Notas |
|---|---|---|
| Caso de preventa (ticket de HubSpot) | `Preventa` | Agregado raíz; uno por caso de `GestionPreventa` y por ticket |

## Objetos de negocio

### `Preventa` (paquete `co.trycore.preventa.model`)

Traza a: ticket del pipeline «Mesa de preventa» y actividades `A03`–`A06` y `A40` del insumo. Descripción: el caso de preventa visto por la automatización: qué ticket es, a quién se asignó y en qué estado va.

| Atributo | Tipo | Obligatorio | Múltiple | Longitud | Relación | Origen (atributo conceptual / actividad que lo crea) | `[PARAM]` |
|---|---|---|---|---|---|---|---|
| ticketId | STRING | sí | no | 50 | — | id del ticket / instanciación (`ticketId`) | — |
| estado | STRING | sí | no | 40 | — | estado del caso / instanciación (`recibida`), `5_asignarConsultor` (`asignada`), `18_esperarArtefactos` (`op_18_esperarArtefactos.estado`), `40_entregarAVentas` (`entregadaAVentas`) | — |
| asunto | STRING | no | no | 255 | — | `subject` del ticket / `3_consultarTicket` (`conn_hubspotLeer`) | — |
| consultor | STRING | no | no | 100 | — | nombre del consultor asignado, tomado de `param_consultores` / `5_asignarConsultor` (`op_5_asignarConsultor.consultor`) | — |
| consultorOwnerId | STRING | no | no | 50 | — | owner de HubSpot del consultor asignado / `5_asignarConsultor` (`op_5_asignarConsultor.consultorOwnerId`) | — |

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
| `param_consultores` | `89450376:Linda;89450377:Viviana` | `89450376:Linda;89450377:Viviana` | `89450376:Linda;89450377:Viviana` |
| `param_pipelineTickets` | `0` | `0` | `0` |

`param_consultores` es la lista de quienes entran en el reparto, en orden: pares «owner de HubSpot:nombre» separados por «;». Quitar a alguien del reparto (vacaciones, incapacidad) es quitar su par. El bot `88449388` («Trynion») nunca va en la lista.

## Organización

**Grupos** (2): `/trycore`, `/trycore/integracion`.

**Roles** (1): `integracion`.

| Actor (actores-proceso.md) | Grupo | Rol | Membresía de prueba (usuarios de ejemplo) | Actor filter necesario |
|---|---|---|---|---|
| Orquestador | `/trycore/integracion` | `integracion` | `ofelia.bot` | — |

`ofelia.bot` es el usuario técnico con el que el middleware instancia el caso y completa la tarea de espera. Las consultoras no son usuarias de Bonita: trabajan en HubSpot. Quienes entran en el reparto están en el parámetro `param_consultores`, no en la organización.

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

No hay formularios: ninguna persona abre una tarea en Bonita.

## Acceso al BDM (decisión previa a los formularios)

- **Mecanismo**: ninguno desde formularios (no los hay). El middleware no lee el BDM: instancia el caso y completa la tarea de espera por la API de procesos. Para encontrar la tarea de un ticket debe guardar por su cuenta la relación ticket → caso (la instanciación le devuelve el identificador del caso).
- **Perfiles previstos**: ninguno.

## Impacto de objetos añadidos tras el cierre (solo si la capa se reabrió)

| Objeto añadido | Fecha | Tareas cuyas operaciones lo leen o escriben | Formularios afectados |
|---|---|---|---|
| — | — | — | — |

## Pendientes de definición

- **Dónde vive la lista de consultoras**: se documenta como parámetro de proceso (`param_consultores`). En Bonita Community cambiarlo exige volver a desplegar el proceso; en Subscription se edita en caliente. La alternativa (un catálogo en el BDM) necesitaría además una pantalla o un proceso para mantenerlo, que nadie pidió. Requiere confirmación.
- **Escritura real en HubSpot** (`PATCH` del ticket): nunca ejecutada. La lectura y la búsqueda sí se verificaron en vivo el 2026-11-12. `[no verificado]`
