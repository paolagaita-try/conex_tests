import { describe, expect, it } from 'vitest';
import { codigoHttpDe, recuentoDe, restaDeRecuentos, sumaDeRecuentos } from '$lib/bonita/marcas';
import { codigoDeError, limiteDeContrato, maximoDeAyuda, ordinal, recuento, simboloDeMoneda } from './formato';

/**
 * Los formatos de los números que NO son cifras de negocio (el código HTTP de un error, un recuento, un ordinal, el
 * límite de un contrato) y el máximo de un importe como ayuda. La expectativa es la forma que sustituyen —la
 * plantilla `${n}`—: pasar por el formato no puede cambiar lo que se ve.
 */
describe('formatos de números que no son cifras de negocio', () => {
  it('el código HTTP de un error, tal cual; y el 0 de «sin respuesta»', () => {
    for (const estado of [400, 403, 404, 500, 503]) expect(codigoDeError(codigoHttpDe({ status: estado })!)).toBe(`${estado}`);
    expect(codigoDeError(0)).toBe('0');
  });

  it("el orden de una entrada de un índice, como `String(i + 1).padStart(2, '0')`", () => {
    for (const n of [1, 2, 9, 10, 11, 99]) expect(ordinal(n)).toBe(String(n).padStart(2, '0'));
  });

  it('un ordinal fuera de 1–99 no se pinta', () => {
    for (const n of [0, 100, 1_000_000, 2.5, -1]) expect(ordinal(n)).toBe('—');
  });

  it('el límite que declara la restricción de un contrato, con punto de miles', () => {
    const conMiles = (n: number) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    for (const n of [0, 5, 255, 500, 999, 1000, 2000, 65535, 1234567]) expect(limiteDeContrato(n)).toBe(conMiles(n));
    expect(limiteDeContrato(2000)).toBe('2.000');
  });

  it('un recuento: de una lista, sumado o restado solo con otros recuentos', () => {
    const tres = recuentoDe(['a', 'b', 'c']);
    const uno = recuentoDe(['x']);
    expect(recuento(tres)).toBe('3');
    expect(recuento(sumaDeRecuentos(tres, uno))).toBe('4');
    expect(recuento(restaDeRecuentos(uno, tres))).toBe('0');
    expect(recuento(recuentoDe(Array.from({ length: 1234 })))).toBe('1234');
    expect(recuentoDe(null)).toBeNull();
  });
});

/** Un número calculado no entra en un formato de lo que no es cifra (lo ejercita `npm run check`). */
describe('un número calculado no entra en un formato de lo que no es cifra', () => {
  it('código de error, recuento y sus operaciones rechazan un número a secas', () => {
    const calculado = 2_000_000 / 2;
    // @ts-expect-error — un número calculado no es un código HTTP de la respuesta.
    codigoDeError(calculado);
    // @ts-expect-error — un número calculado no es un recuento.
    recuento(calculado);
    // @ts-expect-error — los recuentos solo se combinan con recuentos.
    restaDeRecuentos(calculado, recuentoDe([]));
    // @ts-expect-error — ni en la suma.
    sumaDeRecuentos(calculado);
    // @ts-expect-error — un literal no es un código de la respuesta.
    codigoDeError(500);
    // @ts-expect-error — un literal no es un recuento.
    recuento(3);
    expect(calculado).toBe(1_000_000);
  });
});

describe('el máximo de un importe, como ayuda del campo', () => {
  it('«Máximo $X» con el formato del importe del proyecto (miles con coma, sin decimales)', () => {
    expect(maximoDeAyuda(5_000_000)).toBe('Máximo $5,000,000');
    expect(maximoDeAyuda(950)).toBe('Máximo $950');
  });

  it('sin decimales: un máximo con céntimos se redondea como cualquier importe', () => {
    expect(maximoDeAyuda(5_000_000.4)).toBe('Máximo $5,000,000');
  });

  it('lo que no es un importe finito y positivo no dice nada (ni «Máximo —» ni un 0 inventado)', () => {
    for (const v of [0, -1, Number.NaN, Number.POSITIVE_INFINITY]) expect(maximoDeAyuda(v)).toBeNull();
  });

  it('el símbolo de la moneda es el que el locale pone delante del importe', () => {
    expect(maximoDeAyuda(1)).toBe(`Máximo ${simboloDeMoneda()}1`);
  });
});
