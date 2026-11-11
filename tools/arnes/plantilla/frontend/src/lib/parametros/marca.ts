/**
 * La marca `[PARAM]` del proyecto (nombre, logo y colores) como parámetros del módulo, aplicada en ejecución.
 *
 * ## Qué hace
 *
 * Al cargar la pantalla lee los siete parámetros `marca_*` de `GET extension/parametros/valores` y los
 * copia como custom properties a `:root` (`--marca-nombre`, `--marca-logo`, `--color-primario`,
 * `--color-primario-fuerte`, `--color-primario-suave`, `--color-acento`, `--color-superficie`). Cambiar la
 * marca no recompila nada: es un valor del módulo. Los tokens por defecto de `tokens.css` siguen siendo el
 * fallback.
 *
 * ## Si la lectura falla o no hay valor
 *
 * La pantalla se queda con los tokens por defecto: sin error visible y sin pantalla en blanco. Cada
 * parámetro se lee y se aplica por separado; uno que falla no arrastra a los demás.
 *
 * ## Por qué se vuelve a validar aquí
 *
 * El servidor ya rechazó al guardar todo lo que no es un color hexadecimal o una imagen en `data:` URI.
 * Aun así, el valor llega al CSS: se vuelve a comprobar su FORMA antes de aplicarlo (dos barreras, no
 * una), y un valor que no la cumpla se ignora en silencio. Nada de lo que llegue puede cerrar una
 * comilla ni abrir una regla.
 *
 * ## Lectura sin tarea
 *
 * Las bandejas no tienen una tarea abierta, así que la lectura va sin `tarea`: el servidor responde, en
 * ese caso, solo con definiciones de visibilidad CLIENTE y ámbito global. Por eso las siete definiciones
 * son CLIENTE: ninguna otra definición se puede leer así.
 */

import { leerValores, type LectorDeValores } from './opciones';

/** El evento que emite `document` cuando la marca ya está aplicada (para quien la pintó antes de tiempo). */
export const EVENTO_MARCA = 'marca-aplicada';

/** Tope del logo, en caracteres del `data:` URI (el servidor aplica el mismo, ~100 KB). */
export const MAXIMO_LOGO = 102_400;

const HEX = /^#[0-9a-fA-F]{6}$/;
const LOGO = /^data:image\/(png|svg\+xml);base64,[A-Za-z0-9+/]+={0,2}$/;

/** Cada parámetro de la marca, la custom property que alimenta y cómo se vuelve CSS válido. */
export const PARAMETROS_DE_MARCA = [
  { codigo: 'marca_nombre', propiedad: '--marca-nombre', css: nombreComoCss },
  { codigo: 'marca_logo', propiedad: '--marca-logo', css: logoComoCss },
  { codigo: 'marca_color_primario', propiedad: '--color-primario', css: colorComoCss },
  { codigo: 'marca_color_primario_fuerte', propiedad: '--color-primario-fuerte', css: colorComoCss },
  { codigo: 'marca_color_primario_suave', propiedad: '--color-primario-suave', css: colorComoCss },
  { codigo: 'marca_color_acento', propiedad: '--color-acento', css: colorComoCss },
  { codigo: 'marca_color_superficie', propiedad: '--color-superficie', css: colorComoCss },
] as const;

function colorComoCss(valor: string): string | undefined {
  return HEX.test(valor) ? valor.toLowerCase() : undefined;
}

function logoComoCss(valor: string): string | undefined {
  if (valor === 'none') return 'none';
  return valor.length <= MAXIMO_LOGO && LOGO.test(valor) ? `url("${valor}")` : undefined;
}

function nombreComoCss(valor: string): string | undefined {
  const n = valor.trim();
  // eslint-disable-next-line no-control-regex
  if (!n || n.length > 60 || /['"\\\u0000-\u001f]/.test(n)) return undefined;
  return `'${n}'`;
}

const NEGRO: [number, number, number] = [0, 0, 0];
const BLANCO: [number, number, number] = [255, 255, 255];

/** Mezcla un `#rrggbb` con un color: `peso` es cuánto del otro color entra (0 = el original, 1 = el otro). */
function mezclado(hex: string, con: [number, number, number], peso: number): string {
  const canal = (i: number): string =>
    Math.round(parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16) * (1 - peso) + con[i] * peso)
      .toString(16)
      .padStart(2, '0');
  return `#${canal(0)}${canal(1)}${canal(2)}`;
}

/**
 * Lo que sale del color primario cuando el proyecto no fija el suyo. Así cambiar UN color de marca basta: sin esto, el
 * fuerte (enlaces, etiquetas), el suave (fondos) y el acento se quedaban en el morado de fábrica y la pantalla salía
 * mitad azul, mitad morada. El fuerte va más oscuro que el primario, así que lo que ya cumple 4.5:1 sobre blanco lo
 * sigue cumpliendo (y sobre el suave, que es un velo del primario).
 */
const DERIVADOS_DEL_PRIMARIO: ReadonlyArray<{ propiedad: string; de: (primario: string) => string }> = [
  { propiedad: '--color-foco', de: (p) => p },
  { propiedad: '--color-primario-fuerte', de: (p) => mezclado(p, NEGRO, 0.25) },
  { propiedad: '--color-primario-suave', de: (p) => mezclado(p, BLANCO, 0.9) },
  { propiedad: '--color-acento', de: (p) => mezclado(p, BLANCO, 0.35) },
];

/** El valor CSS de un parámetro de la marca, o `undefined` si no hay valor o no tiene la forma esperada. */
export function valorCss(codigo: string, valor: string | null | undefined): string | undefined {
  const p = PARAMETROS_DE_MARCA.find((x) => x.codigo === codigo);
  if (!p || typeof valor !== 'string' || valor === '') return undefined;
  return p.css(valor);
}

/**
 * Lee los siete parámetros y aplica a `raiz` los que llegan bien. Nunca lanza: devuelve las custom
 * properties que SÍ aplicó (para quien quiera comprobarlo).
 */
export async function cargarMarca(
  lector: LectorDeValores = leerValores,
  raiz: HTMLElement | undefined = typeof document === 'undefined' ? undefined : document.documentElement,
): Promise<Record<string, string>> {
  const aplicadas: Record<string, string> = {};
  if (raiz === undefined) return aplicadas;
  await Promise.all(
    PARAMETROS_DE_MARCA.map(async ({ codigo, propiedad }) => {
      try {
        const leido = await lector({ definicion: codigo });
        const css = leido.clase === 'PARAMETRO' ? valorCss(codigo, leido.valor) : undefined;
        if (css !== undefined) {
          raiz.style.setProperty(propiedad, css);
          aplicadas[propiedad] = css;
        }
      } catch {
        // Sin valor o sin lectura: se queda el token por defecto de tokens.css.
      }
    }),
  );
  // El anillo de foco no es un parámetro: sigue siempre al primario. El resto se deriva solo si el proyecto no lo fijó.
  const primario = aplicadas['--color-primario'];
  if (primario !== undefined) {
    for (const { propiedad, de } of DERIVADOS_DEL_PRIMARIO) {
      if (propiedad in aplicadas) continue;
      const derivado = de(primario);
      raiz.style.setProperty(propiedad, derivado);
      aplicadas[propiedad] = derivado;
    }
  }
  if (typeof document !== 'undefined') document.dispatchEvent(new CustomEvent(EVENTO_MARCA));
  return aplicadas;
}
