#!/usr/bin/env bash
# slice-ops.sh — operaciones de dominio del INNER LOOP que conducen las skills
# [EP-OR-08-C]. NO es un hook registrado (mismo estatus que context-sync.sh): lo invocan
# `building-a-slice`, los comandos /build:* y los agentes, UNA invocación por transición.
#
#   uso: slice-ops.sh <subcomando> [opciones]
#   subcomandos IMPLEMENTADOS (13 del plan + phase, issue #52; + propose-epic/epic-status/
#                epic-writeback, issue #62; + graph-sync/graph-sync-status, EP-OR-17):
#                mode | claim | next-step | phase | gate | submit | archive | wiring |
#                progress | checkpoint | fact | propose-asset | propose-epic | epic-status |
#                epic-writeback | graph-sync | graph-sync-status | graph-check (#86) |
#                graph-propose (#86) | graph-apply (#86) | graph-calibrate (#86) |
#                graph-telemetry (#86) | graph-otel-phases (#86) | otel-setup (#86) |
#                status | escalate.
#
# Contrato con la prosa: cada subcomando devuelve un código de salida tipado
# (0 ok · 2 uso · 3 legacy · 4 sin slice · 5 offline · 6 rechazado · 7 sin trabajo) y
# escribe en stdout lo que la skill debe mostrar. Fail-open: el trabajo local nunca se
# bloquea por el runtime (RNF-6).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-ops.sh"
# [#74] `register` manda el mismo harness_version/asset_types que el arranque de sesión.
source "$HERE/lib/harness-meta.sh"
# state_atomic_patch/state_path: escritura del progreso granular en modo legacy
# (wiring/progress/checkpoint dejan de devolver rc 3 y pasan a escribir el fichero).
source "$HERE/lib/state-io.sh"

usage() {
  cat >&2 <<'USAGE'
uso: slice-ops.sh <subcomando> [opciones]

  mode                                          imprime legacy|dual|runtime
  register [--runtime-url U] [--force]          da de alta ESTE árbol como agente propio con
                                                un token que el ADMIN emitió para él (el token
                                                se pide por STDIN, nunca por argumento).
                                                Obligatorio en un worktree antes de escribir:
                                                sin él se opera con la identidad heredada del
                                                clon principal.
  claim [--epic EP-XXX]                          reclama trabajo (solo modo runtime). Sin --epic,
                                                el hub reparte por orden de cola. Con --epic,
                                                claim dirigido ESTRICTO: entrega esa épica o
                                                rebota con el motivo del grafo, sin dejar lease
  next-step                                     deriva la siguiente acción desde la caché
  phase <to>                                    reporta la fase del pipeline (emite la cadena
                                                phase_advanced que falte; idempotente)
  gate <nombre> <pass|fail|na> [--evidence «texto» | --evidence-file F]
                                                reporta un veredicto del slice (hecho medido)
  submit [--pr-url U] [--openspec-change C]     entrega el slice
  archive [--pr-url U] [--openspec-change C] [--epic EP-XXX]
                                                archiva el slice (siempre por la cola)
  wiring seed --file items.json                 siembra el checklist de cableado (failing)
  wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]
  progress «nota» | --file F                    nota de progreso (bitácora = event stream)
  checkpoint [--note «t» | --note-file F]        continuidad tras una caída
  fact <scaffold-confirmed|design-source|project-kind|foundation|harness-phase> …
                                                reporta un hecho de proyecto confirmado
  propose-asset --type-key K --path P --content-file F
  propose-epic --file borrador.json            propone una épica al hub (SIN EP-XXX: la
                                                identidad la asigna el hub al aprobar)
  epic-status [--id P]                         estado de las propuestas (QUEUED|PROPOSED|
                                                APPROVED|REJECTED|FAILED)
  epic-writeback [--id P] [--file F]           escribe en epicas.md las épicas ya APROBADAS,
                                                con el código que asignó el hub (F debe estar
                                                bajo docs/03-backlog/: carve-out §9.2)
  graph-sync --file epics.json [--dry-run]      propone al hub el re-sync del grafo desde los
                                                docs de discovery (el humano aprueba; con
                                                --dry-run solo enseña el bundle, sin enviar)
  graph-sync-status [--id P]                    veredicto del re-sync (QUEUED|PROPOSED|
                                                APPROVED|REJECTED con el motivo del ADMIN)
  graph-check [--epic EP-XXX] [--cap 6] [--format human|json]
                                                valida la granularidad del grafo de épicas
                                                desde los docs (P2/P3/P4/P10 duras → rc 2;
                                                P5/capa/solapes → aviso). Lectura pura; es el
                                                gate que corre el DoR antes de abrir una épica
  graph-propose [--agents 3] [--cap 6] [--cost F] [--out docs/.reviews] [--format human|json] [--no-write]
                                                propone una partición que balancea coste y
                                                paralelismo (frontera + recomendada). Escribe
                                                la propuesta en docs/.reviews/; NO toca discovery
  graph-apply [--from propuesta.json] [--yes] [--format human|json]
                                                materializa el `depende_de` estructurado en
                                                epicas.md (y el `epica:` de las HU con --from);
                                                DRY-RUN salvo --yes; no toca AC (carve-out §9.2)
  graph-calibrate [--telemetry F] [--out F] [--format human|json] [--no-write]
                                                ajusta F/C_HU/S/ρ/I con la telemetría de tokens
                                                de las épicas archivadas (con intervalos) y
                                                escribe el fichero de costes que usa --propose
  graph-telemetry --epic EP-XXX (--tokens N | --phases J | --commits N | --auto) [--concurrent]
                                                registra el coste de una épica archivada en
                                                docs/.reviews/graph-telemetry.json (alimenta
                                                graph-calibrate; HU/tramos se derivan de los docs)
  graph-otel-phases --epic EP-XXX [--events F] [--markers F] [--session S] [--format phases|json]
                                                atribuye tokens por fase cruzando los eventos OTEL
                                                con las marcas de fase (P12-B); su salida alimenta
                                                `graph-telemetry --phases`
  otel-setup [--endpoint URL] [--events F] [--revert]
                                                activa OTEL en .claude/settings.json y genera el
                                                config del collector (opt-in; emite datos de uso)
  status [--no-refresh]                         informe local del agente
  escalate «razón» | --file F [--gate G]        registra un bloqueo (la decisión es humana)

códigos de salida: 0 ok · 2 uso · 3 legacy · 4 sin slice · 5 offline · 6 rechazado · 7 sin trabajo
                   · 9 identidad heredada (este worktree no está dado de alta: `register`)
USAGE
}

# ── claim ────────────────────────────────────────────────────────────────────────────
# Protocolo §3: siempre POST (el GET no acepta el reporte de hashes); regla 1: no se abre
# trabajo con contexto viejo, así que se sincroniza ANTES; los 409 se distinguen por su
# CUERPO (spec §3.1 rev. 2), no por el status.

# _claim_field <json> <clave> — lee una clave de primer nivel de una respuesta JSON.
_claim_field() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    v=d.get(sys.argv[1]) if isinstance(d,dict) else None
    print(v if isinstance(v,str) else "")
except Exception:
    print("")
' "$2" 2>/dev/null
}

# [EP-OR-17] Los motivos del 409 del claim, como los emite el hub DE VERDAD.
#
# Este `case` esperaba `drift`/`contention`/`context_unresolvable`/`cross_project` como valor de
# `reason` en la RAÍZ de la respuesta. Ninguno de esos literales existe en el backend del hub:
# un HTTPException de FastAPI anida SIEMPRE bajo `detail`, y los cuatro casos llegan como
#   • drift de contexto  → detail dict con `manifest_hash` (el hash al que sincronizar)
#   • contención         → detail str «contención con otra escritura del contexto: reintenta…»
#   • contexto irresoluble → detail str «…no hay trabajo sin contexto declarado»
#   • lease ajeno/expirado → detail str «El lease está expirado, es de otro agente o no existe…»
# Todos caían en el `*)` y salían como rechazo duro: un drift —que se resuelve sincronizando y
# reintentando— dejaba al agente sin claim y sin saber por qué. La clasificación por FORMA (el
# dict con manifest_hash) manda sobre la clasificación por texto, que solo se usa donde el hub
# construye el mensaje en un único sitio. Se conserva la lectura plana por compatibilidad.

# _claim_409_kind <json> — clasifica el 409: drift|contention|context_unresolvable|
# cross_project|"" (desconocido).
_claim_409_kind() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
if not isinstance(d,dict):
    print(""); raise SystemExit(0)
det=d.get("detail")
# Compatibilidad: una instancia que sí nombrara el motivo en un campo manda sobre el texto.
for fuente in (det if isinstance(det,dict) else {}, d):
    marca=fuente.get("reason") or fuente.get("error")
    if isinstance(marca,str) and marca:
        print(marca); raise SystemExit(0)
# El drift se reconoce por FORMA, no por texto: el borde del hub garantiza el `manifest_hash`
# en el cuerpo precisamente para que el cliente sepa a qué contexto sincronizar.
if isinstance(det,dict) and det.get("manifest_hash"):
    print("drift"); raise SystemExit(0)
texto=det if isinstance(det,str) else (det.get("message","") if isinstance(det,dict) else "")
t=str(texto).lower()
if "contenci" in t:
    print("contention")
elif "no hay trabajo sin contexto" in t:
    print("context_unresolvable")
elif "otro agente" in t or "otro proyecto" in t:
    print("cross_project")
else:
    print("")
' 2>/dev/null
}

# _claim_409_text <json> — el motivo del hub en prosa, para enseñárselo al humano sin volcarle
# el JSON crudo encima. Cae al cuerpo entero si no hay nada mejor.
_claim_409_text() {
  command -v python3 >/dev/null 2>&1 || { printf '%s' "$1"; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
crudo=sys.stdin.read()
try:
    d=json.loads(crudo)
except Exception:
    print(crudo.strip()); raise SystemExit(0)
if not isinstance(d,dict):
    print(crudo.strip()); raise SystemExit(0)
det=d.get("detail")
if isinstance(det,str) and det:
    print(det)
elif isinstance(det,dict):
    print(det.get("message") or json.dumps(det,ensure_ascii=False))
else:
    print(crudo.strip())
' 2>/dev/null
}

# _claim_render <json> — resumen compacto del slice reclamado (lo lee el humano y el modelo).
_claim_render() {
  command -v python3 >/dev/null 2>&1 || { echo "$1"; return; }
  printf '%s' "$1" | python3 - <<'PY' 2>/dev/null || echo "$1"
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(1)
if not isinstance(d,dict):
    sys.exit(1)
g=d.get("gates") or {}
abiertos=[k for k,v in g.items() if v is False]
lease=d.get("lease") or {}
cp=d.get("checkpoint")
print("slice:        %s (%s %s)" % (d.get("slice_id"), d.get("epic_code"), d.get("epic_title") or ""))
print("fase:         %s" % d.get("phase"))
print("gates abiertos: %s" % (", ".join(abiertos) if abiertos else "ninguno"))
print("rama base:    %s" % d.get("branch_base"))
print("change:       %s" % d.get("openspec_change"))
print("docs:         %s" % d.get("docs_ref"))
print("historias:    %s" % ", ".join(d.get("stories") or []))
print("lease:        expira %s (ttl %ss)" % (lease.get("expires_at"), lease.get("ttl_s")))
if cp:
    print("CHECKPOINT:   rama %s commit %s — CONTINÚA desde aquí, jamás reinicies (protocolo §3 regla 2)"
          % (cp.get("branch"), cp.get("commit_sha")))
PY
}

# _claim_once [epic] — una llamada. rc 20 = reintentable (drift|contention), resto = final.
# El cuerpo lleva context_hashes y, si se pidió una épica concreta, el claim dirigido
# ESTRICTO: `preferred_epic` + `preferred_epic_strict:true`. El estricto garantiza que el hub
# entrega EXACTAMENTE la pedida o rebota 409 con el motivo SIN dejar lease — jamás un claim
# "exitoso" de otra épica (la causa del viejo bloqueo [#39], ya resuelta en el hub).
_claim_once() {
  local hashes body resp status reason gv epic
  epic="${1:-}"
  hashes="$(ops_context_hashes)"
  # [#63] La versión de grafo viaja SOLO si la conocemos: un hub que no versiona (instancia
  # antigua) debe seguir viendo el mismo cuerpo de siempre — compatibilidad hacia atrás.
  gv="$(_runtime_graph_version)"
  if [ -n "$gv" ]; then
    body="{\"context_hashes\":$hashes,\"graph_version\":$gv}"
  else
    body="{\"context_hashes\":$hashes}"
  fi
  if [ -n "$epic" ]; then
    # Se inyecta antes del `}` de cierre, sea cual sea la variante del cuerpo base.
    body="${body%\}},\"preferred_epic\":\"$epic\",\"preferred_epic_strict\":true}"
  fi
  resp="$(runtime_post "$OPS_PATH_CLAIM" "$body")"
  status="$(runtime_http_status)"
  case "$status" in
    200)
      agent_context_fetch_and_cache || \
        echo "⚠ claim aceptado, pero /agent/context no respondió: se sigue con la caché anterior" >&2
      _claim_render "$resp"
      return $OPS_RC_OK ;;
    204)
      echo "NO_WORK: el runtime no tiene trabajo disponible para este agente"
      return $OPS_RC_NO_WORK ;;
    409)
      # [EP-OR-17] El grafo rancio se comprueba ANTES del `case`, con el helper del cliente:
      # conoce la forma REAL del hub (`detail.error = graph_version_stale`) además de la plana
      # que este sitio leía a mano y que el hub no emite en ninguna parte.
      local server_gv
      if server_gv="$(runtime_stale_graph_version "$resp")"; then
        # [#63] No es un error: es la señal de que operamos contra una foto vieja del
        # backlog. Se anota el desfase (lo muestra `status`) y se pide UN reintento con la
        # proyección refrescada. Mismo patrón que el 409 del lease en hb_renew.
        runtime_graph_note_stale "$gv" "$server_gv"
        echo "⚠ 409 (graph_version_stale): el grafo local (v${gv:-?}) va por detrás del hub (v${server_gv:-?})" >&2
        return 21
      fi
      reason="$(_claim_409_kind "$resp")"
      case "$reason" in
        drift|contention)
          echo "⚠ 409 ($reason): reintentable — $(_claim_409_text "$resp")" >&2
          return 20 ;;
        context_unresolvable)
          echo "⛔ 409 contexto irresoluble — NO reintentar: $(_claim_409_text "$resp")" >&2
          echo "  Resuélvelo en el hub (propuesta → publicación) y vuelve a reclamar." >&2
          return $OPS_RC_REJECTED ;;
        cross_project)
          echo "⛔ 409 cruce de proyecto (queda auditado en el servidor): $(_claim_409_text "$resp")" >&2
          echo "  Este clon está registrado contra otro proyecto: revisa runtime.credentials." >&2
          return $OPS_RC_REJECTED ;;
        dependencias_pendientes|lease_vigente|no_vigente|no_encontrada|solape_files_scope)
          # Claim dirigido ESTRICTO (--epic): la épica pedida no es reclamable según el grafo.
          # El hub NO dejó lease (el rechazo corre antes de todo efecto): no hay nada que soltar.
          echo "⛔ claim --epic rechazado por el grafo ($reason): $(_claim_409_text "$resp")" >&2
          echo "  El hub no dejó lease. Según el motivo: depende de otra épica sin archivar," >&2
          echo "  la tiene otro agente, está archivada/detenida, no existe, o su files_scope solapa" >&2
          echo "  con un lease vigente. Elige una épica elegible o reclama sin --epic (cola)." >&2
          return $OPS_RC_REJECTED ;;
        *)
          echo "⛔ 409 del hub: $(_claim_409_text "$resp")" >&2
          return $OPS_RC_REJECTED ;;
      esac ;;
    401|403)
      echo "⛔ token inválido o revocado ($status): pide un token nuevo al ADMIN del proyecto." >&2
      echo "  Los guards siguen operando con el último lock; el trabajo local no se detiene." >&2
      return $OPS_RC_REJECTED ;;
    422)
      echo "⛔ 422 el servidor rechazó el claim: $resp — no reintentar." >&2
      return $OPS_RC_REJECTED ;;
    000)
      echo "OFFLINE: runtime inalcanzable; se sigue con la caché local (RNF-6)" >&2
      return $OPS_RC_OFFLINE ;;
    *)
      echo "⚠ respuesta inesperada del claim ($status): $resp" >&2
      return $OPS_RC_OFFLINE ;;
  esac
}

# ── graph-check (issue #86) ──────────────────────────────────────────────────────────
# Valida la GRANULARIDAD del grafo de épicas desde los docs de discovery (P2 tope de tamaño,
# P3 épica sin HU con AC, P4 convexidad, P10 cierre de líneas — duras, rc 2; P5 deriva, capa,
# solapes — aviso, rc 0). LECTURA pura: queda FUERA de la compuerta de identidad (como
# `status`/`*-status`). Adaptador delgado sobre `scripts/lib/graph-check.py`.

# _run_pylib <script.py> <args…> — localiza un script de scripts/lib (fallback doble-ruta,
# igual que el bundle del grafo) y lo ejecuta, devolviendo su rc. Si falta el script o python3,
# avisa y devuelve OPS_RC_OFFLINE (5) — NUNCA revienta (fail-open sobre la infraestructura).
_run_pylib() {
  local nombre="$1"; shift
  local gc
  gc="$HERE/../../scripts/lib/$nombre"
  [ -f "$gc" ] || gc="$(config_root)/.claude/scripts/lib/$nombre"
  if [ ! -f "$gc" ]; then
    echo "⛔ no se encuentra $nombre: reinstala con \`trycore-build update\`" >&2
    return $OPS_RC_OFFLINE
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "⚠ sin python3: no se puede ejecutar $nombre" >&2
    return $OPS_RC_OFFLINE
  fi
  python3 "$gc" "$@"
}

