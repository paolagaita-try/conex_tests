import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { compile } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

/**
 * Los widgets sobre su **CSS compilado** — la red del ciclo corto.
 *
 * jsdom no aplica las hojas de estilo del componente: un mutante que encoja una ficha a 40 px,
 * quite el anillo de foco o deshaga la hoja inferior sobrevive a la suite de comportamiento. Esto
 * lo caza en segundos; la medición REAL (cajas, `outline` computado, la hoja dentro de la ventana)
 * se hace en Chromium. Mismo instrumento que
 * `areaDeTrabajo.test.ts`. Necesario, no suficiente.
 *
 * La expectativa sale del sistema de diseño, no del componente: objetivo táctil `--objetivo-min`
 * (44 px), foco visible con `--color-foco`, y «no encoger un control por debajo de 44 px: se cambia
 * la composición (hoja inferior del calendario)».
 */
function cssCompilado(ruta: string): string {
  const src = readFileSync(join(process.cwd(), ruta), 'utf8');
  const css = compile(src, { generate: 'client', css: 'external', filename: ruta }).css?.code ?? '';
  return css.replace(/\/\*[\s\S]*?\*\//g, '');
}

/** El cuerpo del bloque que abre `cabecera` (llaves emparejadas), o `null`. */
function bloque(css: string, cabecera: RegExp): string | null {
  const m = cabecera.exec(css);
  if (!m) return null;
  let i = css.indexOf('{', m.index) + 1;
  const inicio = i;
  for (let nivel = 1; nivel > 0 && i < css.length; i++) {
    if (css[i] === '{') nivel++;
    else if (css[i] === '}') nivel--;
  }
  return css.slice(inicio, i - 1);
}

/** Las declaraciones de la primera regla (de nivel superior en `css`) cuyo selector casa. */
function regla(css: string, selector: RegExp): Record<string, string> | null {
  const m = new RegExp(`(?:^|[}\\s])${selector.source}\\s*\\{([^{}]*)\\}`).exec(css);
  if (!m) return null;
  return Object.fromEntries(
    m[1]
      .split(';')
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => [l.slice(0, l.indexOf(':')).trim(), l.slice(l.indexOf(':') + 1).trim()]),
  );
}

const S = '\\.svelte-[a-z0-9]+';

describe('Calendario', () => {
  const CSS = cssCompilado('src/lib/ui/Calendario.svelte');

  it('cada día y cada control de navegación ocupan un objetivo táctil de 44 px', () => {
    const td = regla(CSS, new RegExp(`td${S}`));
    expect(td?.['block-size']).toMatch(/--objetivo-min/);
    expect(td?.['min-inline-size']).toMatch(/--objetivo-min/);
    // Un descendiente compila como `button:where(.svelte-…)`.
    for (const sel of [`\\.abrir${S}`, `\\.mes${S} button:where\\(${S}\\)`]) {
      const r = regla(CSS, new RegExp(sel));
      expect(r?.['min-inline-size'], sel).toMatch(/--objetivo-min/);
      expect(r?.['min-block-size'], sel).toMatch(/--objetivo-min/);
    }
  });

  it('el día con foco, el botón y la navegación tienen anillo de foco visible', () => {
    expect(CSS).toMatch(new RegExp(`td${S}:focus-visible\\s*\\{[^}]*outline:[^;]*--color-foco`));
    expect(CSS).toMatch(new RegExp(`\\.abrir${S}:focus-visible`));
  });

  it('en el teléfono el diálogo es una hoja inferior a todo lo ancho', () => {
    const movil = bloque(CSS, /@media\s*\(max-width:\s*40rem\)/);
    expect(movil, 'falta el corte de teléfono').not.toBeNull();
    const hoja = regla(movil as string, new RegExp(`\\.calendario${S}`));
    expect(hoja?.position).toBe('fixed');
    expect(hoja?.['inset-block-end']).toBe('0');
    expect(hoja?.['inset-inline']).toBe('0');
    // La rejilla NO se estira al ancho de la hoja: con celdas de 51×44 los círculos salían óvalos
    // (medido en la galería desplegada a 390, 2026-10-03). Se centra con celdas cuadradas de 44.
    expect(regla(movil as string, new RegExp(`table${S}`))?.['margin-inline']).toBe('auto');
    expect(regla(movil as string, new RegExp(`table${S}`))?.['inline-size']).toBeUndefined();
  });

  it('los días son círculos, como en el diseño aprobado', () => {
    expect(regla(CSS, new RegExp(`td${S}`))?.['border-radius']).toMatch(/--radio-completo/);
  });

  it('un día deshabilitado no se distingue solo por color', () => {
    expect(regla(CSS, new RegExp(`td\\[aria-disabled='true'\\]${S}`))?.['text-decoration']).toBe(
      'line-through',
    );
  });
});

