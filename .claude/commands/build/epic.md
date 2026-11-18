---
name: "BUILD: Epic"
description: Propone una épica nueva al hub (modo runtime) y, tras la aprobación humana, la escribe en docs/03-backlog/epicas.md con el código que asignó el hub. Con --check no propone nada: solo consulta el estado de las propuestas y proyecta las ya aprobadas. El agente NO inventa el EP-XXX. Adaptador delgado sobre slice-ops.sh propose-epic/epic-status/epic-writeback.
category: Workflow
tags: [build-harness, runtime, backlog, epicas, trycore]
---

# /build:epic — proponer una épica (la identidad la decide el hub)

Carril de las épicas **incrementales de construcción**: las que nacen en una terminal con el
proyecto ya registrado en el hub. La descomposición **inicial** del backlog sigue siendo de
discovery (`/trycore:epicas`, `@trycore/spec-product-flow`) y entra al hub por el import masivo
de admin — este comando no la sustituye.

**Regla dura**: el agente **no elige** el `EP-XXX`. Lo asigna el hub al aprobar. Elegirlo mirando
`epicas.md` es lo que hace que dos terminales creen la misma numeración y sus historias colisionen.

**Entrada (opcional):** `--check`. Sin argumento, el comando **propone** una épica nueva.

## Despacho por argumento (léelo antes que nada)

El comando tiene **dos carriles** y no se recorren de arriba abajo:

- **Con `--check`** → ve directo al **§0** y luego **salta al §3**. `--check` es una consulta de
  **solo lectura** sobre propuestas que ya existen: **no redactes ningún borrador y no propongas
  nada** (§1 y §2 no se ejecutan, ni siquiera "por si acaso"). Es el carril que invocan el DoR
  (`references/dor.md`) y el `dor-dod-gatekeeper` para averiguar si la épica caparazón ya está
  propuesta: si ahí se propusiera una épica, la comprobación crearía **una segunda propuesta de
  la misma épica** — exactamente la colisión que este comando existe para impedir.
- **Sin argumento** → §0 → §1 → §2. El §3 se recorre después, cuando el humano haya aprobado en
  la consola del hub (normalmente en otra invocación, con `--check`).

## 0. Precondición

```bash
bash .claude/hooks/build/slice-ops.sh mode
```

- `legacy` → **STOP**: no hay hub al que proponer. La épica se crea en discovery
  (`/trycore:*`); si es la épica caparazón, por el carve-out de `/build:onboard` Fase 2c.
- `dual` → **STOP** igual, pero por otra razón: aquí **sí hay hub**, y el fichero local es el
  primario. El carril de propuesta solo opera en `runtime`; la épica se crea como en `legacy` y
  llega al hub por el import de admin. No lo diagnostiques como un problema de conexión.
- `runtime` → sigue.

## 1. Redactar el borrador (con el usuario)

Reúne del repo y de `docs/` lo necesario y **propón** al usuario, vía **AskUserQuestion**:
título, objetivo, capa (`foundational` | `business` | `technical`), alcance de archivos y
dependencias con épicas existentes. Las historias van con AC en Given/When/Then.

El grafo del hub solo distingue **dos** capas (`FOUNDATIONAL` y `BUSINESS`): una épica
`technical` viaja como `business` y eso es correcto, no un error que debas corregir.

No inventes la clasificación de capa ni las dependencias: derívalas del PRD / Story Map y
confírmalas. Sin aprobación explícita del usuario, **no propongas nada**.

Escribe el borrador en un fichero temporal (nunca por argv):

```json
{
  "title": "…",
  "objective": "…",
  "layer": "business",
  "files_scope": ["src/…/**"],
  "depends_on": ["EP-012"],
  "stories": [
    {
      "title": "…",
      "description": "Como … quiero … para …",
      "acceptance_criteria": "Dado … Cuando … Entonces …. Dado … Cuando … Entonces …"
    }
  ]
}
```

Escribe los criterios **completos** en `acceptance_criteria`: `slice-ops.sh` los parte en un
escenario por entrada y los manda como `acceptance[]`, que es lo que la consola del hub enseña
en el detalle de la historia (issue #70). Varios escenarios en un mismo campo se separan con
`. Dado …`; si prefieres darlos ya partidos, usa `"acceptance": ["Dado …", "Dado …"]` y manda.

## 2. Proponer

```bash
bash .claude/hooks/build/slice-ops.sh propose-epic --file /tmp/epica-borrador.json
```

| rc | Significado | Qué haces |
|---|---|---|
| `0` | Enviada; el hub devolvió el identificador de la propuesta | Dile al usuario que queda **pendiente de aprobación humana** en la consola del hub |
| `5` | Encolada, aún sin entregar (sin conexión, o el daemon estaba drenando la cola en ese instante) | Igual, avisando de que se despachará sola y de que `epic-status` la sigue |
| `6` | El hub la rechazó (o falta `project_id`) | Muestra la razón; **no** reintentes en bucle |
| `2` | Borrador inválido | Corrige el campo que indica el mensaje y repite |
| `3` | `legacy`/`dual` | Vuelve al paso 0 |

**No escribas `docs/03-backlog/epicas.md` aquí.** El fichero es una proyección del grafo: se
escribe cuando existe el código, y el código no existe hasta que un humano aprueba.

## 3. Después de la aprobación — `/build:epic --check`

**Aquí aterriza `--check`** (viniendo del despacho de arriba). Los dos comandos son mecánicos:
uno consulta, el otro proyecta lo ya aprobado. Ninguno propone nada.

```bash
bash .claude/hooks/build/slice-ops.sh epic-status
bash .claude/hooks/build/slice-ops.sh epic-writeback
```

`epic-status` resuelve el estado de cada propuesta (`QUEUED` · `PROPOSED` · `APPROVED` ·
`REJECTED` · `FAILED`). `epic-writeback` escribe en `epicas.md` **solo** las `APPROVED` que
falten, con el código del hub, y es idempotente (`rc 7` = nada pendiente).

Tras escribir, revisa el bloque con el usuario y **no toques el código a mano**: si algo está
mal, se corrige en el hub y se vuelve a proyectar.

## Guardrails

- El agente **propone**; la identidad la decide el hub y la aprobación es humana (gobierno,
  METODOLOGIA §10 regla 8). Ni el modelo ni el arnés aprueban una épica.
- Los códigos de HU los pone el hub si los devuelve; el arnés **nunca** los inventa.
- El único fichero de `docs/` que este comando toca es `docs/03-backlog/epicas.md`, y solo con
  un código ya asignado (carve-out de METODOLOGIA §9.2).
- En `legacy`/`dual` el comando no hace nada: el backlog vive en el fichero.
