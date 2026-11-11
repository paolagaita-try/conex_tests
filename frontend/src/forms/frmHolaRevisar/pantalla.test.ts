/** Pruebas de la pantalla `frm_holaRevisar`. Del proyecto: el arnés las escribió una vez. */
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import FrmHolaRevisar from './FrmHolaRevisar.svelte';
import { CAMPOS, CUERPO_VACIO, ENTRADAS, LECTURAS } from './generado/contrato';
import { TEXTOS } from './textos';
import { NO_LEIDO } from '$lib/bonita/caso';

/** La plataforma: la extensión de lecturas del caso responde `caso` (con `null`, falla). */
function plataforma(caso: Record<string, unknown> | null): string[] {
  const pedidas: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (entrada: string | URL) => {
      const url = String(entrada);
      pedidas.push(url);
      if (!url.includes('/extension/consultas/caso')) return new Response('{}', { status: 404 });
      return caso === null ? new Response('{}', { status: 500 }) : new Response(JSON.stringify(caso), { status: 200 });
    }),
  );
  return pedidas;
}

beforeEach(() => {
  window.history.replaceState(null, '', '/?caseId=7');
  plataforma({});
});
afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, '', '/');
});

describe('pantalla frm_holaRevisar', () => {
  it('pinta un campo por cada dato del contrato que usa la matriz', () => {
    const { container } = render(FrmHolaRevisar, { props: { enviar: vi.fn(async () => undefined) } });
    for (const campo of CAMPOS) {
      const prueba = `campo-${campo.ruta.replace(/\./g, '-')}`;
      expect(container.querySelector(`[data-testid^="${prueba}"]`), campo.ruta).not.toBeNull();
    }
  });

  it('el cuerpo vacío lleva todas las entradas del contrato', () => {
    expect(Object.keys(CUERPO_VACIO).sort()).toEqual([...ENTRADAS].sort());
  });

  it('con los obligatorios vacíos no envía', async () => {
    const enviar = vi.fn(async () => undefined);
    const { container } = render(FrmHolaRevisar, { props: { enviar } });
    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
    expect(enviar).not.toHaveBeenCalled();
  });

  it('muestra los datos del caso que lee de la extensión de lecturas del caso', async () => {
    const caso = Object.fromEntries(
      LECTURAS.flatMap((l): [string, string][] => (l.atributo ? [[l.atributo, `valor de ${l.etiqueta}`]] : [])),
    );
    const pedidas = plataforma(caso);
    const { container } = render(FrmHolaRevisar, { props: { enviar: vi.fn(async () => undefined) } });
    await waitFor(() => expect(container.querySelector('dl.lecturas')?.getAttribute('aria-busy')).toBe('false'));
    const textos = [...container.querySelectorAll('[data-lee]')].map((e) => e.textContent);
    expect(textos).toEqual(LECTURAS.map((l) => (l.atributo ? `valor de ${l.etiqueta}` : NO_LEIDO)));
    expect(pedidas).toContain('/bonita/API/extension/consultas/caso?caseId=7');
  });

  it('si la lectura del caso falla, lo dice', async () => {
    plataforma(null);
    const { findByText } = render(FrmHolaRevisar, { props: { enviar: vi.fn(async () => undefined) } });
    expect(await findByText(TEXTOS.errorLectura)).toBeTruthy();
  });

  it('si la lectura del caso falla, no deja enviar y lo dice', async () => {
    plataforma(null);
    const enviar = vi.fn(async () => undefined);
    const { container, findByText, getByTestId } = render(FrmHolaRevisar, { props: { enviar } });
    expect(await findByText(TEXTOS.sinDatosNoSeEnvia)).toBeTruthy();
    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
    expect(enviar).not.toHaveBeenCalled();
  });

  it('mientras la lectura del caso carga, no deja enviar', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => undefined)));
    const enviar = vi.fn(async () => undefined);
    const { container, getByTestId } = render(FrmHolaRevisar, { props: { enviar } });
    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(true);
    await fireEvent.submit(container.querySelector('form') as HTMLFormElement);
    expect(enviar).not.toHaveBeenCalled();
  });

  it('con los datos del caso leídos, deja enviar', async () => {
    const { container, getByTestId } = render(FrmHolaRevisar, { props: { enviar: vi.fn(async () => undefined) } });
    await waitFor(() => expect(container.querySelector('dl.lecturas')?.getAttribute('aria-busy')).toBe('false'));
    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(false);
  });
});
