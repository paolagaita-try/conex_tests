import { afterEach, describe, expect, it, vi } from 'vitest';
import { cargarMarca, EVENTO_MARCA, MAXIMO_LOGO, PARAMETROS_DE_MARCA, valorCss } from './marca';
import { LecturaFallida, rutaDeValores, type LectorDeValores } from './opciones';

const PNG = 'data:image/png;base64,iVBORw0KGgo=';

function lectorCon(valores: Record<string, string | null>): LectorDeValores {
  return async ({ definicion }) => {
    if (!(definicion in valores)) throw new LecturaFallida('no-disponible', definicion);
    return { clase: 'PARAMETRO', valor: valores[definicion] };
  };
}

afterEach(() => {
  document.documentElement.removeAttribute('style');
});

describe('valorCss: solo pasa lo que tiene la forma esperada', () => {
  it('acepta un color #rrggbb (y lo baja a minúsculas), un logo data: o «none», y un nombre', () => {
    expect(valorCss('marca_color_primario', '#6B21A8')).toBe('#6b21a8');
    expect(valorCss('marca_logo', PNG)).toBe(`url("${PNG}")`);
    expect(valorCss('marca_logo', 'none')).toBe('none');
    expect(valorCss('marca_nombre', ' Empresa Ejemplo ')).toBe("'Empresa Ejemplo'");
  });

  it.each([
    ['marca_color_acento', 'red'],
    ['marca_color_acento', '#fff'],
    ['marca_color_acento', '#a855f7; background: url(x)'],
    ['marca_logo', 'https://ejemplo.invalid/logo.png'],
    ['marca_logo', 'data:image/gif;base64,R0lGOD=='],
    ['marca_logo', 'data:image/png;base64,AAAA") ; x: url("'],
    ['marca_nombre', "Empresa'; x: y"],
    ['marca_nombre', 'a'.repeat(61)],
    ['marca_nombre', '   '],
    ['otra_cosa', '#aaaaaa'],
  ])('ignora %s = %j', (codigo, valor) => {
    expect(valorCss(codigo, valor)).toBeUndefined();
  });

  it('un logo por encima del tope se ignora', () => {
    const grande = `data:image/png;base64,${'A'.repeat(MAXIMO_LOGO)}`;
    expect(valorCss('marca_logo', grande)).toBeUndefined();
  });

  it('sin valor (null) no hay nada que aplicar', () => {
    expect(valorCss('marca_color_primario', null)).toBeUndefined();
  });
});

