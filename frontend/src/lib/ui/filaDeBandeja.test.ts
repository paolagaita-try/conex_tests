/**
 * La fila de bandeja es un botón legible en un vistazo: título, meta unida por « · », la nota de
 * quién la tomó, y la marca de seleccionada. Sin botón de tomar.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import axe from 'axe-core';
import FilaDeBandeja from './FilaDeBandeja.svelte';

describe('FilaDeBandeja', () => {
  it('es un botón con el título, la meta y su testid, y avisa al abrir', async () => {
    const onabrir = vi.fn();
    const { getByRole } = render(FilaDeBandeja, {
      props: { titulo: 'Revisar la solicitud', meta: ['2026-000123', 'Camila P.', 'hace 2 h'], onabrir, prueba: 'fila-1' },
    });
    const fila = getByRole('button', { name: /Revisar la solicitud/ });
    expect(fila).toHaveAttribute('data-testid', 'fila-1');
    expect(fila).toHaveTextContent('2026-000123 · Camila P. · hace 2 h');
    expect(fila).not.toHaveAttribute('aria-current');
    await fireEvent.click(fila);
    expect(onabrir).toHaveBeenCalledTimes(1);
  });

  it('dice quién la tomó y marca la seleccionada como actual', () => {
    const { getByRole, queryByRole } = render(FilaDeBandeja, {
      props: { titulo: 'Revisar la solicitud', atendidaPor: 'Luis Gerente', seleccionada: true },
    });
    const fila = getByRole('button');
    expect(fila).toHaveTextContent('Tomada por Luis Gerente');
    expect(fila).toHaveAttribute('aria-current', 'true');
    // Ni «tomar» ni «liberar»: la bandeja no asigna (§3.5).
    expect(queryByRole('button', { name: /tomar|liberar/i })).toBeNull();
  });

  it('axe no encuentra infracciones', async () => {
    const { container } = render(FilaDeBandeja, { props: { titulo: 'Revisar', meta: ['x'] } });
    const r = await axe.run(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
    });
    expect(r.violations.map((v) => v.id)).toEqual([]);
  });
});
