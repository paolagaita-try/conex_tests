/**
 * «Dónde se usa» identificado por CÓDIGO, no por etiqueta: opciones homónimas, la frase exacta del diálogo, la clave de las filas y el cliente
 * leyendo cada cifra de su campo. Siempre con cifras distintas entre sí, para que intercambiarlas o confundir filas haga fallar.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import PanelDeUsos from './componentes/PanelDeUsos.svelte';
import { crearKit } from './api';
import { construirVistaPrevia } from './importar';
import { ACT_PAGO, kitDeEjemplo, PROCESO } from './ejemplo';
import { hashDe } from './ruta';
import { usosVM } from './usos';
import * as T from './textos';
import type { Usos } from './kit';

beforeEach(() => {
  location.hash = '';
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const VIAS = { proceso: PROCESO, actividad: ACT_PAGO };

async function dialogoDe(codigo: string, usos: Usos): Promise<string> {
  location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'valores' });
  render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', homonimos: true, usos }) });
  const fila = await screen.findByTestId(`opcion-${codigo}`);
  await fireEvent.click(within(fila).getByRole('button', { name: T.DESACTIVAR }));
  const aviso = await screen.findByTestId('usos-de-la-opcion');
  await waitFor(() => expect(aviso.textContent).toContain('Se usa en'));
  return aviso.textContent ?? '';
}

describe('el diálogo «Desactivar» lee SU fila aunque otra opción se llame igual', () => {
  const usos: Usos = {
    lugares: [],
    expedientes: [
      { codigo: 'aaa_homonimo', guardados: '40', enCurso: '9' },
      { codigo: 'empleado_privado', guardados: '1', enCurso: '1' },
      { codigo: 'cheque', guardados: '198', enCurso: '11' },
    ],
  };
  it('empleado_privado (1 y 1), aunque aaa_homonimo (40 y 9) tenga la misma etiqueta y salga antes', async () => {
    expect(await dialogoDe('empleado_privado', usos)).toContain('1 expediente guardado la eligió, 1 sigue en curso.');
  });
  it('y al revés: aaa_homonimo lee 40 y 9', async () => {
    expect(await dialogoDe('aaa_homonimo', usos)).toContain('40 expedientes guardados la eligieron, 9 siguen en curso.');
  });
  it('la frase exacta lleva los guardados primero y los en curso después, con concordancia', async () => {
    const t = await dialogoDe('cheque', usos);
    expect(t).toContain('198 expedientes guardados la eligieron, 11 siguen en curso.');
    expect(t).not.toContain('11 expedientes guardados');
  });
});

describe('la frase del diálogo', () => {
  it.each([
    ['198', '11', '198 expedientes guardados la eligieron, 11 siguen en curso.'],
    ['1', '1', '1 expediente guardado la eligió, 1 sigue en curso.'],
    ['1', '7', '1 expediente guardado la eligió, 7 siguen en curso.'],
    ['0', '1', '0 expedientes guardados la eligieron, 1 sigue en curso.'],
  ])('%s guardados y %s en curso', (g, e, frase) => expect(T.DESACTIVAR_EXPEDIENTES(g, e)).toBe(frase));
});

describe('la baja por padre', () => {
  it('en un parámetro por modalidad (código `*`, opción en `codigoPadre`) busca la opción por el padre', () => {
    const previa = { resumen: { altas: 0, cambios: 0, bajas: 1, sinCambios: 0, propuestas: 0, errores: 0 }, huella: 'h', filas: [{ fila: 2, clase: 'BAJA', definicion: 'tope_beca_modalidad', proceso: '*', actividad: '*', codigoPadre: 'curso', codigo: '*', detalle: 'se desactiva, no se borra' }] } as never;
    const usos: Usos = { lugares: [], expedientes: [{ codigo: 'taller', guardados: '9', enCurso: '8' }, { codigo: 'curso', guardados: '5', enCurso: '3' }] };
    expect(construirVistaPrevia(previa, [{ codigo: 'tope_beca_modalidad', nombre: 'Tope' }] as never, {}, {}, new Map([['tope_beca_modalidad', usos]])).filas[0]!.detalle).toContain('La usan 5 expedientes guardados y 3 en curso.');
  });
});

describe('el panel: vacío, claves y homónimos', () => {
  it('con lugares y SIN expedientes no dice «todavía nadie»: enseña los lugares', () => {
    render(PanelDeUsos, { usos: usosVM({ lugares: [{ tipo: 'FORMULARIO', titulo: 'Preparar pago', detalle: 'Se usó 3 veces.' }], expedientes: [] }, new Map(), new Set()) });
    expect(screen.queryByTestId('usos-vacio')).toBeNull();
    expect(screen.getByTestId('usos-lugares').textContent).toContain('Preparar pago');
  });
  it('dos expedientes con la MISMA etiqueta y distinto código son dos filas', () => {
    const vm = usosVM({ lugares: [], expedientes: [{ codigo: 'a_1', guardados: '1', enCurso: '2' }, { codigo: 'a_2', guardados: '3', enCurso: '4' }] }, new Map([['a_1', 'Igual'], ['a_2', 'Igual']]), new Set());
    render(PanelDeUsos, { usos: vm });
    expect(screen.getByTestId('usos-expedientes').querySelectorAll('tbody tr').length).toBe(2);
  });
  it('dos lugares del mismo título y distinto tipo, o del mismo tipo y distinto título, son cuatro fichas', () => {
    const lugares = [
      { tipo: 'FORMULARIO', titulo: 'Alta', detalle: 'x' },
      { tipo: 'REGLA', titulo: 'Alta', detalle: 'x' },
      { tipo: 'REGLA', titulo: 'Baja', detalle: 'x' },
      { tipo: 'DOCUMENTO', titulo: 'Baja', detalle: 'x' },
    ];
    render(PanelDeUsos, { usos: usosVM({ lugares, expedientes: [] }, new Map(), new Set()) });
    expect(screen.getByTestId('usos-lugares').querySelectorAll('.ficha').length).toBe(4);
    expect(new Set(usosVM({ lugares, expedientes: [] }, new Map(), new Set()).lugares.map((l) => l.clave)).size).toBe(4);
  });
});

describe('el cliente lee cada cifra de SU campo', () => {
  it('guardados y en curso de cada fila, distintos entre sí, y los de «otros»', async () => {
    const cuerpo = { lugares: [], expedientes: [{ codigo: 'a', guardados: '198', enCurso: '11' }, { codigo: 'b', guardados: '7', enCurso: '61' }], otros: { guardados: '5225', enCurso: '12' } };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(cuerpo), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const r = await crearKit().usos('x');
    expect(r.expedientes).toEqual([{ codigo: 'a', guardados: '198', enCurso: '11' }, { codigo: 'b', guardados: '7', enCurso: '61' }]);
    expect(r.otros).toEqual({ guardados: '5225', enCurso: '12' });
  });
});
