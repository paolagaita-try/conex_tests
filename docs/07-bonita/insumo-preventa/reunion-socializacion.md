# Reunión «Socialización proceso preventa (Ofelia + HubSpot)» — extracción

> Fuente: transcripción de la reunión entre Linda Katherine Lozano Rodríguez (consultora del área, dueña del proceso)
> y Angie Paola Gaita Tapiero (construcción), entregada por el usuario el 2026-11-12. Aquí queda lo que la reunión
> decide o aclara, con la marca de tiempo de la transcripción. La transcripción completa no se copia al repositorio.
> Complementa `Proceso_Preventa_Bonita.bpmn` y el manual (`.docx`); **donde difieren, manda la reunión** (es
> posterior y la propia Linda anuncia que va a corregir el documento).

## 1. Qué se automatiza y qué no

| Tema | Lo que se dijo | Minuto |
|---|---|---|
| Alcance de la automatización | «Lo de la automatización serían casi como tres tareas» (Angie); «Sí» (Linda). Es el carril del orquestador. | 38:17 |
| El proceso largo se puede comprimir | «Este proceso está largo porque están todas las actividades descritas muy detalladas, pero… puede comprimir algunas.» | 00:00 |
| Función principal | «La función principal es que esa parte sea automatizada, que sepa asignar las tareas.» | 07:17 |
| Paso de «En validación» a «Asignado/En diseño» | **Manual**, lo hacen las consultoras: «en ese caso sí nos tocaría manual, porque quienes saben somos nosotras». | 10:15 |
| Paso a «Entregado a ventas» | **Automático** al cargar los artefactos: «cuando yo ya cargo estos artefactos, este ticket automáticamente debe pasar a entregado a ventas». | 28:22, 39:22 |
| Cierre del ticket | **Manual**: «nosotros le entregamos a ventas y el comercial lo cierra». | 39:22 |
| Etapas del negocio (lead) | No las toca la automatización: «el negocio no se debe mover de carril»; lo mueve el comercial cuando envía la propuesta. | 29:45, 32:08 |

## 2. Asignación del consultor (no es un round robin puro)

- Solo hay **dos consultoras** que reciben todos los tickets, sean demo, licitación o propuesta: Linda y Viviana (03:45).
- La asignación es por **balance de carga**, no por turno: «es dependiendo como el balance de cargas que tenemos cada
  una» (03:45).
- **Cómo se mide la carga**: los tickets que cada una tiene en los stages **«En validación»** y **«Asignado/En
  diseño»** del pipeline de tickets: «son los carriles que te dicen exactamente qué tiene cada una» (04:49).
  Ejemplo: «Viviana tiene uno; en teoría se le debería asignar a Linda porque no tiene ninguno asignado» (39:22).
- **De dónde sale el ticket a asignar**: del stage **«Solicitud recibida»**, donde cae al crearlo el comercial (08:12).
- **Hoy** lo asigna John a criterio, en el daily (08:12). Eso es lo que se automatiza.
- **Al asignar**: se fija el propietario del ticket y cambia el estado: «una vez se asigna ya cambia el estado porque
  ya se le coloca quién es el propietario» (11:01). El primer estado tras asignar es «En validación»: «lo tomamos
  pero todavía no hemos iniciado» (04:49).
- **Prioridad y ANS**: el ticket tiene prioridad y acuerdos de nivel de servicio configurados en HubSpot (p. ej.
  prioridad alta ≈ 3 días) y HubSpot ya genera las alertas de vencimiento. Linda lo menciona como algo que «no sé si
  hay que tener en cuenta» (06:08): **no se decidió** usarlo en la asignación.
- **No se dijo** qué hacer si las dos tienen la misma carga.

## 3. Ticket, negocio y artefactos

- El comercial crea primero el **negocio** (con el MEDDPICC adjunto, obligatorio) y luego el **ticket**, que «sí o sí
  siempre va amarrado a un negocio». El ticket existe para medir tiempos (01:22, 02:31).
- Al ticket **no se le pueden asociar** los artefactos: se cargan en el **negocio**, en la sección «definición de
  preventa»: si es viable o no, el enlace de la calculadora (estimación), el de la presentación y el del repositorio
  (27:13, 28:22).
- Cargar esos campos del negocio es lo que dispara el paso del **ticket** a «Entregado a ventas» (28:22).

## 4. Lo que queda fuera de Bonita (se hace a mano)

- Análisis del MEDDPICC, demos, licitaciones (el 95 % de las veces la entidad no responde las preguntas y se sigue
  con supuestos, 17:52), levantamientos, viabilidad técnica con el líder técnico, socialización, presentación,
  ajustes, envío de la propuesta, confirmación del cliente y traspaso.
- **Agente IA**: no es un servicio que alguien invoque por API. Es un *skill* («presales») que las dos consultoras
  ejecutan a mano en Claude, sobre una carpeta de insumos, y que genera propuesta, estimación y presentación (23:23,
  24:44). No hay integración que construir.

## 5. Otros datos

- El área ya no se llama «preventa» sino **«Diseño de soluciones»** (36:27).
- Linda va a corregir el manual: en la actividad posterior a cargar los artefactos el documento decía mover el lead a
  «Propuesta enviada» y lo correcto es mover el **ticket** a «Entregado a ventas» (28:22, 29:45, 37:23).
- Owners de HubSpot de las dos consultoras (Fase 0): Linda Katherine Lozano Rodríguez `89450376`; Viviana Paola
  Velásquez Peña `89450377`.

## 6. Cómo responde a las cuatro preguntas abiertas

| Pregunta | Respuesta de la reunión |
|---|---|
| 1. ¿Cómo modelar la espera de respuestas de la licitación? | No se modela: la licitación entera es trabajo manual fuera de Bonita. |
| 2. ¿Qué stage refleja cada momento? | Asignación → «En validación» (automático, con propietario). «Asignado/En diseño» → manual. Artefactos cargados → «Entregado a ventas» (automático). Cierre → manual. |
| 3. ¿Construir sin los datos reales? | El Agente IA no es una integración. La rotación son Linda y Viviana (owners conocidos). Solo falta el token de HubSpot. |
| 4. ¿Tareas humanas consecutivas? | No aplica: en Bonita no quedan tareas de las consultoras. |
