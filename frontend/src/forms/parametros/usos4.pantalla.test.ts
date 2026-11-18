/**
 * «Dónde se usa» no se queda viejo tras escribir (B1), cada pantalla pide los usos de SU definición (V53), y las ramas que dicen
 * «no sabemos» no dicen «0» (V50, V23, V18, V22, V52, V14, V42). Cada prueba mide antes Y después con un doble que cambia de valor.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import PanelDeUsos from './componentes/PanelDeUsos.svelte';
import { construirVistaPrevia } from './importar';
import { ACT_PAGO, kitDeEjemplo, PROCESO } from './ejemplo';
import { hashDe } from './ruta';
import { usosVM } from './usos';
import * as T from './textos';
import type { Usos } from './kit';
import type { Propuesta } from './tipos';

beforeEach(() => {
  location.hash = '';
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const VIAS = { proceso: PROCESO, actividad: ACT_PAGO };
const irAVias = (pestana: 'valores' | 'usos') => {
  location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana });
};
const filas = () => [...screen.getByTestId('usos-expedientes').querySelectorAll('tbody tr')] as HTMLElement[];
const filaDe = (texto: string) => filas().find((f) => f.textContent?.includes(texto));
const celdas = (tr: HTMLElement) => [...tr.querySelectorAll('td')].map((td) => td.textContent?.replace(/\s+/g, ' ').trim() ?? '');

/** Los usos cambian con lo escrito: antes de escribir, 198/11; después, 203/12. */
const cambiante = (_d: string, escrituras: number): Usos => ({
  lugares: [],
  expedientes: [
    { codigo: 'cheque', guardados: escrituras === 0 ? '198' : '203', enCurso: escrituras === 0 ? '11' : '12' },
    { codigo: 'prepago', guardados: '4', enCurso: '2' },
  ],
});

async function escribirEstado(codigo: string, boton: string, confirmar: string) {
  await fireEvent.click(within(await screen.findByTestId(`opcion-${codigo}`)).getByRole('button', { name: boton }));
  await fireEvent.input(await screen.findByLabelText(/Motivo del cambio/), { target: { value: 'Por la circular.' } });
  await fireEvent.click(screen.getByTestId(confirmar));
}

describe('B1: «Dónde se usa» se relee tras escribir, en los dos sentidos', () => {
  it('desactivar «cheque»: antes sin chip y con 198/11; después con chip «Inactiva» y con 203/12', async () => {
    irAVias('valores');
    const kit = kitDeEjemplo({ perfil: 'superadministracion', usos: cambiante });
    render(Parametros, { kit });
    await screen.findByTestId('opcion-cheque');
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(filaDe('Cheque')).toBeTruthy());
    expect(celdas(filaDe('Cheque')!).slice(1)).toEqual(['198', '11']);
    expect(filaDe('Cheque')!.textContent).not.toContain(T.CHIP_INACTIVA);

    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_VALORES }));
    await escribirEstado('cheque', T.DESACTIVAR, 'confirmar-estado');
    await waitFor(() => expect(kit.escrituras.length).toBeGreaterThan(0));
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(celdas(filaDe('Cheque')!).slice(1)).toEqual(['203', '12']));
    expect(filaDe('Cheque')!.textContent).toContain(T.CHIP_INACTIVA);
  });

  it('reactivar «prepago»: antes con chip; después sin chip', async () => {
    irAVias('valores');
    const kit = kitDeEjemplo({ perfil: 'superadministracion', usos: cambiante });
    render(Parametros, { kit });
    await screen.findByTestId('opcion-prepago');
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(filaDe('prepago')).toBeTruthy());
    expect(filaDe('prepago')!.textContent).toContain(T.CHIP_INACTIVA);

    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_VALORES }));
    await escribirEstado('prepago', T.REACTIVAR, 'confirmar-estado');
    await waitFor(() => expect(kit.escrituras.length).toBeGreaterThan(0));
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(filaDe('prepago')!.textContent).not.toContain(T.CHIP_INACTIVA));
  });

  it('mientras relee no enseña las cifras viejas ni «0»: dice que consulta', async () => {
    irAVias('valores');
    const kit = kitDeEjemplo({ perfil: 'superadministracion', usos: cambiante });
    render(Parametros, { kit });
    await screen.findByTestId('opcion-cheque');
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(filaDe('Cheque')).toBeTruthy());
    // La relectura queda en el aire: lo que se ve mientras tanto no puede ser lo viejo.
    let soltar: (u: Usos) => void = () => {};
    kit.usos = () => new Promise<Usos>((r) => { soltar = r; });
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_VALORES }));
    await escribirEstado('cheque', T.DESACTIVAR, 'confirmar-estado');
    await fireEvent.click(await screen.findByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(screen.queryByTestId('usos-expedientes')).toBeNull());
    expect(screen.getAllByRole('status').map((s) => s.textContent).join(' ')).toContain(T.CARGANDO);
    soltar(cambiante('', 1));
    await waitFor(() => expect(celdas(filaDe('Cheque')!).slice(1)).toEqual(['203', '12']));
  });
});

