process.env.TZ = 'America/Santo_Domingo';

import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import Calendario from './Calendario.svelte';
import { conValorEnlazado } from '$pruebas/valorEnlazado.svelte';
import type { DiaDeLaSemana } from './fechasDelCalendario';

/**
 * El calendario del cimiento. Los fixtures son los del calendario APROBADO
 *: octubre de 2026, el 1 es jueves, el 4 domingo, fines de semana no hábiles y un
 * rango «desde el 29 de septiembre hasta el 29 de octubre».
 *
 * El teclado se dispara con `fireEvent` (`user-event` no está en la lista `allow`); lo que jsdom no
 * hace —la activación nativa, la geometría, el foco VISIBLE— se mide en Chromium.
 */

const RANGO = {
  minimo: '2026-09-29',
  maximo: '2026-10-29',
  noHabiles: { diasDeLaSemana: [0, 6] as const, fechas: ['2026-10-12'] },
};

interface Montaje {
  valor?: string | null;
  error?: string | null;
  deshabilitado?: boolean;
  minimo?: string;
  maximo?: string;
  noHabiles?: { diasDeLaSemana?: readonly DiaDeLaSemana[]; fechas?: readonly string[] };
}

/** Monta con el valor ENLAZADO (getter/setter): así se ve lo que el componente entrega. */
function montar(extra: Montaje = {}) {
  const { valor: inicial = null, ...resto } = extra;
  const enlace = conValorEnlazado(
    { id: 'fecha', etiqueta: 'Fecha de inicio', hoy: '2026-09-29', ...resto },
    inicial as string | null | undefined,
  );
  const r = render(Calendario, { props: enlace.props });
  const campo = r.getByLabelText(/Fecha de inicio/) as HTMLInputElement;
  return { ...r, campo, valor: enlace.valor };
}

const enFoco = () => document.activeElement as HTMLElement;

async function abrir(r: ReturnType<typeof montar>) {
  await fireEvent.click(r.getByRole('button', { name: 'Elegir fecha' }));
  await tick();
}

async function pulsar(tecla: string, extra: Record<string, unknown> = {}) {
  await fireEvent.keyDown(enFoco(), { key: tecla, ...extra });
  await tick();
}

async function teclear(r: ReturnType<typeof montar>, texto: string) {
  await fireEvent.input(r.campo, { target: { value: texto } });
  await fireEvent.blur(r.campo);
  await tick();
}

describe('la rejilla expone su rol y anuncia el día con foco', () => {
  it('el campo de fecha tiene su etiqueta y un botón para abrir el calendario', () => {
    const r = montar();
    expect(r.campo).toHaveAttribute('type', 'text');
    expect(r.getByRole('button', { name: 'Elegir fecha' })).toHaveAttribute('aria-haspopup', 'dialog');
    expect(r.queryByRole('dialog')).toBeNull();
  });

  it('al abrir, un diálogo con una rejilla y el foco DOM en el día elegido, con su fecha completa', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    expect(r.getByRole('dialog', { name: 'Elegir fecha' })).toBeTruthy();
    expect(r.getByRole('grid')).toBeTruthy();
    expect(enFoco()).toHaveAccessibleName('viernes, 2 de octubre de 2026');
    expect(enFoco()).toHaveAttribute('aria-selected', 'true');
    expect(enFoco()).toHaveAttribute('tabindex', '0');
  });

  it('sin valor, el foco entra en hoy, marcado como la fecha actual', async () => {
    const r = montar();
    await abrir(r);
    expect(enFoco()).toHaveAccessibleName('martes, 29 de septiembre de 2026');
    expect(enFoco()).toHaveAttribute('aria-current', 'date');
  });

  it('solo un día está elegido y solo uno está en el orden de tabulación', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    const celdas = r.getAllByRole('gridcell');
    expect(celdas.filter((c) => c.getAttribute('aria-selected') === 'true')).toHaveLength(1);
    expect(celdas.filter((c) => c.getAttribute('tabindex') === '0')).toHaveLength(1);
  });

  it('las cabeceras de la rejilla nombran el día de la semana completo, de lunes a domingo', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    const nombres = r.getAllByRole('columnheader').map((c) => c.getAttribute('abbr'));
    expect(nombres).toEqual(['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']);
  });

  it('las iniciales visibles son las del diseño aprobado: «X» para el miércoles, no dos «M»', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    expect(r.getAllByRole('columnheader').map((c) => c.textContent?.trim())).toEqual(['L', 'M', 'X', 'J', 'V', 'S', 'D']);
  });

  it('el pie dice hoy y hasta cuándo se puede elegir', async () => {
    const r = montar({ valor: '2026-10-02', ...RANGO });
    await abrir(r);
    expect(r.getByText('Hoy: 29 sep')).toBeTruthy();
    expect(r.getByText('Hasta el 29 oct')).toBeTruthy();
  });

  it('el mes visible se anuncia y cambia con sus botones', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    expect(r.getByText('octubre de 2026')).toHaveAttribute('aria-live', 'polite');
    await fireEvent.click(r.getByRole('button', { name: 'Mes siguiente' }));
    expect(r.getByText('noviembre de 2026')).toBeTruthy();
    await fireEvent.click(r.getByRole('button', { name: 'Mes anterior' }));
    await fireEvent.click(r.getByRole('button', { name: 'Mes anterior' }));
    expect(r.getByText('septiembre de 2026')).toBeTruthy();
  });
});

