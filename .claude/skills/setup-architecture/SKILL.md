---
name: setup-architecture
description: Use BEFORE building — after discovery (PRD + user story map + epicas + HUs exist) and before the first slice — to produce the project's architecture layer as ADRs using the ADD method (Attribute-Driven Design, Len Bass). Reads docs/ read-only, extracts architectural drivers/ASRs, drives ADD iterations (tactics → styles → views → ATAM-lite analysis), writes docs/adr/ (0000 drivers catalog + numbered ADRs + architectural backlog) and populates .claude/config/stack-allowlist.json. Runs autonomously and proposes maximally — stops for a single human review and only escalates genuine business trade-offs. The ADRs become build criteria: the DoR gate requires driver coverage and the release-gate stack_arch audits conformance. Delegates driver extraction to asr-extractor and evaluation to architecture-evaluator; never publishes, only proposes.
---

# Definir la arquitectura (método ADD) — capa previa a construcción

Genera la **capa de arquitectura** del proyecto **antes** de que empiece el inner loop de
`building-a-slice`. Su objetivo es que el agente entre a construir con las decisiones técnicas ya
claras (estilo, tácticas, stack), y que esas decisiones se vuelvan **criterios exigibles** por los gates
del arnés. Sigue el método **ADD** (Attribute-Driven Design, Len Bass — *Software Architecture in
Practice*), cuyos pasos son los 8 del diseño arquitectónico:

```
Negocio → ASRs → Tácticas → Estilos → Vistas → Evaluación (ATAM) → Stack → Código
```

> **Dónde encaja.** Corre **después de discovery** (`@trycore/spec-product-flow` dejó listos PRD, user
> story map, `docs/03-backlog/epicas.md` y `docs/04-historias/HU-*.md`) y **antes** del primer slice. No
> reemplaza al Release Gate: lo **habilita**. El gate `stack_arch` sigue auditando en el outer loop, pero
> ahora contra los ADRs que esta capa produce.

## Principio de operación

- **Entrada de solo lectura: `docs/`** (PRD, story map, épicas, HUs). Esta skill **NO escribe** en los
  artefactos de discovery (`docs/01-prd/`…`docs/04-historias/`). Su **única** salida en `docs/` es el
  subárbol **`docs/adr/`** (propiedad de construcción; carve-out declarado en `METODOLOGIA.md`).
- **Propone, no publica.** Genera los `.md` con estado `proposed` / `living-document`. La promoción a
  `accepted` la hace un humano en la revisión única (fase 5). Forward-compat v0.9: los tipos viven en
  `asset-types.json`; con el runtime disponible, la instancia se **propone** por la superficie de
  agente: `bash .claude/hooks/build/slice-ops.sh propose-asset --type-key <k> --path <p> --content-file <f>`
  (la publica un ADMIN; un agente jamás publica contexto).
- **Autónoma y de propuesta máxima.** La IA rellena todo el catálogo y todos los ADRs de una pasada;
  **no** pregunta campo por campo. Solo se detiene ante **trade-offs de negocio** genuinos (ver fase 5).
- **Delega la exploración pesada en subagentes** (`asr-extractor`, `architecture-evaluator`): devuelven
  síntesis condensada y protegen el presupuesto de atención de la sesión principal.
- **Divulgación progresiva:** carga el `references/<tema>.md` solo cuando la fase lo necesita.
- **El estado es el archivo.** `docs/adr/_backlog-arquitectonico.md` es el estado auto-descriptivo de la
  capa (no transiciona el estado del slice). Re-correr = **incremental**: añade iteraciones, no regenera.

## Fases (carga la referencia indicada en cada paso)

