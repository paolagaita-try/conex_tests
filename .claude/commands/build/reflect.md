---
name: "BUILD: Reflect"
description: Reflexión post-slice (ciclo autocorrectivo). Tras cerrar/archivar un slice, detecta convenciones aprendidas y errores recurrentes, PROPONE viñetas para el bloque de aprendizajes de CLAUDE.md (se aplican SOLO con tu aprobación) y estampa el slice como reflexionado. Lo dispara el hook reflect-nudge.sh, pero puedes invocarlo cuando quieras.
category: Workflow
tags: [reflexion, conocimiento, ciclo-autocorrectivo, build-harness, trycore]
---

Captura el **conocimiento tribal** de un slice recién cerrado antes de que se pierda. Un hook bash no
puede razonar qué se aprendió; **tú (el modelo) sí**. Tu trabajo: detectar convención nueva o error
recurrente, **proponérselo al usuario**, y —solo con su aprobación— escribirlo al bloque
`trycore-build-learnings` de `CLAUDE.md`. Nunca escribes sin confirmación.

Esta es la mejora del **pilar "ciclo autocorrectivo"**: el hook `reflect-nudge.sh` (evento `Stop`)
solo **sugiere** ejecutar esto cuando hay slices archivados sin reflexionar; el razonamiento vive
aquí, en el modelo.

---

## Preflight

```bash
test -f .claude/.build-harness-version || echo "NOT_INSTALLED"
command -v python3 >/dev/null 2>&1 || echo "NO_PYTHON3"
```

**Si `NOT_INSTALLED`:**

> Este proyecto no tiene el arnés de construcción instalado. Ejecuta primero `trycore-build init`.

Stop aquí si no está instalado o si falta `python3`.

---

## Fase 1: Identificar slices sin reflexionar

El origen del dato depende del **modo** (igual que consume `reflect-nudge.sh`): en `runtime` puro el
fichero local NO se lee — puede faltar o quedar fósil (`runtime-protocol.md`) — y el cómputo lo hace el
servidor sobre **todo el proyecto**; en `legacy`/`dual` el fichero sigue siendo primario.

```bash
MODE="$(bash .claude/hooks/build/slice-ops.sh mode)"
if [ "$MODE" = "runtime" ]; then
  # runtime: NO se lee el fichero legacy (fósil/ausente). El servidor ya agregó el nudge
  # "reflect" sobre todo el proyecto; lo leemos de la línea `nudges:` de `status`, el mismo
  # dato que consume reflect-nudge.sh.
  bash .claude/hooks/build/slice-ops.sh status | python3 - <<'PY'
import json, sys
nudges = []
for line in sys.stdin:
    if line.startswith("nudges:"):
        try:
            nudges = json.loads(line.split(":", 1)[1].strip())
        except Exception:
            nudges = []
        break
pend = [n.get("message") for n in nudges
        if isinstance(n, dict) and n.get("kind") == "reflect" and n.get("message")]
if pend:
    for m in pend:
        print(m)
    print("TOTAL_RUNTIME", len(pend))
else:
    print("TOTAL 0")
PY
else
  # legacy o dual: el fichero es primario en ambos modos (en dual, reconcile-build-state.py
  # lo mantiene sincronizado — runtime-protocol.md); filtra `history[]` con `reflected != true`.
  python3 - <<'PY'
import json, os, sys
p = ".claude/state/build-state.json"  # legacy: ruta local, no runtime
if not os.path.exists(p):
    print("NO_STATE"); sys.exit(0)             # estado ausente → nada que reflexionar, salir
try:
    d = json.load(open(p))
except Exception as e:
    print("CORRUPT_STATE", e); sys.exit(0)      # JSON inválido → reportar y STOP, NO escribir
pend = [h for h in (d.get("history") or []) if isinstance(h, dict) and h.get("reflected") is not True]
for h in pend:
    print(h.get("epica"), "·", h.get("openspec_change"), "·", h.get("branch"), "·", ",".join(h.get("hus") or []))
print("TOTAL", len(pend))
PY
fi
```

