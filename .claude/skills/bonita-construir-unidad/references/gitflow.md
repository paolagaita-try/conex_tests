# GitHub Flow de una unidad

El proyecto se crea en el hub con `gitflow_policy: github-flow`: `main` siempre desplegable, una rama corta por
unidad, integración **solo por PR**. El hook `gitflow-guard.sh` lo hace cumplir (bloquea el commit en `main`, el push a
`main` y las ramas sin prefijo `feature/`, `fix/` o `chore/`; la política la trae el hub en `.claude/hub-context/`).

## Ciclo

El claim da las dos ramas: `rama` es la de **trabajo** de la unidad (el `branch_base` del hub, que ya es
`feature/<código>-<slug del título>` y coincide con `feature/<change>`) e `integración` la de **partida** y destino del
PR (la primera de `protected_branches` de la política; con github-flow, `main`).

```bash
git switch <integración> && git pull --ff-only          # la «integración» del claim (con github-flow, main)
git switch -c <rama> <integración>                      # la «rama» del claim; si ya existe: git switch <rama>
# … fases red → dod, con commits pequeños y un checkpoint tras cada uno …
git push -u origin <rama>
gh pr create --base <integración> --head <rama> --title "<unidad>: <título>" --body-file evidencia/<unidad>/pr.md
# /opsx:archive <change> → commit del archive en la misma rama → git push (el PR lo recoge)
```

`<change>` es el del claim, ya resuelto (p. ej. `u1-datos-organizacion-y-procesos`): si el hub no lo trae (grafo
importado por el ADMIN), el claim lo deriva de la rama y lo marca `(derivado: el hub no lo trae)`.

- **Una unidad = una rama = un PR.** El archive del change va **dentro** de ese PR, nunca en uno aparte.
- **Commits**: Conventional Commits en español (`feat: proceso con sus compuertas`, `test: caminos del journey`,
  `docs: caminos de la unidad 1`). Tras cada commit, `slice-ops.sh checkpoint --note «…»`.
- **Nada irreversible sin preguntar**: ni push forzado ni `reset --hard` (los bloquea `destructive-guard.sh`).
- **El merge lo hace una persona.** El agente abre el PR y reporta; no mergea.
- **Varias unidades en paralelo**: un worktree por unidad, cada uno registrado con su propio token
  (`slice-ops.sh register`) y solo cuando sus **Ficheros** no se cruzan. Las unidades de cimiento (`U0`…`U4`) no van en
  paralelo.

## Cuerpo del PR (`evidencia/<unidad>/pr.md`)

```markdown
## Unidad <código> — <título>

- Change OpenSpec: `<change>` (archivado en este PR)
- Documentación: <docs_ref>; tareas: <T-…, o «ninguna»>

### Gates
| Gate | Evidencia |
|---|---|
| `dor` | <una línea> |
| `coherence_link` | … |
| `tdd` | rojo: <comando → resultado>; verde: <comando → resultado> |
| `journey_smoke` | `tools/arnes.sh verificar` = 0; journey: <requests>/<assertions>/<fallos> |
| `fidelity` | … o «no aplica: unidad sin formularios» |
| `api` | … |
| `data` | … |
| `wiring_verified` | pasadas usadas: <1 o 2> de 2; <hallazgos corregidos> |
| `dod` | … |

### Pendiente de prueba en Subscription
- <función y por qué, o «nada»>

### Huecos del arnés abiertos en esta unidad
- <fecha · elemento · enlace a `docs/08-construccion/huecos-del-arnes.md`, o «ninguno»>
```
