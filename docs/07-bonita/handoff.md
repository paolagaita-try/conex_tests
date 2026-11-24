---
estado: listo-para-construccion
proyecto: hubspot-bonita
generado_por: agent01
fecha: 2026-11-24
---

# Handoff de construcción — Integración HubSpot ↔ Bonita

> **Alcance de este handoff.** Cubre la entrada del proyecto (descubrimiento y decisiones) y el diseño del proceso
> (capas 0–3), redactado el 2026-11-12 a partir del flujo de diseño de soluciones (preventa) y de la reunión de
> socialización de ese flujo. Fuentes: `docs/07-bonita/insumo-preventa/` (BPMN, manual, imagen y
> `reunion-socializacion.md`) y `HANDOFF-SCAFFOLD.md`.

## Qué se construye (v2 «Bonita-first», decisión del 2026-11-24)

> **La decisión del 2026-11-24 reemplaza el alcance del 12-nov** («Bonita automatiza solo el carril del orquestador»).
> La usuaria aprobó el plan `docs/08-construccion/plan-v2-bonita-first.md` («construye»). El equipo de Preventa **no
> vuelve a entrar a HubSpot**: trabaja en Bonita y Bonita alimenta el CRM.

Proceso `GestionPreventa` **1.1** (`bpmn.md`):

1. Al crearse un ticket en HubSpot se instancia el caso (middleware, webhook `ticket.creation`), con idempotencia
   esperada por `ticketId` (`[no verificado]` en ejecución).
2. Bonita **asigna por carga ponderada por prioridad** (sin cambios) y escribe owner + «En validación».
3. **`10_validarSolicitud`** (tarea humana, solo la consultora elegida: actor filter `filtroConsultoraDelCaso`, owner
   HubSpot → usuario Bonita por `param_consultores`): viable / bloqueado / no viable, con nota en ticket y Negocio.
   - viable → `11_pasarADiseno`: stage «Asignado/En diseño» y `concepto_viabilidad` en el Negocio;
   - bloqueado → `12_pasarAEnEspera`: stage «En espera información del lead» y vuelve a validación;
   - no viable → `13_registrarNoViable`: `concepto_viabilidad` y ticket a **«Closed»** (cerrado por viabilidad;
     nota «Cerrado por viabilidad: …»; decisión de la usuaria, 2026-11-24).
4. **`20_disenarPropuesta`** (misma consultora): las cuatro propiedades del Negocio, nota y adjuntos
   (`21_subirAdjuntos` si los hay); `40_entregarAVentas` pasa el ticket a «Entregado a ventas».
5. El cierre lo hace el comercial en HubSpot, como hoy.

Se retira la espera `18_esperarArtefactos` y la segunda entrada del middleware (artefactos→caso). Los formularios
precargan todo el CRM de solo lectura por la REST API extension `preventaContexto` (`GET preventa/contexto?ticketId=`).
Organización: grupo `/trycore/preventa`, rol `consultora`, usuarias `linda.lozano` (owner `89450376`) y
`viviana.velasquez` (owner `89450377`). Evidencia: `docs/08-construccion/evidencia-v2-proceso.md`.

## Arquitectura acordada

- **Entrada (ticket→caso):** webhook `ticket.creation` → middleware externo →
  `POST /bonita/API/bpm/process/{id}/instantiation`. Es la única entrada desde la v2.
- **Salida:** conectores REST **propios** hacia HubSpot: leer el ticket, carga por consultora, `PATCH` del ticket,
  `PATCH` del Negocio, notas asociadas a ticket y Negocio, subida de archivos. No se usa el conector oficial.
- **Lectura para formularios:** REST API extension `preventaContexto` (token solo del lado servidor).
- **Reconciliación:** job diario Bonita vs HubSpot (sin decidir dónde vive).

### Alcance anterior (12-nov, reemplazado)

#### Qué se construía

Bonita automatiza **solo el carril del orquestador** del proceso de preventa. Todo lo demás lo hacen las personas en
HubSpot, como hoy.

1. Al crearse un ticket en HubSpot (queda en «Solicitud recibida») se instancia un caso en Bonita, con idempotencia
   esperada por `ticketId` (`[no verificado]` en ejecución).