cmd_graph_check() {
  _run_pylib graph-check.py "$@"
}

# graph-propose (#86, P1): propone una partición del grafo que balancea coste y paralelismo
# y escribe una propuesta en docs/.reviews/ (carve-out §9.2). NO toca el discovery ni el estado.
cmd_graph_propose() {
  _run_pylib graph-propose.py "$@"
}

# graph-apply (#86): materializa los campos estructurados del grafo en los docs de discovery
# (carve-out §9.2, aprobación humana). DRY-RUN por defecto; escribe solo con --yes. No toca AC.
cmd_graph_apply() {
  _run_pylib graph-apply.py "$@"
}

# graph-calibrate (#86, P12): ajusta F/C_HU/S/ρ/I con la telemetría de tokens de las épicas
# archivadas (mínimos cuadrados, con intervalos) y escribe el fichero de costes que usa --propose.
cmd_graph_calibrate() {
  _run_pylib graph-calibrate.py "$@"
}

# graph-telemetry (#86, P12): registra el coste de una épica archivada (HU/tramos/concurrencia +
# medida: --tokens/--phases/--commits/--auto) en docs/.reviews/graph-telemetry.json (carve-out) y,
# en dual/runtime, lo REPORTA al hub como evento `agent_token_usage` (para verlo en la consola).
cmd_graph_telemetry() {
  local epic="" tel="docs/.reviews/graph-telemetry.json" prev="" a rc mode payload pfile
  for a in "$@"; do
    case "$prev" in --epic) epic="$a" ;; --telemetry) tel="$a" ;; esac
    prev="$a"
  done
  _run_pylib graph-telemetry.py "$@"
  rc=$?
  # Reporte al hub: solo si se registró bien, hay épica, hay hub (dual/runtime) e identidad PROPIA
  # (#74: nunca reportar consumo con identidad heredada). Todo fail-open: jamás cambia el rc local.
  [ $rc -eq 0 ] && [ -n "$epic" ] || return $rc
  mode="$(ops_mode)"
  case "$mode" in dual|runtime) : ;; *) return $rc ;; esac
  command -v python3 >/dev/null 2>&1 || return $rc
  ops_guard_own_identity graph-telemetry >/dev/null 2>&1 || return $rc
  payload="$(python3 - "$tel" "$epic" <<'PY' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
recs = d.get("epics") if isinstance(d, dict) else d
r = next((x for x in (recs or []) if isinstance(x, dict) and x.get("epic") == sys.argv[2]), None)
if not r:
    sys.exit(0)
out = {"epic": r["epic"], "concurrent": bool(r.get("concurrent"))}
for k in ("hu", "tramos", "measure"):
    if r.get(k) is not None:
        out[k] = r[k]
if isinstance(r.get("phases"), dict):
    out["phases"] = r["phases"]
    tot = 0
    for v in r["phases"].values():
        if isinstance(v, (int, float)):
            tot += v
        elif isinstance(v, dict) and isinstance(v.get("tokens"), (int, float)):
            tot += v["tokens"]
    out["tokens"] = tot
elif r.get("tokens") is not None:
    out["tokens"] = r["tokens"]
print(json.dumps(out, ensure_ascii=False))
PY
)"
  [ -n "$payload" ] || return $rc
  pfile="$(ops_tmpjson "$payload")" || return $rc
  ops_enqueue_from_file agent_token_usage "$pfile" "" >/dev/null 2>&1 || true
  rm -f "$pfile"
  return $rc
}

# graph-otel-phases (#86, P12-B): cruza los eventos OTEL (api_request) con las marcas de fase y
# atribuye tokens a cada fase. Su salida (--format phases) alimenta `graph-telemetry --phases`.
cmd_graph_otel_phases() {
  _run_pylib graph-otel-phases.py "$@"
}

# otel-setup (#86, P12): activa OTEL en .claude/settings.json y genera el config del collector
# (opt-in; emite datos de uso). `--revert` lo desactiva. No toca estado ni discovery.
cmd_otel_setup() {
  _run_pylib otel-setup.py "$@"
}

cmd_claim() {
  local epic="" mode expected rc
  while [ $# -gt 0 ]; do
    case "$1" in
      --epic) epic="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  if [ "$mode" = "legacy" ]; then
    echo "LEGACY: el fichero es primario; abre el slice con el protocolo de references/state-protocol.md"
    return $OPS_RC_LEGACY
  fi
  if [ "$mode" = "dual" ]; then
    echo "DUAL_NO_CLAIM: en dual el slice lo decide el fichero (spec §6.1)."
    echo "Abre el slice en local y reporta cada transición con los demás subcomandos (espejo)."
    return $OPS_RC_LEGACY
  fi
  # Claim dirigido ESTRICTO: `claim --epic EP-XXX` escoge una épica concreta respetando el
  # grafo. El hub (POST /tasks/next con preferred_epic + preferred_epic_strict) entrega
  # EXACTAMENTE la pedida o rebota 409 con el motivo SIN dejar lease. Esto resuelve el viejo
  # bloqueo [#39]: el riesgo era un claim "exitoso" de OTRA épica dejando un lease huérfano;
  # el modo estricto lo hace imposible (jamás entrega una épica distinta de la pedida).
  if [ -n "$epic" ] && ! printf '%s' "$epic" | grep -Eq '^EP-[A-Za-z0-9-]+$'; then
    echo "⛔ --epic debe ser un código de épica (p.ej. EP-040); recibido: '$epic'" >&2
    return $OPS_RC_USAGE
  fi
  # [#86] Gate DURO del grafo antes de reclamar una épica concreta: si viola la política
  # (P2 tope de tamaño, P3 sin HU con AC, P4 ciclo, P10 línea posterior) no se abre. La
  # aceptación del PO no lo salta. Fail-open SOLO sobre la infraestructura (docs ilegibles o
  # sin python3): un backlog que no se puede leer no debe frenar el trabajo, pero una
  # violación REAL sí. El hub revalida el grafo al claim; esto falla rápido en local.
  if [ -n "$epic" ]; then
    local gcout gcrc
    gcout="$(_run_pylib graph-check.py --epic "$epic" 2>&1)"; gcrc=$?
    if [ $gcrc -eq 2 ]; then
      echo "⛔ el grafo de épicas bloquea abrir $epic (política del grafo, graph-check):" >&2
      printf '%s\n' "$gcout" | sed 's/^/  /' >&2
      echo "  Se corrige en los docs de discovery: se parte en épicas, no en tramos." >&2
      return $OPS_RC_REJECTED
    fi
    [ $gcrc -ne 0 ] && echo "⚠ graph-check no pudo validar $epic (rc $gcrc); se continúa (fail-open sobre infraestructura)." >&2
  fi
  # Contexto primero (protocolo §3 regla 1). context-sync.sh es fail-open: si no puede,
  # sale 0 y deja el lock anterior — el claim seguirá y el servidor detectará el drift.
  expected="$(projection_get context.manifest_hash "")"
  [ -n "$expected" ] || expected="$(runtime_field manifest_hash)"
  bash "$HERE/context-sync.sh" "$expected" >/dev/null 2>&1
  _claim_once "$epic"
  rc=$?
  if [ $rc -eq 20 ] || [ $rc -eq 21 ]; then
    # Drift, contención o grafo rancio: refrescar el estado REAL y reintentar EXACTAMENTE una
    # vez (protocolo §7). Pasar "" a context-sync.sh no fuerza nada — su fallback recae en la
    # caché de credenciales, que en el escenario de drift YA coincide con el lock local —, así
    # que se refresca antes con GET /agent/context y se usa SU manifest_hash como EXPECTED.
    # Para `stale_graph` ese mismo refresco es justamente lo que trae la versión nueva.
    agent_context_fetch_and_cache >/dev/null 2>&1
    expected="$(projection_get context.manifest_hash "")"
    bash "$HERE/context-sync.sh" "$expected" >/dev/null 2>&1
    local prev_rc=$rc
    _claim_once "$epic"
    rc=$?
    if [ $rc -eq 21 ]; then
      # Segundo 409 con el grafo ya refrescado: no es una carrera, es un desfase que el
      # cliente no puede resolver solo. El mensaje NOMBRA el desfase y la acción.
      local gs
      gs="$(runtime_graph_status_read)"
      echo "⛔ el hub rechaza el claim por versión de grafo obsoleta, incluso tras refrescar." >&2
      echo "  desfase: $gs" >&2
      echo "  El backlog del hub cambió mientras reclamabas (una épica propuesta, aprobada o" >&2
      echo "  rechazada). Vuelve a intentarlo en unos segundos; si persiste, revisa en la consola" >&2
      echo "  del hub que este proyecto no esté a mitad de un import de grafo." >&2
      return $OPS_RC_REJECTED
    fi
    if [ $rc -eq 20 ]; then
      echo "otro agente tomó la tarea; pide la siguiente"
      return $OPS_RC_NO_WORK
    fi
    # Un claim correcto tras un stale_graph deja el marcador de desfase sin sentido.
    [ $rc -eq 0 ] && [ "$prev_rc" -eq 21 ] && runtime_graph_clear_stale
  fi
  return $rc
}

# ── next-step ────────────────────────────────────────────────────────────────────────
# El servidor entrega hechos; el PASO lo deriva el cliente (spec §2, invierte el plan §1.3).
# Prioridad determinista, la primera que aplique.
cmd_next_step() {
  local sid proj tmp_script
  sid="$(ops_slice_id)"
  if [ -z "$sid" ]; then
    echo "sin slice activo: reclama trabajo (\`slice-ops.sh claim\`) o abre uno por DoR"
    return $OPS_RC_NO_SLICE
  fi
  command -v python3 >/dev/null 2>&1 || { echo "continúa el pipeline por la fase del slice"; return $OPS_RC_OK; }
  proj="$(runtime_projection_read)"
  tmp_script="$(mktemp)"
  cat > "$tmp_script" <<'PY'
import json,sys
orden=sys.argv[1].split()
try:
    d=json.load(sys.stdin)
except Exception:
    d={}
sl=d.get("active_slice") or {}
hint=sl.get("resume_hint")
failing=sl.get("wiring_failing") or []
subs=sl.get("sub_slices_pending") or []
gates=sl.get("gates") or {}
if hint:
    print("resume_hint: %s" % hint)
elif failing:
    it=failing[0]
    _k=it.get("kind")
    print("cablear el item de wiring «%s»%s con prueba REAL ejecutada; no lo marques passing por inspección"
          % (it.get("item_id"), (" (%s)" % _k) if _k else ""))
elif subs:
    print("construir el siguiente sub-slice: %s (journey_smoke verde antes de pasar al siguiente)" % subs[0])
else:
    abierto=next((g for g in orden if gates.get(g) is False), None)
    if abierto:
        print("cerrar el gate «%s» (fase %s)" % (abierto, sl.get("phase")))
    else:
        print("todos los gates conocidos están cerrados: abre el PR, archiva el change y reporta submit")
PY
  echo "$proj" | python3 "$tmp_script" "$OPS_SLICE_GATES" 2>/dev/null || echo "continúa el pipeline por la fase del slice"
  rm -f "$tmp_script"
}

# ── fact ─────────────────────────────────────────────────────────────────────────────
# Hechos de PROYECTO, contrato del catálogo v2 del hub [#38] (project_facts_domain):
# - Hechos MÁQUINA (`project_kind`, `harness_phase`, `foundation`, `design_source_applies`):
#   UN solo tipo, `project_fact_updated`, con el payload EXACTO {fact, value, source:"AGENT"}
#   (extra="forbid": ninguna otra clave viaja). Ámbito proyecto: sin `slice_id`.
# - Hechos HUMANOS (`scaffold_confirmed`, `design_source_*`): el hub los rechaza en TODA
#   superficie de agente — se fijan tras el PDP por la superficie admin
#   (PATCH /orchestrator/projects/{project_id}). En runtime/dual NO se encola: rechazo
#   local claro que dirige al humano a la consola del hub. En legacy nada cambia.
cmd_fact() {
  local hecho="${1:-}" mode
  [ -n "$hecho" ] && shift
  mode="$(ops_mode)"
  if [ "$mode" = "legacy" ]; then
    echo "LEGACY: escribe el hecho en el fichero (scaffold/design_source/project_kind/foundation)"
    return $OPS_RC_LEGACY
  fi
  case "$hecho" in
    scaffold-confirmed) _fact_scaffold "$@" ;;
    design-source) _fact_design_source "$@" ;;
    design-source-applies) _fact_design_source_applies "$@" ;;
    project-kind) _fact_project_kind "$@" ;;
    foundation) _fact_foundation "$@" ;;
    harness-phase) _fact_harness_phase "$@" ;;
    *) echo "uso: slice-ops.sh fact <scaffold-confirmed|design-source|design-source-applies|project-kind|foundation|harness-phase> [opciones]" >&2
       return $OPS_RC_USAGE ;;
  esac
}

# _ops_emit_event <tipo> <payload_json> [slice_id] — evento genérico de dominio: espejo en
# dual (mejor esfuerzo, spec §4.1-D) o cola en runtime (spec §3.1). El slice_id es opcional
# (los hechos de PROYECTO se encolan sin él, spec §3.1 rev. 3; una escalada de slice sí lo
# lleva). Devuelve $OPS_RC_OFFLINE si el runtime no pudo aceptar el evento (outbox no
# escribible, python3 ausente u otro fallo local) — el caller decide qué avisar y nunca debe
# reportar éxito en ese caso (fail-open sobre el trabajo local, nunca sobre el reporte).
_ops_emit_event() {
  local tipo="$1" payload="$2" sid="${3:-}" pfile mode epic
  mode="$(ops_mode)"
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OFFLINE
  if [ "$mode" = "dual" ]; then
    # [EP-OR-17] El `epic_code` va en el SOBRE del espejo, que es donde el hub lo lee. Muchos de
    # los tipos que pasan por aquí (hechos de proyecto, archivado, escalada) no son espejables:
    # `ops_mirror` los corta en local con rc 8 antes de gastar una llamada.
    epic="$(ops_local_slice_ref | python3 -c 'import json,sys; print(json.load(sys.stdin).get("epic_code") or "")' 2>/dev/null)"
    ops_mirror "$tipo" "$pfile" "$epic" || echo "⚠ «${tipo}» no espejado; el comparador dual lo marcará" >&2
    rm -f "$pfile"
    return $OPS_RC_OK
  fi
  if ! ops_enqueue_from_file "$tipo" "$pfile" "$sid"; then
    rm -f "$pfile"
    return $OPS_RC_OFFLINE
  fi
  rm -f "$pfile"
  return $OPS_RC_OK
}

# _fact_human_reject <fact> — [#38] rechazo LOCAL del hecho humano en runtime/dual: el hub
# responde 422 en TODA superficie de agente (`rechazo_de_hecho_humano`); encolarlo era un
# reintento eterno de algo que jamás iba a entrar. El humano lo fija en la consola del hub.
_fact_human_reject() {
  local fact="$1"
  echo "⛔ «${fact}» es un hecho HUMANO: no entra por la superficie de agente del hub." >&2
  echo "  Se fija tras el PDP por la superficie admin: PATCH /orchestrator/projects/{project_id}" >&2
  echo "  (consola del hub). Pide al ADMIN del proyecto que lo confirme allí; este subcomando" >&2
  echo "  no lo encola. En modo legacy sigue escribiéndose en el fichero local." >&2
  return $OPS_RC_REJECTED
}

# _fact_machine_emit <fact> <value_json> — [#38] hecho MÁQUINA del catálogo v2: payload
# EXACTO {fact, value, source:"AGENT"} (extra="forbid" en el hub: nada más viaja) y SIN
# slice_id (ámbito proyecto). También en dual va por la COLA (POST /events): la ingesta
# espejo solo acepta transiciones de slice (TIPOS_DE_ESPEJO) y rechazaría el hecho.
_fact_machine_emit() {
  local fact="$1" value_json="$2" payload pfile
  payload="{\"fact\":$(ops_json_str "$fact"),\"value\":$value_json,\"source\":\"AGENT\"}"
  pfile="$(ops_tmpjson "$payload")" || {
    echo "⚠ hecho \"$fact\" no se pudo encolar (fallo local)" >&2
    return $OPS_RC_OFFLINE
  }
  if ! ops_enqueue_from_file project_fact_updated "$pfile" ""; then
    rm -f "$pfile"
    echo "⚠ hecho \"$fact\" no se pudo encolar (outbox no escribible u otro fallo local)" >&2
    return $OPS_RC_OFFLINE
  fi
  rm -f "$pfile"
  echo "hecho de proyecto \"$fact\" encolado (project_fact_updated)"
  return $OPS_RC_OK
}

_fact_scaffold() {
  _fact_human_reject scaffold_confirmed
}

_fact_design_source() {
  _fact_human_reject design_source_confirmed
}

# `design_source_applies` ("¿el proyecto tiene UI?") es un hecho MÁQUINA — a diferencia de
# `design_source_confirmed` (gobierno, humano): es un hecho OBJETIVO que el agente deriva de
# discovery, como `project_kind`. El hub lo proyecta a un Boolean. Sin él, el
# `design-source-guard` del arnés queda inerte en runtime (siempre lee `false`).
_fact_design_source_applies() {
  local applies="${1:-}"
  [ -n "$applies" ] && shift
  case "$applies" in true|false) : ;; *) echo "⛔ design-source-applies debe ser true|false" >&2; return $OPS_RC_REJECTED ;; esac
  _fact_machine_emit design_source_applies "$applies"
}

