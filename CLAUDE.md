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
- **Decisiones de alto riesgo**: El componente de ENTRADA (quién dispara la instanciación al crearse el ticket) depende del plan de HubSpot — Operations Hub Professional (middleware dentro de HubSpot) vs Free/Starter (webhook de app + middleware externo). Decisión del líder técnico/Laura; no la decide el agente. No bloquea la base de Bonita, que es idéntica en ambos casos.

(Si algún valor sigue entre llaves dobles, ejecuta `/bonita:onboard`.)

### Requisitos

Verifica el entorno con `trycore-bonita doctor` (Node, JDK 17, Maven, hub, credenciales, placeholders sin resolver).
<!-- END trycore-bonita-harness -->

<!-- BEGIN trycore-bonita-learnings -->
## Convenciones aprendidas (mantenido por /bonita:reflect)

<!-- /bonita:reflect propone aquí viñetas concretas tras cerrar una unidad; se agregan SOLO con tu aprobación. -->
<!-- END trycore-bonita-learnings -->

<!-- A partir de aquí, el equipo del proyecto puede agregar instrucciones específicas. -->
