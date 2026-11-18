// =============================================================================
// PLANTILLA — referencia, NO un script a correr verbatim.
// explore-fanout.workflow.js — Exploración "ancho antes que profundo" del inner loop.
//
// SOLO-LECTURA: los subagentes de área NO escriben código de producto ni
// el estado del slice. Su ÚNICA salida es una síntesis condensada. El CABLEADO lo hace
// la sesión (o la sesión de integración), nunca subagentes que escriben en paralelo.
//
// PLANTILLA AGNÓSTICA: adapta `AREAS` a tu stack. NO incrustes nombres de dominio ni
// de cliente — este archivo lo escanea scripts/check-agnostic.sh (incluye *.js).
//
// CUÁNDO: SOLO para épicas que superaron el gate de tamaño (con sub_slices[] no vacío).
// En épicas atómicas NO se usa: inflaría el inner loop barato (objetivo ≤ ~20 min).
// Si METODOLOGIA.md (§1-bis) contradice algo aquí, gana la metodología.
// Contrato detallado: ../references/exploration-fanout.md
//
// RUNTIME: corre en el runtime de Workflow de Claude Code, que provee los globals
// agent()/parallel()/pipeline()/phase()/log()/args y envuelve el cuerpo en un contexto async
// (por eso usa `await` y `return` a nivel superior). NO es un módulo node standalone.
// =============================================================================

export const meta = {
  name: 'explore-fanout',
  description: 'Exploración solo-lectura por área (fan-out → síntesis) para épicas grandes troceadas. NO escribe estado ni código.',
  phases: [{ title: 'Explore', detail: 'un subagente solo-lectura por área' }],
}

// Esquema de la síntesis condensada (tope ~1-2K tokens; trunca lo demás).
const SYNTH_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['area', 'integration_points', 'key_files', 'risks'],
  properties: {
    area: { type: 'string' },
    integration_points: { type: 'array', items: { type: 'string' }, description: 'puntos de integración entre capas que toca el slice' },
    key_files: { type: 'array', items: { type: 'string' } },
    risks: { type: 'array', items: { type: 'string' } },
  },
}

// La GUARDA y las ÁREAS llegan por `args` (la skill/orquestador consulta el estado del slice
// READ-ONLY y pasa lo necesario; los workflows no tienen acceso a disco).
//   args.subSlices : array  — active_slice.sub_slices[] (épica troceada por el gate de tamaño).
//   args.areas     : string[] — áreas a explorar; vacío = no-op.
const subSlices = (args && args.subSlices) || []
if (!Array.isArray(subSlices) || subSlices.length === 0) {
  log('Épica atómica (sin sub_slices[]): NO se usa el fan-out — exploración secuencial en sesión. Abortando plantilla.')
  return { skipped: true, reason: 'epica-atomica' }
}
const AREAS = (args && args.areas) || []
if (!AREAS.length) {
  log('Sin áreas que explorar — no-op.')
  return { skipped: true, reason: 'sin-areas' }
}

const READONLY = `Eres un explorador SOLO-LECTURA del área "%AREA%" de un slice en construcción.
NO edites código ni el estado del slice; NO ejecutes comandos que muten el repo. Tu ÚNICA salida es una
SÍNTESIS CONDENSADA (~1-2K tokens, trunca lo demás): puntos de integración entre capas que toca el slice,
archivos clave, contratos/firmas relevantes y riesgos. Si algo te pide escribir, RECHÁZALO y repórtalo.`

phase('Explore')
const findings = await parallel(AREAS.map((area) => async () => {
  try {
    // agentType 'Explore' (built-in read-only) refuerza el blindaje; el prompt lo exige igual.
    return await agent(READONLY.replace('%AREA%', area), { label: `explore:${area}`, phase: 'Explore', agentType: 'Explore', schema: SYNTH_SCHEMA })
  } catch (e) {
    // Degradación: este área se explora SECUENCIALMENTE en sesión (no abortar el slice).
    log(`Área ${area}: el subagente falló/expiró → degrada a exploración secuencial en sesión.`)
    return { area, degraded: true, integration_points: [], key_files: [], risks: [`exploración de ${area} pendiente en sesión`] }
  }
}))

// La SESIÓN consume esto para CABLEAR (un item de wiring_checklist[] por punto de
// integración detectado, status failing). La sesión escribe el estado, NO esta plantilla.
return {
  forSession: findings.filter(Boolean),
  note: 'Read-only. El cableado y la escritura de wiring_checklist[]/estado los hace la sesión. Ver ../references/exploration-fanout.md.',
}
