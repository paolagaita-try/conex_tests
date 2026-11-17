// =============================================================================
// PLANTILLA — referencia, NO un script a correr verbatim.
// wiring-verify.workflow.js — Conducción ADVERSARIAL del gate wiring_verified (inner loop).
//
// El GENERADOR (la sesión que construyó el slice) y el VERIFICADOR (este workflow) están
// SEPARADOS por diseño: contexto virgen, NO reuses el contexto del constructor. Esta
// plantilla es una ENVOLTURA reproducible del agente wiring-adversarial-verifier que ya
// existe; equivale a la prosa de building-a-slice, NO crea un gate nuevo ni cambia política.
//
// READ-ONLY sobre el estado: NO escribe gates.wiring_verified ni ningún campo de
// el estado del slice. El ÚNICO que reporta el gate sigue siendo build-orchestrator, que aplica
// el mapeo a partir del veredicto que esta plantilla DEVUELVE.
//
// PLANTILLA AGNÓSTICA: sin AC/evidence literales — solo RUTAS de estado/repo en runtime.
// Regla dura: ante CUALQUIER ambigüedad o señal faltante, nunca "pasa". Si METODOLOGIA.md
// (§1-bis) contradice algo aquí, gana la metodología.
//
// RUNTIME: corre en el runtime de Workflow de Claude Code, que provee los globals
// agent()/parallel()/pipeline()/phase()/log()/args y envuelve el cuerpo en un contexto async
// (por eso usa `await` y `return` a nivel superior). NO es un módulo node standalone.
// =============================================================================

export const meta = {
  name: 'wiring-verify',
  description: 'Verificación adversarial independiente del cableado de un slice (gate wiring_verified). Read-only; devuelve veredicto, no escribe estado.',
  phases: [{ title: 'Refute', detail: 'wiring-adversarial-verifier intenta refutar el cableado' }],
}

const WIRING_VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'gaps'],
  properties: {
    verdict: { type: 'string', enum: ['CABLEADO_COMPLETO', 'HUECOS'] },
    gaps: { type: 'array', items: { type: 'string' }, description: 'huecos priorizados (archivo:línea, HU/AC o par de capas)' },
    reproduced: { type: 'array', items: { type: 'string' }, description: 'ids de wiring_checklist[] cuya evidence fue re-ejecutada en ESTA pasada (build-orchestrator les estampa verified_at_sha)' },
    unchanged: { type: 'array', items: { type: 'string' }, description: 'ids que conservaron veredicto como «sin cambios desde <sha>» (diff vacío desde su verified_at_sha; no se re-ejecutó su evidence)' },
  },
}

// Insumos por `args` (la sesión/orquestador los pasa READ-ONLY; el workflow no toca disco):
//   args.checklistPresent  : boolean  — ¿active_slice.wiring_checklist[] existe y NO está vacío?
//   args.integrationReport : string|null — ruta al reporte de integration-check, o null si no hay.
//   args.passNumber        : number   — nº de pasada adversarial sobre este slice (1 = primera).
//   args.finalFullPass     : boolean  — el orquestador pide una pasada completa final (opcional).
const checklistPresent = !!(args && args.checklistPresent)
const integrationReport = (args && args.integrationReport) || null
const integrationPresent = !!integrationReport
const passNumber = (args && args.passNumber) || 1
const finalFullPass = !!(args && args.finalFullPass)
// Selección incremental: pasada completa solo la primera (o una final explícita); las pasadas 2+
// re-ejecutan SOLO los items cuyo código cambió desde su verified_at_sha, acotadas al diff de los
// arreglos + sus rutas gemelas. Condición de parada (fase dod): máximo 2 pasadas completas por
// slice — la 3ª solo existe como pasada ACOTADA por hallazgo ALTA en código preexistente.
const incremental = passNumber > 1 && !finalFullPass

// (ii) wiring_checklist[] ausente/vacío (slice trivial) → INSUFICIENTE, nunca verde por defecto.
if (!checklistPresent) {
  return {
    verdict: 'INSUFICIENTE', maps_to_wiring_verified: false,
    reason: 'wiring_checklist[] ausente o vacío: build-orchestrator debe sembrarlo y verificar; wiring_verified permanece false.',
  }
}

phase('Refute')
let result
try {
  result = await agent(
    `Eres el verificador ADVERSARIAL e INDEPENDIENTE del cableado (contexto virgen; no construiste este slice).
Tu sesgo por defecto es "está incompleto": solo das CABLEADO_COMPLETO si, tras intentar romperlo activamente, NO
encuentras ningún hueco. Lee READ-ONLY: active_slice.wiring_checklist[] del estado, el diff del slice y las HU en
alcance${integrationPresent ? `, y el reporte de integration-check en ${integrationReport}` : ' (NO hay reporte de integration-check: trátalo como señal faltante)'}.
${incremental
  ? `PASADA INCREMENTAL (nº ${passNumber}): re-ejecuta la evidencia SOLO de los items cuyo código cambió desde su
verified_at_sha (git diff <sha>..HEAD -- <rutas del item>) o que no traen verified_at_sha; los demás conservan
veredicto y los listas en "unchanged" como «sin cambios desde <sha>». Acota el foco al diff de los arreglos +
sus rutas gemelas (el patrón de defectos inducidos: blindar una ruta y dejar la gemela). Si un diff no se puede
calcular, ese item SE RE-EJECUTA (nunca «sin cambios» por fallo). Si re-ejecutas un item «sin cambios» y su
evidencia es irreproducible → HUECOS igual que siempre.`
  : `PASADA COMPLETA (nº ${passNumber}): por cada AC y cada punto de integración, REPRODUCE la evidencia ejecutándola.`}
Si no puedes ejecutar una evidencia, ese item es failing. Reporta en "reproduced" los ids re-ejecutados en esta
pasada (build-orchestrator les estampará verified_at_sha). Ante CUALQUIER duda no resuelta o señal faltante →
HUECOS. No edites estado ni código.`,
    { label: 'wiring-verify', agentType: 'wiring-adversarial-verifier', phase: 'Refute', schema: WIRING_VERDICT_SCHEMA },
  )
} catch (e) {
  // (iv) el verificador no pudo correr → NO-CONCLUYENTE; wiring_verified permanece false.
  return {
    verdict: 'NO-CONCLUYENTE', maps_to_wiring_verified: false,
    reason: 'El verificador no pudo ejecutarse (toolerror/entorno). Sin ejecución no hay evidencia: wiring_verified permanece false.',
  }
}

// (i) sin éxito silencioso: si no hay veredicto claro → no verde.
if (!result || !result.verdict) {
  return {
    verdict: 'NO-CONCLUYENTE', maps_to_wiring_verified: false,
    reason: 'El verificador no devolvió un veredicto claro. wiring_verified permanece false.',
  }
}

// (iii) sin reporte de integration-check → señal faltante → degrada a HUECOS (no verde).
const greenlit = result.verdict === 'CABLEADO_COMPLETO' && integrationPresent
return {
  verdict: greenlit ? 'CABLEADO_COMPLETO' : (result.verdict === 'CABLEADO_COMPLETO' ? 'HUECOS' : 'HUECOS'),
  gaps: result.gaps && result.gaps.length ? result.gaps : (integrationPresent ? [] : ['falta reporte de integration-check: señal faltante']),
  reproduced: result.reproduced || [],
  unchanged: result.unchanged || [],
  maps_to_wiring_verified: greenlit,
  note: 'Read-only. build-orchestrator es quien escribe gates.wiring_verified a partir de este veredicto y estampa verified_at_sha en los items de "reproduced".',
}
