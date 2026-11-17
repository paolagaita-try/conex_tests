#!/usr/bin/env bash
# release-ops.sh — operaciones del OUTER LOOP que conducen las skills [EP-OR-08-C]:
# veredictos del Release Gate y reporte de integración de un miembro del front paralelo.
# NO es un hook registrado: lo invocan `releasing-a-version` y `managing-parallel-front`.
#
# Línea de corte (spec §2): **reportar un hecho medido es acto de agente; decidir es acto
# humano**. Por eso aquí están los veredictos y el reporte de integración, y NO están:
# cerrar la release, planificar/abrir/drenar/cerrar el front, ni publicar contexto — esos
# viven en la consola del hub, con PDP, y las skills se limitan a instruir al humano.
#
#   uso: release-ops.sh <verdict|close-hint|front-integration> …
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-ops.sh"

usage() {
  cat >&2 <<'USAGE'
uso: release-ops.sh <subcomando> [opciones]

  verdict <line> <security|smell|ux|coherence|stack_arch|integration> <pass|fail|na>
          [--evidence T | --evidence-file F]     reporta un veredicto del Release Gate
  close-hint <line>                              recuerda cómo se cierra (acto humano)
  front-integration <front_id> --merge-status <pending|merged|conflict>
          [--resmoke pass|fail] [--evidence T | --evidence-file F]

códigos de salida: 0 ok · 2 uso · 3 legacy · 5 offline · 6 rechazado
                   · 9 identidad heredada (da de alta el worktree: `slice-ops.sh register`)
USAGE
}

# _rel_evidence_json — misma política que en slice-ops: fichero preferido, texto corto si no.
_rel_evidence_json() {
  local ev="$1" evfile="$2"
  if [ -n "$evfile" ]; then ops_json_str_file "$evfile"; else ops_json_str "$ev"; fi
}

# ── verdict ──────────────────────────────────────────────────────────────────────────
cmd_verdict() {
  local line="${1:-}" gate="${2:-}" estado="${3:-}" ev="" evfile="" mode payload resp status rel_status closed_by
  if [ -z "$line" ] || [ -z "$gate" ] || [ -z "$estado" ]; then usage; return $OPS_RC_USAGE; fi
  shift 3
  while [ $# -gt 0 ]; do
    case "$1" in
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case " $OPS_RELEASE_GATES " in
    *" $gate "*) : ;;
    *) echo "⛔ gate de release desconocido «${gate}». Canónicos: $OPS_RELEASE_GATES" >&2
       echo "  (los gates por slice — dor, tdd, journey_smoke… — van por slice-ops.sh gate)" >&2
       return $OPS_RC_REJECTED ;;
  esac
  case "$estado" in
    pass|fail|na) : ;;
    *) echo "⛔ estado inválido «${estado}» (pass|fail|na)" >&2; return $OPS_RC_REJECTED ;;
  esac
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: escribe el gate en releases[] del fichero"; return $OPS_RC_LEGACY; }
  payload="{\"release_line\":$(ops_json_str "$line"),\"gate\":$(ops_json_str "$gate"),\"status\":$(ops_json_str "$estado"),\"verdict\":$(ops_json_str "$(printf %s "$estado" | tr a-z A-Z)"),\"evidence\":$(_rel_evidence_json "$ev" "$evfile")}"
  if [ "$mode" = "dual" ]; then
    # [EP-OR-17] El hub NO tiene canal de espejo para los veredictos de release:
    # `release_verdict_reported` no existe en su catálogo de eventos (`TIPOS_DE_ESPEJO` solo
    # cubre transiciones de slice) y su superficie síncrona es de gobierno humano. Mandarlo era
    # gastar una llamada para recibir un rechazo por elemento y un aviso genérico que mandaba a
    # revisar una red que funcionaba. Se dice lo que pasa y se sigue: el fichero es primario.
    echo "DUAL: veredicto anotado en local. El hub todavía no espeja veredictos de release"
    echo "(no hay tipo en su catálogo): quedará reflejado al pasar a modo \`runtime\`."
    return $OPS_RC_OK
  fi
  resp="$(runtime_post "$(ops_path_release_verdicts "$(ops_urlenc "$line")")" "$payload")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202)
      echo "veredicto de release registrado: $gate=$estado en $line"
      # [A-con-B] El hub auto-cierra la release cuando el ÚLTIMO veredicto de cada uno
      # de los 6 gates canónicos es PASS (closed_by=AUTO_6_OF_6_PASS, queda en el audit
      # trail). Con algún fail/partial el cierre sigue siendo decisión HUMANA en la
      # consola. Fail-open: un hub previo sin release_status cae al recordatorio.
      rel_status="$(printf '%s' "$resp" | python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("release_status") or "")
