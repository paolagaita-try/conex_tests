/**
 * CÓMO se escribe una cifra en pantalla: las constantes de formato de la galería.
 *
 * Aquí está todo lo que un formato necesita y nada que diga algo de negocio: el locale, la moneda, el «sin dato» y
 * los formatos con nombre. El locale y la moneda son del PROYECTO: ajústalos aquí y cambian en todas las pantallas.
 */
import type { CodigoHttp, Recuento } from '$lib/bonita/marcas';

/**
 * El locale de todas las cifras. Ajústalo al del proyecto. Con `es-US` los miles van con «,» y el decimal con «.», la
 * misma convención con la que `numeroTecleado` lee lo que la persona escribe: si cambias una, cambia la otra.
 */
export const LOCALE = 'es-US';

/** La moneda de los importes (ISO 4217). Ajústala a la del proyecto. */
export const MONEDA = 'USD';

/** Lo que se pinta donde no hay cifra. Nunca 0 ni `NaN`. */
export const SIN_DATO = '—';

/** Separa la cifra de su unidad («36 meses», «18.5 %»). */
export const ESPACIO = ' ';

/** Importes: la moneda del proyecto, sin decimales. */
export const IMPORTE: Intl.NumberFormatOptions = {
  style: 'currency',
  currency: MONEDA,
  maximumFractionDigits: 0,
};

/** El símbolo de la moneda del proyecto en el locale del proyecto («$» en `es-US`): lo que lleva delante un importe. */
export function simboloDeMoneda(): string {
  return new Intl.NumberFormat(LOCALE, IMPORTE).formatToParts(0).find((p) => p.type === 'currency')?.value ?? MONEDA;
}

/** Enteros: el número tal cual, sin separador de miles. */
export const ENTERO: Intl.NumberFormatOptions = {
  useGrouping: false,
  maximumFractionDigits: 0,
};

/** El código HTTP de un error de la plataforma, dentro de un texto: «500». `0` = sin respuesta. */
export function codigoDeError(estado: CodigoHttp | 0): string {
  return new Intl.NumberFormat(LOCALE, ENTERO).format(estado);
}

/** Un recuento, dentro de un texto: «3», sin separador de miles. */
export function recuento(n: Recuento): string {
  return new Intl.NumberFormat(LOCALE, ENTERO).format(n);
}

/** Un ordinal de índice: al menos dos cifras, sin separador de miles. */
const ORDINAL: Intl.NumberFormatOptions = {
  minimumIntegerDigits: 2,
  useGrouping: false,
};

/** Los índices que numera la galería no pasan de aquí: más allá, un «ordinal» ya no es un orden. */
const TOPE_DEL_ORDINAL = 99;

/** El orden de una entrada en un índice, con dos cifras como mínimo: «01». Fuera de 1–99 no pinta un número. */
export function ordinal(n: number): string {
  if (!Number.isInteger(n) || n < 1 || n > TOPE_DEL_ORDINAL) return SIN_DATO;
  return new Intl.NumberFormat(LOCALE, ORDINAL).format(n);
}

/** El separador de miles de un límite de contrato. */
const MILES_DEL_LIMITE = '.';

/**
 * El límite que declara la restricción de un contrato (`≤ 2000` → «2.000»), dentro de «máximo …» o «mínimo …»
 * (`CamposDeContrato`). El separador se compone a mano en vez de con `Intl`: el formateo por locale depende del ICU
 * del entorno, y un límite debe leerse igual en la pantalla y en el test que la vigila.
 */
export function limiteDeContrato(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, MILES_DEL_LIMITE);
}

/**
 * El máximo que el módulo de parámetros fija para un importe, dicho como ayuda del campo: «Máximo $5,000,000».
 *
 * La cifra NO se escribe en ninguna pantalla: llega del tope que lee el servidor y aquí solo se le da formato. Lo que
 * no es un importe finito y positivo no dice nada: devuelve `null` y el campo no pinta ayuda, en vez de pintar
 * «Máximo —» o un 0 inventado.
 */
export function maximoDeAyuda(maximo: number): string | null {
  if (!Number.isFinite(maximo) || maximo <= 0) return null;
  return `Máximo${ESPACIO}${new Intl.NumberFormat(LOCALE, IMPORTE).format(maximo)}`;
}
