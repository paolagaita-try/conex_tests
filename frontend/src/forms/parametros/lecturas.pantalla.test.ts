/**
 * Una lectura que falla se dice como fallo (B2) y la verificación de la cadena mira toda la cadena (B1):
 * el contenedor real con un doble que falla en CADA lectura de la aplicación, y que, como el kit real,
 * solo ve una entrada interior manipulada con `verificar(true)`.
 */
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { FalloDelKit, type Kit } from './kit';
import { kitDeEjemplo, type OpcionesDelKit, type PerfilDeEjemplo } from './ejemplo';
import { hashDe, type Ruta } from './ruta';
import * as T from './textos';

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
const SERVIDOR = new FalloDelKit('SERVIDOR');
const GLOBAL = { proceso: '*', actividad: '*' };
const LISTA: Ruta = { vista: 'definicion', definicion: 'vias_pago', ambito: GLOBAL, pestana: 'historial' };
const PARAMETRO = (pestana: 'valores' | 'usos' | 'historial'): Ruta => ({ vista: 'definicion', definicion: 'porcentaje_beca', ambito: GLOBAL, pestana });

describe('B2 · un fallo de lectura no se pinta como dato', () => {
  it('Permisos: sin leer las delegaciones no dice «no hay delegaciones»', async () => {
    abrir({ vista: 'permisos' }, { fallaDespuesDe: { delegaciones: 0 } });
    expect(await screen.findByTestId('permisos-error')).toBeInTheDocument();
    expect(screen.queryByTestId('permisos-vacio')).toBeNull();
    expect(screen.queryByTestId('vista-permisos')).toBeNull();
  });

  it('Aprobaciones: sin leer las propuestas no dice «nada espera tu aprobación»', async () => {
    abrir({ vista: 'aprobaciones' }, { fallaDespuesDe: { propuestas: 1 } });
    expect(await screen.findByTestId('aprobaciones-error')).toBeInTheDocument();
    expect(screen.queryByTestId('aprobaciones-vacio')).toBeNull();
  });

  it('Traza: sin leer la traza no dice «ninguna entrada coincide»', async () => {
    abrir({ vista: 'traza' }, { fallaDespuesDe: { traza: 1 } });
    expect(await screen.findByTestId('traza-error')).toBeInTheDocument();
    expect(screen.queryByTestId('traza-vacia')).toBeNull();
  });

  it('Traza: una verificación que falla lo dice; no se queda muda', async () => {
    abrir({ vista: 'traza' }, { fallos: { verificar: SERVIDOR } });
    await fireEvent.click(await screen.findByTestId('verificar'));
    expect(await screen.findByTestId('verificacion-error')).toBeInTheDocument();
    expect(screen.queryByTestId('resultado-de-verificacion')).toBeNull();
  });

  it('Lista: el historial que falla se dice', async () => {
    abrir(LISTA, { fallaDespuesDe: { traza: 1 } });
    expect(await screen.findByTestId('historial-error')).toBeInTheDocument();
    expect(screen.queryByTestId('historial-vacio')).toBeNull();
  });

  it('Lista: quién edita, cuando falla, se dice', async () => {
    abrir({ ...LISTA, pestana: 'valores' }, { fallaDespuesDe: { editores: 0 } });
    expect(await screen.findByTestId('editores-error')).toBeInTheDocument();
  });

  it('Parámetro: quién edita, cuando falla, se dice', async () => {
    abrir(PARAMETRO('valores'), { fallaDespuesDe: { editores: 0 } });
    expect(await screen.findByTestId('editores-error')).toBeInTheDocument();
  });

  it('Parámetro: los usos que fallan no se confunden con «aún no disponible»', async () => {
    abrir(PARAMETRO('usos'), { fallos: { usos: SERVIDOR } });
    expect(await screen.findByTestId('usos-error')).toBeInTheDocument();
    expect(screen.queryByTestId('usos-no-disponible')).toBeNull();
  });

  it('Parámetro: la cadena que no se pudo verificar no se calla', async () => {
    abrir(PARAMETRO('historial'), { fallos: { verificar: SERVIDOR } });
    await waitFor(() => expect(document.body.textContent).toContain(T.ERROR_CADENA));
  });

  it('el arranque: una lectura de identidad que falla es un error, no un perfil «de consulta»', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const roto: Kit = { ...kit, membresias: async () => { throw SERVIDOR; } };
    render(Parametros, { kit: roto });
    expect(await screen.findByText(T.ERROR_TITULO)).toBeInTheDocument();
  });

  it('el arranque: los procesos que no se pueden leer son un error, no una aplicación sin procesos', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const roto: Kit = { ...kit, procesos: async () => { throw SERVIDOR; } };
    render(Parametros, { kit: roto });
    expect(await screen.findByText(T.ERROR_TITULO)).toBeInTheDocument();
  });
});

