#!/usr/bin/env bash
# load-build-state.sh — SessionStart
# Inyecta al contexto: rama actual, harness_phase, slice activo y gates abiertos.
# [EP-OR-08-B] Dos caminos según runtime_mode():
#   - legacy|dual: comportamiento v0.8.5 exacto (el fichero es primario; además sincroniza
#     harness_phase y resetea el guard de handoff por sesión).
#   - runtime: render desde la caché de proyección; NO se sourcea state-io.sh ni se invoca
#     el reconciliador (la maquinaria legacy no se carga en runtime, spec §4.2-E).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"

# render_runtime — pinta el mismo bloque de contexto que el camino legacy, pero con los
# hechos del runtime. Todo lo que falte degrada a un texto neutro: jamás rompe el arranque.
render_runtime() {
  local root branch slice gates wiring subs hint ver age
  root="$(config_root)"
  branch="$(git -C "$root" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'desconocida')"
  echo "🏗️  Arnés de construcción · modo runtime"
  echo "   Rama: $branch | Fase del arnés: $(projection_get project.harness_phase desconocida)"
  ver="$(projection_get context.version "")"
  [ -n "$ver" ] && echo "   Contexto sincronizado: v$ver"
  if projection_is_stale; then
    age="$(projection_age_seconds)"
    echo "   ⚠ Proyección local sin refrescar (${age}s): el runtime no respondió. Los guards siguen operando con esta caché."
  fi
  if [ "$(cat "$root/.claude/state/heartbeat-status.json" 2>/dev/null | grep -c '"lease_lost": true')" != "0" ]; then
    echo "   ⚠ Lease perdido: otro agente pudo tomar el slice. Haz checkpoint y vuelve a reclamar (/build:claim)."
  fi
  slice="$(projection_get active_slice.slice_id "")"
  if [ -z "$slice" ]; then
    echo "   Slice activo: ninguno. Reclama el siguiente con /build:claim (skill building-a-slice)."
    return 0
  fi
  echo "   Slice activo: $(projection_get active_slice.epic_code '?') [$(projection_get active_slice.hus '[]' | tr -d '[]"')] · change=$(projection_get active_slice.openspec_change '—') · fase=$(projection_get active_slice.phase '—')"
  gates="$(projection_get active_slice.gates '{}' | python3 -c 'import json,sys
try: g=json.load(sys.stdin)
except Exception: g={}
abiertos=[k for k,v in g.items() if v is False]
print(", ".join(abiertos) if abiertos else "ninguno ✅")' 2>/dev/null)"
  echo "   Gates pendientes: ${gates:-desconocidos}"
  wiring="$(projection_get active_slice.wiring_failing '[]' | python3 -c 'import json,sys
try: w=json.load(sys.stdin)
except Exception: w=[]
if w:
    # El `kind` solo viaja en el checklist en objeto; la `wiring_failing` del hub son item_ids
    # a secas, así que sin kind se muestra el item_id solo (y no «item(None)»).
    muestra="; ".join(("%s(%s)" % (i.get("item_id"), i.get("kind"))) if i.get("kind")
                      else ("%s" % i.get("item_id")) for i in w[:8])
    extra=" (+%d más)" % (len(w)-8) if len(w)>8 else ""
    print("%d|%s%s" % (len(w), muestra, extra))' 2>/dev/null)"
  if [ -n "$wiring" ]; then
    echo "   ⚠️  Cableado pendiente (${wiring%%|*} item/s failing): ${wiring#*|}"
    echo "       NO declares el slice terminado mientras queden items failing (verifica con prueba real)."
  fi
  subs="$(projection_get active_slice.sub_slices_pending '[]' | tr -d '[]"')"
  [ -n "$subs" ] && echo "   ⚠️  Sub-slices pendientes: $subs"
  hint="$(projection_get active_slice.resume_hint "")"
  [ -n "$hint" ] && echo "   ▶️  Retomar: $hint"
  return 0
}

