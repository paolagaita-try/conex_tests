/**
 * El campo del logo de la marca: se elige un archivo en vez de teclear un `data:` de decenas de miles de caracteres.
 * El servidor valida de nuevo; esto solo comprueba que el selector convierte, rechaza y deja quitar.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { MAXIMO_LOGO } from '$lib/parametros/marca';
import CampoDeValor from './componentes/CampoDeValor.svelte';
import { valorLegible } from './formatos';
import type { Definicion } from './tipos';

const props = { id: 'valor', etiqueta: 'Logo', valor: 'none', tipoDato: 'TEXTO', imagen: true, prueba: 'campo-valor' };

async function elegir(entrada: HTMLElement, archivo: File): Promise<void> {
  Object.defineProperty(entrada, 'files', { value: [archivo], configurable: true });
  await fireEvent.change(entrada);
}

describe('CampoDeValor con imagen (logo de la marca)', () => {
  it('ofrece un selector de archivo, no un campo de texto', () => {
    const { getByTestId, queryByRole } = render(CampoDeValor, { props });
    expect((getByTestId('campo-valor') as HTMLInputElement).type).toBe('file');
    expect(queryByRole('textbox')).toBeNull();
  });

  it('convierte un PNG en data: y enseña la vista previa', async () => {
    const { getByTestId } = render(CampoDeValor, { props });
    await elegir(getByTestId('campo-valor'), new File([new Uint8Array([137, 80, 78, 71])], 'logo.png', { type: 'image/png' }));
    await waitFor(() => expect(getByTestId('logo-vista-previa').getAttribute('src')).toMatch(/^data:image\/png;base64,/));
  });

  it('rechaza un archivo que no es PNG ni SVG, con un mensaje', async () => {
    const { getByTestId, findByRole, queryByTestId } = render(CampoDeValor, { props });
    await elegir(getByTestId('campo-valor'), new File(['%PDF'], 'logo.pdf', { type: 'application/pdf' }));
    expect((await findByRole('alert')).textContent).toMatch(/PNG o SVG/);
    expect(queryByTestId('logo-vista-previa')).toBeNull();
  });

  it('rechaza un logo por encima del tope del servidor', async () => {
    const { getByTestId, findByRole, queryByTestId } = render(CampoDeValor, { props });
    await elegir(getByTestId('campo-valor'), new File([new Uint8Array(MAXIMO_LOGO)], 'grande.png', { type: 'image/png' }));
    expect((await findByRole('alert')).textContent).toMatch(/demasiado grande/);
    // El aviso lleva el tope escrito (la barrera de cifras impide calcularlo): se ata aquí al del servidor.
    expect(MAXIMO_LOGO).toBe(100 * 1024);
    expect((await findByRole('alert')).textContent).toContain('100 KB');
    expect(queryByTestId('logo-vista-previa')).toBeNull();
  });

  it('permite quitar el logo', async () => {
    const { getByTestId, queryByTestId } = render(CampoDeValor, { props: { ...props, valor: 'data:image/png;base64,AAAA' } });
    await fireEvent.click(getByTestId('quitar-logo'));
    await waitFor(() => expect(queryByTestId('logo-vista-previa')).toBeNull());
  });
});

describe('un valor que es una imagen se lee como «imagen», no como la cadena base64', () => {
  const def: Pick<Definicion, 'tipoDato' | 'unidad'> = { tipoDato: 'TEXTO', unidad: null };
  const png = `data:image/png;base64,${'A'.repeat(4096)}`;
  const svg = `data:image/svg+xml;base64,${'B'.repeat(2048)}`;

  it('un PNG', () => {
    const t = valorLegible(def, png);
    expect(t).not.toContain('data:');
    expect(t).not.toContain('AAAA');
    expect(t).toMatch(/Imagen/);
    expect(t).toMatch(/PNG/);
  });

  it('un SVG', () => {
    const t = valorLegible(def, svg);
    expect(t).not.toContain('base64');
    expect(t).toMatch(/SVG/);
  });

  it('un texto corriente no cambia', () => {
    expect(valorLegible(def, 'Academia Norte')).toBe('Academia Norte');
    expect(valorLegible(def, 'none')).toBe('none');
  });
});
