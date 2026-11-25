/**
 * Validación de la pantalla antes de enviar. El esquema generado (`generado/esquema.ts`) espeja la matriz;
 * las reglas propias de esta pantalla se añaden aquí. La verdad última es el contrato de Bonita.
 */
import { esquema } from './generado/esquema';
import type { CuerpoDelContrato } from './generado/contrato';

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

/** Reglas propias de la pantalla (contrato: el concepto es obligatorio si es viable o no viable). */
export function erroresDePantalla(cuerpo: CuerpoDelContrato): Record<string, string> {
  const errores = erroresDe(cuerpo);
  if (cuerpo.resultado === null) errores.resultado = 'Elija el resultado de la validación.';
  const exigeConcepto = cuerpo.resultado === 'viable' || cuerpo.resultado === 'no viable';
  if (exigeConcepto && !cuerpo.conceptoViabilidad?.trim()) {
    errores.conceptoViabilidad = 'El concepto de viabilidad es obligatorio si la solicitud es viable o no viable.';
  }
  if (!cuerpo.notaValidacion?.trim()) errores.notaValidacion = 'La nota de validación es obligatoria.';
  return errores;
}