except Exception:
    print("")' 2>/dev/null)"
      closed_by="$(printf '%s' "$resp" | python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("closed_by") or "")
except Exception:
    print("")' 2>/dev/null)"
      case "$rel_status" in
        PASSED)
          echo "✅ release «${line}» CERRADA por el hub: 6/6 gates PASS (closed_by: ${closed_by:-AUTO_6_OF_6_PASS})." ;;
        FAILED)
          echo "⛔ release «${line}» en FAILED en el hub; los hallazgos bloqueantes se corrigen como slice y se re-mide." ;;
        IN_PROGRESS)
          echo "release aún IN_PROGRESS: el hub auto-cierra al llegar el 6/6 PASS; con algún fail/partial el cierre es decisión humana en la consola (spec §2)." ;;
        *)
          echo "El hub auto-cierra con 6/6 PASS; si algún gate queda en fail, el cierre/decisión es humano en la consola (spec §2)." ;;
      esac
      return $OPS_RC_OK ;;
    422)
      echo "⛔ 422 el servidor rechazó el veredicto: $resp — no reintentes; corrige y vuelve a medir." >&2
      return $OPS_RC_REJECTED ;;
    401|403)
      echo "⛔ token sin permiso para reportar veredictos de release ($status): habla con el ADMIN." >&2
      return $OPS_RC_REJECTED ;;
    *)
      # [#44] SIN fallback offline: `release_gate_verdict` es del agregado `release` y
      # POST /events solo ingiere ámbito slice (slice_id obligatorio y slice existente,
      # progress_service._apply_and_append) o proyecto — el evento encolado era rechazo
      # garantizado al drenar y el veredicto jamás llegaba. Mismo patrón que
      # propose-asset: rc 5 y reintento explícito al reconectar.
      echo "OFFLINE: no se pudo reportar el veredicto de release (status $status) y este acto" >&2
      echo "  no tiene camino por la cola offline. Reintenta cuando haya red:" >&2
      echo "  release-ops.sh verdict $line $gate $estado" >&2
      return $OPS_RC_OFFLINE ;;
  esac
}

