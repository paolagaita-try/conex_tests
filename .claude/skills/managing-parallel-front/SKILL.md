---
name: managing-parallel-front
description: Use when building multiple NON-foundational, file-disjoint epics in parallel via git worktrees. Prepares the disjoint selection and merge order locally (front-plan.py), enrolls each worktree as its own agent with its own ADMIN-issued token (slice-ops.sh register), and reports each member's integration (re-smoke, merge_status) through the agent surface. Planning, opening, draining and closing the front are human acts in the hub console. Never parallelizes foundational epics, overlapping file scopes, or two worktrees sharing one token.
---

# Gestionar el front paralelo inter-épica (outer-loop)

**Invariante:** el paralelismo es outer-loop. Cada worktree es un checkout aislado con **su
propio agente registrado** — un token propio, emitido por el ADMIN para ese agente — y un slice
activo singular: el inner loop no cambia.

> **Un token por agente, no uno por proyecto.** El hub **no crea identidad** en
> `POST /agents/register`: el `agent_key` es el `agent_id` que el ADMIN grabó en el token al
> emitirlo. Dos worktrees con el mismo token son **el mismo agente**, y el segundo `claim`
> devuelve el slice que ya tiene reclamado el primero. Y un worktree **sin** credenciales
> propias no queda huérfano: hereda en silencio las del clon principal (`config_root()` cae
> al `--git-common-dir`) y **suplanta** a ese agente. Por eso toda escritura —`claim`, `gate`,
> `submit`, `archive`, `wiring`, `progress`, `checkpoint`, `fact`, `escalate`,
> `front-integration`— aborta con **rc 9** hasta que el árbol se da de alta. Las lecturas
> (`status`, `next-step`) siguen funcionando, y `status` avisa con `identidad: ⚠ HEREDADA`.

**Reparto agente ↔ humano (spec §2).** El agente **prepara y reporta**; la persona **decide**:

| Acto | Quién |
|---|---|
| Proponer el conjunto disjunto y el `merge_order` (`front-plan.py`, local) | agente |
| **Emitir un token por agente** (uno por worktree, `agent_id` distinto) | **humano** (ADMIN), en la consola del hub |
| **Planificar, abrir, drenar y cerrar** el front | **humano**, en la consola del hub |
| Construir cada worktree (inner loop) | agente (uno por worktree) |
| Reportar re-smoke y `merge_status` de su miembro | agente, vía `release-ops.sh front-integration` |

## Precondiciones (compuertas)
- Scaffold confirmado (`bash .claude/hooks/build/slice-ops.sh status`).
- **Un token de agente por worktree**, ya emitido por el ADMIN (paso 3). Sin él no hay front:
  no es un trámite, es lo que hace que dos agentes sean dos.
- **G1 Fundacionales primero:** ninguna épica `layer=foundational` abierta. Si aparece una, el
  front debe **drenarse** (terminar en curso, no admitir nuevas) antes de abrirla — el drenaje
  lo hace una persona en la consola.

## Procedimiento
1. **Reunir candidatas** no fundacionales listas (DoR pasado), cada una con `layer`,
   `files_scope` y `depends_on` (las dependencias declaradas del grafo; `graph-bundle.py` ya las
   computa desde los docs de discovery). Sin `files_scope` declarado una épica **no es
   candidata** y `front-plan.py` la serializa — no es un olvido tolerable, es la compuerta.
2. **Seleccionar el conjunto disjunto** (G2) + regla del pionero (P8) + ancho (P9), en local:
   `echo "$CANDS" | python3 .claude/scripts/lib/front-plan.py [--width 3] [--built-families f1,f2]`
   → `selected` propuestas al front; `serialized` esperan (construir secuencial después) por
   solape de ficheros, por camino en el DAG de `depends_on`, por no declarar `files_scope`, por la
   **regla del pionero** (P8: una familia sin miembro archivado solo deja pasar a su pionera — pasa
   en `--built-families` las familias ya iniciadas) o por el **ancho del frente** (P9: a lo sumo
   `--width` épicas, default 3); `excluded_foundational` nunca en paralelo. **Presenta el plan al
   humano**: es él quien abre el front en la consola con ese `merge_order`.
3. **Abrir un worktree por épica aprobada y darlo de alta con su propio token:**
   `git worktree add ".wt/<epica>" -b feature/<slug>` (rama por `1 épica = 1 rama = 1 PR`).
   El estado del arnés está en `.gitignore`, así que **no viaja al worktree**: en cada uno,
   1. `trycore-build init` (sin `--runtime-token`) para tender `.claude/`;
   2. `bash .claude/hooks/build/slice-ops.sh register` — **pide el token por stdin**, nunca por
      argumento (un `--token` queda en el historial del shell y en `ps`). Cada worktree usa el
      token que el ADMIN emitió **para ese agente**.
   `register` siembra las credenciales locales antes de tocar la red, verifica contra el hub que
   el `agent_key` obtenido **difiere** del del clon principal y, ante cualquier fallo, revierte:
   el fichero del clon principal nunca se toca. Si el token repetido es el del principal, lo
   rechaza y te manda a pedir uno con `agent_id` distinto.
4. **Construir cada worktree** con la skill `building-a-slice` (inner loop normal, en su cwd).
   Cada uno reclama su slice y mantiene su `journey_smoke` verde localmente.
5. **Coordinar merge (G3)** en el `merge_order` aprobado:
   - Merge del PR; tras cada merge, **re-smoke del journey completo** en el árbol principal.
   - Reporta el resultado desde el worktree:
     `bash .claude/hooks/build/release-ops.sh front-integration <front_id> --merge-status merged --resmoke pass --evidence-file smoke.txt`
   - Conflicto → `--merge-status conflict`; serializa la perdedora (rebase + re-correr sus gates).
6. **Cerrar el front** cuando todos los miembros estén `merged`: lo hace una persona en la consola
   (el agente solo reporta que su miembro terminó).

## Reglas duras
- **Un token por agente.** Dos worktrees con el mismo token son un solo agente para el hub.
- Un worktree sin dar de alta **no trabaja**: toda escritura sale con rc 9 hasta que corras
  `register`. No lo esquives exportando `CLAUDE_PROJECT_DIR` — el guard compara el árbol real.
- Nunca escritores paralelos sobre el mismo árbol (por eso worktrees).
- Nunca paralelizar dentro de una épica (preserva la "regla del esqueleto que camina").
- Un solape de `files_scope` no detectado que cause conflicto de merge → el re-smoke (G3) lo caza.
- El agente **no** abre, drena ni cierra el front: esas superficies exigen decisión humana.
