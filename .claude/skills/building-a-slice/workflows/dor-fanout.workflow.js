// =============================================================================
// PLANTILLA — referencia, NO un script a correr verbatim.
// dor-fanout.workflow.js — Fan-out de los chequeos PER-HU del DoR (inner loop).
//
// QUÉ PARALELIZA (y qué NO): SOLO los criterios del DoR que son por-HU e independientes
// entre sí — frontmatter completo + estado:lista, AC en Given/When/Then proporcional a
// `complejidad`, e INVEST. Los criterios de NIVEL ÉPICA (trazabilidad de la épica,
// dependencias en history[], cimiento construido, gate de tamaño, stack/allowlist,
// fuente de diseño, cobertura de ADR) NO van aquí: los valida dor-dod-gatekeeper en
// sesión — necesitan estado y son baratos. Este workflow ataca lo LENTO: O(HUs) → O(1).
//
// READ-ONLY sobre el estado: NO escribe gates.dor ni abre active_slice. El ÚNICO que
// abre el slice sigue siendo dor-dod-gatekeeper, que COMBINA este diagnóstico per-HU
// con sus criterios de épica y emite el veredicto DoR completo.
//
// CUÁNDO: SOLO con ≥ 3 HUs (bajo eso el fan-out no paga su overhead y el inner loop
// debe seguir barato). Consolidación FAIL-CLOSED con cobertura COMPLETA: una HU
// fallida o un shard ausente = DoR per-HU false, nunca muestreo silencioso.
//
// PLANTILLA AGNÓSTICA: sin vocabulario de dominio/cliente (scripts/check-agnostic.sh
// escanea *.js). Si METODOLOGIA.md (§3.1) contradice algo aquí, gana la metodología.
//
// RUNTIME: corre en el runtime de Workflow de Claude Code, que provee los globals
// agent()/parallel()/pipeline()/phase()/log()/args y envuelve el cuerpo en un contexto
// async (por eso usa `await` y `return` a nivel superior). NO es un módulo node standalone.
// =============================================================================

export const meta = {
  name: 'dor-fanout',
  description: 'Fan-out per-HU de los chequeos del DoR (frontmatter, AC G/W/T proporcional, INVEST) con consolidación fail-closed. Read-only; dor-dod-gatekeeper combina el diagnóstico y emite el veredicto.',
  phases: [{ title: 'HUs', detail: 'un validador solo-lectura por HU, en paralelo' }],
}

const HU_CHECK_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['hu', 'pass', 'faltantes'],
  properties: {
    hu: { type: 'string' },
    pass: { type: 'boolean', description: 'true SOLO si los 3 bloques (frontmatter, AC, INVEST) están completos y verificados' },
    faltantes: {
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
      description: 'cada criterio incumplido, con detalle accionable',
    },
  },
}

// Insumos por `args` (dor-dod-gatekeeper los pasa READ-ONLY; el workflow no decide alcance):
//   args.epica  : string   — ID de la épica (solo para el reporte).
//   args.hus    : string[] — IDs de las HU en alcance (hus[] del slice candidato).
//   args.husDir : string   — directorio de las HU (default 'docs/04-historias').
const epica = (args && args.epica) || '<EP-XXX>'
const hus = (args && Array.isArray(args.hus)) ? args.hus.filter(Boolean) : []
const husDir = (args && args.husDir) || 'docs/04-historias'

// Guard de tamaño: bajo 3 HUs el fan-out no paga su overhead → el gatekeeper valida
// secuencial en sesión (comportamiento previo). Espeja el guard de explore-fanout.
if (hus.length < 3) {
  log(`Épica ${epica} con ${hus.length} HU(s): fan-out no amortiza — validación secuencial en sesión.`)
  return { skipped: true, reason: 'pocas-hus', hus_count: hus.length }
}

phase('HUs')
log(`DoR per-HU: fan-out de ${hus.length} HUs de ${epica} (cobertura completa, sin muestreo)`)
const checks = await parallel(hus.map((hu) => async () => {
  try {
    const v = await agent(
      `Eres un validador SOLO-LECTURA del DoR para UNA SOLA historia de usuario: ${hu} (épica ${epica}).
Lee ${husDir}/${hu}.md y verifica EXACTAMENTE estos 3 bloques (nada de nivel épica):
1. FRONTMATTER completo: id, titulo, epica, prioridad, complejidad, estado — y estado: lista.
2. AC en Given/When/Then PROPORCIONAL a complejidad: trivial/baja → 1-2 (happy + error/edge crítico si
   existe); media → 3 (happy + error + edge); alta → 3-5 (cobertura completa). Regla dura: toda rama de
   error/edge que exista DEBE tener su escenario; NO exijas cuota fija a una HU trivial.
3. INVEST: por cada uno de los 6 criterios (Independent, Negotiable, Valuable, Estimable, Small,
   Testable), cita el fragmento o la línea del documento de la HU que lo sustenta, o marca
   explícitamente que no lo encontraste — no lo evalúes de memoria.
pass:true SOLO si los 3 bloques cumplen. Cada incumplimiento va en faltantes[] como objeto con el
fichero y la línea, por qué está mal, y cómo demostrar que falla (qué campo/escenario/criterio y por
qué). Si el archivo no existe o es ilegible → pass:false con el motivo. NO edites nada; NO valides
otras HU ni criterios de épica.`,
      // agentType: 'Explore' hereda el modelo de la sesión (Tarea 2): corre en el mismo modelo que
      // dor-dod-gatekeeper, así que no hay nada que ceder sustituyéndolo por un agente del arnés.
      { label: `dor:${hu}`, phase: 'HUs', agentType: 'Explore', schema: HU_CHECK_SCHEMA },
    )
    if (!v) return { hu, pass: false, faltantes: [{ file: '<n/a>', why: `${hu}: sin veredicto` }] }
    return { hu, pass: v.pass === true, faltantes: v.faltantes || [] }
  } catch (e) {
    return { hu, pass: false, faltantes: [{ file: '<n/a>', why: `${hu}: el validador falló — revalidar en sesión` }] }
  }
}))

// Consolidación FAIL-CLOSED + cobertura completa: shard ausente = hueco, nunca verde.
const done = checks.filter(Boolean)
const missing = hus.length - done.length
const bad = done.filter((c) => !c.pass)
const all_pass = bad.length === 0 && missing === 0

return {
  epica,
  all_pass,                       // pass per-HU; NO es el DoR completo (falta el nivel épica)
  hus: done,                      // diagnóstico por HU para el reporte ✓/✗ del gatekeeper
  faltantes: [
    ...bad.flatMap((c) => c.faltantes),
    ...(missing > 0 ? [{ file: '<n/a>', why: `${missing} HU(s) sin resultado — cobertura incompleta, revalidar en sesión` }] : []),
  ],
  note: 'Read-only. dor-dod-gatekeeper combina esto con los criterios de NIVEL ÉPICA (dependencias, cimiento, tamaño, stack, diseño, ADR) y es el único que emite el veredicto DoR y abre active_slice.',
}
