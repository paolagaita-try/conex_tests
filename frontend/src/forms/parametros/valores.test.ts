/** Validar el valor de un parámetro contra su definición, con la expectativa escrita aquí. */
import { describe, expect, it } from 'vitest';
import { DEFINICIONES } from './ejemplo';
import { rangoLegible, validarValor } from './valores';
import { valorLegible, numeroLegible, fechaLegible, valorParaEditar } from './formatos';

const porcentaje = DEFINICIONES.find((d) => d.codigo === 'porcentaje_beca')!;
const tope = DEFINICIONES.find((d) => d.codigo === 'tope_coordinador')!;

describe('el rango se dice en lenguaje de negocio', () => {
  it('«Entre 20 % y 60 %, con un decimal como máximo.»', () => {
    expect(rangoLegible(porcentaje)).toBe('Entre 20 % y 60 %, con un decimal como máximo.');
  });
  it('un monto sin decimales lo dice con su moneda', () => {
    expect(rangoLegible(tope)).toBe('Entre US$100,000 y US$10,000,000, sin decimales.');
  });
});

describe('validar lo tecleado', () => {
  it('un valor dentro del rango y de los decimales vale y se canoniza', () => {
    expect(validarValor(porcentaje, '30')).toEqual({ ok: true, canonico: '30' });
    expect(validarValor(porcentaje, '35.5')).toEqual({ ok: true, canonico: '35.5' });
    expect(validarValor(tope, '2,350,000')).toEqual({ ok: true, canonico: '2350000' });
  });

  it('los extremos del rango valen y un paso más allá, no', () => {
    expect(validarValor(porcentaje, '20').ok).toBe(true);
    expect(validarValor(porcentaje, '60').ok).toBe(true);
    expect(validarValor(porcentaje, '19.9').ok).toBe(false);
    expect(validarValor(porcentaje, '60.1').ok).toBe(false);
  });

  it('65 % fuera de 20–60 % no vale y el mensaje trae el rango permitido', () => {
    expect(validarValor(porcentaje, '65')).toEqual({ ok: false, mensaje: 'Entre 20 % y 60 %, con un decimal como máximo.' });
  });

  it('más decimales de los permitidos no vale (no se redondea)', () => {
    expect(validarValor(porcentaje, '35.55')).toEqual({ ok: false, mensaje: 'Entre 20 % y 60 %, con un decimal como máximo.' });
    expect(validarValor(tope, '1500000.5').ok).toBe(false);
  });

  it('lo que no es un número no vale, ni el separador de miles mal puesto', () => {
    for (const malo of ['', '  ', 'abc', '3 0', '2.350.000', '1,5', '--3']) expect(validarValor(porcentaje, malo).ok, malo).toBe(false);
  });
});

describe('escribir un valor para quien lo lee', () => {
  it('cada tipo con su unidad', () => {
    expect(valorLegible(porcentaje, '35')).toBe('35 %');
    expect(valorLegible(tope, '1500000')).toBe('US$1,500,000');
    expect(valorLegible({ tipoDato: 'ENTERO', unidad: 'meses' }, '36')).toBe('36 meses');
    expect(valorLegible({ tipoDato: 'BOOLEANO', unidad: null }, 'true')).toBe('Sí');
    expect(valorLegible({ tipoDato: 'FECHA', unidad: null }, '2026-10-31')).toBe('31 oct 2026');
    expect(valorLegible(porcentaje, null)).toBe('—');
  });
  it('los miles se agrupan de a tres desde la derecha y los ceros finales no se escriben', () => {
    expect(numeroLegible('1')).toBe('1');
    expect(numeroLegible('1000')).toBe('1,000');
    expect(numeroLegible('1234567.50')).toBe('1,234,567.5');
    expect(numeroLegible('-1500000')).toBe('-1,500,000');
    expect(numeroLegible('100.00')).toBe('100');
  });
  it('una fecha que no es canónica se devuelve tal cual', () => {
    expect(fechaLegible('mañana')).toBe('mañana');
  });
  it('para el campo de edición sin ceros finales', () => {
    expect(valorParaEditar('35.0')).toBe('35');
    expect(valorParaEditar('1500000')).toBe('1500000');
    expect(valorParaEditar(null)).toBe('');
  });
});
