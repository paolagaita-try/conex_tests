---
name: "BONITA: Onboard"
description: Prepara un proyecto con el arnés Bonita instalado — comprueba el gate de entrada del arnés de documentación (docs/.flow-state.json y handoff.md), resuelve los placeholders de dominio del bloque de CLAUDE.md, propone el plan de unidades (docs/08-construccion/plan.md, solo con aprobación humana), genera el bundle del grafo con trycore-bonita grafo y entrega al ADMIN la lista de pasos en el hub. Si la documentación y el generador no coinciden, para y lista lo que falta.
category: Workflow
tags: [bonita, onboarding, plan, grafo, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/onboard.md (reescrito para Bonita: gate de entrada, plan de unidades y grafo) -->

Deja el proyecto listo para `/bonita:unidad`. El CLI (`trycore-bonita init`) ya instaló agentes, comandos, skills,
hooks y el bloque de `CLAUDE.md` con `{{placeholders}}`. Aquí se **lee** la documentación, se **propone** y se
**confirma** con una persona; no se escribe nada de `docs/07-bonita/`. Si algo aquí contradice el bloque del arnés en
`CLAUDE.md`, gana `CLAUDE.md`.

## Fase 0: preflight

```bash
test -f .claude/.bonita-harness.json || echo "NOT_INSTALLED"
trycore-bonita doctor
```

`NOT_INSTALLED` → `trycore-bonita init` y vuelve. `doctor` en 1 → arregla lo que diga o para y pregunta. Sus
«Avisos» listan los placeholders sin resolver de `CLAUDE.md` (esta es la tarea) y «Runtime (hub)» dice si hay
credenciales.

## Fase 1: gate de entrada (si no pasa, PARA)

Lee, sin modificar, `docs/.flow-state.json` y `docs/07-bonita/handoff.md`:

| Qué se comprueba | Valor exigido |
|---|---|
| `gates.bonita.entrada` | `pasa` |
| `gates.bonita.capa-0`, `capa-1`, `capa-2`, `capa-3` | `pasa` las cuatro |
| `docs/07-bonita/handoff.md`, campo `estado` | `listo-para-construccion` |

Si algún valor falta, no es `pasa` o está `reabierto`: **para**. Lista qué gate o campo falla y dónde, y di que la
documentación vuelve al arnés de documentación (cerrar la capa con su gate); construir encima es la forma en que
vuelve el retrabajo. No hay override.

## Fase 2: la documentación y el generador deben coincidir (si no, PARA)

El lector del generador exige cosas que las plantillas del arnés de documentación (v0.8.0) aún no traen. Comprueba
que `docs/07-bonita/` las tiene, **leyendo** los ficheros, y consulta las skills de componente para el formato exacto:

| Falta en la documentación | Dónde se explica | Salida del generador |
|---|---|---|
| Subsección «`Pool` versión» **por pool** en «Contrato de instanciación» de `contratos.md` (también con un solo pool) | `bonita-construir-contratos-y-operaciones` | `generar` sale 2 nombrando la sección |
| Línea **Iniciador** por pool (y las demás secciones marcadas **[+]** de `bpmn.md`) | `bonita-construir-proceso` | `generar` sale 2 nombrando la sección |
| Línea **Contraseña de prueba** en `bdm.md` § «Organización» | `bonita-construir-organizacion` | «falta **Contraseña de prueba**» |
| Tabla de **valores por entorno** de los `param_*` en `bdm.md` § «Parámetros» | `bonita-construir-parametros-y-entornos` | «falta la tabla de valores por entorno» |
| Conector escrito «`conn_x` (REST GET)» y modo «síncrono» en «Conectores por tarea» | `bonita-construir-conectores` | tipo de conector o modo no soportado |

**No adivines ni rellenes tú.** Si algo falta: **para y lista** qué falta, en qué fichero y sección y qué skill
describe el formato. Añadirlo es editar `docs/07-bonita/` (la fuente aprobada): lo decide una persona y se registra
como hueco del arnés en `docs/08-construccion/huecos-del-arnes.md`
(`skills/bonita-construir-unidad/references/huecos-del-arnes.md`). Un elemento que el generador no soporta de verdad
se trata igual: hueco, no se rodea.

## Fase 3: placeholders de dominio

Propón valores derivados de `docs/` (PRD en `docs/01-prd/`, `docs/07-bonita/handoff.md`, `bdm.md`,
`docs/02-flujo-proceso/catalogo-conectores.md`) y confírmalos con una pregunta por punto (tu propuesta, primera,
«(Recomendado)»):

| Placeholder | Qué es |
|---|---|
| `{{PROCESO}}` | el proceso que se construye: nombre y una línea de qué hace |
| `{{SISTEMAS_EXTERNOS}}` | los sistemas con los que se integra (conectores) o «no aplica» |
| `{{DATOS_SENSIBLES}}` | categorías reguladas o personales del dominio |
| `{{DECISIONES_DE_ALTO_RIESGO}}` | decisiones que exigen explicabilidad o aprobación |

Si un punto no aplica, escribe «no aplica»: no lo dejes entre llaves. Edita **solo** dentro del bloque marcado
`trycore-bonita-harness` de `CLAUDE.md`, y solo esas cuatro líneas. Confirma con `trycore-bonita doctor` que «Avisos»
ya no lista marcadores.

## Fase 4: plan de unidades (se escribe SOLO con aprobación)

Formato exacto y reglas: `skills/bonita-construir-unidad/references/plan-de-unidades.md`. Propón la tabla a partir de
`handoff.md`, `matriz-formularios.md` y, si existe, el backlog de `docs/03-backlog/`. En v1:

- `U0` «Plantilla configurada» (la plantilla y el arnés instalado; sin organización).
- `U1` «Datos, organización y procesos» (todo lo que escribe `generar`, subprocesos incluidos; depende de `U0`).
- `U2` y `S-<subproceso>` **reservadas**: no las propongas (no hay generación por alcance todavía).
- `U3`, `U4`, `E-<familia>` y `SUB`, solo si la documentación lo pide, con `U1` entre sus dependencias.

Muestra la tabla y pregunta: **aprobar tal cual**, **editar** o **descartar**. Solo con la aprobación, escribe
`docs/08-construccion/plan.md`. Sin aprobación no se escribe nada.

## Fase 5: el bundle del grafo y el hub

```bash
trycore-bonita grafo --salida grafo.json
```

Salida `1` → el plan no cumple las reglas (un motivo por línea): corrígelo con la persona y repite. `2` → no hay plan
legible. Con el bundle, **entrega al ADMIN del hub** esta lista (el agente no importa nada ni crea proyectos):

1. Crear el proyecto en el hub con `gitflow_policy: github-flow` y `cycle_budget: 2`.
2. Importar `grafo.json` (consola del proyecto).
3. Emitir **un token por agente** (cada worktree se registra por separado con su token: `slice-ops.sh register`,
   token por stdin o `TRYCORE_REGISTER_TOKEN`, nunca por argv).

## Fase 6: comprobar que el grafo está

Cuando el ADMIN avise y este árbol esté registrado:

```bash
bash .claude/hooks/bonita/slice-ops.sh status
```

La línea `grafo:` y las unidades deben aparecer. Si no, el grafo aún no está importado: dilo y para. Con todo en
orden, el siguiente paso es `/bonita:unidad` (o `/bonita:work`).

## Guardrails

- **El gate de entrada y la coincidencia documentación-generador no tienen override.**
- **No escribes `docs/07-bonita/`** ni inventas lo que falta: paras y listas.
- **`plan.md` solo con aprobación humana**; el estado del plan lo manda el hub, no la columna Estado.
- **El ADMIN gobierna el hub**: crear el proyecto, importar el grafo y emitir tokens no son del agente.