2. Bonita **asigna el ticket por balance de carga**: a la consultora que tenga menos tickets en los stages «En
   validación» y «Asignado/En diseño». Hoy son dos consultoras (Linda y Viviana) y la asignación la hace una persona
   a criterio en el daily.
3. Bonita escribe en el ticket el **propietario** y el stage **«En validación»**.
4. El caso espera mientras las consultoras trabajan en HubSpot.
5. Cuando se cargan los artefactos en el **negocio** asociado, Bonita pasa el **ticket** a **«Entregado a ventas»**.

Bonita **no** mueve el ticket de «En validación» a «Asignado/En diseño» (lo hace la consultora), **no** lo cierra (lo
hace el comercial) y **no** toca las etapas del negocio.

**Cambios frente al planteamiento del 2026-11-11** (los fija la reunión, ver `reunion-socializacion.md`):

| Antes | Ahora |
|---|---|
| Asignación por round robin | Asignación por balance de carga; alternar solo se usa como desempate (propuesta) |
| Cada transición del flujo se refleja como stage del ticket | Bonita escribe dos stages: «En validación» y «Entregado a ventas» |
| El proceso completo (40 tareas) como tareas de Bonita | Solo las 5 actividades del orquestador (`A03`–`A06`, `A40`) más una espera |
| Agente IA como integración | No hay integración: es una herramienta que las consultoras usan a mano |

El borrador del proceso completo queda archivado, sin uso, en `insumo-preventa/borrador-proceso-completo/`.

#### Arquitectura de entonces

- **Entrada (ticket→caso):** un Workflow nativo de HubSpot (Sales Hub Pro) dispara un webhook al crearse el ticket; el
  middleware externo lo recibe y llama a `POST /bonita/API/bpm/process/{id}/instantiation`.
- **Segunda entrada (artefactos→caso):** otro Workflow nativo dispara un webhook cuando cambian las propiedades del
  negocio; el middleware completa la tarea de espera del caso si los cuatro artefactos tienen valor, o si el ticket se
  cerró sin entregar. **Vía confirmada (Workflows nativos); el middleware aún no existe.**
- **Salida:** conectores REST **propios** del proyecto hacia HubSpot: leer el ticket, contar la carga por consultora y
  `PATCH` del ticket (`hs_pipeline_stage`, `hubspot_owner_id`). No se usa el conector oficial Bonita–HubSpot.
- **Reconciliación:** job diario Bonita vs HubSpot (sin decidir dónde vive).

## Decisiones vigentes

- **v2 «Bonita-first» (2026-11-24):** reemplaza el alcance del 12-nov (ver «Qué se construye»). «No viable» cierra el
  ticket («Closed», `4`) con nota «Cerrado por viabilidad:» (decisión de la usuaria, 2026-11-24).

- **Plan de HubSpot = Sales Hub Pro (confirmado 2026-11-13):** no se compra Operations Hub Pro. El middleware es un
  servicio externo propio, disparado por Workflows nativos de HubSpot (incluidos en Sales Hub Pro) que llaman por
  webhook al crearse el ticket y al cambiar las propiedades del negocio. Lo construye la encargada del proyecto.
- **No hay Fase 2:** la asignación no usa bloqueo transaccional ni contador; el último asignado se lee del caso
  más reciente.
- **Responsable de desarrollo:** el agente.
- **Token de Private App de HubSpot:** lo gestiona Laura; nunca en repo ni en argumentos (solo variable de entorno).

## Insumos de descubrimiento (entrada)

- **Reunión de socialización del proceso:** `docs/07-bonita/insumo-preventa/reunion-socializacion.md`.
- **Flujo de preventa:** `docs/07-bonita/insumo-preventa/` (BPMN, manual, imagen).
- **Fase 0 — IDs reales de HubSpot (verificada en vivo):** `docs/08-construccion/fase-0-descubrimiento-hubspot.md`.
  Pipeline «Mesa de preventa» id=0, 6 stages, 18 owners (las dos consultoras: `89450376` y `89450377`, en `param_consultores`; el owner
  `88449388` «Trynion» es un bot y no entra en el reparto).
