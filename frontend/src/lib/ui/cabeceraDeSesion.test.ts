/**
 * La cabecera de la bandeja: la marca por token y la persona con «Salir» hacia el
 * servicio de cierre de sesión de la plataforma.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { EVENTO_MARCA } from '$lib/parametros/marca';
import axe from 'axe-core';
import CabeceraDeSesion from './CabeceraDeSesion.svelte';

describe('CabeceraDeSesion', () => {
  it('pinta la marca, la persona y, en su panel de cuenta, el enlace de salir a la plataforma', async () => {
    const { getByRole, getByText } = render(CabeceraDeSesion, {
      props: { marca: 'Empresa Demo', persona: 'Ana Analista', prueba: 'cabecera' },
    });
    expect(getByText('Empresa Demo')).toBeTruthy();
    expect(getByRole('navigation', { name: 'Sesión' })).toHaveTextContent('Ana Analista');
    await fireEvent.click(getByRole('button', { name: /cuenta de Ana Analista/i }));
    const salir = getByRole('link', { name: 'Salir' });
    expect(salir.getAttribute('href')).toBe('/bonita/logoutservice?redirect=true');
  });

  it('la marca y el rótulo de salir se pueden parametrizar; la marca nunca va incrustada', async () => {
    const { getByRole } = render(CabeceraDeSesion, {
      props: { persona: 'Ana', rotuloSalir: 'Cerrar sesión', urlSalir: '/bonita/logoutservice' },
    });
    await fireEvent.click(getByRole('button', { name: /cuenta de Ana/i }));
    expect(getByRole('link', { name: 'Cerrar sesión' }).getAttribute('href')).toBe('/bonita/logoutservice');
  });

  it('el nombre de la marca que llega del módulo DESPUÉS de montar se pinta (no se queda con el de antes)', async () => {
    document.documentElement.style.setProperty('--marca-nombre', "'Empresa Demo'");
    const { queryByText } = render(CabeceraDeSesion, { props: { persona: 'Ana' } });
    expect(queryByText('Empresa Demo')).toBeTruthy();
    document.documentElement.style.setProperty('--marca-nombre', "'Academia Norte'");
    document.dispatchEvent(new CustomEvent(EVENTO_MARCA));
    await waitFor(() => expect(queryByText('Academia Norte')).toBeTruthy());
    expect(queryByText('Empresa Demo')).toBeNull();
    document.documentElement.style.removeProperty('--marca-nombre');
  });

  it('axe no encuentra infracciones', async () => {
    const { container } = render(CabeceraDeSesion, { props: { marca: 'Empresa Demo', persona: 'Ana' } });
    const r = await axe.run(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
    });
    expect(r.violations.map((v) => v.id)).toEqual([]);
  });
});
