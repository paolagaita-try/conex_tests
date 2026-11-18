import { afterEach, describe, expect, it, vi } from 'vitest';
import { entenderValores, LecturaFallida, leerValores, rutaDeValores } from './opciones';

/**
 * La lectura de opciones del módulo. Lo que importa de este módulo no es que
 * funcione cuando todo va bien sino que NUNCA devuelva «una lista» cuando algo salió mal: un fallo
 * disfrazado de lista vacía sería el texto libre por la puerta de atrás.
 */

const LISTA = {
  definicion: 'modalidad_estudio',
  clase: 'LISTA',
  tipoDato: 'TEXTO',
  opciones: [
    { codigo: 'presencial', etiqueta: 'Presencial', ayuda: null, orden: 1, valor: null },
    { codigo: 'otro', etiqueta: 'Otro', ayuda: 'Otra situación', orden: 2, valor: null },
  ],
};

describe('entenderValores', () => {
  it('lee una lista con sus códigos y etiquetas, y la ayuda solo si la hay', () => {
    expect(entenderValores(LISTA, 'modalidad_estudio')).toEqual({
      clase: 'LISTA',
      opciones: [
        { codigo: 'presencial', etiqueta: 'Presencial' },
        { codigo: 'otro', etiqueta: 'Otro', ayuda: 'Otra situación' },
      ],
    });
  });

  it('lee el valor de un parámetro como el texto que sirvió el servidor, sin convertirlo', () => {
    const r = entenderValores(
      { definicion: 'tope_importe_por_tipo', clase: 'PARAMETRO', tipoDato: 'MONTO', unidad: 'USD', valor: '5000000.00' },
      'tope_importe_por_tipo',
    );
    expect(r).toEqual({ clase: 'PARAMETRO', valor: '5000000.00', unidad: 'USD' });
  });

  it('un parámetro sin valor resuelto es null, no 0 ni cadena vacía', () => {
    const r = entenderValores({ definicion: 'x', clase: 'PARAMETRO', valor: null }, 'x');
    expect(r).toEqual({ clase: 'PARAMETRO', valor: null });
  });

  it.each([
    ['una respuesta que no es un objeto', 'texto'],
    ['una respuesta de otra definición', { ...LISTA, definicion: 'otra' }],
    ['una clase desconocida', { ...LISTA, clase: 'RARA' }],
    ['una lista sin opciones', { definicion: 'modalidad_estudio', clase: 'LISTA' }],
    ['una opción sin código', { ...LISTA, opciones: [{ etiqueta: 'Sin código' }] }],
    ['una opción con código vacío', { ...LISTA, opciones: [{ codigo: '', etiqueta: 'Vacío' }] }],
    ['una opción sin etiqueta', { ...LISTA, opciones: [{ codigo: 'a' }] }],
    ['códigos repetidos', { ...LISTA, opciones: [{ codigo: 'a', etiqueta: 'A' }, { codigo: 'a', etiqueta: 'B' }] }],
    ['un valor numérico donde se espera texto', { definicion: 'x', clase: 'PARAMETRO', valor: 5000000 }],
  ])('rechaza %s como fallo de formato, nunca como lista vacía', (_nombre, crudo) => {
    expect(() => entenderValores(crudo, 'modalidad_estudio')).toThrow(LecturaFallida);
    try {
      entenderValores(crudo, 'modalidad_estudio');
    } catch (e) {
      expect((e as LecturaFallida).motivo).toBe('formato');
    }
  });

  it('una lista legítimamente vacía SÍ es una lista vacía (no confundir con fallo)', () => {
    expect(entenderValores({ ...LISTA, opciones: [] }, 'modalidad_estudio')).toEqual({ clase: 'LISTA', opciones: [] });
  });
});

describe('rutaDeValores', () => {
  it('manda solo definición y tarea, y el padre únicamente cuando lo hay', () => {
    expect(rutaDeValores({ definicion: 'modalidad_estudio', tarea: '77' })).toBe(
      '/extension/parametros/valores?definicion=modalidad_estudio&tarea=77',
    );
    expect(rutaDeValores({ definicion: 'plazos_por_tipo', tarea: '77', padre: 'anual' })).toBe(
      '/extension/parametros/valores?definicion=plazos_por_tipo&tarea=77&padre=anual',
    );
  });

  it('el formulario de instanciación (sin tarea) manda el id de la definición del proceso; con tarea, solo la tarea', () => {
    expect(rutaDeValores({ definicion: 'tipos_ausencia', instanciacion: '6152430123456789012' })).toBe(
      '/extension/parametros/valores?definicion=tipos_ausencia&instanciacion=6152430123456789012',
    );
    expect(rutaDeValores({ definicion: 'a', tarea: '1', instanciacion: '6152430123456789012' })).toBe(
      '/extension/parametros/valores?definicion=a&tarea=1',
    );
  });

  it('un padre vacío no viaja: el servidor lo leería como «padre = *»', () => {
    expect(rutaDeValores({ definicion: 'a', tarea: '1', padre: '' })).toBe('/extension/parametros/valores?definicion=a&tarea=1');
  });

  it('codifica lo que viaja en la dirección', () => {
    expect(rutaDeValores({ definicion: 'a', tarea: '1', padre: 'a&b=c' })).toContain('padre=a%26b%3Dc');
  });
});

describe('leerValores (contra fetch)', () => {
  afterEach(() => vi.unstubAllGlobals());

  function responde(estado: number, cuerpo?: unknown) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), { status: estado })),
    );
  }

  it('devuelve la lista cuando la API responde 200', async () => {
    responde(200, LISTA);
    const r = await leerValores({ definicion: 'modalidad_estudio', tarea: '9' });
    expect(r.clase).toBe('LISTA');
  });

  it.each([403, 404, 500])('un %i es «no-disponible», no una lista', async (estado) => {
    responde(estado, { motivo: 'X' });
    await expect(leerValores({ definicion: 'modalidad_estudio', tarea: '9' })).rejects.toMatchObject({
      name: 'LecturaFallida',
      motivo: 'no-disponible',
    });
  });

  it('una red caída es «sin-respuesta»', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))));
    await expect(leerValores({ definicion: 'modalidad_estudio', tarea: '9' })).rejects.toMatchObject({
      motivo: 'sin-respuesta',
    });
  });

  it('un 200 con basura es «formato»', async () => {
    responde(200, { cosa: 'rara' });
    await expect(leerValores({ definicion: 'modalidad_estudio', tarea: '9' })).rejects.toMatchObject({ motivo: 'formato' });
  });
});
