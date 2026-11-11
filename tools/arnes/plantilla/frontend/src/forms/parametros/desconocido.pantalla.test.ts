/**
 * B1: una escritura cuya respuesta no llega NO dice «no se cambió nada» (el servidor pudo aplicarla): dice que no
 * se sabe, relee la vista y no invita a repetir a ciegas. B2: tras importar se releen las listas que tocó.
 * El doble aplica la escritura y luego pierde la respuesta (`escrituraSinRespuesta`), como un tiempo agotado real.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { ACT_PAGO, DELEGACIONES, kitDeEjemplo, PROCESO, type OpcionesDelKit, type PerfilDeEjemplo } from './ejemplo';
import { explicar } from './fallos';
import { FalloDelKit } from './kit';
import { hashDe, type Ruta } from './ruta';
import * as T from './textos';

vi.mock('./csv', async (original) => {
  const real = await original<typeof import('./csv')>();
  return { ...real, descargar: vi.fn(() => true) };
});

beforeEach(() => {
  location.hash = '';
});
afterEach(cleanup);

async function abrir(ruta: Ruta, extra: Partial<OpcionesDelKit> = {}, perfil: PerfilDeEjemplo = 'superadministracion') {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil, ...extra });
  render(Parametros, { kit });
  await screen.findAllByRole('tab');
  return kit;
}
const motivo = (m: string) => fireEvent.input(screen.getAllByLabelText(/Motivo/).at(-1)!, { target: { value: m } });
const VIAS = { proceso: PROCESO, actividad: ACT_PAGO };
const porcentaje: Ruta = { vista: 'definicion', definicion: 'porcentaje_beca', ambito: { proceso: PROCESO, actividad: '*' }, pestana: 'valores' };

/** Lo que TODA escritura sin respuesta debe decir. */
async function noSabemos(): Promise<void> {
  await waitFor(() => expect(document.body.textContent).toContain(T.FALLO_DESCONOCIDO));
  expect(document.body.textContent).not.toContain('no se cambió nada');
  expect(document.body.textContent).not.toContain(T.FALLO_GENERAL);
}

