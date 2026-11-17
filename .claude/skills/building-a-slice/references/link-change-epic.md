# Enlace OpenSpec change ↔ épica + HU cubiertas (bloque de Trazabilidad)

Cada OpenSpec change corresponde a **una épica** (la unidad de construcción) y declara las
**historia(s)** que cubre. Este enlace es el puente entre la discovery de Trycore (`docs/`) y la
construcción (`openspec/`). Lo valida `change-epic-coherence`.

## Dónde y cómo
En el **cuerpo markdown** del `openspec/changes/<name>/proposal.md`, añade una sección al final:

```markdown
## Trazabilidad
- Épica: EP-003
- Historias: HU-010, HU-011, HU-012
- Discovery: docs/03-backlog/epicas.md#ep-003
```

> ⚠️ **NO** lo pongas en frontmatter YAML del proposal: OpenSpec valida la estructura del change
> con `openspec validate --strict` y un frontmatter ajeno puede romperla. El bloque markdown es seguro.

## Reglas
1. **Exactamente una épica** por change = la unidad del slice (un change no cruza épicas). Si
   necesitas dos épicas, son dos slices/changes distintos.
2. **Las HU de esa épica** que entran en el alcance (las de `hus[]`). Cada `HU-XXX` debe existir y
   su `epica:` debe coincidir con la EP. La lista de `Historias:` debe igualar a `hus[]`.
3. **Nombre del change**: kebab-case basado en la épica, p.ej. `ep-003-pricing-engine`.
4. **Back-reference**: al archivar, añade la nota `> OpenSpec change: ep-003-pricing-engine` en la
   épica (`docs/03-backlog/epicas.md`) y en cada HU de `hus[]` (cierra el enlace bidireccional
   Trycore↔OpenSpec).

## Validación
```bash
openspec validate "<name>" --type change --strict --json
```
El agente `change-epic-coherence` corre esto + comprueba existencia de EP/HU + coherencia de alcance.