describe('OpcionesEnFicha', () => {
  const CSS = cssCompilado('src/lib/ui/OpcionesEnFicha.svelte');

  it('cada ficha mide al menos 44 px de alto y su límite es el de un control', () => {
    const ficha = regla(CSS, new RegExp(`\\.ficha${S}`));
    expect(ficha?.['min-block-size']).toMatch(/--objetivo-min/);
    expect(ficha?.border).toMatch(/--color-borde-control/);
  });

  it('en fila, las fichas se reparten el ancho', () => {
    expect(regla(CSS, new RegExp(`\\.fichas\\.en-fila${S}`))?.['grid-template-columns']).toMatch(/auto-fit/);
  });

  it('la ficha con foco tiene anillo visible', () => {
    expect(CSS).toMatch(new RegExp(`\\.ficha${S}:focus-visible\\s*\\{[^}]*outline:[^;]*--color-foco`));
  });
});

describe('Interruptor', () => {
  const CSS = cssCompilado('src/lib/ui/Interruptor.svelte');

  it('el botón ocupa un objetivo táctil de 44 px y tiene anillo de foco visible', () => {
    const boton = regla(CSS, new RegExp(`\\.interruptor${S}`));
    expect(boton?.['min-block-size']).toMatch(/--objetivo-min/);
    expect(boton?.['min-inline-size']).toMatch(/--objetivo-min/);
    expect(CSS).toMatch(new RegExp(`\\.interruptor${S}:focus-visible\\s*\\{[^}]*outline:[^;]*--color-foco`));
  });

  it('el límite de la pista es el de un control', () => {
    expect(regla(CSS, new RegExp(`\\.pista${S}`))?.border).toMatch(/--color-borde-control/);
  });
});

describe('CampoConAfijo', () => {
  const CSS = cssCompilado('src/lib/ui/CampoConAfijo.svelte');

  it('el CAMPO mide 44 px, su límite es el de un control y el foco se ve en el grupo', () => {
    // Medido en Chromium : con el mínimo en el grupo, su borde se
    // comía 2 px y el input medía 42. El objetivo táctil es el campo, no su marco.
    expect(regla(CSS, new RegExp(`input${S}`))?.['min-block-size']).toMatch(/--objetivo-min/);
    const grupo = regla(CSS, new RegExp(`\\.grupo${S}`));
    expect(grupo?.border).toMatch(/--color-borde-control/);
    expect(CSS).toMatch(new RegExp(`\\.grupo${S}:focus-within\\s*\\{[^}]*outline:[^;]*--color-foco`));
  });
});

describe('Autocompletar', () => {
  const CSS = cssCompilado('src/lib/ui/Autocompletar.svelte');

  it('el campo y cada opción ocupan un objetivo táctil de 44 px', () => {
    expect(regla(CSS, new RegExp(`input${S}`))?.['min-height']).toMatch(/--objetivo-min/);
    expect(regla(CSS, new RegExp(`li${S}`))?.['min-block-size']).toMatch(/--objetivo-min/);
  });

  it('el campo tiene anillo de foco y su límite es el de un control', () => {
    expect(CSS).toMatch(new RegExp(`input${S}:focus-visible\\s*\\{[^}]*outline:[^;]*--color-foco`));
    expect(regla(CSS, new RegExp(`input${S}`))?.border).toMatch(/--color-borde-control/);
  });

  it('la opción activa no se distingue solo por color', () => {
    expect(regla(CSS, new RegExp(`li\\.activa${S}`))?.['box-shadow']).toMatch(/inset/);
  });
});
