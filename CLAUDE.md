# CLAUDE.md

<!-- BEGIN trycore-bonita-harness v0.13.0 -->
## Arnés de construcción Bonita (Trycore)

Este proyecto usa `@trycore-co/bonita-build-harness` para **construir** el proceso documentado en `docs/07-bonita/`
(fuente de verdad) y `docs/08-construccion/`. Cada unidad (`U0`...`U4`, `E-<familia>`, `S-<subproceso>`, `SUB`) es
una épica del hub. Los detalles de cada paso están en las skills `.claude/skills/`; aquí solo las reglas.

### El hub es la fuente de verdad

- **El ADMIN del hub** crea el proyecto (`gitflow_policy: github-flow`, `cycle_budget: 2`), importa el grafo que
  produce `trycore-bonita grafo` y emite un token por agente. **El agente** se registra, reclama y avanza fases; no
  decide el estado.
- Registro: `.claude/hooks/bonita/slice-ops.sh register` (token por stdin o `TRYCORE_REGISTER_TOKEN`, nunca por argv).
  Cada worktree nuevo se registra por separado.
- Todo cambio de estado va por `slice-ops.sh`, nunca a mano. Lo local (`.claude/state/`, fuera de git) es caché y cola.
- Los assets del hub se materializan en `.claude/hub-context/` (caché de solo lectura; no se edita; los cambios se
  proponen por el hub).
- Códigos de salida de `slice-ops.sh`: `5` = operación en cola sin conexión (continúa y avisa); `6` = el hub la
  rechazó (detente y muestra el motivo); `9` = este worktree no está registrado (ejecuta `register`).
- Una microtarea (claim con `work_type: micro_work`) usa `micro-fase`, `micro-checkpoint` y `micro-escalar`.

### Comandos

| Comando | Para qué |
|---|---|
| `/bonita:work` | siguiente trabajo reclamable (unidad o microtarea) |
| `/bonita:unidad` | construir una unidad, fase a fase |
| `/bonita:bugfix` | corregir un defecto con prueba que lo reproduce |
| `/bonita:microwork` | cambio pequeño sin ciclo completo |
| `/bonita:onboard` | parametrizar el dominio de este proyecto |
| `/bonita:reflect` | proponer convenciones aprendidas tras cerrar una unidad |
| `/bonita:resume` | retomar el trabajo tras una interrupción |
| `/bonita:status` | estado de la unidad, el hub y la cola |
| `/bonita:studio` | llevar el proyecto al Bonita Studio para verlo y recorrerlo (`tools/arnes.sh studio`) |

### Los dos loops

- **Loop de la unidad**: `dor`, `change`, `red`, `green`, `refactor`, `smoke`, `api`, `data`, `dod`, `pr`, `archived`.
- **Loop del verificador**: el gate `wiring_verified` antes de `dod`. Un verificador adversarial independiente, con
  contexto virgen, intenta refutar la unidad (stubs, caminos sin cablear, casos sin prueba); cada hallazgo se corrige
  y se repite, con un máximo de **2 pasadas** (`cycle_budget`).

| Fase del hub | Qué es en una unidad Bonita |
|---|---|
| `dor` | DoR de §6.4 (gatekeeper) |
| `change` | change OpenSpec con `## Trazabilidad` a `docs/07-bonita/` |
| `red` | expectativas primero y fallando: casos del journey por camino de compuerta (`docs/08-construccion/caminos.md`), inventario esperado de los custodios, pruebas Spock si hay código |
| `green` | `tools/arnes.sh generar` y `mvn clean install -Pbundle` hasta que custodios y casos nuevos pasan |
| `refactor` | limpiar `docs/08-construccion/` y código propio sin cambiar comportamiento; todo sigue verde |
| `smoke` | journey completo (todos los caminos) contra el bundle |
| `api` | contratos de proceso (payloads del journey) y, desde la unidad 3, REST API extensions |
| `data` | BDM y operaciones contra `bdm.md` y `contratos.md` |
| `dod`, `pr`, `archived` | DoD de §6.4, PR con el archive de OpenSpec dentro, cierre |

