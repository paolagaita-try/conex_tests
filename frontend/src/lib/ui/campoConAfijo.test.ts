import { describe, expect, it } from 'vitest';
import { fireEvent, isInaccessible, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import type { ComponentProps } from 'svelte';
import CampoConAfijo from './CampoConAfijo.svelte';
import Entrada from './Entrada.svelte';
import { conValorEnlazado } from '$pruebas/valorEnlazado.svelte';
import { tecleado } from '$pruebas/tecleado';
import type { NumeroTecleado } from '$lib/ui/valores';

/**
 * Campo con prefijo o sufijo. Ejemplos del diseño: importe en $ con
 * tope de $2,000,000, porcentaje en %, duración en días.
 * Los números esperados se escriben a mano (separador de miles «,» y decimal «.», `es-US`).
 */
interface Montaje {
  valor?: NumeroTecleado | null;
  prefijo?: string;
  sufijo?: string;
  minimo?: number;
  maximo?: number;
  decimales?: number;
  ayuda?: string;
  error?: string | null;
  deshabilitado?: boolean;
  etiqueta?: string;
}

function montar(extra: Montaje = {}) {
  const { valor: inicial = null, ...resto } = extra;
  const enlace = conValorEnlazado(
    { id: 'monto', etiqueta: 'Anticipo solicitado', ...resto },
    inicial as NumeroTecleado | null | undefined,
  );
  const r = render(CampoConAfijo, { props: enlace.props });
  const campo = r.getByRole('textbox') as HTMLInputElement;
  return { ...r, campo, valor: enlace.valor };
}

async function escribir(r: ReturnType<typeof montar>, texto: string) {
  await fireEvent.input(r.campo, { target: { value: texto } });
  await fireEvent.blur(r.campo);
  await tick();
}

const MONTO = { prefijo: '$', minimo: 1000, maximo: 2_000_000 };

describe('fuera de rango o con decimales de más', () => {
  it('por encima del máximo: error asociado, campo inválido y sin valor', async () => {
    const r = montar(MONTO);
    await escribir(r, '2,350,000');
    const alerta = r.getByRole('alert');
    expect(alerta).toHaveTextContent('Supera el máximo de $2,000,000.');
    expect(r.campo.getAttribute('aria-describedby')).toContain(alerta.id);
    expect(r.campo).toHaveAttribute('aria-invalid', 'true');
    expect(r.valor()).toBeNull();
  });

  it('un error retira el valor válido que había: nunca queda un número anterior detrás de un error', async () => {
    const r = montar({ ...MONTO, valor: tecleado(850000) });
    await escribir(r, '2,350,000');
    expect(r.getByRole('alert')).toBeTruthy();
    expect(r.valor()).toBeNull();
  });

  it('por debajo del mínimo', async () => {
    const r = montar(MONTO);
    await escribir(r, '500');
    expect(r.getByRole('alert')).toHaveTextContent('El mínimo es $1,000.');
    expect(r.valor()).toBeNull();
  });

  it('con más decimales de los permitidos', async () => {
    const r = montar(MONTO);
    await escribir(r, '850000.555');
    expect(r.getByRole('alert')).toHaveTextContent('Usa como máximo 2 decimales.');
    expect(r.valor()).toBeNull();
  });

  it('un plazo en meses no admite decimales', async () => {
    const r = montar({ etiqueta: 'Plazo aprobado', sufijo: 'meses', decimales: 0 });
    await escribir(r, '48.5');
    expect(r.getByRole('alert')).toHaveTextContent('Escribe un número entero.');
  });

  it('un formato que no es número (incluido el separador europeo) se dice, no se adivina', async () => {
    const r = montar(MONTO);
    await escribir(r, '2.350.000');
    expect(r.getByRole('alert')).toHaveTextContent('Escribe solo números, con punto para los decimales.');
    await escribir(r, 'mil');
    expect(r.getByRole('alert')).toHaveTextContent('Escribe solo números, con punto para los decimales.');
    expect(r.valor()).toBeNull();
  });
});

describe('el valor es numérico y la unidad se anuncia una vez', () => {
  it('un monto válido con separador de miles se entrega como número y se muestra formateado', async () => {
    const r = montar(MONTO);
    await escribir(r, '850000');
    expect(r.valor()).toBe(850000);
    expect(r.campo.value).toBe('850,000');
    expect(r.queryByRole('alert')).toBeNull();
    await escribir(r, '1,250,000.5');
    expect(r.valor()).toBe(1250000.5);
    expect(r.campo.value).toBe('1,250,000.5');
  });

  it('un valor que llega de fuera se pinta formateado', () => {
    expect(montar({ ...MONTO, valor: tecleado(2_000_000) }).campo.value).toBe('2,000,000');
  });

  it('el afijo visible está oculto al lector y la unidad se anuncia una sola vez', () => {
    const r = montar(MONTO);
    expect(r.getByText('$', { selector: '.afijo' })).toHaveAttribute('aria-hidden', 'true');
    expect(r.campo).toHaveAccessibleName('Anticipo solicitado');
    expect(r.campo).toHaveAccessibleDescription('en $');
  });

  it('el texto de la unidad no queda suelto en el árbol de accesibilidad: solo viaja como descripción', () => {
    // Sin esto, un lector en modo lectura anunciaba «en $» dos veces: como descripción del campo
    // y como texto (hallazgo H1 de la verificación adversarial, pasada 1).
    const r = montar(MONTO);
    const unidad = r.container.querySelector(`#${r.campo.getAttribute('aria-describedby')?.split(' ')[0]}`) as HTMLElement;
    expect(unidad).toHaveTextContent('en $');
    expect(isInaccessible(unidad)).toBe(true);
    expect(r.campo).toHaveAccessibleDescription('en $');
  });

  it('con sufijo, igual: «%» una sola vez', () => {
    const r = montar({ etiqueta: 'Porcentaje de jornada', sufijo: '%' });
    expect(r.getByText('%', { selector: '.afijo' })).toHaveAttribute('aria-hidden', 'true');
    expect(r.campo).toHaveAccessibleDescription('en %');
  });

  it('el teclado del teléfono es el decimal', () => {
    expect(montar(MONTO).campo).toHaveAttribute('inputmode', 'decimal');
  });

  it('vaciarlo deja el valor vacío, sin error (lo obligatorio lo dice la pantalla)', async () => {
    const r = montar({ ...MONTO, valor: tecleado(850000) });
    await escribir(r, '');
    expect(r.valor()).toBeNull();
    expect(r.queryByRole('alert')).toBeNull();
  });
});

describe('estado deshabilitado', () => {
  it('no se puede escribir', () => {
    expect(montar({ ...MONTO, valor: tecleado(850000), deshabilitado: true }).campo).toBeDisabled();
  });
});

/**
 * Barrera de compilador: un número a secas no entra en un widget numérico, solo uno tecleado. Si
 * el valor de `CampoConAfijo` o de `Entrada` volviera a aceptar `number`, estas directivas quedarían sin usar y
 * `npm run check` fallaría.
 */
describe('barrera de compilador · un número calculado no entra en un widget', () => {
  it('ni en `CampoConAfijo` ni en `Entrada`', () => {
    const calculado = 2_000_000 / 2;
    // @ts-expect-error — el valor de `CampoConAfijo` es un número tecleado
    const conAfijo: ComponentProps<typeof CampoConAfijo> = { id: 'x', etiqueta: 'X', valor: calculado };
    // @ts-expect-error — y el de `Entrada`, también
    const entrada: ComponentProps<typeof Entrada> = { id: 'y', etiqueta: 'Y', valor: calculado };
    expect([conAfijo, entrada]).toBeDefined();
  });
});