_fact_project_kind() {
  local kind="${1:-}" src="human"
  [ -n "$kind" ] && shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --source) src="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$kind" in greenfield|brownfield) : ;; *) echo "⛔ project-kind debe ser greenfield|brownfield" >&2; return $OPS_RC_REJECTED ;; esac
  # --source auto|human se sigue aceptando (compat con los comandos /build:*), pero NO
  # viaja: en la superficie de agente el hub solo admite source="AGENT" (progress_service).
  case "$src" in auto|human) : ;; *) echo "⛔ --source debe ser auto|human" >&2; return $OPS_RC_REJECTED ;; esac
  _fact_machine_emit project_kind "$(ops_json_str "$kind")"
}

_fact_foundation() {
  local required="" epic="" cfile=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --required) required="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --epic) epic="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --checklist-file) cfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$required" in true|false) : ;; *) echo "⛔ --required debe ser true|false" >&2; return $OPS_RC_REJECTED ;; esac
  # El hub proyecta `foundation` a un Boolean (`foundation_confirmed`): el value es el
  # booleano de --required. --epic y --checklist-file se aceptan por compat con
  # /build:onboard pero NO viajan (extra="forbid"): la checklist queda en los docs locales.
  _fact_machine_emit foundation "$required"
}

_fact_harness_phase() {
  local fase="${1:-}"
  case "$fase" in authoring|building) : ;; *) echo "⛔ harness-phase debe ser authoring|building" >&2; return $OPS_RC_REJECTED ;; esac
  _fact_machine_emit harness_phase "$(ops_json_str "$fase")"
}

# ── propose-asset ────────────────────────────────────────────────────────────────────
# Un agente JAMÁS publica contexto (protocolo §6): propone contra la superficie de agente
# `…/context/agent-proposals` (no la humana `…/context/proposals`) y un ADMIN publica.
cmd_propose_asset() {
  local type_key="" path="" cfile="" mode pid body resp status
  while [ $# -gt 0 ]; do
    case "$1" in
      --type-key) type_key="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --path) path="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --content-file) cfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$type_key" ] || [ -z "$path" ] || [ -z "$cfile" ]; then
    echo "uso: slice-ops.sh propose-asset --type-key K --path P --content-file F" >&2
    return $OPS_RC_USAGE
  fi
  [ -f "$cfile" ] || { echo "⛔ no existe el fichero de contenido: $cfile" >&2; return $OPS_RC_USAGE; }
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: el documento queda en git; no hay plano de contexto que proponer"; return $OPS_RC_LEGACY; }
  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || { echo "⛔ sin project_id en runtime.credentials: corre \`trycore-build init\`" >&2; return $OPS_RC_REJECTED; }
  # El contenido puede ser largo: se serializa por fichero (nunca por argv) y el body sale
  # por `curl --data-binary @fichero` dentro de runtime_post.
  body="{\"path\":$(ops_json_str "$path"),\"type_key\":$(ops_json_str "$type_key"),\"content\":$(ops_json_str_file "$cfile" 200000)}"
  resp="$(runtime_post "$(ops_path_proposals "$pid")" "$body")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202)
      echo "propuesta creada: $resp"
      echo "El agente NO publica contexto: la revisa y publica un ADMIN en la consola del hub."
      return $OPS_RC_OK ;;
    422)
      echo "⛔ 422 la propuesta no valida contra el schema del tipo \"$type_key\": $resp" >&2
      return $OPS_RC_REJECTED ;;
    401|403)
      echo "⛔ token inválido o sin permiso para proponer ($status): habla con el ADMIN." >&2
      return $OPS_RC_REJECTED ;;
    *)
      echo "OFFLINE: no se pudo proponer el asset (status $status). El documento queda en git; reintenta al reconectar." >&2
      return $OPS_RC_OFFLINE ;;
  esac
}

# ── propose-epic ─────────────────────────────────────────────────────────────────────
# [#62] La terminal PROPONE, el hub decide la identidad, un humano aprueba. El agente pierde
# a propósito la potestad de inventar el `EP-XXX`: elegirlo mirando `epicas.md` es lo que hizo
# que dos terminales crearan EP-042 y EP-043 el mismo día y sus historias colisionaran.
# Va por el carril directo de la outbox (endpoint propio, hub#113) para sobrevivir a estar
# offline, y se intenta despachar en el acto para poder devolver el identificador del hub.

# _epic_draft_normalize <fichero> — imprime el cuerpo de la propuesta ya normalizado, o "" con
# rc 2 si el borrador no vale. `epic_code`/`code`/`id` se DESCARTAN (no se rechaza la
# propuesta: la decisión de hub#113 es ignorar el campo, no fallar por él).
_epic_draft_normalize() {
  local f="$1"
  # [Importante 4] sin python3 no es "borrador inválido" (rc 2 de uso): es una degradación de
  # infraestructura — se anuncia con esas palabras y con OFFLINE, para que no se confunda con
  # un borrador mal escrito.
  command -v python3 >/dev/null 2>&1 || {
    echo "⛔ sin python3: no se puede validar el borrador en local" >&2
    return $OPS_RC_OFFLINE
  }
  # OJO: sin `2>/dev/null` aquí — el llamador captura este stderr en `$errf` para mostrar
  # el motivo del rc 2 (validación) o el aviso de `epic_code` ignorado; silenciarlo aquí
  # los perdería a los dos.
  python3 - "$f" <<'PY'
import json,re,sys
# [#70] El vocabulario del BORRADOR (lo que escribe el agente) y el del CONTRATO del hub
# (`EpicProposalIn`) no son el mismo: el borrador habla en minúsculas y conoce `technical`;
# el hub solo acepta el literal FOUNDATIONAL|BUSINESS. La traducción vive aquí, en el borde,
# porque rechazar `technical` sería castigar al agente por una distinción que el grafo no
# hace: para el hub una épica técnica es de negocio.
CAPAS={"foundational":"FOUNDATIONAL","business":"BUSINESS","technical":"BUSINESS"}

def escenarios(txt):
    """Criterios en prosa -> `acceptance[]` del contrato: un escenario Dado/Cuando/Entonces
    por entrada. Se parte por líneas y, dentro de cada una, por el `. Dado ` que separa dos
    escenarios seguidos en un mismo párrafo."""
    out=[]
    for linea in str(txt).splitlines():
        linea=linea.strip().lstrip("-*•").strip()
        if not linea:
            continue
        for trozo in re.split(r"\.\s+(?=Dado\s)", linea):
            trozo=trozo.strip()
            if trozo:
                out.append(trozo[:2000])
    return out[:20]

try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print("⛔ el borrador no es un JSON legible", file=sys.stderr); raise SystemExit(2)
if not isinstance(d,dict):
    print("⛔ el borrador debe ser un objeto JSON", file=sys.stderr); raise SystemExit(2)
title=(d.get("title") or "").strip()
objective=(d.get("objective") or "").strip()
if not title:
    print("⛔ el borrador no trae `title` (título de la épica)", file=sys.stderr); raise SystemExit(2)
if not objective:
    print("⛔ el borrador no trae `objective` (objetivo de la épica)", file=sys.stderr); raise SystemExit(2)
layer=str(d.get("layer") or "business").strip().lower()
if layer not in CAPAS:
    print("⛔ `layer` debe ser uno de: %s" % ", ".join(sorted(CAPAS)), file=sys.stderr); raise SystemExit(2)
ignorados=[k for k in ("epic_code","code","id") if d.get(k)]
stories=[]
for s in d.get("stories") or []:
    if isinstance(s,str):
        stories.append({"title":s[:300]})
    elif isinstance(s,dict) and (s.get("title") or "").strip():
        st={"title":s["title"].strip()[:300]}
        if s.get("description"):
            st["description"]=str(s["description"])[:2000]
        # La `acceptance` explícita del borrador manda; si no, se derivan de los criterios en
        # prosa. `acceptance_criteria` NO viaja: el hub descarta el campo en el borde
        # (`extra="ignore"`) y la consola enseñaba las historias sin un solo criterio.
        acc=s.get("acceptance")
        if isinstance(acc,list):
            acc=[str(x).strip()[:2000] for x in acc if str(x).strip()][:20]
        elif s.get("acceptance_criteria"):
            acc=escenarios(s["acceptance_criteria"])
        else:
            acc=[]
        if acc:
            st["acceptance"]=acc
        stories.append(st)
out={"title":title[:300],"objective":objective[:2000],"layer":CAPAS[layer],
     "files_scope":[str(x) for x in (d.get("files_scope") or []) if isinstance(x,(str,int))],
     "depends_on":[str(x) for x in (d.get("depends_on") or []) if isinstance(x,(str,int))],
     "stories":stories}
if ignorados:
    print("IGNORADOS %s" % ",".join(ignorados), file=sys.stderr)
print(json.dumps(out,ensure_ascii=False))
PY
}

# [#70] `EpicProposalOut` del contrato nombra `id` al identificador de la propuesta (el
# borrador de hub#113 lo llamaba `proposal_id`). Sin esto la terminal decía «sin identificador
# en la respuesta» y el ledger guardaba "" — `epic-status` se quedaba sin a quién preguntar.
# Se acepta el nombre viejo como respaldo: un hub anterior al contrato sigue funcionando.
_epic_proposal_id() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    r=(d.get("response") if isinstance(d.get("response"),dict) else d) or {}
    print(r.get("id") or r.get("proposal_id") or "")
except Exception:
    print("")
' 2>/dev/null
}

# _epic_from_response <respuesta> — la épica aprobada como objeto para el ledger. El contrato
# la devuelve en la RAÍZ de `EpicProposalOut`; el borrador viejo la anidaba en `epic`.
_epic_from_response() {
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    print("{}"); raise SystemExit(0)
if not isinstance(d,dict):
    print("{}"); raise SystemExit(0)
e=d.get("epic")
if not isinstance(e,dict):
    e={k:d[k] for k in ("title","objective","layer","stories","files_scope","depends_on") if k in d}
print(json.dumps(e,ensure_ascii=False))
' 2>/dev/null || echo "{}"
}

cmd_propose_epic() {
  local file="" mode pid norm errf rc cid pfile ack proposal_id reason
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$file" ]; then
    echo "uso: slice-ops.sh propose-epic --file borrador.json" >&2
    echo "  borrador: {title, objective, layer, files_scope[], depends_on[], stories[]}" >&2
    echo "  SIN EP-XXX: el código lo asigna el hub al aprobar." >&2
    return $OPS_RC_USAGE
  fi
  [ -f "$file" ] || { echo "⛔ no existe el borrador: $file" >&2; return $OPS_RC_USAGE; }
  mode="$(ops_mode)"
  # [Ronda final] El texto ramifica por modo: en `dual` SÍ hay hub (el fichero es primario,
  # pero el proyecto está registrado), y decirle al usuario «no hay hub al que proponer» le
  # hacía buscar un problema de conexión que no existe.
  if [ "$mode" = "dual" ]; then
    echo "DUAL: el fichero local es primario y el carril de propuesta solo opera en modo \`runtime\`."
    echo "La épica se crea en discovery (\`/trycore:epicas\`) o, si es la caparazón, por el"
    echo "carve-out de /build:onboard Fase 2c; llega al hub por el import de admin."
    return $OPS_RC_LEGACY
  fi
  if [ "$mode" != "runtime" ]; then
    echo "LEGACY: la épica se crea en discovery (\`/trycore:epicas\`) o, si es la caparazón,"
    echo "por el carve-out de /build:onboard Fase 2c. No hay hub al que proponer."
    return $OPS_RC_LEGACY
  fi
  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || { echo "⛔ sin project_id en runtime.credentials: corre \`trycore-build init\`" >&2; return $OPS_RC_REJECTED; }

  errf="$(mktemp)" || return $OPS_RC_OFFLINE
  norm="$(_epic_draft_normalize "$file" 2>"$errf")"
  rc=$?
  # [Importante 4] rc OFFLINE (sin python3) no es lo mismo que rc USAGE (borrador inválido):
  # el primero es fallo de infraestructura, reintentable; el segundo es del agente.
  if [ "$rc" -eq "$OPS_RC_OFFLINE" ]; then
    cat "$errf" >&2
    rm -f "$errf"
    return $OPS_RC_OFFLINE
  fi
  if [ $rc -ne 0 ] || [ -z "$norm" ]; then
    cat "$errf" >&2
    rm -f "$errf"
    return $OPS_RC_USAGE
  fi
  if grep -q '^IGNORADOS ' "$errf"; then
    echo "⚠ código de épica ignorado ($(sed -n 's/^IGNORADOS //p' "$errf")): la identidad la asigna el hub al aprobar." >&2
  fi
  rm -f "$errf"

  pfile="$(ops_tmpjson "$norm")" || return $OPS_RC_OFFLINE
  # El `1` final pide el estampado de la versión de grafo AL DESPACHAR [#63]: una propuesta
  # encolada offline debe salir con la versión vigente en ese momento, no con la de ayer.
  cid="$(runtime_enqueue_direct epic_proposed POST "$(ops_path_epic_proposals "$pid")" "$pfile" 1)"
  rm -f "$pfile"
  if [ -z "$cid" ]; then
    echo "⛔ no se pudo encolar la propuesta (outbox no escribible): guárdala y reintenta." >&2
    return $OPS_RC_OFFLINE
  fi
  ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"QUEUED\",\"proposal_id\":null,\"epic_code\":null,\"written_back_at\":null,\"draft\":$norm}"

  # Intento de despacho inmediato: si hay red, la skill puede enseñar YA el identificador.
  runtime_dispatch_outbox >/dev/null 2>&1
  ack="$(ops_epic_ack_read "$cid")"
  if [ -n "$ack" ]; then
    proposal_id="$(_epic_proposal_id "$ack")"
    ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"PROPOSED\",\"proposal_id\":$(ops_json_str "$proposal_id")}"
    echo "propuesta enviada: ${proposal_id:-sin identificador en la respuesta}"
    echo "Queda en PROPOSED: NO es reclamable hasta que un humano la apruebe en la consola del hub."
    echo "El código EP-XXX lo asigna el hub AL APROBAR. Consulta con \`slice-ops.sh epic-status\`."
    return $OPS_RC_OK
  fi
  reason="$(ops_epic_rejected_reason "$cid")"
  if [ -n "$reason" ]; then
    ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"FAILED\",\"reason\":$(ops_json_str "$reason")}"
    echo "⛔ la propuesta no se pudo entregar: $reason" >&2
    return $OPS_RC_REJECTED
  fi
  echo "propuesta encolada: $cid"
  # [Ronda final] El texto ya no afirma «sin conexión»: desde que el despacho lleva mutex
  # (A1), este camino también se toma cuando el daemon estaba despachando la cola en ese
  # mismo instante y el intento en primer plano cedió el turno. La propuesta está encolada y
  # el daemon la lleva en los dos casos —el rc 5 y la conducta no cambian—, pero nombrar una
  # causa que puede ser falsa manda al usuario a revisar una red que funciona.
  echo "PENDIENTE: se despachará sola (el daemon de heartbeat la lleva). Sin conexión aún, o"
  echo "el daemon estaba drenando la cola en este instante. \`slice-ops.sh epic-status\` la sigue."
  echo "NO escribas la épica en docs/03-backlog/epicas.md: el código lo asigna el hub al aprobar."
  return $OPS_RC_OFFLINE
}

