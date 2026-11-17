# Caminos del journey — Gestión de Preventa

Dos caminos por la compuerta `gwXor_1`. El middleware (usuario técnico `ofelia.bot`) instancia el caso y completa la tarea de espera; las tareas de servicio (3, 4, 6) corren solas contra el **mock** (`mock.json`, puerto 8099). Nunca se toca HubSpot real.

## Camino `entregada`

El ticket se asigna por balance de carga, se pasa a «En validación» y, cuando el negocio carga los artefactos, el middleware informa `entregado` y Bonita pasa el ticket a «Entregado a ventas».

- **Fin esperado**: `fin_entregada`
- **Salidas cubiertas**: `gwXor_1→40_entregarAVentas`

| Paso | Tarea | Usuario | Payload |
|---|---|---|---|
| 1 | (instanciación) | ofelia.bot | `{"ticketId": "T-001"}` |
| 2 | `18_esperarArtefactos` | ofelia.bot | `{"resultado": "entregado"}` |

| Atributo | Valor esperado |
|---|---|
| `preventa.estado` | `entregadaAVentas` |
| `preventa.consultorOwnerId` | `89450376` |
| `preventa.consultor` | `Linda` |
| `preventa.asunto` | `Preventa cliente ACME` |

## Camino `cerrada`

El caso se asigna igual, pero el ticket se cierra sin entregar: el middleware informa `cerrado` y el caso termina sin pasar a «Entregado a ventas».

- **Fin esperado**: `fin_cerrada`
- **Salidas cubiertas**: `gwXor_1→fin_cerrada`

| Paso | Tarea | Usuario | Payload |
|---|---|---|---|
| 1 | (instanciación) | ofelia.bot | `{"ticketId": "T-002"}` |
| 2 | `18_esperarArtefactos` | ofelia.bot | `{"resultado": "cerrado"}` |

| Atributo | Valor esperado |
|---|---|
| `preventa.estado` | `cerrada` |
| `preventa.consultorOwnerId` | `89450376` |
| `preventa.consultor` | `Linda` |
