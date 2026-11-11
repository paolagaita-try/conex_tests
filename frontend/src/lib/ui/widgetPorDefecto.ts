/**
 * La regla de widget por defecto — UNA sola función para que ninguna pantalla la
 * reescriba campo a campo.
 *
 * Es la tabla de la regla de widget por defecto:
 * 2–5 opciones → fichas; 6–15 → desplegable; más de 15 → autocompletar; sí/no de estado →
 * interruptor; consentimiento → casilla; fecha → calendario; monto o porcentaje → campo con afijo.
 * El contrato de la tarea puede declarar otro y entonces gana el
 * declarado. La consumirán `CamposDeContrato` y la vista previa de la app de
 * administración.
 *
 * Lo que la tabla no dice, decidido aquí y no inventado al vuelo:
 *  · un sí/no sin decir si es estado o consentimiento → casilla: el caso conservador, porque una
 *    casilla exige un acto explícito y un interruptor encendido por defecto no;
 *  · una lista de 0 o 1 opciones → desplegable: no hay elección que enseñar en fichas, y el
 *    desplegable con su opción vacía obliga a un acto explícito;
 *  · un número de opciones que no es un entero no negativo, o un widget declarado que no existe,
 *    es un error del dato: se rechaza, no se le busca un widget.
 */

export const WIDGETS = [
  'fichas',
  'desplegable',
  'autocompletar',
  'interruptor',
  'casilla',
  'calendario',
  'afijo',
] as const;

export type Widget = (typeof WIDGETS)[number];

/** Lo que el contrato dice del dato. El generador lo construye desde la anotación del contrato. */
export type DescripcionDelDato =
  | { clase: 'lista'; opciones: number }
  | { clase: 'booleano'; sentido?: 'estado' | 'consentimiento' }
  | { clase: 'fecha' }
  | { clase: 'monto' }
  | { clase: 'porcentaje' };

/** Hasta cuántas opciones van en fichas, y hasta cuántas en desplegable. */
const MAX_FICHAS = 5;
const MAX_DESPLEGABLE = 15;

export function widgetPorDefecto(dato: DescripcionDelDato, declarado?: Widget): Widget {
  if (declarado !== undefined) {
    if (!(WIDGETS as readonly string[]).includes(declarado)) {
      throw new RangeError(`widget declarado desconocido: «${declarado}»`);
    }
    return declarado;
  }
  switch (dato.clase) {
    case 'lista': {
      const n = dato.opciones;
      if (!Number.isInteger(n) || n < 0) {
        throw new RangeError(`número de opciones inválido: ${n}`);
      }
      if (n < 2) return 'desplegable';
      if (n <= MAX_FICHAS) return 'fichas';
      if (n <= MAX_DESPLEGABLE) return 'desplegable';
      return 'autocompletar';
    }
    case 'booleano':
      // Sin sentido declarado → casilla (D-7). Un sentido que NO es ninguno de los dos es un error
      // del contrato: «Estado» o «estdo» no pueden cambiar el widget en silencio (N1, gemela de H4).
      if (dato.sentido !== undefined && dato.sentido !== 'estado' && dato.sentido !== 'consentimiento') {
        throw new RangeError(`sentido de booleano desconocido: «${String(dato.sentido)}»`);
      }
      return dato.sentido === 'estado' ? 'interruptor' : 'casilla';
    case 'fecha':
      return 'calendario';
    case 'monto':
    case 'porcentaje':
      return 'afijo';
    default:
      // Llegará de un JSON de contrato: una clase que la tabla no conoce es un error del
      // dato, no un `undefined` que la pantalla pintaría como nada.
      throw new RangeError(`clase de dato desconocida: «${(dato as { clase: unknown }).clase}»`);
  }
}
