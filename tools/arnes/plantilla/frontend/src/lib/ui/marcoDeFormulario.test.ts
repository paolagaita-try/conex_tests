/**
 * El marco: un iframe con título por la dirección corta del motor, que entrega el mensaje del
 * protocolo mientras está montado y deja de hacerlo al desmontarse.
 */
import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import MarcoDeFormulario from './MarcoDeFormulario.svelte';
import { urlDelFormularioDeTarea } from '$lib/bonita/marco';
import { estaEnMarcoDeBonita } from '$lib/bonita/config';

function llega(data: unknown, origin = window.location.origin): void {
  window.dispatchEvent(new MessageEvent('message', { data, origin }));
}

describe('MarcoDeFormulario', () => {
  it('pinta el iframe con su título, la dirección corta y el testid', () => {
    const { getByTitle } = render(MarcoDeFormulario, {
      props: { src: urlDelFormularioDeTarea('233'), titulo: 'Revisar la solicitud', prueba: 'marco' },
    });
    const marco = getByTitle('Revisar la solicitud') as HTMLIFrameElement;
    expect(marco.tagName).toBe('IFRAME');
    expect(marco.getAttribute('src')).toBe('/bonita/portal/form/taskInstance/233');
    expect(marco).toHaveAttribute('data-testid', 'marco');
  });

  /**
   * El contrato con `estaEnMarcoDeBonita()`: decide «estoy embebida» mirando que
   * `window.frameElement.id` empiece por `bonitaframe`, y de eso cuelga que la pantalla emita el
   * protocolo. Medido en el runtime 2025.2-u0 (2026-09-22): sin ese id, la tarea salía `completed`
   * y la bandeja no se enteraba. Se comprueba con la función real, no con una copia de su regla.
   */
  it('su iframe lleva un id que estaEnMarcoDeBonita() reconoce: sin él la pantalla no emitiría', () => {
    const { getByTitle } = render(MarcoDeFormulario, {
      props: { src: urlDelFormularioDeTarea('233'), titulo: 'T' },
    });
    const marco = getByTitle('T') as HTMLIFrameElement;
    expect(marco.id.startsWith('bonitaframe')).toBe(true);
    Object.defineProperty(window, 'frameElement', { value: marco, configurable: true });
    try {
      expect(estaEnMarcoDeBonita()).toBe(true);
    } finally {
      Object.defineProperty(window, 'frameElement', { value: null, configurable: true });
    }
  });

  it('entrega a la bandeja solo los mensajes válidos del propio origen, y deja de escuchar al desmontar', () => {
    const onmensaje = vi.fn();
    const { unmount } = render(MarcoDeFormulario, {
      props: { src: urlDelFormularioDeTarea('233'), titulo: 'T', onmensaje },
    });
    llega(JSON.stringify({ action: 'Submit task', message: 'success', taskId: '233' }));
    llega({ action: 'Submit task', message: 'success', taskId: '233' }, 'https://otro.example');
    llega({ action: 'Nada', message: 'success' });
    expect(onmensaje).toHaveBeenCalledTimes(1);
    expect(onmensaje).toHaveBeenCalledWith({ action: 'Submit task', message: 'success', taskId: '233' });

    unmount();
    llega({ action: 'Submit task', message: 'success', taskId: '233' });
    expect(onmensaje).toHaveBeenCalledTimes(1);
  });
});
