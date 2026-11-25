/**
 * Una lista, probada como se ejecuta: el contenedor real con un doble del kit que
 * recuerda lo que se escribe y aplica el bloqueo optimista. Lo que el doble NO prueba —que el kit real
 * se comporte así— lo miden las pruebas del módulo y el journey en el runtime.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import * as csv from './csv';
import { ACT_DECANATO, ACT_COMITE, ACT_PAGO, kitDeEjemplo, PROCESO, type PerfilDeEjemplo } from './ejemplo';
import { hashDe, type PestanaDeDefinicion } from './ruta';
import * as T from './textos';
import type { Ambito } from './ambitos';
import { FalloDelKit, type Usos } from './kit';

vi.mock('./csv', async (original) => {
  const real = await original<typeof import('./csv')>();
  return { ...real, descargar: vi.fn(() => true) };
});

beforeEach(() => {
  location.hash = '';
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const VIAS: Ambito = { proceso: PROCESO, actividad: ACT_PAGO };

async function abrir(definicion: string, ambito: Ambito, perfil: PerfilDeEjemplo = 'superadministracion', pestana: PestanaDeDefinicion = 'valores', usos?: Usos | null) {
  location.hash = hashDe({ vista: 'definicion', definicion, ambito, pestana });
  const kit = kitDeEjemplo({ perfil, usos });
  render(Parametros, { kit });
  await screen.findByTestId('vista-lista');
  return kit;
}

const fila = (codigo: string) => screen.getByTestId(`opcion-${codigo}`);
const motivo = (texto: string) => fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: texto } });

describe('renombrar una opción en uso se guarda sin diálogo', () => {
  it('guarda con su motivo, bloquea el código, actualiza la vista previa y el historial lo cuenta', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('cheque')).getByRole('button', { name: T.EDITAR }));

    const codigo = screen.getByLabelText(T.CAMPO_CODIGO) as HTMLInputElement;
    expect(codigo.value).toBe('cheque');
    expect(codigo.readOnly).toBe(true);
    expect(screen.getByText(T.CODIGO_BLOQUEADO)).toBeInTheDocument();

    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque certificado' } });
    await motivo('Cambio de nombre del instrumento según la circular interna OP-2026-09.');
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));

    // Sin diálogo de confirmación: reversible y de impacto normal.
    await waitFor(() => expect(screen.queryByTestId('formulario-edicion')).toBeNull());
    expect(screen.queryByTestId('confirmacion-estado')).toBeNull();
    expect(screen.queryByTestId('confirmacion-ambito')).toBeNull();

    // La petición lleva el código, la versión leída y el motivo.
    expect(kit.escrituras).toHaveLength(1);
    const p = kit.escrituras[0].datos as Record<string, unknown>;
    expect(p).toMatchObject({ accion: 'EDITAR', definicion: 'vias_pago', codigo: 'cheque', motivo: 'Cambio de nombre del instrumento según la circular interna OP-2026-09.' });
    expect(p.datos).toMatchObject({ etiqueta: 'Cheque certificado' });
    expect(typeof p.persistenceVersion).toBe('number');

    // La tabla y la vista previa (el widget real del cimiento) usan el nombre nuevo.
    expect(within(fila('cheque')).getByText('Cheque certificado')).toBeInTheDocument();
    const previa = screen.getByTestId('vista-previa');
    expect(within(previa).getByRole('radio', { name: /Cheque certificado/ })).toBeInTheDocument();
    expect(within(previa).queryByText('Cheque de administración')).toBeNull();

    // El historial lo recoge en lenguaje de negocio, con el antes → después y el motivo.
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_HISTORIAL }));
    const eventos = await screen.findByTestId('eventos');
    await waitFor(() => expect(eventos.textContent).toContain('cambió el nombre de una opción'));
    expect(eventos.textContent).toContain('Cheque de administración');
    expect(eventos.textContent).toContain('Cheque certificado');
    expect(eventos.textContent).toContain('Motivo:');
    expect(eventos.textContent).toContain('circular interna OP-2026-09');
    expect(eventos.textContent).not.toMatch(/persistenceVersion|"etiqueta"|\{/);

    // Exportable en CSV, sin columnas técnicas.
    await fireEvent.click(screen.getByRole('button', { name: T.EXPORTAR_CSV }));
    const [nombre, contenido] = (csv.descargar as unknown as { mock: { calls: string[][] } }).mock.calls[0];
    expect(nombre).toBe(T.NOMBRE_DEL_FICHERO_DE_HISTORIAL);
    expect(contenido).toContain('Cheque certificado');
    expect(contenido).not.toContain('persistence');
  });

  it('el historial enseña el estado de la cadena a la superadministración', async () => {
    await abrir('vias_pago', VIAS, 'superadministracion', 'historial');
    expect(await screen.findByText(/Cadena coherente · verificada/)).toBeInTheDocument();
  });
});

describe('desactivar una opción en uso, confirmada con motivo', () => {
  it('el diálogo explica qué pasa; al confirmar pasa a «Inactiva» y se puede reactivar', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('efectivo')).getByRole('button', { name: T.DESACTIVAR }));

    const dialogo = screen.getByTestId('confirmacion-estado');
    expect(dialogo.textContent).toContain('¿Desactivar «Pago en caja»?');
    expect(dialogo.textContent).toMatch(/los expedientes que ya la eligieron la conservan/i);
    expect(dialogo.textContent).toContain('nada se borra');
    expect(kit.escrituras).toHaveLength(0); // abrir el diálogo no escribe nada

    await fireEvent.input(within(dialogo).getByLabelText(/Motivo del cambio/), { target: { value: 'La sede principal deja de entregar efectivo.' } });
    await fireEvent.click(within(dialogo).getByRole('button', { name: T.DESACTIVAR_OPCION }));
    await waitFor(() => expect(screen.queryByTestId('confirmacion-estado')).toBeNull());

    expect(kit.escrituras[0].datos).toMatchObject({ accion: 'DESACTIVAR', codigo: 'efectivo', motivo: 'La sede principal deja de entregar efectivo.' });
    expect(within(fila('efectivo')).getByText(T.CHIP_INACTIVA)).toBeInTheDocument();
    expect(within(fila('efectivo')).getByRole('button', { name: T.REACTIVAR })).toBeInTheDocument();
    // Fuera de la vista previa: ya no se ofrece.
    expect(within(screen.getByTestId('vista-previa')).queryByText('Pago en caja')).toBeNull();
  });

  it('desactivar sin motivo no llama a la API y lo dice en el campo (la confirmación cuelga del resultado)', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('efectivo')).getByRole('button', { name: T.DESACTIVAR }));
    await fireEvent.click(screen.getByRole('button', { name: T.DESACTIVAR_OPCION }));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);
    expect(within(fila('efectivo')).getByText(T.CHIP_ACTIVA)).toBeInTheDocument();
  });

  it('una inactiva se reactiva por el mismo camino: con su motivo', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('prepago')).getByRole('button', { name: T.REACTIVAR }));
    expect(screen.getByTestId('confirmacion-estado').textContent).toContain('¿Reactivar «Bono prepago»?');
    await fireEvent.click(screen.getByRole('button', { name: T.REACTIVAR_OPCION }));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);
    await fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: 'Vuelve a venderse.' } });
    await fireEvent.click(screen.getByRole('button', { name: T.REACTIVAR_OPCION }));
    await waitFor(() => expect(within(fila('prepago')).getByText(T.CHIP_ACTIVA)).toBeInTheDocument());
  });
});

describe('crear una versión propia de una lista heredada', () => {
  it('avisa de que la actividad dejará de ver la lista del proceso y, al crearla, tiene una copia exacta', async () => {
    const kit = await abrir('duraciones_modalidad', { proceso: PROCESO, actividad: ACT_DECANATO });
    expect(screen.getByText(/Esta actividad usa la lista de «Becas de estudio · todo el proceso»/)).toBeInTheDocument();
    expect(screen.getByText(/dejará de ver la lista del proceso y usará solo la suya/)).toBeInTheDocument();
    expect(screen.getByText(T.CHIP_HEREDADA, { selector: '.chip' })).toBeInTheDocument();
    // Heredada: se lee, no se edita.
    expect(screen.queryByRole('button', { name: T.EDITAR })).toBeNull();

    await fireEvent.click(screen.getByRole('button', { name: T.CREAR_VERSION_PROPIA }));
    await fireEvent.click(screen.getByTestId('confirmar-ambito'));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);

    await fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: 'El decanato necesita 72 semanas.' } });
    await fireEvent.click(screen.getByTestId('confirmar-ambito'));
    await waitFor(() => expect(screen.queryByTestId('confirmacion-ambito')).toBeNull());
    expect(kit.escrituras[0].datos).toMatchObject({ accion: 'CREAR_VERSION_PROPIA', definicion: 'duraciones_modalidad', ambito: { proceso: PROCESO, actividad: ACT_DECANATO } });
    // Ahora es propia, con la copia exacta (12 a 60) y editable.
    expect(screen.getByText(T.LISTA_PROPIA_DE_LA_ACTIVIDAD, { selector: '.chip' })).toBeInTheDocument();
    expect(fila('60')).toBeInTheDocument();
    expect(within(fila('12')).getByRole('button', { name: T.EDITAR })).toBeInTheDocument();
  });

  it('una versión propia avisa de cuántas opciones nuevas tiene el origen', async () => {
    await abrir('duraciones_modalidad', { proceso: PROCESO, actividad: ACT_COMITE });
    expect(screen.getByText(/El origen tiene 3 opciones nuevas/)).toBeInTheDocument();
  });
});

describe('guardar sin motivo', () => {
  it('el campo muestra el error en lenguaje de negocio y no se guarda ni se traza nada', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('cheque')).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque certificado' } });
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));

    const campo = screen.getByLabelText(/Motivo del cambio/);
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    expect(kit.escrituras).toHaveLength(0);
    // El formulario sigue abierto con lo que se había escrito.
    expect((screen.getByLabelText(/Nombre que ve el formulario/) as HTMLInputElement).value).toBe('Cheque certificado');
    // Un motivo de solo espacios tampoco vale.
    await fireEvent.input(campo, { target: { value: '   ' } });
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    expect(kit.escrituras).toHaveLength(0);
  });

  it('un nombre vacío tampoco se envía', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('cheque')).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: '  ' } });
    await motivo('Ajuste.');
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    expect(await screen.findByText(T.ERROR_ETIQUETA)).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);
  });

  it('si otra persona cambió la opción mientras se editaba, el servidor rechaza la versión vieja: se explica y no se pierde lo escrito', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('cheque')).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque certificado' } });
    await motivo('Mi cambio.');

    // Otra persona guarda primero (por el mismo doble): la versión que leyó la pantalla ya no es la vigente.
    const leida = (await kit.valores('vias_pago')).filas.find((f) => f.codigo === 'cheque');
    await kit.cambiar({
      accion: 'EDITAR',
      definicion: 'vias_pago',
      ambito: VIAS,
      codigoPadre: '*',
      codigo: 'cheque',
      datos: { etiqueta: 'Cheque de caja' },
      persistenceVersion: leida?.persistenceVersion,
      motivo: 'Otra persona.',
    });

    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    expect(await screen.findByText(T.FALLO_CONFLICTO)).toBeInTheDocument();
    expect(screen.getByTestId('formulario-edicion')).toBeInTheDocument();
    expect((screen.getByLabelText(/Nombre que ve el formulario/) as HTMLInputElement).value).toBe('Cheque certificado');
    expect(document.body.textContent).not.toMatch(/persistenceVersion|CONFLICTO|409/);
    // Nada se pisó: sigue el nombre de la otra persona.
    expect((await kit.valores('vias_pago')).filas.find((f) => f.codigo === 'cheque')?.etiqueta).toBe('Cheque de caja');
  });
});

describe('dónde se usa sale de los usos registrados', () => {
  const usos: Usos = {
    lugares: [
      { tipo: 'FORMULARIO', titulo: 'Preparar pago', detalle: 'campo «Vía de pago» · se muestra como opciones en ficha.' },
      { tipo: 'DOCUMENTO', titulo: 'Carta de pago', detalle: 'Imprime el nombre de la vía elegida.' },
      { tipo: 'REGLA', titulo: 'Alta contable en el core', detalle: 'Usa el código, no el nombre.' },
    ],
    expedientes: [
      { codigo: 'transferencia', guardados: '198', enCurso: '11' },
      { codigo: 'prepago', guardados: '12', enCurso: '0' },
    ],
  };

  it('el diálogo de desactivar dice dónde se usa la opción cuando el módulo lo sabe', async () => {
    await abrir('vias_pago', VIAS, 'superadministracion', 'valores', usos);
    await screen.findByTestId('vista-lista');
    await waitFor(() => expect(screen.queryByTestId('opcion-transferencia')).not.toBeNull());
    await fireEvent.click(within(fila('transferencia')).getByRole('button', { name: T.DESACTIVAR }));
    const aviso = (await screen.findByTestId('usos-de-la-opcion')).textContent ?? '';
    expect(aviso).toContain('Preparar pago');
    expect(aviso).toContain('198');
  });

  it('y cuando la lectura de usos falla, lo dice en el diálogo: no calla ni inventa', async () => {
    location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'valores' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', fallos: { usos: new FalloDelKit('SERVIDOR') } }) });
    await screen.findByTestId('vista-lista');
    await fireEvent.click(within(await screen.findByTestId('opcion-transferencia')).getByRole('button', { name: T.DESACTIVAR }));
    expect((await screen.findByTestId('usos-de-la-opcion')).textContent).toContain(T.DESACTIVAR_USOS_ERROR);
  });

  it('con los usos registrados enseña formularios, documentos y reglas y los expedientes por opción', async () => {
    await abrir('vias_pago', VIAS, 'superadministracion', 'usos', usos);
    const lugares = await screen.findByTestId('usos-lugares');
    expect(lugares.textContent).toContain('Preparar pago');
    expect(lugares.textContent).toContain('Carta de pago');
    expect(lugares.textContent).toContain('Alta contable en el core');
    const tabla = screen.getByTestId('usos-expedientes');
    expect(tabla.textContent).toContain('Transferencia a la cuenta del becario');
    expect(tabla.textContent).toContain('198');
    expect(tabla.textContent).toContain('Bono prepago');
    expect(within(tabla).getByText(T.CHIP_INACTIVA)).toBeInTheDocument();
  });

  it('si la lectura de usos falla, la pantalla lo dice: no pinta un vacío que parezca «nadie la usa»', async () => {
    location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: VIAS, pestana: 'usos' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', fallos: { usos: new FalloDelKit('SERVIDOR') } }) });
    expect(await screen.findByTestId('usos-error')).toBeInTheDocument();
    expect(screen.queryByTestId('usos-vacio')).toBeNull();
  });
});

describe('cascada con una modalidad sin duraciones', () => {
  it('al elegir ficha explica que es correcto y que el campo no aparecerá', async () => {
    await abrir('duraciones_modalidad', { proceso: PROCESO, actividad: '*' });
    expect(screen.getByRole('button', { name: /Curso en línea · 5/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Taller presencial · 0/ })).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: /Taller presencial · 0/ }));
    expect(await screen.findByText(/Taller presencial no tiene opciones en esta lista/)).toBeInTheDocument();
    expect(screen.getByText(/es correcto si Taller presencial no usa esta lista/i)).toBeInTheDocument();
    expect(screen.getByText(/el campo «Duraciones por modalidad» no aparece/)).toBeInTheDocument();
  });

  it('añadir una duración para una modalidad crea la opción con SU padre', async () => {
    const kit = await abrir('duraciones_modalidad', { proceso: PROCESO, actividad: '*' });
    await fireEvent.click(screen.getByRole('button', { name: /Taller presencial · 0/ }));
    await fireEvent.click(screen.getByTestId('anadir-opcion'));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: '6 semanas' } });
    await fireEvent.input(screen.getByLabelText(/^Código/), { target: { value: '6' } });
    await motivo('Taller con duración corta.');
    await fireEvent.click(screen.getByTestId('guardar-nueva'));
    await waitFor(() => expect(kit.escrituras).toHaveLength(1));
    expect(kit.escrituras[0].datos).toMatchObject({ accion: 'CREAR', definicion: 'duraciones_modalidad', codigoPadre: 'taller', codigo: '6' });
  });
});

describe('volver a heredar la lista del proceso', () => {
  it('con el motivo escrito, la actividad vuelve a ver la lista del proceso y el cambio queda en el historial', async () => {
    const kit = await abrir('duraciones_modalidad', { proceso: PROCESO, actividad: ACT_COMITE });
    await fireEvent.click(screen.getByRole('button', { name: T.VOLVER_A_HEREDAR }));
    const dialogo = screen.getByTestId('confirmacion-ambito');
    expect(dialogo.textContent).toContain('¿Volver a heredar la lista del proceso?');
    await fireEvent.input(within(dialogo).getByLabelText(/Motivo del cambio/), { target: { value: 'El comité usa las duraciones estándar.' } });
    await fireEvent.click(screen.getByTestId('confirmar-ambito'));
    await waitFor(() => expect(screen.queryByTestId('confirmacion-ambito')).toBeNull());
    expect(kit.escrituras[0].datos).toMatchObject({ accion: 'VOLVER_A_HEREDAR', ambito: { proceso: PROCESO, actividad: ACT_COMITE }, motivo: 'El comité usa las duraciones estándar.' });
    expect(screen.getByText(T.CHIP_HEREDADA, { selector: '.chip' })).toBeInTheDocument();

    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANA_HISTORIAL }));
    const eventos = await screen.findByTestId('eventos');
    await waitFor(() => expect(eventos.textContent).toContain('volvió a heredar'));
    expect(eventos.textContent).toContain('El comité usa las duraciones estándar.');
  });
});

describe('orden de la lista', () => {
  it('subir una opción arma un orden nuevo que se guarda con su motivo, no al pulsar la flecha', async () => {
    const kit = await abrir('vias_pago', VIAS);
    await fireEvent.click(within(fila('efectivo')).getByRole('button', { name: T.subirA('Pago en caja') }));
    expect(kit.escrituras).toHaveLength(0); // mover no escribe
    const filas = screen.getAllByTestId(/^opcion-/).map((r) => r.getAttribute('data-testid'));
    expect(filas.slice(0, 3)).toEqual(['opcion-transferencia', 'opcion-efectivo', 'opcion-cheque']);

    await fireEvent.click(screen.getByTestId('guardar-orden'));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);

    await fireEvent.input(within(screen.getByTestId('confirmacion-orden')).getByLabelText(/Motivo del cambio/), { target: { value: 'Efectivo se usa más.' } });
    await fireEvent.click(screen.getByTestId('guardar-orden'));
    await waitFor(() => expect(kit.escrituras).toHaveLength(1));
    const p = kit.escrituras[0].datos as { accion: string; datos: { orden: Array<{ codigo: string; persistenceVersion: number }> } };
    expect(p.accion).toBe('ORDENAR');
    expect(p.datos.orden.map((o) => o.codigo)).toEqual(['transferencia', 'efectivo', 'cheque', 'prepago']);
    expect(p.datos.orden.every((o) => typeof o.persistenceVersion === 'number')).toBe(true);
  });
});

describe('quién puede qué', () => {
  it('la consulta ve la lista sin ningún control de edición', async () => {
    await abrir('vias_pago', VIAS, 'consulta');
    expect(screen.queryByRole('button', { name: T.EDITAR })).toBeNull();
    expect(screen.queryByTestId('anadir-opcion')).toBeNull();
    expect(screen.queryByRole('button', { name: T.DESACTIVAR })).toBeNull();
    expect(screen.queryByRole('button', { name: T.VOLVER_A_HEREDAR })).toBeNull();
    expect(screen.getByTestId('tabla-de-valores')).toBeInTheDocument();
  });

  it('el delegado edita lo de su proceso', async () => {
    await abrir('vias_pago', VIAS, 'delegado');
    expect(within(fila('cheque')).getByRole('button', { name: T.EDITAR })).toBeInTheDocument();
  });

  it('desde el inicio se llega a la lista y se vuelve', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    render(Parametros, { kit });
    await screen.findByText('Hola, Marta Rivas');
    await fireEvent.click(screen.getByTestId('fila-vias_pago'));
    expect(await screen.findByTestId('vista-lista')).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: new RegExp(T.VOLVER_A_TODOS) }));
    expect(await screen.findByText('Hola, Marta Rivas')).toBeInTheDocument();
  });
});