describe('B1 · sin respuesta no es «no se cambió nada»', () => {
  it('editar una opción: dice que no sabe y la vista ya muestra lo que el servidor aplicó', async () => {
    await abrir({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'valores' }, { escrituraSinRespuesta: ['cambiar'] });
    await fireEvent.click(within(await screen.findByTestId('opcion-cheque')).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque certificado' } });
    await motivo('Cambio de nombre.');
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    await noSabemos();
    await waitFor(() => expect(within(screen.getByTestId('opcion-cheque')).getByText('Cheque certificado')).toBeInTheDocument());
  });

  it('proponer un cambio de impacto alto', async () => {
    await abrir(porcentaje, { escrituraSinRespuesta: ['cambiar'], sinPropuestas: [1] });
    await fireEvent.input(screen.getByTestId('campo-valor'), { target: { value: '30' } });
    await motivo('Circular.');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    await fireEvent.click(await screen.findByTestId('enviar-a-aprobacion'));
    await noSabemos();
    // La propuesta SÍ existe en el servidor: la vista releída la muestra (se puede retirar).
    expect(await screen.findByTestId('retirar')).toBeInTheDocument();
  });

  it('retirar la propuesta propia', async () => {
    await abrir(porcentaje, { escrituraSinRespuesta: ['decidir'] });
    await fireEvent.click(await screen.findByTestId('retirar'));
    await noSabemos();
    // El servidor SÍ la retiró: la vista releída ya no ofrece retirarla.
    await waitFor(() => expect(screen.queryByTestId('retirar')).toBeNull());
  });

  it('aprobar: la propuesta deja de esperar (el servidor la aplicó) y el panel no promete «inténtalo de nuevo»', async () => {
    await abrir({ vista: 'aprobaciones' }, { escrituraSinRespuesta: ['decidir'] });
    await fireEvent.click(await screen.findByTestId('aprobar'));
    await noSabemos();
    await waitFor(() => expect(screen.queryByTestId('grupo-esperan')).toBeNull());
  });

  it('rechazar', async () => {
    await abrir({ vista: 'aprobaciones' }, { escrituraSinRespuesta: ['decidir'] });
    await fireEvent.input(await screen.findByLabelText(/Tu comentario/), { target: { value: 'Falta el acta.' } });
    await fireEvent.click(screen.getByTestId('rechazar'));
    await noSabemos();
  });

  it('revocar, prorrogar y delegar', async () => {
    await abrir({ vista: 'permisos' }, { escrituraSinRespuesta: ['revocar'] });
    await screen.findByTestId('tabla-de-permisos');
    await fireEvent.click(screen.getByRole('button', { name: T.REVOCAR }));
    await motivo('Cambió de puesto.');
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    await noSabemos();
    // El servidor sí la revocó: la vista releída lo muestra.
    await waitFor(() => expect(screen.getByRole('button', { name: /Vigentes · 0/ })).toBeInTheDocument());
  });

  it('delegar (Nueva delegación)', async () => {
    await abrir({ vista: 'nuevaDelegacion' }, { escrituraSinRespuesta: ['delegar'] });
    await fireEvent.click(await screen.findByText('Una persona', { exact: true }));
    await fireEvent.input(screen.getByRole('combobox', { name: /Persona/ }), { target: { value: 'Ana' } });
    await fireEvent.click(await screen.findByRole('option', { name: /Ana Pérez/ }));
    await fireEvent.change(screen.getByLabelText(/^Proceso/), { target: { value: PROCESO } });
    await motivo('Cobertura.');
    await fireEvent.click(screen.getByTestId('enviar-delegacion'));
    await noSabemos();
  });

  it('prorrogar', async () => {
    const manana = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    await abrir({ vista: 'permisos' }, { escrituraSinRespuesta: ['delegar'], delegaciones: [{ ...DELEGACIONES[0]!, vigenteHasta: manana }] });
    await screen.findByTestId('tabla-de-permisos');
    await fireEvent.click(screen.getByRole('button', { name: T.PRORROGAR }));
    const campo = within(screen.getByTestId('confirmacion-permiso')).getByLabelText(new RegExp(T.NUEVA_FECHA));
    await fireEvent.input(campo, { target: { value: '31/12/2030' } });
    await fireEvent.blur(campo);
    await motivo('Cobertura del cierre anual.');
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    await noSabemos();
  });

  it('importar: no dice «no pudimos guardar» ni invita a repetir; relee lo que tocaba', async () => {
    const kit = await abrir({ vista: 'importar' }, { escrituraSinRespuesta: ['importar'] });
    const csv = 'definicion,codigo,etiqueta,activo\nvias_pago,cheque,Cheque V3,\n';
    await fireEvent.change(await screen.findByTestId('fichero-csv'), { target: { files: [new File([csv], 'a.csv', { type: 'text/csv' })] } });
    await screen.findByTestId('resumen-de-importacion');
    await fireEvent.input(screen.getByLabelText(new RegExp(T.MOTIVO_DE_LA_IMPORTACION)), { target: { value: 'Nombres nuevos.' } });
    await fireEvent.click(screen.getByTestId('confirmar-importacion'));
    await waitFor(() => expect(document.body.textContent).toContain(T.IMPORTACION_SIN_RESPUESTA));
    expect(document.body.textContent).not.toContain(T.FALLO_GENERAL);
    expect(kit.escrituras.filter((e) => e.operacion === 'importar')).toHaveLength(1);
    // El servidor SÍ la aplicó: al abrir la lista se ve lo importado (se releyó), no la versión vieja.
    location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'valores' });
    await fireEvent(window, new HashChangeEvent('hashchange'));
    expect(within(await screen.findByTestId('opcion-cheque')).getByText('Cheque V3')).toBeInTheDocument();
  });

  it('solo un 4xx prueba «no se cambió nada»: SIN_RESPUESTA, SERVIDOR y FORMA son desconocidos', () => {
    for (const clase of ['SIN_RESPUESTA', 'SERVIDOR', 'FORMA'] as const) {
      const x = explicar(new FalloDelKit(clase));
      expect(x.desconocido).toBe(true);
      expect(x.mensaje).toBe(T.FALLO_DESCONOCIDO);
    }
    for (const clase of ['SIN_PERMISO', 'NO_EXISTE', 'VALIDACION', 'CONFLICTO'] as const) expect(explicar(new FalloDelKit(clase)).desconocido).toBeUndefined();
  });
});

