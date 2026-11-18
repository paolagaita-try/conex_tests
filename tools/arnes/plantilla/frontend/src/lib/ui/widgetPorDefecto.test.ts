import { describe, expect, it } from 'vitest';
import { widgetPorDefecto } from './widgetPorDefecto';

/**
 * La regla de widget por defecto.
 *
 * La expectativa se escribe AQUÍ, a mano, desde la tabla de la regla de widget por defecto:
 *
 *   | Lista o dato        | Widget por defecto          |
 *   | 2–5 opciones        | Opciones en ficha         |
 *   | 6–15 opciones       | Desplegable                 |
 *   | Más de 15 opciones  | Autocompletar               |
 *   | Sí/no de estado     | Interruptor                 |
 *   | Consentimiento      | Casilla                     |
 *   | Fecha               | Calendario                  |
 *   | Monto o porcentaje  | Campo con prefijo o sufijo  |
 *
 * y «el contrato de la tarea puede elegir otro de forma explícita». Importarla del módulo haría el
 * test tautológico: no podría detectar una fila cambiada.
 */
describe('la tabla de la regla', () => {
  it.each([
    [{ clase: 'lista', opciones: 2 }, 'fichas'],
    [{ clase: 'lista', opciones: 4 }, 'fichas'],
    [{ clase: 'lista', opciones: 10 }, 'desplegable'],
    [{ clase: 'lista', opciones: 40 }, 'autocompletar'],
    [{ clase: 'booleano', sentido: 'estado' }, 'interruptor'],
    [{ clase: 'booleano', sentido: 'consentimiento' }, 'casilla'],
    [{ clase: 'fecha' }, 'calendario'],
    [{ clase: 'monto' }, 'afijo'],
    [{ clase: 'porcentaje' }, 'afijo'],
  ] as const)('%o → %s', (dato, esperado) => {
    expect(widgetPorDefecto(dato)).toBe(esperado);
  });
});

describe('los bordes de la tabla', () => {
  it.each([
    [5, 'fichas'],
    [6, 'desplegable'],
    [15, 'desplegable'],
    [16, 'autocompletar'],
  ] as const)('%i opciones → %s', (opciones, esperado) => {
    expect(widgetPorDefecto({ clase: 'lista', opciones })).toBe(esperado);
  });
});

describe('gana el widget declarado por el contrato', () => {
  it('una lista de 3 que el contrato quiere en desplegable', () => {
    expect(widgetPorDefecto({ clase: 'lista', opciones: 3 }, 'desplegable')).toBe('desplegable');
  });

  it('un sí/no de estado que el contrato quiere como casilla', () => {
    expect(widgetPorDefecto({ clase: 'booleano', sentido: 'estado' }, 'casilla')).toBe('casilla');
  });

  it('un widget declarado que no existe es un error del contrato, no un widget inventado', () => {
    expect(() => widgetPorDefecto({ clase: 'fecha' }, 'ruleta' as never)).toThrow(/ruleta/);
  });
});

describe('caso raro · un dato que la tabla no clasifica', () => {
  it('un sí/no sin decir si es estado o consentimiento → casilla (el acto explícito)', () => {
    expect(widgetPorDefecto({ clase: 'booleano' })).toBe('casilla');
  });

  it('una lista de 0 o 1 opciones → desplegable (no hay elección que enseñar en fichas)', () => {
    expect(widgetPorDefecto({ clase: 'lista', opciones: 0 })).toBe('desplegable');
    expect(widgetPorDefecto({ clase: 'lista', opciones: 1 })).toBe('desplegable');
  });

  it('un sentido de booleano mal escrito se rechaza, no cae en casilla en silencio (N1, gemela de H4)', () => {
    for (const sentido of ['Estado', 'estdo', 42]) {
      expect(() => widgetPorDefecto({ clase: 'booleano', sentido } as never)).toThrow(RangeError);
    }
  });

  it('una clase de dato desconocida se rechaza', () => {
    expect(() => widgetPorDefecto({ clase: 'texto' } as never)).toThrow(RangeError);
  });

  it('un número de opciones inválido se rechaza', () => {
    for (const opciones of [-1, 2.5, Number.NaN]) {
      expect(() => widgetPorDefecto({ clase: 'lista', opciones })).toThrow(RangeError);
    }
  });
});
