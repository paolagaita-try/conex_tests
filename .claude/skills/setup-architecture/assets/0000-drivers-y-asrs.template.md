---
id: 0000
title: "Catálogo de Drivers Arquitectónicos y ASRs (entrada del método ADD)"
date: YYYY-MM-DD
status: living-document
authors:
  - <Equipo Arquitectura>
tags:
  - add
  - drivers
  - asr
  - quality-attributes
---

# ADR 0000 — Drivers Arquitectónicos y ASRs

> **Naturaleza:** No es un ADR de decisión, sino la **entrada de diseño** (Paso 1 del método ADD de Len
> Bass). Consolida propósito, requisitos funcionales primarios, escenarios de atributos de calidad
> priorizados, restricciones y concerns. Toda decisión en un ADR (0001+) debe trazar a uno o más drivers
> de este catálogo, y todo driver debe estar cubierto por al menos un ADR (ver
> [_backlog-arquitectonico.md](_backlog-arquitectonico.md)).
>
> **Cómo se genera:** la skill `setup-architecture` (`/build:architect`) lo **propone** leyendo `docs/`
> (PRD + user story map + `03-backlog/epicas.md` + `04-historias/HU-*.md`) — de solo lectura. Este es un
> **documento vivo**: cada re-corrida añade drivers nuevos que surjan de HUs/épicas nuevas.

## Cómo se usa este documento en ADD

ADD diseña por **rondas e iteraciones** de 7 pasos. Este catálogo alimenta los pasos 1 y 2:

- **Paso 1 — Review Inputs:** todo lo de este documento.
- **Paso 2 — Establish Iteration Goal:** cada iteración selecciona un subconjunto priorizado de estos
  drivers (ver §6 Plan de iteraciones).

## Propósito de diseño

<Greenfield / brownfield; una línea sobre qué es el sistema y su enfoque de diseño (top-down desde el
sistema completo, o refinamiento de elementos internos).>

Fuente: [docs/01-prd/<prd>.md](../01-prd/<prd>.md) §<x>.

## 1. Objetivos de negocio (OE)

| ID | Objetivo | Métrica / Meta |
|----|----------|----------------|
| OE-01 | … | … |

## 2. Requisitos funcionales primarios (UC) — arquitecturalmente significativos

> Solo los casos de uso que **moldean** la arquitectura. No es el backlog completo.

| UC | Descripción | Trazabilidad |
|----|-------------|--------------|
| UC-1 | … | OE-…, HU-… |

## 3. Escenarios de atributos de calidad (QA) — formato de 6 partes

> Formato Bass: **Fuente del estímulo · Estímulo · Artefacto · Entorno · Respuesta · Medida de respuesta.**
> Cada escenario lleva prioridad `(Importancia de negocio, Impacto/Dificultad arquitectónica)` en escala
> {A=Alta, M=Media, B=Baja}. La **medida de respuesta** debe ser cuantificable (es lo que convierte un
> deseo en un ASR verificable).

### QA-1 — <Atributo> · prioridad (A, M)
- **Fuente:** …
- **Estímulo:** …
- **Artefacto:** …
- **Entorno:** …
- **Respuesta:** …
- **Medida:** … (traza a HU/AC/PRD)

## 4. Restricciones (CON)

| ID | Restricción | Origen |
|----|-------------|--------|
| CON-1 | … | … |

## 5. Concerns / preocupaciones del proyecto (CRN)

| ID | Concern | Implicación de diseño |
|----|---------|-----------------------|
| CRN-1 | … | … |

## 6. Plan de iteraciones (rondas ADD ↔ fases del PRD / líneas de release)

> Estrategia: iterar en el orden de las fases del PRD (o las líneas de release del Story Map). Cada
> iteración ejecuta los Pasos 2–7 de ADD sobre el subconjunto de drivers indicado.

| Iteración | Fase PRD / Release | Drivers seleccionados (Paso 2) | Elementos a refinar (Paso 3) | ADRs |
|-----------|--------------------|--------------------------------|------------------------------|------|
| **1** | … | … | … | … |

## 7. Matriz de priorización (Importancia de negocio × Impacto arquitectónico)

| | Impacto arq. ALTO | Impacto arq. MEDIO | Impacto arq. BAJO |
|---|---|---|---|
| **Negocio ALTO** | … | … | — |
| **Negocio MEDIO** | … | … | — |

> Los cuadrantes superiores (alta importancia × alto impacto) son los **ASRs críticos**: se atacan
> primero o se mitiga su riesgo lo antes posible (principio ADD de iterar hasta satisfacer los drivers
> críticos / mitigar el riesgo).
