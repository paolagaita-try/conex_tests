# Auditoría de las capas 0–3 — Gestión de Preventa (2026-11-12 y 2026-11-13)

Auditoría adversarial e independiente de `docs/07-bonita/` (`bdm.md`, `bpmn.md`, `contratos.md`,
`matriz-formularios.md`), `docs/00-parametros/catalogo-parametros.md` y `handoff.md`. La hizo un subagente con contexto
virgen, distinto del autor de los documentos, sin permiso de escritura sobre el repositorio. Dos pasadas (el máximo).

## Resultado

| Capa | Documento | Pasada 1 (2026-11-12) | Pasada 2 (2026-11-13) |
|---|---|---|---|
| 0 | `bdm.md` | NO PASA | PASA |
| 1 | `bpmn.md` | NO PASA | PASA |
| 2 | `contratos.md` | NO PASA | PASA |
| 3 | `matriz-formularios.md` | PASA | PASA |

## Pasada 1 — hallazgos y su corrección

| # | Severidad | Hallazgo | Corrección aplicada |
|---|---|---|---|
| B1 | bloqueante | La business variable `turno` nunca se cargaba; la operación fallaba con `turno` nulo | Se eliminó `TurnoAsignacion`; el último asignado se lee con `Preventa.findAsignadasRecientes` |
| B2 | bloqueante | El catálogo `ConsultorPreventa` era inalcanzable desde los scripts (el generador solo declara el DAO de objetos con business variable) | Se eliminó; la lista es el parámetro `param_consultores` |
| M3 | mayor | `handoff.md` con títulos numerados: el lector no encontraba «Estado de los gates» | Títulos sin número |
| M4 | mayor | Regla de asignación incompleta y repartida en tres scripts dependientes | Regla cerrada de 4 puntos dentro del conector `conn_hubspotCarga`; salida `ownerElegido` |
| M5 | mayor | Nada cargaba los catálogos | Ya no hay catálogos |
| M6 | mayor | «Sin consultoras» sin especificar | Punto 1 de la regla: el conector falla con mensaje |
| M7 | mayor | Idempotencia por `ticketId` afirmada como hecho | Marcada `[no verificado]` |
| M8 | mayor | La espera sin temporizador ni decisión explícita | Decisión documentada bajo Eventos |
| m9–m14 | menor | Atributos sin uso, ruta «verificada», fuente de `A18`, lista de artefactos, `ownerId` vacío, concurrencia | Corregidos |

## Pasada 2 — observaciones menores y su corrección

| # | Observación | Corrección aplicada |
|---|---|---|
| N1 | «Más reciente» sin decir por qué campo | `persistenceId` descendente, declarado |
| N2 | El conector no recibía el pipeline | `param_pipelineTickets` y entrada `pipelineId` |
| N3 | Idempotencia aún como hecho en tres sitios | Redactada como esperada, `[no verificado]` |
| N4 | «Los detecta la reconciliación» en presente | Condicional; añadido a los puntos sin resolver del handoff |
| N5 | Cómo localiza el middleware la tarea de espera | El middleware guarda la relación ticket → caso (documentado) |
| N6 | Aviso que llega antes de la tarea de espera | Requisito de reintento del middleware, en Pendientes |
| N7 | Un consultor vacío dejaría el ticket sin propietario y sin error | En `6_actualizarTicket` el propietario es obligatorio |
| N8 | `param_consultores` mal formado | La tarea falla con mensaje |
| N9 | `CLAUDE.md` y `base-scaffold.md` siguen hablando de round robin; nota obsoleta en `.flow-state.json` | Nota de `.flow-state.json` actualizada; `CLAUDE.md` y `base-scaffold.md` **pendientes** (fuera de estos documentos) |

## Qué se ejecutó

- `construir_spec` sobre el repositorio: solo errores de trabajo de construcción pendiente (Groovy, consultas, caminos,
  definiciones de conectores) y, antes del cierre, los gates en `pendiente`.
- `leer_matriz`: 0 errores, 3 formularios `No form`.
- Simulación en una copia fuera del repositorio, con borradores de expresiones, consultas, caminos y conectores:
  `construir_spec` da 0 errores y `generar` escribe el `.proc` (6 tareas, 1 compuerta, 2 fines, 4 invocaciones de
  conector), el `bom.xml`, el `.conf` Local, la organización y la colección del journey. `preventaDAO` queda declarado
  y `param_consultores` es legible desde una entrada de conector y desde un script.

## Qué NO se verificó

- Nada en un runtime de Bonita (`mvn clean install`, journey): que la consulta compile, que la restricción única
  rechace un segundo caso y que el usuario técnico complete por API la tarea de espera.
- La escritura `PATCH` en HubSpot real y el evento que avisa de la carga de artefactos.
- La extracción de la reunión contra la transcripción original (el auditor solo tuvo la extracción).
- Las correcciones de las observaciones N1–N8 no pasaron por una tercera auditoría (el presupuesto es de dos pasadas);
  se comprobaron con `construir_spec`.
