# Protocolo del archivo de estado (`build-state.json`) — **modo `legacy`**

> **Vigencia:** este documento describe el protocolo del **modo `legacy`** (v0.8.5 exacto),
> donde el fichero es la fuente de verdad. En `dual` el fichero sigue siendo primario **y
> además** cada transición se espeja al runtime; en `runtime` el fichero es fósil y **no se
> lee ni se escribe**. Para esos dos modos, el protocolo es
> [`runtime-protocol.md`](runtime-protocol.md). Comprueba el modo con
> `bash .claude/hooks/build/slice-ops.sh mode`.

El estado es **cómo se comunican los agentes** en el modelo secuencial: cada uno lee antes de
actuar y escribe su resultado, dejando el testigo al siguiente. Esquema y reglas base viven en
`.claude/state/README.md` y `.claude/state/build-state.schema.json`; aquí va el uso operativo.

## Lectura
```bash
python3 -c 'import json;print(json.dumps(json.load(open(".claude/state/build-state.json")),indent=2,ensure_ascii=False))'
```
- `active_slice == null` → no hay slice; solo `dor` puede abrir uno.
- Si no es null → identifica el **primer gate en `false`**: ahí se reanuda.

## Refresh de contexto = estado por defecto (handoff en disco)
Cada iteración nace **headless / contexto virgen** y reconstruye el estado **desde disco** (git history +
este `build-state.json` + logs de build), **no** desde la conversación viva: alargar una sesión degrada
el razonamiento (ruido acumulado → deriva). Para retomar sin "creer que ya está":
- **`wiring_checklist[]`** — un item por escenario AC de cada HU y por **punto de integración entre capas**.
  Nace `failing`; pasa a `passing` **SOLO tras prueba real ejecutada** (con `evidence`), nunca por inspección.
  **Mientras quede un item `failing`, el slice NO está cableado** — no cierres `wiring_verified` ni `dod`.
  Cada item puede llevar **`verified_at_sha`** (opcional): sha del commit en que su evidencia fue
  reproducida por última vez; lo estampa el `build-orchestrator` al aplicar un veredicto del
  `wiring-adversarial-verifier` y habilita la re-verificación **incremental** (pasadas 2+ solo
  re-ejecutan items cuyo código cambió desde su sha).
- **`progress_log[]`** — bitácora append-only (`{at, by, note}`) de qué se hizo / qué falta. Deja una nota
  por hito para que la siguiente sesión retome el cableado.
- **`sub_slices[]`** — si la épica superó el gate de tamaño (>3 HU ó ≥3 capas), se trocea aquí; cada
  sub-slice se construye de a uno con su `journey_smoke` verde antes de pasar al siguiente.
`load-build-state.sh` inyecta al arrancar los items `failing` y la última bitácora (JIT, solo lo pendiente).

## Escritura (una transición = una escritura)
Patrón seguro (lee-modifica-escribe) con timestamp UTC:
```bash
python3 - <<'PY'
import json,datetime
p=".claude/state/build-state.json"; d=json.load(open(p))
s=d["active_slice"]
s["gates"]["journey_smoke"]=True  # el gate que cierras (inner loop)
s["phase"]="smoke"               # la nueva fase
s["updated_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
s["updated_by"]="build-orchestrator"  # quién escribe
json.dump(d,open(p,"w"),indent=2,ensure_ascii=False)
PY
```

## Inner loop vs releases[]
- **Inner loop (por slice)**: gates `dor`, `tdd`, `journey_smoke`, `coherence_link`, `data`, `fidelity`,
  `api`, `wiring_verified`, `dod` en `active_slice.gates`. Los escribe el flujo de `building-a-slice` /
  `build-orchestrator`. **`wiring_verified` es prerequisito de `dod`** (lo cierra el verificador
  adversarial independiente, no el mismo agente que construyó).
- **Outer loop (por release)**: los gates pesados (`security`, `smell`, `ux`, `coherence`,
  `stack_arch`, `integration`) **no** viven en el slice — viven en una entrada de `releases[]` que
  escribe la skill `releasing-a-version`. Una release = una línea de release del Story Map.

## Reglas
1. **No saltes gates**: no cierres `dod` con gates abiertos; en particular `dod` exige `wiring_verified: true`.
2. **Retroceso permitido**: si una revisión posterior falla, pon su gate en `false` y retrocede `phase`.
3. **`fidelity`/`api` = `null`** cuando no aplican (no cuentan como abiertos para DoD). `fidelity` NO puede
   quedar `null` si el slice toca UI (`design_source.applies===true`): ahí debe llegar a `true` por
   verificación visual real (MCP). `wiring_verified` aplica siempre (no admite `null`).
4. **Archivar**: mueve `active_slice` a `history[]` con `phase:"archived"`, deja `active_slice:null`.
5. **Valida tras escribir**:
   ```bash
   python3 -c "import jsonschema,json; jsonschema.Draft202012Validator(json.load(open('.claude/state/build-state.schema.json'))).validate(json.load(open('.claude/state/build-state.json'))); print('OK')"
   ```

6. **Los workflows NO escriben el estado.** Las plantillas `*.workflow.js` (de `building-a-slice/workflows/`
   y `releasing-a-version/workflows/`) son **read-only** sobre `build-state.json`: devuelven un diagnóstico y
   el agente **dueño del gate** (single-writer: `build-orchestrator` para gates de slice, `releasing-a-version`
   para `releases[]`) aplica el mapeo respetando las reglas 1–5. Ningún workflow toca el estado en paralelo.

## Tabla de responsabilidad (quién cierra cada gate)
Ver `.claude/state/README.md` § "Quién escribe qué". El `build-orchestrator` es el único que
transiciona `phase` y archiva; los reviewers solo tocan su propio gate.
