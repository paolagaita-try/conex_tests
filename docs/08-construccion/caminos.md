# Caminos del journey — Gestión de Preventa

Tres caminos por la compuerta `gwXor_1` (v2 «Bonita-first», pool 1.3). El middleware (usuario técnico `ofelia.bot`) instancia el caso; las tareas de servicio (3, 4, 6, 11, 12, 40) y los conectores de salida corren solos contra el **mock** (`mock.json`, puerto 8099). Las tareas humanas las hace la consultora que eligió el reparto (con la carga del mock, `linda.lozano`); el actor filter `filtroConsultoraDelCaso` no se las ofrece a `viviana.velasquez`. Nunca se toca HubSpot real.

## Camino `entregada`

La consultora valida «viable», Bonita pasa el ticket a «Asignado/En diseño», la consultora diseña la propuesta con un adjunto (Bonita lo sube al Negocio) y Bonita lo pasa a «Entregado a ventas».

- **Fin esperado**: `fin_entregada`
- **Salidas cubiertas**: `gwXor_1→11_pasarADiseno`; `gwXor_2→21_subirAdjuntos`

| Paso | Tarea | Usuario | Payload |
|---|---|---|---|
| 1 | (instanciación) | ofelia.bot | `{"ticketId": "T-001"}` |
| 2 | (no ve `10_validarSolicitud`) | viviana.velasquez | — |
| 3 | `10_validarSolicitud` | linda.lozano | `{"resultado": "viable", "conceptoViabilidad": "Aprobado (Viable)", "notaValidacion": "Requerimiento claro; se valida.", "supuestos": "Cliente entrega muestras"}` |
| 4 | `20_disenarPropuesta` | linda.lozano | `{"valoracionOperaciones": "https://example.com/valoracion", "urlPptaPreventa": "https://example.com/ppta", "linkRepoPreventa": "https://example.com/repo", "notaPropuesta": "Propuesta lista", "adjuntos": [{"$archivo": "propuesta.pdf"}]}` |

| Atributo | Valor esperado |
|---|---|
| `preventa.estado` | `entregadaAVentas` |
| `preventa.consultorOwnerId` | `89450376` |
| `preventa.consultor` | `Linda` |
| `preventa.asunto` | `Preventa cliente ACME` |
| `preventa.resultadoValidacion` | `viable` |
| `preventa.urlPptaPreventa` | `https://example.com/ppta` |
| `preventa.conceptoViabilidad` | `Aprobado (Viable)` |
| `preventa.valoracionOperaciones` | `https://example.com/valoracion` |
| `preventa.cantidadAdjuntos` | `1` |

## Camino `bloqueada`

La consultora valida «bloqueado» (falta información del lead): Bonita pasa el ticket a «En espera información del lead» y la validación vuelve a la misma consultora, que la concluye «viable» y sigue hasta la entrega sin adjuntos.

- **Fin esperado**: `fin_entregada`
- **Salidas cubiertas**: `gwXor_1→12_pasarAEnEspera`; `gwXor_1→11_pasarADiseno`; `gwXor_2→40_entregarAVentas`

| Paso | Tarea | Usuario | Payload |
|---|---|---|---|
| 1 | (instanciación) | ofelia.bot | `{"ticketId": "T-003"}` |
| 2 | `10_validarSolicitud` | linda.lozano | `{"resultado": "bloqueado", "conceptoViabilidad": "", "notaValidacion": "Falta el volumen de documentos.", "supuestos": ""}` |
| 3 | `10_validarSolicitud` | linda.lozano | `{"resultado": "viable", "conceptoViabilidad": "Aprobado con Condiciones", "notaValidacion": "El lead completó la información.", "supuestos": ""}` |
| 4 | `20_disenarPropuesta` | linda.lozano | `{"valoracionOperaciones": "https://example.com/valoracion2", "urlPptaPreventa": "https://example.com/ppta2", "linkRepoPreventa": "https://example.com/repo2", "notaPropuesta": "", "adjuntos": []}` |

| Atributo | Valor esperado |
|---|---|
| `preventa.estado` | `entregadaAVentas` |
| `preventa.resultadoValidacion` | `viable` |
| `preventa.notaValidacion` | `El lead completó la información.` |
| `preventa.conceptoViabilidad` | `Aprobado con Condiciones` |

## Camino `noViable`

La consultora valida «no viable»: queda la nota en HubSpot, Bonita escribe el concepto en el Negocio y pasa el ticket a «Closed» (`4`): cerrado por viabilidad (decisión de la usuaria, 2026-11-24); la nota empieza por «Cerrado por viabilidad:».

- **Fin esperado**: `fin_noViable`
- **Salidas cubiertas**: `gwXor_1→13_registrarNoViable`

| Paso | Tarea | Usuario | Payload |
|---|---|---|---|
| 1 | (instanciación) | ofelia.bot | `{"ticketId": "T-002"}` |
| 2 | `10_validarSolicitud` | linda.lozano | `{"resultado": "no_viable", "conceptoViabilidad": "No Viable (Rechazado)", "notaValidacion": "No aplica a DocFly ni Oriuno.", "supuestos": ""}` |

| Atributo | Valor esperado |
|---|---|
| `preventa.estado` | `noViable` |
| `preventa.consultorOwnerId` | `89450376` |
| `preventa.consultor` | `Linda` |
| `preventa.resultadoValidacion` | `no_viable` |
| `preventa.conceptoViabilidad` | `No Viable (Rechazado)` |