describe('B1: tras decidir en Aprobaciones se relee lo que se usa', () => {
  const propuesta: Propuesta = {
    id: 9100, definicion: 'vias_pago', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: 'cheque', accion: 'EDITAR', valorAnterior: [{ valor: '1' }],
    valorPropuesto: { accion: 'EDITAR', definicion: 'vias_pago', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: 'cheque', datos: { valor: '2' } } as never,
    proponente: 'luis.gil', motivo: 'Prueba.', estado: 'PENDIENTE', aprobador: null, comentario: null, creadaEn: '2026-10-05T10:00:00.000Z', resueltaEn: null, persistenceVersion: 0, esPropia: false, puedesAprobar: true,
  };
  async function abrir() {
    location.hash = hashDe({ vista: 'aprobaciones' });
    const kit = kitDeEjemplo({ perfil: 'superadministracion', propuestasAdicionales: [propuesta] });
    const pedidos: string[] = [];
    kit.usos = async (d) => {
      pedidos.push(d);
      // Cada definición sirve SU cifra: 198 para las vías, 7 para cualquier otra.
      return { lugares: [], expedientes: [{ codigo: 'cheque', guardados: d === 'vias_pago' ? '198' : '7', enCurso: '11' }] };
    };
    render(Parametros, { kit });
    const grupo = await screen.findByTestId('grupo-esperan', {}, { timeout: 3000 });
    await fireEvent.click([...grupo.querySelectorAll('button.fila')].find((b) => /Vías de pago/.test(b.textContent ?? ''))!);
    const bloque = await screen.findByTestId('usos-de-la-aprobacion', {}, { timeout: 3000 });
    return { bloque, pedidos };
  }
  it('el bloque de una propuesta lleva la cifra de SU definición (no la de otra)', async () => {
    const { bloque, pedidos } = await abrir();
    await waitFor(() => expect(bloque.textContent).toContain('11'));
    expect(pedidos).toContain('vias_pago');
    expect(within(bloque).getByTestId('expedientes-en-curso').textContent).toContain('11');
  });
  it('tras decidir se relee lo que se usa de las definiciones ya leídas', async () => {
    const { pedidos } = await abrir();
    await waitFor(() => expect(pedidos).toContain('vias_pago'));
    const antes = pedidos.filter((d) => d === 'vias_pago').length;
    await fireEvent.click(await screen.findByTestId('aprobar'));
    await waitFor(() => expect(pedidos.filter((d) => d === 'vias_pago').length).toBeGreaterThan(antes));
  });
});

describe('B1: en la pantalla de un parámetro, proponer y retirar releen lo que se usa', () => {
  const lecturas = (pedidos: string[]) => pedidos.filter((d) => d === 'porcentaje_beca').length;
  it('al enviar una propuesta y al retirarla se vuelve a pedir `usos` de ESE parámetro', async () => {
    location.hash = hashDe({ vista: 'definicion', definicion: 'porcentaje_beca', ambito: { proceso: PROCESO, actividad: '*' }, pestana: 'valores' });
    const kit = kitDeEjemplo({ perfil: 'superadministracion', sinPropuestas: [1] });
    const pedidos: string[] = [];
    const original = kit.usos;
    kit.usos = (d) => { pedidos.push(d); return original(d); };
    render(Parametros, { kit });
    await screen.findByTestId('campo-valor');
    await waitFor(() => expect(lecturas(pedidos)).toBe(1));
    await fireEvent.input(screen.getByTestId('campo-valor'), { target: { value: '30' } });
    await fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: 'Circular.' } });
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    await fireEvent.click(await screen.findByTestId('enviar-a-aprobacion'));
    await waitFor(() => expect(kit.escrituras).toHaveLength(1));
    await waitFor(() => expect(lecturas(pedidos)).toBe(2));
    await fireEvent.click(await screen.findByTestId('retirar'));
    await waitFor(() => expect(kit.escrituras.length).toBeGreaterThan(1));
    await waitFor(() => expect(lecturas(pedidos)).toBe(3));
  });
  it('un directo (impacto normal) también relee', async () => {
    location.hash = hashDe({ vista: 'definicion', definicion: 'tope_beca_modalidad', ambito: { proceso: PROCESO, actividad: '*' }, pestana: 'valores' });
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const pedidos: string[] = [];
    const original = kit.usos;
    kit.usos = (d) => { pedidos.push(d); return original(d); };
    render(Parametros, { kit });
    await screen.findByTestId('campo-valor');
    await waitFor(() => expect(pedidos.length).toBe(1));
    await fireEvent.input(screen.getByTestId('campo-valor'), { target: { value: '2500000' } });
    await fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: 'Ajuste.' } });
    await fireEvent.click(screen.getByTestId('guardar-valor'));
    await waitFor(() => expect(kit.escrituras).toHaveLength(1));
    await waitFor(() => expect(pedidos.length).toBe(2));
  });
});