describe('B1 · la verificación mira TODA la cadena', () => {
  it('una entrada interior manipulada (previa al último punto verificado) se detecta', async () => {
    abrir({ vista: 'traza' }, { manipulacion: 'interior' });
    await fireEvent.click(await screen.findByTestId('verificar'));
    const r = await screen.findByTestId('resultado-de-verificacion');
    expect(r.textContent).toContain('Deja de casar');
    expect(r.textContent).not.toContain('coincide');
  });

  it('gemela: una manipulación posterior al punto verificado también se detecta', async () => {
    abrir({ vista: 'traza' }, { manipulacion: 'posterior' });
    await fireEvent.click(await screen.findByTestId('verificar'));
    expect((await screen.findByTestId('resultado-de-verificacion')).textContent).toContain('Deja de casar');
  });

  it('la cadena rota habla de la lista por su nombre, no por su código', async () => {
    abrir({ vista: 'traza' }, { cadenaRota: true });
    await fireEvent.click(await screen.findByTestId('verificar'));
    const t = (await screen.findByTestId('resultado-de-verificacion')).textContent ?? '';
    expect(t).toContain('Vías de pago');
    expect(t).not.toContain('vias_pago');
  });

  it('una cadena íntegra dice que se comprobó toda', async () => {
    abrir({ vista: 'traza' });
    await fireEvent.click(await screen.findByTestId('verificar'));
    expect((await screen.findByTestId('resultado-de-verificacion')).textContent).toContain('cada entrada coincide');
  });

  it('el estado de la cadena en el historial de un parámetro también es la verificación completa', async () => {
    abrir(PARAMETRO('historial'), { manipulacion: 'interior' });
    await waitFor(() => expect(document.body.textContent).toContain(T.CADENA_NO_COHERENTE_CHIP));
    expect(document.body.textContent).not.toContain('Cadena coherente ·');
  });
});

describe('quién hizo cada cambio, por su nombre', () => {
  it('el historial de un parámetro no cuenta a nadie por su usuario', async () => {
    abrir(PARAMETRO('historial'));
    await waitFor(() => expect(screen.queryByTestId('eventos')).not.toBeNull());
    const t = screen.getByTestId('eventos').textContent ?? '';
    expect(t).not.toMatch(/\b[a-z]+\.[a-z]+ (propuso|aprobó|rechazó|retiró|cambió|fijó|desactivó|añadió)/);
  });
});

describe('B1/B4 · gemelas de lo que sobrevivió a la mutación', () => {
  it('verificar una cadena sin entradas no afirma que «coinciden»', async () => {
    abrir({ vista: 'traza' }, { cadenaVacia: true });
    await fireEvent.click(await screen.findByTestId('verificar'));
    const t = (await screen.findByTestId('resultado-de-verificacion')).textContent ?? '';
    expect(t).toContain(T.CADENA_SIN_ENTRADAS_CUERPO);
    expect(t).not.toContain('coincide');
  });

  it('y el historial de un parámetro no pinta «verificada» con cero entradas comprobadas', async () => {
    abrir(PARAMETRO('historial'), { cadenaVacia: true });
    await waitFor(() => expect(screen.queryByTestId('eventos')).not.toBeNull());
    expect(document.body.textContent).not.toContain('Cadena coherente ·');
  });

  it('quien hizo un cambio antiguo se cuenta por su nombre aunque ninguna otra pantalla lo haya nombrado', async () => {
    abrir(PARAMETRO('historial'), { usuarioAjeno: true });
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('Olga Negocio'));
    expect(screen.getByTestId('eventos').textContent).not.toContain('olga.negocio');
  });
});

describe('la búsqueda de personas, grupos y roles', () => {
  it('si falla, la aplicación abre y solo Permisos lo dice (no «no disponible» ni error general)', async () => {
    abrir({ vista: 'inicio' }, { fallos: { organizacion: SERVIDOR } });
    expect(await screen.findAllByRole('tab')).not.toHaveLength(0);
    expect(screen.queryByText(T.ERROR_TITULO)).toBeNull();
    expect(screen.queryByTestId('no-disponible')).toBeNull();
    await fireEvent.click(screen.getByRole('tab', { name: /Permisos/ }));
    expect(await screen.findByTestId('organizacion-error')).toBeInTheDocument();
    expect(screen.queryByTestId('permisos-vacio')).toBeNull();
  });
});
