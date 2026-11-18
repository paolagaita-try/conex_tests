---
name: "BONITA: Status"
description: Informe del agente y su trabajo — proyecto, unidad o micro-work reclamado, fase, gates, wiring en failing, versión de contexto, lease y cola de eventos pendientes (slice-ops.sh status), más el estado local del arnés (trycore-bonita status). Solo lectura.
category: Workflow
tags: [bonita, status, runtime, trycore]
---
<!-- Origen: trycore-spec-build-harness@062c6fd commands/build/status.md (adaptado a Bonita y al modo servidor) -->

# /bonita:status — ¿Dónde estamos?

## 1. Informe

```bash
bash .claude/hooks/bonita/slice-ops.sh status
trycore-bonita status
```

El primero refresca la proyección desde el hub y muestra proyecto y agente, la unidad (o micro-work) reclamada con
fase, gates y wiring, rama de trabajo, rama de integración y change, versión de contexto (`✓ vN` o `⚠ stale`), lease, grafo y eventos pendientes en
la cola. El segundo, el estado local del arnés. Con `--no-refresh` el primero no toca la red.

## 2. Leer las señales

- `⚠ stale` → la proyección no se pudo refrescar: los guards siguen con lo último sincronizado. **No cierres gates a
  ciegas**; reintenta cuando vuelva el hub.
- `⚠ lease perdido` → `slice-ops.sh checkpoint --note …`, detén el trabajo y reclama de nuevo.
- `cola: N evento(s)` creciendo sin bajar → el heartbeat no está drenando; revisa `.claude/state/` y
  `trycore-bonita doctor`.
- Salida `9` → este árbol no está registrado.
- Sin proyecto o sin grafo → el ADMIN aún no importó el plan: `/bonita:onboard`.

## Guardrails

- **Solo lectura**: no transiciona nada.
- El estado de la flota (otros agentes, otras unidades) vive en la consola del hub, no aquí.