if [ "$(runtime_mode)" = "runtime" ]; then
  cat >/dev/null 2>&1   # consumir el payload del hook (protocolo)
  render_runtime
  exit 0
fi

# ── A partir de aquí, camino legacy|dual: v0.8.5 exacto ──
source "$HERE/lib/state-io.sh"

# Lee el payload de SessionStart (JSON en stdin) para extraer session_id. Fail-open:
# si no hay stdin o no trae session_id, seguimos sin tocar session_continuity.
payload="$(cat 2>/dev/null || true)"

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
STATE="$(state_path)"
BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'desconocida')"

# Determina la fase real del arnés.
if [ -f "$ROOT/package.json" ]; then PHASE="active"; else PHASE="authoring"; fi

# Ancla el estado a disco antes de leerlo (fail-open; nunca rompe SessionStart).
if [ -f "$STATE" ] && command -v python3 >/dev/null 2>&1; then
  python3 "$(dirname "${BASH_SOURCE[0]}")/reconcile-build-state.py" "$STATE" 2>/dev/null || true
fi

# Reset once-per-SESSION del guard de auto-handoff (A1): si esta sesión (session_id del
# payload de SessionStart) es distinta de la última registrada en session_continuity,
# reabrimos critical_recorded para que context-monitor.sh pueda volver a escribir handoff
# fresco en ESTA sesión. Fail-open: sin stdin/session_id/state, no se toca nada.
if [ -f "$STATE" ] && command -v python3 >/dev/null 2>&1; then
  SESSION_ID="$(printf '%s' "$payload" | python3 -c '
import json,sys
try:
    p=json.load(sys.stdin)
    sid=p.get("session_id","")
    print(sid if isinstance(sid,str) else "")
except Exception:
    print("")
' 2>/dev/null || true)"
  if [ -n "$SESSION_ID" ]; then
    SID_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$SESSION_ID" 2>/dev/null || true)"
    if [ -n "$SID_JSON" ]; then
      state_atomic_patch "$STATE" "
s = d.get('active_slice')
if isinstance(s, dict):
    sc = s.setdefault('session_continuity', {})
    if sc.get('last_session') != $SID_JSON:
        sc['last_session'] = $SID_JSON
        sc['critical_recorded'] = False
"
    fi
  fi
fi

