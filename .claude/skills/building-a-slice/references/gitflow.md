# GitHub Flow (estricto) — Build

Modelo de ramas **GitHub Flow**: `main` siempre desplegable; todo cambio nace en una rama corta y
se integra **solo por Pull Request** con checks verdes. El hook `gitflow-guard.sh` lo hace cumplir
de forma determinista (bloquea commit/push directo a `main` y ramas no tipadas).

## Ciclo por slice
```bash
git switch main && git pull --ff-only          # parte de main al día
git switch -c feature/<slug>                    # rama tipada: feature/* | fix/* | chore/*
# ... TDD + gates (se reportan con slice-ops.sh gate) ...
git add -A && git commit -m "<tipo>: <mensaje>" # commit en la rama feature (nunca en main)
git push -u origin feature/<slug>               # push de la rama feature (nunca a main)
gh pr create --base main --head feature/<slug> --fill   # integración por PR
```

## Convenciones
- **Rama**: `feature/<slug-kebab>` (nuevo valor), `fix/<slug>` (corrección), `chore/<slug>` (infra/docs).
  Una rama por **épica** (= un slice): `feature/ep-003-pricing-engine`. Las ramas `fix/*` y `chore/*`
  son también el carril de la skill `building-a-micro-change` (mantenimiento que no es producto nuevo:
  va a PR sin abrir épica ni `active_slice`; ver sus límites duros).
- **Commits**: Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`, `docs:`).
- **PR**: título claro, descripción enlazando la épica, sus HU (`hus[]`) y el OpenSpec change; checks
  (lint, types, tests, newman) en verde antes de merge; squash recomendado.

## Qué bloquea `gitflow-guard.sh`
- `git commit` estando en `main`/`master`. → crea una rama feature.
- `git commit` desde una rama que no es `feature/*|fix/*|chore/*`.
- `git push` apuntando a `main`/`master`. → abre un PR.

> No es GitFlow clásico: **no hay `develop` ni `release/*`**. Una sola línea estable (`main`) +
> ramas cortas + PR.
