#!/usr/bin/env python3
"""otel-setup.py — activa la telemetría OTEL del proyecto para la calibración del grafo (#86, P12).

Deja al arnés "con OTEL puesto" en vez de pedírselo a cada persona a mano:
  1. escribe las variables OTEL en `.claude/settings.json` (bloque `env`), de forma idempotente
     y sin pisar el resto de la config;
  2. genera un config de OpenTelemetry Collector (`.claude/otel-collector.yaml`) con receptor OTLP
     y exportador `file` apuntando al fichero de eventos que lee `graph-otel-phases`;
  3. imprime el comando para arrancar el collector.

AVISO DE CONSENTIMIENTO: activar OTEL hace que Claude Code EMITA datos de uso (tokens, coste,
modelo) al endpoint configurado. Por eso es OPT-IN explícito (lo corre el proyecto, no viene
activado por defecto) y `--revert` lo quita.

Uso:
    otel-setup.py [--settings .claude/settings.json] [--events docs/.reviews/otel-api-requests.jsonl]
                  [--endpoint http://localhost:4318] [--collector-config .claude/otel-collector.yaml]
                  [--revert] [--format human|json]

Códigos de salida: 0 ok · 1 error de E/S.
"""
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

COLLECTOR_IMAGE = "otel/opentelemetry-collector-contrib:0.111.0"

OTEL_ENV = {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_LOGS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318",
}


def collector_yaml(events_path, puerto):
    return (
        "# OpenTelemetry Collector — generado por otel-setup.py (#86, P12).\n"
        "# Recibe los eventos OTLP de Claude Code y los vuelca a un fichero que lee\n"
        "# `graph-otel-phases` (formato del exportador `file`, OTLP anidado).\n"
        "receivers:\n"
        "  otlp:\n"
        "    protocols:\n"
        "      http:\n"
        "        endpoint: 0.0.0.0:%d\n"
        "exporters:\n"
        "  file:\n"
        "    path: \"%s\"\n"
        "service:\n"
        "  pipelines:\n"
        "    logs:\n"
        "      receivers: [otlp]\n"
        "      exporters: [file]\n"
    ) % (puerto, events_path)


def compose_yaml(collector_cfg_rel, events_dir_rel, puerto):
    """docker-compose que corre el collector SUPERVISADO (restart: unless-stopped → docker lo
    mantiene vivo). Montajes RELATIVOS al directorio del propio compose (así no hay rutas
    absolutas ni `C:\\` que rompan el YAML o el mapeo host→contenedor). El collector escribe en
    `/data` dentro del contenedor, que es el directorio de eventos del host montado ahí."""
    return (
        "# docker-compose generado por otel-setup.py (#86, P12). Collector supervisado:\n"
        "#   docker compose -f .claude/otel-compose.yml up -d\n"
        "services:\n"
        "  otelcol:\n"
        "    image: %s\n"
        "    restart: unless-stopped\n"
        "    command: [\"--config=/etc/otelcol-config.yaml\"]\n"
        "    ports: [\"%d:%d\"]\n"
        "    volumes:\n"
        "      - \"%s:/etc/otelcol-config.yaml:ro\"\n"
        "      - \"%s:/data\"\n"
    ) % (COLLECTOR_IMAGE, puerto, puerto, collector_cfg_rel, events_dir_rel)


def _docker():
    """Devuelve el invocador de docker compose disponible, o None."""
    if shutil.which("docker"):
        return ["docker", "compose"]
    return None


