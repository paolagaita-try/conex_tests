---
name: "BUILD: Escalate"
description: Registra un bloqueo del slice en el runtime (evento slice_escalated) y devuelve la decisión al humano — recortar, diferir o desbloquear nunca lo decide el modelo. Adaptador delgado sobre slice-ops.sh escalate.
category: Workflow
tags: [build-harness, runtime, escalada, gobierno, trycore]
---

# /build:escalate — Bloqueo que decide una persona

**Entrada:** la razón del bloqueo (una frase concreta y verificable). Opcional: el gate afectado.

## 1. Registrar

```bash
bash .claude/hooks/build/slice-ops.sh escalate "<razón>" --gate <gate opcional>
```

Deja el rastro tipado en el runtime (ámbito slice si hay slice reclamado; de proyecto si no).
Para razones largas, escríbelas en un fichero y usa `--file`.

## 2. Devolver la decisión al humano

Presenta al usuario, en tres líneas: **qué está bloqueado**, **qué evidencia lo demuestra** y
**las opciones reales** (con su coste). No elijas por él. Este es un formato de pantalla específico
de la escalada (no contradice `### Cómo reportar` del CLAUDE.md: ya lidera con la decisión) y queda
subordinado a él.

> **Regla dura del arnés:** *Producto completo, no MVP.* Recortar o diferir alcance es un
> **bloqueante explícito** que requiere acuerdo del equipo — jamás una decisión del modelo. Escalar
> no es rendirse: es negarse a degradar el alcance en silencio.

## Guardrails

- **No** cierres gates «para avanzar» mientras el bloqueo esté vivo.
- **No** inventes alternativas fuera del alcance acordado.
- Si el bloqueo es de contexto gobernado (allowlist, política, reglas), la salida es una
  **propuesta** en el hub que publica un ADMIN, no una edición local del fichero sincronizado.
- Si algo contradice `METODOLOGIA.md`, **gana la metodología**.
