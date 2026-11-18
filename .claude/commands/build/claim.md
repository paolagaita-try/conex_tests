---
name: "BUILD: Claim"
description: Reclama trabajo al Agent Orchestrator Runtime (POST /tasks/next) sincronizando el contexto antes, reportando los hashes locales de los archivos gobernados y continuando desde el checkpoint si lo hay. Adaptador delgado sobre slice-ops.sh claim; en modo legacy o dual el slice lo decide el fichero local.
category: Workflow
tags: [build-harness, runtime, claim, trycore]
---

# /build:claim — Pedir la siguiente tarea al runtime

**Entrada (opcional):** `EP-XXX` para pedir una épica concreta. Sin argumento, el runtime elige.

## 1. Reclamar

```bash
bash .claude/hooks/build/slice-ops.sh claim ${1:+--epic "$1"}
echo "rc=$?"
```

El comando ya hace, por ti y en este orden: sincroniza el contexto (no se abre trabajo con
contexto viejo), reporta los `sha256` locales efectivos de los archivos gobernados (el servidor
detecta drift), reclama por **POST**, refresca la caché de proyección y rinde el slice.

## 2. Ramificar por el código de salida

| rc | Qué significa | Qué haces |
|---|---|---|
| 0 | slice reclamado | si la salida trae **CHECKPOINT**, haz checkout de esa rama y **continúa desde ahí, jamás reinicies**; luego `/build:slice` |
| 3 | modo `legacy`, o `dual` (el fichero decide) | abre/retoma el slice con el protocolo del fichero (`/build:slice`) |
| 5 | runtime inalcanzable | **sigue trabajando** con lo local; reintenta al reconectar |
| 6 | rechazo del servidor (409/401/422) | muestra su razón tal cual; **no reintentes** — token, contexto o proyecto a resolver con el ADMIN |
| 7 | sin trabajo disponible, o carrera perdida | dilo y termina limpio; ofrece `/build:status` |

## 3. Seguir

```bash
bash .claude/hooks/build/slice-ops.sh next-step
```

Ejecuta esa acción, o entra al pipeline con `/build:slice`.

## Guardrails

- **No** armes peticiones al runtime a mano: todo pasa por `slice-ops.sh`.
- **Un solo slice activo**: reclamar con lease vigente devuelve el mismo slice (idempotente).
- **Nunca reinicies** un slice que trae checkpoint: es trabajo de otro agente que cayó.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
