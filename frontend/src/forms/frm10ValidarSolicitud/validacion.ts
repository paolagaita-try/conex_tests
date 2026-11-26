/**
 * Validación de la pantalla antes de enviar. El esquema generado (`generado/esquema.ts`) espeja la matriz;
 * las reglas propias de esta pantalla se añaden aquí. La verdad última es el contrato de Bonita.
 */
import { esquema } from './generado/esquema';
import type { CuerpoDelContrato } from './generado/contrato';

/**
 * Las dos opciones de `concepto_viabilidad` que admite «viable» (constraint `conceptoViabilidad_viable` de
 * `ctr_10_validarSolicitud`, docs/07-bonita/contratos.md, versión 1.4). Son las únicas que ofrece el selector.
 */
export const CONCEPTOS_VIABLE = ['Aprobado (Viable)', 'Aprobado con Condiciones'] as const;

/** El concepto que exige las condiciones (constraint `supuestos_siCondiciones`). */
export const CONCEPTO_CON_CONDICIONES = 'Aprobado con Condiciones';

/**
 * El concepto que fija el proceso para «bloqueado» y «no viable» (`op_10_validarSolicitud.conceptoViabilidad`): el
 * formulario no muestra el selector y envía el input vacío.
 */
export const CONCEPTO_FIJADO: Readonly<Record<string, string>> = {
  bloqueado: 'Requiere más información',
  no_viable: 'No Viable (Rechazado)',
};

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
 * Reglas propias de la pantalla, que espejan las constraints del contrato: con «viable» el concepto es «Aprobado
 * (Viable)» o «Aprobado con Condiciones»; con «bloqueado» o «no viable» va vacío o es el que fija el proceso; y
 * «Aprobado con Condiciones» exige las condiciones (supuestos).
 */
export function erroresDePantalla(cuerpo: CuerpoDelContrato): Record<string, string> {
  const errores = erroresDe(cuerpo);
  if (cuerpo.resultado === null) errores.resultado = 'Elija el resultado de la validación.';
  const concepto = cuerpo.conceptoViabilidad ?? '';
  if (cuerpo.resultado === 'viable') {
    if (!(CONCEPTOS_VIABLE as readonly string[]).includes(concepto)) {
      errores.conceptoViabilidad =
        'Si la solicitud es viable, el concepto debe ser Aprobado (Viable) o Aprobado con Condiciones.';
    }
  } else if (cuerpo.resultado !== null && cuerpo.resultado in CONCEPTO_FIJADO) {
    const fijado = CONCEPTO_FIJADO[cuerpo.resultado];
    if (concepto !== '' && concepto !== fijado) {
      errores.conceptoViabilidad = `Con este resultado el concepto lo fija el proceso (${fijado}).`;
    }
  }
  if (concepto === CONCEPTO_CON_CONDICIONES && !cuerpo.supuestos?.trim()) {
    errores.supuestos = 'Si el concepto es Aprobado con Condiciones, escriba las condiciones.';
  }
  if (!cuerpo.notaValidacion?.trim()) errores.notaValidacion = 'La nota de validación es obligatoria.';
  return errores;
}