describe('B1: una lectura vieja que llega tarde no pisa a la nueva', () => {
  it('si la primera lectura responde después de la segunda, manda la segunda', async () => {
    irAVias('valores');
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const sueltas: Array<(u: Usos) => void> = [];
    kit.usos = () => new Promise<Usos>((r) => { sueltas.push(r); });
    render(Parametros, { kit });
    await screen.findByTestId('opcion-cheque');
    await waitFor(() => expect(sueltas).toHaveLength(1)); // la lectura de entrada, en el aire
    await escribirEstado('cheque', T.DESACTIVAR, 'confirmar-estado');
    await waitFor(() => expect(sueltas).toHaveLength(2)); // la de después de escribir
    sueltas[1]!(cambiante('', 1));
    await fireEvent.click(await screen.findByRole('tab', { name: T.PESTANA_DONDE_SE_USA }));
    await waitFor(() => expect(celdas(filaDe('Cheque')!).slice(1)).toEqual(['203', '12']));
    sueltas[0]!(cambiante('', 0)); // la vieja llega tarde
    await new Promise((r) => setTimeout(r, 30));
    expect(celdas(filaDe('Cheque')!).slice(1)).toEqual(['203', '12']);
  });
});

describe('V53: cada pantalla pide los usos de SU definición', () => {
  it('la lista pide «vias_pago»', async () => {
    irAVias('usos');
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const pedidos: string[] = [];
    const original = kit.usos;
    kit.usos = (d) => { pedidos.push(d); return original(d); };
    render(Parametros, { kit });
    await waitFor(() => expect(pedidos.length).toBeGreaterThan(0));
    expect([...new Set(pedidos)]).toEqual(['vias_pago']);
  });
  it('el parámetro pide «porcentaje_beca»', async () => {
    location.hash = hashDe({ vista: 'definicion', definicion: 'porcentaje_beca', ambito: { proceso: PROCESO, actividad: '*' }, pestana: 'usos' });
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const pedidos: string[] = [];
    const original = kit.usos;
    kit.usos = (d) => { pedidos.push(d); return original(d); };
    render(Parametros, { kit });
    await waitFor(() => expect(pedidos.length).toBeGreaterThan(0));
    expect([...new Set(pedidos)]).toEqual(['porcentaje_beca']);
  });
});

describe('V50 y V52: el diálogo «Desactivar»', () => {
  async function abrir(usos: Usos | (() => Promise<Usos>)) {
    irAVias('valores');
    const kit = kitDeEjemplo({ perfil: 'superadministracion', usos: typeof usos === 'function' ? undefined : usos });
    if (typeof usos === 'function') kit.usos = usos;
    render(Parametros, { kit });
    await fireEvent.click(within(await screen.findByTestId('opcion-cheque')).getByRole('button', { name: T.DESACTIVAR }));
    return screen.findByTestId('usos-de-la-opcion');
  }
  it('V50: sin fila para la opción en `expedientes` no dice «0» ni habla de expedientes', async () => {
    const aviso = await abrir({ lugares: [], expedientes: [{ codigo: 'otra_opcion', guardados: '9', enCurso: '3' }] });
    await waitFor(() => expect(aviso.textContent).toContain(T.DESACTIVAR_SE_USA_EN));
    expect(aviso.textContent).not.toMatch(/\d/);
    expect(aviso.textContent).not.toMatch(/expediente/);
  });
  it('V50: con `expedientes: []` tampoco', async () => {
    const aviso = await abrir({ lugares: [], expedientes: [] });
    await waitFor(() => expect(aviso.textContent).toContain(T.DESACTIVAR_SE_USA_EN));
    expect(aviso.textContent).not.toMatch(/\d|expediente/);
  });
  it('V52: mientras lee, el diálogo no dice nada (ni «ningún lugar», ni «0», ni un error)', async () => {
    const aviso = await abrir(() => new Promise<Usos>(() => {}));
    expect(aviso.textContent?.trim()).toBe('');
  });
});

