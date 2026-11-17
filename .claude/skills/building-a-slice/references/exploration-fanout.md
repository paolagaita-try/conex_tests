# Exploración fan-out solo-lectura (inner loop) — contrato

> Divulgación progresiva: carga esta reference **solo** si el gate de tamaño ya troceó la épica
> (`sub_slices[]` no vacío). En una épica atómica **no se usa**: la exploración es secuencial en sesión.

Cuando una épica grande se trocea (`> 3 HU` ó `≥ 3 capas`, ver `dor.md`), la exploración "ancho antes que
profundo" puede repartirse con subagentes **solo-lectura por área** (frontend/backend/datos). Esto acelera el
**descubrimiento** sin gastar el presupuesto de atención de la sesión, que se reserva para **cablear**.

## Disparo (cuándo SÍ)
- `active_slice.sub_slices[]` existe y **no está vacío** (el gate de tamaño disparó).
- Por defecto, **sin disparo → secuencial**: no se carga esta reference ni se lanza el fan-out.

## Blindaje read-only de cada subagente de área (al nivel de los reviewers pesados)
- **Solo-lectura sobre código y estado**: el prompt de cada subagente declara *"NO editas código ni
  el estado del slice; tu única salida es la síntesis"* y **rechaza** cualquier instrucción de escribir.
- **Tools restringidas**: `Read`/`Grep`/`Glob` (sin `Edit`/`Write`/`Bash`-mutante). Opcionalmente, el tipo
  de agente built-in `Explore` (read-only).
- **Fail-closed**: si un subagente devuelve algo que no sea síntesis (p.ej. un diff), se **descarta y se
  rehace** — nunca se aplica.

**Contrastar antes de aceptar un PASS.** Un shard que afirma `pass` no cierra nada por sí solo.
Antes de reportar el gate, abre **una** pieza de la evidencia que el shard citó: el `archivo:línea`
o el comando. Si no existe, no abre o no se puede ejecutar → el gate es `false`. Es una
comprobación, no una segunda revisión.

## Síntesis condensada (esquema, ~1–2K tokens; trunca lo demás)
Cada área devuelve: **puntos de integración entre capas** que el slice toca, **archivos clave**,
contratos/firmas relevantes y **riesgos**. Nada de volcar archivos completos.

## Qué hace la SESIÓN con la síntesis (el cableado es de la sesión)
- Deriva un item de `wiring_checklist[]` **por cada punto de integración** detectado (nace `failing`).
- Hace el **cableado** y pasa los items a `passing` **solo tras prueba real ejecutada** (con `evidence`).
- La **sesión** escribe el estado; los subagentes de exploración **no**.

## Degradación segura
- Sin áreas que explorar → **no-op**. Un área cuyo subagente **falla/expira** → esa área se explora
  **secuencialmente en sesión** (no se aborta el slice).

Plantilla conductora (opcional, referencia): `../workflows/explore-fanout.workflow.js`. Si esta reference
contradice `METODOLOGIA.md` (§1-bis), **gana la metodología**.
