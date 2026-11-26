# Base del scaffold — Integración HubSpot ↔ Bonita

> **Qué es esto:** notas de construcción (capa `08-construccion`) para armar la **base** del proyecto Bonita
> `hubspot-bonita`. Fuente del encargo: `HANDOFF-SCAFFOLD.md` (raíz del repo).
> **No** sustituye a `docs/07-bonita/` (diseño aprobado del proceso, hoy `GestionPreventa` 1.4), que manda sobre lo
> que aquí se dice. El modelo vigente es la v2 «Bonita-first» (`plan-v2-bonita-first.md`).

## 1. Qué construye la base y qué espera

| Pieza | Unidad | ¿Se puede ya? | Depende de |
|---|---|---|---|
| Plantilla configurada (versión/edición, módulo de parámetros, frontend, proceso `hola`, runtime, build) | **U0** | Sí, no depende del flujo de preventa | **token de registro del hub** (ver §4) |
| BDM, organización, procesos, reparto por carga, conectores REST de salida | **U1** | **No** — espera `docs/07-bonita/` en `listo-para-construccion` | flujo de preventa (llega pronto) |

El BDM y los procesos **no se inventan** (`HANDOFF-SCAFFOLD.md` §8): se modelan cuando llegue el flujo de preventa.

## 2. Arquitectura acordada (de `HANDOFF-SCAFFOLD.md` §3)

- **Entrada (ticket→caso):** middleware que escucha `ticket.creation` y llama a Bonita
  `POST /bonita/API/bpm/process/{processId}/instantiation`. **Idempotencia por `ticketId`**.
- **Reparto:** service task con el conector `hubspot-consultores-menor-carga`: carga ponderada por prioridad de cada
  consultora en «En validación» y «Asignado/En diseño»; empate, en círculo tras la última asignada (se lee del caso más
  reciente, sin contador). Sin bloqueo transaccional. Regla completa en `docs/07-bonita/bpmn.md`.
- **Salida:** conectores REST propios de Bonita en las tareas que cambian el stage del ticket
  (`PATCH /crm/v3/objects/tickets/{id}`) o escriben en el Negocio (propiedades, notas, adjuntos).
- **Dirección:** solo Bonita→HubSpot (salvo el disparo inicial), para evitar bucles en rutas de retorno.
- **Reconciliación:** job diario Bonita vs HubSpot para huérfanos/desincronizados.
- ❌ No se usa el conector oficial Bonita–HubSpot (Beta, sin tickets). Solo REST nativos.

## 3. Decisión abierta (NO la decide el agente)

Componente de **entrada** según el plan de HubSpot (`HANDOFF-SCAFFOLD.md` §2):

- **Operations Hub Professional:** middleware dentro de HubSpot (custom code action + webhook nativo). Sin servidor externo.
- **Free/Starter (sin costo):** suscripción de webhook de app + middleware externo pequeño.

La base de Bonita es **idéntica** en ambos casos: solo cambia quién dispara la instanciación. Lo decide el líder/Laura.
→ reflejado en el bloque de dominio de `CLAUDE.md` (**Decisiones de alto riesgo**).

## 4. Estado y bloqueos

- ✅ Entorno verificado (`trycore-bonita doctor`: 10 requisitos duros en verde).
- ✅ Placeholders de dominio resueltos en `CLAUDE.md`.
- ✅ **Fase 0** (descubrimiento de IDs de HubSpot) ejecutada → `fase-0-descubrimiento-hubspot.md`.
- ⛔ **U0 bloqueado:** falta el **token de registro del hub** (lo emite el ADMIN, por agente y worktree).
  El token entregado es el de **Private App de HubSpot**, que es distinto y solo sirve para la Fase 0.
  Sin registro, `slice-ops.sh claim U0` rechaza con «no construyas sin claim».
- ⏳ **U1 en espera** del flujo de preventa (`docs/07-bonita/`).

## 5. Índice de la carpeta

- `fase-0-descubrimiento-hubspot.md` — IDs reales de HubSpot (pipeline, stages, owners, propiedades).
- `base-scaffold.md` — este documento.
