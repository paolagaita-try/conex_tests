/**
 * La app dice lo que hay aunque haya MÁS que en la demo (>100 propuestas, >100 entradas de traza, >20 personas): cada
 * lectura pagina o busca en el servidor, y nunca afirma «ninguna» mientras quede por leer.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { ACT_PAGO, DELEGACIONES, kitDeEjemplo, PROCESO, type OpcionesDelKit, type PerfilDeEjemplo } from './ejemplo';
import * as T from './textos';
import { hashDe, type Ruta } from './ruta';

beforeEach(() => {
  location.hash = '';
});
afterEach(cleanup);

function abrir(ruta: Ruta, extra: Partial<OpcionesDelKit> = {}, perfil: PerfilDeEjemplo = 'superadministracion') {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil, ...extra });
  render(Parametros, { kit });
  return kit;
}

describe('[1] más de 100 propuestas: las pendientes antiguas no se esconden', () => {
  it('Aprobaciones lista «Esperan tu aprobación» aunque la primera página del kit sean 127 retiradas', async () => {
    abrir({ vista: 'aprobaciones' }, { relleno: 127 });
    expect(await screen.findByTestId('grupo-esperan')).toBeInTheDocument();
    expect(screen.getByTestId('grupo-esperan').textContent).toContain('Tope de aprobación del coordinador');
    expect(screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim())).toContain('Aprobaciones 1');
  });
  it('y el contador de la pestaña también cuenta las pendientes de la segunda página', async () => {
    abrir({ vista: 'inicio' }, { relleno: 127 });
    await waitFor(() => expect(screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim())).toContain('Aprobaciones 1'));
  });
});

describe('[7] la persona de la sesión se distingue de una que se llama igual', () => {
  it('no se lee «propuesto por Marta Rivas» junto a la cabecera «Marta Rivas»: cada una lleva su usuario', async () => {
    abrir({ vista: 'aprobaciones' }, { homonimos: true });
    await screen.findByTestId('grupo-esperan');
    await waitFor(() => expect(document.body.textContent).toContain('Marta Rivas (marta.rivas2)'));
    // La cabecera (la persona de la sesión) también se distingue.
    expect(document.body.textContent).toContain('Marta Rivas (marta.rivas)');
  });
});

describe('[8] un valor leído al arrancar no se pinta como vigente al abrir la definición', () => {
  const porcentaje: Ruta = { vista: 'definicion', definicion: 'tope_coordinador', ambito: { proceso: 'x', actividad: '*' }, pestana: 'valores' };
  it('al abrir se vuelve a leer: otra sesión cambió el valor mientras tanto', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    location.hash = hashDe({ vista: 'inicio' });
    render(Parametros, { kit });
    await screen.findAllByRole('tab');
    // Otra sesión cambia el valor DESPUÉS de que esta arrancó.
    const antes = await kit.valores('tope_coordinador');
    const llamadas: string[] = [];
    const original = kit.valores;
    kit.valores = async (d) => { llamadas.push(d); return original(d); };
    location.hash = hashDe({ ...porcentaje, ambito: { proceso: antes.filas[0]!.proceso, actividad: antes.filas[0]!.actividad } });
    await fireEvent(window, new HashChangeEvent('hashchange'));
    await waitFor(() => expect(llamadas).toContain('tope_coordinador'));
  });
  it('si la lectura al abrir falla, dice que el valor puede estar viejo (no lo pinta mudo)', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion', fallaDespuesDe: { valores: 12 } });
    location.hash = hashDe({ vista: 'inicio' });
    render(Parametros, { kit });
    await screen.findAllByRole('tab');
    location.hash = hashDe({ vista: 'definicion', definicion: 'vias_pago', ambito: { proceso: 'x', actividad: '*' }, pestana: 'valores' });
    await fireEvent(window, new HashChangeEvent('hashchange'));
    expect(await screen.findByTestId('lectura-vieja')).toBeInTheDocument();
  });
});

describe('[5] más de 20 personas: se busca en el servidor y se resuelve por id', () => {
  it('buscar «Zoe» encuentra a la persona 21 (una lista cargada de 20 diría «ninguna coincide»)', async () => {
    abrir({ vista: 'nuevaDelegacion' }, { muchasPersonas: true });
    await fireEvent.click(await screen.findByText('Una persona', { exact: true }));
    await fireEvent.input(screen.getByRole('combobox', { name: /Persona/ }), { target: { value: 'Zoe' } });
    expect(await screen.findByRole('option', { name: /Zoe Ultima · zeta\.ultima/ })).toBeInTheDocument();
    expect(screen.queryByText('Ninguna opción coincide.')).toBeNull();
  });

  it('una delegación a la persona 21 sale con su nombre en Permisos y en el diálogo de revocar, no «Una persona»', async () => {
    const d = { ...DELEGACIONES[0]!, tipoSujeto: 'USUARIO' as const, sujetoUsuarioId: 200, sujetoGrupoId: null, sujetoRolId: null, sujetoRuta: null };
    abrir({ vista: 'permisos' }, { muchasPersonas: true, delegaciones: [d] });
    const tabla = await screen.findByTestId('tabla-de-permisos');
    await waitFor(() => expect(tabla.textContent).toContain('Zoe Ultima'));
    expect(tabla.textContent).not.toMatch(/Una persona/);
    await fireEvent.click(screen.getByRole('button', { name: T.REVOCAR }));
    expect(document.body.textContent).toContain('Zoe Ultima');
  });
});

describe('[3] la Traza con más de 100 entradas', () => {
  it('filtrar por lista sigue leyendo páginas antiguas en vez de decir «ninguna entrada coincide»', async () => {
    abrir({ vista: 'traza' }, { muchasEntradas: 250 });
    await screen.findByTestId('eventos');
    expect(screen.getByTestId('eventos').textContent).not.toContain('prepago'); // las de «Vías» están en la 3.ª página
    await fireEvent.input(screen.getByLabelText(T.FILTRO_QUE), { target: { value: 'Vías' } });
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('prepago'), { timeout: 4000 });
    expect(screen.queryByTestId('traza-vacia')).toBeNull();
  });

  it('el CSV sin filtros descarga TODO lo que hay (no solo las 100 más recientes) y no avisa de recorte', async () => {
    const descargas: string[] = [];
    const csv = await import('./csv');
    const espia = vi.spyOn(csv, 'descargar').mockImplementation((_n, c) => (descargas.push(c), true));
    abrir({ vista: 'traza' }, { muchasEntradas: 250 });
    await screen.findByTestId('eventos');
    await fireEvent.click(screen.getByTestId('exportar-traza'));
    await waitFor(() => expect(descargas.length).toBe(1), { timeout: 4000 });
    const filas = descargas[0]!.replace(/^﻿/, '').trim().split('\r\n').length - 1;
    expect(filas).toBeGreaterThanOrEqual(250 + 4);
    expect(screen.queryByTestId('aviso-de-exportacion')).toBeNull();
    espia.mockRestore();
  });

  it('si hay más de lo que se puede leer, el aviso dice exactamente cuánto se exportó', async () => {
    const csv = await import('./csv');
    const espia = vi.spyOn(csv, 'descargar').mockImplementation(() => true);
    abrir({ vista: 'traza' }, { muchasEntradas: 1100 });
    await screen.findByTestId('eventos');
    await fireEvent.click(screen.getByTestId('exportar-traza'));
    expect((await screen.findByTestId('aviso-de-exportacion', {}, { timeout: 6000 })).textContent).toContain('entradas más recientes que coinciden');
    espia.mockRestore();
  }, 30000);

  it('el filtro por persona lo hace el servidor: encuentra entradas fuera de las 100 más recientes', async () => {
    abrir({ vista: 'traza' }, { muchasEntradas: 250 });
    await screen.findByTestId('eventos');
    await fireEvent.input(screen.getByRole('combobox', { name: /Persona/ }), { target: { value: 'Ana' } });
    await fireEvent.click(await screen.findByRole('option', { name: /Ana Pérez/ }));
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('Ana Pérez'));
    expect(screen.getByTestId('eventos').textContent).not.toContain('Jorge Peña');
  });
});

describe('[4] el historial de una lista no dice «no hay cambios» mientras queden páginas', () => {
  it('con 250 entradas más nuevas de otra lista, las de «Vías de pago» (3.ª página) se encuentran', async () => {
    abrir({ vista: 'definicion', definicion: 'vias_pago', ambito: { proceso: 'Becas de estudio', actividad: '*' }, pestana: 'historial' }, { muchasEntradas: 250 });
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('prepago'), { timeout: 5000 });
    expect(screen.queryByTestId('historial-vacio')).toBeNull();
  });
  it('si el tope de la API se alcanza sin encontrar nada, lo dice (no afirma «no hay cambios»)', async () => {
    abrir({ vista: 'definicion', definicion: 'vias_pago', ambito: { proceso: 'Becas de estudio', actividad: '*' }, pestana: 'historial' }, { muchasEntradas: 1100 });
    expect(await screen.findByTestId('historial-tope', {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.queryByTestId('historial-vacio')).toBeNull();
  }, 30000);
});

describe('teclado: el foco acompaña a los paneles', () => {
  it('abrir la edición lleva el foco a su primer campo; Escape la cierra y el foco vuelve al botón que la abrió', async () => {
    abrir({ vista: 'definicion', definicion: 'vias_pago', ambito: { proceso: PROCESO, actividad: ACT_PAGO }, pestana: 'valores' });
    const fila = await screen.findByTestId('opcion-cheque');
    const editar = within(fila).getByRole('button', { name: T.EDITAR });
    editar.focus();
    await fireEvent.click(editar);
    const form = await screen.findByTestId('formulario-edicion');
    await waitFor(() => expect(form.contains(document.activeElement)).toBe(true));
    await fireEvent.keyDown(form, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('formulario-edicion')).toBeNull());
    expect(document.activeElement).toBe(editar);
  });
});
