import { describe, expect, it } from 'vitest';
import { contextoDelCaso, enteroDelCodigo, esEntero, registroDeProblemas } from './contrato';

/** Lo que una pantalla con campos anotados necesita para ENVIAR: entero del código, contexto y registro. */
describe('enteroDelCodigo', () => {
  it.each([['36', 36], ['0', 0], ['084', 84], ['12', 12]])('«%s» → %i', (codigo, esperado) => {
    expect(enteroDelCodigo(codigo)).toBe(esperado);
  });

  // Gemelas: lo que NO es un entero escrito en dígitos se manda null (el servidor lo devuelve), nunca un número inventado.
  it.each(['', ' ', '36 ', ' 36', '3.6', '-5', '+5', '1e3', '0x10', '36dias', 'treinta', '٣٦'])(
    '«%s» no es un entero: null',
    (codigo) => {
      expect(enteroDelCodigo(codigo)).toBeNull();
    },
  );
});

describe('esEntero', () => {
  it('solo INTEGER lo es', () => {
    expect(esEntero({ tipo: 'INTEGER' })).toBe(true);
    for (const tipo of ['TEXT', 'DECIMAL', 'BOOLEAN', 'DATE', 'FILE', 'integer', '']) expect(esEntero({ tipo })).toBe(false);
  });
});

describe('contextoDelCaso', () => {
  it('nombra el dato del caso que una cascada puede pedir con la ruta del contrato', () => {
    expect(contextoDelCaso('solicitud.tipo', 'horas')).toEqual({ 'solicitud.tipo': 'horas' });
    expect(contextoDelCaso('solicitud.tipo', undefined)).toEqual({ 'solicitud.tipo': undefined });
  });
});

describe('registroDeProblemas', () => {
  it('empieza vacío', () => {
    expect(registroDeProblemas().hay()).toBe(false);
  });

  it('un problema por ruta lo activa y limpiarlo lo apaga; cada ruta es independiente', () => {
    const r = registroDeProblemas();
    r.registrar('a', 'falló');
    r.registrar('b', 'falló');
    expect(r.hay()).toBe(true);
    r.registrar('a', null);
    expect(r.hay()).toBe(true); // b sigue
    r.registrar('b', null);
    expect(r.hay()).toBe(false);
  });

  it('el mismo problema dos veces no se acumula: con UNA limpieza basta', () => {
    const r = registroDeProblemas();
    r.registrar('a', 'falló');
    r.registrar('a', 'falló otra vez');
    r.registrar('a', null);
    expect(r.hay()).toBe(false);
  });

  it('limpiar lo que no estaba no inventa un problema', () => {
    const r = registroDeProblemas();
    r.registrar('nunca', null);
    expect(r.hay()).toBe(false);
  });

  it('dos registros no comparten estado (una pantalla no bloquea a otra)', () => {
    const a = registroDeProblemas();
    const b = registroDeProblemas();
    a.registrar('x', 'falló');
    expect(b.hay()).toBe(false);
  });
});
