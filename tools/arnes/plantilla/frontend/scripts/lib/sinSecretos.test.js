import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { comprobarSinSecretos, secretosDeDesarrollo } from './sinSecretos.js';

/**
 * La contraseña de desarrollo no viaja en un ZIP: si el JS construido contiene su valor, el build
 * falla antes de empaquetar, y el error no repite el valor.
 */
const CLAVE = 'centinela-de-prueba-123';
let dir;

function construido(ficheros) {
  dir = mkdtempSync(path.join(tmpdir(), 'sin-secretos-'));
  for (const [rel, contenido] of Object.entries(ficheros)) {
    mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    writeFileSync(path.join(dir, rel), contenido);
  }
  return dir;
}

afterEach(() => dir && rmSync(dir, { recursive: true, force: true }));

describe('comprobarSinSecretos', () => {
  it('pasa si ningún fichero construido contiene la clave', async () => {
    await expect(comprobarSinSecretos(construido({ 'js/a.js': 'const x = 1;', 'index.html': '<html>' }), [CLAVE]))
      .resolves.toBeUndefined();
  });

  it('falla si un fichero la contiene, dice cuál y no repite la clave', async () => {
    const d = construido({ 'js/a.js': `const c = "${CLAVE}";` });
    const error = await comprobarSinSecretos(d, [CLAVE]).catch((e) => e);
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toContain(path.join('js', 'a.js'));
    expect(error.message).toContain('VITE_BONITA_DEV_PASSWORD');
    expect(error.message).not.toContain(CLAVE);
  });

  it('sin clave definida no hay nada que buscar', async () => {
    await expect(comprobarSinSecretos(construido({ 'js/a.js': 'x' }), ['', undefined])).resolves.toBeUndefined();
  });
});

describe('secretosDeDesarrollo', () => {
  it('toma la clave del entorno del proceso y de los .env del proyecto', () => {
    const d = construido({ '.env': 'VITE_BONITA_DEV_PASSWORD=de-env\n', '.env.local': 'VITE_BONITA_DEV_PASSWORD=de-local\n' });
    expect(secretosDeDesarrollo(d, { VITE_BONITA_DEV_PASSWORD: 'de-proceso' }).sort())
      .toEqual(['de-env', 'de-local', 'de-proceso']);
    expect(secretosDeDesarrollo(d, {}).sort()).toEqual(['de-env', 'de-local']);
  });
});
