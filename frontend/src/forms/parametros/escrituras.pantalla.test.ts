/**
 * B2 gemela: una lectura POSTERIOR a una escritura que falla no deshace la escritura. En CADA pantalla y
 * acción de escritura de la aplicación (lista: editar/añadir/estado/ordenar/versión propia/heredar, parámetro:
 * proponer y retirar, aprobaciones: aprobar/rechazar/retirar, permisos: revocar/prorrogar/delegar, importar) el
 * doble aplica la escritura y falla las lecturas que la siguen: la pantalla dice «guardado, pero no pudimos
 * actualizar la vista», jamás un error de guardado, y deja el reintento a la vista.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { ACT_PAGO, DELEGACIONES, kitDeEjemplo, PROCESO, type OpcionesDelKit, type PerfilDeEjemplo } from './ejemplo';
import { hashDe, type Ruta } from './ruta';
import { explicar } from './fallos';
import { cuandoCompleto } from './formatos';
import { FalloDelKit } from './kit';
import * as T from './textos';

vi.mock('./csv', async (original) => {
  const real = await original<typeof import('./csv')>();
  return { ...real, descargar: vi.fn(() => true) };
});

const LECTURAS: OpcionesDelKit['fallaTrasEscritura'] = ['valores', 'propuestas', 'delegaciones', 'traza', 'editores', 'verificar'];
const VIAS = { proceso: PROCESO, actividad: ACT_PAGO };
let errores: string[] = [];

beforeEach(() => {
  location.hash = '';
  errores = [];
  window.addEventListener('unhandledrejection', (e) => errores.push(String(e.reason)));
});
afterEach(cleanup);

async function abrir(ruta: Ruta, perfil: PerfilDeEjemplo = 'superadministracion', extra: Partial<OpcionesDelKit> = {}) {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil, fallaTrasEscritura: LECTURAS, ...extra });
  render(Parametros, { kit });
  await screen.findAllByRole('tab');
  return kit;
}
const motivo = (m: string) => fireEvent.input(screen.getAllByLabelText(/Motivo/).at(-1)!, { target: { value: m } });
const escrituraDe = (kit: { escrituras: Array<{ operacion: string }> }, op: string) => kit.escrituras.filter((e) => e.operacion === op);

/** Lo que TODA escritura buena con lectura caída debe cumplir. */
async function esGuardadoSinActualizar(): Promise<void> {
  const aviso = await screen.findByTestId('refresco-fallido');
  expect(aviso.textContent).toContain(T.GUARDADO_SIN_ACTUALIZAR_TITULO);
  expect(within(aviso).getByRole('button', { name: T.REINTENTAR })).toBeInTheDocument();
  const t = document.body.textContent ?? '';
  for (const falso of [T.FALLO_GENERAL, T.FALLO_CONFLICTO, T.FALLO_REVISA]) expect(t).not.toContain(falso);
  expect(errores).toEqual([]);
}

