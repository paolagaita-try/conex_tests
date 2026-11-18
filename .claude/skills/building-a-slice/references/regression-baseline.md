# Baseline de regresión — «¿rompí algo?» con tests rojos heredados

Cómo medir regresión de un slice cuando la suite del destino **no está verde** por tests rojos
«ambientales» heredados. Sin esto, la pregunta «¿rompí algo?» exige el ritual completo (worktree
del destino + suite ×2 + comparar conjuntos de rojos) en **cada** medición — un impuesto de
~35 min que paga todo slice. Si algo aquí contradice `METODOLOGIA.md`, **gana la metodología**.

## Dos vías (no excluyentes)

1. **La buena — suite verde.** Sanear o cuarentenar los rojos heredados (skip anotado con su
   issue, o arreglo) hasta que la suite del destino esté verde. Entonces «¿rompí algo?» vuelve a
   ser **una** corrida normal y esta referencia deja de aplicar. Es **trabajo del proyecto
   consumidor** (sus suites, sus issues): el arnés no lo hace por él, pero es el estado objetivo.
2. **La pragmática — baseline cacheado por sha** (mientras la suite no esté verde). El veredicto
   del baseline (el conjunto de ficheros rojos de `origin/<destino>`) se captura **una vez** y se
   cachea en un JSON versionable (`baseline-verdict.<sha>.json`). La medición de regresión de un
   slice pasa a ser: **1 corrida de la suite del working tree + comparación estilo `comm`** contra
   el JSON. Ni worktree ni segunda suite por medición.

## El script: `assets/baseline-verdict.sh`

Bash portable (macOS/Linux), agnóstico del runner de tests. En el consumidor queda instalado en
`.claude/skills/building-a-slice/assets/baseline-verdict.sh`.

```bash
# 1) capturar el baseline (una vez por sha del destino; ~el coste del ritual, pagado UNA vez)
bash .claude/skills/building-a-slice/assets/baseline-verdict.sh capture origin/main

# 2) medir regresión del slice (cada vez que haga falta; 1 corrida de suite)
bash .claude/skills/building-a-slice/assets/baseline-verdict.sh compare origin/main
```

- `capture <ref>` corre la suite del sha remoto en un **worktree temporal** (symlinkeando
  `node_modules` por defecto, `BASELINE_LINK_DIRS`) y escribe
  `.baseline/baseline-verdict.<sha>.json` con el conjunto ordenado de ficheros rojos +
  metadatos (`captured_at`, `suite_cmd`, `red_filter`). Versiona el JSON en git si quieres que
  todo el equipo/agente reuse la captura.
- `compare <ref>` corre la suite del working tree **una vez** y reporta tres conjuntos:
  **regresiones nuevas** (rojo que no estaba en el baseline → sale con rc 1), **arreglados** y
  **heredados sin cambio** (no cuentan como regresión). **Invalidación automática**: si el sha de
  `origin/<destino>` ya no coincide con ningún cache, lo dice y pide re-capturar (rc 3).

### Parametrización (agnóstica del runner)

| Variable | Default | Qué es |
|---|---|---|
| `BASELINE_SUITE_CMD` | `npm test` | Comando de la suite. Con vitest, p.ej. `npx vitest run`. Puede salir ≠0 (los rojos son el dato). |
| `BASELINE_RED_FILTER` | `grep -E '^[[:space:]]*FAIL([[:space:]]\|$)' \| awk '{print $2}' \| sort -u` | Pipeline shell que lee la salida de la suite y emite un fichero rojo por línea (el default entiende el formato `FAIL <fichero> …` de reporters tipo vitest; ajústalo a tu runner). |
| `BASELINE_DIR` | `.baseline/` en la raíz | Dónde viven los JSON de veredicto. |
| `BASELINE_LINK_DIRS` | `node_modules` | Dirs de la raíz a symlinkear en el worktree de `capture`. |
| `BASELINE_NO_FETCH=1` | — | No hacer `git fetch origin` antes de resolver el ref. |

## Guard: siempre contra `origin/<destino>`, nunca un ref local

El script **rechaza refs locales** (rc 2): solo acepta `origin/<rama>` o un sha verificado como
remoto (`git branch -r --contains <sha>` no vacío). Comparar contra la rama local (que puede ir
detrás del remoto) **ya produjo una medición falsa** que costó un hallazgo ALTA corregir — el
guard no es negociable y no se puentea editando el JSON a mano.

## Cuándo usar cada cosa

- Suite del destino **verde** → ni cache ni ritual: una corrida normal (esta referencia N/A).
- Suite del destino **con rojos heredados** → `compare` contra el cache en cada medición del
  slice; `capture` solo cuando el destino avanza (el propio `compare` avisa con rc 3).
- El cache **no sustituye** los gates del pipeline (`tdd`, `journey_smoke`, `wiring_verified`):
  solo abarata la pregunta «¿introduje regresiones respecto del destino?». Y cada slice es una
  oportunidad de mover rojos heredados a la vía buena (arreglar o cuarentenar con issue).
