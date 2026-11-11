/**
 * El lanzador de aplicaciones: en TODA cabecera de sesión, un acceso al home de Bonita (`/bonita/`, el directorio
 * «Lista de aplicaciones»), como el icono de cuadrícula de las suites de oficina.
 */
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import axe from 'axe-core';
import CabeceraDeSesion from './CabeceraDeSesion.svelte';
import LanzadorDeApps from './LanzadorDeApps.svelte';

describe('LanzadorDeApps', () => {
  it('es un enlace con nombre accesible que lleva al home de Bonita', () => {
    const { getByRole } = render(LanzadorDeApps);
    const enlace = getByRole('link', { name: 'Todas mis aplicaciones' });
    expect(enlace.getAttribute('href')).toBe('/bonita/');
    expect(enlace.getAttribute('title')).toBe('Todas mis aplicaciones');
  });

  it('se abre en la ventana completa, no dentro del marco de la aplicación (las pantallas viven en un iframe)', () => {
    const { getByRole } = render(LanzadorDeApps);
    expect(getByRole('link', { name: 'Todas mis aplicaciones' }).getAttribute('target')).toBe('_top');
  });

  it('el icono es decorativo (el nombre lo da el enlace) y no pinta texto', () => {
    const { container } = render(LanzadorDeApps);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('aria-hidden')).toBe('true');
    expect(container.querySelectorAll('svg circle, svg rect').length).toBe(9);
  });

  it('axe no encuentra infracciones', async () => {
    const { container } = render(LanzadorDeApps);
    const r = await axe.run(container, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] }, rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } });
    expect(r.violations.map((v) => v.id)).toEqual([]);
  });
});

describe('la cabecera de las bandejas lleva el lanzador', () => {
  it('antes del nombre de la persona, dentro de la navegación de la sesión', () => {
    const { getByRole } = render(CabeceraDeSesion, { props: { marca: 'Empresa Demo', persona: 'Ana Analista' } });
    const sesion = getByRole('navigation', { name: 'Sesión' });
    const enlace = getByRole('link', { name: 'Todas mis aplicaciones' });
    expect(sesion.contains(enlace)).toBe(true);
    expect(sesion.firstElementChild).toBe(enlace);
  });
});
