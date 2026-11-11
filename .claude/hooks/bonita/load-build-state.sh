#!/usr/bin/env bash
# Origen: trycore-spec-build-harness@062c6fd hooks/build/load-build-state.sh
# load-build-state.sh — SessionStart (después de session-start.sh).
# Inyecta al contexto: rama, fase del arnés, la UNIDAD activa (código, título, fase, gates
# abiertos, cableado pendiente, resume_hint), los nudges del hub y la tabla fase→qué hacer del
# método Bonita (U17) con la fase vigente marcada. Si el último claim fue un micro-work, lo
# rinde a él y a su carril.
# Todo sale de ficheros locales (caché de proyección, caché del claim, estado del heartbeat):
# CERO red. Lo que falte degrada a un texto neutro: jamás rompe el arranque (exit 0 siempre).
# Cambios sobre el original: sin el camino con fichero de estado local (modo servidor siempre,
# U16), vocabulario de unidad y tabla fase→qué hacer.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/lib/runtime-client.sh"
source "$HERE/lib/projection.sh"

cat >/dev/null 2>&1   # consumir el payload del hook (protocolo)
command -v python3 >/dev/null 2>&1 || { echo "🏗️  Arnés Bonita (sin python3: no se puede leer el estado; instala python3)"; exit 0; }

ROOT="$(config_root)"
# `symbolic-ref` primero: en un repo sin commits `rev-parse --abbrev-ref` imprime «HEAD» Y falla,
# y con `|| echo` la línea salía partida en dos.
BRANCH="$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null)" \
  || BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)" || BRANCH="desconocida"

echo "🏗️  Arnés Bonita · modo servidor (el estado de la unidad vive en el IA Hub)"
echo "   Rama: $BRANCH | Fase del arnés: $(projection_get project.harness_phase desconocida)"
if [ -z "$(runtime_url)" ] || [ -z "$(runtime_field project_token)" ]; then
  echo "   ⚠ Hub: sin registrar (no hay credenciales). Alta con un token de agente del ADMIN, por stdin:"
  echo "       trycore-bonita init --token-stdin   ·   o   bash .claude/hooks/bonita/slice-ops.sh register"
fi
ver="$(projection_get context.version "")"
[ -n "$ver" ] && echo "   Contexto sincronizado: v$ver"
if [ -f "$(runtime_projection_path)" ] && projection_is_stale; then
  echo "   ⚠ Proyección local sin refrescar ($(projection_age_seconds)s): el hub no respondió. Los guards siguen operando con esta caché."
fi
if grep -q '"lease_lost": *true' "$ROOT/.claude/state/heartbeat-status.json" 2>/dev/null; then
  echo "   ⚠ Lease perdido: otro agente pudo tomar el trabajo. Haz checkpoint y vuelve a reclamar (/bonita:unidad <código>)."
fi

python3 - "$(runtime_projection_path)" "$(claim_cache_path)" <<'PY' 2>/dev/null || true
import json,sys

def leer(p):
    try:
        d=json.load(open(p))
        return d if isinstance(d,dict) else {}
    except Exception:
        return {}

proj,claim=leer(sys.argv[1]),leer(sys.argv[2])
s=proj.get("active_slice") if isinstance(proj.get("active_slice"),dict) else None

# Tabla fase→qué hacer del método Bonita (Global Constraints del plan 3, U17). Literal: si el
# método cambia, se cambia aquí y en la tabla del plan.
TABLA=[
    ("dor", "DoR de §6.4 (gatekeeper)"),
    ("change", "change OpenSpec con `## Trazabilidad` a `docs/07-bonita/`"),
    ("red", "expectativas primero y fallando: casos del journey por camino de compuerta "
            "(`docs/08-construccion/caminos.md`), inventario esperado de los custodios, pruebas Spock si hay código"),
    ("green", "`tools/arnes.sh generar` + `mvn clean install -Pbundle` hasta que custodios y casos nuevos pasan"),
    ("refactor", "limpiar `docs/08-construccion/` y código propio sin cambiar comportamiento; todo sigue verde"),
    ("smoke", "journey completo (todos los caminos) contra el bundle"),
    ("api", "contratos de proceso (payloads del journey) y, desde la unidad 3, REST API extensions"),
    ("data", "BDM y operaciones contra `bdm.md` y `contratos.md`"),
    ("dod", "DoD de §6.4"),
    ("pr", "PR con el archive de OpenSpec dentro"),
    ("archived", "cierre"),
]

