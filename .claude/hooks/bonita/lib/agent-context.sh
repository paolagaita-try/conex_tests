#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/lib/agent-context.sh
# agent-context.sh — hidratación de la caché de proyección desde GET /agent/context
# [EP-OR-08-B]. Es la ÚNICA pieza que conoce la forma cruda de la respuesta del servidor:
# la normaliza al esquema documentado del plan (fetched_at/project/active_slice/nudges/
# context/lease) para que guards, renders y nudges dependan solo de ese esquema. Si el
# servidor añade o renombra campos, se toca este fichero y nada más.
# Diseño fail-open: ante red caída o respuesta ilegible, la caché ANTERIOR queda intacta.

# projection.sh trae runtime-client.sh y la ruta de la caché del claim (claim_cache_path), sin red.
source "$(dirname "${BASH_SOURCE[0]}")/projection.sh"

AGENT_CONTEXT_PATH="/agent/context"

# agent_context_normalize <fichero-con-el-json-crudo> — imprime el JSON normalizado
# (o "{}" si es ilegible, con rc 1). El crudo se pasa por FICHERO, no por argv: la
# respuesta puede traer nudges y wiring largos y argv está acotado por ARG_MAX.
agent_context_normalize() {
  local raw_file="$1"
  local out rc
  command -v python3 >/dev/null 2>&1 || { echo "{}"; return 1; }
  # La salida de python3 se captura en vez de dejarla fluir directo a stdout:
  # si el script ya imprimió "{}" y salió con rc 1 (JSON ilegible), no queremos
  # que el manejo de fallo de abajo imprima un segundo "{}" encima (doble salida).
  out="$(python3 - "$raw_file" "$(claim_cache_path)" <<'PY' 2>/dev/null
import json,sys,datetime

def as_dict(x):
    return x if isinstance(x, dict) else {}

def as_list(x):
    return x if isinstance(x, list) else []

def first(*vals):
    for v in vals:
        if v is not None:
            return v
    return None

try:
    raw = as_dict(json.load(open(sys.argv[1])))
except Exception:
    print("{}")
    sys.exit(1)

proj = as_dict(first(raw.get("project"), raw.get("project_facts"), {}))
scaffold = as_dict(proj.get("scaffold"))
ds = as_dict(proj.get("design_source"))
sl = as_dict(first(raw.get("active_slice"), raw.get("slice"), {}))

wiring = []
for w in as_list(first(sl.get("wiring_checklist"), sl.get("wiring"), sl.get("wiring_failing"), [])):
    # [Arnés Bonita] `ActiveSliceOut.wiring_failing` del hub es una lista de IDS (list[str]):
    # leída como dicts, cada item salía con item_id None y el render no nombraba ninguno.
    if isinstance(w, str):
        wiring.append({"item_id": w, "kind": None})
        continue
    w = as_dict(w)
    # Sin `status` se asume failing: la lista `wiring_failing` del servidor ya viene filtrada.
    if w.get("status") in (None, "failing"):
        wiring.append({"item_id": first(w.get("item_id"), w.get("id")), "kind": w.get("kind")})

subs = []
for s in as_list(sl.get("sub_slices")):
    s = as_dict(s)
    if s.get("status") != "done":
        sid = first(s.get("id"), s.get("sub_slice_id"))
        if sid:
            subs.append(sid)

nudges = []
# [Arnés Bonita] `AgentContextOut.nudges` del hub es un OBJETO `NudgesOut` (gates_abiertos,
# slices_sin_reflexion, epicas_sin_release, epicas_aprobadas_sin_reclamar, total), no una
# lista: leído como lista quedaba vacío y ningún nudge llegaba a Stop ni al arranque. Se
# aplana aquí a la forma {kind, message} que consumen reflect-nudge y load-build-state.
raw_nudges = raw.get("nudges")
if isinstance(raw_nudges, dict):
    def codigos(xs):
        return ", ".join(str(as_dict(x).get("epic_code") or "?") for x in xs)
    sin_refl = as_list(raw_nudges.get("slices_sin_reflexion"))
    if sin_refl:
        nudges.append({"kind": "reflect",
                       "message": "%d unidad(es) archivada(s) sin reflexionar: %s" % (len(sin_refl), codigos(sin_refl))})
    for g in as_list(raw_nudges.get("gates_abiertos")):
        g = as_dict(g)
        nudges.append({"kind": "gate_open",
                       "message": "%s: gate %s abierto en fase %s (%s pendiente/s)" % (
                           g.get("epic_code") or "?", g.get("gate") or "?", g.get("phase") or "?", g.get("pendientes", "?"))})
    sin_rel = as_list(raw_nudges.get("epicas_sin_release"))
    if sin_rel:
        nudges.append({"kind": "release_gate",
                       "message": "%d unidad(es) sin release: %s" % (len(sin_rel), codigos(sin_rel))})
    for e in as_list(raw_nudges.get("epicas_aprobadas_sin_reclamar")):
        e = as_dict(e)
        nudges.append({"kind": "info",
                       "message": "unidad aprobada sin reclamar: %s %s" % (e.get("epic_code") or "?", e.get("title") or "")})
    raw_nudges = []
for n in as_list(raw_nudges):
    if isinstance(n, str):
        nudges.append({"kind": "info", "message": n})
    else:
        n = as_dict(n)
        nudges.append({"kind": first(n.get("kind"), n.get("type"), "info"),
                       "message": first(n.get("message"), n.get("text"), "")})

hus = [h for h in as_list(first(sl.get("stories"), sl.get("hus"), [])) if isinstance(h, str)]
ctx = as_dict(raw.get("context"))
lease = as_dict(raw.get("lease"))
checkpoint = as_dict(sl.get("checkpoint")) or None

# [Hub real] `ActiveSliceOut` no trae openspec_change (y el claim lo trae null si el ADMIN importó el grafo):
# se usa el de la caché del claim, que `slice-ops.sh claim` guarda ya resuelto, SOLO si es del mismo slice.
change = sl.get("openspec_change")
if not change and sl:
    try:
        cc = as_dict(json.load(open(sys.argv[2])))
    except Exception:
        cc = {}
    if cc.get("slice_id") and cc.get("slice_id") == first(sl.get("slice_id"), sl.get("id")):
        change = cc.get("openspec_change") or None

# [I3] `ActiveSliceOut.resolution` ({decision, note}) es la decisión humana sobre la última escalada. Una
# instancia que no la mande cae a la del claim del MISMO slice (`TaskClaimOut.resolution`).
resolution = as_dict(sl.get("resolution")) or None
if not resolution and sl:
    try:
        cc = as_dict(json.load(open(sys.argv[2])))
    except Exception:
        cc = {}
    if cc.get("slice_id") and cc.get("slice_id") == first(sl.get("slice_id"), sl.get("id")):
        resolution = as_dict(cc.get("resolution")) or None

out = {
    "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "source": "agent_context",
    "project": {
        "scaffold_confirmed": bool(first(proj.get("scaffold_confirmed"), scaffold.get("confirmed"), False)),
        "design_source_applies": bool(first(proj.get("design_source_applies"), ds.get("applies"), False)),
        "design_source_confirmed": bool(first(proj.get("design_source_confirmed"), ds.get("confirmed"), False)),
        "project_kind": first(proj.get("project_kind"), raw.get("project_kind")),
        "harness_phase": first(proj.get("harness_phase"), raw.get("harness_phase")),
        # `ProjectFactsOut.foundation` del hub es un bool (o None); el original lo esperaba anidado.
        "foundation_done": bool(first(proj.get("foundation_done"),
                                      proj.get("foundation") if isinstance(proj.get("foundation"), bool) else None,
                                      as_dict(proj.get("foundation")).get("done"), False)),
    },
    "active_slice": None if not sl else {
        "slice_id": first(sl.get("slice_id"), sl.get("id")),
        "epic_code": first(sl.get("epic_code"), sl.get("epica")),
        "epic_title": sl.get("epic_title"),
        "hus": hus,
        "phase": sl.get("phase"),
        "gates": as_dict(sl.get("gates")),
        "branch": first(sl.get("branch"), sl.get("branch_base")),
        "openspec_change": change,
        "docs_ref": sl.get("docs_ref"),
        "wiring_failing": wiring,
        "sub_slices_pending": subs,
        "resume_hint": first(sl.get("resume_hint"), as_dict(sl.get("session_continuity")).get("resume_hint")),
        "checkpoint": checkpoint,
        "resolution": resolution,
    },
    "nudges": nudges,
    # [#63] `graph_version` viaja junto al manifest_hash: es la foto del BACKLOG (épicas y sus
    # estados), no la del contexto gobernado. Un hub que no versiona la deja en None y el
    # cliente sigue funcionando exactamente igual que antes (compatibilidad hacia atrás).
    "context": {"manifest_hash": first(ctx.get("manifest_hash"), raw.get("manifest_hash")),
                "version": first(ctx.get("version"), raw.get("context_version")),
                "graph_version": first(ctx.get("graph_version"), raw.get("graph_version"))},
    "lease": {"expires_at": first(lease.get("expires_at"), raw.get("lease_expires_at")),
              "ttl_s": first(lease.get("ttl_s"), raw.get("lease_ttl_s"))},
}
print(json.dumps(out, ensure_ascii=False))
PY
)"
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "{}"
    return 1
  fi
  printf '%s\n' "$out"
  return 0
}

