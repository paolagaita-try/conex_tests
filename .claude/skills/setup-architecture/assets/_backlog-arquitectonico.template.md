# Backlog Arquitectónico (ADD — Paso 7)

> Tablero de seguimiento del método ADD. Rastrea qué drivers/ASRs
> ([0000-drivers-y-asrs.md](0000-drivers-y-asrs.md)) han sido abordados por una decisión, cuáles están en
> progreso y cuáles pendientes. Equivale al Kanban arquitectónico que recomienda Len Bass para no perder
> de vista la cobertura entre iteraciones.
>
> **Este archivo es el estado de la capa de arquitectura.** Lo escribe la skill `setup-architecture`
> (`/build:architect`) y lo consumen los gates del arnés: el **DoR** verifica que los drivers
> arquitectónicamente significativos de una épica tengan un ADR con estado ≥ `ABORDADO` antes de abrir el
> slice; el gate **`stack_arch`** del Release Gate audita conformidad contra los ADRs referenciados aquí.

**Convención de estado:**
- `PENDIENTE` — driver sin decisión asociada.
- `EN DISEÑO` — iteración en curso.
- `ABORDADO` — existe ADR que lo cubre con análisis (Paso 7) registrado.
- `VERIFICADO` — el análisis confirma que la decisión satisface la medida de respuesta (idealmente
  revisado por un par).

## Tablero por driver

> La columna **Trazabilidad** (EP/HU/§PRD de los que sale el driver, heredada del `0000`) es la que usa
> el DoR para el join épica↔driver: dado un `EP-XXX`, sus drivers son las filas cuya trazabilidad cita
> esa épica o alguna de sus HU.

| Driver | Tipo | Prioridad | Trazabilidad (EP/HU) | Iteración | ADR | Estado |
|--------|------|-----------|----------------------|-----------|-----|--------|
| UC-1 … | Funcional | (A,A) | EP-…, HU-… | 1 | 000N | PENDIENTE |
| QA-1 … | QA | (A,M) | HU-…, §PRD | 1 | 000N | PENDIENTE |
| CON-1 … | Restricción | — | §PRD | 1 | 000N | PENDIENTE |
| CRN-1 … | Concern | — | — | 1 | 000N | PENDIENTE |

## Riesgos arquitectónicos abiertos

> Salida del análisis ATAM-lite (Paso 6/7): puntos de sensibilidad, trade-offs y riesgos sin mitigar.
> Cada riesgo traza a su driver y a la mitigación planificada. Marcar ✅ CERRADO al resolver (no borrar:
> deja el rastro).

| Riesgo | Driver | Mitigación planificada | Iteración |
|--------|--------|------------------------|-----------|
| … | QA-… | … | … |

## Bitácora de iteraciones

> Una fila por ronda ADD. `Objetivo` = Paso 2; `Resultado` = Paso 7 (qué ADR se creó/refactorizó y qué
> quedó sin resolver). La fila de **Cierre** registra la promoción `proposed → accepted` tras la revisión
> humana.

| Iteración | Fecha | Objetivo (Paso 2) | Resultado (Paso 7) |
|-----------|-------|-------------------|--------------------|
| 1 | YYYY-MM-DD | … | … |
