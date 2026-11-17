#!/usr/bin/env python3
"""graph-otel-phases.py — atribuye tokens a cada fase cruzando OTEL con las marcas (#86, P12-B).

La vía exacta de P12 (tokens por fase) necesita dos cosas que ninguna basta sola:
  - las VENTANAS de fase: las marca `slice-ops.sh phase <to>` en
    `.claude/state/graph-phase-markers.jsonl` (`{at, phase, epic, session_id}`);
  - los EVENTOS de API con tokens y timestamp: los emite Claude Code por OpenTelemetry
    (`claude_code.api_request`), que un collector local vuelca a un fichero.

Este script hace el JOIN por tiempo: cada evento cae en la ventana `[inicio_fase, fin_fase)`
que contiene su timestamp, y suma sus tokens en esa fase. La salida es el `--phases`
compatible con `graph-telemetry --epic EP-XXX --phases '{…}'`.

EVENTOS (`--events`, JSONL — una línea por `api_request`). Formato normalizado (contrato del
arnés; el collector OTLP debería emitirlo, o transformarse con jq):
    {"ts":"2026-10-09T12:00:00Z","session_id":"…","input_tokens":100,"output_tokens":50,
     "cache_read_tokens":0,"cache_creation_tokens":0,"cost_usd":0.012}
También se intenta, best-effort, el log OTLP crudo (`timeUnixNano`/`attributes`).

MARCAS (`--markers`, JSONL): `{"at":"…ISO8601…","phase":"dor","epic":"EP-001","session_id":"…"}`.
Se filtran por `--epic` (y `--session` si se da), se ordenan por `at`, y definen las ventanas:
la fase de la marca i va de su `at` al `at` de la i+1; la última se cierra en `--end` (o ahora).

Uso:
    graph-otel-phases.py --epic EP-XXX [--events f.jsonl] [--markers …] [--session S]
                         [--end ISO8601] [--format human|json|phases]

Salida: `--format phases` imprime solo `{"dor":N,…}` (para encadenar a graph-telemetry);
`json` añade el desglose; `human` una tabla. Códigos: 0 ok · 1 entrada ilegible / sin ventanas.
"""
import datetime
import json
import os
import re
import sys

sys.dont_write_bytecode = True

TOKEN_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens")


def parse_ts(v):
    """ISO8601 o epoch (s/ms/µs/ns) → datetime UTC. None si no se puede."""
    if v is None:
        return None
    if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"\d{10,21}", v.strip())):
        n = float(v)
        # Normaliza por magnitud: s(10) ms(13) µs(16) ns(19).
        for umbral, div in ((1e18, 1e9), (1e15, 1e6), (1e12, 1e3), (0, 1)):
            if n >= umbral:
                try:
                    return datetime.datetime.fromtimestamp(n / div, datetime.timezone.utc)
                except (OverflowError, OSError, ValueError):
                    return None
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        try:
            d = datetime.datetime.fromisoformat(s)
            return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return None
    return None


def _otlp_attrs(rec):
    """Aplana los `attributes` de un log record OTLP ([{key,value:{intValue|stringValue…}}])."""
    out = {}
    attrs = rec.get("attributes")
    if isinstance(attrs, list):
        for a in attrs:
            if not isinstance(a, dict):
                continue
            k = a.get("key")
            val = a.get("value")
            if isinstance(val, dict):
                val = next((val[x] for x in ("intValue", "doubleValue", "stringValue",
                                             "boolValue") if x in val), None)
            if k is not None:
                out[k] = val
    elif isinstance(attrs, dict):
        out.update(attrs)
    return out


def expandir_otlp(rec):
    """Aplana un ExportLogsServiceRequest OTLP (`resourceLogs/scopeLogs/logRecords`) a la lista
    de sus logRecords. Si no es OTLP anidado, devuelve [rec] (registro plano / un logRecord suelto).
    Así `graph-otel-phases` lee DIRECTAMENTE el fichero del exportador `file` del collector."""
    if not isinstance(rec, dict):
        return []
    if "resourceLogs" in rec:
        out = []
        for rl in rec.get("resourceLogs") or []:
            for sl in (rl.get("scopeLogs") or rl.get("instrumentationLibraryLogs") or []):
                out.extend(sl.get("logRecords") or sl.get("log_records") or [])
        return out
    return [rec]