def _compose(compose_path, *args, timeout=120):
    """Ejecuta `docker compose -f <compose> <args>`; (rc, salida). (-1,'') si no hay docker."""
    dc = _docker()
    if dc is None or not os.path.isfile(compose_path):
        return -1, ""
    try:
        p = subprocess.run(dc + ["-f", compose_path] + list(args),
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return -2, str(e)


def _compose_detached(compose_path):
    """`docker compose up -d` SIN esperar (fire-and-forget): para el SessionStart, que no debe
    bloquearse con la primera descarga de la imagen. True si lo lanzó."""
    dc = _docker()
    if dc is None or not os.path.isfile(compose_path):
        return False
    try:
        subprocess.Popen(dc + ["-f", compose_path, "up", "-d"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def gestionar_collector(opts):
    """start/stop/status/ensure del collector vía docker compose. SIEMPRE fail-open (rc 0): no
    debe tumbar una sesión — `--ensure` lo llama el hook de SessionStart."""
    compose = opts["compose"]
    if opts["status"]:
        rc, out = _compose(compose, "ps", timeout=30)
        print("otel-setup: collector no gestionable (sin docker o sin %s)." % compose
              if rc == -1 else (out.strip() or "(sin salida)"))
        return 0
    if opts["stop"]:
        rc, _ = _compose(compose, "down", timeout=60)
        print("otel-setup: collector detenido." if rc == 0
              else "otel-setup: no se pudo detener (sin docker/compose o error).")
        return 0
    # `--ensure` (lo llama el SessionStart): fire-and-forget, NUNCA bloquea el arranque de sesión.
    if opts["ensure"]:
        if not os.path.isfile(compose):
            return 0  # sin opt-in (no hay compose): silencioso
        _compose_detached(compose)
        return 0
    # `--start` (acción explícita del usuario): espera (la 1ª vez baja la imagen) y reporta.
    rc, out = _compose(compose, "up", "-d", timeout=300)
    if rc == -1:
        print("otel-setup: no se pudo arrancar el collector (sin docker o sin %s). "
              "Arráncalo a mano con el comando que imprime `otel-setup`." % compose)
    elif rc == 0:
        print("otel-setup: collector arriba (docker compose up -d, supervisado en 4318).")
    else:
        print("otel-setup: docker compose falló: %s" % (out.strip()[:300]))
    return 0  # fail-open siempre


def cargar_settings(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (IOError, OSError, ValueError):
        return {}


def construir_env(endpoint):
    e = dict(OTEL_ENV)
    e["OTEL_EXPORTER_OTLP_ENDPOINT"] = endpoint
    return e


def escribir_collector_files(opts):
    """Escribe el collector config (exporta a /data) y el docker-compose (bind-mounts relativos).
    Devuelve (collector_path, compose_path) o (None, None) si falla."""
    puerto = 4318
    ep = opts["endpoint"].rsplit(":", 1)
    if len(ep) == 2 and ep[1].split("/")[0].isdigit():
        puerto = int(ep[1].split("/")[0])
    events_dir = os.path.dirname(opts["events"]) or "."
    compose_dir = os.path.dirname(opts["compose"]) or "."

    def rel_mount(p):
        r = os.path.relpath(p, compose_dir).replace("\\", "/")
        return r if r.startswith((".", "/")) else "./" + r  # `./` → bind-mount, no volumen

    container_events = "/data/" + os.path.basename(opts["events"])
    try:
        for p in (opts["collector-config"], opts["compose"]):
            dd = os.path.dirname(p)
            if dd:
                os.makedirs(dd, exist_ok=True)
        os.makedirs(events_dir, exist_ok=True)
        with open(opts["collector-config"], "w", encoding="utf-8") as fh:
            fh.write(collector_yaml(container_events, puerto))
        with open(opts["compose"], "w", encoding="utf-8") as fh:
            fh.write(compose_yaml(rel_mount(opts["collector-config"]), rel_mount(events_dir), puerto))
        return opts["collector-config"], opts["compose"]
    except (IOError, OSError) as e:
        print("otel-setup: no se pudo escribir el config/compose del collector: %s" % e,
              file=sys.stderr)
        return None, None


def _config_otel_desactivado(paths):
    """True solo si algún build-config declara `telemetry.otel.enabled == false` (opt-OUT
    explícito). Por defecto (ausente) la telemetría LOCAL está encendida."""
    for p in paths:
        if p and os.path.isfile(p):
            try:
                c = json.load(open(p, encoding="utf-8"))
            except (IOError, OSError, ValueError):
                continue
            t = (((c or {}).get("telemetry") or {}).get("otel") or {})
            if isinstance(t, dict) and t.get("enabled") is False:
                return True
    return False


def auto_setup(opts):
    """Lo llama el SessionStart: enciende la telemetría OTEL LOCAL por defecto (endpoint
    localhost; los datos se quedan en el fichero del proyecto) y arranca el collector. Opt-OUT
    con `telemetry.otel.enabled:false` en build-config. Idempotente y FAIL-OPEN: nunca bloquea
    ni rompe la sesión, y solo reescribe settings.json si de verdad cambia algo."""
    cfgs = [opts.get("config"), "config/build-config.json", ".claude/config/build-config.json"]
    if _config_otel_desactivado(cfgs):
        return 0
    settings = cargar_settings(opts["settings"])
    env = settings.get("env") if isinstance(settings.get("env"), dict) else {}
    deseado = construir_env(opts["endpoint"])
    if any(env.get(k) != v for k, v in deseado.items()):
        env.update(deseado)
        settings["env"] = env
        try:
            d = os.path.dirname(opts["settings"])
            if d:
                os.makedirs(d, exist_ok=True)
            with open(opts["settings"], "w", encoding="utf-8") as fh:
                json.dump(settings, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
        except (IOError, OSError):
            pass
    if not (os.path.isfile(opts["compose"]) and os.path.isfile(opts["collector-config"])):
        escribir_collector_files(opts)
    if not opts.get("no-start"):
        _compose_detached(opts["compose"])  # fire-and-forget
    return 0


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    opts = {"settings": ".claude/settings.json",
            "events": "docs/.reviews/otel-api-requests.jsonl",
            "endpoint": "http://localhost:4318",
            "collector-config": ".claude/otel-collector.yaml",
            "compose": ".claude/otel-compose.yml", "config": None,
            "revert": False, "start": False, "stop": False, "status": False,
            "ensure": False, "auto": False, "format": "human"}
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--revert", "--start", "--stop", "--status", "--ensure", "--auto", "--no-start"):
            opts[a[2:]] = True
            i += 1
            continue
        if a in ("--settings", "--events", "--endpoint", "--collector-config", "--compose",
                 "--config", "--format"):
            if i + 1 >= len(argv):
                print("otel-setup: %s exige un valor" % a, file=sys.stderr)
                return 1
            opts[a[2:]] = argv[i + 1]
            i += 2
            continue
        print("otel-setup: opción desconocida: %s" % a, file=sys.stderr)
        return 1

    # ── Modo AUTO (lo llama el SessionStart): enciende la telemetría local y arranca el collector,
    #    salvo opt-out en build-config. Idempotente, fail-open.
    if opts["auto"]:
        return auto_setup(opts)
    # ── Ciclo de vida del collector (no toca settings): start / stop / status / ensure ──
    if opts["start"] or opts["stop"] or opts["status"] or opts["ensure"]:
        return gestionar_collector(opts)

    settings = cargar_settings(opts["settings"])
    env = settings.get("env") if isinstance(settings.get("env"), dict) else {}

    if opts["revert"]:
        quitadas = [k for k in OTEL_ENV if k in env]
        for k in quitadas:
            env.pop(k, None)
        settings["env"] = env
        accion = {"revert": True, "quitadas": quitadas}
    else:
        env_otel = construir_env(opts["endpoint"])
        env.update(env_otel)
        settings["env"] = env
        accion = {"revert": False, "env": env_otel}

    # Escribe settings.json preservando el resto.
    try:
        d = os.path.dirname(opts["settings"])
        if d:
            os.makedirs(d, exist_ok=True)
        with open(opts["settings"], "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    except (IOError, OSError) as e:
        print("otel-setup: no se pudo escribir %s: %s" % (opts["settings"], e), file=sys.stderr)
        return 1

    collector_path = compose_path = None
    if opts["revert"]:
        # Detiene el collector supervisado (si lo había) y retira el compose.
        _compose(opts["compose"], "down")
    else:
        collector_path, compose_path = escribir_collector_files(opts)

    if opts["format"] == "json":
        json.dump({"settings": opts["settings"], "collector_config": collector_path,
                   "compose": compose_path, "endpoint": opts["endpoint"], "accion": accion},
                  sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    elif opts["revert"]:
        print("otel-setup: OTEL desactivado en %s (quitadas: %s). Collector detenido."
              % (opts["settings"], ", ".join(accion["quitadas"]) or "nada"))
    else:
        print("otel-setup: OTEL ACTIVADO en %s (endpoint %s)." % (opts["settings"], opts["endpoint"]))
        print("  ⚠ Claude Code emitirá datos de uso (tokens/coste) al endpoint. Reinicia la sesión.")
        print("  Collector supervisado (docker, restart: unless-stopped):")
        print("    bash .claude/hooks/build/slice-ops.sh otel-setup --start")
        print("    # equivale a: docker compose -f %s up -d" % compose_path)
        print("  A partir de aquí el arnés lo arranca solo en cada sesión (SessionStart → --ensure).")
        print("  Sin docker: corre el collector a mano -> otelcol-contrib --config %s" % collector_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
