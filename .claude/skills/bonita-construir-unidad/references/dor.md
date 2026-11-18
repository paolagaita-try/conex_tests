# Definition of Ready (DoR) de una unidad

Una unidad **no entra a construcción** hasta cumplir todo esto (§6.4 del diseño). Lo comprueba el agente
`bonita-gatekeeper-dor-dod` en la fase `dor`, justo después del claim; su informe es la evidencia del gate `dor`.

## Checklist

- [ ] **La unidad está en el plan.** Su código (`U0`…`U4`, `E-<familia>`, `S-<subproceso>`, `SUB`) es una fila de
  `docs/08-construccion/plan.md` con **Ficheros** y **Entrada** no vacíos, y coincide con la unidad del claim
  (`ficheros` y `docs` del claim = esa fila). Formato: `plan-de-unidades.md`.
- [ ] **La documentación que la alimenta está en `pasa`.** En `docs/.flow-state.json`, los gates de capa del arnés de
  documentación que consume la unidad:

| Unidad | Gates de `docs/.flow-state.json` en `pasa` | Además |
|---|---|---|
| `U0` | `gates.bonita.entrada` | `docs/07-bonita/handoff.md` con `estado: listo-para-construccion` |
| `U1` | `gates.bonita.capa-0`, `gates.bonita.capa-1` y `gates.bonita.capa-2` | — (genera BDM, organización y procesos en una pasada) |
| `U2`, `S-<subproceso>` | reservadas en v1 (no se proponen): si aparecen en un plan, es un hallazgo | — |
| `U3` | `gates.bonita.capa-1` (conectores) y `gates.bonita.capa-3` (acceso al BDM) | interfaces en `docs/02-flujo-proceso/`; `U1` archivada (el módulo de parámetros y su semilla) |
| `U4`, `E-<familia>` (formularios) | `gates.bonita.capa-3` (la matriz de formularios en `pasa`) | **módulo de parámetros desplegado y semilla del proceso aplicada** (`GET …/API/extension/parametros/valores` responde con la semilla), `U3` archivada (adaptador y extensión de consultas) y, para `E-<familia>`, `U4` archivada |
| `SUB` | todos los anteriores | edición de destino `subscription` |

  Si un gate no está en `pasa` (o está `reabierto`), la documentación no está lista: construir igual es la forma en que
  vuelve el retrabajo.
- [ ] **Las unidades de las que depende están archivadas** en el hub (columna **Depende de** del plan). El hub solo
  reparte unidades cuyas dependencias están listas; el gatekeeper lo confirma con `slice-ops.sh status` y, si algo no
  cuadra, es un hallazgo.
- [ ] **Los insumos de construcción que consume están fijados** en la tabla «Insumos de construcción» de `handoff.md`
  (estado `fijado`, no `pendiente`): decisión y plantilla de persistencia (desde `U1`), galería de componentes y tipo de
  form mapping (desde `U4`), acceso al BDM y permisos (desde `U3`).
- [ ] **Parámetros antes que formularios** (solo `U4` y `E-<familia>`). Comprobado, no supuesto: el módulo responde
  (`parametros/valores` con un usuario de la familia interna, 200) y la semilla de `bonita-project/parametros/semillas/`
  está aplicada. Antes, tras desplegar, `tools/arnes.sh perfiles` dejó a los usuarios en el perfil `User` (sin él, 403). Sin eso el hallazgo es de orden: los parámetros entran en capas 0–2 y los formularios en 8–14; saltarse
  el orden fue la mayor fuente de reprocesos del método estudiado.
- [ ] **Las fuentes existen.** Cada ruta de **Entrada** existe; cada `T-*.md` de **Tareas** existe en
  `docs/04-tareas-proceso/` y tiene sus criterios Given/When/Then (se vuelven pasos del journey).
- [ ] **El entorno está listo.** `trycore-bonita doctor` sale 0 (requisitos duros). Aparte, en su salida: la sección
  «Avisos» no lista marcadores sin resolver del bloque de dominio de `CLAUDE.md`, y la sección «Runtime (hub)» dice
  `Credenciales: ✓`. Un marcador sin resolver es un aviso, no cambia el código de salida: este criterio se comprueba
  leyendo esas líneas.
- [ ] **Sin `[no verificado]` en lo que la unidad construye**, o cada uno está declarado como pendiente en la
  evidencia (consulta antes el MCP `bonita-doc-index`).

## Si todo se cumple

```bash
bash .claude/hooks/bonita/slice-ops.sh gate dor pass --evidence-file evidencia/<unidad>/dor.md
bash .claude/hooks/bonita/slice-ops.sh phase change
```

La evidencia lista cada criterio con lo comprobado (fichero, campo, valor), no «ok».

## Si algo falla

No se abre el trabajo de la unidad ni se reporta `pass`. Tampoco `fail`: un `fail` gasta presupuesto del verificador y
el DoR no se arregla reintentando. La documentación vuelve al arnés de documentación (una persona decide):

```bash
bash .claude/hooks/bonita/slice-ops.sh escalate --file evidencia/<unidad>/dor.md --gate dor
```

y reporta qué falta, dónde y quién lo resuelve (normalmente, cerrar la capa en el arnés de documentación).
