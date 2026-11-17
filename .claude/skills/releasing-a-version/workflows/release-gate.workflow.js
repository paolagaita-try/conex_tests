// =============================================================================
// PLANTILLA — referencia, no obligatoria. Adapta los nombres de agente y el rango de
// diff a tu proyecto. El arnés es AGNÓSTICO: este archivo NO debe contener vocabulario
// de dominio ni de cliente — lo verifica scripts/check-agnostic.sh (incluye *.js).
//
// release-gate.workflow.js — Conducción del Release Gate (outer loop), §5 de METODOLOGIA.md.
// Hogar PRIMARIO de los workflows: corre UNA vez por release (O(releases)), fuera del camino
// caliente del inner loop. NO duplica el inner loop (ni TDD ni gates por slice).
//
// READ-ONLY sobre el estado: esta plantilla devuelve un diagnóstico; la skill
// releasing-a-version es la ÚNICA que reporta los veredictos (release-ops.sh verdict por gate;
// en modo legacy, una entrada en releases[] del fichero). El agregado y el auto-cierre en verde son del
// runtime/humano. Parciales NO promueven a passed. Si METODOLOGIA.md (§5) contradice algo aquí,
// gana la metodología.
//
// RUNTIME: corre en el runtime de Workflow de Claude Code, que provee los globals
// agent()/parallel()/pipeline()/phase()/log()/args y envuelve el cuerpo en un contexto async
// (por eso usa `await` y `return` a nivel superior). NO es un módulo node standalone.
// =============================================================================

export const meta = {
  name: 'release-gate',
  description: 'Reviewers pesados en paralelo (coherence shardeado por HU cuando la release es grande) + integración secuencial + síntesis para el Release Gate (outer loop). Read-only; devuelve veredictos, no escribe estado.',
  phases: [
    { title: 'Reviewers', detail: '5 reviewers en paralelo; el carril coherence fan-out por HU (≥3 HUs) con consolidación fail-closed' },
    { title: 'Integration', detail: 'journey completo con deps reales (SECUENCIAL, fuera del parallel)' },
  ],
}

const RELEASE_REVIEW_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean', description: 'true solo si no hay hallazgos bloqueantes y se pudo verificar' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'number' },
          why: { type: 'string' },
          how_to_show: { type: 'string' },
        },
        required: ['file', 'why'],
      },
    },
  },
}

// diffRange, si la release tiene UI y la lista de HUs llegan por `args` (la skill los computa READ-ONLY).
//   args.hus : string[] — IDs de TODAS las HU de las épicas de la release (para shardear coherence).
//              Ausente o < 3 → coherence corre monolítico (comportamiento previo, sin inflar releases chicas).
const diffRange = (args && args.diffRange) || '<merge-anterior>..main'
const hasUI = !!(args && args.hasUI)
const hus = (args && Array.isArray(args.hus)) ? args.hus.filter(Boolean) : []

// --- Carril coherence: SHARDING por HU (lossless) ----------------------------
// La trazabilidad triple AC↔change↔código de cada HU es INDEPENDIENTE de las demás: shardearla
// no pierde hallazgos cruzados (a diferencia de security/smell, que quedan monolíticos a propósito).
// Consolidación FAIL-CLOSED y cobertura COMPLETA: un shard fallido/ausente = gate false, nunca
// muestreo silencioso. Con < 3 HUs el fan-out no paga su overhead → monolítico como siempre.
async function coherenceLane() {
  if (hus.length < 3) {
    try {
      const v = await agent(
        `Eres el reviewer pesado del Release Gate para el gate "coherence". Verifica READ-ONLY la trazabilidad
triple AC↔change↔código de TODAS las HU de la release sobre el diff acumulado (${diffRange}). Si NO puedes
verificar, devuelve pass:false con el motivo — nunca PASS por defecto.`,
        { label: 'release:coherence', agentType: 'coherence-three-way', phase: 'Reviewers', schema: RELEASE_REVIEW_SCHEMA },
      )
      if (!v) return { gate: 'coherence', value: false, error: 'sin veredicto' }
      return { gate: 'coherence', value: v.pass === true, findings: v.findings || [] }
    } catch (e) {
      return { gate: 'coherence', value: false, error: 'el reviewer falló' }
    }
  }
  log(`coherence: fan-out por HU (${hus.length} shards — cobertura completa, sin muestreo)`)
  const shards = await parallel(hus.map((hu) => async () => {
    try {
      const v = await agent(
        `Eres un shard del reviewer "coherence" del Release Gate. Verifica READ-ONLY la trazabilidad triple
AC↔change↔código de UNA SOLA HU: ${hu}. Lee sus AC (Given/When/Then), el change OpenSpec que la cubre y el
código/tests del diff acumulado (${diffRange}) que la implementan. pass:true SOLO si cada AC de ${hu} tiene
test real y código cableado, sin huérfanos. Si NO puedes verificar → pass:false con el motivo.`,
        { label: `release:coherence:${hu}`, agentType: 'coherence-three-way', phase: 'Reviewers', schema: RELEASE_REVIEW_SCHEMA },
      )
      if (!v) return { hu, pass: false, findings: [{ file: '<n/a>', why: `${hu}: sin veredicto` }] }
      return { hu, pass: v.pass === true, findings: (v.findings || []).map((f) => ({ ...f, why: `${hu}: ${f.why}` })) }
    } catch (e) {
      return { hu, pass: false, findings: [{ file: '<n/a>', why: `${hu}: el shard falló` }] }
    }
  }))
  const done = shards.filter(Boolean)
  const missing = hus.length - done.length            // shard ausente (skip/kill) = hueco de cobertura
  const bad = done.filter((s) => !s.pass)
  const value = bad.length === 0 && missing === 0
  return {
    gate: 'coherence', value,
    findings: [
      ...bad.flatMap((s) => s.findings),
      ...(missing > 0 ? [{ file: '<n/a>', why: `coherence: ${missing} shard(s) sin resultado — cobertura incompleta, gate false` }] : []),
    ],
  }
}

