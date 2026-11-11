/**
 * El menú de cuenta: el avatar de Bonita de la persona de la sesión (o sus iniciales) junto a su nombre, y un panel con
 * su información y «Salir». Como la cuenta de las suites de oficina.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import axe from 'axe-core';
import CabeceraDeSesion from './CabeceraDeSesion.svelte';
import MenuDeCuenta from './MenuDeCuenta.svelte';

const base = { nombre: 'Ana Pérez', usuario: 'ana.perez', cargo: 'Responsable de personal' };
const abrir = async () => {
  await fireEvent.click(screen.getByRole('button', { name: /cuenta de Ana Pérez/i }));
};

describe('MenuDeCuenta', () => {
  it('cerrado: el nombre se ve y el panel no está', () => {
    const r = render(MenuDeCuenta, { props: base });
    const boton = r.getByRole('button', { name: /cuenta de Ana Pérez/i });
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    expect(boton).toHaveTextContent('Ana Pérez');
    expect(r.queryByRole('link', { name: 'Salir' })).toBeNull();
  });

  it('abierto: enseña nombre, usuario y cargo, y «Salir» hacia el cierre de sesión de la plataforma', async () => {
    const r = render(MenuDeCuenta, { props: base });
    await abrir();
    expect(r.getByRole('button', { name: /cuenta de Ana Pérez/i }).getAttribute('aria-expanded')).toBe('true');
    const panel = r.getByTestId('panel-de-cuenta');
    expect(panel).toHaveTextContent('ana.perez');
    expect(panel).toHaveTextContent('Responsable de personal');
    expect(r.getByRole('link', { name: 'Salir' }).getAttribute('href')).toBe('/bonita/logoutservice?redirect=true');
  });

  it('sin cargo no pinta una línea vacía', async () => {
    const r = render(MenuDeCuenta, { props: { nombre: 'Ana Pérez', usuario: 'ana.perez' } });
    await abrir();
    expect(r.queryByTestId('cargo-de-cuenta')).toBeNull();
  });

  it('Escape cierra el panel y devuelve el foco al botón', async () => {
    const r = render(MenuDeCuenta, { props: base });
    await abrir();
    await fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => expect(r.queryByTestId('panel-de-cuenta')).toBeNull());
    expect(document.activeElement).toBe(r.getByRole('button', { name: /cuenta de Ana Pérez/i }));
  });

  it('un clic fuera lo cierra', async () => {
    const r = render(MenuDeCuenta, { props: base });
    await abrir();
    await fireEvent.pointerDown(document.body);
    await waitFor(() => expect(r.queryByTestId('panel-de-cuenta')).toBeNull());
  });

  it('con la silueta por defecto de Bonita muestra las iniciales, no esa imagen', () => {
    const r = render(MenuDeCuenta, { props: { ...base, icono: 'icons/default/icon_user.png' } });
    expect(r.container.querySelector('img')).toBeNull();
    expect(r.getByTestId('avatar')).toHaveTextContent('AP');
  });

  it('con un avatar propio lo pide al tema de la aplicación (misma ruta que el portal)', () => {
    const r = render(MenuDeCuenta, { props: { ...base, icono: 'icons/12/avatar.png' } });
    expect(r.container.querySelector('img')?.getAttribute('src')).toBe('../theme/icons/12/avatar.png');
  });

  it('un avatar SUBIDO en Bonita (`../API/avatars/<n>`) se pide a la API de la plataforma, en absoluto', () => {
    const r = render(MenuDeCuenta, { props: { ...base, icono: '../API/avatars/1' } });
    expect(r.container.querySelector('img')?.getAttribute('src')).toBe('/bonita/API/avatars/1');
  });

  it('solo se acepta esa forma exacta de avatar subido', () => {
    for (const icono of ['../API/avatars/', '../API/avatars/x', '../API/avatars/1/../../x', '../API/avatars/1?a=b', '../API/otra/1', '/API/avatars/1']) {
      const r = render(MenuDeCuenta, { props: { ...base, icono } });
      expect(r.container.querySelector('img'), icono).toBeNull();
      r.unmount();
    }
  });

  it('si el avatar no carga, caen las iniciales', async () => {
    const r = render(MenuDeCuenta, { props: { ...base, icono: 'icons/12/avatar.png' } });
    await fireEvent.error(r.container.querySelector('img') as HTMLImageElement);
    await waitFor(() => expect(r.container.querySelector('img')).toBeNull());
    expect(r.getByTestId('avatar')).toHaveTextContent('AP');
  });

  it('una ruta de icono que intenta salir del tema se ignora', () => {
    for (const icono of ['../../x.png', 'https://otro.invalid/a.png', '//otro.invalid/a.png', 'javascript:alert(1)']) {
      const r = render(MenuDeCuenta, { props: { ...base, icono } });
      expect(r.container.querySelector('img'), icono).toBeNull();
      r.unmount();
    }
  });

  it('axe no encuentra infracciones, cerrado ni abierto', async () => {
    const r = render(MenuDeCuenta, { props: { ...base, icono: 'icons/default/icon_user.png' } });
    const opciones = { runOnly: { type: 'tag' as const, values: ['wcag2a', 'wcag2aa'] }, rules: { 'color-contrast': { enabled: false }, region: { enabled: false } } };
    expect((await axe.run(r.container, opciones)).violations.map((v) => v.id)).toEqual([]);
    await abrir();
    expect((await axe.run(r.container, opciones)).violations.map((v) => v.id)).toEqual([]);
  });
});

describe('la cabecera de las bandejas', () => {
  it('lleva el lanzador y el menú de cuenta, en ese orden, en la navegación de la sesión', () => {
    const r = render(CabeceraDeSesion, { props: { marca: 'Empresa Demo', persona: 'Ana Pérez', usuario: 'ana.perez' } });
    const sesion = r.getByRole('navigation', { name: 'Sesión' });
    expect(sesion.children[0]).toBe(r.getByRole('link', { name: 'Todas mis aplicaciones' }));
    expect(sesion.children[1]).toContainElement(r.getByRole('button', { name: /cuenta de Ana Pérez/i }));
  });
});