describe('B2 · tras importar se releen las listas que tocó', () => {
  it('la lista muestra lo importado y editarla después no choca con una versión vieja', async () => {
    await abrir({ vista: 'importar' });
    const csv = 'definicion,codigo,etiqueta,activo\nvias_pago,cheque,Cheque V3,\n';
    await fireEvent.change(await screen.findByTestId('fichero-csv'), { target: { files: [new File([csv], 'a.csv', { type: 'text/csv' })] } });
    await screen.findByTestId('resumen-de-importacion');
    await fireEvent.input(screen.getByLabelText(new RegExp(T.MOTIVO_DE_LA_IMPORTACION)), { target: { value: 'Nombres nuevos.' } });
    await fireEvent.click(screen.getByTestId('confirmar-importacion'));
    await screen.findByTestId('importacion-aplicada');
    location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'valores' });
    await fireEvent(window, new HashChangeEvent('hashchange'));
    const fila = await screen.findByTestId('opcion-cheque');
    expect(within(fila).getByText('Cheque V3')).toBeInTheDocument();
    await fireEvent.click(within(fila).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque certificado' } });
    await motivo('Ajuste posterior.');
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    await waitFor(() => expect(within(screen.getByTestId('opcion-cheque')).getByText('Cheque certificado')).toBeInTheDocument());
    expect(document.body.textContent).not.toMatch(/Ya hay un cambio tuyo|ya se guardó/i);
  });

  it('un conflicto contra uno mismo no afirma que el cambio de ahora se guardó', () => {
    const e = new FalloDelKit('CONFLICTO', null, null, 'marta.rivas', '2026-10-20T12:00:00.000Z');
    expect(explicar(e, 'marta.rivas').mensaje).toContain('Ya hay un cambio tuyo');
    expect(explicar(e, 'marta.rivas').mensaje).not.toMatch(/ya se guardó/i);
  });
});

describe('B3 · Aprobaciones no miente sobre qué se resolvió', () => {
  it('la confirmación de la decisión no se queda dentro del panel de OTRA propuesta, y se retira al elegir otra', async () => {
    await abrir({ vista: 'aprobaciones' }, {}, 'superadministracion');
    await fireEvent.click(await screen.findByTestId('aprobar'));
    const aviso = await screen.findByTestId('aviso-de-decision');
    expect(aviso.textContent).toContain(T.APROBADO_Y_APLICADO);
    // No está dentro del panel de la propuesta que queda abierta (ahí diría «aprobado» junto a «Aprobar y aplicar»).
    const panel = screen.queryByTestId('detalle-de-aprobacion');
    if (panel) expect(panel.contains(aviso)).toBe(false);
    const filas = screen.queryAllByRole('button', { name: /Tope|Porcentaje|propuesta/i }).filter((b) => b.classList.contains('fila'));
    if (filas[0]) {
      await fireEvent.click(filas[0]);
      expect(screen.queryByTestId('aviso-de-decision')).toBeNull();
    }
  });

  it('cada lectura es dueña de su aviso: si la de Aprobaciones cae, que la de la aplicación funcione NO lo borra', async () => {
    await abrir({ vista: 'aprobaciones' }, { completasFallanTrasEscritura: true });
    await fireEvent.click(await screen.findByTestId('aprobar'));
    const banner = await screen.findByTestId('refresco-fallido');
    // La app releyó lo pendiente con éxito, pero la lista de Aprobaciones sigue vieja: el aviso se queda.
    await waitFor(() => expect(banner.isConnected).toBe(true));
    expect(screen.getByTestId('refresco-fallido').textContent).toContain(T.GUARDADO_SIN_ACTUALIZAR_TITULO);
  });
});