// --- PASO A · Reviewers pesados EN PARALELO (exactamente estos 5) ------------
// Cada uno delega en su subagente sobre el MISMO diff acumulado y devuelve síntesis.
// Barrera deliberada: la síntesis de release necesita los 5 veredictos juntos.
// security/smell/ux/stack_arch quedan MONOLÍTICOS a propósito: shardearlos por archivos
// puede perder hallazgos cross-cutting (p.ej. un bypass de auth visible solo entre módulos).
phase('Reviewers')
const REVIEWERS = [
  { gate: 'security',   agentType: 'security-reviewer' },
  { gate: 'smell',      agentType: 'simple-design-reviewer' },
  { gate: 'ux',         agentType: 'ux-krug-reviewer' },   // null SOLO si la release no tiene UI
  { gate: 'coherence',  agentType: 'coherence-three-way' }, // carril con sharding interno por HU (ver coherenceLane)
  { gate: 'stack_arch', agentType: 'stack-guardian' },
]
const reviews = await parallel(REVIEWERS.map((r) => async () => {
  // N/A legítimo: ux sin UI → null (NO es fallo). El resto SIEMPRE corre.
  if (r.gate === 'ux' && !hasUI) return { gate: r.gate, value: null, na: true }
  if (r.gate === 'coherence') return coherenceLane()
  try {
    const v = await agent(
      `Eres el reviewer pesado del Release Gate para el gate "${r.gate}". Revisa READ-ONLY el diff acumulado de la
release (${diffRange}) y devuelve tu veredicto + hallazgos bloqueantes. Por cada hallazgo: el fichero y la
línea, por qué está mal, y cómo demostrar que falla (comando o pasos reproducibles). Si NO puedes verificar
(herramienta ausente, app no levantable), devuelve pass:false con el motivo — nunca PASS por defecto, nunca
null por fallo.`,
      { label: `release:${r.gate}`, agentType: r.agentType, phase: 'Reviewers', schema: RELEASE_REVIEW_SCHEMA },
    )
    if (!v) return { gate: r.gate, value: false, error: 'sin veredicto' } // ausente/indeterminado = FALLO
    return { gate: r.gate, value: v.pass === true, findings: v.findings || [] }
  } catch (e) {
    return { gate: r.gate, value: false, error: 'el reviewer falló' }     // fallo = gate false, NUNCA null
  }
}))

// --- PASO B · integration SECUENCIAL, FUERA del parallel() ------------------
// integration NO va dentro del parallel() y NO delega en un reviewer: lo corre la skill
// verify/run con DEPS REALES (+ MCP chrome-devtools). Es el gate no negociable.
phase('Integration')
let integration
try {
  integration = await agent(
    `Recorre el JOURNEY COMPLETO de la release end-to-end con DEPENDENCIAS REALES (no stubs), usando la skill
verify/run (+ MCP chrome-devtools si hay UI). Diff: ${diffRange}. Devuelve si el journey camina entero. Si no
puedes levantarlo o falta una dep real → pass:false (nunca PASS por defecto).`,
    { label: 'release:integration', phase: 'Integration', schema: RELEASE_REVIEW_SCHEMA },
  )
} catch (e) {
  integration = { pass: false, findings: [{ file: '<n/a>', why: 'integration no pudo correr (deps reales/app no levantable)' }] }
}

// --- PASO C · Síntesis → diagnóstico para releasing-a-version ----------------
// Mapea los 6 gates. Parciales NO promueven a passed: todos true (o ux=null por N/A) +
// integration=true → passed; cualquier otra cosa → failed.
const gates = {}
for (const rv of reviews.filter(Boolean)) gates[rv.gate] = rv.na ? null : rv.value
gates.integration = !!(integration && integration.pass === true)

const reviewersGreen = reviews.filter(Boolean).every((r) => r.na || r.value === true)
const status = (reviewersGreen && gates.integration === true) ? 'passed' : 'failed'

return {
  status,            // reportado por releasing-a-version vía release-ops.sh verdict (agregado y auto-cierre en verde son del runtime; el degradado lo decide un humano).
  gates,             // {security, smell, ux, coherence, stack_arch, integration}
  blocking: [
    ...reviews.filter((r) => r && r.value === false).map((r) => ({ gate: r.gate, error: r.error || null, findings: r.findings || [] })),
    ...(gates.integration === true ? [] : [{ gate: 'integration', findings: (integration && integration.findings) || [] }]),
  ],
  note: 'Read-only. releasing-a-version reporta un veredicto por gate (release-ops.sh verdict). El runtime agrega y AUTO-CIERRA con 6/6 PASS (closed_by: AUTO_6_OF_6_PASS); el caso degradado lo decide un humano en la consola. Parciales NO promueven a passed.',
}