| Gate del hub | Evidencia en una unidad Bonita |
|---|---|
| `dor` | informe del gatekeeper |
| `coherence_link` | change, `docs/07-bonita/` y `docs_ref` de la épica del hub coherentes |
| `tdd` | salida roja y después verde de los mismos casos y custodios (fases `red` y `green`) |
| `journey_smoke` | `tools/arnes.sh verificar` = 0 y journey completo verde (requests, assertions, fallos) |
| `fidelity` | formularios contra `matriz-formularios.md`; sin formularios: PASS con evidencia «no aplica: unidad sin formularios» |
| `api` | contratos y REST API probados |
| `data` | informe del verificador de datos |
| `wiring_verified` | verificador adversarial sobre el wiring checklist (caminos, reglas, integraciones) |
| `dod` | informe del gatekeeper |

### Reglas duras

1. `docs/07-bonita/` es la fuente. Un fichero generado no se edita: se cambia la fuente y se regenera con
   `tools/arnes.sh generar`.
2. Una unidad = una épica del hub = un change de OpenSpec = una rama = un PR que incluye el archive.
3. El journey nunca queda en rojo al cerrar una fase, salvo en modo existente (regla 9), donde el arnés no corre el
   journey.
4. Máximo 2 pasadas del verificador (`cycle_budget`). Si persiste un hallazgo, escala; no hay una tercera.
5. Lo que solo se prueba en Subscription nunca bloquea: va como items de wiring de la unidad `SUB` y, en las demás,
   como «pendiente de prueba en Subscription» dentro de la evidencia.
6. Sube la versión del pool en cada cambio de proceso; si no, el runtime sigue con la definición anterior.
7. Dudas sobre Bonita: consulta el MCP `bonita-doc-index`; si no está conectado, marca «[no verificado]». Nunca de memoria.
8. **Producto completo.** El alcance acordado se construye entero. Recortar o diferir alcance es un bloqueo explícito
   que requiere acuerdo del equipo; nunca lo decide el modelo. La verificación se ejecuta (suite, journey, bundle),
   no por inspección.
9. **Modo existente** (`.trycore-bonita.json` con `modo: "existente"`, proyecto adoptado con `init --existente`): lo
   que el proyecto ya tenía (la línea base, `.trycore-bonita-linea-base.json`) **nunca se edita a mano**. `generar`
   solo corre tras `tools/arnes.sh cambios confirmar`, que responde **una persona** en su propia terminal, fuera de
   esta sesión (el agente se lo pide; nunca lo ejecuta, ni con `!`, ni toca `docs/08-construccion/cambios-confirmados.md`
   salvo para leerlo; el hook lo deniega de buena fe y `respondido_por`/`fecha` se revisan en el PR).
   Sin journey: se cierra con `verificar` = 0, `mvn clean install` y `tools/arnes.sh linea-base actualizar
   --micro-work <id>`. Recorrido: skill `bonita-micro-cambio`, apartado «Modo existente».

### Autonomía y puntos de parada

**Continúa sin preguntar** cuando el siguiente paso es el que calcula `slice-ops.sh next-step`, o cuando la
clasificación del trabajo es clara. Pon las notas de estado en el mismo mensaje que la siguiente acción.

**Para y pregunta** solo ante: (a) una acción irreversible (push forzado, `reset --hard`, borrado de datos,
escritura fuera del repositorio); (b) recortar o diferir alcance (regla de producto completo); (c) editar
`docs/07-bonita/`, la fuente aprobada; (d) el generador no soporta este elemento; (e) el hub rechaza la operación
(código `6`).

**Ningún gate se salta.** Esta sección regula cuándo interrumpir a una persona, no qué verificar.

**Paradas propias del proyecto:** añádelas en el bloque de convenciones aprendidas, no aquí. Esta sección se
reescribe entera en cada actualización del arnés; aquel bloque sobrevive.

### Cómo reportar (gana sobre cualquier otro formato de cierre)

Escribe para alguien que no tiene tu contexto de sesión.

