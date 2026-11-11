/**
 * El panel de detalle: una sección con nombre accesible, el contenido que le pasa la bandeja y,
 * si se le da `onvolver`, el botón de volver (móvil).
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import axe from 'axe-core';
import PanelDeDetalle from './PanelDeDetalle.svelte';

const cuerpo = () => createRawSnippet(() => ({ render: () => '<p>Contenido del expediente</p>' }));

describe('PanelDeDetalle', () => {
  it('es una sección nombrada por su título, con subtítulo y contenido', () => {
    const { getByRole } = render(PanelDeDetalle, {
      props: { titulo: 'Revisar la solicitud', subtitulo: 'Solicitud 2026-000123 · zona gris', children: cuerpo(), prueba: 'detalle' },
    });
    const seccion = getByRole('region', { name: 'Revisar la solicitud' });
    expect(seccion).toHaveAttribute('data-testid', 'detalle');
    expect(seccion).toHaveTextContent('Solicitud 2026-000123 · zona gris');
    expect(seccion).toHaveTextContent('Contenido del expediente');
  });

  it('sin onvolver no hay botón de volver; con él, se pinta con su rótulo y avisa', async () => {
    const sin = render(PanelDeDetalle, { props: { titulo: 'T', children: cuerpo() } });
    expect(sin.queryByRole('button')).toBeNull();
    sin.unmount();

    const onvolver = vi.fn();
    const { getByRole } = render(PanelDeDetalle, {
      props: { titulo: 'T', children: cuerpo(), onvolver, rotuloVolver: 'Por hacer' },
    });
    const volver = getByRole('button', { name: /Por hacer/ });
    await fireEvent.click(volver);
    expect(onvolver).toHaveBeenCalledTimes(1);
  });

  it('axe no encuentra infracciones', async () => {
    const { container } = render(PanelDeDetalle, { props: { titulo: 'T', children: cuerpo(), onvolver: () => {} } });
    const r = await axe.run(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
    });
    expect(r.violations.map((v) => v.id)).toEqual([]);
  });
});