# ── epic-status ──────────────────────────────────────────────────────────────────────
# [#62] Resuelve el ciclo de vida de cada propuesta del ledger. Dos fuentes por estado:
#   QUEUED   → mira el ack del carril directo (¿ya se despachó?) o el rechazo local.
#   PROPOSED → pregunta al hub por su estado (APPROVED con `epic_code`, o REJECTED con razón).
# Es INFORMATIVO: rc 0 siempre en runtime, pase lo que pase.
cmd_epic_status() {
  local only="" mode pid entries n i cid pidv st ack resp status tmp
  while [ $# -gt 0 ]; do
    case "$1" in
      --id) only="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  if [ "$mode" = "dual" ]; then
    echo "DUAL: no hay propuestas que consultar (el carril solo opera en modo \`runtime\`);"
    echo "las épicas viven en docs/03-backlog/epicas.md"
    return $OPS_RC_LEGACY
  fi
  if [ "$mode" != "runtime" ]; then
    echo "LEGACY: no hay propuestas que consultar; las épicas viven en docs/03-backlog/epicas.md"
    return $OPS_RC_LEGACY
  fi
  command -v python3 >/dev/null 2>&1 || { echo "sin python3: no se puede leer el ledger"; return $OPS_RC_OK; }
  pid="$(runtime_field project_id)"

  # Primero, la parte que NO toca la red: acks y rechazos del carril directo.
  tmp="$(mktemp)" || return $OPS_RC_OK
  ops_epic_ledger_read > "$tmp"
  n="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["proposals"]))' "$tmp" 2>/dev/null)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  if [ "$n" -eq 0 ]; then
    rm -f "$tmp"
    echo "sin propuestas de épica registradas en esta copia del proyecto"
    return $OPS_RC_OK
  fi
  i=0
  while [ "$i" -lt "$n" ]; do
    cid="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposals"][int(sys.argv[2])].get("client_event_id") or "")' "$tmp" "$i" 2>/dev/null)"
    pidv="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposals"][int(sys.argv[2])].get("proposal_id") or "")' "$tmp" "$i" 2>/dev/null)"
    st="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["proposals"][int(sys.argv[2])].get("status") or "")' "$tmp" "$i" 2>/dev/null)"
    i=$((i + 1))
    [ -n "$only" ] && [ "$only" != "$pidv" ] && continue

    if [ "$st" = "QUEUED" ] && [ -n "$cid" ]; then
      ack="$(ops_epic_ack_read "$cid")"
      if [ -n "$ack" ]; then
        pidv="$(_epic_proposal_id "$ack")"
        st=PROPOSED
        ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"PROPOSED\",\"proposal_id\":$(ops_json_str "$pidv")}"
      else
        local rej; rej="$(ops_epic_rejected_reason "$cid")"
        if [ -n "$rej" ]; then
          ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"FAILED\",\"reason\":$(ops_json_str "$rej")}"
          echo "$cid  FAILED       $rej"
          continue
        fi
        echo "$cid  QUEUED       aún en la cola: se despachará al recuperar conexión"
        continue
      fi
    fi

    if [ "$st" = "PROPOSED" ] && [ -n "$pidv" ] && [ -n "$pid" ]; then
      resp="$(runtime_get "$(ops_path_epic_proposal "$pid" "$(ops_urlenc "$pidv")")")"
      status="$(runtime_http_status)"
      case "$status" in
        200)
          st="$(_claim_field "$resp" status)"
          case "$st" in
            APPROVED)
              local code epic
              # [#70] El código lo asigna el hub en `assigned_code` (EP-OR-15); `epic_code` era
              # el nombre del borrador y se conserva como respaldo.
              code="$(_claim_field "$resp" assigned_code)"
              [ -n "$code" ] || code="$(_claim_field "$resp" epic_code)"
              epic="$(_epic_from_response "$resp")"
              [ -n "$epic" ] || epic="{}"
              ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"APPROVED\",\"epic_code\":$(ops_json_str "$code"),\"epic\":$epic}"
              echo "$pidv  APPROVED     $code — escríbela con \`slice-ops.sh epic-writeback\`" ;;
            REJECTED)
              # [#70] El motivo del rechazo humano viaja en `reject_reason` (EP-OR-15).
              local why; why="$(_claim_field "$resp" reject_reason)"
              [ -n "$why" ] || why="$(_claim_field "$resp" reason)"
              ops_epic_ledger_upsert "{\"client_event_id\":\"$cid\",\"status\":\"REJECTED\",\"reason\":$(ops_json_str "$why")}"
              echo "$pidv  REJECTED     ${why:-sin motivo registrado}" ;;
            *)
              echo "$pidv  PROPOSED     pendiente de aprobación humana en la consola del hub" ;;
          esac ;;
        404)
          echo "$pidv  ?            el hub no expone la consulta de propuestas: instancia sin soporte (hub#113 pendiente)" ;;
        401|403)
          echo "$pidv  ?            token inválido o sin permiso ($status): habla con el ADMIN" ;;
        *)
          echo "$pidv  ?            OFFLINE: no se pudo consultar (status $status); se conserva el estado local" ;;
      esac
      continue
    fi
    echo "${pidv:-$cid}  $st"
  done
  rm -f "$tmp"
  return $OPS_RC_OK
}

# ── epic-writeback ───────────────────────────────────────────────────────────────────
# [#62] La vuelta del ciclo: aprobada la propuesta (hub#114), la épica se escribe en
# docs/03-backlog/epicas.md con el código que asignó el HUB. El fichero queda como
# PROYECCIÓN del grafo, nunca al revés — por eso el bloque es mecánico y siempre el mismo:
# una redacción libre por write-back haría que el fichero y el hub se separaran a cada pasada.
# Idempotente: si el `EP-XXX` ya tiene sección en el fichero, no se duplica (se marca hecho).
# Los códigos de HU los pone el hub si los trae; el arnés NUNCA los inventa (inventarlos es
# exactamente la colisión que motivó el issue).
# _epic_writeback_path_ok <ruta> <directorio-permitido> — imprime "OK" solo si la ruta cae
# DENTRO del directorio permitido, con symlinks y `..` ya resueltos (`realpath` sobre ambos).
# Sin python3 no se puede resolver la ruta: imprime "" (rechaza). Preferir el rechazo al
# permiso es lo correcto aquí — es una compuerta de escritura sobre ficheros ajenos.
_epic_writeback_path_ok() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  python3 - "$1" "$2" <<'PY' 2>/dev/null
import os,sys
try:
    t=os.path.realpath(sys.argv[1])
    base=os.path.realpath(sys.argv[2])
except Exception:
    print(""); raise SystemExit(0)
print("OK" if t.startswith(base + os.sep) else "")
PY
}

cmd_epic_writeback() {
  local only="" target="" mode root wrote rc
  while [ $# -gt 0 ]; do
    case "$1" in
      --id) only="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --file) target="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  if [ "$mode" = "dual" ]; then
    echo "DUAL: el fichero local es primario; docs/03-backlog/epicas.md ya es la fuente y no"
    echo "hay grafo del hub que proyectar sobre él (el carril solo opera en modo \`runtime\`)"
    return $OPS_RC_LEGACY
  fi
  if [ "$mode" != "runtime" ]; then
    echo "LEGACY: la épica ya vive en docs/03-backlog/epicas.md; no hay grafo que proyectar"
    return $OPS_RC_LEGACY
  fi
  command -v python3 >/dev/null 2>&1 || { echo "⛔ sin python3 no se puede escribir el fichero" >&2; return $OPS_RC_OFFLINE; }
  root="$(config_root)"
  [ -n "$target" ] || target="$root/docs/03-backlog/epicas.md"
  # [Ronda final · METODOLOGIA §9.2] `--file` aceptaba CUALQUIER ruta: con eso, un carve-out
  # de escritura acotado a cuatro sitios se convertía en una escritura libre sobre `docs/`, y
  # los Guardrails de /build:epic prometen justo lo contrario. La ruta se restringe al subárbol
  # del backlog (con symlinks y `..` resueltos), y la comprobación va ANTES de la existencia:
  # una ruta fuera del carve-out se rechaza exista o no.
  if [ "$(_epic_writeback_path_ok "$target" "$root/docs/03-backlog")" != "OK" ]; then
    echo "⛔ --file fuera del carve-out: $target" >&2
    echo "  El write-back solo escribe dentro de $root/docs/03-backlog/ (METODOLOGIA §9.2)." >&2
    echo "  Usa esa ruta (o ninguna: por defecto es docs/03-backlog/epicas.md)." >&2
    return $OPS_RC_USAGE
  fi
  if [ ! -f "$target" ]; then
    echo "⛔ no existe $target — el backlog de discovery es su dueño: créalo allí primero." >&2
    return $OPS_RC_NO_SLICE
  fi
  # [Importante 1/2/3] fsync en AMBAS escrituras (epicas.md es un fichero de discovery que
  # el arnés solo toca por carve-out: dejarlo truncado por un corte de energía es exactamente
  # el daño que la restricción prohíbe); epicas.md solo se reescribe si de verdad hay algo que
  # escribir (si no, cada invocación en vacío convertiría CRLF→LF y degradaría los permisos de
  # 0644 a 0600 heredados del `mkstemp` de un fichero AJENO); y si el ledger no se puede
  # persistir, la excepción SUBE (no se traga): reportar éxito con el ledger desincronizado
  # es peor que fallar ruidosamente.
  wrote="$(python3 - "$(ops_epic_ledger_path)" "$target" "$only" <<'PY' 2>/dev/null
import json,sys,os,tempfile,datetime,re
ledger,target,only=sys.argv[1],sys.argv[2],sys.argv[3]
try:
    d=json.load(open(ledger))
except Exception:
    d={}
ps=[p for p in (d.get("proposals") or []) if isinstance(p,dict)]
texto=open(target,encoding="utf-8").read()
escritas=[]
for p in ps:
    if p.get("status")!="APPROVED" or p.get("written_back_at"):
        continue
    if only and p.get("proposal_id")!=only:
        continue
    code=p.get("epic_code")
    if not code:
        continue
    epic=p.get("epic") or p.get("draft") or {}
    # [Ronda final] La sangría permitida se alinea con RE_ENCABEZADO de graph-bundle.py
    # (`^\s{0,3}#{1,6}`): con `#` exigido en columna 0, un encabezado sangrado —que el
    # extractor SÍ reconoce— daba falso negativo y el write-back DUPLICABA la sección.
    if re.search(r"^[ \t]{0,3}#{1,6}\s+.*\b%s\b" % re.escape(code), texto, re.M):
        p["written_back_at"]=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        continue
    deps=[str(x) for x in (epic.get("depends_on") or [])]
    lineas=["", "## %s — %s" % (code, epic.get("title") or "sin título"), "",
            "- layer: %s" % (epic.get("layer") or "business"),
            "- origin: harness-writeback",
            "- depende_de: [%s]" % ", ".join(deps),
            "- propuesta: %s (aprobada en el hub)" % (p.get("proposal_id") or "?"),
            "", "**Objetivo**: %s" % (epic.get("objective") or ""), ""]
    historias=epic.get("stories") or []
    if historias:
        lineas.append("**Historias**")
        for h in historias:
            if not isinstance(h,dict):
                continue
            t=h.get("title") or ""
            c=h.get("code")
            lineas.append("- %s — %s" % (c,t) if c else "- %s" % t)
        lineas.append("")
    texto=texto.rstrip("\n")+"\n"+"\n".join(lineas)
    p["written_back_at"]=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    escritas.append(code)
if escritas:
    dirn=os.path.dirname(target) or "."
    fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".epicas.",suffix=".tmp")
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as out:
            out.write(texto)
            out.flush(); os.fsync(out.fileno())
        os.replace(tmp,target)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
ldir=os.path.dirname(ledger) or "."
fd,tmp=tempfile.mkstemp(dir=ldir,prefix=".epic-proposals.",suffix=".tmp")
try:
    with os.fdopen(fd,"w") as out:
        json.dump({"proposals":ps},out,indent=2,ensure_ascii=False)
        out.flush(); os.fsync(out.fileno())
    os.replace(tmp,ledger)
except Exception:
    try: os.unlink(tmp)
    except OSError: pass
    raise
print(" ".join(escritas))
PY
)"
  rc=$?
  # [Importante 3/4] rc != 0 del heredoc es un fallo de E/S (epicas.md o el ledger no se
  # pudieron escribir), NUNCA "no había trabajo" — un `$wrote` vacío por éxito (rc 0, nada
  # pendiente) y un `$wrote` vacío por excepción (rc != 0) son cosas distintas.
  if [ "$rc" -ne 0 ]; then
    echo "⛔ el write-back no se pudo completar (fallo de E/S al escribir $target o el ledger): reintenta." >&2
    return $OPS_RC_OFFLINE
  fi
  if [ -z "$wrote" ]; then
    echo "nada que escribir: no hay propuestas APPROVED pendientes (consulta \`slice-ops.sh epic-status\`)"
    return $OPS_RC_NO_WORK
  fi
  echo "escritas en $target: $wrote"
  echo "El fichero es una PROYECCIÓN del grafo del hub: no edites el código a mano."
  echo "Las HU sin código las numera discovery (\`/trycore:*\`): el arnés no las inventa."
  return $OPS_RC_OK
}

# ── graph-sync ───────────────────────────────────────────────────────────────────────
# [EP-OR-17] Hasta ahora el grafo del hub dejaba de evolucionar tras el import inicial de
# ADMIN: las épicas que discovery añadía después no tenían por dónde entrar, y TODOS los
# eventos de un slice cuya épica no está en el grafo rebotan con «la épica no existe en el
# grafo del proyecto». Este carril lo cierra sin regalarle al agente la potestad de mutar el
# grafo: el arnés PROPONE el bundle, el hub calcula el delta y un humano aprueba en la consola.

# _graph_sync_bundle <fichero-epics> [from_docs] — imprime el bundle proyectado al contrato,
# o "" con rc 2 (no cumple el contrato) / rc 5 (falta infraestructura local).
_graph_sync_bundle() {
  local f="$1" docs="${2:-}" gb
  gb="$HERE/../../scripts/lib/graph-bundle.py"
  [ -f "$gb" ] || gb="$(config_root)/.claude/scripts/lib/graph-bundle.py"
  if [ ! -f "$gb" ]; then
    echo "⛔ no se encuentra graph-bundle.py: reinstala con \`trycore-build update\`" >&2
    return $OPS_RC_OFFLINE
  fi
  # [Importante] Sin python3 no es "bundle inválido" (rc 2 de uso): es una degradación de
  # infraestructura. Se anuncia con esas palabras para que no se confunda con un backlog mal
  # escrito, que es lo que el agente iría a arreglar.
  command -v python3 >/dev/null 2>&1 || {
    echo "⛔ sin python3: no se puede construir el bundle en local" >&2
    return $OPS_RC_OFFLINE
  }
  if [ -n "$docs" ]; then
    python3 "$gb" --for-sync --from-docs "$docs" < "$f"
  else
    python3 "$gb" --for-sync < "$f"
  fi
}

# _graph_sync_out <respuesta> <clave> — escalar de la respuesta del hub ("" si falta). Acepta
# tanto el cuerpo desnudo como el sobre `{"response": …}` con el que el carril directo guarda
# los acks, que es de donde lo lee este comando.
_graph_sync_out() {
  command -v python3 >/dev/null 2>&1 || { echo ""; return; }
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    r=(d.get("response") if isinstance(d.get("response"),dict) else d) or {}
    v=r.get(sys.argv[1])
    print("" if v is None else (v if isinstance(v,str) else json.dumps(v,ensure_ascii=False)))
except Exception:
    print("")
' "$2" 2>/dev/null
}

# _graph_sync_delta_render <delta-json> — resumen legible del delta que devuelve el hub. Es lo
# que el humano va a aprobar: enseñarlo aquí evita que el agente proponga a ciegas.
_graph_sync_delta_render() {
  command -v python3 >/dev/null 2>&1 || return 0
  printf '%s' "$1" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not isinstance(d,dict):
    raise SystemExit(0)
print("delta propuesto: %d épicas nuevas · %d épicas con cambios · %d historias nuevas · %d historias con cambios"
      % (len(d.get("epics_added") or []), len(d.get("epics_changed") or []),
         len(d.get("stories_added") or []), len(d.get("stories_changed") or [])))
for e in (d.get("epics_added") or [])[:10]:
    print("  + %s %s" % (e.get("code",""), e.get("title","")))
for e in (d.get("epics_changed") or [])[:10]:
    print("  ~ %s (%s)" % (e.get("code",""), ", ".join(sorted((e.get("fields") or {}).keys()))))
' 2>/dev/null
}

cmd_graph_sync() {
  local file="" docs="" dry=0 mode pid bundle rc cid pfile n_epicas
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --from-docs) docs="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --dry-run) dry=1; shift ;;
      *) shift ;;
    esac
  done
  if [ -z "$file" ]; then
    echo "uso: slice-ops.sh graph-sync --file epics.json [--from-docs docs/03-backlog/epicas.md] [--dry-run]" >&2
    echo "  epics.json: {\"epics\":[{code,title,layer,files_scope[],depends_on[],stories[]}]}" >&2
    echo "  lo escribes leyendo docs/03-backlog/epicas.md y las HU-*.md (igual que en /build:onboard)." >&2
    return $OPS_RC_USAGE
  fi
  [ -f "$file" ] || { echo "⛔ no existe el fichero de épicas: $file" >&2; return $OPS_RC_USAGE; }
  [ -z "$docs" ] || [ -f "$docs" ] || { echo "⛔ no existe el documento de épicas: $docs" >&2; return $OPS_RC_USAGE; }

  # El bundle se construye ANTES de mirar el modo: `--dry-run` tiene que servir también en
  # legacy y dual, que es donde más falta hace revisar el grafo antes de registrarse.
  bundle="$(_graph_sync_bundle "$file" "$docs")"
  rc=$?
  if [ $rc -ne 0 ] || [ -z "$bundle" ]; then
    [ $rc -eq $OPS_RC_OFFLINE ] && return $OPS_RC_OFFLINE
    echo "⛔ el bundle no se envía: corrige los docs de discovery y vuelve a intentarlo." >&2
    return $OPS_RC_USAGE
  fi
  if [ "$dry" = 1 ]; then
    printf '%s\n' "$bundle"
    echo "--dry-run: nada se ha enviado. Quita la opción para proponer el re-sync al hub." >&2
    return $OPS_RC_OK
  fi

  mode="$(ops_mode)"
  if [ "$mode" != "runtime" ]; then
    echo "${mode}: el re-sync del grafo solo opera en modo \`runtime\`."
    echo "Con el fichero local como fuente de verdad, el grafo vive en los documentos y entra"
    echo "al hub por el import de admin (\`/build:onboard\`). Usa --dry-run para revisarlo."
    return $OPS_RC_LEGACY
  fi
  pid="$(runtime_field project_id)"
  [ -n "$pid" ] || { echo "⛔ sin project_id en runtime.credentials: corre \`trycore-build init\`" >&2; return $OPS_RC_REJECTED; }

  cid="$(ops_graph_sync_cid)"
  # El cid es determinista, luego REUTILIZABLE: si el ledger se pierde o se limpia, el
  # contador vuelve atrás y el rastro local de un envío anterior con ese mismo cid (su ack o
  # su apartado) seguiría en disco. Leerlo haría que este comando reportara el resultado de
  # una propuesta que NO acaba de enviar. Se retira antes de encolar: el hub sigue
  # deduplicando por cid igualmente, así que borrar el rastro local no duplica nada.
  rm -f "$(runtime_outbox_dir)/acks/${cid}.json" 2>/dev/null
  rm -f "$(runtime_outbox_dir)/rejected/"*"${cid}.json" 2>/dev/null
  pfile="$(ops_tmpjson "{\"bundle\":$bundle}")" || return $OPS_RC_OFFLINE
  # El `1` pide el estampado de `graph_version` AL DESPACHAR: un re-sync que espera en la cola
  # offline debe salir con la versión vigente en ese momento, no con la de ayer. El `$cid` fija
  # la identidad: el reintento tras un 409 la reusa y el hub deduplica.
  cid="$(runtime_enqueue_direct graph_sync_proposed POST "$(ops_path_graph_sync_proposals "$pid")" "$pfile" 1 "$cid")"
  rm -f "$pfile"
  if [ -z "$cid" ]; then
    echo "⛔ no se pudo encolar el re-sync (outbox no escribible): reintenta." >&2
    return $OPS_RC_OFFLINE
  fi
  n_epicas="$(printf '%s' "$bundle" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["epics"]))' 2>/dev/null || echo 0)"
  ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"QUEUED\",\"proposal_id\":null,\"epics\":$n_epicas}"

  _graph_sync_despachar "$cid"
}