**Sin decisión pendiente, nada sin verificar y tarea corta:** dos líneas y «No necesito nada de ti». Sin formato largo.

**En cualquier otro caso, en este orden:**

1. **Lo que necesito de ti.** La decisión como pregunta, con 2-3 opciones, el coste de cada una y tu recomendación.
   Si no hay decisión pero sí un riesgo, aquí.
2. **Resumen.** Una o dos frases: qué se hizo y si salió bien o mal.
3. **Qué significa.** El impacto para el proceso o la persona usuaria, sin jerga interna.
4. **Riesgo ahora mismo.** Sí o no, y por qué: ¿algo roto o expuesto ahora?
5. **Qué cambió en disco.** Ficheros tocados, si se commiteó y **cómo se deshace**. Obligatorio si hubo escritura.
6. **Pendiente o no verificado.** Lo no probado y lo probado **solo contra dobles, stubs o fixtures** (p. ej. sin el
   hub real o solo en Community y no en Subscription). La ausencia de evidencia no es evidencia de ausencia de problemas.

Reglas de escritura: un término interno (gate, unidad, DoR, arnés) se explica en media frase la primera vez; cada
número dice qué significa; el detalle técnico (rutas, sha, cifras) va al final, en tres líneas como máximo, o en un
fichero con solo la ruta aquí.

### Bloque de dominio (lo resuelve `/bonita:onboard`)

- **Proceso**: Gestión de casos de la integración HubSpot↔Bonita. Al crearse un ticket en HubSpot se instancia un caso en Bonita, se asigna responsable por round robin y cada transición del flujo BPMN se refleja como `stage` del ticket en HubSpot (incluidas las rutas de retorno).
- **Sistemas externos**: HubSpot CRM API (tickets, owners, pipelines, suscripción de webhooks `ticket.creation`). Solo conectores REST nativos de Bonita; no se usa el conector oficial Bonita–HubSpot (Beta, sin soporte de tickets).
- **Datos sensibles**: Token de Private App de HubSpot (secreto; nunca en el repo ni en argumentos de línea de comandos). Datos de contacto/lead del ticket.
- **Decisiones de alto riesgo**: El componente de ENTRADA (quién dispara la instanciación al crearse el ticket) depende del plan de HubSpot. **Dirección decidida (2026-11-11): sin costo** → Free/Starter con **webhook de app `ticket.creation` + middleware externo**; se descarta Operations Hub Professional (tiene costo moderado), aunque técnicamente habilitaba el middleware dentro de HubSpot. Enterprise solo si la tarjeta dentro del ticket fuera requisito de negocio. El plan se coordina con **Laura** (objetivo: que no genere costo); confirmación final pendiente. No bloquea la base de Bonita, idéntica en ambos casos.
- **Sin Fase 2**: no hay Fase 2 en este proyecto. El **bloqueo/transacción del contador round robin** (que se había bosquejado para Fase 2) queda **descartado**: el round robin es un service task sin bloqueo transaccional.
- **Roles/estado (2026-11-11)**: responsable de desarrollo = el agente (yo). **Token de Private App de HubSpot: pendiente, lo gestiona Laura.** Fase 0 (descubrimiento de IDs) asignada al agente — ya documentada en `docs/08-construccion/fase-0-descubrimiento-hubspot.md` (pipeline "Mesa de preventa" id=0, 6 stages, owners); verificación/refresco a la espera del token. El **flujo de diseño de soluciones** (preventa, insumo de U1/`docs/07-bonita/`) se entrega **mañana**.

(Si algún valor sigue entre llaves dobles, ejecuta `/bonita:onboard`.)

### Requisitos

Verifica el entorno con `trycore-bonita doctor` (Node, JDK 17, Maven, hub, credenciales, placeholders sin resolver).
<!-- END trycore-bonita-harness -->

<!-- BEGIN trycore-bonita-learnings -->
## Convenciones aprendidas (mantenido por /bonita:reflect)

<!-- /bonita:reflect propone aquí viñetas concretas tras cerrar una unidad; se agregan SOLO con tu aprobación. -->
<!-- END trycore-bonita-learnings -->