describe('lista: toda escritura aplicada con la lectura caída', () => {
  const abrirLista = () => abrir({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'valores' });
  const fila = (c: string) => screen.getByTestId(`opcion-${c}`);

  it('editar una opción', async () => {
    const kit = await abrirLista();
    await fireEvent.click(within(fila('cheque')).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque certificado' } });
    await motivo('Cambio de nombre del instrumento.');
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    await waitFor(() => expect(escrituraDe(kit, 'cambiar')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });

  it('desactivar una opción', async () => {
    const kit = await abrirLista();
    await fireEvent.click(within(fila('efectivo')).getByRole('button', { name: T.DESACTIVAR }));
    await motivo('La sede deja de entregar efectivo.');
    await fireEvent.click(within(screen.getByTestId('confirmacion-estado')).getByRole('button', { name: T.DESACTIVAR_OPCION }));
    await waitFor(() => expect(escrituraDe(kit, 'cambiar')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });
});

describe('parámetro: proponer y retirar con la lectura caída', () => {
  const porcentaje: Ruta = { vista: 'definicion', definicion: 'porcentaje_beca', ambito: { proceso: PROCESO, actividad: '*' }, pestana: 'valores' };

  it('enviar un cambio de impacto alto: la propuesta existe aunque no se pueda releer', async () => {
    const kit = await abrir(porcentaje, 'superadministracion', { sinPropuestas: [1] });
    await fireEvent.input(screen.getByTestId('campo-valor'), { target: { value: '30' } });
    await motivo('Acuerdo CA-2026-14.');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    await fireEvent.click(await screen.findByTestId('enviar-a-aprobacion'));
    await waitFor(() => expect(escrituraDe(kit, 'cambiar')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });

  it('retirar la propuesta propia: se retiró y no se declara error', async () => {
    const kit = await abrir(porcentaje);
    await fireEvent.click(await screen.findByTestId('retirar'));
    await waitFor(() => expect(escrituraDe(kit, 'decidir')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });
});

describe('aprobaciones: aprobar, rechazar y retirar con la lectura caída', () => {
  it('aprobar', async () => {
    const kit = await abrir({ vista: 'aprobaciones' });
    await fireEvent.click(await screen.findByTestId('aprobar'));
    await waitFor(() => expect(escrituraDe(kit, 'decidir')).toHaveLength(1));
    expect(await screen.findByText(T.APROBADO_Y_APLICADO)).toBeInTheDocument();
    await esGuardadoSinActualizar();
  });

  it('rechazar', async () => {
    const kit = await abrir({ vista: 'aprobaciones' });
    await fireEvent.input(await screen.findByLabelText(/Tu comentario/), { target: { value: 'Falta el acta.' } });
    await fireEvent.click(screen.getByTestId('rechazar'));
    await waitFor(() => expect(escrituraDe(kit, 'decidir')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });

  it('retirar lo propio', async () => {
    const kit = await abrir({ vista: 'aprobaciones' }, 'delegado');
    await fireEvent.click(within(await screen.findByTestId('grupo-propias')).getByRole('button', { name: /Tope de aprobación del coordinador/ }));
    await fireEvent.click(await screen.findByTestId('retirar-propuesta'));
    await waitFor(() => expect(escrituraDe(kit, 'decidir')).toHaveLength(1));
    expect(await screen.findByText(T.PROPUESTA_RETIRADA)).toBeInTheDocument();
    await esGuardadoSinActualizar();
  });
});

describe('permisos: revocar, prorrogar y delegar con la lectura caída', () => {
  it('revocar', async () => {
    const kit = await abrir({ vista: 'permisos' });
    await screen.findByTestId('tabla-de-permisos');
    await fireEvent.click(screen.getByRole('button', { name: T.REVOCAR }));
    await motivo('Cambió de puesto.');
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    await waitFor(() => expect(escrituraDe(kit, 'revocar')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });

  it('prorrogar', async () => {
    const manana = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const kit = await abrir({ vista: 'permisos' }, 'superadministracion', { delegaciones: [{ ...DELEGACIONES[0]!, vigenteHasta: manana }] });
    await screen.findByTestId('tabla-de-permisos');
    await fireEvent.click(screen.getByRole('button', { name: T.PRORROGAR }));
    const campo = within(screen.getByTestId('confirmacion-permiso')).getByLabelText(new RegExp(T.NUEVA_FECHA));
    await fireEvent.input(campo, { target: { value: '31/12/2030' } });
    await fireEvent.blur(campo);
    await motivo('Cobertura del cierre anual.');
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    await waitFor(() => expect(escrituraDe(kit, 'delegar')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });

  it('delegar', async () => {
    const kit = await abrir({ vista: 'nuevaDelegacion' });
    await fireEvent.click(await screen.findByText('Una persona', { exact: true }));
    const persona = screen.getByRole('combobox', { name: /Persona/ });
    await fireEvent.input(persona, { target: { value: 'Ana' } });
    await fireEvent.click(await screen.findByRole('option', { name: /Ana Pérez/ }));
    await fireEvent.change(screen.getByLabelText(/^Proceso/), { target: { value: PROCESO } });
    await motivo('Cobertura del cierre anual.');
    await fireEvent.click(screen.getByTestId('enviar-delegacion'));
    await waitFor(() => expect(escrituraDe(kit, 'delegar')).toHaveLength(1));
    await esGuardadoSinActualizar();
  });
});

describe('importar con la lectura caída', () => {
  it('la importación aplicada no se pinta también como error', async () => {
    const kit = await abrir({ vista: 'importar' });
    const csv = 'definicion,codigo,etiqueta,activo\nvias_pago,leasing,Arrendamiento,\n';
    await fireEvent.change(await screen.findByTestId('fichero-csv'), { target: { files: [new File([csv], 'a.csv', { type: 'text/csv' })] } });
    await screen.findByTestId('resumen-de-importacion');
    await fireEvent.input(screen.getByLabelText(new RegExp(T.MOTIVO_DE_LA_IMPORTACION)), { target: { value: 'Nuevas duraciones.' } });
    await fireEvent.click(screen.getByTestId('confirmar-importacion'));
    await waitFor(() => expect(escrituraDe(kit, 'importar')).toHaveLength(1));
    expect(await screen.findByTestId('importacion-aplicada')).toBeInTheDocument();
    await esGuardadoSinActualizar();
  });
});

describe('un conflicto contra uno mismo no es «otra persona»', () => {
  it('con el kit real: guardadoPor = la persona de la sesión dice que ya se guardó', () => {
    const e = new FalloDelKit('CONFLICTO', null, null, 'marta.rivas', '2026-10-20T12:00:00.000Z');
    expect(explicar(e, 'marta.rivas').mensaje).toBe(T.conflictoPropio(cuandoCompleto('2026-10-20T12:00:00.000Z')));
    expect(explicar(e, 'marta.rivas').mensaje).not.toMatch(/ya se guardó/i);
    expect(explicar(e, 'otra.persona').mensaje).toBe(T.FALLO_CONFLICTO);
    expect(explicar(e).mensaje).toBe(T.FALLO_CONFLICTO);
  });
});