**Si `NO_STATE`** (solo aplica en `legacy`/`dual`): no hay estado → nada que reflexionar; termina.
**Si `CORRUPT_STATE`:** el estado está corrupto → repórtalo y **detente sin escribir** (no estampes ni
edites). **Si `TOTAL 0`:** informa "No hay slices pendientes de reflexión ✅" y termina. No inventes
trabajo.

**En `runtime`** el servidor solo entrega el **conteo agregado** (`TOTAL_RUNTIME`), sin `epica`/
`openspec_change`/`branch` por slice (el cliente no puede enumerarlos hoy). Si `TOTAL_RUNTIME > 0`,
dile al humano cuántos hay pendientes según el runtime y **pregúntale con AskUserQuestion** qué slice
(`EP-XXX` + `openspec_change`) reflexionar primero; no adivines ni asumas "el más reciente" sin ese dato.

Si tienes el detalle por slice (`legacy`/`dual`) y hay varios, procésalos **de uno en uno** (el más
reciente primero), o pregunta al usuario cuál.

---

## Fase 2: Recolectar señal del slice

Para el slice elegido, reúne evidencia **real** (no especules):

1. **El change OpenSpec**: `openspec show <openspec_change>` y/o los archivos del change
   (proposal/tasks). ¿Qué se decidió y qué tasks costaron más?
2. **El diff de la rama**: `git log --oneline <branch>` y `git diff main...<branch> --stat` (si la
   rama o sus commits existen). ¿Qué patrón de código se repitió? ¿Qué se reescribió varias veces?
3. **La sesión actual**: qué hooks se dispararon más de una vez (p.ej. `stack-guard.sh`,
   `gitflow-guard.sh`, `lint-typecheck.sh`), qué gates retrocedieron, qué correcciones se repitieron.

Con esa evidencia, detecta **0–3** aprendizajes candidatos, de estas categorías:

- **Convención nueva**: un patrón de código/estructura/nombrado que se repitió y conviene fijar para
  el equipo (ej. "los handlers validan en el borde con el esquema X antes de tocar el dominio").
- **Error recurrente**: algo que un gate o hook atrapó >1 vez y vale la pena prevenir
  (ej. "recordar correr migraciones antes del journey-smoke").
- **Fricción del propio arnés**: si el aprendizaje es sobre el arnés (un gate confuso, un paso que
  sobra), NO lo escribas a CLAUDE.md — anótalo como candidato para `internal/skills/auditar-arnes`
  y dilo al usuario.

Si no hay nada que valga la pena fijar, es válido **no proponer aprendizajes** (solo estampar, Fase 5).

---

## Fase 2-bis: Registrar la telemetría de coste (P12, #86)

