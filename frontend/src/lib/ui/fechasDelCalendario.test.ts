// La zona del proyecto (GMT-4, sin horario de verano). Se fija ANTES de cualquier cálculo: con
// `new Date('2026-10-02')` leído en hora local, el 2 de octubre cae el 1 a las 20:00 — el
// defecto clásico que esta aritmética existe para no tener.
process.env.TZ = 'America/Santo_Domingo';

import { describe, expect, it } from 'vitest';
import {
  aIso,
  aTexto,
  deIso,
  deTexto,
  diaCorto,
  diaDeLaSemana,
  finDeSemana,
  inicioDeSemana,
  mensajeDeError,
  motivoNoElegible,
  nombreCompleto,
  rejillaDelMes,
  sumarDias,
  sumarMeses,
} from './fechasDelCalendario';

/**
 * Los fixtures salen del calendario del diseño (octubre de 2026): la
 * primera fila es «28 29 30 1 2 3 4» bajo «L M X J V S D», así que el 1 es jueves y el 4 domingo,
 * y su error de ejemplo es «El 4 de octubre es domingo: elige un día hábil.». Nada se calcula con
 * el módulo que se prueba.
 */
const d = (a: number, m: number, dia: number) => ({ a, m, d: dia });

describe('texto dd/mm/aaaa e ISO', () => {
  it('lee la fecha que escribe la persona', () => {
    expect(deTexto('02/10/2026')).toEqual(d(2026, 10, 2));
    expect(deTexto(' 2/10/2026 ')).toEqual(d(2026, 10, 2));
  });

  it('rechaza lo que no es una fecha real', () => {
    expect(deTexto('31/02/2026')).toBeNull();
    expect(deTexto('29/02/2026')).toBeNull();
    expect(deTexto('2026-10-02')).toBeNull();
    expect(deTexto('abc')).toBeNull();
    expect(deTexto('')).toBeNull();
    expect(deTexto('00/10/2026')).toBeNull();
    expect(deTexto('10/13/2026')).toBeNull();
  });

  it('acepta el 29 de febrero de un año bisiesto', () => {
    expect(deTexto('29/02/2024')).toEqual(d(2024, 2, 29));
  });

  it('escribe y lee el ISO que viaja al contrato', () => {
    expect(aIso(d(2026, 10, 2))).toBe('2026-10-02');
    expect(deIso('2026-10-02')).toEqual(d(2026, 10, 2));
    expect(deIso('2026-02-30')).toBeNull();
    expect(aTexto(d(2026, 1, 5))).toBe('05/01/2026');
  });
});

describe('el pie del calendario (diseño aprobado: «Hoy: 29 sep · Hasta el 29 oct»)', () => {
  it('dice el día con el mes abreviado', () => {
    expect(diaCorto(d(2026, 9, 29))).toBe('29 sep');
    expect(diaCorto(d(2026, 10, 29))).toBe('29 oct');
    expect(diaCorto(d(2027, 1, 5))).toBe('5 ene');
  });
});

describe('sin zona horaria', () => {
  it('el 2 de octubre de 2026 es viernes también a las 20:00 de Santo Domingo', () => {
    expect(diaDeLaSemana(d(2026, 10, 2))).toBe(5);
    expect(nombreCompleto(d(2026, 10, 2))).toBe('viernes, 2 de octubre de 2026');
    expect(diaDeLaSemana(d(2026, 10, 4))).toBe(0);
  });
});