def extraer_evento(rec):
    """(ts:datetime, tokens:int, cost:float, session_id:str|None) de un registro, o None."""
    if not isinstance(rec, dict):
        return None
    attrs = _otlp_attrs(rec)
    fuente = {**attrs, **rec}  # las claves planas ganan sobre las de OTLP
    ts = parse_ts(fuente.get("ts") or fuente.get("time") or fuente.get("timestamp")
                  or fuente.get("timeUnixNano") or fuente.get("observedTimeUnixNano"))
    if ts is None:
        return None
    tokens = 0
    tiene = False
    for k in TOKEN_KEYS:
        v = fuente.get(k)
        if v is not None:
            try:
                tokens += int(float(v))
                tiene = True
            except (TypeError, ValueError):
                pass
    if not tiene:
        return None  # no es un evento de uso de tokens
    try:
        cost = float(fuente.get("cost_usd")) if fuente.get("cost_usd") is not None else 0.0
    except (TypeError, ValueError):
        cost = 0.0
    sid = fuente.get("session_id") or fuente.get("session.id")
    return ts, tokens, cost, (sid if isinstance(sid, str) else None)


def leer_jsonl(path):
    filas = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                filas.append(json.loads(ln))
            except ValueError:
                continue
    return filas


def ventanas(marcas, epic, session, end, kind):
    """Lista de (nombre, inicio, fin) desde las marcas de la épica, del `kind` pedido
    (`gate` = los 9 nodos del timeline del hub; `phase` = las fases del pipeline; `all` = todas),
    ordenadas. Cada ventana va de su marca a la siguiente; la última se cierra en `end`."""
    ms = []
    for m in marcas:
        if not isinstance(m, dict) or m.get("epic") != epic:
            continue
        if session and m.get("session_id") and m.get("session_id") != session:
            continue
        mk = m.get("kind") or "phase"
        if kind != "all" and mk != kind:
            continue
        at = parse_ts(m.get("at"))
        ph = m.get("phase")
        if at and isinstance(ph, str):
            ms.append((at, ph))
    ms.sort(key=lambda x: x[0])
    out = []
    for i, (at, ph) in enumerate(ms):
        fin = ms[i + 1][0] if i + 1 < len(ms) else end
        out.append((ph, at, fin))
    return out


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts = {"epic": None, "events": "docs/.reviews/otel-api-requests.jsonl",
            "markers": ".claude/state/graph-phase-markers.jsonl",
            "session": None, "end": None, "kind": "gate", "format": "human"}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--epic", "--events", "--markers", "--session", "--end", "--kind", "--format"):
            if i + 1 >= len(argv):
                print("graph-otel-phases: %s exige un valor" % a, file=sys.stderr)
                return 1
            opts[a[2:]] = argv[i + 1]
            i += 2
            continue
        print("graph-otel-phases: opción desconocida: %s" % a, file=sys.stderr)
        return 1

    if not opts["epic"] or not re.match(r"^EP-[A-Za-z0-9-]+$", opts["epic"]):
        print("graph-otel-phases: --epic EP-XXX es obligatorio", file=sys.stderr)
        return 1
    if opts["kind"] not in ("gate", "phase", "all"):
        print("graph-otel-phases: --kind debe ser gate|phase|all", file=sys.stderr)
        return 1
    if not os.path.isfile(opts["markers"]):
        print("graph-otel-phases: no hay marcas en %s (las emiten `slice-ops.sh phase`/`gate`)"
              % opts["markers"], file=sys.stderr)
        return 1
    if not os.path.isfile(opts["events"]):
        print("graph-otel-phases: no hay eventos OTEL en %s (configura el collector; ver docs)"
              % opts["events"], file=sys.stderr)
        return 1

    end = parse_ts(opts["end"]) if opts["end"] else datetime.datetime.now(datetime.timezone.utc)
    try:
        vs = ventanas(leer_jsonl(opts["markers"]), opts["epic"], opts["session"], end, opts["kind"])
    except (IOError, OSError) as e:
        print("graph-otel-phases: marcas ilegibles: %s" % e, file=sys.stderr)
        return 1
    if not vs:
        print("graph-otel-phases: ninguna marca (%s) para %s" % (opts["kind"], opts["epic"]),
              file=sys.stderr)
        return 1

    try:
        eventos = leer_jsonl(opts["events"])
    except (IOError, OSError) as e:
        print("graph-otel-phases: eventos ilegibles: %s" % e, file=sys.stderr)
        return 1

    # Normaliza los eventos (ts, tokens, cost) una vez, filtrando por sesión.
    evs = []
    for rec in eventos:
        for lr in expandir_otlp(rec):
            ev = extraer_evento(lr)
            if ev is None:
                continue
            ts, tokens, cost, sid = ev
            if opts["session"] and sid and sid != opts["session"]:
                continue
            evs.append((ts, tokens, cost))

    # La PRIMERA ventana se extiende hacia atrás hasta el evento más temprano, para que el trabajo
    # anterior a la primera marca (p.ej. el DoR, antes de cerrar su gate) cuente en el primer nodo.
    if evs:
        min_ev = min(e[0] for e in evs)
        ph0, ini0, fin0 = vs[0]
        if min_ev < ini0:
            vs[0] = (ph0, min_ev, fin0)

    def iso(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    total, orden = {}, []
    for ph, ini, fin in vs:
        if ph not in total:
            total[ph] = {"tokens": 0, "cost_usd": 0.0, "llamadas": 0,
                         "started_at": iso(ini), "ended_at": iso(fin)}
            orden.append(ph)
        else:  # varias marcas del mismo nombre: abarca de la 1ª a la última
            total[ph]["started_at"] = min(total[ph]["started_at"], iso(ini))
            total[ph]["ended_at"] = max(total[ph]["ended_at"], iso(fin))
    sin_ventana = 0
    for ts, tokens, cost in evs:
        colocado = False
        for ph, ini, fin in vs:
            if ini <= ts < fin:
                total[ph]["tokens"] += tokens
                total[ph]["cost_usd"] = round(total[ph]["cost_usd"] + cost, 6)
                total[ph]["llamadas"] += 1
                colocado = True
                break
        if not colocado:
            sin_ventana += 1

    # Estructura RICA por nodo (lista para el hub): {tokens, started_at, ended_at, cost_usd}.
    rich = {ph: {"tokens": total[ph]["tokens"], "started_at": total[ph]["started_at"],
                 "ended_at": total[ph]["ended_at"], "cost_usd": total[ph]["cost_usd"]}
            for ph in orden}
    phases_tokens = {ph: total[ph]["tokens"] for ph in orden if total[ph]["tokens"] > 0}

    if opts["format"] == "phases":
        json.dump(phases_tokens, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    elif opts["format"] == "phases-rich":
        json.dump(rich, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
    elif opts["format"] == "json":
        json.dump({"epic": opts["epic"], "kind": opts["kind"], "phases": rich,
                   "phases_tokens": phases_tokens,
                   "total_tokens": sum(phases_tokens.values()),
                   "eventos_sin_ventana": sin_ventana}, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("graph-otel-phases %s (kind=%s) — tokens por nodo (%d eventos fuera de ventana):"
              % (opts["epic"], opts["kind"], sin_ventana))
        for ph in orden:
            v = total[ph]
            print("  %-16s %8d tokens  %9.4f USD  [%s → %s]"
                  % (ph, v["tokens"], v["cost_usd"], v["started_at"], v["ended_at"]))
        print("  Encadena: graph-telemetry --epic %s --phases '%s'"
              % (opts["epic"], json.dumps(rich, ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
