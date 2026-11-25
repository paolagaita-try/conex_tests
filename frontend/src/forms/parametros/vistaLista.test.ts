/** La vista de una lista sola, con un modelo y espías: la primera barrera del motivo, sin contenedor. */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/svelte';
import VistaLista from './vistas/VistaLista.svelte';
import { bien } from './acciones';
import { capacidadesDe, ROL_DE_SUPERADMINISTRACION } from './capacidades';
import { ACT_PAGO, PROCESOS, PROCESO, valoresDeEjemplo } from './ejemplo';
import { construirLista } from './lista';
import * as T from './textos';

function montar() {
  const lista = construirLista({
    valores: valoresDeEjemplo('vias_pago'),
    padre: null,
    ambito: { proceso: PROCESO, actividad: ACT_PAGO },
    procesos: PROCESOS,
    capacidades: capacidadesDe('m', [{ rol: ROL_DE_SUPERADMINISTRACION, grupo: '/a' }], []),
    editores: [],
    nombres: {},
  });
  const espias = {
    guardarEdicion: vi.fn(async () => bien()),
    anadir: vi.fn(async () => bien()),
    cambiarEstado: vi.fn(async () => bien()),
    guardarOrden: vi.fn(async () => bien()),
    versionPropia: vi.fn(async () => bien()),
    volverAHeredar: vi.fn(async () => bien()),
  };
  render(VistaLista, {
    lista,
    pestana: 'valores',
    usos: null,
    eventos: [],
    periodo: 'noventa',
    cadena: null,
    hayMasHistorial: false,
    ultimaModificacion: '',
    onpestana: vi.fn(),
    onvolver: vi.fn(),
    onambito: vi.fn(),
    onpadre: vi.fn(),
    onperiodo: vi.fn(),
    onmasHistorial: vi.fn(),
    onexportarHistorial: vi.fn(),
    ...espias,
  });
  return espias;
}

describe('la vista no entrega un guardado sin motivo, venga del formulario que venga', () => {
  it.each([
    ['editar', async () => {
      await fireEvent.click(within(screen.getByTestId('opcion-cheque')).getByRole('button', { name: T.EDITAR }));
      await fireEvent.click(screen.getByTestId('guardar-edicion'));
    }, 'guardarEdicion'],
    ['desactivar', async () => {
      await fireEvent.click(within(screen.getByTestId('opcion-cheque')).getByRole('button', { name: T.DESACTIVAR }));
      await fireEvent.click(screen.getByTestId('confirmar-estado'));
    }, 'cambiarEstado'],
    ['volver a heredar', async () => {
      await fireEvent.click(screen.getByRole('button', { name: T.VOLVER_A_HEREDAR }));
      await fireEvent.click(screen.getByTestId('confirmar-ambito'));
    }, 'volverAHeredar'],
  ] as const)('%s', async (_n, accion, espia) => {
    const espias = montar();
    await accion();
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(espias[espia]).not.toHaveBeenCalled();
  });

  it('con motivo sí lo entrega, una vez', async () => {
    const espias = montar();
    await fireEvent.click(within(screen.getByTestId('opcion-cheque')).getByRole('button', { name: T.DESACTIVAR }));
    await fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: 'Porque sí.' } });
    await fireEvent.click(screen.getByTestId('confirmar-estado'));
    await vi.waitFor(() => expect(espias.cambiarEstado).toHaveBeenCalledTimes(1));
    expect(espias.cambiarEstado).toHaveBeenCalledWith({ clave: '*|cheque', activar: false, motivo: 'Porque sí.' });
  });
});