# _graph_sync_despachar <cid> — despacha, interpreta el resultado y, ante un grafo rancio,
# refresca la proyección y reintenta UNA vez.
#
# El reintento vive AQUÍ y no en el despachador porque `runtime-client.sh` es agnóstico al
# dominio: no sabe qué es un bundle ni cuándo vale la pena volver a intentarlo. Y re-estampar
# con la versión nueva ES «recalcular el bundle contra la versión que devuelve el hub»: el
# bundle no depende de la versión del grafo, solo el sello que lo acompaña.
_graph_sync_despachar() {
  local cid="$1" intento=1 ack reason id_prop delta
  while :; do
    runtime_dispatch_outbox >/dev/null 2>&1
    ack="$(ops_epic_ack_read "$cid")"
    if [ -n "$ack" ]; then
      if [ "$(_graph_sync_out "$ack" empty_delta)" = "true" ]; then
        # HU-OR-72 E2: no es un error ni una propuesta — el bundle coincide con el grafo
        # vigente. Se cierra la entrada del ledger para que `graph-sync-status` no vaya a
        # preguntar por una propuesta que el hub nunca creó.
        ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"EMPTY_DELTA\"}"
        echo "el grafo del hub ya está al día: no hay cambios que proponer."
        return $OPS_RC_OK
      fi
      id_prop="$(_graph_sync_out "$ack" id)"
      delta="$(_graph_sync_out "$ack" delta)"
      ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"PROPOSED\",\"proposal_id\":$(ops_json_str "$id_prop")}"
      echo "re-sync propuesto: ${id_prop:-sin identificador en la respuesta}"
      [ -n "$delta" ] && _graph_sync_delta_render "$delta"
      echo "Queda en PROPOSED: NADA se ha aplicado al grafo hasta que un humano lo apruebe en"
      echo "la consola del hub. Sigue el veredicto con \`slice-ops.sh graph-sync-status\`."
      return $OPS_RC_OK
    fi
    reason="$(ops_epic_rejected_reason "$cid")"
    if [ -n "$reason" ]; then
      ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":\"FAILED\",\"reason\":$(ops_json_str "$reason")}"
      case "$reason" in
        *"HTTP 404"*|*404*)
          # Anti-oráculo (HU-OR-72 E4): el hub responde lo MISMO para «no existe» y «no es
          # tuyo». Afirmar una de las dos causas mandaría a buscar el problema equivocado.
          echo "⛔ el hub respondió 404. Son dos causas indistinguibles POR DISEÑO: o el proyecto" >&2
          echo "  no existe, o no es el tuyo (el hub no confirma cuál para no filtrar proyectos" >&2
          echo "  ajenos). Verifica el project_id de runtime.credentials y que el hub tenga" >&2
          echo "  la superficie de re-sync (EP-OR-17)." >&2 ;;
        *) echo "⛔ el hub rechazó el re-sync: $reason" >&2 ;;
      esac
      return $OPS_RC_REJECTED
    fi
    # Sigue en la cola. Si fue por grafo rancio, el despachador dejó el marcador de desfase: se
    # refresca la proyección y se reintenta UNA vez con la versión nueva.
    if [ "$intento" = 1 ] && [ -n "$(runtime_graph_status_read)" ] && [ "$(runtime_graph_status_read)" != "{}" ]; then
      intento=2
      echo "⚠ el hub dice que nuestro grafo va rancio: se refresca el contexto y se reintenta una vez." >&2
      agent_context_fetch_and_cache >/dev/null 2>&1 || \
        echo "⚠ no se pudo refrescar /agent/context: el reintento sale con la versión que haya" >&2
      # El despacho lleva mutex y estado de backoff: sin limpiarlo, el segundo intento cedería
      # el turno y el reintento no ocurriría en este proceso.
      rm -f "$(runtime_outbox_dir)/.dispatch-state.json" 2>/dev/null
      continue
    fi
    echo "re-sync encolado: $cid"
    echo "PENDIENTE: se despachará solo (el daemon de heartbeat lo lleva). Sin conexión aún, o el"
    echo "daemon estaba drenando la cola en este instante. \`slice-ops.sh graph-sync-status\` lo sigue."
    return $OPS_RC_OFFLINE
  done
}

# ── graph-sync-status ────────────────────────────────────────────────────────────────
# [EP-OR-17] El motivo del rechazo lo escribe el ADMIN precisamente para que lo lea la terminal
# que propuso: sin este subcomando el veredicto humano se queda en la consola del hub y el
# agente vuelve a proponer exactamente lo mismo. Informativo: rc 0 siempre en runtime, pase lo
# que pase — es una consulta, y fallar aquí no arregla nada.
cmd_graph_sync_status() {
  local only="" mode pid entries n i cid pidv st resp status reason ack
  while [ $# -gt 0 ]; do
    case "$1" in
      --id) only="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  if [ "$mode" != "runtime" ]; then
    echo "${mode}: no hay hub al que preguntar por el re-sync del grafo."
    return $OPS_RC_LEGACY
  fi
  pid="$(runtime_field project_id)"
  entries="$(ops_graph_sync_ledger_read)"
  n="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("proposals") or []))' 2>/dev/null || echo 0)"
  case "$n" in ''|*[!0-9]*) n=0 ;; esac
  if [ "$n" = 0 ]; then
    echo "no hay ninguna propuesta de re-sync registrada en esta terminal."
    echo "Propón una con \`slice-ops.sh graph-sync --file epics.json\`."
    return $OPS_RC_OK
  fi
  i=0
  while [ "$i" -lt "$n" ]; do
    cid="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(json.load(sys.stdin)["proposals"][int(sys.argv[1])].get("client_event_id") or "")' "$i" 2>/dev/null)"
    pidv="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(json.load(sys.stdin)["proposals"][int(sys.argv[1])].get("proposal_id") or "")' "$i" 2>/dev/null)"
    st="$(printf '%s' "$entries" | python3 -c 'import json,sys; print(json.load(sys.stdin)["proposals"][int(sys.argv[1])].get("status") or "")' "$i" 2>/dev/null)"
    i=$((i + 1))
    [ -z "$only" ] || [ "$only" = "$pidv" ] || [ "$only" = "$cid" ] || continue
    if [ -z "$pidv" ]; then
      # Todavía sin identificador del hub: el estado lo dicta el carril directo local, no la red.
      ack="$(ops_epic_ack_read "$cid")"
      reason="$(ops_epic_rejected_reason "$cid")"
      if [ "$st" = "EMPTY_DELTA" ]; then
        echo "$cid  EMPTY_DELTA  (el grafo ya estaba al día: el hub no creó ninguna propuesta)"
      elif [ -n "$reason" ]; then
        echo "$cid  FAILED  $reason"
      elif [ -n "$ack" ]; then
        echo "$cid  PROPOSED (ack recibido, sin identificador legible en la respuesta)"
      else
        echo "$cid  ${st:-QUEUED}  (pendiente de despacho: el daemon de heartbeat la lleva)"
      fi
      continue
    fi
    resp="$(runtime_get "$(ops_path_graph_sync_proposal "$pid" "$pidv")")"
    status="$(runtime_http_status)"
    case "$status" in
      200) _graph_sync_status_render "$cid" "$pidv" "$resp" ;;
      404)
        # HU-OR-73 E5: «no existe» y «es de otro proyecto» son el MISMO cuerpo, bit a bit.
        echo "$pidv  DESCONOCIDA para el hub (o es de otro proyecto: son indistinguibles)" ;;
      *)
        echo "$pidv  ${st:-?}  (el hub no respondió, HTTP $status: se muestra el último estado conocido)" ;;
    esac
  done
  return $OPS_RC_OK
}

# _graph_sync_status_render <cid> <proposal_id> <respuesta> — pinta el veredicto y lo persiste
# en el ledger. La persistencia va aquí y no en el llamador porque el estado del hub SOLO se
# conoce al leer la respuesta: guardarlo fuera obligaría a re-parsearla.
_graph_sync_status_render() {
  local cid="$1" pidv="$2" resp="$3" st reason applied
  st="$(_graph_sync_out "$resp" status)"
  reason="$(_graph_sync_out "$resp" reject_reason)"
  applied="$(_graph_sync_out "$resp" graph_version_applied)"
  case "$st" in
    APPROVED)
      echo "$pidv  APPROVED  (grafo del hub en v${applied:-?})"
      echo "         nada más que hacer: las historias nuevas entran solas al reparto del claim." ;;
    REJECTED)
      echo "$pidv  REJECTED  ${reason:-sin motivo registrado}"
      echo "         corrige los docs de discovery y vuelve a proponer con \`graph-sync\`." ;;
    PROPOSED)
      echo "$pidv  PROPOSED  (esperando aprobación humana en la consola del hub)" ;;
    *)
      echo "$pidv  ${st:-?}" ;;
  esac
  ops_graph_sync_ledger_upsert "{\"client_event_id\":$(ops_json_str "$cid"),\"status\":$(ops_json_str "${st:-PROPOSED}"),\"reject_reason\":$(ops_json_str "$reason"),\"graph_version_applied\":$(ops_json_str "$applied")}"
}

# ── status ───────────────────────────────────────────────────────────────────────────
# Informe local del agente: modo, proyecto (con sus hechos: scaffold/fuente de diseño/
# tipo/caparazón — la línea `hechos:` de abajo solo se emite en `dual`/`runtime`; en
# `legacy` la precondición temprana de /build:slice y /build:work lee el fichero de
# estado directo, no esta línea), slice, gates, wiring, contexto, lease y cola.
# Es INFORMATIVO: rc 0 siempre, pase lo que pase (lo consume /build:status).
cmd_status() {
  local refresh=1 mode sid pend lock age
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-refresh) refresh=0; shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  # [#74] `status` conserva el fallback a propósito — es la herramienta de diagnóstico de un
  # worktree que todavía no se dio de alta, y negarle la lectura lo dejaría a ciegas. Pero se
  # dice en la primera línea de quién es el estado que está mirando: sin el banner, un informe
  # heredado es indistinguible de uno propio, y es exactamente así como se llega a creer que
  # se tiene un lease que en realidad es de otro agente.
  if config_is_inherited_root; then
    echo "identidad:    ⚠ HEREDADA del clon principal ($(config_main_clone_root)) — solo lectura"
    echo "              lo de abajo es el estado de ESE agente, no del tuyo. Antes de reclamar"
    echo "              o reportar: \`slice-ops.sh register\` con un token propio del ADMIN."
  fi
  echo "modo:         $mode"
  if [ "$mode" = "legacy" ]; then
    echo "estado:       el fichero .claude/state/build-state.json es la fuente de verdad (v0.8.5)"
    echo "runtime:      sin credenciales o modo legacy: no hay nada que consultar"
    return $OPS_RC_OK
  fi
  [ "$refresh" = 1 ] && { agent_context_fetch_and_cache >/dev/null 2>&1 || echo "aviso:        no se pudo refrescar /agent/context (se muestra la caché)"; }
  echo "proyecto:     $(runtime_field project_id)  ·  agente: $(runtime_field agent_key)"
  echo "hechos:       scaffold_confirmed=$(projection_get project.scaffold_confirmed false)  ·  design_source_confirmed=$(projection_get project.design_source_confirmed false) (aplica=$(projection_get project.design_source_applies false))  ·  project_kind=$(projection_get project.project_kind "?")  ·  foundation_done=$(projection_get project.foundation_done false)"
  sid="$(ops_slice_id)"
  if [ -z "$sid" ]; then
    echo "slice:        ninguno reclamado"
  else
    echo "slice:        $sid  ·  $(projection_get active_slice.epic_code "?")  ·  fase $(projection_get active_slice.phase "?")"
    echo "gates:        $(projection_get active_slice.gates '{}')"
    echo "wiring:       $(projection_get active_slice.wiring_failing '[]')"
    echo "rama:         $(projection_get active_slice.branch "?")  ·  change: $(projection_get active_slice.openspec_change "?")"
  fi
  lock="$(runtime_lock_manifest_hash)"
  age="$(projection_age_seconds)"
  if projection_is_stale; then
    echo "contexto:     $lock  ⚠ proyección sin refrescar (${age}s)"
  else
    echo "contexto:     $lock  ✓ v$(projection_get context.version "?") (${age}s)"
  fi
  # [#63] La versión de grafo es la foto del BACKLOG. Solo se menciona si el hub versiona:
  # inventarla en una instancia antigua sería ruido sin significado.
  local gv gs gserver
  gv="$(projection_get context.graph_version "")"
  if [ -n "$gv" ]; then
    gs="$(runtime_graph_status_read)"
    gserver="$(printf '%s' "$gs" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("server") or "")' 2>/dev/null)"
    # [Ronda de arreglo 1, Important 3] La comparación es «servidor MAYOR que local», no
    # «distinto»: un marcador de desfase que se quedó pegado con un `server` viejo (porque el
    # carril directo no lo limpiaba al despachar con éxito — ya corregido) podía apuntar a una
    # versión POR DEBAJO de la local, y `!=` mentía diciendo «por detrás» con el local por
    # delante. `2>/dev/null` deja la comparación fail-open si algún valor no es entero.
    if [ -n "$gserver" ] && [ "$gserver" -gt "$gv" ] 2>/dev/null; then
      echo "grafo:        v$gv  ⚠ por detrás del hub (v$gserver): refresca antes de reclamar o proponer"
    else
      echo "grafo:        v$gv"
    fi
  fi
  echo "lease:        expira $(projection_get lease.expires_at "?")"
  local hbf hbstatus
  hbf="$(config_root)/.claude/state/heartbeat-status.json"
  if [ -f "$hbf" ]; then
    grep -q '"lease_lost": *true' "$hbf" 2>/dev/null \
      && echo "              ⚠ lease perdido: haz checkpoint y vuelve a reclamar"
    # [#61] Una caché vieja porque la red está caída NO es lo mismo que una caché vieja
    # porque nadie la pidió: la primera exige no cerrar gates a ciegas.
    if grep -q '"context_stale": *true' "$hbf" 2>/dev/null; then
      hbstatus="$(command -v python3 >/dev/null 2>&1 && python3 - "$hbf" <<'PY' 2>/dev/null
import json,sys
try:
    print(json.load(open(sys.argv[1])).get("last_context_status"))
except Exception:
    print("?")
PY
)"
      echo "              ⚠ el heartbeat no pudo refrescar /agent/context (último intento: ${hbstatus:-?})"
      echo "                se opera con la última proyección buena; no cierres gates a ciegas"
    fi
  fi
  pend="$(find "$(runtime_outbox_dir)" -maxdepth 1 -name '*.json' ! -name '.dispatch-state.json' 2>/dev/null | wc -l | tr -d ' ')"
  echo "cola:         $pend evento(s) pendiente(s) de despacho"
  # [issue #52] outbox/rejected/ era invisible: la cola mostraba 0 pendientes y parecía
  # éxito mientras el hub había descartado eventos (p.ej. un slice_archived sin la cadena
  # de fases). Se reporta el conteo y la razón del rechazo más reciente.
  local rej rejinfo
  rej="$(find "$(runtime_outbox_dir)/rejected" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${rej:-0}" -gt 0 ] 2>/dev/null; then
    echo "rechazados:   ⚠ $rej evento(s) en outbox/rejected/ — el hub los descartó, NO se reenvían"
    rejinfo="$(command -v python3 >/dev/null 2>&1 && python3 - "$(runtime_outbox_dir)/rejected" <<'PY' 2>/dev/null
import json,glob,os,sys
files=sorted(glob.glob(os.path.join(sys.argv[1],"*.json")))
if files:
    try:
        d=json.load(open(files[-1]))
    except Exception:
        d={}
    print("%s — %s" % (d.get("type") or d.get("event_type") or "?",
                       d.get("rejected_reason") or "razón no registrada (apartado por un cliente anterior)"))
PY
)"
    [ -n "$rejinfo" ] && echo "              último: $rejinfo"
    echo "              revisa la causa y re-emite el hecho corregido (un rechazo no se reintenta solo)"
  else
    echo "rechazados:   ninguno"
  fi
  echo "nudges:       $(projection_get nudges '[]')"
  return $OPS_RC_OK
}

# ── helpers para escalate ────────────────────────────────────────────────────────────

# _ops_evidence_json <texto> <fichero> — evidencia para escalate (texto preferentemente,
# fichero si es grande).
_ops_evidence_json() {
  local txt="$1" file="$2"
  if [ -n "$file" ]; then
    ops_json_str_file "$file"
  else
    ops_json_str "$txt"
  fi
}

