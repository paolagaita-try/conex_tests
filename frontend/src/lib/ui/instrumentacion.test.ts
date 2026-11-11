import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import CamposDeContrato from './CamposDeContrato.svelte';
import AccionesDeFormulario from './AccionesDeFormulario.svelte';

import { CAPTURA, CONTRATOS, DECISION, RAMAS, type CampoDeContrato } from '$pruebas/contratosDeEjemplo';
import type { ValoresDelFormulario } from '$lib/ui/valores';

/**
 * La interfaz declarada entre el producto y sus pruebas.
 *
 * El `data-testid` **se deriva del contrato**, no se inventa por pantalla: un campo nuevo en
 * el contrato trae su testid sin que nadie decida nada, y un custodio puede cruzarlos.
 * Por eso se prueba contra contratos con la forma de los generados (`$pruebas/contratosDeEjemplo`).
 *
 * Se verifica sobre el **DOM renderizado** —el atributo tiene que estar en el control que la
 * automatización va a tocar—, no sobre las props que el componente recibe: una prop que llega
 * y no se pinta deja la suite anclada a nada.
 */

type Campo = CampoDeContrato;

/** Todo elegido: fuerza a que los campos condicionales se pinten (si no, no se miden). */
function todoElegido(campos: readonly Campo[]): ValoresDelFormulario {
  const valores: ValoresDelFormulario = {};
  for (const campo of campos) {
    const conjunto = campo.constraint.match(/∈\s*\{([^}]+)\}/);
    if (conjunto) valores[campo.ruta] = conjunto[1].split(',')[0].trim();
    else if (campo.tipo === 'BOOLEAN') valores[campo.ruta] = true;
  }
  return valores;
}

/** El testid que el contrato dicta para un campo. La regla, en un solo sitio. */
function testidDe(ruta: string): string {
  return `campo-${ruta.replace(/\./g, '-')}`;
}

describe('Instrumentación · los campos la heredan del contrato', () => {
  it('pone en cada control el testid que dicta la ruta del contrato', () => {
    const campos = DECISION;
    const { container } = render(CamposDeContrato, {
      props: { campos, valores: todoElegido(campos), ramas: RAMAS, producto: 'anual' },
    });

    const pintado = [...container.querySelectorAll('[data-testid]')].map((e) =>
      e.getAttribute('data-testid'),
    );
    expect(pintado).toContain(testidDe('decision.resultado'));
    expect(pintado).toContain(testidDe('decision.justificacion'));
  });

  it('no deja ningún campo pintado sin su testid, en ninguna pantalla', () => {
    const huerfanos: string[] = [];

    for (const [pantalla, campos] of Object.entries(CONTRATOS)) {
      const { container } = render(CamposDeContrato, {
        props: { campos, valores: todoElegido(campos as readonly Campo[]) },
      });
      // El universo son los controles que la persona toca, sacados del DOM renderizado.
      for (const control of container.querySelectorAll('input, select, textarea')) {
        const id = control.getAttribute('id');
        if (!id) continue;
        if (!control.getAttribute('data-testid')) huerfanos.push(`${pantalla}: ${id}`);
      }
    }

    expect(huerfanos).toEqual([]);
  });

  it('el testid sale de la ruta del contrato, no del id ni del orden', () => {
    // Dos grupos distintos con el mismo nombre de campo no pueden colisionar: la ruta los
    // separa. Es el contrato de captura, que tiene `solicitud.comentario` y `conformidad.comentario`.
    const campos = CAPTURA;
    const { container } = render(CamposDeContrato, {
      props: { campos, valores: todoElegido(campos) },
    });

    const pintados = [...container.querySelectorAll('input, select, textarea')]
      .map((c) => c.getAttribute('data-testid'))
      .filter((t): t is string => t !== null);

    // Sin esto el test pasaría en vacío: sin un solo testid, el bucle de abajo no itera y la
    // ausencia total se leería como conformidad.
    expect(pintados.length).toBe(
      container.querySelectorAll('input, select, textarea').length,
    );
    // Y no se repiten: dos campos de grupos distintos con el mismo nombre son dos testids.
    expect(new Set(pintados).size).toBe(pintados.length);

    for (const testid of pintados) {
      const ruta = testid.replace(/^campo-/, '').replace(/-/g, '.');
      expect(campos.some((c) => c.ruta === ruta)).toBe(true);
    }
  });
});

describe('Instrumentación · las acciones y la confirmación de lo grave', () => {
  it('nombra la acción principal y la secundaria', () => {
    const { container } = render(AccionesDeFormulario, {
      props: { principal: 'Enviar dictamen', secundaria: { etiqueta: 'Guardar' } },
    });

    expect(container.querySelector('[data-testid="accion-principal"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="accion-secundaria"]')).not.toBeNull();
  });

  it('nombra el panel de confirmación y sus dos salidas cuando lo grave se confirma', () => {
    const { container } = render(AccionesDeFormulario, {
      props: {
        principal: 'Enviar dictamen',
        confirmacionPendiente: true,
        graveExterno: { etiqueta: 'Rechazar', consecuencia: 'La solicitud se cierra.' },
      },
    });

    expect(container.querySelector('[data-testid="confirmacion"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="confirmacion-aceptar"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="confirmacion-cancelar"]')).not.toBeNull();
  });

  it('no pinta el panel de confirmación mientras no hay nada grave que confirmar', () => {
    const { container } = render(AccionesDeFormulario, {
      props: { principal: 'Enviar dictamen', secundaria: { etiqueta: 'Guardar' } },
    });

    expect(container.querySelector('[data-testid="confirmacion"]')).toBeNull();
  });
});
