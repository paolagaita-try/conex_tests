/**
 * Segunda tanda de la clase «la app afirma más de lo que sabe cuando hay más datos que en la demo»: cada barrera con la
 * gemela que la mutación pidió (pendientes más allá de la primera página, filtros que viajan al servidor, la persona 21+
 * en Aprobaciones y en la Traza, la sesión entre los homónimos, valores releídos al volver a Inicio, nodos técnicos).
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import PanelDeHistorial from './componentes/PanelDeHistorial.svelte';
import VistaTraza from './vistas/VistaTraza.svelte';
import { cargarContexto } from './carga';
import { kitDeEjemplo, PROCESO, type OpcionesDelKit } from './ejemplo';
import { opcionesDeActividad } from './permisos';
import { hashDe, type Ruta } from './ruta';
import { SIN_FILTROS } from './traza';
import { TRAZA_REAL } from './trazaReal.fixture';
import * as T from './textos';
import type { EntradaDeTraza, Propuesta } from './tipos';

beforeEach(() => {
  location.hash = '';
});
afterEach(cleanup);

function abrir(ruta: Ruta, extra: Partial<OpcionesDelKit> = {}) {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil: 'superadministracion', ...extra });
  render(Parametros, { kit });
  return kit;
}

describe('pendientes: más de 100 aprobables', () => {
  it('Aprobaciones las lista TODAS y el contador de la pestaña las cuenta (la primera página del kit solo trae 100)', async () => {
    abrir({ vista: 'aprobaciones' }, { rellenoPendientes: 130 });
    const grupo = await screen.findByTestId('grupo-esperan', {}, { timeout: 4000 });
    await waitFor(() => expect(grupo.querySelectorAll('button.fila').length).toBeGreaterThan(130));
    const pestana = screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim() ?? '').find((t) => t.startsWith('Aprobaciones'))!;
    expect(Number(pestana.replace(/\D/g, ''))).toBeGreaterThan(130);
  });
});

describe('la Traza pide al servidor lo que el servidor sabe filtrar', () => {
  it('las fechas viajan al servidor como instantes, y un filtro local no deja de leer al cambiar uno del servidor', async () => {
    const llamadas: Array<{ desde?: string; hasta?: string }> = [];
    const kit = abrir({ vista: 'traza' }, { muchasEntradas: 250 });
    const original = kit.traza;
    kit.traza = async (f, p) => (llamadas.push({ desde: f.desde, hasta: f.hasta }), original(f, p));
    await screen.findByTestId('eventos');
    await fireEvent.change(screen.getByLabelText(T.FILTRO_DESDE), { target: { value: '2000-01-01' } });
    await waitFor(() => expect(llamadas.some((l) => l.desde === '2000-01-01T00:00:00.000Z')).toBe(true));
    await fireEvent.change(screen.getByLabelText(T.FILTRO_HASTA), { target: { value: '2030-01-01' } });
    await waitFor(() => expect(llamadas.some((l) => l.hasta === '2030-01-01T23:59:59.999Z')).toBe(true));
  });

  it('con un filtro de lista puesto, al cambiar una fecha se vuelve a leer y se sigue leyendo hasta encontrar', async () => {
    const kit = abrir({ vista: 'traza' }, { muchasEntradas: 250 });
    await screen.findByTestId('eventos');
    await fireEvent.input(screen.getByLabelText(T.FILTRO_QUE), { target: { value: 'Vías' } });
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('prepago'), { timeout: 4000 });
    const paginas: number[] = [];
    const original = kit.traza;
    kit.traza = async (f, p) => (paginas.push(p), original(f, p));
    await fireEvent.change(screen.getByLabelText(T.FILTRO_DESDE), { target: { value: '2000-01-01' } });
    // Releer desde la primera página y SEGUIR hasta llegar a las antiguas (3.ª página), porque el filtro de lista sigue puesto.
    await waitFor(() => expect(Math.max(...paginas, -1)).toBeGreaterThanOrEqual(2), { timeout: 4000 });
    expect(paginas[0]).toBe(0);
    expect(screen.queryByTestId('traza-vacia')).toBeNull();
  });
});

describe('«ninguna» solo cuando se sabe', () => {
  const base = { eventos: [], puedeVerificar: false, verificacion: null, filtros: SIN_FILTROS, buscarPersonas: async () => [], onfiltros: () => {}, onverificar: () => {}, onmas: () => {}, onexportar: () => {} };
  it('Traza vacía con entradas más antiguas por leer: sigue buscando, no dice «ninguna»', () => {
    render(VistaTraza, { ...base, hayMas: true, quedaMas: true });
    expect(screen.getByTestId('traza-buscando')).toBeInTheDocument();
    expect(screen.queryByTestId('traza-vacia')).toBeNull();
  });
  it('Traza vacía tras el tope de lectura con más en el servidor: lo dice (no «ninguna»)', () => {
    render(VistaTraza, { ...base, hayMas: false, quedaMas: true });
    expect(screen.getByTestId('traza-tope')).toBeInTheDocument();
    expect(screen.queryByTestId('traza-vacia')).toBeNull();
  });
  it('Traza vacía y todo leído: sí dice que ninguna coincide', () => {
    render(VistaTraza, { ...base, hayMas: false, quedaMas: false });
    expect(screen.getByTestId('traza-vacia')).toBeInTheDocument();
  });
  it('Historial vacío con páginas por leer: ofrece seguir, no dice «no hay cambios»', () => {
    render(PanelDeHistorial, { eventos: [], periodo: 'todo', cadena: null, hayMas: true, onperiodo: () => {}, onmas: () => {}, onexportar: () => {} });
    expect(screen.getByTestId('historial-sigue-buscando')).toBeInTheDocument();
    expect(screen.queryByTestId('historial-vacio')).toBeNull();
  });
});

describe('la persona 21+ por su id, en Aprobaciones y en la Traza', () => {
  const datos = { tipoSujeto: 'USUARIO', sujetoUsuarioId: 200, actividades: [], proceso: PROCESO };
  const propuesta: Propuesta = {
    id: 9000, definicion: '*', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: '*', accion: 'DELEGAR', valorAnterior: [],
    valorPropuesto: { accion: 'DELEGAR', definicion: '*', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: '*', datos } as never,
    proponente: 'luis.gil', motivo: 'Cobertura.', estado: 'PENDIENTE', aprobador: null, comentario: null, creadaEn: '2026-10-02T10:00:00.000Z', resueltaEn: null, persistenceVersion: 0, esPropia: false, puedesAprobar: true,
  };
  it('Aprobaciones nombra a la persona 21, no «una persona»', async () => {
    abrir({ vista: 'aprobaciones' }, { muchasPersonas: true, propuestasAdicionales: [propuesta] });
    const grupo = await screen.findByTestId('grupo-esperan');
    await fireEvent.click([...grupo.querySelectorAll('button.fila')].find((b) => /Permisos/.test(b.textContent ?? ''))!);
    await waitFor(() => expect(screen.getByTestId('detalle-de-delegacion').textContent).toContain('Zoe Ultima'), { timeout: 3000 });
    expect(screen.getByTestId('detalle-de-delegacion').textContent).not.toMatch(/Una persona: Una persona/);
  });
  it('la Traza nombra a la persona 21 en «propuso delegar Permisos · …»', async () => {
    const entrada = JSON.parse(JSON.stringify(TRAZA_REAL.find((e) => e.accion === 'PROPONER' && e.claveNegocio.includes('|USUARIO|')))) as EntradaDeTraza;
    (entrada.valorNuevo as { valorPropuesto: { datos: { sujetoUsuarioId: number } } }).valorPropuesto.datos.sujetoUsuarioId = 200;
    abrir({ vista: 'traza' }, { muchasPersonas: true, trazaAdicional: [entrada] });
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('Zoe Ultima'), { timeout: 3000 });
  });
});

describe('la sesión cuenta entre los homónimos', () => {
  it('una sesión que se llama como otra persona se distingue por su usuario', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion', homonimos: true });
    const ctx = await cargarContexto({ ...kit, sesion: async () => ({ ...(await kit.sesion()), usuario: 'recien.llegada', nombre: 'Marta Rivas' }) });
    expect(ctx.nombres['recien.llegada']).toBe('Marta Rivas (recien.llegada)');
  });
});

describe('al volver a Inicio se releen los valores', () => {
  it('lo que otra sesión cambió mientras tanto se ve al volver', async () => {
    const kit = abrir({ vista: 'inicio' });
    await screen.findAllByRole('tab');
    const leidos: string[] = [];
    const original = kit.valores;
    kit.valores = async (d) => (leidos.push(d), original(d));
    await fireEvent.click(screen.getByRole('tab', { name: /Aprobaciones/ }));
    await fireEvent.click(screen.getByRole('tab', { name: /Parámetros/ }));
    await waitFor(() => expect(leidos.length).toBeGreaterThan(0));
  });
});

describe('nodos técnicos', () => {
  it('«Fin» e «Inicio» no se ofrecen como actividades en las que delegar', () => {
    expect(opcionesDeActividad(['Fin', 'inicio', 'F8 Aprobar beca completa (Comite academico)']).map((o) => o.valor)).toEqual(['F8 Aprobar beca completa (Comite academico)']);
  });
});