# Sincroniza harness_phase en el estado (si python3 disponible y el archivo existe).
# Escritura ATÓMICA + validada: este hook corre en CADA SessionStart (alta frecuencia,
# headless incluido); una escritura no atómica que se interrumpa truncaría la ÚNICA
# fuente de verdad. Solo escribe si harness_phase cambia; si algo falla, deja el original
# intacto (fail-open) y nunca rompe el SessionStart.
if [ -f "$STATE" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$STATE" "$PHASE" <<'PY' 2>/dev/null || true
import json,sys,os,tempfile
path,phase=sys.argv[1],sys.argv[2]
try:
    with open(path) as fh:
        d=json.load(fh)
    # No escribir si no hay cambio.
    if d.get("harness_phase")==phase:
        sys.exit(0)
    # Validación mínima de forma antes de tocar disco (no relajamos el schema completo,
    # solo evitamos persistir algo que claramente no es un build-state).
    if not isinstance(d,dict) or not all(k in d for k in ("version","harness_phase","active_slice","history","releases")):
        sys.exit(0)
    d["harness_phase"]=phase
    dirn=os.path.dirname(path) or "."
    fd,tmp=tempfile.mkstemp(dir=dirn,prefix=".build-state.",suffix=".tmp")
    try:
        with os.fdopen(fd,"w") as out:
            json.dump(d,out,indent=2,ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp,path)  # sustitución atómica
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
except Exception:
    pass
PY
fi

echo "🏗️  Arnés de construcción"
echo "   Rama: $BRANCH | Fase del arnés: $PHASE"

if [ -f "$STATE" ] && command -v python3 >/dev/null 2>&1; then
  python3 - "$STATE" <<'PY' 2>/dev/null || true
import json,sys
d=json.load(open(sys.argv[1]))
s=d.get("active_slice")
if not s:
    print("   Slice activo: ninguno. Usa la skill building-a-slice para abrir uno (empieza por DoR).")
else:
    g=s.get("gates",{})
    abiertos=[k for k,v in g.items() if v is False]
    hus=", ".join(s.get("hus") or []) or "—"
    print(f"   Slice activo: {s.get('epica')} [{hus}] · change={s.get('openspec_change')} · fase={s.get('phase')}")
    print(f"   Gates pendientes: {', '.join(abiertos) if abiertos else 'ninguno ✅'}")
    # Handoff fino en disco (A1): items de cableado aún FAILING + última bitácora.
    # Una sesión fresca arranca de aquí; mientras queden failing, el cableado NO está hecho.
    failing=[w for w in (s.get("wiring_checklist") or []) if w.get("status")=="failing"]
    if failing:
        muestra="; ".join(f"{w.get('id')}({w.get('kind')})" for w in failing[:8])
        extra=f" (+{len(failing)-8} más)" if len(failing)>8 else ""
        print(f"   ⚠️  Cableado pendiente ({len(failing)} item/s failing): {muestra}{extra}")
        print("       NO declares el slice terminado mientras queden items failing (verifica con prueba real).")
    pend=[ss for ss in (s.get("sub_slices") or []) if ss.get("status")!="done"]
    if pend:
        print(f"   ⚠️  Sub-slices pendientes: {', '.join(ss.get('id') for ss in pend)}")
    log=s.get("progress_log") or []
    if log:
        last=log[-1]
        print(f"   Última bitácora: [{last.get('by')}] {last.get('note')}")
    sc=s.get("session_continuity") or {}
    if sc.get("resume_hint"):
        print(f"   ▶️  Retomar: {sc.get('resume_hint')}" + ("  [auto-continue]" if sc.get("auto_continue") else ""))
    if s.get("branch_drift"):
        drift=s.get("branch_drift") or ""
        # [#79] Rama de mantenimiento (fix/*|chore/*): carril de bugfix, no drift del slice.
        # El reconciliador sigue anotando branch_drift (es verdad); solo cambia cómo se lee.
        if drift.startswith(("fix/","chore/")):
            print(f"   ℹ️  Rama de mantenimiento ({drift}); el slice {s.get('epica')} sigue en pausa en {s.get('branch')}.")
        else:
            print(f"   ⚠️  Rama real ({drift}) != branch del slice ({s.get('branch')}).")
PY
fi

# [#86 P12] Telemetría de tokens por fase: ON por defecto, LOCAL (endpoint localhost; los datos
# se quedan en un fichero del propio proyecto). `--auto` enciende OTEL en settings.json y arranca
# el collector, salvo opt-OUT explícito (`telemetry.otel.enabled:false` en build-config). Corre en
# segundo plano: fire-and-forget y fail-open — NUNCA bloquea ni rompe el arranque de sesión; sin
# docker no hace nada.
_otel="$HERE/../../scripts/lib/otel-setup.py"
[ -f "$_otel" ] || _otel="$(config_root 2>/dev/null)/.claude/scripts/lib/otel-setup.py"
if [ -f "$_otel" ] && command -v python3 >/dev/null 2>&1; then
  _root="$(config_root 2>/dev/null)"
  ( python3 "$_otel" --auto \
      --settings "$_root/.claude/settings.json" \
      --collector-config "$_root/.claude/otel-collector.yaml" \
      --compose "$_root/.claude/otel-compose.yml" \
      --events "$_root/docs/.reviews/otel-api-requests.jsonl" \
      --config "$_root/.claude/config/build-config.json" \
      >/dev/null 2>&1 & ) 2>/dev/null || true
fi
exit 0