# ── escalate ─────────────────────────────────────────────────────────────────────────
# Reportar un bloqueo es acto de agente; DECIDIR qué hacer con él es humano (spec §2).
# El evento deja el rastro en el runtime; la resolución se pide por el canal humano.
# La nota de gobierno SOLO se imprime si el evento de verdad quedó registrado (mismo patrón
# de fallo que _fact_machine_emit): un agente jamás debe creer que escaló algo que se perdió.
cmd_escalate() {
  local razon="" file="" gate="" mode sid payload
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --gate) gate="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) [ -z "$razon" ] && razon="$1"; shift ;;
    esac
  done
  if [ -z "$razon" ] && [ -z "$file" ]; then
    echo "uso: slice-ops.sh escalate «razón» | --file F [--gate G]" >&2
    return $OPS_RC_USAGE
  fi
  mode="$(ops_mode)"
  if [ "$mode" = "legacy" ]; then
    echo "LEGACY: no hay runtime donde registrar la escalada; anótala en el PR y habla con el equipo"
    return $OPS_RC_LEGACY
  fi
  # [#44] El catálogo v2 la llama `slice_escalated` y su payload es EXACTAMENTE {cause}
  # (extra="forbid"): gate y fase viajan DENTRO del texto de la causa, no como claves.
  local prefix="" phase tmptxt
  phase="$(projection_get active_slice.phase "")"
  [ -n "$gate" ] && prefix="[gate: ${gate}] "
  [ -n "$phase" ] && prefix="${prefix}[fase: ${phase}] "
  tmptxt="$(mktemp)" || return $OPS_RC_OFFLINE
  { printf '%s' "$prefix"; if [ -n "$file" ] && [ -f "$file" ]; then cat "$file"; else printf '%s' "$razon"; fi; } > "$tmptxt"
  payload="{\"cause\":$(ops_json_str_file "$tmptxt" "$OPS_MAX_TEXT")}"
  rm -f "$tmptxt"
  sid="$(ops_slice_id)"
  # slice_escalated es de ámbito slice (slice_id obligatorio): sin slice el hub lo
  # rechazaría elemento a elemento — mejor un fallo local accionable que ruido en rejected/.
  if [ "$mode" = "runtime" ] && [ -z "$sid" ]; then
    echo "⛔ sin slice activo: slice_escalated exige slice_id (catálogo v2) y el hub rechazaría el evento." >&2
    echo "  Reclama trabajo primero o reporta el bloqueo por el PR / la consola del hub." >&2
    return $OPS_RC_NO_SLICE
  fi
  if ! _ops_emit_event slice_escalated "$payload" "$sid"; then
    echo "⚠ la escalada no se pudo registrar (outbox no escribible u otro fallo local): repórtala por el PR mientras tanto" >&2
    return $OPS_RC_OFFLINE
  fi
  [ "$mode" = "runtime" ] && echo "escalada registrada (evento encolado)"
  echo "La DECISIÓN es humana (gobierno, spec §2): recortar, diferir o desbloquear lo acuerda el equipo"
  echo "en la consola del hub o en el PR. El arnés no decide por ti ni degrada el alcance."
  return $OPS_RC_OK
}

# ── Helpers comunes de los subcomandos que transicionan ──────────────────────────────
# _ops_dual_mirror <event_type> <payload_json> — en `dual` el fichero es primario: la transición
# se manda al espejo con el `epic_code` del estado local. Un fallo del espejo NUNCA bloquea: se
# avisa y se devuelve 0 (queda como discrepancia del comparador, spec §6.1).
#
# [EP-OR-17] El `slice_ref` que se inyectaba DENTRO del payload se ha eliminado: los schemas del
# catálogo son `extra="forbid"` y ese campo era rechazo garantizado. Su información —de qué
# épica es la transición— es justamente el `epic_code` del SOBRE, que ahora sí viaja donde el
# hub lo lee.
_ops_dual_mirror() {
  local event_type="$1" payload="$2" epic pfile rc
  epic="$(ops_local_slice_ref | python3 -c 'import json,sys; print(json.load(sys.stdin).get("epic_code") or "")' 2>/dev/null)"
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OK
  ops_mirror "$event_type" "$pfile" "$epic"
  rc=$?
  rm -f "$pfile"
  [ $rc -eq 0 ] || echo "⚠ transición «${event_type}» no espejada (rc $rc): el comparador dual la marcará" >&2
  return $OPS_RC_OK
}

# _ops_evidence_json — evidencia por fichero (preferida) o por texto corto.
_ops_evidence_json() {
  local ev="$1" evfile="$2"
  if [ -n "$evfile" ]; then ops_json_str_file "$evfile"; else ops_json_str "$ev"; fi
}

# _ops_require_slice — id del slice activo o rc 4 con mensaje accionable.
_ops_require_slice() {
  local sid
  sid="$(ops_slice_id)"
  if [ -z "$sid" ]; then
    echo "⛔ no hay slice activo en la caché de proyección: reclama primero (\`slice-ops.sh claim\`)" >&2
    return $OPS_RC_NO_SLICE
  fi
  echo "$sid"
  return $OPS_RC_OK
}

# _ops_post_or_queue <path> <payload> <tipo_evento> <slice_id> <etiqueta> [queue_payload]
# Camino común de los actos primarios: POST y, si el servidor no está, encolar el hecho.
# Rechazo del servidor (409/422/401/403) => NUNCA se encola (no se reintenta lo rechazado).
# [#44] `queue_payload` (opcional, default = payload): el cuerpo del endpoint síncrono y
# el payload del catálogo pueden diferir (p.ej. el checkpoint lleva slice_id en el body
# de POST /checkpoints, pero el catálogo lo prohíbe dentro del payload del evento).
_ops_post_or_queue() {
  local path="$1" payload="$2" tipo="$3" sid="$4" etiqueta="$5" queue_payload="${6:-$2}" resp status pfile
  resp="$(runtime_post "$path" "$payload")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202)
      agent_context_fetch_and_cache >/dev/null 2>&1
      echo "$etiqueta registrado en el runtime"
      return $OPS_RC_OK ;;
    422)
      echo "⛔ 422 el servidor rechazó $etiqueta: $resp" >&2
      echo "  Compuerta mecánica funcionando: NO reintentes; corrige la causa y vuelve a medir." >&2
      return $OPS_RC_REJECTED ;;
    409)
      echo "⛔ 409 el servidor rechazó $etiqueta (lease perdido o transición ya aplicada): $resp" >&2
      echo "  Haz checkpoint local y vuelve a reclamar antes de seguir." >&2
      return $OPS_RC_REJECTED ;;
    401|403)
      echo "⛔ token inválido o revocado ($status): pide un token nuevo al ADMIN." >&2
      return $OPS_RC_REJECTED ;;
    *)
      pfile="$(ops_tmpjson "$queue_payload")" || { echo "OFFLINE: no se pudo encolar $etiqueta" >&2; return $OPS_RC_OFFLINE; }
      if ops_enqueue_from_file "$tipo" "$pfile" "$sid"; then
        rm -f "$pfile"
        echo "OFFLINE: $etiqueta encolado (tipo protegido, se entrega al reconectar)"
      else
        rm -f "$pfile"
        echo "⚠ OFFLINE: $etiqueta NO se pudo encolar (outbox no escribible u otro fallo local) — se perderá" >&2
      fi
      return $OPS_RC_OFFLINE ;;
  esac
}

# ── phase ────────────────────────────────────────────────────────────────────────────
# [issue #52] El hub modela la fase con `phase_advanced {to}` de ORDEN ESTRICTO
# (domain.py:400-407: solo la fase siguiente exacta) y `slice_archived` exige phase == pr
# (domain.py:499-500). Este subcomando emite la cadena que falte DESDE la fase conocida
# (proyección ∪ cola pendiente, ops_known_phase) HASTA <to>: nada si ya está (idempotente),
# la cadena completa si hay huecos. Va SIEMPRE por la cola en runtime (no hay endpoint
# síncrono de fase) y por el espejo en dual (phase_advanced ∈ TIPOS_DE_ESPEJO del hub).

# _phase_chain_enqueue <sid> <desde_idx> <hasta_idx> — encola phase_advanced por paso.
# rc 0 si toda la cadena quedó encolada; rc 5 si algún eslabón no se pudo encolar (y se
# corta ahí: encolar eslabones posteriores con un hueco delante era rechazo garantizado).
_phase_chain_enqueue() {
  local sid="$1" i="$2" hasta="$3" step pfile
  i=$((i + 1))
  while [ "$i" -le "$hasta" ]; do
    step="$(ops_phase_at "$i")"
    pfile="$(ops_tmpjson "{\"to\":\"$step\"}")" || return $OPS_RC_OFFLINE
    if ! ops_enqueue_from_file phase_advanced "$pfile" "$sid"; then
      rm -f "$pfile"
      echo "⚠ phase_advanced → «${step}» NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
      return $OPS_RC_OFFLINE
    fi
    rm -f "$pfile"
    i=$((i + 1))
  done
  return $OPS_RC_OK
}

# _phase_chain_mirror <desde_idx> <hasta_idx> — espeja la cadena en dual (fichero primario).
# Un rechazo del espejo no bloquea (queda como discrepancia del comparador, spec §6.1).
_phase_chain_mirror() {
  local i="$1" hasta="$2" step
  i=$((i + 1))
  while [ "$i" -le "$hasta" ]; do
    step="$(ops_phase_at "$i")"
    _ops_dual_mirror phase_advanced "{\"to\":\"$step\"}" >/dev/null
    i=$((i + 1))
  done
  return $OPS_RC_OK
}

# _graph_phase_mark <kind> <nombre> — deja una MARCA LOCAL (ventana temporal) para la telemetría
# de tokens por fase/gate (#86, P12-B: `graph-otel-phases.py` la cruza con los eventos OTEL).
# `kind` es `phase` (fases del pipeline) o `gate` (los 9 nodos del timeline del hub). Fail-open
# PURO: nunca afecta al rc ni al flujo; es una escritura de telemetría, no de estado.
_graph_phase_mark() {
  command -v python3 >/dev/null 2>&1 || return 0
  local kind="$1" nombre="$2" epic at root markers
  epic="$(ops_local_slice_ref 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("epic_code") or "")' 2>/dev/null)"
  at="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || return 0
  root="$(config_root 2>/dev/null)" || root="."
  markers="$root/.claude/state/graph-phase-markers.jsonl"
  mkdir -p "$root/.claude/state" 2>/dev/null || return 0
  printf '{"at":"%s","kind":"%s","phase":"%s","epic":"%s","session_id":"%s"}\n' \
    "$at" "$kind" "$nombre" "$epic" "${CLAUDE_SESSION_ID:-}" >> "$markers" 2>/dev/null || true
}

cmd_phase() {
  local to="${1:-}" mode sid base bidx tidx rc
  if [ -z "$to" ]; then
    echo "uso: slice-ops.sh phase <to>   (fases: $OPS_SLICE_PHASES)" >&2
    return $OPS_RC_USAGE
  fi
  tidx="$(ops_phase_idx "$to")"
  if [ "$tidx" -lt 0 ]; then
    echo "⛔ fase desconocida «${to}». Canónicas: $OPS_SLICE_PHASES" >&2
    echo "  (la fase terminal archived no se reporta por aquí: la produce \`slice-ops.sh archive\`)" >&2
    return $OPS_RC_REJECTED
  fi
  _graph_phase_mark phase "$to"   # marca local para la telemetría por fase (P12-B); no afecta al flujo
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: la fase vive en el fichero (active_slice.phase, references/state-protocol.md)"; return $OPS_RC_LEGACY; }
  # La base es la fase que el SERVIDOR conoce: refresco de la proyección a mejor esfuerzo
  # (fail-open: sin red se sigue con la caché y con los pendientes de la cola).
  agent_context_fetch_and_cache >/dev/null 2>&1
  if [ "$mode" = "dual" ]; then
    base="$(ops_known_phase)"
    bidx="$(ops_phase_idx "$base")"; [ "$bidx" -ge 0 ] || bidx=0
    if [ "$bidx" -ge "$tidx" ]; then
      echo "fase «${to}» ya reportada (server-side: ${base}) — nada que emitir"
      return $OPS_RC_OK
    fi
    [ $((tidx - bidx)) -gt 1 ] && echo "⚠ el slice estaba en «${base}» server-side: se espeja la cadena completa hasta «${to}» (orden estricto del hub, sin saltos)"
    _phase_chain_mirror "$bidx" "$tidx"
    echo "fase espejada: ${base} → ${to} ($((tidx - bidx)) transición(es) phase_advanced)"
    return $OPS_RC_OK
  fi
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  base="$(ops_known_phase "$sid")"
  bidx="$(ops_phase_idx "$base")"; [ "$bidx" -ge 0 ] || bidx=0
  if [ "$bidx" -ge "$tidx" ]; then
    echo "fase «${to}» ya reportada (server-side o pendiente en la cola: ${base}) — nada que emitir"
    return $OPS_RC_OK
  fi
  [ $((tidx - bidx)) -gt 1 ] && echo "⚠ el slice estaba en «${base}» server-side: se emite la cadena completa hasta «${to}» (orden estricto del hub, sin saltos)"
  _phase_chain_enqueue "$sid" "$bidx" "$tidx"
  rc=$?
  [ "$rc" = "$OPS_RC_OK" ] || return $rc
  echo "fase reportada: ${base} → ${to} ($((tidx - bidx)) evento(s) phase_advanced encolados; se entregan al reconectar)"
  return $OPS_RC_OK
}

# ── gate ─────────────────────────────────────────────────────────────────────────────
# Un veredicto es un HECHO MEDIDO: acto de agente (spec §2). El nombre del gate y el
# estado se validan en el cliente (compuerta barata, sin round-trip); la compuerta real,
# que conoce el orden y las precondiciones, es el servidor.
cmd_gate() {
  local gate="${1:-}" estado="${2:-}" evfile="" ev="" mode sid evjson payload
  if [ -z "$gate" ] || [ -z "$estado" ]; then
    echo "uso: slice-ops.sh gate <nombre> <pass|fail|na> [--evidence «texto» | --evidence-file F]" >&2
    return $OPS_RC_USAGE
  fi
  shift 2
  while [ $# -gt 0 ]; do
    case "$1" in
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case " $OPS_SLICE_GATES " in
    *" $gate "*) : ;;
    *) echo "⛔ gate desconocido «${gate}». Canónicos: $OPS_SLICE_GATES" >&2; return $OPS_RC_REJECTED ;;
  esac
  case "$estado" in
    pass|fail|na) : ;;
    *) echo "⛔ estado inválido «${estado}» (pass|fail|na)" >&2; return $OPS_RC_REJECTED ;;
  esac
  # [#86 P12-B] Marca la ventana del nodo del timeline (los 9 gates) al cerrarse (pass), en TODOS
  # los modos: es la frontera que usa `graph-otel-phases` para los tokens por fase. No afecta al flujo.
  [ "$estado" = "pass" ] && _graph_phase_mark gate "$gate"
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: escribe el gate en el fichero (references/state-protocol.md)"; return $OPS_RC_LEGACY; }
  # [#44] El hub no tiene veredicto «na»: cualquier verdict ≠ PASS/FAIL es bloqueo
  # (domain.py, invariante 5) — emitirlo era rechazo garantizado. El gate no aplicable
  # simplemente no se reporta; queda documentado en el PR.
  if [ "$estado" = "na" ]; then
    echo "veredicto «na» de «${gate}»: el catálogo del hub no lo admite (solo PASS/FAIL) — no se reporta."
    echo "Documenta la no-aplicabilidad del gate en el PR; en el hub el gate queda sin evaluar."
    return $OPS_RC_OK
  fi
  # [#44] Contrato real del hub: la clave es `verdict` (VerdictIn y el catálogo
  # GateVerdict) y el reducer solo promueve con "PASS"/"FAIL" en MAYÚSCULA
  # (domain.py:423-431) — `status:"pass"` era rechazo en el sync Y en la cola.
  local verdict
  case "$estado" in
    pass) verdict="PASS" ;;
    fail) verdict="FAIL" ;;
  esac
  evjson="$(_ops_evidence_json "$ev" "$evfile")"
  payload="{\"gate\":$(ops_json_str "$gate"),\"verdict\":$(ops_json_str "$verdict"),\"evidence\":$evjson}"
  if [ "$mode" = "dual" ]; then
    _ops_dual_mirror gate_verdict "$payload"
    return $?
  fi
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  _ops_post_or_queue "$(ops_path_verdicts "$sid")" "$payload" gate_verdict "$sid" "el veredicto de «${gate}»"
}

# ── submit ───────────────────────────────────────────────────────────────────────────
cmd_submit() {
  local pr="" change="" mode sid payload
  while [ $# -gt 0 ]; do
    case "$1" in
      --pr-url) pr="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --openspec-change) change="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: el submit no existe en el fichero; sigue el pipeline local"; return $OPS_RC_LEGACY; }
  payload="{\"pr_url\":$(ops_json_str "$pr"),\"openspec_change\":$(ops_json_str "$change")}"
  if [ "$mode" = "dual" ]; then
    _ops_dual_mirror slice_submitted "$payload"
    return $?
  fi
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  # [#44] El catálogo v2 no admite ningún campo en slice_submitted (extra="forbid"):
  # el evento encolado va con payload {} — pr_url/openspec_change solo acompañan el POST
  # síncrono (SubmitIn los ignora) y viven en el PR.
  _ops_post_or_queue "$(ops_path_submit "$sid")" "$payload" slice_submitted "$sid" "el submit del slice" "{}"
}