# ── close-hint ───────────────────────────────────────────────────────────────────────
# Cero red a propósito: es un recordatorio de gobierno, no una llamada.
cmd_close_hint() {
  local line="${1:-}"
  [ -n "$line" ] || { usage; return $OPS_RC_USAGE; }
  cat <<HINT
Política de cierre de la release «${line}» (A-con-B):
  1. El agente reporta los 6 veredictos con \`release-ops.sh verdict $line <gate> <estado>\`.
  2. El runtime agrega y AUTO-CIERRA en verde: con el último veredicto de los 6 gates
     canónicos en PASS la release pasa a PASSED (closed_by=AUTO_6_OF_6_PASS, audit trail).
  3. Los casos DEGRADADOS (algún fail/partial, deudas por decidir) siguen siendo gobierno
     humano: una persona con permiso decide y cierra en la consola del hub (PDP).
Parciales no promueven; el gobierno humano vive donde hay decisión real, no en el clic.
HINT
  return $OPS_RC_OK
}

# ── front-integration ────────────────────────────────────────────────────────────────
# Cada worktree se registra como AGENTE PROPIO y reporta la integración de SU miembro.
# Planificar, abrir, drenar y cerrar el front siguen siendo humanos.
#
# [#74] «Mismo token de proyecto, agent_key distinto» era falso y estuvo escrito aquí y en la
# skill: el hub NO crea identidad en `POST /agents/register` — el `agent_key` es el `agent_id`
# que el ADMIN grabó en el token al emitirlo. Un token por agente, o los dos worktrees son el
# mismo agente. La compuerta va en el despacho (`ops_guard_own_identity`), no aquí: el
# `[ -n "$akey" ]` de más abajo era inefectivo por construcción — leía la clave vía
# `config_root()`, que en un worktree sin credenciales ya había heredado la del principal, así
# que solo saltaba si el principal TAMPOCO estaba registrado.
cmd_front_integration() {
  local front="${1:-}" merge="" resmoke="" ev="" evfile="" mode akey payload resp status
  [ -n "$front" ] || { usage; return $OPS_RC_USAGE; }
  shift
  while [ $# -gt 0 ]; do
    case "$1" in
      --merge-status) merge="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --resmoke) resmoke="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence) ev="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      --evidence-file) evfile="${2:-}"; [ $# -ge 2 ] && shift 2 || shift ;;
      *) shift ;;
    esac
  done
  case "$merge" in
    pending|merged|conflict) : ;;
    *) echo "⛔ --merge-status debe ser pending|merged|conflict" >&2; return $OPS_RC_REJECTED ;;
  esac
  case "$resmoke" in
    ""|pass|fail) : ;;
    *) echo "⛔ --resmoke debe ser pass|fail" >&2; return $OPS_RC_REJECTED ;;
  esac
  mode="$(ops_mode)"
  [ "$mode" = "legacy" ] && { echo "LEGACY: actualiza parallel_front.members[] en el fichero"; return $OPS_RC_LEGACY; }
  payload="{\"merge_status\":$(ops_json_str "$merge"),\"re_smoke\":{\"status\":$(ops_json_str "$resmoke"),\"evidence\":$(_rel_evidence_json "$ev" "$evfile")}}"
  if [ "$mode" = "dual" ]; then
    # Mismo caso que los veredictos de release: `front_integration_reported` no existe en el
    # catálogo del hub y el agregado `front` no entra por la ingesta espejo.
    echo "DUAL: integración anotada en local. El hub todavía no espeja integraciones de front"
    echo "(no hay tipo en su catálogo): quedará reflejada al pasar a modo \`runtime\`."
    return $OPS_RC_OK
  fi
  akey="$(runtime_field agent_key)"
  [ -n "$akey" ] || {
    echo "⛔ este árbol no tiene \`agent_key\`: da de alta el agente con" >&2
    echo "   \`bash .claude/hooks/build/slice-ops.sh register\` (token propio del ADMIN)." >&2
    return $OPS_RC_REJECTED; }
  resp="$(runtime_post "$(ops_path_front_integration "$(ops_urlenc "$front")" "$(ops_urlenc "$akey")")" "$payload")"
  status="$(runtime_http_status)"
  case "$status" in
    200|201|202) echo "integración reportada: merge_status=$merge re_smoke=${resmoke:-n/a}"; return $OPS_RC_OK ;;
    422) echo "⛔ 422 el servidor rechazó el reporte: $resp" >&2; return $OPS_RC_REJECTED ;;
    401|403) echo "⛔ token sin permiso ($status): habla con el ADMIN." >&2; return $OPS_RC_REJECTED ;;
    *)
      # [#44] SIN fallback offline: `front_integration_reported` NO existe en el catálogo
      # v2 del hub (el hecho del catálogo, `front_member_integrated`, es del agregado
      # `front` y POST /events no lo ingiere) y la superficie síncrona de integración es
      # de gobierno humano (`can_govern_front`). Encolarlo era rechazo garantizado: rc 5
      # y reintento explícito al reconectar (mismo patrón que propose-asset).
      echo "OFFLINE: no se pudo reportar la integración (status $status) y este acto no" >&2
      echo "  tiene camino por la cola offline. Reintenta cuando haya red:" >&2
      echo "  release-ops.sh front-integration $front --merge-status $merge${resmoke:+ --resmoke $resmoke}" >&2
      return $OPS_RC_OFFLINE ;;
  esac
}

SUB="${1:-}"
[ $# -gt 0 ] && shift

# [#74] Reportar la integración de un miembro del front es EL acto por-agente de este fichero
# (la ruta lleva el `agent_key` en el path): desde un árbol con identidad heredada estaría
# firmando por el agente del clon principal. `verdict` queda fuera de la compuerta a propósito
# — un veredicto de release es del proyecto, no del agente, y se reporta desde el árbol
# principal; `close-hint` no toca la red.
case "$SUB" in
  front-integration) ops_guard_own_identity "front-integration" || exit $? ;;
esac

case "$SUB" in
  verdict) cmd_verdict "$@"; exit $? ;;
  close-hint) cmd_close_hint "$@"; exit $? ;;
  front-integration) cmd_front_integration "$@"; exit $? ;;
  ""|-h|--help|help) usage; exit $OPS_RC_USAGE ;;
  *) echo "subcomando desconocido: $SUB" >&2; usage; exit $OPS_RC_USAGE ;;
esac
