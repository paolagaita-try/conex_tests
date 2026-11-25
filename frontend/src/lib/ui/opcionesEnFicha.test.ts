import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import OpcionesEnFicha from './OpcionesEnFicha.svelte';
import { conValorEnlazado } from '$pruebas/valorEnlazado.svelte';

/**
 * Opciones en ficha — patrón «Radio Group» de WAI-ARIA APG. Las opciones
 * son las del modo de disfrute de un permiso.
 *
 * El tamaño de 44 px y el foco VISIBLE no los ve jsdom: los vigila el CSS compilado
 * (`estilosDeWidgets.test.ts`) y se miden en Chromium.
 */
const VIAS = [
  { valor: 'continuo', etiqueta: 'Días seguidos', detalle: 'Todo el permiso de una vez' },
  { valor: 'partido', etiqueta: 'En dos tramos', detalle: 'Se reparte en dos periodos' },
  { valor: 'horas', etiqueta: 'Por horas', detalle: 'Solo hasta 40 horas' },
];

function montar(extra: { valor?: string | null; error?: string | null; obligatorio?: boolean; deshabilitado?: boolean; disposicion?: 'columna' | 'fila' } = {}) {
  const { valor: inicial = null, ...resto } = extra;
  const enlace = conValorEnlazado(
    { id: 'via', etiqueta: 'Modo de disfrute', opciones: VIAS, ...resto },
    inicial as string | null | undefined,
  );
  const r = render(OpcionesEnFicha, { props: enlace.props });
  const ficha = (nombre: string) => r.getByRole('radio', { name: nombre });
  return { ...r, ficha, valor: enlace.valor };
}

const enFoco = () => document.activeElement as HTMLElement;

async function pulsar(tecla: string) {
  await fireEvent.keyDown(enFoco(), { key: tecla });
  await tick();
}

describe('un grupo de radio con nombre', () => {
  it('el grupo se nombra con la etiqueta del campo y cada ficha con la suya', () => {
    const r = montar();
    expect(r.getByRole('radiogroup', { name: 'Modo de disfrute' })).toBeTruthy();
    expect(r.getAllByRole('radio')).toHaveLength(3);
  });

  it('el detalle de cada opción es su descripción, no parte del nombre', () => {
    const r = montar();
    expect(r.ficha('En dos tramos')).toHaveAccessibleDescription('Se reparte en dos periodos');
  });

  it('sin valor, ninguna está marcada y solo la primera está en el orden de tabulación', () => {
    const r = montar();
    const radios = r.getAllByRole('radio');
    expect(radios.map((x) => x.getAttribute('aria-checked'))).toEqual(['false', 'false', 'false']);
    expect(radios.map((x) => x.getAttribute('tabindex'))).toEqual(['0', '-1', '-1']);
  });

  it('con valor, la elegida es la única marcada y la única en el orden de tabulación', () => {
    const r = montar({ valor: 'partido' });
    const radios = r.getAllByRole('radio');
    expect(radios.map((x) => x.getAttribute('aria-checked'))).toEqual(['false', 'true', 'false']);
    expect(radios.map((x) => x.getAttribute('tabindex'))).toEqual(['-1', '0', '-1']);
  });
});

describe('se elige con el clic, las flechas y Espacio', () => {
  it('un clic elige la ficha, la marca y la deja con el foco', async () => {
    const r = montar();
    await fireEvent.click(r.ficha('En dos tramos'));
    expect(r.valor()).toBe('partido');
    expect(r.ficha('En dos tramos')).toHaveAttribute('aria-checked', 'true');
    expect(enFoco()).toBe(r.ficha('En dos tramos'));
  });

  it('las flechas mueven el foco y la elección, y dan la vuelta', async () => {
    const r = montar({ valor: 'continuo' });
    r.ficha('Días seguidos').focus();
    await pulsar('ArrowRight');
    expect(enFoco()).toBe(r.ficha('En dos tramos'));
    expect(r.valor()).toBe('partido');
    await pulsar('ArrowDown');
    expect(r.valor()).toBe('horas');
    await pulsar('ArrowRight');
    expect(r.valor()).toBe('continuo');
    await pulsar('ArrowLeft');
    expect(enFoco()).toBe(r.ficha('Por horas'));
    expect(r.valor()).toBe('horas');
    await pulsar('ArrowUp');
    expect(r.valor()).toBe('partido');
  });

  it('Espacio elige la ficha con foco cuando aún no hay ninguna', async () => {
    const r = montar();
    r.ficha('Días seguidos').focus();
    await pulsar(' ');
    expect(r.valor()).toBe('continuo');
  });

  it('solo una queda marcada tras varias elecciones', async () => {
    const r = montar();
    await fireEvent.click(r.ficha('En dos tramos'));
    await fireEvent.click(r.ficha('Por horas'));
    expect(r.getAllByRole('radio').filter((x) => x.getAttribute('aria-checked') === 'true')).toHaveLength(1);
  });
});

describe('disposición (diseño aprobado: «Producto» con sus opciones en fila)', () => {
  it('por defecto apila; en fila lo declara el grupo', () => {
    expect(montar().getByRole('radiogroup')).toHaveAttribute('data-disposicion', 'columna');
    expect(montar({ disposicion: 'fila' }).getAllByRole('radiogroup')[1]).toHaveAttribute('data-disposicion', 'fila');
  });
});

describe('error y deshabilitado', () => {
  it('obligatoria sin elegir: el grupo es inválido y el error se asocia al grupo y se anuncia', () => {
    const r = montar({ obligatorio: true, error: 'Elige una vía para continuar.' });
    const grupo = r.getByRole('radiogroup');
    const alerta = r.getByRole('alert');
    expect(alerta).toHaveTextContent('Elige una vía para continuar.');
    expect(grupo).toHaveAttribute('aria-invalid', 'true');
    expect(grupo).toHaveAttribute('aria-required', 'true');
    expect(grupo.getAttribute('aria-describedby')).toContain(alerta.id);
  });

  it('deshabilitado: no se elige, nada está en el orden de tabulación y se expone deshabilitado', async () => {
    const r = montar({ valor: 'partido', deshabilitado: true });
    await fireEvent.click(r.ficha('Por horas'));
    expect(r.valor()).toBe('partido');
    const radios = r.getAllByRole('radio');
    expect(radios.every((x) => x.getAttribute('tabindex') === '-1')).toBe(true);
    expect(radios.every((x) => x.getAttribute('aria-disabled') === 'true')).toBe(true);
  });
});
