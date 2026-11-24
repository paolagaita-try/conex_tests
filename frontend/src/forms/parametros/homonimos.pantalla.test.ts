/**
 * B4: personas, grupos y roles se identifican por su ID, no por el nombre que se ve. Dos «Ana Ruiz», dos roles que se
 * humanizan igual y dos «Sara Parametros» en la traza son siete cosas distintas, y ninguna rompe la pantalla ni se confunde.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { kitDeEjemplo, PROCESO } from './ejemplo';
import { etiquetasUnicas, nombresUnicos } from './nombres';
import { hashDe, type Ruta } from './ruta';

const errores: string[] = [];
beforeEach(() => {
  location.hash = '';
  errores.length = 0;
  window.addEventListener('error', (e) => errores.push(e.message));
});
afterEach(cleanup);

function abrir(ruta: Ruta) {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil: 'superadministracion', homonimos: true });
  render(Parametros, { kit });
  return kit;
}

describe('etiquetas únicas', () => {
  it('el que no se repite se queda; los que se repiten se distinguen por su extra y, si coincide, por una letra', () => {
    const r = etiquetasUnicas([
      { id: 1, nombre: 'Ana Ruiz', extra: 'ana.ruiz' },
      { id: 2, nombre: 'Ana Ruiz', extra: 'ana.ruiz2' },
      { id: 3, nombre: 'Luis Gil', extra: 'luis.gil' },
      { id: 4, nombre: 'Jefe evaluacion', extra: 'jefeEvaluacion' },
      { id: 5, nombre: 'Jefe evaluacion', extra: 'jefeEvaluacion' },
    ]);
    expect(r.map((x) => x.nombre)).toEqual(['Ana Ruiz · ana.ruiz', 'Ana Ruiz · ana.ruiz2', 'Luis Gil', 'Jefe evaluacion · jefeEvaluacion · A', 'Jefe evaluacion · jefeEvaluacion · B']);
    expect(new Set(r.map((x) => x.nombre)).size).toBe(5);
    expect(r.map((x) => x.id)).toEqual([1, 2, 3, 4, 5]);
  });
  it('dos personas con el mismo nombre en un texto se distinguen por su usuario', () => {
    expect(nombresUnicos({ a: 'Sara', b: 'Sara', c: 'Luis' })).toEqual({ a: 'Sara (a)', b: 'Sara (b)', c: 'Luis' });
  });
});

describe('Nueva delegación con homónimos', () => {
  it('dos «Ana Ruiz»: se pueden elegir las dos, sin error de clave repetida, y se envía el ID de la elegida', async () => {
    const kit = abrir({ vista: 'nuevaDelegacion' });
    await fireEvent.click(await screen.findByText('Una persona', { exact: true }));
    await fireEvent.input(screen.getByRole('combobox', { name: /Persona/ }), { target: { value: 'Ana' } });
    const opciones = await screen.findAllByRole('option', { name: /Ana Ruiz/ });
    expect(opciones.length).toBe(2);
    expect(opciones[0]!.textContent).not.toBe(opciones[1]!.textContent);
    await fireEvent.click(screen.getByRole('option', { name: /ana\.ruiz2/ }));
    await fireEvent.change(screen.getByLabelText(/^Proceso/), { target: { value: PROCESO } });
    await fireEvent.input(screen.getAllByLabelText(/Motivo/).at(-1)!, { target: { value: 'Cobertura.' } });
    await fireEvent.click(screen.getByTestId('enviar-delegacion'));
    await waitFor(() => expect(kit.escrituras.filter((e) => e.operacion === 'delegar')).toHaveLength(1));
    const d = (kit.escrituras.find((e) => e.operacion === 'delegar')?.datos as { d: { sujetoUsuarioId: number } }).d;
    expect(d.sujetoUsuarioId).toBe(32); // la segunda, no «la primera que se llame Ana Ruiz»
    expect(errores.filter((m) => /each_key_duplicate|duplicate/i.test(m))).toEqual([]);
  });

  it('dos roles que se humanizan igual: la pantalla abre, ofrece los dos y envía el ID del elegido', async () => {
    const kit = abrir({ vista: 'nuevaDelegacion' });
    await fireEvent.click(await screen.findByText('Un rol', { exact: true }));
    await fireEvent.input(screen.getByRole('combobox', { name: /^Rol/ }), { target: { value: 'Jefe' } });
    const opciones = await screen.findAllByRole('option', { name: /Jefe evaluacion/ });
    const rotulos = opciones.map((o) => o.textContent ?? '');
    expect(rotulos.length).toBeGreaterThanOrEqual(3); // jefeEvaluacion (ya existente) + los dos homónimos
    expect(new Set(rotulos).size).toBe(rotulos.length);
    await fireEvent.click(opciones.find((o) => /jefe_evaluacion/.test(o.textContent ?? ''))!);
    await fireEvent.change(screen.getByLabelText(/^Proceso/), { target: { value: PROCESO } });
    await fireEvent.input(screen.getAllByLabelText(/Motivo/).at(-1)!, { target: { value: 'Cobertura.' } });
    await fireEvent.click(screen.getByTestId('enviar-delegacion'));
    await waitFor(() => expect(kit.escrituras.filter((e) => e.operacion === 'delegar')).toHaveLength(1));
    expect((kit.escrituras.find((e) => e.operacion === 'delegar')?.datos as { d: { sujetoRolId: number } }).d.sujetoRolId).toBe(42);
  });
});

describe('Traza con dos «Sara Parametros»', () => {
  it('el filtro «Persona» es por usuario: no mezcla las entradas de la otra', async () => {
    abrir({ vista: 'traza' });
    await screen.findByTestId('eventos');
    await fireEvent.input(screen.getByRole('combobox', { name: /Persona/ }), { target: { value: 'Sara' } });
    const saras = await screen.findAllByRole('option', { name: /Sara Parametros/ });
    expect(saras.length).toBe(2);
    expect(saras[0]!.textContent).not.toBe(saras[1]!.textContent);
    await fireEvent.click(saras.find((o) => /sara\.parametros2/.test(o.textContent ?? ''))!);
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).not.toContain('propuso'));
    expect(screen.getByTestId('eventos').textContent).toContain('aprobó');
  });

  it('no se lee «Sara Parametros aprobó…, propuesto por Sara Parametros»: se distinguen', async () => {
    abrir({ vista: 'traza' });
    await screen.findByTestId('eventos');
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toMatch(/Sara Parametros \(sara\.parametros2\) aprobó/));
    expect(within(screen.getByTestId('eventos')).getByText(/propuesto por Sara Parametros \(sara\.parametros\)/)).toBeInTheDocument();
  });
});

describe('«Quién puede editar esto» con editores que se leen igual', () => {
  it('no se rompe (clave repetida) ni se vacía: sale la superadministración y cada editor, distintos', async () => {
    const fallos: string[] = [];
    const oir = (e: ErrorEvent) => fallos.push(e.message);
    window.addEventListener('error', oir);
    abrir({ vista: 'definicion', definicion: 'porcentaje_beca', ambito: { proceso: PROCESO, actividad: '*' }, pestana: 'valores' });
    const ficha = await screen.findByLabelText('Quién puede editar esto');
    await waitFor(() => expect(ficha.textContent).toContain('Superadministración'));
    const lineas = [...ficha.querySelectorAll('p')].map((x) => x.textContent ?? '');
    expect(new Set(lineas).size).toBe(lineas.length);
    expect(lineas.filter((l) => /Jefe evaluacion/.test(l)).length).toBe(2);
    expect(lineas.filter((l) => /Ana Ruiz/.test(l)).length).toBe(2);
    window.removeEventListener('error', oir);
    expect(fallos.filter((m) => /each_key_duplicate|duplicate/i.test(m))).toEqual([]);
  });
});