- **Arquitectura:** `docs/arquitectura-hubspot-bonita.html` (anterior a la reunión; no refleja el alcance actual).
- **Opciones y costos:** `docs/hubspot-bonita-opciones-costes-referencia.md`.
- **Conector oficial (referencia de por qué NO se usa):** `docs/conector-hubspot-bonita-referencia.md`.

## Estado de los gates

| Gate | Estado |
|---|---|
| entrada | pasa |
| capa-0 | pasa |
| capa-1 | pasa |
| capa-2 | pasa |
| capa-3 | pasa |

> Las cuatro capas pasaron una auditoría adversarial independiente en dos pasadas (la primera dio «no pasa» a las
> capas 0, 1 y 2; la segunda, «pasa» a las cuatro con observaciones menores ya aplicadas). Informe: `docs/.reviews/2026-11-13-auditoria-capas-0-3.md`.
>
> | Capa | Documento | Contenido | Comprobación ejecutada |
> |---|---|---|---|
> | 0 | `docs/07-bonita/bdm.md` | 1 objeto, 1 actor, 7 parámetros | el lector del arnés la parsea sin errores de formato |
> | 1 | `docs/07-bonita/bpmn.md` | 6 tareas, 1 compuerta, 9 transiciones, 4 invocaciones de 3 conectores | parsea sin errores de formato |
> | 2 | `docs/07-bonita/contratos.md` | 2 contratos | parsea sin errores de formato |
> | 3 | `docs/07-bonita/matriz-formularios.md` | 3 registros, los tres `No form` | parsea sin errores de formato |
>
> Lo que `construir_spec` todavía reporta es trabajo de construcción: el Groovy de
> `docs/08-construccion/expresiones.md`, `consultas.md`, `caminos.md` y las definiciones de los tres conectores
> propios (`hubspot-ticket-leer`, `hubspot-consultores-menor-carga`, `hubspot-ticket-actualizar`).

## Términos marcados `[no verificado]`

Verificado en vivo el 2026-11-12, solo lectura: la ruta de tickets, la búsqueda por propietario y stage que mide la
carga (dio 0 y 1 ticket para las dos consultoras, como en la reunión), que los tickets tienen negocio asociado y los
nombres de las cuatro propiedades del negocio donde se cargan los artefactos. Sigue sin verificar:

- **Escritura `PATCH` del ticket en HubSpot:** nunca ejecutada. Por política de la empresa no se tocan tickets reales
  de producción: las pruebas de escritura van contra mocks/Postman o un entorno aislado (confirmado 2026-11-13).
- **Comportamiento en ejecución de Bonita:** rechazo de un segundo caso del mismo ticket; completar por API la tarea
  de espera con el usuario técnico.

## Puntos que la reunión no resuelve

Son elecciones de diseño de esta documentación; están aplicadas y pueden cambiarse.

1. **Empate de carga**: si las dos consultoras tienen la misma cantidad de tickets, se alterna respecto de la última
   asignada.
2. **Cómo se entera Bonita de que se cargaron los artefactos**: una tarea de espera que completa el middleware cuando un
   Workflow nativo de HubSpot le avisa del cambio en el negocio. Criterio confirmado por negocio: los cuatro campos
   (`concepto_viabilidad`, `estimacion_costos`, `url_ppta_preventa`, `link_repo_preventa`), que completa comercial, con
   algún valor (no vacíos). El generador no soporta eventos de mensaje; la tarea de espera es la forma soportada.
3. **Tickets que se cierran sin entregar** (demo descartada, requerimiento no viable): el middleware completa la
   espera con `cerrado` y el caso termina sin escribir en HubSpot.
4. **Prioridad y ANS del ticket**: no intervienen en la asignación.
5. **Middleware**: no está en este repositorio; lo construye la encargada del proyecto (servicio externo). Sin él la
   automatización no arranca en producción.
6. **Lista de consultoras** como parámetro de proceso (`param_consultores`): en Community cambiarla exige
   volver a desplegar.
7. **Job de reconciliación diaria**: dónde vive.
8. **La espera no tiene temporizador**: un caso solo termina cuando el middleware informa; sin reconciliación, un
   aviso perdido deja el caso abierto.
