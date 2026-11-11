import { describe, expect, it } from 'vitest';

import {
  comoArchivo,
  comoBooleano,
  comoTexto,
  comoTextoONumero,
  numeroTecleado,
  tecleadoDeEjemplo,
  textoDe,
  type ValorDeCampo,
  type ValoresDelFormulario,
} from './valores';

/**
 * Lo que la persona teclea, con su tipo. Las barreras de compilador de abajo son permanentes: si
 * un número calculado volviera a entrar en los valores del formulario, la directiva quedaría sin usar y
 * `npm run check` fallaría.
 */

describe('el número que la persona escribió', () => {
  it('se lee con los miles de `es-US` y punto decimal, como lo leía `CampoConAfijo`', () => {
    expect(numeroTecleado('2,350,000.50')).toBe(2350000.5);
    expect(numeroTecleado('850000')).toBe(850000);
    expect(numeroTecleado('  48 ')).toBe(48);
    expect(numeroTecleado('-3.25')).toBe(-3.25);
  });

  it('lo que no está escrito así no se adivina: `null`', () => {
    for (const texto of ['2.350.000', '1,00', '12,34,567', 'abc', '', '1e6', '0x10']) {
      expect(numeroTecleado(texto), texto).toBeNull();
    }
  });
});

describe('cada widget recibe su valor estrechado por `typeof`, sin `as`', () => {
  const archivo = { nombre: 'justificante.pdf', contenido: 'JVBERi0=' };
  const tecleado = numeroTecleado('850000');

  it('texto, número, casilla y archivo: el suyo pasa, lo demás llega vacío', () => {
    const casos: [ValorDeCampo, unknown, unknown, unknown, unknown][] = [
      ['hola', 'hola', 'hola', undefined, undefined],
      [tecleado, undefined, tecleado, undefined, undefined],
      [true, undefined, undefined, true, undefined],
      [archivo, undefined, undefined, undefined, archivo],
      [null, null, null, null, null],
      [undefined, undefined, undefined, undefined, undefined],
    ];
    for (const [v, texto, textoONumero, booleano, deArchivo] of casos) {
      expect(comoTexto(v)).toBe(texto);
      expect(comoTextoONumero(v)).toBe(textoONumero);
      expect(comoBooleano(v)).toBe(booleano);
      expect(comoArchivo(v)).toBe(deArchivo);
    }
  });

  it('el texto para el contrato es la cadena del campo; un número no se convierte aquí', () => {
    expect(textoDe('001-1234567-8')).toBe('001-1234567-8');
    expect(textoDe(tecleado)).toBe('');
    expect(textoDe(null)).toBe('');
    expect(textoDe(undefined)).toBe('');
  });
});

describe('los ejemplos de la galería y la muestra', () => {
  it('entran como tecleados', () => {
    expect(tecleadoDeEjemplo(850_000)).toBe(850000);
    expect(tecleadoDeEjemplo(14.5)).toBe(14.5);
  });

  it('solo como literales: un número calculado no compila', () => {
    const calculado = 2_000_000 / 2;
    // @ts-expect-error — un número calculado no es un ejemplo
    tecleadoDeEjemplo(calculado);
  });
});

describe('barrera de compilador: un número calculado no entra en los valores del formulario', () => {
  it('ni en un campo ni en el conjunto', () => {
    // @ts-expect-error — un número a secas no es un valor de campo: solo uno tecleado
    const campo: ValorDeCampo = 25;
    const valores: ValoresDelFormulario = { 'decision.diasAprobados': numeroTecleado('25') };
    // @ts-expect-error — tampoco por la ruta de un campo
    valores['decision.diasAprobados'] = 50 / 2;
    expect([campo, valores]).toBeDefined();
  });
});
