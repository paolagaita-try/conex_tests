# Arquitectura de orquestación por eventos — HubSpot ↔ Bonita

## Resumen

El **núcleo del flujo es dirigido por eventos (event-driven)**: HubSpot emite eventos de webhook y el middleware reacciona instanciando/avanzando casos en Bonita. Hay además dos piezas **basadas en tiempo** (un temporizador de negocio y un detector de seguridad) que se documentan aquí con honestidad.

## Eventos (primario)

```
HubSpot ──ticket.creation──────────────► Middleware ──► Bonita: instancia el caso (idempotente)
HubSpot ──deal.propertyChange (4 fuentes)► Middleware ──► Bonita: completa la espera → «Entregado a ventas»
HubSpot ──ticket.propertyChange (cerrado)► Middleware ──► Bonita: completa la espera → «cerrado»
Bonita  ──conectores REST──────────────► HubSpot: PATCH del ticket (En validación / Entregado)
```

- **Entrada**: `ticket.creation` → `POST /webhooks/ticket-created` → instanciación. 100% evento.
- **Artefactos**: `deal.propertyChange` sobre las 4 fuentes del Negocio → `POST /webhooks/artifacts-loaded` → si las 4 están, completa la espera. 100% evento.
- **Cierre sin entrega**: `ticket.propertyChange` a stage cerrado → `cerrado`. 100% evento.

## Piezas basadas en tiempo (no evento) — y por qué

| Pieza | Qué hace | Naturaleza | Nota |
|---|---|---|---|
| `avanzar_a_diseno` | Tras ~5 min en «En validación», mueve el ticket a «Diseño» | **Temporizador de negocio** | Requisito explícito de Preventa (evitar que quede parado). Es tiempo, no evento, **por diseño**. Puede migrarse a un **evento temporizador dentro del proceso Bonita** si se quiere 100% en el pool. |
| `revisar_artefactos` | Revisa los casos en espera y entrega si las 4 fuentes están | **Polling (red de seguridad)** | El webhook `deal.propertyChange` es el primario e instantáneo; este polling es el respaldo por si se pierde un webhook. |
| `reconciliar` | Compara casos activos vs tickets del pipeline (log) | **Polling diario** | Barrido de consistencia; no actúa, solo reporta. |

## Garantías

- **Idempotencia**: la entrada no duplica casos (store `ticketId → caseId`).
- **Durabilidad**: el reloj del avance a «Diseño» vive en el store (sobrevive a reinicios).
- **Blindaje de pipeline**: solo actúa sobre el pipeline de Preventa; ignora otros (p. ej. «Comercio»).
- **Separación de objetos**: Bonita solo **escribe el ticket**; el **Negocio nunca se mueve**.

## Para que sea 100% event-driven (opcional)

1. Mover el temporizador de 5 min al **proceso Bonita** (evento temporizador de borde entre `6_actualizarTicket` y la espera, con una service task que PATChea a «Diseño»). Elimina el polling `avanzar_a_diseno` del middleware.
2. Confiar solo en `deal.propertyChange` y bajar la frecuencia de `revisar_artefactos` a reconciliación (el polling quedaría como pura red de seguridad).
