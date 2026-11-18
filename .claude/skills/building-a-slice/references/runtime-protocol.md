# Protocolo de estado sobre el runtime (modos `dual` y `runtime`)

El estado del pipeline vive en el **Agent Orchestrator Runtime**: fases, gates, wiring,
checkpoints, releases y hechos de proyecto son suyos. El arnés **observa el working tree**
(hooks) y **transiciona el dominio** por la API. Ningún agente arma peticiones a mano: todo
acto pasa por `slice-ops.sh` (inner loop) y `release-ops.sh` (outer loop), instalados en
`.claude/hooks/build/`.

> **Antes de nada, pregunta el modo:**
> ```bash
> bash .claude/hooks/build/slice-ops.sh mode      # legacy | dual | runtime
> ```
> - `legacy` → **no** uses este documento: el fichero es primario, sigue `state-protocol.md`.
> - `dual` → el **fichero sigue siendo primario** (escríbelo como en `state-protocol.md`) y
>   **además** invoca los subcomandos: espejan cada transición al runtime. El claim NO
>   aplica en `dual` (devuelve rc 3): el slice lo decide el fichero.
> - `runtime` → el fichero es fósil: **no lo leas ni lo escribas**. Todo pasa por los
>   subcomandos, y el estado se consulta con `slice-ops.sh status`.

## Códigos de salida (ramifica sobre ellos, no sobre el texto)

| rc | Significado | Qué hace la skill |
|---|---|---|
| 0 | aceptado | continúa |
| 2 | uso incorrecto | corrige la invocación (bug de la skill, no del runtime) |
| 3 | modo `legacy` (o claim en `dual`) | sigue el protocolo del fichero |
| 4 | sin slice activo | reclama primero (`claim`) o abre el slice por DoR |
| 5 | offline: encolado | **sigue trabajando**; el daemon entrega al reconectar |
| 6 | rechazado por el servidor | **NO reintentes**: muestra la razón y corrige la causa |
| 7 | sin trabajo (204) o carrera perdida | comunica y termina limpio |

## El ciclo del slice

| Acto | Comando | Notas |
|---|---|---|
| Reclamar | `slice-ops.sh claim [--epic EP-XXX]` | Sincroniza el contexto **antes** (regla: no se abre trabajo con contexto viejo) y reporta los sha256 locales de los archivos gobernados. Si la respuesta trae `checkpoint`, **continúa desde él; jamás reinicies**. |
| Saber el paso | `slice-ops.sh next-step` | Lo deriva el **cliente** desde la proyección: `resume_hint` → wiring `failing` → sub-slice pendiente → primer gate abierto. |
| Reportar la fase | `slice-ops.sh phase <to>` | **Al entrar en cada fase del pipeline** (`dor → change → red → green → refactor → smoke → api → data → dod → pr`, orden estricto del hub). Emite la cadena `phase_advanced` que falte desde la fase que el servidor conoce (nada si ya está: idempotente). Sin esto el slice se queda en `dor` server-side y el archivado se rechaza. `archived` no se reporta aquí: lo produce `archive`. |
| Sembrar el cableado | `slice-ops.sh wiring seed --file items.json` | Un item por escenario AC y por punto de integración entre capas. Nacen `failing`. |
| Cablear un item | `slice-ops.sh wiring update <item_id> passing --kind K --ref HU-XXX --evidence-file f` | `passing` **solo tras prueba real ejecutada**. Sin evidencia el comando avisa: no lo ignores. |
| Frontera (`BND-*`) | mismos `wiring seed` / `wiring update <item_id> passing --kind integration_point --ref boundary:<id>#<forma>` | Un item por forma de mensaje contra una frontera declarada; no hay comando propio. La proyección descarta `ref`: el par `(frontera, forma)` se recupera del `item_id` por **prefijo más largo** de `boundaries[].id`. La memoria `boundaries[].verified[]` se escribe siempre en el `config/build-config.json` local. Ver [`boundary-check.md`](boundary-check.md). |
| Cerrar un gate | `slice-ops.sh gate <nombre> <pass\|fail\|na> --evidence-file f` | Gates canónicos: `dor coherence_link tdd journey_smoke fidelity api data wiring_verified dod`. Un `na` es legítimo cuando el gate no aplica. |
| Dejar bitácora | `slice-ops.sh progress «hito»` | Sustituye a `progress_log[]`: el event stream **es** la bitácora. |
| Guardar continuidad | `slice-ops.sh checkpoint --note «dónde me quedé»` | Rama + commit reales. Es lo que permite que otro agente continúe tras una caída. |
| Entregar | `slice-ops.sh submit --pr-url U --openspec-change C` | Tras abrir el PR. |
| Archivar | `slice-ops.sh archive --epic EP-XXX --openspec-change C --pr-url U` | Lo dispara `opsx:archive` en el mismo PR. Va por cola (idempotente, protegido de la cota). **Catch-up automático**: si la fase server-side quedó atrás, emite la cadena `phase_advanced` hasta `pr` antes del archivado y lo avisa (`⚠ … server-side`). |
| Hechos de proyecto | `slice-ops.sh fact scaffold-confirmed --by «persona»` · `fact design-source …` · `fact project-kind …` · `fact foundation …` | **Reportan lo que un humano confirmó**; el agente nunca confirma por su cuenta. |
| Bloqueo | `slice-ops.sh escalate «razón» --gate G` | Deja el rastro; la decisión (recortar/diferir/desbloquear) es del equipo. |
| Ver el estado | `slice-ops.sh status` | Modo, slice, gates, wiring, contexto, lease, cola pendiente y **rechazados** (`outbox/rejected/`: conteo + razón del más reciente — un rechazo del hub NO se reintenta solo; corrige la causa y re-emite). |