# ── archive ──────────────────────────────────────────────────────────────────────────
# SIEMPRE por la cola, también con el runtime vivo: `opsx:archive` corre dentro del PR,
# en el momento menos oportuno para una llamada síncrona, y el evento es idempotente por
# `client_event_id`. El tipo está protegido de la cota (Task 1): un archivado no se evicta.
cmd_archive() {
  local pr="" change="" epic="" mode sid payload pfile
  while [ $# -gt 0 ]; do
    case "$1" in
      --pr-url) pr="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --openspec-change) change="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --epic) epic="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: archiva moviendo active_slice a history[] en el fichero"; return $OPS_RC_LEGACY; }
  # [issue #52] Catch-up de fase: `slice_archived` exige phase == pr en el hub
  # (domain.py:499-500) y el orden de fases es estricto — un pipeline que no reportó
  # `phase` dejaba el slice en dor server-side y el archivado caía a rejected/ EN SILENCIO
  # (piloto 2026-08-28: slices «en construcción» con el PR ya mergeado). Antes de emitir el
  # archivado se completa la cadena phase_advanced que falte hasta pr — el workaround del
  # piloto, hecho sistema. Sin refresco de red: la base sale de la caché ∪ cola pendiente
  # (sobre-emitir desde atrás es seguro: el hub aplica el lote en orden y rechaza solo los
  # eslabones ya aplicados, elemento a elemento).
  local base bidx pridx
  pridx="$(ops_phase_idx pr)"
  payload="{\"epic_code\":$(ops_json_str "$epic"),\"openspec_change\":$(ops_json_str "$change"),\"pr_url\":$(ops_json_str "$pr")}"
  if [ "$mode" = "dual" ]; then
    base="$(ops_known_phase)"
    bidx="$(ops_phase_idx "$base")"; [ "$bidx" -ge 0 ] || bidx=0
    if [ "$bidx" -lt "$pridx" ]; then
      echo "⚠ el slice estaba en «${base}» server-side: se espeja la cadena phase_advanced hasta pr antes del archivado"
      _phase_chain_mirror "$bidx" "$pridx"
    fi
    _ops_dual_mirror slice_archived "$payload"
    return $?
  fi
  # [#44] El catálogo v2 no admite ningún campo en slice_archived (extra="forbid") y el
  # tipo es de ámbito slice (slice_id de primer nivel OBLIGATORIO): con --epic/--pr-url
  # en el payload o sin slice el hub rechazaba TODO archivado — payload {} y slice exigido.
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  base="$(ops_known_phase "$sid")"
  bidx="$(ops_phase_idx "$base")"; [ "$bidx" -ge 0 ] || bidx=0
  if [ "$bidx" -lt "$pridx" ]; then
    echo "⚠ el slice estaba en «${base}» server-side: se encola la cadena phase_advanced hasta pr antes del archivado"
    _phase_chain_enqueue "$sid" "$bidx" "$pridx" || return $OPS_RC_OFFLINE
  fi
  pfile="$(ops_tmpjson "{}")" || return $OPS_RC_OFFLINE
  if ops_enqueue_from_file slice_archived "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "slice_archived encolado (se entrega al reconectar; tipo protegido de la cota)"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ slice_archived NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# ── escritura de progreso granular en modo legacy ──────────────────────────────────────
# [D10, ajuste 2026-09-23] wiring/progress/checkpoint dejaban rc 3 en legacy (le pedían al
# modelo editar el JSON a mano); el checklist que sostiene la regla anti-context-rot quedaba
# opcional en la práctica justo en el modo por defecto. `state_atomic_patch` es fail-open y
# SOLO comprueba que el resultado sea un diccionario — no valida contra el schema — así que
# cada función de abajo relee el fichero tras escribir y confirma que el dato quedó puesto.
_ops_state_has_active_slice() {
  python3 -c "import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
sys.exit(0 if isinstance(d.get('active_slice'), dict) else 1)" "$1" 2>/dev/null
}

# ── wiring ───────────────────────────────────────────────────────────────────────────
# El checklist de cableado es el corazón del refresh de contexto: nace `failing` y solo
# pasa a `passing` tras prueba REAL ejecutada. Se emite como eventos del agregado slice
# (spec §4.1-C: el reducer proyecta status + kind/ref/evidence, no solo el status).
cmd_wiring() {
  local accion="${1:-}" mode
  [ -n "$accion" ] && shift
  mode="$(ops_mode)"
  if [ "$mode" = "legacy" ]; then
    case "$accion" in
      seed) _wiring_seed_legacy "$@" ;;
      update) _wiring_update_legacy "$@" ;;
      *) echo "uso: slice-ops.sh wiring seed --file items.json | wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]" >&2
         return $OPS_RC_USAGE ;;
    esac
    return $?
  fi
  case "$accion" in
    seed) _wiring_seed "$@" ;;
    update) _wiring_update "$@" ;;
    *) echo "uso: slice-ops.sh wiring seed --file items.json | wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]" >&2
       return $OPS_RC_USAGE ;;
  esac
}

# _wiring_seed_legacy --file <json array de {item_id, kind, ref}> — reemplaza
# active_slice.wiring_checklist[] entero (mismo contrato que la siembra por eventos: cada
# item nace `failing`). Falla sin escribir si el fichero no tiene items válidos.
_wiring_seed_legacy() {
  local file="" sfile n_items expr
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  [ -n "$file" ] && [ -f "$file" ] || { echo "uso: slice-ops.sh wiring seed --file items.json" >&2; return $OPS_RC_USAGE; }
  command -v python3 >/dev/null 2>&1 || { echo "⚠ sin python3: no se puede sembrar el checklist" >&2; return $OPS_RC_OFFLINE; }
  sfile="$(state_path)"
  [ -f "$sfile" ] || { echo "⛔ no hay build-state.json en este proyecto (\`trycore-build init\` primero)" >&2; return $OPS_RC_NO_SLICE; }
  _ops_state_has_active_slice "$sfile" || { echo "⛔ no hay slice activo en el fichero: abre un slice primero" >&2; return $OPS_RC_NO_SLICE; }
  n_items="$(python3 -c '
import json,sys
try:
    raw=json.load(open(sys.argv[1]))
except Exception:
    raw=[]
if isinstance(raw,dict): raw=raw.get("items") or []
n=0
for it in raw if isinstance(raw,list) else []:
    if isinstance(it,dict) and (it.get("item_id") or it.get("id")): n+=1
print(n)
' "$file" 2>/dev/null || echo 0)"
  if [ "$n_items" = 0 ]; then
    echo "⛔ el checklist no tiene items válidos (item_id obligatorio)" >&2
    return $OPS_RC_REJECTED
  fi
  export _SO_SEED_FILE="$file"
  expr='
import os, json
raw = json.load(open(os.environ["_SO_SEED_FILE"]))
if isinstance(raw, dict):
    raw = raw.get("items") or []
items = []
for it in raw if isinstance(raw, list) else []:
    if not isinstance(it, dict):
        continue
    iid = it.get("item_id") or it.get("id")
    if not iid:
        continue
    kind = it.get("kind") or "integration_point"
    if kind not in ("hu_ac", "integration_point"):
        kind = "integration_point"
    items.append({"id": iid, "kind": kind, "ref": it.get("ref") or iid, "status": "failing"})
sl = d.get("active_slice")
if isinstance(sl, dict) and items:
    sl["wiring_checklist"] = items
'
  state_atomic_patch "$sfile" "$expr"
  unset _SO_SEED_FILE
  if _ops_state_has_active_slice "$sfile" && [ "$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len((d.get('active_slice') or {}).get('wiring_checklist') or []))" "$sfile" 2>/dev/null || echo 0)" != 0 ]; then
    echo "LEGACY: checklist de wiring sembrado en active_slice.wiring_checklist[] (${n_items} items)"
    return $OPS_RC_OK
  fi
  echo "⚠ el checklist no se pudo escribir en el fichero" >&2
  return $OPS_RC_NO_SLICE
}

# _wiring_update_legacy <item_id> <passing|failing> [--kind K] [--ref R] [--evidence T|--evidence-file F]
# Escribe directo en active_slice.wiring_checklist[] del fichero. Si el item ya existe (caso
# normal: lo sembró dor-dod-gatekeeper), actualiza status/evidence; si no existe, lo crea con
# los cuatro campos que el schema exige (id, kind, ref, status) para no dejarlo inválido.
_wiring_update_legacy() {
  local item="${1:-}" estado="${2:-}" kind="" ref="" ev="" evfile="" sfile expr ok
  if [ -z "$item" ] || [ -z "$estado" ]; then
    echo "uso: slice-ops.sh wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]" >&2
    return $OPS_RC_USAGE
  fi
  shift 2
  while [ $# -gt 0 ]; do
    case "$1" in
      --kind) kind="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --ref) ref="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$estado" in
    passing|failing) : ;;
    *) echo "⛔ estado inválido «${estado}» (passing|failing)" >&2; return $OPS_RC_REJECTED ;;
  esac
  [ -n "$evfile" ] && [ -f "$evfile" ] && ev="$(cat "$evfile" 2>/dev/null || echo "$ev")"
  if [ "$estado" = "passing" ] && [ -z "$ev" ]; then
    echo "⚠ marcando «${item}» como passing SIN evidencia: la regla dura exige prueba real ejecutada" >&2
  fi
  sfile="$(state_path)"
  [ -f "$sfile" ] || { echo "⛔ no hay build-state.json en este proyecto (\`trycore-build init\` primero)" >&2; return $OPS_RC_NO_SLICE; }
  _ops_state_has_active_slice "$sfile" || { echo "⛔ no hay slice activo en el fichero: abre un slice primero" >&2; return $OPS_RC_NO_SLICE; }
  export _SO_ITEM="$item" _SO_STATUS="$estado" _SO_KIND="$kind" _SO_REF="$ref" _SO_EV="$ev"
  expr='
import os
item = os.environ.get("_SO_ITEM", "")
estado = os.environ.get("_SO_STATUS", "")
kind = os.environ.get("_SO_KIND", "")
ref = os.environ.get("_SO_REF", "")
ev = os.environ.get("_SO_EV", "")
if kind not in ("hu_ac", "integration_point"):
    kind = ""
sl = d.get("active_slice")
if isinstance(sl, dict):
    wc = sl.setdefault("wiring_checklist", [])
    found = None
    for it in wc:
        if isinstance(it, dict) and it.get("id") == item:
            found = it
            break
    if found is None:
        found = {"id": item, "kind": kind or "integration_point", "ref": ref or item}
        wc.append(found)
    found["status"] = estado
    if kind:
        found["kind"] = kind
    if ref:
        found["ref"] = ref
    if ev:
        found["evidence"] = ev
'
  state_atomic_patch "$sfile" "$expr"
  ok="$(python3 -c "
import json,sys,os
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print('0'); sys.exit()
sl=d.get('active_slice') or {}
wc=sl.get('wiring_checklist') or []
item=os.environ.get('_SO_ITEM'); estado=os.environ.get('_SO_STATUS')
print('1' if any(isinstance(it,dict) and it.get('id')==item and it.get('status')==estado for it in wc) else '0')
" "$sfile" 2>/dev/null)"
  unset _SO_ITEM _SO_STATUS _SO_KIND _SO_REF _SO_EV
  if [ "$ok" = "1" ]; then
    echo "LEGACY: wiring «${item}» → ${estado} (escrito en active_slice.wiring_checklist[])"
    return $OPS_RC_OK
  fi
  echo "⚠ wiring «${item}» no se pudo escribir en el fichero" >&2
  return $OPS_RC_NO_SLICE
}

# _wiring_seed --file <json array de {item_id, kind, ref}>
_wiring_seed() {
  local file="" sid pfile mode
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  [ -n "$file" ] && [ -f "$file" ] || { echo "uso: slice-ops.sh wiring seed --file items.json" >&2; return $OPS_RC_USAGE; }
  command -v python3 >/dev/null 2>&1 || { echo "⚠ sin python3: no se puede sembrar el checklist" >&2; return $OPS_RC_OFFLINE; }
  pfile="$(mktemp)" || return $OPS_RC_OFFLINE
  # El payload se construye leyendo el fichero DENTRO de python3 (nunca por argv) y se
  # normaliza al schema del catálogo v2 [#44]: WiringChecklistItem es {item_id, kind, ref}
  # EXACTO (extra="forbid") — `status` no viaja (cada ítem nace `failing` en el fold del
  # hub; el estado inicial no es negociable) y kind/ref nunca son null (son obligatorios).
  python3 - "$file" > "$pfile" <<'PY' 2>/dev/null
import json,sys
try:
    raw=json.load(open(sys.argv[1]))
except Exception:
    raw=[]
if isinstance(raw,dict):
    raw=raw.get("items") or []
items=[]
for it in raw if isinstance(raw,list) else []:
    if not isinstance(it,dict):
        continue
    iid=it.get("item_id") or it.get("id")
    if not iid:
        continue
    items.append({"item_id":iid,"kind":it.get("kind") or "","ref":it.get("ref") or ""})
print(json.dumps({"items":items},ensure_ascii=False))
PY
  # El hub exige al menos un ítem (WiringChecklistSeeded.items min_length=1): un checklist
  # vacío es rechazo garantizado — se corta aquí, sin encolar.
  local n_items
  n_items="$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1])).get("items") or []))' "$pfile" 2>/dev/null || echo 0)"
  if [ "$n_items" = 0 ]; then
    rm -f "$pfile"
    echo "⛔ el checklist no tiene items válidos (item_id obligatorio): el hub exige al menos uno" >&2
    return $OPS_RC_REJECTED
  fi
  mode="$(ops_mode)"
  if [ "$mode" = "dual" ]; then
    ops_mirror wiring_checklist_seeded "$pfile" \
      "$(ops_local_slice_ref | python3 -c 'import json,sys; print(json.load(sys.stdin).get("epic_code") or "")' 2>/dev/null)" \
      || echo "⚠ siembra de wiring no espejada; el comparador dual la marcará" >&2
    rm -f "$pfile"
    return $OPS_RC_OK
  fi
  sid="$(ops_slice_id)"
  if ops_enqueue_from_file wiring_checklist_seeded "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "checklist de wiring sembrado (evento encolado)"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ checklist de wiring NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# _wiring_update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence T|--evidence-file F]
_wiring_update() {
  local item="${1:-}" estado="${2:-}" kind="" ref="" ev="" evfile="" sid payload pfile mode
  if [ -z "$item" ] || [ -z "$estado" ]; then
    echo "uso: slice-ops.sh wiring update <item_id> <passing|failing> [--kind K] [--ref R] [--evidence-file F]" >&2
    return $OPS_RC_USAGE
  fi
  shift 2
  while [ $# -gt 0 ]; do
    case "$1" in
      --kind) kind="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --ref) ref="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$estado" in
    passing|failing) : ;;
    *) echo "⛔ estado inválido «${estado}» (passing|failing)" >&2; return $OPS_RC_REJECTED ;;
  esac
  if [ "$estado" = "passing" ] && [ -z "$ev" ] && [ -z "$evfile" ]; then
    echo "⚠ marcando «${item}» como passing SIN evidencia: la regla dura exige prueba real ejecutada" >&2
  fi
  payload="{\"item_id\":$(ops_json_str "$item"),\"status\":$(ops_json_str "$estado"),\"kind\":$(ops_json_str "$kind"),\"ref\":$(ops_json_str "$ref"),\"evidence\":$(_ops_evidence_json "$ev" "$evfile")}"
  mode="$(ops_mode)"
  if [ "$mode" = "dual" ]; then
    _ops_dual_mirror wiring_item_updated "$payload"
    return $?
  fi
  sid="$(ops_slice_id)"
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OFFLINE
  if ops_enqueue_from_file wiring_item_updated "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "wiring «${item}» → $estado (evento encolado)"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ wiring «${item}» NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# ── progress ─────────────────────────────────────────────────────────────────────────
# Sustituye a progress_log[]: el event stream ES la bitácora (spec §5.6, el comparador NO
# compara progress_log). Tipo EVICTABLE a propósito: es volumen, no hecho de dominio.
cmd_progress() {
  local nota="" file="" mode sid payload pfile
  while [ $# -gt 0 ]; do
    case "$1" in
      --file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) [ -z "$nota" ] && nota="$1"; shift ;;
    esac
  done
  if [ -z "$nota" ] && [ -z "$file" ]; then
    echo "uso: slice-ops.sh progress «nota» | --file F" >&2
    return $OPS_RC_USAGE
  fi
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { _progress_legacy "$nota" "$file"; return $?; }
  # [#44] Nombre del catálogo v2: `progress_noted` (payload {note}, sin cambio de claves).
  payload="{\"note\":$(_ops_evidence_json "$nota" "$file")}"
  if [ "$mode" = "dual" ]; then
    _ops_dual_mirror progress_noted "$payload"
    return $?
  fi
  sid="$(ops_slice_id)"
  pfile="$(ops_tmpjson "$payload")" || return $OPS_RC_OFFLINE
  if ops_enqueue_from_file progress_noted "$pfile" "$sid"; then
    rm -f "$pfile"
    echo "nota de progreso encolada"
    return $OPS_RC_OK
  fi
  rm -f "$pfile"
  echo "⚠ nota de progreso NO se pudo encolar (outbox no escribible u otro fallo local)" >&2
  return $OPS_RC_OFFLINE
}

