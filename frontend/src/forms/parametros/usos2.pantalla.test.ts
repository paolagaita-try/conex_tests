/**
 * Qué cifra va en qué columna y con qué nombre: «Dónde se usa» en el panel, en la aprobación y en la baja. Cada barrera se prueba con
 * cifras DISTINTAS entre sí (guardados ≠ en curso ≠ otros), para que intercambiarlas, repetirlas o perderlas haga fallar.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import PanelDeUsos from './componentes/PanelDeUsos.svelte';
import { construirVistaPrevia } from './importar';
import { kitDeEjemplo, PROCESO } from './ejemplo';
import { hashDe } from './ruta';
import { etiquetasDeOpciones, usosVM } from './usos';
import type { Usos } from './kit';
import type { Propuesta } from './tipos';

beforeEach(() => {
  location.hash = '';
});
afterEach(cleanup);

const celdas = (tr: HTMLElement) => [...tr.querySelectorAll('td')].map((td) => td.textContent?.trim() ?? '');

describe('el panel: cada cifra en su columna', () => {
  const usos: Usos = {
    lugares: [],
    expedientes: [
      { codigo: 'a', guardados: '198', enCurso: '11' },
      { codigo: 'fuera_1', guardados: '37', enCurso: '5', fueraDeLista: true, etiqueta: 'fuera_1' },
    ],
    otros: { guardados: '5225', enCurso: '12' },
  };
  it('guardados es la 2.ª columna y en curso la 3.ª, en cada fila y en «otros»', () => {
    render(PanelDeUsos, { usos: usosVM(usos, new Map([['a', 'Opción A']]), new Set()) });
    const filas = [...screen.getByTestId('usos-expedientes').querySelectorAll('tbody tr')] as HTMLElement[];
    expect(celdas(filas[0]!).slice(1)).toEqual(['198', '11']);
    expect(celdas(filas[1]!).slice(1)).toEqual(['37', '5']);
    expect(celdas(screen.getByTestId('usos-otros')).slice(1)).toEqual(['5225', '12']);
  });
  it('el chip «Fuera de la lista» está en la fila de fuera y SOLO en ella', () => {
    render(PanelDeUsos, { usos: usosVM(usos, new Map([['a', 'Opción A']]), new Set()) });
    const filas = [...screen.getByTestId('usos-expedientes').querySelectorAll('tbody tr')] as HTMLElement[];
    expect(filas[0]!.textContent).not.toContain('Fuera de la lista');
    expect(filas[1]!.textContent).toContain('Fuera de la lista');
  });
});

describe('la aprobación: «dónde se usa» con cifras y nombres', () => {
  const propuesta: Propuesta = {
    id: 9100, definicion: 'vias_pago', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: 'cheque', accion: 'EDITAR', valorAnterior: [{ valor: '1' }],
    valorPropuesto: { accion: 'EDITAR', definicion: 'vias_pago', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: 'cheque', datos: { valor: '2' } } as never,
    proponente: 'luis.gil', motivo: 'Prueba.', estado: 'PENDIENTE', aprobador: null, comentario: null, creadaEn: '2026-10-05T10:00:00.000Z', resueltaEn: null, persistenceVersion: 0, esPropia: false, puedesAprobar: true,
  };
  async function abrirConUsos(usos: Usos) {
    location.hash = hashDe({ vista: 'aprobaciones' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', usos, propuestasAdicionales: [propuesta] }) });
    const grupo = await screen.findByTestId('grupo-esperan', {}, { timeout: 3000 });
    await fireEvent.click([...grupo.querySelectorAll('button.fila')].find((b) => /Vías de pago/.test(b.textContent ?? ''))!);
    return screen.findByTestId('usos-de-la-aprobacion', {}, { timeout: 3000 });
  }

  it('cada fila dice la etiqueta de la opción y SUS expedientes en curso (no los guardados)', async () => {
    const panel = await abrirConUsos({ lugares: [], expedientes: [{ codigo: 'cheque', guardados: '198', enCurso: '11' }, { codigo: 'efectivo', guardados: '73', enCurso: '4' }] });
    await waitFor(() => expect(within(panel).getByTestId('expedientes-en-curso')).toBeInTheDocument());
    const lis = [...within(panel).getByTestId('expedientes-en-curso').querySelectorAll('li')];
    expect(lis.map((li) => li.textContent)).toEqual(['Cheque de administración: 11', 'Pago en caja: 4']);
  });

  it('con `otros` SOLO: pinta la fila agregada con su en curso y no dice que el módulo no lo informa', async () => {
    const panel = await abrirConUsos({ lugares: [], expedientes: [], otros: { guardados: '5225', enCurso: '12' } });
    await waitFor(() => expect(within(panel).getByTestId('usos-otros-aprobacion')).toBeInTheDocument());
    expect(within(panel).getByTestId('usos-otros-aprobacion').textContent).toBe('Otros códigos fuera de la lista (agrupados): 12');
    expect(within(panel).queryByTestId('expedientes-afectados-sin-dato')).toBeNull();
  });

  it('con filas Y `otros`: cada cifra en su sitio, la de «otros» la última', async () => {
    const panel = await abrirConUsos({ lugares: [], expedientes: [{ codigo: 'cheque', guardados: '198', enCurso: '11' }], otros: { guardados: '5225', enCurso: '12' } });
    await waitFor(() => expect(within(panel).getByTestId('usos-otros-aprobacion')).toBeInTheDocument());
    expect([...within(panel).getByTestId('expedientes-en-curso').querySelectorAll('li')].map((li) => li.textContent)).toEqual(['Cheque de administración: 11', 'Otros códigos fuera de la lista (agrupados): 12']);
    expect(panel.textContent).not.toContain('5225');
    expect(panel.textContent).not.toContain('198');
  });

  it('un parámetro por modalidad: la aprobación nombra la opción por la lista PADRE («Curso en línea»), no «curso»', async () => {
    const porProducto: Propuesta = { ...propuesta, id: 9200, definicion: 'tope_beca_modalidad', codigoPadre: 'curso', codigo: '*', creadaEn: '2026-10-06T10:00:00.000Z' };
    location.hash = hashDe({ vista: 'aprobaciones' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', usos: { lugares: [], expedientes: [{ codigo: 'curso', guardados: '5', enCurso: '3' }] }, propuestasAdicionales: [porProducto] }) });
    const grupo = await screen.findByTestId('grupo-esperan', {}, { timeout: 3000 });
    await fireEvent.click([...grupo.querySelectorAll('button.fila')].find((b) => /Tope de beca por modalidad/.test(b.textContent ?? ''))!);
    const panel = await screen.findByTestId('usos-de-la-aprobacion', {}, { timeout: 3000 });
    await waitFor(() => expect([...within(panel).getByTestId('expedientes-en-curso').querySelectorAll('li')].map((li) => li.textContent)).toEqual(['Curso en línea: 3']));
  });

  it('con filas y `otros` vacíos: sí dice que el módulo no informa los expedientes afectados', async () => {
    const panel = await abrirConUsos({ lugares: [], expedientes: [] });
    await waitFor(() => expect(within(panel).getByTestId('expedientes-afectados-sin-dato')).toBeInTheDocument());
    expect(within(panel).queryByTestId('usos-otros-aprobacion')).toBeNull();
  });
});

describe('etiquetas de las opciones', () => {
  const filas = (xs: Array<[string, string, string | null]>) => ({ filas: xs.map(([codigo, codigoPadre, etiqueta]) => ({ codigo, codigoPadre, etiqueta })) });
  it('en un parámetro por modalidad (fila `*`, opción en `codigoPadre`) el nombre lo da la lista PADRE: «Curso en línea», no «curso»', () => {
    const m = etiquetasDeOpciones('tope_beca_por_modalidad', { tope_beca_por_modalidad: filas([['*', 'curso', null], ['*', 'taller', null]]), modalidad: filas([['curso', '*', 'Curso en línea'], ['taller', '*', 'Taller presencial']]) }, 'modalidad');
    expect(m.get('curso')).toBe('Curso en línea');
    expect(m.get('taller')).toBe('Taller presencial');
  });
  it('una opción propia manda sobre la del padre, y un código del prototipo no resuelve a nada', () => {
    const m = etiquetasDeOpciones('x', { x: filas([['a', '*', 'Mía']]), p: filas([['a', '*', 'Del padre']]) }, 'p');
    expect(m.get('a')).toBe('Mía');
    expect(m.get('constructor')).toBeUndefined();
    expect(m.get('__proto__')).toBeUndefined();
  });
});

describe('la baja: lo que afirma y cuándo', () => {
  const DEFS = [{ codigo: 'vias_pago', nombre: 'Vías de pago' }] as never;
  const previa = { resumen: { altas: 0, cambios: 0, bajas: 1, sinCambios: 0, propuestas: 0, errores: 0 }, huella: 'h', filas: [{ fila: 2, clase: 'BAJA', definicion: 'vias_pago', proceso: '*', actividad: '*', codigoPadre: '*', codigo: 'efectivo', detalle: 'se desactiva, no se borra' }] } as never;
  it('mientras lee (sin usos todavía) no afirma «0 y 0» ni nada', () => {
    const d = construirVistaPrevia(previa, DEFS, {}, {}, new Map()).filas[0]!.detalle;
    expect(d).not.toMatch(/La usa|0 en curso|0 expedientes/);
  });
  it('busca la opción por su CÓDIGO, no por la etiqueta de otra fila', () => {
    const usos: Usos = { lugares: [], expedientes: [{ codigo: 'zzz', etiqueta: 'efectivo', guardados: '9', enCurso: '8', fueraDeLista: true }, { codigo: 'efectivo', guardados: '73', enCurso: '4' }] };
    expect(construirVistaPrevia(previa, DEFS, {}, {}, new Map([['vias_pago', usos]])).filas[0]!.detalle).toContain('La usan 73 expedientes guardados y 4 en curso.');
  });
  it('singular y plural: «La usa 1 expediente guardado y 1 en curso»', () => {
    const usos: Usos = { lugares: [], expedientes: [{ codigo: 'efectivo', guardados: '1', enCurso: '1' }] };
    expect(construirVistaPrevia(previa, DEFS, {}, {}, new Map([['vias_pago', usos]])).filas[0]!.detalle).toContain('La usa 1 expediente guardado y 1 en curso.');
  });
  it('al subir OTRO fichero no se enseña lo leído para el anterior mientras se lee el nuevo', async () => {
    location.hash = hashDe({ vista: 'importar' });
    const kit = kitDeEjemplo({ perfil: 'superadministracion', usos: { lugares: [], expedientes: [{ codigo: 'efectivo', guardados: '73', enCurso: '4' }] } });
    render(Parametros, { kit });
    const csv = 'definicion,codigo,etiqueta,activo\nvias_pago,efectivo,,no\n';
    const subir = async (n: string) => fireEvent.change(await screen.findByTestId('fichero-csv'), { target: { files: [new File([csv], n, { type: 'text/csv' })] } });
    await subir('a.csv');
    await waitFor(() => expect(screen.getByTestId('filas-de-importacion').textContent).toContain('La usan 73'));
    // El segundo fichero se lee con una lectura de usos que NO responde: lo del primero no puede seguir pintado.
    const original = kit.usos;
    kit.usos = () => new Promise(() => undefined);
    await fireEvent.click(screen.getByRole('button', { name: /Cambiar fichero/ }));
    await subir('b.csv');
    // El 2.º preview SÍ se pinta (su lectura de usos no responde); lo leído para el 1.º no puede seguir en pantalla.
    const filas = await screen.findByTestId('filas-de-importacion');
    expect(filas.textContent).toContain('Se da de baja');
    expect(filas.textContent).not.toContain('La usan 73');
    kit.usos = original;
  });
});