# agent_context_fetch_and_cache — GET /agent/context, normaliza y escribe la caché.
# rc 0 = caché actualizada · 1 = no se pudo TRAER (red caída, status != 200) · 2 = el hub
# respondió 200 pero la respuesta no se pudo normalizar o la proyección no se pudo escribir.
# En ambos fallos la caché anterior NO se toca y los guards siguen operando con ella.
# [#61 · ronda final] El 2 no es cosmético: con un solo rc de fallo, quien diagnostica después
# leía `runtime_http_status` == 200 y anunciaba «no se pudo refrescar (último intento: 200)»,
# que manda a mirar la red cuando el problema está en el disco o en el cuerpo de la respuesta.
# Todos los llamadores ramifican sobre «rc != 0», así que el código nuevo no cambia su flujo.
agent_context_fetch_and_cache() {
  local body status tmp norm rc
  body="$(runtime_get "$AGENT_CONTEXT_PATH")"
  status="$(runtime_http_status)"
  [ "$status" = "200" ] || return 1
  tmp="$(mktemp)" || return 2
  printf '%s' "$body" > "$tmp"
  norm="$(agent_context_normalize "$tmp")"
  rc=$?
  rm -f "$tmp"
  [ $rc -eq 0 ] || return 2
  [ -n "$norm" ] && [ "$norm" != "{}" ] || return 2
  runtime_projection_write "$norm" || return 2
  return 0
}