describe('moverse por la rejilla', () => {
  it('suma días cruzando mes y año', () => {
    expect(sumarDias(d(2026, 12, 31), 1)).toEqual(d(2027, 1, 1));
    expect(sumarDias(d(2026, 10, 1), -1)).toEqual(d(2026, 9, 30));
    expect(sumarDias(d(2026, 10, 2), 7)).toEqual(d(2026, 10, 9));
  });

  it('suma meses sin saltarse el mes corto', () => {
    expect(sumarMeses(d(2026, 1, 31), 1)).toEqual(d(2026, 2, 28));
    expect(sumarMeses(d(2024, 1, 31), 1)).toEqual(d(2024, 2, 29));
    expect(sumarMeses(d(2026, 12, 15), 1)).toEqual(d(2027, 1, 15));
    expect(sumarMeses(d(2026, 1, 15), -1)).toEqual(d(2025, 12, 15));
  });

  it('la semana va de lunes a domingo', () => {
    expect(inicioDeSemana(d(2026, 10, 4))).toEqual(d(2026, 9, 28));
    expect(finDeSemana(d(2026, 10, 1))).toEqual(d(2026, 10, 4));
    expect(inicioDeSemana(d(2026, 9, 28))).toEqual(d(2026, 9, 28));
  });

  it('octubre de 2026 se pinta como en el diseño aprobado', () => {
    const semanas = rejillaDelMes(2026, 10);
    expect(semanas).toHaveLength(5);
    expect(semanas[0]).toEqual([
      d(2026, 9, 28), d(2026, 9, 29), d(2026, 9, 30),
      d(2026, 10, 1), d(2026, 10, 2), d(2026, 10, 3), d(2026, 10, 4),
    ]);
    expect(semanas[4]).toEqual([
      d(2026, 10, 26), d(2026, 10, 27), d(2026, 10, 28), d(2026, 10, 29),
      d(2026, 10, 30), d(2026, 10, 31), d(2026, 11, 1),
    ]);
  });
});

describe('qué días se pueden elegir', () => {
  const r = {
    minimo: '2026-09-29',
    maximo: '2026-10-29',
    noHabiles: { diasDeLaSemana: [0, 6] as const, fechas: ['2026-10-12'] },
  };

  it('un día hábil dentro del rango se puede elegir', () => {
    expect(motivoNoElegible(d(2026, 10, 2), r)).toBeNull();
    expect(motivoNoElegible(d(2026, 9, 29), r)).toBeNull();
    expect(motivoNoElegible(d(2026, 10, 29), r)).toBeNull();
  });

  it('fuera del rango, por los dos lados', () => {
    expect(motivoNoElegible(d(2026, 9, 28), r)).toBe('antes');
    expect(motivoNoElegible(d(2026, 10, 30), r)).toBe('despues');
  });

  it('un fin de semana o un feriado no son hábiles', () => {
    expect(motivoNoElegible(d(2026, 10, 4), r)).toBe('no-habil');
    expect(motivoNoElegible(d(2026, 10, 12), r)).toBe('no-habil');
  });

  it('sin restricciones, todo día se puede elegir', () => {
    expect(motivoNoElegible(d(2026, 10, 4), {})).toBeNull();
  });
});

describe('el error que se le dice a la persona', () => {
  const r = {
    minimo: '2026-09-29',
    maximo: '2026-10-29',
    noHabiles: { diasDeLaSemana: [0, 6] as const, fechas: ['2026-10-12'] },
  };

  it('un domingo, con el texto del diseño aprobado', () => {
    expect(mensajeDeError('04/10/2026', r)).toBe('El 4 de octubre es domingo: elige un día hábil.');
  });

  it('un feriado', () => {
    expect(mensajeDeError('12/10/2026', r)).toBe('El 12 de octubre es feriado: elige un día hábil.');
  });

  it('fuera de rango', () => {
    expect(mensajeDeError('30/10/2026', r)).toBe(
      'Elige una fecha entre el 29 de septiembre de 2026 y el 29 de octubre de 2026.',
    );
    expect(mensajeDeError('30/10/2026', { maximo: '2026-10-29' })).toBe(
      'Elige una fecha hasta el 29 de octubre de 2026.',
    );
    expect(mensajeDeError('28/09/2026', { minimo: '2026-09-29' })).toBe(
      'Elige una fecha desde el 29 de septiembre de 2026.',
    );
  });

  it('un formato que no es fecha', () => {
    expect(mensajeDeError('2026-10-04', r)).toBe('Escribe la fecha como dd/mm/aaaa.');
    expect(mensajeDeError('31/02/2026', r)).toBe('Escribe la fecha como dd/mm/aaaa.');
  });

  it('una fecha válida no tiene error, y el vacío tampoco (lo obligatorio lo dice la pantalla)', () => {
    expect(mensajeDeError('02/10/2026', r)).toBeNull();
    expect(mensajeDeError('', r)).toBeNull();
  });
});