describe('se elige la fecha solo con el teclado', () => {
  it('las flechas mueven por días y semanas', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await pulsar('ArrowRight');
    expect(enFoco()).toHaveAccessibleName('sábado, 3 de octubre de 2026');
    await pulsar('ArrowLeft');
    await pulsar('ArrowLeft');
    expect(enFoco()).toHaveAccessibleName('jueves, 1 de octubre de 2026');
    await pulsar('ArrowDown');
    expect(enFoco()).toHaveAccessibleName('jueves, 8 de octubre de 2026');
    await pulsar('ArrowUp');
    await pulsar('ArrowUp');
    expect(enFoco()).toHaveAccessibleName('jueves, 24 de septiembre de 2026');
  });

  it('Re Pág y Av Pág cambian de mes; Inicio y Fin van al lunes y al domingo de la semana', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await pulsar('PageDown');
    expect(enFoco()).toHaveAccessibleName('lunes, 2 de noviembre de 2026');
    expect(r.getByText('noviembre de 2026')).toBeTruthy();
    await pulsar('PageUp');
    await pulsar('Home');
    expect(enFoco()).toHaveAccessibleName('lunes, 28 de septiembre de 2026');
    await pulsar('End');
    expect(enFoco()).toHaveAccessibleName('domingo, 4 de octubre de 2026');
  });

  it('Enter elige el día con foco, cierra y devuelve el foco al campo', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await pulsar('ArrowDown');
    await pulsar('Enter');
    expect(r.valor()).toBe('2026-10-09');
    expect(r.campo.value).toBe('09/10/2026');
    expect(r.queryByRole('dialog')).toBeNull();
    expect(enFoco()).toBe(r.campo);
  });

  it('Espacio también elige', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await pulsar('ArrowRight');
    await pulsar('ArrowRight');
    await pulsar('ArrowRight');
    await pulsar(' ');
    expect(r.valor()).toBe('2026-10-05');
  });

  it('Escape cierra sin cambiar el valor y devuelve el foco al campo', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await pulsar('ArrowRight');
    await pulsar('Escape');
    expect(r.queryByRole('dialog')).toBeNull();
    expect(r.valor()).toBe('2026-10-02');
    expect(enFoco()).toBe(r.campo);
  });

  it('un clic en un día lo elige', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await fireEvent.click(r.getByRole('gridcell', { name: 'miércoles, 7 de octubre de 2026' }));
    expect(r.valor()).toBe('2026-10-07');
    expect(r.queryByRole('dialog')).toBeNull();
  });

  it('el Tab queda atrapado en el diálogo: del último control vuelve al primero, y al revés', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    const anterior = r.getByRole('button', { name: 'Mes anterior' });
    await pulsar('Tab');
    expect(enFoco()).toBe(anterior);
    await pulsar('Tab', { shiftKey: true });
    expect(enFoco()).toHaveAccessibleName('viernes, 2 de octubre de 2026');
  });

  it('un clic fuera del calendario lo cierra', async () => {
    const r = montar({ valor: '2026-10-02' });
    await abrir(r);
    await fireEvent.pointerDown(document.body);
    expect(r.queryByRole('dialog')).toBeNull();
    expect(r.valor()).toBe('2026-10-02');
  });
});