| Fase | Acción | Delega en | Salida | Referencia |
|---|---|---|---|---|
| 0 · preflight | Verifica discovery listo (PRD + `epicas.md` + ≥1 HU). Si falta → **STOP**, remite a `/trycore:*`. Solo lectura. | — | — | — |
| 1 · drivers | Extrae el catálogo de drivers/ASRs (OE, UC significativos, escenarios QA de 6 partes, CON, CRN, matriz de prioridad, plan de iteraciones) | `asr-extractor` (fan-out sobre `docs/`) | `docs/adr/0000-drivers-y-asrs.md` | `drivers-extraction.md` |
| 2 · iterar ADD | Por ronda (una por fase PRD / línea de release): selecciona drivers → elige **tácticas y estilos** → instancia responsabilidades/interfaces → boceta **vistas** (mermaid) | sesión principal + `references/add-method.md` | `docs/adr/000N-*.md` (plantilla 7 secciones) | `add-method.md` |
| 3 · evaluar (ATAM) | Análisis adversarial de cada ADR: puntos de sensibilidad, trade-offs, riesgos, drivers no cubiertos | `architecture-evaluator` | actualiza §5 del ADR + riesgos del backlog | `atam-lite.md` |
| 4 · backlog | Actualiza el tablero de cobertura driver↔ADR, riesgos abiertos y bitácora de iteraciones | sesión principal | `docs/adr/_backlog-arquitectonico.md` | `atam-lite.md` |
| 5 · revisión | Presenta el set completo; escala **solo** trade-offs de negocio (una `AskUserQuestion` batcheada); al aceptar promueve `proposed → accepted` y consolida el stack | usuario (default computado) | `.claude/config/stack-allowlist.json` + estados `accepted` | `add-method.md` |

**Plantillas de salida.** La spec canónica de cada archivo vive en **`assets/` de esta skill** —se
instala con ella en ambos canales—: `assets/0000-drivers-y-asrs.template.md`, `assets/adr-add.template.md`
y `assets/_backlog-arquitectonico.template.md` (única fuente de verdad de la estructura; declarada para el
runtime v0.9 vía `asset-types.json`). La skill **lee la plantilla y escribe** en `docs/adr/`; crea el
directorio si no existe. **No pises** ADRs ya `accepted` (re-corrida incremental).

## Fase 5 · Revisión única (mínimo HITL)

Al terminar de generar 0000 + los ADRs + el backlog:

1. **Resumen** de una pantalla: nº de drivers por tipo, nº de ADRs, estilo(s) elegidos, stack propuesto,
   y **riesgos abiertos** del backlog.
2. **Escala solo lo que es decisión de negocio**, no de arquitectura, con **una sola** `AskUserQuestion`
   que agrupe todos los trade-offs pendientes (p.ej.: "¿el historial de versiones es visible para
   consumidores o solo auditores?", "¿se fijan objetivos de DR (RTO/RPO) ahora o se aplazan?"). Todo lo
   demás la IA ya lo decidió y lo dejó registrado con su rationale. Sin TTY/headless: **no bloquees**;
   deja los trade-offs como riesgos abiertos en el backlog y emítelos por stdout.
3. Al aceptar: promueve los ADRs de decisión `proposed → accepted`, añade la fila **Cierre** a la
   bitácora, y **consolida el stack** → actualiza `.claude/config/stack-allowlist.json` con **merge
   aditivo, nunca overwrite**: añade a `allow` las deps decididas y a `rationale` la referencia al ADR
   que las justifica (p.ej. `"fastapi": "ADR-0001"`); **preserva `source`** (ese campo es el contrato
   del arnés: la ruta a la sección técnica del PRD del consumidor — NO lo pises) y no borra entradas
   que el consumidor haya puesto a mano. Desde aquí, `stack-guard.sh` ya hace cumplir la lista.

## Cómo alimenta al build (los ADRs son criterios)

- **`stack-allowlist.json`** — lo puebla esta capa; el hook `stack-guard.sh` (PreToolUse) bloquea deps
  fuera de lista en tiempo real.
- **DoR** — `dor-dod-gatekeeper` exige que los drivers arquitectónicamente significativos de la épica
  (sobre todo `layer: foundational`) tengan un ADR con estado ≥ `ABORDADO` en el backlog (ver
  `building-a-slice/references/dor.md`).
- **`stack_arch`** (Release Gate) — `stack-guardian` audita el diff acumulado contra las decisiones de
  `docs/adr/`, no solo contra la allowlist.

## Guardrails

- **Solo lectura sobre discovery.** Nunca edites `docs/01-prd/`…`docs/04-historias/`. La única escritura
  en `docs/` es `docs/adr/`.
- **Propón, no publiques.** Estados `proposed`/`living-document`; la promoción a `accepted` es del humano.
- **Ante la duda técnica, decide y registra** (con alternativas descartadas y rationale). **Ante la duda
  de negocio, escala** en la revisión única. No confundas una con otra.
- **Incremental en re-corridas.** No regeneres ADRs ya `accepted`; añade una iteración nueva a la bitácora.
- **Agnóstico.** El vocabulario ADD (drivers, tácticas, estilos, vistas) es genérico del arnés; el
  dominio entra **por `docs/`**, nunca hardcodeado en la skill.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
