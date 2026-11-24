/** Pruebas de la vista del caso `frm_overview` con datos simulados. */
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import FrmOverview from './FrmOverview.svelte';
import { CASO_EJEMPLO, CONTEXTO_EJEMPLO } from '$lib/preventa/ejemplo';
import { infraccionesAxe } from '$pruebas/axe';

const cargar = async () => ({ caso: CASO_EJEMPLO, hubspot: CONTEXTO_EJEMPLO });

describe('vista del caso frm_overview', () => {
  it('pinta la línea de tiempo con el estado de cada hito', async () => {
    const { container } = render(FrmOverview, { props: { cargar } });
    await screen.findByText('Ticket creado en HubSpot');
    expect(screen.getByText('Viable: pasa a diseño')).toBeInTheDocument();
    expect(container.querySelector('[data-estado="actual"]')).toHaveTextContent('Diseño de la propuesta');
  });

  it('un caso no viable no muestra el diseño', async () => {
    render(FrmOverview, {
      props: { cargar: async () => ({ caso: { ...CASO_EJEMPLO, resultadoValidacion: 'no viable' }, hubspot: CONTEXTO_EJEMPLO }) },
    });
    expect(await screen.findByText('No viable: cerrado por viabilidad')).toBeInTheDocument();
    expect(screen.queryByText('Diseño de la propuesta')).toBeNull();
  });

  it('axe: sin infracciones de accesibilidad', async () => {
    const { container } = render(FrmOverview, { props: { cargar } });
    await screen.findByText('Ticket creado en HubSpot');
    expect(await infraccionesAxe(container)).toEqual([]);
  });
});