describe('cargarMarca', () => {
  it('aplica a :root los siete parámetros que llegan bien', async () => {
    const lector = lectorCon({
      marca_nombre: 'Empresa Ejemplo',
      marca_logo: PNG,
      marca_color_primario: '#003366',
      marca_color_primario_fuerte: '#002244',
      marca_color_primario_suave: '#e6f0fa',
      marca_color_acento: '#ff8800',
      marca_color_superficie: '#f7f9fb',
    });
    const aplicadas = await cargarMarca(lector);
    const estilo = document.documentElement.style;
    // Los siete parámetros más el anillo de foco, que no es un parámetro: sigue al primario.
    expect(Object.keys(aplicadas)).toHaveLength(PARAMETROS_DE_MARCA.length + 1);
    expect(estilo.getPropertyValue('--color-foco')).toBe('#003366');
    expect(estilo.getPropertyValue('--color-primario')).toBe('#003366');
    expect(estilo.getPropertyValue('--color-primario-fuerte')).toBe('#002244');
    expect(estilo.getPropertyValue('--color-primario-suave')).toBe('#e6f0fa');
    expect(estilo.getPropertyValue('--color-acento')).toBe('#ff8800');
    expect(estilo.getPropertyValue('--color-superficie')).toBe('#f7f9fb');
    expect(estilo.getPropertyValue('--marca-nombre')).toBe("'Empresa Ejemplo'");
    expect(estilo.getPropertyValue('--marca-logo')).toBe(`url("${PNG}")`);
  });

  it('pide cada definición SIN tarea: la marca se lee igual en una bandeja', async () => {
    const pedidas: unknown[] = [];
    await cargarMarca(async (p) => {
      pedidas.push(p);
      return { clase: 'PARAMETRO', valor: null };
    });
    expect(pedidas).toHaveLength(7);
    for (const p of pedidas) expect(p).not.toHaveProperty('tarea');
    expect(rutaDeValores({ definicion: 'marca_logo' })).toBe('/extension/parametros/valores?definicion=marca_logo');
  });

  it('si la lectura falla del todo, no lanza y no toca ningún token', async () => {
    const aplicadas = await cargarMarca(async ({ definicion }) => {
      throw new LecturaFallida('sin-respuesta', definicion);
    });
    expect(aplicadas).toEqual({});
    expect(document.documentElement.getAttribute('style') ?? '').toBe('');
  });

  it('si no hay valor (null), se quedan los tokens por defecto', async () => {
    const aplicadas = await cargarMarca(lectorCon({ marca_color_primario: null, marca_nombre: null }));
    expect(aplicadas).toEqual({});
  });

  it('un fallo en un parámetro no arrastra a los demás', async () => {
    const aplicadas = await cargarMarca(lectorCon({ marca_color_acento: '#ff8800' }));
    expect(aplicadas).toEqual({ '--color-acento': '#ff8800' });
  });

  it('un valor con forma inválida (servidor comprometido o dato viejo) se ignora y el resto se aplica', async () => {
    const aplicadas = await cargarMarca(
      lectorCon({ marca_color_primario: 'url(javascript:x)', marca_color_acento: '#ff8800' }),
    );
    expect(aplicadas).toEqual({ '--color-acento': '#ff8800' });
    expect(document.documentElement.style.getPropertyValue('--color-primario')).toBe('');
  });

  it('avisa al documento cuando termina, aunque no haya aplicado nada', async () => {
    const oyente = vi.fn();
    document.addEventListener(EVENTO_MARCA, oyente);
    await cargarMarca(async ({ definicion }) => {
      throw new LecturaFallida('sin-respuesta', definicion);
    });
    document.removeEventListener(EVENTO_MARCA, oyente);
    expect(oyente).toHaveBeenCalledTimes(1);
  });
});

describe('cargarMarca: un solo color de marca basta (los demás se derivan del primario)', () => {
  const estilo = (p: string) => document.documentElement.style.getPropertyValue(p);
  const luminancia = (hex: string): number => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const contraste = (a: string, b: string): number => {
    const [x, y] = [luminancia(a), luminancia(b)].sort((m, n) => n - m);
    return (x + 0.05) / (y + 0.05);
  };

  it('con solo el primario, el foco, el fuerte, el suave y el acento salen de él (ya no queda el morado)', async () => {
    await cargarMarca(lectorCon({ marca_color_primario: '#003366' }));
    expect(estilo('--color-primario')).toBe('#003366');
    expect(estilo('--color-foco')).toBe('#003366');
    for (const p of ['--color-primario-fuerte', '--color-primario-suave', '--color-acento']) {
      expect(estilo(p), p).toMatch(/^#[0-9a-f]{6}$/);
      expect(estilo(p), p).not.toMatch(/^#(581c87|f3e8ff|a855f7|6b21a8)$/);
    }
    // El fuerte es texto sobre blanco y sobre el suave: tiene que seguir leyéndose.
    expect(contraste(estilo('--color-primario-fuerte'), '#ffffff')).toBeGreaterThanOrEqual(4.5);
    expect(contraste(estilo('--color-primario-fuerte'), estilo('--color-primario-suave'))).toBeGreaterThanOrEqual(4.5);
  });

  it('un valor explícito del proyecto gana sobre el derivado', async () => {
    await cargarMarca(lectorCon({ marca_color_primario: '#003366', marca_color_primario_fuerte: '#112233', marca_color_acento: '#ff8800' }));
    expect(estilo('--color-primario-fuerte')).toBe('#112233');
    expect(estilo('--color-acento')).toBe('#ff8800');
    expect(estilo('--color-primario-suave')).not.toBe('');
  });

  it('sin primario no se deriva nada: se quedan los tokens por defecto', async () => {
    await cargarMarca(lectorCon({ marca_nombre: 'Empresa Ejemplo' }));
    for (const p of ['--color-primario', '--color-foco', '--color-primario-fuerte', '--color-primario-suave', '--color-acento']) expect(estilo(p), p).toBe('');
  });

  it('un primario inválido no deriva nada', async () => {
    await cargarMarca(lectorCon({ marca_color_primario: 'azul' }));
    expect(estilo('--color-foco')).toBe('');
  });
});