mw = claim if claim.get("work_type")=="micro_work" and claim.get("phase") not in ("done","escalated") else None
if mw:
    print("   Micro-work activo: %s · %s · tipo %s · fase %s · rama %s" % (
        mw.get("micro_work_id"), mw.get("title") or "—", mw.get("kind") or "?", mw.get("phase") or "?", mw.get("branch") or "?"))
    if mw.get("files_scope"):
        print("   Ficheros: %s" % ", ".join(str(x) for x in mw.get("files_scope")))
    print("   Carril (slice-ops.sh): micro-fase <in_progress|pr|done> · micro-checkpoint --branch B --commit SHA [--resumen T]")
    print("                          · micro-escalar --motivo M [--limite L] si desborda sus límites (pasa a propuesta de unidad)")
elif not s or not s.get("slice_id"):
    print("   Unidad activa: ninguna. Reclama la siguiente con /bonita:unidad <código> (o `slice-ops.sh claim`).")
else:
    titulo=s.get("epic_title")
    if not titulo and claim.get("slice_id")==s.get("slice_id"):
        titulo=claim.get("epic_title")
    fase=s.get("phase") or "?"
    print("   Unidad activa: %s · %s · fase %s (slice %s)" % (s.get("epic_code") or "?", titulo or "sin título en caché", fase, s.get("slice_id")))
    # [I3] La decisión humana sobre la última escalada manda sobre todo lo demás al retomar.
    res=s.get("resolution") if isinstance(s.get("resolution"),dict) else {}
    if res.get("decision") or res.get("note"):
        print("   ⚖️  Resolución de la escalada: %s — %s" % (res.get("decision") or "?", res.get("note") or "sin nota"))
        print("       Es la decisión del ADMIN: síguela antes que nada (no repitas lo que se escaló).")
    g=s.get("gates") if isinstance(s.get("gates"),dict) else {}
    abiertos=[k for k,v in g.items() if v is not True]
    print("   Gates abiertos: %s" % (", ".join(abiertos) if abiertos else "ninguno ✅"))
    w=[x for x in (s.get("wiring_failing") or []) if isinstance(x,dict)]
    if w:
        muestra="; ".join("%s%s" % (x.get("item_id"), "(%s)" % x["kind"] if x.get("kind") else "") for x in w[:8])
        extra=" (+%d más)" % (len(w)-8) if len(w)>8 else ""
        print("   ⚠️  Cableado pendiente (%d item/s failing): %s%s" % (len(w), muestra, extra))
        print("       NO declares la unidad terminada mientras queden items failing (verifica con prueba real).")
    subs=s.get("sub_slices_pending") or []
    if subs:
        print("   ⚠️  Sub-unidades pendientes: %s" % ", ".join(str(x) for x in subs))
    if s.get("resume_hint"):
        print("   ▶️  Retomar: %s" % s.get("resume_hint"))
    print("   Qué hacer en cada fase (la vigente va marcada):")
    for f,txt in TABLA:
        print("   %s%-9s %s" % ("▶ " if f==fase else "  ", f, txt))

ns=[n for n in (proj.get("nudges") or []) if isinstance(n,dict) and n.get("message")]
if ns:
    print("   Avisos del hub:")
    for n in ns[:8]:
        print("     💡 %s" % n.get("message"))
PY
exit 0
