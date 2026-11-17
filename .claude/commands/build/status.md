---
name: "BUILD: Status"
description: Informe del agente y su trabajo — modo, proyecto, slice activo, gates, wiring failing, versión de contexto, lease y cola de eventos pendientes. Solo lectura, nunca bloquea. Adaptador delgado sobre slice-ops.sh status.
category: Workflow
tags: [build-harness, runtime, status, trycore]
---

# /build:status — ¿Dónde estamos?

## 1. Informe

```bash
bash .claude/hooks/build/slice-ops.sh status
```

Refresca la proyección desde `/agent/context` y muestra: **modo**, proyecto y agente, slice activo
con fase/gates/wiring, rama y change, versión de contexto (`✓ vN` o `⚠ stale`), lease y número de
eventos pendientes en la cola. En modo `legacy` dice que la fuente de verdad es el fichero local y
no consulta nada.

Con `--no-refresh` no toca la red (útil sin conexión).

## 2. Leer las señales

- `⚠ stale` → la proyección no se pudo refrescar: los guards siguen operando con lo último
  sincronizado. **No cierres gates a ciegas**; reintenta cuando vuelva el runtime.
- `⚠ lease perdido` → haz `slice-ops.sh checkpoint --note …`, detén el trabajo y vuelve a reclamar.
- `cola: N evento(s)` con N creciendo y sin bajar → el daemon no está despachando; revisa
  `.claude/state/heartbeat-status.json` (y, en el sub-slice D, `trycore-build doctor`).

## Guardrails

- **Solo lectura**: este comando no transiciona nada.
- El estado de **la flota** (otros agentes, otros slices, releases y fronts del proyecto) vive en la
  consola del hub: es superficie humana, no de agente.
