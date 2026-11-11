import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import Interruptor from './Interruptor.svelte';
import { conValorEnlazado } from '$pruebas/valorEnlazado.svelte';

/**
 * Interruptor — patrón «Switch» de WAI-ARIA APG. El ejemplo es el del
 * diseño aprobado: «Persona ya registrada».
 *
 * Espacio es la activación NATIVA del botón: jsdom no la implementa, así que aquí se
 * prueba el clic y Espacio se mide en Chromium.
 */
function montar(extra: { valor?: boolean | null; error?: string | null; deshabilitado?: boolean } = {}) {
  const { valor: inicial = null, ...resto } = extra;
  const enlace = conValorEnlazado(
    { id: 'existente', etiqueta: 'Persona ya registrada', ...resto },
    inicial as boolean | null | undefined,
  );
  const r = render(Interruptor, { props: enlace.props });
  return { ...r, interruptor: r.getByRole('switch'), valor: enlace.valor };
}

describe('el interruptor dice qué activa', () => {
  it('es un switch nombrado con lo que activa, no con «sí» ni «no»', () => {
    const r = montar({ valor: true });
    expect(r.interruptor).toHaveAccessibleName('Persona ya registrada');
    expect(r.interruptor.tagName).toBe('BUTTON');
    expect(r.interruptor).toHaveAttribute('type', 'button');
  });

  it('expone su estado con aria-checked, coherente con el valor', () => {
    expect(montar({ valor: true }).interruptor).toHaveAttribute('aria-checked', 'true');
  });

  it('sin valor, está apagado', () => {
    expect(montar().interruptor).toHaveAttribute('aria-checked', 'false');
  });

  it('un clic lo conmuta en los dos sentidos y entrega un booleano', async () => {
    const r = montar({ valor: false });
    await fireEvent.click(r.interruptor);
    expect(r.valor()).toBe(true);
    expect(r.interruptor).toHaveAttribute('aria-checked', 'true');
    await fireEvent.click(r.interruptor);
    expect(r.valor()).toBe(false);
    expect(r.interruptor).toHaveAttribute('aria-checked', 'false');
  });

  it('el estado se ve también como texto, oculto al lector para no duplicar aria-checked', () => {
    const r = montar({ valor: true });
    const visible = r.getByText('Sí');
    expect(visible.closest('[aria-hidden="true"]')).not.toBeNull();
  });
});

describe('deshabilitado y error', () => {
  it('deshabilitado: no conmuta y se expone deshabilitado', async () => {
    const r = montar({ valor: true, deshabilitado: true });
    expect(r.interruptor).toBeDisabled();
    await fireEvent.click(r.interruptor);
    expect(r.valor()).toBe(true);
  });

  it('con error: inválido y con el error asociado', () => {
    const r = montar({ error: 'Indica si es cliente del proyecto.' });
    const alerta = r.getByRole('alert');
    expect(r.interruptor).toHaveAttribute('aria-invalid', 'true');
    expect(r.interruptor.getAttribute('aria-describedby')).toContain(alerta.id);
  });
});
