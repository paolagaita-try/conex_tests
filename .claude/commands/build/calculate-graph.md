---
name: "BUILD: Calculate Graph"
description: Calcula y valida el grafo de épicas del proyecto buscando el balance entre coste por épica y paralelismo. En Fase 1 implementa --check (solo lectura): valida tope de tamaño (P2), épicas sin HU con AC (P3), convexidad/ciclos (P4) y cierre de líneas (P10) como reglas DURAS, más deriva de dependencias y solapes como avisos. Adaptador delgado sobre slice-ops.sh graph-check. --propose/--apply/--calibrate llegan en una fase posterior.
category: Workflow
tags: [build-harness, grafo, epicas, dor, trycore]
---

# /build:calculate-graph — valida el grafo de épicas (balance coste/paralelismo)

El número y el tamaño de las épicas, y sus dependencias, se declaran en discovery
(`docs/03-backlog/epicas.md` + `docs/04-historias/HU-*.md`). Este comando **valida** ese grafo
contra la política del grafo (METODOLOGIA §5-ter, P1–P12): es el mismo gate que corre el DoR
antes de abrir cualquier épica. Equivocarse en la granularidad —épicas demasiado finas que pagan
el coste fijo muchas veces, o demasiado gruesas que explotan de forma superlineal— sale caro, y
nada lo validaba hasta ahora.

**Regla dura (METODOLOGIA §10.15):** el grafo es **convexo y acotado**. `> 6 HU` o un ciclo
bloquean el DoR; la aceptación del PO **no lo salta** (se parte en épicas, no en tramos).

## Despacho por argumento (léelo antes que nada)

- **`--check`** (por defecto) → **solo lectura**. Valida el grafo y sale con un código tipado.
  No escribe nada.
- **`--propose`** → **propone** una partición que balancea coste y paralelismo (frontera +
  recomendada) y escribe la propuesta en `docs/.reviews/`. **No toca el discovery.** Solo lectura
  sobre los docs de entrada.
- **`--apply`** → tras la aprobación humana, **materializa** los campos estructurados en los docs
  (el `depende_de` de `epicas.md` y, con `--from`, el `epica:` de las HU). **DRY-RUN por defecto**;
  escribe solo con `--yes`. **No toca ningún AC** (carve-out §9.2).
- **`--calibrate`** → ajusta los parámetros del modelo de coste (F/C_HU/S/ρ/I) con la **telemetría
  de tokens** de las épicas archivadas y escribe el fichero de costes que `--propose` carga.

## 1. Validar (`--check`)

```bash
# Todo el grafo:
bash .claude/hooks/build/slice-ops.sh graph-check
# Una épica concreta (lo que corre el DoR antes de abrirla):
bash .claude/hooks/build/slice-ops.sh graph-check --epic EP-XXX
```

Opciones: `--cap N` (tope de HU por épica, default 6), `--format human|json` (default `human`).
Lee por defecto `docs/03-backlog/epicas.md` y `docs/04-historias/`; se pueden fijar con
`--epicas <ruta>` y `--historias <dir>`.

### Qué valida

| Regla | Qué comprueba | Severidad |
|---|---|---|
| **P2** | `> cap` HU en una épica (default 6); `> 2 tramos` si `tramos:` está declarado | **DURA** |
| **P3** | épica sin ninguna HU, o sin ninguna HU con AC en Given/When/Then (Dado/Cuando/Entonces) | **DURA** |
| **P4** | ciclo en el grafo de épicas (declarado ∪ derivado de las deps duras entre HU) | **DURA** |
| **P10** | una épica depende de otra en una `linea_release` posterior (si ambas la declaran) | **DURA** |
| **P5** | el `depende_de` declarado difiere del derivado de las HU (si las HU declaran `depende_de_duras`) | aviso |
| capa | épica sin `layer:` declarado | aviso |
| solape | dos épicas de negocio con `files_scope` solapado y sin dependencia entre ambas | aviso |

Un ciclo se reporta con **su camino y los pares de HU que lo causan**, para corregirlo en origen.

## 2. Leer el resultado (códigos de salida)

