#!/usr/bin/env bash
# agent-context.sh — hidratación de la caché de proyección desde GET /agent/context
# [EP-OR-08-B]. Es la ÚNICA pieza que conoce la forma cruda de la respuesta del servidor:
# la normaliza al esquema documentado del plan (fetched_at/project/active_slice/nudges/
# context/lease) para que guards, renders y nudges dependan solo de ese esquema. Si el
# servidor añade o renombra campos, se toca este fichero y nada más.
# Diseño fail-open: ante red caída o respuesta ilegible, la caché ANTERIOR queda intacta.

source "$(dirname "${BASH_SOURCE[0]}")/runtime-client.sh"

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
  out="$(python3 - "$raw_file" <<'PY' 2>/dev/null
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
# `foundation` llega en TRES formas y hay que tolerar las tres: el `project_facts` del hub
# (`GET /agent/context`) lo manda como BOOLEANO (`"foundation": true`); un estado/proyección
# legada lo trae como objeto `{"done": bool}`; y algún productor manda ya `foundation_done`
# plano. Antes solo se leía la forma objeto (`as_dict(True).get("done") → None → False`), así
# que el booleano del hub se perdía y el local quedaba en `false` con el hub en `true`.
_foundation = proj.get("foundation")
foundation_done = first(
    proj.get("foundation_done"),
    _foundation if isinstance(_foundation, bool) else None,
    as_dict(_foundation).get("done"),
    False,
)
sl = as_dict(first(raw.get("active_slice"), raw.get("slice"), {}))

wiring = []
for w in as_list(first(sl.get("wiring_checklist"), sl.get("wiring"), sl.get("wiring_failing"), [])):
    # El hub (`GET /agent/context`) manda `wiring_failing` como lista de CADENAS: cada una ES
    # el `item_id` de un item ya filtrado a `failing` (sin `kind` ni `status`). Antes
    # `as_dict("x")` daba `{}` y proyectaba `{item_id: None, kind: None}` → el status mostraba
    # «None(None)» y next-step pedía cablear «None». El `kind` queda None: el contrato de
    # agent/context no lo trae (solo el checklist en objeto lo tiene).
    if isinstance(w, str):
        if w:
            wiring.append({"item_id": w, "kind": None})
        continue
    w = as_dict(w)
    # Objeto (checklist local/mirror): sin `status` se asume failing (la lista ya viene filtrada).
    if w.get("status") in (None, "failing"):
        wiring.append({"item_id": first(w.get("item_id"), w.get("id")), "kind": w.get("kind")})

subs = []
for s in as_list(sl.get("sub_slices")):
    s = as_dict(s)
    if s.get("status") != "done":
        sid = first(s.get("id"), s.get("sub_slice_id"))
        if sid:
            subs.append(sid)

def nudges_from_grouped(g):
    """El hub (contrato `NudgesOut` de `GET /agent/context`) manda los nudges
    AGRUPADOS por tipo, NO como lista plana: `{gates_abiertos[],
    slices_sin_reflexion[], epicas_sin_release[], epicas_aprobadas_sin_reclamar[],
    total}`. Se aplanan aquí al esquema interno `[{kind, message}]` que renderizan
    `reflect-nudge.sh` (`kind=reflect`) y `release-gate-nudge.sh`
    (`kind=release_gate`). Antes el `as_list(dict)` devolvía `[]` y TODO aviso del
    hub se perdía: la sesión nunca veía reflexión pendiente ni Release Gate."""
    out = []
    # Reflexión pendiente -> UN nudge que cuenta los slices. Mismo texto que el
    # render legacy de reflect-nudge.sh, para que runtime y fichero se vean igual.
    sin_reflexion = as_list(g.get("slices_sin_reflexion"))
    if sin_reflexion:
        k = len(sin_reflexion)
        p = "s" if k != 1 else ""
        out.append({"kind": "reflect",
                    "message": "Reflexión pendiente: %d slice%s archivado%s sin capturar aprendizajes." % (k, p, p)})
    # Release Gate -> UN nudge con los códigos. El render antepone "Release Gate
    # sugerido:", así que el mensaje lleva solo el conteo y los códigos.
    sin_release = as_list(g.get("epicas_sin_release"))
    codigos = sorted(c for c in (as_dict(e).get("epic_code") for e in sin_release) if c)
    if codigos:
        k = len(codigos)
        p = "s" if k != 1 else ""
        out.append({"kind": "release_gate",
                    "message": "%d épica%s archivada%s sin auditar desde el último release (%s)." % (k, p, p, ", ".join(codigos))})
    # Sin render dedicado hoy, pero se PRESERVAN tipados (en vez de descartarlos):
    # `slice-ops.sh status` los lista y un render futuro los puede consumir.
    for ga in as_list(g.get("gates_abiertos")):
        ga = as_dict(ga)
        epic = first(ga.get("epic_code"), ga.get("slice_id"), "?")
        gate = first(ga.get("gate"), "?")
        pend = ga.get("pendientes")
        cola = (" (%d pendiente%s)" % (pend, "s" if pend != 1 else "")) if isinstance(pend, int) else ""
        out.append({"kind": "gate_open",
                    "message": "%s: gate '%s' por cerrar%s." % (epic, gate, cola)})
    for ep in as_list(g.get("epicas_aprobadas_sin_reclamar")):
        ep = as_dict(ep)
        code = first(ep.get("epic_code"), "?")
        title = ep.get("title") or ""
        sep = " — %s" % title if title else ""
        out.append({"kind": "epic_unclaimed",
                    "message": "Épica aprobada sin reclamar: %s%s." % (code, sep)})
    return out