Con la evidencia ya reunida, registra el **coste** del slice para que `/build:calculate-graph
--calibrate` pueda estimar el modelo del grafo por proyecto. La medida por defecto es el **nº de
commits** de la épica (el proxy que usó la evidencia de #86; el arnés aún no cuenta tokens):

```bash
bash .claude/hooks/build/slice-ops.sh graph-telemetry --epic <EP-XXX> --auto
# añade --concurrent si el slice se construyó dentro de un front paralelo (convivió con otra rama)
```

HU y tramos se derivan de los docs; el registro es idempotente (reemplaza el previo de la épica) y
va a `docs/.reviews/graph-telemetry.json` (carve-out §9.2, no toca discovery). Con **≥ 5 épicas**
archivadas registradas, corre `/build:calculate-graph --calibrate`.

**Tokens exactos por fase (opt-in, OpenTelemetry).** Si el proyecto tiene OTEL activado y un
collector que vuelca los eventos `api_request` a `docs/.reviews/otel-api-requests.jsonl`, usa la
atribución por fase en vez del proxy de commits (las ventanas de fase las marca `slice-ops.sh
phase` solo):

```bash
PH="$(bash .claude/hooks/build/slice-ops.sh graph-otel-phases --epic <EP-XXX> --format phases-rich)"
bash .claude/hooks/build/slice-ops.sh graph-telemetry --epic <EP-XXX> --phases "$PH"
```

Detalle del montaje OTEL en `/build:calculate-graph` (§5, `--calibrate`).

---

## Fase 3: Proponer (con aprobación explícita)

Por **cada** aprendizaje candidato, usa **AskUserQuestion** para que el usuario lo apruebe, edite o
descarte. Presenta cada uno como una **viñeta concreta y accionable**, lista para CLAUDE.md. Ejemplo
de opciones: "Agregar tal cual" (Recomendado) · "Editar" · "Descartar".

**Reglas:**
- Una viñeta = una convención. Concreta, verificable, en presente imperativo. Nada vago.
- No propongas conocimiento que ya está en el bloque (léelo antes). No dupliques.
- Si un aprendizaje es **personal/cross-proyecto** (no de equipo), ofrécelo para **auto-memory**
  (`type: project`/`user`) en vez de CLAUDE.md — pregunta cuál destino.

---

## Fase 4: Aplicar SOLO lo aprobado al bloque de aprendizajes

Para las viñetas aprobadas, **inserta** (no reemplaces) dentro del bloque marcado de `CLAUDE.md`,
**justo antes** de `<!-- END trycore-build-learnings -->`:

```markdown
- (EP-XXX) <viñeta aprobada>
```

- Prefija cada viñeta con la épica del slice `(EP-XXX)` para trazabilidad.
- **NO toques nada fuera del bloque** `trycore-build-learnings`. En particular, NO modifiques el
  bloque `trycore-build-harness` ni sus `{{placeholders}}` de dominio (eso es de `/build:onboard`).
- Si el bloque `trycore-build-learnings` no existe (instalación vieja), pide correr
  `trycore-build update` antes de continuar.
- Las viñetas son cambio de equipo: se revisan en PR como cualquier otra línea de `CLAUDE.md`.

---

## Fase 5: Estampar el slice como reflexionado

El estampado es una transición de dominio más: la hace el ejecutable, no un `json.dump` a mano.

```bash
MODE="$(bash .claude/hooks/build/slice-ops.sh mode)"
if [ "$MODE" = "legacy" ]; then
  # Modo legacy (v0.8.5): se estampa `reflected`/`reflected_at` en la entrada de history[]
  # del fichero, con escritura atómica y validación contra el schema local. Protocolo en
  # skills/building-a-slice/references/state-protocol.md.
  echo "legacy: estampa reflected=true en la entrada de history[] del fichero"
else
  bash .claude/hooks/build/slice-ops.sh progress \
    "reflexión completada de <EP-XXX> (<openspec_change>): <N> aprendizajes aplicados"
  bash .claude/hooks/build/slice-ops.sh fact harness-phase building >/dev/null 2>&1 || true
fi
```

En `dual`/`runtime` el hecho «este slice ya se reflexionó» vive en el event stream del runtime:
el nudge de `reflect-nudge.sh` lo computa el servidor sobre **todo** el proyecto, no sobre este
clon (por eso el nudge dejó de mentir con 31/33 slices sin estampar).

---

## Fase 6: Confirmación

```
## ✓ Reflexión completada

Slice:        <EP-XXX> (<openspec_change>)
Aprendizajes: <N agregados a CLAUDE.md> · <M a auto-memory> · <0 si solo se estampó>
Estampado:    reportado al runtime (o reflected=true en modo legacy)

Pendientes de reflexión restantes: <K>
```

Si quedan slices pendientes (`K > 0`), ofrece continuar con el siguiente.

---

## Guardrails

- **Aprobación explícita siempre.** Nunca escribes a CLAUDE.md sin que el usuario apruebe cada
  viñeta. Espeja la regla del scaffold: el arnés propone, el humano confirma.
- **Evidencia, no invención.** Cada aprendizaje sale del change/diff/sesión reales. Si no hay
  evidencia, no propongas.
- **No reescribas.** Inserta viñetas; jamás borres ni reemplaces aprendizajes previos del equipo.
- **No toques el paquete.** No modifiques agentes/skills/hooks del arnés (eso es mantenimiento, ver
  `internal/skills/auditar-arnes`).
- **Estampa siempre** al terminar, para no re-molestar con el mismo slice.
- La pantalla de la Fase 6 es un formato de pantalla específico de este comando (confirmación de
  reflexión), no contradice `### Cómo reportar` del CLAUDE.md y queda subordinada a él.
- Si algo aquí contradice `METODOLOGIA.md`, **gana la metodología**.
