import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { compile } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

/**
 * El área de trabajo única, custodiada sobre el **CSS compilado**
 * que viaja en el ZIP.
 *
 * Por qué sobre el CSS y no con `getComputedStyle`: jsdom no ejecuta las hojas de estilo del
 * componente, así que un mutante que devuelva el `70vh`, quite el `sticky` o el alto de ventana
 * sobrevive a la suite entera — por eso se mide aquí. La medición VISUAL
 * se hace en un navegador real; esta red es la del ciclo corto.
 */
function cssCompilado(ruta: string): string {
  const src = readFileSync(join(process.cwd(), ruta), 'utf8');
  return compile(src, { generate: 'client', css: 'external', filename: ruta }).css?.code ?? '';
}

/** La declaración `propiedad: valor` de la primera regla cuyo selector casa, sin comentarios. */
function declaracion(css: string, selector: RegExp, propiedad: string): string | null {
  const sinComentarios = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const regla = sinComentarios.match(new RegExp(`(^|\\n|})\\s*${selector.source}\\s*\\{([^}]*)\\}`));
  if (!regla) return null;
  const linea = regla[2]
    .split(';')
    .map((l) => l.trim())
    .find((l) => l.startsWith(`${propiedad}:`));
  return linea ? linea.slice(propiedad.length + 1).trim() : null;
}

const ACCIONES = cssCompilado('src/lib/ui/AccionesDeFormulario.svelte');
const MARCO = cssCompilado('src/lib/ui/MarcoDeFormulario.svelte');
const PANEL = cssCompilado('src/lib/ui/PanelDeDetalle.svelte');

describe('la barra que cierra el trabajo está siempre a la vista', () => {
  it('la barra de acciones es pegajosa al fondo del scroller', () => {
    // Medido: `accion-principal` nacía en top 1885 con un viewport de 800 (1280x800).
    expect(declaracion(ACCIONES, /\.barra\.svelte-[a-z0-9]+/, 'position')).toBe('sticky');
    expect(declaracion(ACCIONES, /\.barra\.svelte-[a-z0-9]+/, 'inset-block-end')).toBe('0');
  });

  it('la barra se despega del contenido que pasa por debajo (fondo y línea propios)', () => {
    expect(declaracion(ACCIONES, /\.barra\.svelte-[a-z0-9]+/, 'background')).toMatch(/--color-fondo/);
    expect(declaracion(ACCIONES, /\.barra\.svelte-[a-z0-9]+/, 'border-block-start')).toMatch(/--color-borde/);
  });

  it('el diálogo de confirmación NO es pegajoso: se lee junto a su consecuencia', () => {
    expect(declaracion(ACCIONES, /\.confirmacion\.svelte-[a-z0-9]+/, 'position')).toBeNull();
  });
});

describe('un solo scroller: el marco llena el área', () => {
  it('el marco cede su alto al contenedor en vez de imponer el suyo', () => {
    expect(declaracion(MARCO, /\.marco\.svelte-[a-z0-9]+/, 'flex')).toBe('1 1 auto');
    // Sin esto, el contenido del iframe le pone un suelo y el contenedor vuelve a desbordar.
    expect(declaracion(MARCO, /\.marco\.svelte-[a-z0-9]+/, 'min-block-size')).toBe('0');
  });

  it('el panel de detalle pasa el alto a su cuerpo, que es quien aloja el marco', () => {
    expect(declaracion(PANEL, /\.cuerpo\.svelte-[a-z0-9]+/, 'flex')).toBe('1 1 auto');
    expect(declaracion(PANEL, /\.cuerpo\.svelte-[a-z0-9]+/, 'min-block-size')).toBe('0');
    expect(declaracion(PANEL, /\.panel\.svelte-[a-z0-9]+/, 'min-block-size')).toBe('0');
  });
});

describe('embebida, la pantalla no repite la cabecera del contenedor', () => {
  const TOKENS = readFileSync(join(process.cwd(), 'src/lib/estilos/tokens.css'), 'utf8');

  it('todas las pantallas de tarea marcan el documento cuando van dentro de una bandeja', () => {
    // La clase que cierra: no es «las de hoy», es «las que haya». Una pantalla nueva que
    // olvide el import repetiría la cabecera dentro del marco y nadie se enteraría.
    // Las técnicas y la administración de parámetros no se abren dentro de una bandeja.
    const SIN_MARCO = ['_muestra', '_semilla', 'parametros'];
    const carpetas = readdirSync(join(process.cwd(), 'src/forms'), { withFileTypes: true }).filter((d) => d.isDirectory());
    expect(carpetas.map((d) => d.name), 'el barrido mide en el sitio equivocado').toContain('_semilla');
    const pantallas = carpetas
      .filter((d) => !SIN_MARCO.includes(d.name) && existsSync(join(process.cwd(), `src/forms/${d.name}/main.ts`)))
      .map((d) => d.name);
    const sinMarcar = pantallas.filter(
      (p) => !readFileSync(join(process.cwd(), `src/forms/${p}/main.ts`), 'utf8').includes('estilos/enMarco'),
    );
    expect(sinMarcar, 'estas pantallas repetirían su cabecera dentro de la bandeja').toEqual([]);
  });

  it('la cabecera propia se retira SOLO embebida, y el scroll se integra', () => {
    // El selector NO cuelga del padre. Si colgara —`main > header.cabecera`—,
    // lo que protege dependería de la GEOMETRÍA del marcado: una pantalla que envuelve en
    // `<div class="marco">` seguiría pintando su cabecera embebida.
    expect(declaracion(TOKENS, /\[data-en-marco\] header\.cabecera/, 'display')).toBe('none');
    // Ancho completo: tampoco repite la marca del proyecto, que ya pinta la bandeja que lo contiene.
    expect(declaracion(TOKENS, /\[data-en-marco\] header\.marca/, 'display')).toBe('none');
    expect(TOKENS).not.toMatch(/\[data-en-marco\] main > header\.cabecera/);
    expect(declaracion(TOKENS, /\[data-en-marco\]/, 'scrollbar-width')).toBe('thin');
    // Suelta no cambia nada: la regla cuelga del atributo, no del elemento.
    expect(TOKENS).not.toMatch(/\n\s*header\.cabecera\s*\{[^}]*display:\s*none/);
  });

  it('el marco no se lee como una caja dentro de la caja', () => {
    expect(declaracion(MARCO, /\.marco\.svelte-[a-z0-9]+/, 'border')).toBe('0');
    expect(declaracion(MARCO, /\.marco\.svelte-[a-z0-9]+/, 'border-radius')).toBeNull();
  });
});

describe('presupuesto vertical', () => {
  it('la cabecera de la app es UNA fila compacta', () => {
    const CABECERA = cssCompilado('src/lib/ui/CabeceraDeSesion.svelte');
    expect(declaracion(CABECERA, /\.cabecera\.svelte-[a-z0-9]+/, 'min-block-size')).toMatch(/--alto-cabecera/);
    expect(declaracion(CABECERA, /\.cabecera\.svelte-[a-z0-9]+/, 'display')).toBe('flex');
    // El título del detalle va en una línea con el volver y el subtítulo.
    expect(declaracion(PANEL, /\.subtitulo\.svelte-[a-z0-9]+/, 'margin')).toBe('0');
  });

  it('el panel no hereda el margen inferior del tema del portal (hueco bajo el marco)', () => {
    expect(declaracion(PANEL, /\.panel\.svelte-[a-z0-9]+/, 'margin')).toBe('0');
  });
});
