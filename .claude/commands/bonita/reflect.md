---
name: "BONITA: Reflect"
description: Reflexión tras cerrar una unidad. Detecta convenciones aprendidas y errores recurrentes con evidencia real y PROPONE — solo con aprobación — las generales al arnés (slice-ops.sh propose-asset, o docs/08-construccion/propuestas-al-arnes.md si no hay tipo de asset) y las del dominio al bloque de aprendizajes de CLAUDE.md. Lo sugiere el hook reflect-nudge.sh; puedes invocarlo cuando quieras.
category: Workflow
tags: [bonita, reflexion, conocimiento, ciclo-autocorrectivo, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/reflect.md (adaptado a Bonita y al modo servidor) -->

Captura el **conocimiento tribal** de una unidad recién cerrada antes de que se pierda. Un hook no razona qué se
aprendió; tú sí. Detecta convención nueva o error recurrente, **proponla**, y solo con aprobación escríbela donde
toca. Nunca escribes sin confirmación.

## Preflight

```bash
test -f .claude/.bonita-harness.json || echo "NOT_INSTALLED"
command -v python3 >/dev/null 2>&1 || echo "NO_PYTHON3"
```

`NOT_INSTALLED` → `trycore-bonita init`. Para aquí si falta algo.

## Fase 1: qué unidades quedan sin reflexionar

```bash
bash .claude/hooks/bonita/slice-ops.sh status
```

El hub agrega sobre todo el proyecto el aviso `reflect` en la línea `nudges:` de `status`. Sin aviso: «No hay
unidades pendientes de reflexión» y termina; no inventes trabajo. El hub solo da el conteo: **pregunta** cuál
unidad reflexionar (código y change) en vez de suponer «la más reciente».

## Fase 2: recolectar señal real

Para la unidad elegida: `openspec show <change>` (o los ficheros del change archivado), `git log --oneline` y
`git diff main...<rama> --stat`, y lo ocurrido en la sesión (qué hooks se dispararon más de una vez, qué gates
retrocedieron, qué huecos del arnés se anotaron en `docs/08-construccion/huecos-del-arnes.md`, qué hallazgos dio el
verificador). Detecta **0 a 3** candidatos:

- **Convención general del arnés** (vale para cualquier proyecto Bonita: un patrón del generador, un gate confuso, una
  receta que falló, un hueco que se repite).
- **Convención o error recurrente del dominio de este proyecto** (un nombre, una regla de negocio, una trampa de su
  BDM o de un conector).

Si no hay nada que valga la pena, es válido no proponer nada (solo estampar, Fase 5).

## Fase 3: proponer (aprobación explícita)

Por **cada** candidato, una pregunta para aprobarlo, editarlo o descartarlo, como viñeta concreta y accionable,
en presente imperativo. No propongas lo que ya está en el bloque (léelo antes) y no dupliques. Una viñeta = una
convención.

## Fase 4: aplicar SOLO lo aprobado

- **Del dominio** → inserta (no reemplaces) dentro del bloque marcado de `CLAUDE.md`, justo antes de
  `<!-- END trycore-bonita-learnings -->`, con el prefijo de la unidad:

  ```markdown
  - (U1) <viñeta aprobada>
  ```

  No toques nada fuera de ese bloque, en particular el bloque `trycore-bonita-harness` ni sus `{{…}}`. Si el bloque
  no existe, pide `trycore-bonita update`.
- **General del arnés** (no es de este proyecto): se propone al hub con `slice-ops.sh propose-asset` **si el
  proyecto declara un tipo de asset** (`.claude/asset-types.json`, lista `types`) que la admite:

  ```bash
  bash .claude/hooks/bonita/slice-ops.sh propose-asset --type-key <tipo> --path <ruta> --content-file <fichero>
  ```

  Hoy `types` está vacío, así que en la práctica va a `docs/08-construccion/propuestas-al-arnes.md` (créalo si no
  existe; una sección por propuesta con fecha, unidad, la convención y la evidencia). Ese fichero es lo que el
  equipo lleva al repositorio del arnés; este comando **no** modifica agentes, skills ni hooks instalados.
- **Personal o de varios proyectos** (no de equipo) → ofrécelo para la memoria del asistente en vez de `CLAUDE.md`.

Las viñetas son cambio de equipo: se revisan en PR como cualquier otra línea.

## Fase 5: estampar

```bash
bash .claude/hooks/bonita/slice-ops.sh progress "reflexión completada de <unidad> (<change>): <N> aprendizajes aplicados"
```

El hecho «ya se reflexionó» vive en el flujo de eventos del hub; estampa siempre para no volver a molestar.

## Fase 6: confirmación

```
Reflexión completada
Unidad:        <código> (<change>)
Aprendizajes:  <N al bloque de CLAUDE.md> · <M propuestos al arnés> · <0 si solo se estampó>
Pendientes de reflexión restantes: <K>
```

Con `K > 0`, ofrece continuar. Este formato es específico de este comando y queda subordinado a «Cómo reportar» del
bloque del arnés.

## Guardrails

- **Aprobación explícita siempre**: el arnés propone, la persona confirma.
- **Evidencia, no invención**: cada aprendizaje sale del change, el diff o la sesión reales.
- **No reescribas**: inserta viñetas; jamás borres las del equipo.
