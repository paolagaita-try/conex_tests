/**
 * El vacío se anuncia sin interrumpir (`status`), con el enunciado que le pasa la bandeja y,
 * si procede, una acción dentro.
 */
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import axe from 'axe-core';
import EstadoVacio from './EstadoVacio.svelte';

describe('EstadoVacio', () => {
  it('es un status con título, detalle y testid', () => {
    const { getByRole } = render(EstadoVacio, {
      props: { titulo: 'Nada pendiente por ahora.', detalle: 'Cuando llegue un expediente aparecerá aquí.', prueba: 'vacio' },
    });
    const caja = getByRole('status');
    expect(caja).toHaveAttribute('data-testid', 'vacio');
    expect(caja).toHaveTextContent('Nada pendiente por ahora.');
    expect(caja).toHaveTextContent('Cuando llegue un expediente aparecerá aquí.');
  });

  it('pinta la acción que se le pasa como hijo', () => {
    const { getByRole } = render(EstadoVacio, {
      props: {
        titulo: 'Sin expedientes',
        children: createRawSnippet(() => ({ render: () => '<button type="button">Nueva solicitud</button>' })),
      },
    });
    expect(getByRole('button', { name: 'Nueva solicitud' })).toBeTruthy();
  });

  it('axe no encuentra infracciones', async () => {
    const { container } = render(EstadoVacio, { props: { titulo: 'Nada pendiente' } });
    const r = await axe.run(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
    });
    expect(r.violations.map((v) => v.id)).toEqual([]);
  });
});
