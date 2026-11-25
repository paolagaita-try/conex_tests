/**
 * Contratos DE EJEMPLO con la forma de los `generado/contrato.ts` que escribe el generador de formularios, para las
 * pruebas de la galería. Dominio neutro (solicitud de vacaciones). Vive en `src/pruebas/` (alias `$pruebas`, solo en
 * vitest): no viaja al ZIP.
 *
 * Reúnen a propósito las formas difíciles que un contrato real trae en sus columnas «Obligatorio» y «Constraint»
 * —condiciones «al aprobar», ramas entre paréntesis, la forma inversa «no (sí si …)», notas de implementación,
 * catálogos del módulo con cascada y tope, casillas con motivo, archivos— para que la galería se pruebe contra
 * ellas y no contra un caso fácil. Cuando el proyecto tenga sus contratos generados, sus pruebas de pantalla los
 * usan a ellos.
 */

/** La descripción de un campo, igual que en `generado/contrato.ts`. */
export interface CampoDeContrato {
  readonly ruta: string;
  readonly grupo: string;
  readonly nombre: string;
  readonly tipo: 'TEXT' | 'DECIMAL' | 'INTEGER' | 'BOOLEAN' | 'DATE' | 'FILE';
  readonly multiple: boolean;
  readonly obligatorio: string;
  readonly requeridoSiempre: boolean;
  readonly constraint: string;
  readonly catalogo?: string;
  readonly widget?: 'fichas' | 'desplegable' | 'autocompletar';
  readonly depende?: string;
  readonly tope?: string;
}

/** Las ramas del caso que el contrato nombra entre paréntesis: el tipo de permiso de la solicitud. */
export const RAMAS = ['anual', 'horas'] as const;

/** Captura de la solicitud: dos grupos con un campo del mismo nombre, archivo, casillas y listas del módulo. */
export const CAPTURA: readonly CampoDeContrato[] = [
  { ruta: 'solicitud.tipo', grupo: 'solicitud', nombre: 'tipo', tipo: 'TEXT', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: '∈ {anual, horas}' },
  { ruta: 'solicitud.fechaInicio', grupo: 'solicitud', nombre: 'fechaInicio', tipo: 'DATE', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: 'ISO 8601 con zona' },
  { ruta: 'solicitud.dias', grupo: 'solicitud', nombre: 'dias', tipo: 'INTEGER', multiple: false, obligatorio: 'sí (anual)', requeridoSiempre: false, constraint: '> 0' },
  { ruta: 'solicitud.correo', grupo: 'solicitud', nombre: 'correo', tipo: 'TEXT', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: 'formato email' },
  { ruta: 'solicitud.comentario', grupo: 'solicitud', nombre: 'comentario', tipo: 'TEXT', multiple: false, obligatorio: 'no', requeridoSiempre: false, constraint: '≤ 500' },
  { ruta: 'solicitud.datosExtra', grupo: 'solicitud', nombre: 'datosExtra', tipo: 'TEXT', multiple: false, obligatorio: 'no', requeridoSiempre: false, constraint: 'JSON válido' },
  { ruta: 'solicitud.justificante', grupo: 'solicitud', nombre: 'justificante', tipo: 'FILE', multiple: true, obligatorio: 'sí por perfil (`[PARAM]`)', requeridoSiempre: false, constraint: 'base64' },
  { ruta: 'conformidad.aceptada', grupo: 'conformidad', nombre: 'aceptada', tipo: 'BOOLEAN', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: 'debe ser `true` para continuar' },
  { ruta: 'conformidad.comentario', grupo: 'conformidad', nombre: 'comentario', tipo: 'TEXT', multiple: false, obligatorio: 'no', requeridoSiempre: false, constraint: '≤ 500' },
] as const;

/** La decisión de quien aprueba: condiciones «al aprobar», ramas, excepción y una nota de implementación. */
export const DECISION: readonly CampoDeContrato[] = [
  { ruta: 'decision.resultado', grupo: 'decision', nombre: 'resultado', tipo: 'TEXT', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: '∈ {aprobar, aprobar_condicionado, rechazar, escalar, derivar_por_excepcion}' },
  { ruta: 'decision.diasAprobados', grupo: 'decision', nombre: 'diasAprobados', tipo: 'DECIMAL', multiple: false, obligatorio: 'sí al aprobar', requeridoSiempre: false, constraint: '> 0; DECIMAL (long no aplica a contratos de task — doc contracts)' },
  { ruta: 'decision.anticipoAprobado', grupo: 'decision', nombre: 'anticipoAprobado', tipo: 'DECIMAL', multiple: false, obligatorio: 'sí al aprobar', requeridoSiempre: false, constraint: '> 0' },
  { ruta: 'decision.plazoAprobado', grupo: 'decision', nombre: 'plazoAprobado', tipo: 'INTEGER', multiple: false, obligatorio: 'sí al aprobar (anual)', requeridoSiempre: false, constraint: '∈ catálogo plazos_por_tipo; depende: solicitud.tipo', catalogo: 'plazos_por_tipo', depende: 'solicitud.tipo' },
  { ruta: 'decision.horasAprobadas', grupo: 'decision', nombre: 'horasAprobadas', tipo: 'DECIMAL', multiple: false, obligatorio: 'sí al aprobar (horas)', requeridoSiempre: false, constraint: '> 0' },
  { ruta: 'decision.motivoExcepcion', grupo: 'decision', nombre: 'motivoExcepcion', tipo: 'TEXT', multiple: false, obligatorio: 'sí al derivar por excepción', requeridoSiempre: false, constraint: '≤ 255 (límite del campo BDM)' },
  { ruta: 'decision.sustentoExcepcion', grupo: 'decision', nombre: 'sustentoExcepcion', tipo: 'TEXT', multiple: false, obligatorio: 'sí al derivar por excepción', requeridoSiempre: false, constraint: '≤ 255 (límite del campo BDM)' },
  { ruta: 'decision.justificacion', grupo: 'decision', nombre: 'justificacion', tipo: 'TEXT', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: '≤ 2000' },
] as const;

/** El registro de que el permiso se disfrutó: casilla rectora, la forma inversa y una fecha condicional. */
export const REGISTRO: readonly CampoDeContrato[] = [
  { ruta: 'registro.completado', grupo: 'registro', nombre: 'completado', tipo: 'BOOLEAN', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: '—' },
  { ruta: 'registro.motivo', grupo: 'registro', nombre: 'motivo', tipo: 'TEXT', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: '∈ {disfrutado, cancelado}' },
  { ruta: 'registro.fechaRegistro', grupo: 'registro', nombre: 'fechaRegistro', tipo: 'DATE', multiple: false, obligatorio: 'sí al completar', requeridoSiempre: false, constraint: 'ISO 8601 con zona' },
  { ruta: 'registro.observacion', grupo: 'registro', nombre: 'observacion', tipo: 'TEXT', multiple: false, obligatorio: 'no (sí si no completado)', requeridoSiempre: false, constraint: '≤ 500' },
  { ruta: 'registro.conforme', grupo: 'registro', nombre: 'conforme', tipo: 'BOOLEAN', multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint: 'debe ser `true` (confirmado por la persona)' },
] as const;

/** Los contratos de ejemplo, por pantalla. */
export const CONTRATOS: Readonly<Record<string, readonly CampoDeContrato[]>> = {
  captura: CAPTURA,
  decision: DECISION,
  registro: REGISTRO,
};