<!-- A partir de aquí, el equipo del proyecto puede agregar instrucciones específicas. -->

<!-- BEGIN trycore-build-harness v0.20.0 -->
## Arnés de construcción (Trycore Build Harness)

Este proyecto usa el arnés `@trycore-co/spec-build-harness` para **construir** sobre la discovery
(compañero de `@trycore/spec-product-flow`: Discovery → Construcción). Modelo de **dos loops**:

```
Inner loop (por épica EP-XXX):  DoR → OpenSpec change → TDD → journey-smoke → api/data → verificación adversarial → DoD → PR + archive
Outer loop (por release):       Release Gate (seguridad · diseño · UX · coherencia triple · arquitectura · integración)
```

- **Unidad de construcción**: la épica (`EP-XXX`). Un slice = una épica = un OpenSpec change = una rama = un PR.
- **Una sola fuente de verdad**: `.claude/state/build-state.json` (schema + protocolo en `.claude/state/README.md`).
- **Skills**: `building-a-slice` (inner loop), `releasing-a-version` (outer loop), `building-a-micro-change` (carril de mantenimiento, dos modos: `/build:bugfix` y `/build:microwork`), `openspec-*` (ciclo de changes).
- **Agentes** en `.claude/agents/build/`; **comandos** `/build:*` + `/opsx:*`; gates automatizados por **hooks** en `.claude/hooks/build/`.

### Slash commands

| Comando | Propósito |
|---|---|
| `/build:work` | Router (classify-and-act): enruta el trabajo a micro-change / slice / release |
| `/build:bugfix` | Bug: ancla al AC, reproduce ejecutando, arregla, re-ejecuta, test validado por reversión |
| `/build:microwork` | Mantenimiento sin bug (copy, config, docs, infra): cambio → verificar → test solo si cambia comportamiento → PR |
| `/build:slice` | Abre/continúa un slice (épica `EP-XXX`) — entrada del inner loop |
| `/build:release` | Corre el Release Gate (outer loop) sobre el diff acumulado de la release |
| `/build:onboard` | Parametriza el dominio del arnés (rellena el bloque de dominio de abajo) y escribe memoria |
| `/build:reflect` | Reflexión post-slice: propone aprendizajes a `CLAUDE.md` (solo con tu aprobación) |
| `/opsx:explore` `/opsx:new` `/opsx:continue` `/opsx:apply` | Ciclo OpenSpec: explorar → crear change → artefactos → implementar |
| `/opsx:verify` `/opsx:archive` `/opsx:sync` `/opsx:ff` `/opsx:bulk-archive` | Verificar, archivar, sincronizar specs |

### Reglas duras (no negociables)

1. **GitHub Flow estricto**: `main` siempre desplegable; integración solo por PR (el hook `gitflow-guard.sh` bloquea commit/push directo a `main`).
2. El enlace change↔épica va en el bloque `## Trazabilidad` del `proposal.md`, **nunca** en frontmatter YAML (rompe `openspec validate`).
3. Las dependencias se vigilan contra `.claude/config/stack-allowlist.json` (hook `stack-guard.sh`), derivado de la sección de requisitos técnicos del PRD.
4. Las revisiones pesadas (seguridad/diseño/UX/coherencia triple/arquitectura/integración) corren **una vez por release** (outer loop), no por épica.
5. **Producto completo, no MVP.** El alcance acordado se construye **entero**. **Recortar o diferir es bloqueante explícito** que requiere acuerdo del equipo — **nunca** una decisión del modelo. No se "deja para después" ni se deriva en lo complejo. La verificación es **ejecutada, no por inspección** (correr la suite, cargar la página, leer la consola).
6. **Cierre verificado, no declarado.** `dod` exige el gate `wiring_verified`: un subagente **adversarial independiente** (`wiring-adversarial-verifier`, contexto virgen) intenta refutar el slice (stubs, rutas sin cablear, AC sin test) antes de cerrar. El estado del cableado vive en disco (`wiring_checklist[]` + `progress_log[]`) para que una sesión fresca retome sin "creer que ya está".
7. **Fidelidad por verificación visual real.** Para slices con UI, el gate `fidelity` solo cierra observando la salida real vía MCP de devtools de navegador (screenshot app vs prototipo); sin verificación visual queda `false` (no "INCONCLUSO pasa").
8. **Cimiento antes que negocio y unidades pequeñas.** Las épicas de cimiento (auth, datos, arquitectura base, design-system) se construyen antes que las de negocio; una épica grande (>3 HU ó ≥3 capas) se descompone en sub-slices construidos de a uno. En proyectos **nuevos** (`project_kind: greenfield`), la **épica caparazón** (app shell: navegación, layout, homepage, login, redirecciones — gate de proyecto `foundation`) se construye y archiva **con evidencia** antes que cualquier épica de negocio; en brownfield el mecanismo es N/A.
9. Si una regla del arnés contradice la metodología Trycore (`METODOLOGIA.md`), **gana la metodología**.