| rc | Significado | Qué haces |
|---|---|---|
| `0` | Sin violaciones duras (puede haber avisos) | El grafo cumple la política. Revisa los avisos con el usuario si los hay |
| `2` | ≥1 violación DURA (un motivo por línea) | **Se corrige en los docs de discovery**: partir una épica grande en épicas (no en tramos), romper el ciclo, dar AC a una HU, reordenar líneas. No se abre la épica hasta que pase |
| `1` | Docs ilegibles (ruta inexistente, épica desconocida con `--epic`, args mal) | Revisa la ruta/el argumento que indica el mensaje |

## 3. Proponer una partición (`--propose`)

```bash
bash .claude/hooks/build/slice-ops.sh graph-propose --agents 3
```

Opciones: `--agents k` (default 2), `--cap N`, `--cost <ruta>` (parámetros calibrados; por
defecto usa `docs/.reviews/graph-cost.json` si existe), `--out <dir>` (default `docs/.reviews`),
`--format human|json`, `--no-write` (no escribe, solo informa).

Calcula el **modelo de coste** (F/s/ρ/I, defaults calibrables) y simula la **duración con k
agentes**, y hace **búsqueda local** (fusionar, partir, mover HU) bajo P2/P3/P4, la coherencia
(una HU solo se une a épicas de su misma área) y sin mezclar `draft` con `lista`. Entrega:

- la **frontera** coste vs. duración (variantes: Actual, Fina, Gruesa, Óptimo) con la duración
  con 2 y 3 agentes;
- la **partición recomendada** (la de mínima `coste/C* + duración_k/T*`);
- una **propuesta** en `docs/.reviews/<fecha>-grafo-propuesta.md`.

**No toca el discovery** (`docs/01-prd` … `docs/04-historias`): solo escribe en `docs/.reviews/`
(carve-out §9.2). La aprobación es humana; `--apply` la materializa al backlog.

## 4. Materializar (`--apply`) — con aprobación humana

```bash
# DRY-RUN (enseña el plan, no escribe):
bash .claude/hooks/build/slice-ops.sh graph-apply
# Escribe el `depende_de` estructurado en epicas.md:
bash .claude/hooks/build/slice-ops.sh graph-apply --yes
# Aplica además una partición aprobada (reasigna el `epica:` de las HU):
bash .claude/hooks/build/slice-ops.sh graph-apply --from docs/.reviews/<fecha>-grafo-propuesta.json --yes
```

Materializa en `epicas.md` el `depende_de` **estructurado** (el grafo efectivo, derivado de las
`depende_de_duras` de las HU) — haciendo explícito el grafo y eliminando la deriva P5 — y, con
`--from`, reasigna el `epica:` de las HU a la partición aprobada. **Es DRY-RUN por defecto**
(escribe discovery solo con `--yes`), **nunca toca un AC**, y un split con código no canónico se
**rechaza** (la renumeración de épicas es decisión humana). Después, `/build:graph-sync` propone el
grafo al hub.

## 5. Calibrar el modelo de coste (`--calibrate`)

```bash
bash .claude/hooks/build/slice-ops.sh graph-calibrate --telemetry docs/.reviews/graph-telemetry.json
```

Lee la **telemetría de tokens por fase** de las épicas ya archivadas (P12) y estima por mínimos
cuadrados los parámetros del modelo de coste (**F, C_HU, S, ρ, I**), cada uno con su **intervalo de
confianza del 95 %**. Escribe `docs/.reviews/graph-cost.json`, que `--propose` carga
automáticamente (o con `--propose --cost <ruta>`). Los parámetros que la telemetría no identifica
(p.ej. ninguna épica con más de un tramo, o ninguna construida en paralelo) se **dejan en su
default** y se marcan como tales — no se inventan.

Formato de un registro de telemetría (por épica archivada):

```json
{"epic":"EP-001","hu":3,"tramos":1,"concurrent":false,
 "phases":{"dor":800,"change":5000,"tdd":3000,"smoke":600,"adversarial":4000,"dod":700,"integration":1500}}
```

