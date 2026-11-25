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