### Ámbito de las reglas de evidencia

- Las reglas pesadas — **mutación obligatoria, evidencia anclada a sha, regresión con
  worktree/baseline** — aplican al **inner loop de slices** (fase tdd→dod de `building-a-slice`),
  **no** al carril `building-a-micro-change`: allí la única mutación es la reversión del fix (modo
  bugfix) y ninguna en microwork sin cambio de comportamiento; suite del módulo tocado en verde
  (las señales de escalada — forma → slice, requisito → discovery — quedan intactas).
- **Presupuesto de mutación**: obligatoria solo para los tests que sostienen un item de
  `wiring_checklist[]` (AC de HU, puntos de integración); opcional para tests auxiliares.
  Alternativa al ciclo manual: mutación automatizada acotada a los ficheros cambiados, con el
  reporte como evidencia.
- **Dos clases de evidencia**: la **determinista** (runners sin LLM) se re-ancla a HEAD; la **viva**
  (corridas contra el LLM real del proyecto) se ancla al último commit que tocó el módulo medido
  (`anchored_at.sha`; `head_at_run` informativo) y solo se regenera cuando cambió el código que mide.
  Detalle operativo: `.claude/skills/building-a-slice/references/evidence-budget.md`.

### Autonomía y puntos de parada

**Continúa sin preguntar** cuando el siguiente paso es el que calcula `slice-ops.sh next-step`, o
cuando la clasificación del carril es clara. Pon las notas de estado en el mismo mensaje que la
siguiente acción, no en un mensaje aparte.

**Para y pregunta** solo ante: (a) cualquier acción irreversible — push forzado, `reset --hard`,
borrado de datos, migración destructiva, escritura fuera del repositorio; (b) recortar o diferir
alcance, que es la regla dura de producto completo y nunca es decisión del modelo; (c) los cuatro carve-outs sobre
documentos de discovery.

**Ningún gate se salta.** Esta sección regula cuándo interrumpir a una persona, no qué verificar.

**Paradas propias del proyecto:** añádelas en el bloque de convenciones de este mismo fichero, no
aquí. Esta sección se reescribe entera en cada actualización del arnés; aquel bloque sobrevive.

### Cómo reportar (gana sobre cualquier otro formato de cierre)

Escribe para alguien que **no tiene tu contexto de sesión**.

**Si no hay decisión que tomar, nada quedó sin verificar y la tarea fue corta:** dos líneas y
«No necesito nada de ti». No uses el formato largo.

**En cualquier otro caso, en este orden:**

1. **Lo que necesito de ti.** La decisión como pregunta, con 2-3 opciones, el coste de cada una y
   tu recomendación. Si no hay decisión pero sí un riesgo, ponlo aquí.
2. **Resumen.** Una o dos frases: qué se hizo y si salió bien o mal.
3. **Qué significa.** El impacto para el producto o la persona usuaria, sin jerga interna.
4. **Riesgo ahora mismo.** Sí o no, y por qué. ¿Hay algo roto o expuesto en este momento?
5. **Qué cambió en disco.** Ficheros tocados, si se commiteó, y **cómo se deshace**. Obligatorio
   siempre que hubo escritura.
