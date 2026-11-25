# Arquitectura de eventos — HubSpot ↔ Bonita (v2 «Bonita-first»)

## Resumen

Desde la v2 (`docs/08-construccion/plan-v2-bonita-first.md`) el equipo de Preventa trabaja **solo en Bonita**. HubSpot
emite **un único evento** hacia el sistema: la creación del ticket, que el middleware convierte en un caso de Bonita.
Todo lo demás avanza **dentro del proceso Bonita** (tareas automáticas y las tareas humanas de la consultora en
formularios), y Bonita escribe en HubSpot con sus conectores REST. No hay temporizadores ni sondeos que muevan el
caso; la única pieza periódica es una reconciliación que solo informa.

## Eventos

```
HubSpot ──ticket.creation──► Middleware ──► Bonita: instancia el caso (idempotente)
Bonita  ──conectores REST──► HubSpot: PATCH del ticket (stage/owner), PATCH del Negocio (propiedades),
                                      notas en ticket y Negocio, carga de adjuntos
```

- **Entrada**: `ticket.creation` → `POST /webhooks/ticket-created` → instanciación. Es la única entrada HubSpot→Bonita.
- **Avance del caso**: lo deciden las tareas humanas en Bonita (`10_validarSolicitud`, `20_disenarPropuesta`); a su
  salida, el mismo caso ejecuta los conectores que escriben en HubSpot. No se escuchan cambios hechos en HubSpot.
- **Cierre por el comercial**: se hace en HubSpot y no genera evento hacia Bonita.

## Piezas basadas en tiempo

| Pieza | Qué hace | Naturaleza | Nota |
|---|---|---|---|
| `reconciliar` (middleware) | Compara casos activos de Bonita con tickets del pipeline (log) | **Barrido periódico** (`RECONCILE_MS`, por defecto diario) | No actúa, solo reporta. |

## Garantías

- **Idempotencia**: la entrada no duplica casos (store `ticketId → caseId`).
- **Blindaje de pipeline**: el middleware solo actúa sobre el pipeline de Preventa; ignora los demás.
- **Una sola dirección de escritura**: el middleware no escribe en HubSpot; escriben los conectores de Bonita.
- **Separación de objetos**: Bonita mueve de stage solo el **ticket**; del **Negocio** escribe propiedades, notas y
  adjuntos, nunca su etapa.