describe('fuera de rango, día no hábil o formato inválido', () => {
  it('los días fuera de rango y los no hábiles están deshabilitados en la rejilla', async () => {
    const r = montar({ valor: '2026-10-02', ...RANGO });
    await abrir(r);
    const celda = (nombre: string) => r.getByRole('gridcell', { name: nombre });
    expect(celda('domingo, 4 de octubre de 2026')).toHaveAttribute('aria-disabled', 'true');
    expect(celda('lunes, 12 de octubre de 2026')).toHaveAttribute('aria-disabled', 'true');
    expect(celda('viernes, 30 de octubre de 2026')).toHaveAttribute('aria-disabled', 'true');
    expect(celda('lunes, 28 de septiembre de 2026')).toHaveAttribute('aria-disabled', 'true');
    expect(celda('viernes, 2 de octubre de 2026')).not.toHaveAttribute('aria-disabled');
  });

  it('un día deshabilitado no se elige ni con Enter ni con un clic', async () => {
    const r = montar({ valor: '2026-10-02', ...RANGO });
    await abrir(r);
    await pulsar('ArrowRight');
    expect(enFoco()).toHaveAccessibleName('sábado, 3 de octubre de 2026');
    await pulsar('Enter');
    expect(r.valor()).toBe('2026-10-02');
    expect(r.getByRole('dialog')).toBeTruthy();
    await fireEvent.click(r.getByRole('gridcell', { name: 'domingo, 4 de octubre de 2026' }));
    expect(r.valor()).toBe('2026-10-02');
  });

  it('un día no hábil tecleado: error asociado, campo inválido y sin valor', async () => {
    const r = montar({ valor: '2026-10-02', ...RANGO });
    await teclear(r, '04/10/2026');
    const alerta = r.getByRole('alert');
    expect(alerta).toHaveTextContent('El 4 de octubre es domingo: elige un día hábil.');
    expect(r.campo.getAttribute('aria-describedby')).toContain(alerta.id);
    expect(r.campo).toHaveAttribute('aria-invalid', 'true');
    expect(r.valor()).toBeNull();
  });

  it('una fecha fuera de rango tecleada: error con el rango', async () => {
    const r = montar({ ...RANGO });
    await teclear(r, '30/10/2026');
    expect(r.getByRole('alert')).toHaveTextContent(
      'Elige una fecha entre el 29 de septiembre de 2026 y el 29 de octubre de 2026.',
    );
    expect(r.valor()).toBeNull();
  });

  it('un formato inválido tecleado: error de formato y sin valor', async () => {
    const r = montar({ valor: '2026-10-02', ...RANGO });
    await teclear(r, '2026-10-05');
    expect(r.getByRole('alert')).toHaveTextContent('Escribe la fecha como dd/mm/aaaa.');
    expect(r.valor()).toBeNull();
  });

  it('una fecha válida tecleada se acepta, sin error, y entrega el ISO', async () => {
    const r = montar({ ...RANGO });
    await teclear(r, '5/10/2026');
    expect(r.queryByRole('alert')).toBeNull();
    expect(r.valor()).toBe('2026-10-05');
    expect(r.campo.value).toBe('05/10/2026');
  });

  it('corregir el error lo retira', async () => {
    const r = montar({ ...RANGO });
    await teclear(r, '04/10/2026');
    expect(r.getByRole('alert')).toBeTruthy();
    await teclear(r, '05/10/2026');
    expect(r.queryByRole('alert')).toBeNull();
    expect(r.campo).toHaveAttribute('aria-invalid', 'false');
  });
});

describe('estado deshabilitado', () => {
  it('ni el campo ni el botón se pueden usar', () => {
    const r = montar({ valor: '2026-10-02', deshabilitado: true });
    expect(r.campo).toBeDisabled();
    expect(r.getByRole('button', { name: 'Elegir fecha' })).toBeDisabled();
  });
});
