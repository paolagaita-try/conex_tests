# Contrato del caparazón (épica fundacional de app shell) — solo greenfield

El **caparazón** es el shell con contenido donde aterrizan las features: navegación, layout,
homepage, login y redirecciones. No es el *scaffold* (shell vacío que arranca — gate
`scaffold.confirmed`) ni el *walking skeleton* (primer journey de negocio más delgado): es la
infraestructura de UI/entrada fundacional que, si no existe primero, cada épica de negocio
improvisa a pedazos y acumula deuda estructural.

**Aplica si y solo si `project_kind === "greenfield"`.** En brownfield el mecanismo entero es
N/A y el arnés no pregunta ni exige nada (`foundation.required: false`).

## Checklist base (ids canónicos)

| id | Qué cubre | Poda típica |
|---|---|---|
| `navegacion-menus` | Menús / estructura de navegación principal | API sin UI |
| `layout-panel-central` | Layout base + panel/área central de contenido | API sin UI |
| `homepage` | Página de inicio real (no placeholder del scaffold) | API sin UI |
| `login-authn` | Login + autenticación cableada end-to-end | app pública sin cuentas |
| `redirecciones-guards` | Redirecciones y guards de ruta (authed/anon, 404, deep-links) | API sin UI |

- La **poda** se decide una vez, en `/build:onboard` Fase 2c, con el humano (ítem podado =
  `applies: false`; queda en la checklist como decisión trazable, no se borra).
- El proyecto puede **añadir** ítems propios (id kebab-case) si su caparazón exige más.

## Ciclo de vida

1. **Onboard (Fase 2c)** — se poda la checklist, se persiste en `foundation.checklist[]` y se
   identifica (o redacta en borrador híbrido) la épica caparazón → `foundation.epic`.
2. **DoR (gate proactivo)** — mientras la épica caparazón no esté **archivada**, ninguna épica
   `layer: business` abre slice (solo fundacionales). Ver `dor.md`.
3. **DoD de la épica caparazón** — cada ítem `applies: true` exige `evidence` de ejecución real
   (test, comando, screenshot MCP), patrón `wiring_checklist`. Sin evidencia completa no se
   archiva.
4. **Cierre** — al archivar con la checklist evidenciada se estampa `foundation.completed_at` y
   las épicas de negocio quedan desbloqueadas.

## Reglas duras

- El arnés **propone** el borrador de la épica caparazón; **solo** lo escribe en
  `docs/03-backlog/epicas.md` con aprobación humana explícita (carve-out acotado, ver
  METODOLOGIA §9.2). Si el humano rechaza, STOP: la épica se crea en discovery (`/trycore:*`).
  En modo `runtime`, esa aprobación humana en `/build:onboard` **propone al hub**
  (`slice-ops.sh propose-epic`), no escribe: el fichero se escribe después, cuando el hub
  también aprueba y asigna el `EP-XXX`, vía `/build:epic --check` (issue #62). En `legacy`/`dual`
  la aprobación humana escribe directo, como arriba.
- La evidencia es de **ejecución**, nunca de inspección.
- Si contradice `METODOLOGIA.md`, gana la metodología.
