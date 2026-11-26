---
estado: listo-para-construccion
proyecto: hubspot-bonita
generado_por: agent01
fecha: 2026-11-25
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

Proceso `GestionPreventa` **1.4** (`bpmn.md`). El equipo de Preventa opera **100 % desde Bonita**: abre su tarea en
el portal de Bonita, ve el CRM precargado en el formulario y, al enviar, Bonita escribe en HubSpot el stage del
ticket, las notas, las propiedades del Negocio y los adjuntos. El middleware solo instancia el caso.

1. Al crearse un ticket en HubSpot se instancia el caso (middleware, webhook `ticket.creation`), con idempotencia
   esperada por `ticketId` (`[no verificado]` en ejecución).
2. Bonita **asigna por carga ponderada por prioridad** (URGENT 4, HIGH 3, MEDIUM 2, LOW 1, sin prioridad 2; tickets
   del pipeline «Mesa de preventa» en «En validación» y «Asignado/En diseño»; el ticket que se asigna no cuenta; el bot
   `88449388` no entra) y escribe owner + «En validación».
3. **`10_validarSolicitud`** (formulario «Validar la solicitud», solo la consultora elegida: actor filter
   `filtroConsultoraDelCaso`, owner HubSpot → usuario Bonita por `param_consultores`): viable / bloqueado / no viable,
   con nota en ticket y Negocio. El concepto de viabilidad (`concepto_viabilidad` del Negocio) depende del resultado:
   - viable → la consultora elige «Aprobado (Viable)» o «Aprobado con Condiciones» (este exige las condiciones, que
     quedan en la nota de HubSpot); `11_pasarADiseno`: stage «Asignado/En diseño» y concepto en el Negocio;
   - bloqueado → el proceso fija «Requiere más información»; `12_pasarAEnEspera`: concepto en el Negocio, stage «En
     espera información del lead» y vuelve a validación (la nota dice lo que falta);
   - no viable → el proceso fija «No Viable (Rechazado)»; `13_registrarNoViable`: concepto en el Negocio y ticket a
     **«Closed»** (cerrado por viabilidad; nota «Cerrado por viabilidad: …»; decisión de la usuaria, 2026-11-24).
4. **`20_disenarPropuesta`** (formulario «Diseñar la propuesta», misma consultora): los cuatro artefactos del Negocio
   (`concepto_viabilidad`, `valoracion_operaciones`, `url_ppta_preventa`, `link_repo_preventa`), nota y adjuntos
   (`21_subirAdjuntos` si los hay); `40_entregarAVentas` pasa el ticket a «Entregado a ventas».
5. El cierre lo hace el comercial en HubSpot, como hoy.

Los formularios precargan todo el CRM de solo lectura por la REST API extension `preventaContexto`
(`GET preventa/contexto?ticketId=`). Organización: grupo `/trycore/preventa`, rol `consultora`, usuarias
`linda.lozano` (owner `89450376`) y `viviana.velasquez` (owner `89450377`). Evidencia del proceso v2:
`docs/08-construccion/evidencia-v2-proceso.md`.

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
  servicio externo propio (`middleware/`, Rust) con una sola entrada: el webhook `ticket.creation`. No escucha cambios
  del Negocio ni del ticket: todo lo que pasa después lo escribe Bonita.
- **Concepto de viabilidad por resultado (versión 1.4, reglas aprobadas por la usuaria el 2026-11-25):** viable admite
  «Aprobado (Viable)» o «Aprobado con Condiciones» (con condiciones obligatorias); bloqueado escribe «Requiere más
  información» y no viable «No Viable (Rechazado)», sin que la consultora los elija.
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
- **Arquitectura:** vigente en `README.md` y `docs/arquitectura-eventos.md`; `docs/arquitectura-hubspot-bonita.html` es
  el diagrama del 2026-11-11 (anterior a la reunión), marcado como histórico.
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

- **Escritura en HubSpot real:** solo con un ticket y un Negocio de prueba (prueba real v2, 2026-11-25); por política
  de la empresa no se tocan tickets reales de producción. Las pruebas de cada versión van contra el mock.
- **Comportamiento en ejecución de Bonita:** rechazo de un segundo caso del mismo ticket.
## Puntos que la reunión no resuelve

Son elecciones de diseño de esta documentación; están aplicadas y pueden cambiarse.

1. **Empate de carga**: si las consultoras tienen la misma carga ponderada, gana la primera empatada después de la
   última asignada, recorriendo `param_consultores` en círculo (`bpmn.md` › Regla de `conn_hubspotCarga`, punto 4).
2. **Cómo llegan los artefactos a HubSpot**: los carga la consultora en el formulario «Diseñar la propuesta» de
   Bonita (`20_disenarPropuesta`) y Bonita los escribe en el Negocio al enviar (`concepto_viabilidad`,
   `valoracion_operaciones`, `url_ppta_preventa`, `link_repo_preventa`), con la nota de la propuesta y los adjuntos
   (`21_subirAdjuntos`). Nadie los edita en HubSpot y no hay que esperar ni detectar cambios en el Negocio.
3. **Solicitudes que no siguen**: las decide la consultora en «Validar la solicitud». «No viable» cierra el ticket
   («Closed», cerrado por viabilidad) y escribe «No Viable (Rechazado)»; «bloqueado» lo deja «En espera información del
   lead» con «Requiere más información» y la validación vuelve a la misma consultora. Un ticket que el comercial cierra
   en HubSpot con el caso abierto no se detecta (lo detectaría la reconciliación).
4. **Prioridad y ANS del ticket**: la prioridad pondera la carga del reparto (URGENT 4, HIGH 3, MEDIUM 2, LOW 1, sin
   prioridad 2). Los ANS no intervienen: HubSpot los vigila y las tareas de Bonita no llevan temporizador.
5. **Middleware**: está en este repositorio (`middleware/`, Rust, imagen Docker) y solo instancia el caso al recibir
   `ticket.creation`; no escribe en HubSpot. Falta desplegarlo con HTTPS público y registrar el webhook de la app;
   sin él la automatización no arranca en producción.
6. **Lista de consultoras** como parámetro de proceso (`param_consultores`): en Community cambiarla exige
   volver a desplegar.
7. **Job de reconciliación diaria**: dónde vive.
8. **Sin temporizadores en el caso**: el caso avanza cuando la consultora envía cada formulario; si una tarea queda sin
   atender, el caso sigue abierto y el aviso lo da el ANS del ticket en HubSpot. Un fallo de un conector deja la tarea
   en fallo, a reintentar desde la administración de Bonita (reintentar puede duplicar notas o adjuntos).
