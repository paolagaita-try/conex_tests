---
id: NNNN
title: "<Título de la decisión>"
date: YYYY-MM-DD
status: proposed   # proposed | accepted | superseded | deprecated
authors:
  - <Equipo / persona>
tags: []
add:
  iteracion: <n>
  fase_prd: "<Fase X>"
---

# ADR NNNN — <Título>

> Plantilla alineada al método **ADD** (Attribute-Driven Design, Len Bass — *Software Architecture in
> Practice*). Cada sección numerada corresponde a un paso del método. Las decisiones deben trazar a
> [0000-drivers-y-asrs.md](0000-drivers-y-asrs.md) y actualizar
> [_backlog-arquitectonico.md](_backlog-arquitectonico.md). Generada por la skill `setup-architecture`
> (`/build:architect`); un humano la promueve `proposed → accepted`.

## 1. Objetivo de la iteración y drivers seleccionados (Pasos 2–3)

- **Objetivo de la iteración:** <qué se busca resolver en esta ronda>.
- **Elemento(s) a refinar:** <sistema completo | servicio X | módulo Y>.
- **Drivers abordados:**
  - Funcionales: UC-…
  - Atributos de calidad: QA-… (con su medida de respuesta)
  - Restricciones: CON-…
  - Concerns: CRN-…

## 2. Conceptos de diseño elegidos (Paso 4)

> Patrones arquitectónicos, **tácticas** (sentido Bass), componentes externos o arquitecturas de
> referencia evaluados y elegidos para satisfacer los drivers. Registra las alternativas descartadas:
> ese es el valor del ADR.

| Driver | Concepto / Táctica | Alternativas descartadas | Razón |
|--------|--------------------|--------------------------|-------|
| QA-… | … | … | … |

## 3. Instanciación: responsabilidades e interfaces (Paso 5)

> Cómo se convierten los conceptos en estructuras reales: componentes/módulos, sus responsabilidades y
> los contratos (interfaces) por los que se comunican.

- **Elementos instanciados:** …
- **Responsabilidades:** …
- **Interfaces / contratos:** …

## 4. Vistas y registro de la decisión (Paso 6)

> Boceto de vista(s) estructural(es) — de módulos, de componentes-y-conectores o de asignación física —
> y el rationale + trade-offs.

```mermaid
%% vista estructural / de despliegue / de secuencia
```

**Decisión:** …

**Trade-offs aceptados:** …

## 5. Análisis del diseño (Paso 7)

> ¿La decisión satisface el objetivo de la iteración? Cada driver con veredicto y evidencia/medida.

| Driver | ¿Satisfecho? | Evidencia / medida | Riesgo residual |
|--------|--------------|--------------------|-----------------|
| QA-… | ✅/⚠️/❌ | … | … |

**Drivers no resueltos en esta iteración:** … (se devuelven al backlog arquitectónico).

## 6. Consecuencias

- Positivas: …
- Negativas / riesgos: …
- Operacionales: …

## 7. Trazabilidad

- Drivers: [0000-drivers-y-asrs.md](0000-drivers-y-asrs.md)
- PRD / HU / Flows: …
- Stack operacionalizado en: `.claude/config/stack-allowlist.json` (si esta ADR decide stack)
