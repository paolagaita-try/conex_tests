/**
 * Los tres momentos de la bandeja son un `tablist` de verdad: roles, selección, teclado, y el
 * contador solo cuando hay algo que contar.
 */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import axe from 'axe-core';
import Pestanas, { type Pestana } from './Pestanas.svelte';
import { cuantos } from '$pruebas/recuento';

const MOMENTOS = [
  { id: 'por-hacer', rotulo: 'Por hacer', contador: cuantos(3) },
  { id: 'expedientes', rotulo: 'Expedientes', contador: cuantos(0) },
  { id: 'iniciar', rotulo: 'Iniciar' },
];

describe('Pestanas', () => {
  it('pinta un tablist con una pestaña seleccionada y el contador solo si es > 0', () => {
    const { getByRole, getAllByRole, queryByLabelText } = render(Pestanas, {
      props: { pestanas: MOMENTOS, activa: 'por-hacer', nombre: 'Momentos', prueba: 'momentos' },
    });
    expect(getByRole('tablist', { name: 'Momentos' })).toHaveAttribute('data-testid', 'momentos');
    const tabs = getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true');
    expect(tabs[1]).toHaveAttribute('aria-selected', 'false');
    expect(tabs[0]).toHaveTextContent('3');
    expect(queryByLabelText('0 pendientes')).toBeNull();
    // Solo la activa está en el orden de tabulación.
    expect(tabs[0]).toHaveAttribute('tabindex', '0');
    expect(tabs[2]).toHaveAttribute('tabindex', '-1');
  });

  it('al pulsar otra pestaña avisa con su id; al pulsar la activa, no', async () => {
    const onchange = vi.fn();
    const { getAllByRole } = render(Pestanas, { props: { pestanas: MOMENTOS, activa: 'por-hacer', onchange } });
    const tabs = getAllByRole('tab');
    await fireEvent.click(tabs[0]);
    expect(onchange).not.toHaveBeenCalled();
    await fireEvent.click(tabs[2]);
    expect(onchange).toHaveBeenCalledWith('iniciar');
  });

  it('las flechas recorren las pestañas en círculo y eligen', async () => {
    const onchange = vi.fn();
    const { getAllByRole } = render(Pestanas, { props: { pestanas: MOMENTOS, activa: 'por-hacer', onchange } });
    const tabs = getAllByRole('tab');
    await fireEvent.keyDown(tabs[0], { key: 'ArrowLeft' });
    expect(onchange).toHaveBeenLastCalledWith('iniciar');
    await fireEvent.keyDown(tabs[0], { key: 'End' });
    expect(onchange).toHaveBeenLastCalledWith('iniciar');
    await fireEvent.keyDown(tabs[0], { key: 'ArrowRight' });
    expect(onchange).toHaveBeenLastCalledWith('expedientes');
  });

  it('axe no encuentra infracciones', async () => {
    const { container } = render(Pestanas, { props: { pestanas: MOMENTOS, activa: 'por-hacer' } });
    const r = await axe.run(container, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
    });
    expect(r.violations.map((v) => v.id)).toEqual([]);
  });
});

/**
 * Barrera de compilador: el contador de una pestaña es un `Recuento`; un número a secas no compila.
 */
describe('barrera de compilador · el contador solo cuenta', () => {
  it('un número calculado no es un recuento', () => {
    const calculado = 2_000_000 / 2;
    // @ts-expect-error — el contador es un `Recuento`
    const pestana: Pestana = { id: 'a', rotulo: 'A', contador: calculado };
    expect(pestana).toBeDefined();
  });
});