describe('V23 y V18: la baja de una opción que no está entre las filas', () => {
  const previa = { resumen: { altas: 0, cambios: 0, bajas: 1, sinCambios: 0, propuestas: 0, errores: 0 }, huella: 'h', filas: [{ fila: 2, clase: 'BAJA', definicion: 'vias_pago', proceso: PROCESO, actividad: ACT_PAGO, codigoPadre: '*', codigo: 'cheque', detalle: 'se desactiva, no se borra' }] } as never;
  const detalleCon = (u: Usos | 'error' | undefined) => construirVistaPrevia(previa, [], {}, {}, new Map(u === undefined ? [] : [['vias_pago', u]])).filas[0]!.detalle;
  it('contrato declarado: con filas pero sin la de la opción NO se afirma «0»: dice que no se cuenta', () => {
    expect(detalleCon({ lugares: [], expedientes: [{ codigo: 'otra', guardados: '9', enCurso: '3' }] })).toContain(T.BAJA_SIN_CONTEO);
    expect(detalleCon({ lugares: [], expedientes: [{ codigo: 'otra', guardados: '9', enCurso: '3' }] })).not.toMatch(/\b0\b/);
  });
  it('con `expedientes: []` también dice que no se cuenta', () => {
    expect(detalleCon({ lugares: [], expedientes: [] })).toContain(T.BAJA_SIN_CONTEO);
  });
  it('con la fila de la opción, su cifra exacta (y no la de otra)', () => {
    const d = detalleCon({ lugares: [], expedientes: [{ codigo: 'otra', guardados: '9', enCurso: '3' }, { codigo: 'cheque', guardados: '198', enCurso: '11' }] });
    expect(d).toContain(T.BAJA_LA_USAN('198', '11'));
    expect(d).not.toContain('9 expedientes');
  });
  it('V22: mientras todavía lee no dice «No pudimos leer…» ni nada de expedientes; con error sí', () => {
    const leyendo = detalleCon(undefined);
    expect(leyendo).not.toContain(T.BAJA_USOS_NO_LEIDOS);
    expect(leyendo).not.toContain(T.BAJA_SIN_CONTEO);
    expect(leyendo).not.toMatch(/expediente/);
    expect(detalleCon('error')).toContain(T.BAJA_USOS_NO_LEIDOS);
  });
});

describe('V14 y V42: las fichas de «lugares» muestran su tipo y su detalle', () => {
  const usos: Usos = {
    lugares: [
      { tipo: 'FORMULARIO', titulo: 'Preparar el pago', detalle: 'Se usó 3 veces.' },
      { tipo: 'DOCUMENTO', titulo: 'Carta de aprobación', detalle: 'Lleva la vía elegida.' },
      { tipo: 'REGLA', titulo: 'Tope por monto', detalle: 'Decide la ruta de aprobación.' },
    ],
    expedientes: [],
  };
  it('cada ficha: tipo en español, título y detalle, en su sitio', () => {
    render(PanelDeUsos, { usos: usosVM(usos, new Map(), new Set()) });
    const fichas = [...screen.getByTestId('usos-lugares').querySelectorAll('.ficha')] as HTMLElement[];
    expect(fichas).toHaveLength(3);
    const esperado = [
      [T.TIPO_DE_USO.FORMULARIO, 'Preparar el pago', 'Se usó 3 veces.'],
      [T.TIPO_DE_USO.DOCUMENTO, 'Carta de aprobación', 'Lleva la vía elegida.'],
      [T.TIPO_DE_USO.REGLA, 'Tope por monto', 'Decide la ruta de aprobación.'],
    ];
    fichas.forEach((t, i) => {
      expect(t.querySelector('h4')?.textContent).toBe(esperado[i]![1]);
      expect(t.querySelector('p')?.textContent).toBe(esperado[i]![2]);
      expect(t.textContent).toContain(esperado[i]![0]);
      for (const otro of esperado.filter((_, j) => j !== i)) expect(t.textContent).not.toContain(otro[0]);
    });
  });
});
