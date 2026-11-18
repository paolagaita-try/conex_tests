import { describe, expect, it } from 'vitest';
import { cssDelTema, ficheroDeEntrada } from './tema.js';

const BOOTSTRAP = [
  '/*! Bootstrap v3.4.1 */',
  "@font-face { font-family: 'Glyphicons Halflings'; src: url('../fonts/glyphicons-halflings-regular.eot'); }",
  'html { font-size: 10px; }',
].join('\n');

describe('tema propio de la Living Application', () => {
  it('pone Bootstrap 3 primero y la hoja del proyecto después, para que la propia gane', () => {
    const css = cssDelTema(BOOTSTRAP, ':root { --color-primario: #123456; }\n');
    expect(css.indexOf('Bootstrap v3.4.1')).toBeLessThan(css.indexOf('--color-primario'));
    expect(css.endsWith(':root { --color-primario: #123456; }\n')).toBe(true);
  });

  it('las fuentes de Bootstrap se buscan junto a theme.css, no en la carpeta de al lado', () => {
    // El paquete lleva `resources/theme.css` y `resources/fonts/`: desde theme.css, `../fonts/` saldría del tema.
    const css = cssDelTema(BOOTSTRAP, '');
    expect(css).toContain("url('fonts/glyphicons-halflings-regular.eot')");
    expect(css).not.toContain('../fonts/');
  });

  it('es determinista', () => {
    expect(cssDelTema(BOOTSTRAP, 'a{}')).toBe(cssDelTema(BOOTSTRAP, 'a{}'));
  });

  it('el fichero que dice si hay fuente: tema.css en un tema, index.html en lo demás', () => {
    expect(ficheroDeEntrada({ tipo: 'tema' })).toBe('tema.css');
    for (const tipo of ['negocio', 'pagina', 'tecnico', 'administracion']) {
      expect(ficheroDeEntrada({ tipo })).toBe('index.html');
    }
  });
});