6. **Pendiente o no verificado.** Lo que no se probó, y lo que se probó **solo contra dobles,
   mocks o fixtures**. Nunca lo escondas: aquí la ausencia de evidencia no es evidencia de que
   no haya problemas.

**Reglas de escritura.** Un término interno (gate, slice, DoR, arnés, caparazón) se explica en
media frase **la primera vez en la conversación**, no en cada mensaje. Cada número dice qué
significa. El detalle técnico (rutas, sha, cifras de corrida) va al final y ocupa como mucho tres
líneas; si hace falta más, va a un fichero y aquí solo la ruta.

### Bloque de dominio (lo resuelve `/build:onboard`)

Estos puntos de extensión los leen los agentes `security-reviewer`, `stack-guardian`,
`data-consistency-checker`, `ux-krug-reviewer`, `simple-design-reviewer` y `ux-fidelity-reviewer`:

- **PRD técnico (fuente del stack)**: no aplica (sin PRD formal todavía). Stack definido en `.trycore-bonita.json` y los `pom.xml`: Bonita 2026.2 community, Groovy (lógica de proceso), Svelte/TypeScript (formularios), Maven, JDK 17. Contexto de negocio en `HANDOFF-SCAFFOLD.md`. El PRD de la integración llega con el flujo de preventa.
- **Capa de servicios externos / IA (frontera)**: HubSpot CRM API. Entrada: webhook de app `ticket.creation` + middleware externo → instanciación en Bonita. Salida: conectores REST **nativos** de Bonita hacia HubSpot (tickets, owners, pipelines). Aislamiento: todo el trato con HubSpot vive en conectores REST de Bonita; no se usa el conector oficial Bonita–HubSpot (Beta, sin tickets).
- **Lógica que debe ser determinista (no-IA)**: la asignación **round robin** (service task con contador persistente en el BDM, sin bloqueo transaccional) y el **mapa estado Bonita→`stageId` de HubSpot**. Sin IA; falla silenciosa si el mapa deriva.
- **Categorías de datos sensibles / PII reguladas**: datos de contacto/lead del ticket de HubSpot (nombre, correo, empresa y demás propiedades del ticket). Token de Private App de HubSpot (secreto).
- **Secretos server-side**: token de Private App de HubSpot (`HUBSPOT_PRIVATE_APP_TOKEN`). Nunca al cliente, nunca al repo ni a argumentos de línea de comandos; solo variable de entorno. Lo gestiona Laura.
- **Decisiones de alto impacto que exigen explicabilidad UX**: la asignación de responsable por round robin (quién queda asignado y por qué; excluir del reparto el owner bot `88449388` «Trynion»). El componente de entrada depende del plan de HubSpot (decidido: sin costo → Free/Starter + middleware externo; coordina Laura, confirmación final pendiente).
- **Fuente de diseño / referencia visual**: N/A por ahora — sin UI ni prototipo todavía. Los formularios Svelte y su diseño llegan con el flujo de preventa. `/build:prototype` puede generar el prototipo en `docs/05-prototipo/` cuando haya pantallas (la confirmación sigue siendo humana).

(Si aparecen como `{{...}}`, ejecuta `/build:onboard` para parametrizarlos.)

### Requisitos

- `openspec` CLI instalado (`npm i -g @fission-ai/openspec`) — lo usan `/opsx:*` y las skills `openspec-*`.
- `python3` y `git` disponibles — los usan los hooks de `.claude/hooks/build/`.
- Verifica con `trycore-build doctor`.

<!-- END trycore-build-harness -->

<!-- BEGIN trycore-build-learnings -->
## Convenciones aprendidas (mantenido por /build:reflect)

<!-- /build:reflect propone aquí viñetas concretas (convención nueva o error recurrente) tras cerrar un slice; se agregan SOLO con tu aprobación. Revísalas en PR como cualquier cambio de equipo. -->
<!-- END trycore-build-learnings -->
