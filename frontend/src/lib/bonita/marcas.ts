/**
 * Números con MARCA que produce el cliente de Bonita: no son cifras de negocio y no se calculan en una pantalla.
 *
 * Cada marca la pone una sola productora, que copia el número de donde sale (la respuesta, la longitud de una
 * lista, el total que declara el motor): un número calculado no la tiene y no compila donde se pide la marca.
 */

declare const deCodigoHttp: unique symbol;
/** El código HTTP de un error de la plataforma. Solo `codigoHttpDe` lo produce, copiando `status` de la respuesta. */
export type CodigoHttp = number & { readonly [deCodigoHttp]: typeof deCodigoHttp };

/** La productora del código HTTP: copia `status` de la respuesta, no calcula nada. */
export function codigoHttpDe(respuesta: { readonly status: number } | null): CodigoHttp | null {
  return (respuesta?.status ?? null) as CodigoHttp | null;
}

declare const deRecuento: unique symbol;
/**
 * Cuántos hay de algo que la pantalla cuenta (filas, tareas, casos). Lo producen `recuentoDe` (la longitud de una
 * lista), el lector paginado (el total que declara el motor) y las operaciones entre recuentos.
 */
export type Recuento = number & { readonly [deRecuento]: typeof deRecuento };

/**
 * La productora del recuento: copia la longitud de la lista, no calcula nada. Una lista da un recuento y `null` da
 * `null`.
 */
export function recuentoDe<L extends readonly unknown[] | null>(lista: L): L extends null ? null : Recuento {
  return (lista?.length ?? null) as L extends null ? null : Recuento;
}

/** La suma de recuentos: solo recuentos entran, así que solo un recuento sale. */
export function sumaDeRecuentos(...partes: readonly Recuento[]): Recuento {
  return partes.reduce((total, parte) => total + parte, 0) as Recuento;
}

/** Lo que queda de un recuento al quitarle otro, nunca por debajo de cero. */
export function restaDeRecuentos(de: Recuento, quitar: Recuento): Recuento {
  return Math.max(0, de - quitar) as Recuento;
}