### Cómo se emite la telemetría (dos medidas)

`/build:reflect` (Fase 2-bis) la emite al cerrar cada épica. Hay dos medidas de coste:

**(a) Commits como proxy — sin infraestructura, por defecto.** Es la medida que usó la evidencia
de #86 («commits por épica como indicador del coste»):

```bash
bash .claude/hooks/build/slice-ops.sh graph-telemetry --epic EP-XXX --auto
```

**(b) Tokens EXACTOS por fase — vía OpenTelemetry (ON por defecto, LOCAL).** Es la cifra que
enumera P12. Los hooks de Claude Code **no** reciben tokens, así que la fuente es OTEL.

**El arnés lo enciende y lo mantiene solo:** el hook de **SessionStart** corre `otel-setup --auto`
en cada sesión, que (1) escribe las variables OTEL en `.claude/settings.json` apuntando a un
collector **local** (`http://localhost:4318`), y (2) arranca ese collector (docker, supervisado).
Claude Code emite un evento `claude_code.api_request` por llamada con
`input_tokens`/`output_tokens`/`cache_*`/`cost_usd` + timestamp + `session.id`.

> **Privacidad:** el endpoint por defecto es **localhost** — los datos de uso **no salen de la
> máquina**; se quedan en `docs/.reviews/otel-api-requests.jsonl` del propio proyecto, para
> calibrar su modelo de coste. El arnés **nunca** apunta a un endpoint remoto por defecto.
> **Opt-OUT:** pon `"telemetry": {"otel": {"enabled": false}}` en `config/build-config.json` (o
> `slice-ops.sh otel-setup --revert`) y no se enciende nada.

La primera vez (o a mano) puedes forzar la activación/arranque:
   ```bash
   bash .claude/hooks/build/slice-ops.sh otel-setup          # activa + genera el compose
   bash .claude/hooks/build/slice-ops.sh otel-setup --start  # --status · --stop · --revert
   ```
   Tras activar, reinicia la sesión de Claude Code para que las variables apliquen.

El collector (docker, `restart: unless-stopped`) recibe OTLP en `:4318` y vuelca a
`docs/.reviews/otel-api-requests.jsonl`; `graph-otel-phases` lo lee **directamente** (OTLP anidado
del exportador `file`), sin transformarlo. **Requiere Docker**; sin Docker, corre el collector a
mano (`otel-setup` imprime el comando). Las **ventanas de fase** las marca el arnés solo: cada
`slice-ops.sh phase <to>` deja una línea en `.claude/state/graph-phase-markers.jsonl`.

Luego, **atribuye y registra** (lo hace `/build:reflect` al archivar, o a mano):
   ```bash
   PH="$(bash .claude/hooks/build/slice-ops.sh graph-otel-phases --epic EP-XXX --format phases-rich)"
   bash .claude/hooks/build/slice-ops.sh graph-telemetry --epic EP-XXX --phases "$PH"
   ```
   `graph-otel-phases` cruza cada evento con la ventana de fase que contiene su timestamp y suma
   los tokens por fase (DoR/change/TDD/smoke/adversarial/DoD/integración).

Lo único que necesita el proyecto es **Docker** (para el collector supervisado); el arnés hace el
resto solo. Con el opt-OUT puesto o sin Docker, no hay tokens por fase y se usa el proxy (a).

## Integración con el resto del arnés

- El **DoR** (`dor-dod-gatekeeper`) corre `graph-check --epic EP-XXX` como precondición y **no
  abre el slice** si devuelve `2`.
- En modo `runtime`, `slice-ops.sh claim --epic EP-XXX` revalida el grafo en local antes de
  reclamar (fail-fast); el hub lo revalida al claim.

## Guardrails

- **Solo lectura**: `--check` no transiciona ni escribe nada.
- **No edites `docs/03-backlog/epicas.md` para "pasar" el check**: el fichero es la fuente; si no
  cumple, lo que está mal es el grafo, y se corrige en discovery con el usuario delante.
- **La política del grafo gana** (METODOLOGIA §5-ter y §10.15): el PO no salta P2/P3/P4/P10.