## Reglas duras

1. **Un gate no se salta y `dod` exige `wiring_verified`.** La compuerta real es el servidor:
   un `422` es la compuerta funcionando, no un error a reintentar.
2. **Nunca marques `passing`/`pass` por inspección.** La evidencia es de ejecución real.
3. **Contexto antes que trabajo.** Si el `manifest_hash` no coincide, el claim sincroniza
   solo; si el servidor responde `409 drift`, el cliente re-sincroniza y reintenta **una** vez.
4. **Un solo slice activo.** Reclamar con lease vigente devuelve el mismo slice (idempotente).
5. **Lease perdido** (`⚠ lease` en la statusline, `heartbeat-status.json`): haz `checkpoint`,
   detén el trabajo y vuelve a reclamar. No sigas cerrando gates con el lease caído.
6. **Offline no bloquea.** rc 5 = encolado: sigue construyendo; el daemon despacha al
   reconectar y el `client_event_id` evita duplicados.
7. **El agente no gobierna.** No cierra releases, no publica contexto, no importa el grafo,
   no abre/drena/cierra fronts: prepara, propone, reporta — y el humano decide en la consola.
8. **La fase se reporta al entrar, no al final.** El hub lleva la fase con `phase_advanced`
   de orden estricto: invoca `phase <to>` en cada transición del pipeline. Si un pipeline
   corrió sin reportarla, `archive` completa la cadena solo (catch-up) — pero la telemetría
   intermedia del hub habrá estado ciega todo el slice.

## Qué queda del fichero (legado)

En `runtime` el fichero `.claude/state/build-state.json` **no se lee ni se escribe** (queda fósil hasta que el sub-slice E lo retire); solo en modo `legacy` sigue siendo el protocolo primario — ver `state-protocol.md`. Lo que antes se leía de él ahora:

| Antes (fichero) | Ahora |
|---|---|
| `active_slice.gates` | `slice-ops.sh status` / caché de proyección |
| `active_slice.wiring_checklist[]` | eventos `wiring_*` + `wiring_failing` de la proyección |
| `active_slice.progress_log[]` | eventos `progress_noted` (event stream) |
| `session_continuity.resume_hint` | `resume_hint` de `/agent/context` (lo rinde `next-step`) |
| `scaffold`, `design_source`, `project_kind`, `foundation` | hechos de proyecto (`fact …`) |
| `history[]`, `releases[]`, `parallel_front` | proyecciones del runtime (consola del hub) |
