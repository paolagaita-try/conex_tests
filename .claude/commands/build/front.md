---
name: "BUILD: Front"
description: Prepara y coordina un front paralelo de épicas NO fundacionales y disjuntas en archivos, cada una en su worktree/rama/PR con su propio agente registrado (un token por agente, alta con slice-ops.sh register). Delega en la skill managing-parallel-front (selección disjunta local vía scripts/lib/front-plan.py, worktrees, merge en orden con re-smoke reportado por cada worktree). Planificar, abrir, drenar y cerrar el front son actos humanos en la consola.
category: Workflow
tags: [build-harness, outer-loop, front-paralelo, trycore]
---

# /build:front — Front paralelo inter-épica

Delega en la skill **managing-parallel-front**. Resumen:
1. Verifica precondiciones (scaffold confirmado; sin épica foundational abierta) con
   `bash .claude/hooks/build/slice-ops.sh status`.
2. Reúne candidatas no fundacionales listas (DoR pasado) con `layer`, `files_scope` y
   `depends_on`. Sin `files_scope` declarado la épica **no es candidata** (se serializa).
3. Propón el conjunto disjunto y el `merge_order` (`scripts/lib/front-plan.py`, local; aplica
   también la **regla del pionero** P8 y el **ancho del frente** P9 con `--width`/`--built-families`)
   y **preséntaselo a una persona**: abrir el front es acto de gobierno, en la consola del hub.
4. Un worktree por épica aprobada, cada uno dado de alta como **agente propio** con **su
   propio token** emitido por el ADMIN: `trycore-build init` (sin `--runtime-token`) y luego
   `bash .claude/hooks/build/slice-ops.sh register` (pide el token por stdin). Sin ese alta,
   toda escritura desde el worktree sale con **rc 9**: estaría suplantando al clon principal.
   Después, construye con `/build:slice`.
5. Tras cada merge, re-smoke y reporte desde el worktree:
   `bash .claude/hooks/build/release-ops.sh front-integration <front_id> --merge-status … --resmoke …`.

Úsalo solo cuando haya ≥2 épicas no fundacionales disjuntas listas. Para una sola épica, usa `/build:slice`.
