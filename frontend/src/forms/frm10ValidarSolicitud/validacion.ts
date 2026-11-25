/**
 * Validación de la pantalla antes de enviar. El esquema generado (`generado/esquema.ts`) espeja la matriz;
 * las reglas propias de esta pantalla se añaden aquí. La verdad última es el contrato de Bonita.
 */
import { esquema } from './generado/esquema';
import type { CuerpoDelContrato } from './generado/contrato';

/**
 * Las cuatro opciones de `concepto_viabilidad` en HubSpot (enumeración; valor interno = etiqueta). Espeja la
 * constraint `conceptoViabilidad_valido` de `ctr_10_validarSolicitud` (docs/07-bonita/contratos.md, versión 1.3).
 */
export const CONCEPTOS = [
  'Aprobado (Viable)',
  'Aprobado con Condiciones',
  'No Viable (Rechazado)',
  'Requiere más información',
] as const;

/** El concepto que exige el camino «no viable» (constraint `conceptoViabilidad_noViable`). */
export const CONCEPTO_NO_VIABLE = 'No Viable (Rechazado)';

/** Los errores por ruta (`grupo.campo`); vacío = se puede enviar. */
export function erroresDe(cuerpo: CuerpoDelContrato): Record<string, string> {
  const resultado = esquema.safeParse(cuerpo);
  const errores: Record<string, string> = {};
  if (resultado.success) return errores;
  for (const problema of resultado.error.issues) {
    // Un input múltiple trae el índice en la ruta: el campo es el mismo para todos.
    const ruta = problema.path.filter((p): p is string => typeof p === 'string').join('.');
    if (!(ruta in errores)) errores[ruta] = problema.message;
  }
  return errores;
}

/**
 * Reglas propias de la pantalla, que espejan las constraints del contrato: el concepto es obligatorio si es viable o
 * no viable, es una de las cuatro opciones de HubSpot y, si no es viable, es «No Viable (Rechazado)».
 */
export function erroresDePantalla(cuerpo: CuerpoDelContrato): Record<string, string> {
  const errores = erroresDe(cuerpo);
  if (cuerpo.resultado === null) errores.resultado = 'Elija el resultado de la validación.';
  const concepto = cuerpo.conceptoViabilidad ?? '';
  const exigeConcepto = cuerpo.resultado === 'viable' || cuerpo.resultado === 'no_viable';
  if (exigeConcepto && !concepto.trim()) {
    errores.conceptoViabilidad = 'El concepto de viabilidad es obligatorio si la solicitud es viable o no viable.';
  } else if (concepto !== '' && !(CONCEPTOS as readonly string[]).includes(concepto)) {
    errores.conceptoViabilidad =
      'El concepto de viabilidad debe ser Aprobado (Viable), Aprobado con Condiciones, No Viable (Rechazado) o Requiere más información.';
  } else if (cuerpo.resultado === 'no_viable' && concepto !== CONCEPTO_NO_VIABLE) {
    errores.conceptoViabilidad = 'Si la solicitud no es viable, el concepto debe ser No Viable (Rechazado).';
  }
  if (!cuerpo.notaValidacion?.trim()) errores.notaValidacion = 'La nota de validación es obligatoria.';
  return errores;
}