# _progress_legacy <nota> <fichero-de-nota> — apendiza {at, by, note} a
# active_slice.progress_log[] (append-only, sobrevive al reset de contexto — §1-bis.1).
_progress_legacy() {
  local nota="$1" file="$2" sfile note ok
  sfile="$(state_path)"
  [ -f "$sfile" ] || { echo "⛔ no hay build-state.json en este proyecto (\`trycore-build init\` primero)" >&2; return $OPS_RC_NO_SLICE; }
  _ops_state_has_active_slice "$sfile" || { echo "⛔ no hay slice activo en el fichero: abre un slice primero" >&2; return $OPS_RC_NO_SLICE; }
  if [ -n "$file" ] && [ -f "$file" ]; then note="$(cat "$file" 2>/dev/null || echo "$nota")"; else note="$nota"; fi
  export _SO_NOTE="$note"
  local expr='
import os, datetime
sl = d.get("active_slice")
if isinstance(sl, dict):
    pl = sl.setdefault("progress_log", [])
    pl.append({
        "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "by": "slice-ops.sh (legacy)",
        "note": os.environ.get("_SO_NOTE", ""),
    })
'
  state_atomic_patch "$sfile" "$expr"
  ok="$(python3 -c "
import json,sys,os
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print('0'); sys.exit()
pl=(d.get('active_slice') or {}).get('progress_log') or []
note=os.environ.get('_SO_NOTE')
print('1' if any(isinstance(it,dict) and it.get('note')==note for it in pl) else '0')
" "$sfile" 2>/dev/null)"
  unset _SO_NOTE
  if [ "$ok" = "1" ]; then
    echo "LEGACY: nota de progreso apendizada en active_slice.progress_log[]"
    return $OPS_RC_OK
  fi
  echo "⚠ la nota de progreso no se pudo escribir en el fichero" >&2
  return $OPS_RC_NO_SLICE
}

# ── checkpoint ───────────────────────────────────────────────────────────────────────
# El checkpoint es lo que permite que OTRO agente continúe tras una caída (protocolo §3
# regla 2). La rama y el commit se leen del repo del PROYECTO, no del cwd de la sesión.
cmd_checkpoint() {
  local nota="" file="" mode sid branch commit payload root
  while [ $# -gt 0 ]; do
    case "$1" in
      --note) nota="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --note-file) file="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { _checkpoint_legacy "$nota" "$file"; return $?; }
  root="$(config_root)"
  branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  commit="$(git -C "$root" rev-parse HEAD 2>/dev/null || echo "")"
  # [#44] Contrato real del hub: la nota se llama `summary` (CheckpointIn, max 1000; el
  # catálogo CheckpointRecorded también). `note` se descartaba en silencio en el sync y
  # era rechazo por extra="forbid" en la cola. Tope 970 + marcador < 1000.
  local sumjson
  if [ -n "$file" ]; then sumjson="$(ops_json_str_file "$file" 970)"; else sumjson="$(ops_json_str "$nota")"; fi
  if [ "$mode" = "dual" ]; then
    payload="{\"branch\":$(ops_json_str "$branch"),\"commit_sha\":$(ops_json_str "$commit"),\"summary\":$sumjson}"
    _ops_dual_mirror checkpoint_recorded "$payload"
    return $?
  fi
  sid="$(_ops_require_slice)" || return $OPS_RC_NO_SLICE
  # El body síncrono lleva slice_id (POST /checkpoints, CheckpointIn); el payload del
  # EVENTO no lo admite (extra="forbid"): el slice_id va de primer nivel en la cola.
  payload="{\"slice_id\":$(ops_json_str "$sid"),\"branch\":$(ops_json_str "$branch"),\"commit_sha\":$(ops_json_str "$commit"),\"summary\":$sumjson}"
  local queue_payload
  queue_payload="{\"branch\":$(ops_json_str "$branch"),\"commit_sha\":$(ops_json_str "$commit"),\"summary\":$sumjson}"
  _ops_post_or_queue "$OPS_PATH_CHECKPOINTS" "$payload" checkpoint_recorded "$sid" "el checkpoint" "$queue_payload"
}

# _checkpoint_legacy <nota> <fichero-de-nota> — registra la continuidad en
# active_slice.session_continuity del fichero (equivalente legacy del checkpoint remoto).
# No toca `critical_recorded`/`auto_continue`: esos los gestiona el auto-handoff de
# context-monitor.sh, no un checkpoint manual.
_checkpoint_legacy() {
  local nota="$1" file="$2" sfile note branch commit root ok
  sfile="$(state_path)"
  [ -f "$sfile" ] || { echo "⛔ no hay build-state.json en este proyecto (\`trycore-build init\` primero)" >&2; return $OPS_RC_NO_SLICE; }
  _ops_state_has_active_slice "$sfile" || { echo "⛔ no hay slice activo en el fichero: abre un slice primero" >&2; return $OPS_RC_NO_SLICE; }
  if [ -n "$file" ] && [ -f "$file" ]; then note="$(cat "$file" 2>/dev/null || echo "$nota")"; else note="$nota"; fi
  root="$(config_root)"
  branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  commit="$(git -C "$root" rev-parse --short HEAD 2>/dev/null || echo "")"
  export _SO_NOTE="$note" _SO_BRANCH="$branch" _SO_COMMIT="$commit"
  local expr='
import os, datetime
sl = d.get("active_slice")
if isinstance(sl, dict):
    sc = sl.setdefault("session_continuity", {})
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    branch = os.environ.get("_SO_BRANCH", "")
    commit = os.environ.get("_SO_COMMIT", "")
    if branch or commit:
        sc["last_session"] = f"{branch}@{commit}"
    sc["stopped_at"] = f"checkpoint manual ({now})"
    note = os.environ.get("_SO_NOTE", "")
    if note:
        sc["resume_hint"] = note
'
  state_atomic_patch "$sfile" "$expr"
  ok="$(python3 -c "
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception:
    print('0'); sys.exit()
sc=(d.get('active_slice') or {}).get('session_continuity') or {}
print('1' if sc.get('stopped_at') else '0')
" "$sfile" 2>/dev/null)"
  unset _SO_NOTE _SO_BRANCH _SO_COMMIT
  if [ "$ok" = "1" ]; then
    echo "LEGACY: checkpoint registrado en active_slice.session_continuity"
    return $OPS_RC_OK
  fi
  echo "⚠ el checkpoint no se pudo escribir en el fichero" >&2
  return $OPS_RC_NO_SLICE
}

# ── register ─────────────────────────────────────────────────────────────────────────
# [#74] Alta EXPLÍCITA de este árbol de trabajo como agente propio.
#
# El caso que lo motiva: dos agentes construyendo dos épicas en la misma máquina, cada uno en
# su worktree. El hub reparte las dos sin objeción — el bloqueo estaba aquí: un worktree sin
# `.claude/state/runtime.credentials` propio hereda el del clon principal por el fallback de
# `config_root()` y trabaja con SU identidad sin decirlo.
#
# Tres decisiones de diseño que no son gratuitas:
#   1. El token entra por STDIN (prompt si hay TTY), jamás por argumento: un `--token` queda
#      en el historial del shell y en `ps`. Por eso `register` es un comando de terminal
#      humano y NO se invoca desde dentro de un claim — los hooks y las tool calls no tienen
#      TTY y un `read` ahí colgaría la llamada.
#   2. Se siembra PRIMERO el fichero local, para que `config_root()` ancle en este árbol antes
#      de cualquier merge. Al revés, `runtime_register` habría hecho upsert del token nuevo
#      sobre el fichero del clon principal, pisándole la identidad al agente que trabaja ahí.
#   3. Se valida que el `agent_key` obtenido DIFIERA del que tiene el principal. El hub no crea
#      identidades en `/agents/register`: el `agent_key` es el `agent_id` que el ADMIN grabó en
#      el token al emitirlo. Mismo token ⇒ mismo agente ⇒ el claim devolvería el trabajo del
#      otro worktree. Un token por agente, siempre.
#
# Ante cualquier fallo se revierte: o el árbol queda con identidad propia y verificada, o
# queda exactamente como estaba. Un fichero de credenciales a medias es peor que ninguno.

# _reg_rollback <fichero> <backup> — deja el fichero local como estaba antes de `register`.
_reg_rollback() {
  local file="$1" backup="$2"
  if [ -n "$backup" ] && [ -f "$backup" ]; then
    cp "$backup" "$file" 2>/dev/null
    rm -f "$backup"
  else
    rm -f "$file"
  fi
}

cmd_register() {
  local url="" force=0 wt main localfile mainfile mainkey newkey token backup="" hv at rc
  while [ $# -gt 0 ]; do
    case "$1" in
      --runtime-url) url="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --force) force=1; shift ;;
      --token|--project-token|--runtime-token)
        echo "⛔ el token NO se pasa por argumento: quedaría en el historial del shell y en \`ps\`." >&2
        echo "   \`register\` lo pide por stdin. Córrelo en un terminal humano." >&2
        return $OPS_RC_USAGE ;;
      *) shift ;;
    esac
  done
  command -v python3 >/dev/null 2>&1 || {
    echo "⛔ register necesita python3 para escribir las credenciales." >&2; return $OPS_RC_OFFLINE; }

  wt="$(config_candidate_root)"
  main="$(config_main_clone_root)"
  localfile="$wt/.claude/state/runtime.credentials"
  mainfile=""
  if [ -n "$main" ] && [ "$main" != "$wt" ]; then mainfile="$main/.claude/state/runtime.credentials"; fi

  if [ -f "$localfile" ] && [ "$force" != 1 ]; then
    echo "este árbol YA tiene identidad propia — no se toca nada:"
    echo "  raíz:      $wt"
    echo "  agente:    $(runtime_credentials_field_at "$localfile" agent_key)"
    echo "  proyecto:  $(runtime_credentials_field_at "$localfile" project_id)"
    echo "(para re-registrarlo con OTRO token: \`register --force\`)"
    return $OPS_RC_OK
  fi

  # La URL no es secreta y es la MISMA del proyecto: se hereda del principal si no se da.
  if [ -z "$url" ]; then
    url="$(runtime_credentials_field_at "$localfile" runtime_url)"
    [ -n "$url" ] || url="$(runtime_credentials_field_at "$mainfile" runtime_url)"
  fi
  case "$url" in
    http://*|https://*) : ;;
    *)
      echo "⛔ no hay runtime_url que usar (ni --runtime-url, ni credenciales del clon principal)." >&2
      echo "   Pásala explícita: \`register --runtime-url https://…\`" >&2
      return $OPS_RC_USAGE ;;
  esac

  mainkey="$(runtime_credentials_field_at "$mainfile" agent_key)"

  if [ -t 0 ]; then
    printf 'Token de agente para este árbol (no se muestra en pantalla): ' >&2
    IFS= read -rs token
    printf '\n' >&2
  else
    IFS= read -r token || token=""
  fi
  token="$(printf '%s' "$token" | tr -d '[:space:]')"
  [ -n "$token" ] || { echo "⛔ token vacío: no se registró nada." >&2; return $OPS_RC_USAGE; }

  # Compuerta barata y decisiva, ANTES de la red: si el token es el del clon principal, el hub
  # devolverá su misma identidad — el `agent_key` va grabado en el token, no se crea al
  # registrar. Preguntarlo por HTTP solo añadiría una llamada al mismo veredicto.
  if [ -n "$mainfile" ] && [ "$token" = "$(runtime_credentials_field_at "$mainfile" project_token)" ]; then
    token=""
    echo "⛔ ese token es la identidad del clon principal: registrarlo aquí daría el MISMO" >&2
    echo "   agent_key y el claim te devolvería el trabajo que ya tiene reclamado el otro árbol." >&2
    echo "   Pide al ADMIN un token con \`agent_id\` distinto (uno por agente)." >&2
    echo "   El fichero del clon principal NO se ha tocado." >&2
    return $OPS_RC_REJECTED
  fi

  if [ -f "$localfile" ]; then
    backup="$(mktemp)" && cp "$localfile" "$backup" 2>/dev/null || backup=""
  fi

  if ! TRYCORE_REGISTER_TOKEN="$token" runtime_credentials_seed_at "$localfile" "$url"; then
    token=""
    _reg_rollback "$localfile" "$backup"
    echo "⛔ no se pudo escribir $localfile — revisa permisos." >&2
    return $OPS_RC_OFFLINE
  fi
  token=""   # el secreto ya está en el fichero 0600: fuera de las variables del shell

  hv="$(harness_version)"
  at="$(harness_asset_types)"
  runtime_register "$hv" "$at"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    _reg_rollback "$localfile" "$backup"
    if [ "$rc" -eq 2 ]; then
      echo "⛔ el hub rechaza esta versión del arnés ($hv): incompatible_version." >&2
      echo "   Actualiza el paquete y repite \`register\`." >&2
      return $OPS_RC_REJECTED
    fi
    case "$(runtime_http_status)" in
      401|403)
        echo "⛔ el hub no acepta ese token (HTTP $(runtime_http_status)): pide al ADMIN uno válido" >&2
        echo "   para este proyecto. Nada quedó escrito." >&2
        return $OPS_RC_REJECTED ;;
      *)
        echo "OFFLINE: no se pudo registrar contra $url (HTTP $(runtime_http_status))." >&2
        echo "  Nada quedó escrito: repite \`register\` cuando haya red." >&2
        return $OPS_RC_OFFLINE ;;
    esac
  fi

  newkey="$(runtime_credentials_field_at "$localfile" agent_key)"
  if [ -z "$newkey" ]; then
    _reg_rollback "$localfile" "$backup"
    echo "⛔ el hub respondió 200 pero sin \`agent_key\`: sin identidad verificable no se da" >&2
    echo "   de alta el árbol. Nada quedó escrito." >&2
    return $OPS_RC_REJECTED
  fi
  if [ -n "$mainkey" ] && [ "$newkey" = "$mainkey" ]; then
    _reg_rollback "$localfile" "$backup"
    echo "⛔ ese token resuelve al MISMO agent_key que el clon principal ($mainkey): no es una" >&2
    echo "   identidad nueva. El \`agent_key\` lo graba el ADMIN en el token al emitirlo —" >&2
    echo "   pide uno con \`agent_id\` distinto. El fichero del clon principal NO se ha tocado." >&2
    return $OPS_RC_REJECTED
  fi
  rm -f "$backup"

  # A partir de aquí `config_root()` ancla en este árbol, y con él TODA la resolución de
  # config: si `build-config.json` no viajó al worktree (no está versionado en el consumidor),
  # `runtime.mode` caería al default `legacy` y el árbol recién dado de alta dejaría de hablar
  # con el hub — el registro habría «funcionado» apagando justo lo que venía a encender. Se
  # copia del principal solo si aquí no hay ninguno: nunca se pisa una config local.
  if [ -n "$main" ] && [ ! -f "$wt/.claude/config/build-config.json" ] \
     && [ -f "$main/.claude/config/build-config.json" ]; then
    mkdir -p "$wt/.claude/config"
    cp "$main/.claude/config/build-config.json" "$wt/.claude/config/build-config.json" 2>/dev/null \
      && echo "  (build-config.json copiado del clon principal: modo $(ops_mode))"
  fi

  echo "árbol dado de alta con identidad propia:"
  echo "  raíz:      $wt"
  echo "  agente:    $newkey"
  echo "  proyecto:  $(runtime_credentials_field_at "$localfile" project_id)"
  [ -n "$mainkey" ] && echo "  (distinto del clon principal: $mainkey — su fichero no se tocó)"
  echo "Desde aquí el claim, los gates y el heartbeat son de ESTE árbol. Siguiente paso:"
  echo "  bash .claude/hooks/build/slice-ops.sh claim"
  return $OPS_RC_OK
}

SUB="${1:-}"
[ $# -gt 0 ] && shift

# [#74] Compuerta de identidad ANTES de despachar. Las operaciones de ESCRITURA — todo lo que
# firma un acto con el `agent_key` o toca la cola/los ledgers — abortan si este árbol heredó la
# identidad del clon principal. Las LECTURAS (`mode`, `next-step`, `status`, los `*-status`)
# quedan fuera a propósito: son el diagnóstico de un worktree que aún no se dio de alta, y
# `status` avisa de quién es el estado que enseña. `register` tampoco entra: es la salida.
case " claim phase gate submit archive wiring progress checkpoint fact propose-asset propose-epic epic-writeback graph-sync escalate " in
  *" $SUB "*) ops_guard_own_identity "$SUB" || exit $? ;;
esac

case "$SUB" in
  mode) ops_mode; exit 0 ;;
  register) cmd_register "$@"; exit $? ;;
  claim) cmd_claim "$@"; exit $? ;;
  next-step) cmd_next_step; exit $? ;;
  phase) cmd_phase "$@"; exit $? ;;
  gate) cmd_gate "$@"; exit $? ;;
  submit) cmd_submit "$@"; exit $? ;;
  archive) cmd_archive "$@"; exit $? ;;
  wiring) cmd_wiring "$@"; exit $? ;;
  progress) cmd_progress "$@"; exit $? ;;
  checkpoint) cmd_checkpoint "$@"; exit $? ;;
  fact) cmd_fact "$@"; exit $? ;;
  propose-asset) cmd_propose_asset "$@"; exit $? ;;
  propose-epic) cmd_propose_epic "$@"; exit $? ;;
  epic-status) cmd_epic_status "$@"; exit $? ;;
  epic-writeback) cmd_epic_writeback "$@"; exit $? ;;
  graph-sync) cmd_graph_sync "$@"; exit $? ;;
  graph-sync-status) cmd_graph_sync_status "$@"; exit $? ;;
  graph-check) cmd_graph_check "$@"; exit $? ;;
  graph-propose) cmd_graph_propose "$@"; exit $? ;;
  graph-apply) cmd_graph_apply "$@"; exit $? ;;
  graph-calibrate) cmd_graph_calibrate "$@"; exit $? ;;
  graph-telemetry) cmd_graph_telemetry "$@"; exit $? ;;
  graph-otel-phases) cmd_graph_otel_phases "$@"; exit $? ;;
  otel-setup) cmd_otel_setup "$@"; exit $? ;;
  status) cmd_status "$@"; exit $? ;;
  escalate) cmd_escalate "$@"; exit $? ;;
  ""|-h|--help|help) usage; exit $OPS_RC_USAGE ;;
  *) echo "subcomando desconocido: $SUB" >&2; usage; exit $OPS_RC_USAGE ;;
esac