raw_nudges = raw.get("nudges")
if isinstance(raw_nudges, dict):
    # Forma canónica del hub (objeto agrupado).
    nudges = nudges_from_grouped(raw_nudges)
else:
    # Compatibilidad: lista plana de strings o de {kind/type, message/text}.
    nudges = []
    for n in as_list(raw_nudges):
        if isinstance(n, str):
            nudges.append({"kind": "info", "message": n})
        else:
            n = as_dict(n)
            nudges.append({"kind": first(n.get("kind"), n.get("type"), "info"),
                           "message": first(n.get("message"), n.get("text"), "")})

# `hus` llega en dos formas: lista de strings (códigos, forma legacy) o la lista `stories`
# del hub/claim con objetos `{code, acceptance_ref}` — de esta se extrae el `code`. Antes solo
# se aceptaban strings, así que las historias del hub (objetos) se descartaban y `hus` salía
# vacío (SessionStart con "[—]" aunque la épica tuviera sus HU).
hus = []
for h in as_list(first(sl.get("stories"), sl.get("hus"), [])):
    if isinstance(h, str):
        if h:
            hus.append(h)
    else:
        code = as_dict(h).get("code") or as_dict(h).get("id")
        if isinstance(code, str) and code:
            hus.append(code)
ctx = as_dict(raw.get("context"))
lease = as_dict(raw.get("lease"))
checkpoint = as_dict(sl.get("checkpoint")) or None

out = {
    "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "source": "agent_context",
    "project": {
        "scaffold_confirmed": bool(first(proj.get("scaffold_confirmed"), scaffold.get("confirmed"), False)),
        "design_source_applies": bool(first(proj.get("design_source_applies"), ds.get("applies"), False)),
        "design_source_confirmed": bool(first(proj.get("design_source_confirmed"), ds.get("confirmed"), False)),
        "project_kind": first(proj.get("project_kind"), raw.get("project_kind")),
        "harness_phase": first(proj.get("harness_phase"), raw.get("harness_phase")),
        "foundation_done": bool(foundation_done),
    },
    "active_slice": None if not sl else {
        "slice_id": first(sl.get("slice_id"), sl.get("id")),
        "epic_code": first(sl.get("epic_code"), sl.get("epica")),
        "epic_title": sl.get("epic_title"),
        "hus": hus,
        "phase": sl.get("phase"),
        "gates": as_dict(sl.get("gates")),
        "branch": first(sl.get("branch"), sl.get("branch_base")),
        "openspec_change": sl.get("openspec_change"),
        "docs_ref": sl.get("docs_ref"),
        "wiring_failing": wiring,
        "sub_slices_pending": subs,
        "resume_hint": first(sl.get("resume_hint"), as_dict(sl.get("session_continuity")).get("resume_hint")),
        "checkpoint": checkpoint,
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
