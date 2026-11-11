/**
 * La contraseña de desarrollo no viaja en un ZIP.
 *
 * `credencialesDeDesarrollo` solo lee `VITE_BONITA_DEV_PASSWORD` con `import.meta.env.DEV`, y en un
 * build Vite elimina esa rama. Esta pieza lo MIDE sobre lo construido, antes de empaquetar: si el
 * valor de la clave (del entorno del proceso o de un `.env` del proyecto) aparece en algún
 * fichero, el build falla. El error nombra el fichero y la variable, nunca el valor.
 */

import { existsSync, readFileSync } from 'node:fs';
import { readdir, readFile } from 'node:fs/promises';
import path from 'node:path';

const VARIABLE = 'VITE_BONITA_DEV_PASSWORD';
const FICHEROS_ENV = ['.env', '.env.local', '.env.production', '.env.production.local'];

/** Los valores de la clave de desarrollo que hay a la vista: el entorno del proceso y los `.env` de `raiz`. */
export function secretosDeDesarrollo(raiz, entorno = process.env) {
  const valores = new Set();
  if (entorno[VARIABLE]) valores.add(entorno[VARIABLE]);
  for (const nombre of FICHEROS_ENV) {
    const fichero = path.join(raiz, nombre);
    if (!existsSync(fichero)) continue;
    for (const linea of readFileSync(fichero, 'utf8').split(/\r?\n/)) {
      const m = linea.match(new RegExp(`^\\s*(?:export\\s+)?${VARIABLE}\\s*=\\s*(.*?)\\s*$`));
      const valor = m?.[1].replace(/^(['"])(.*)\1$/, '$2');
      if (valor) valores.add(valor);
    }
  }
  return [...valores];
}

async function ficherosDe(dir) {
  const salida = [];
  for (const entrada of await readdir(dir, { withFileTypes: true })) {
    const ruta = path.join(dir, entrada.name);
    if (entrada.isDirectory()) salida.push(...(await ficherosDe(ruta)));
    else salida.push(ruta);
  }
  return salida;
}

/** Lanza si algún fichero bajo `dir` contiene alguno de `secretos` (los vacíos no cuentan). */
export async function comprobarSinSecretos(dir, secretos) {
  const buscados = secretos.filter((s) => typeof s === 'string' && s.length > 0).map((s) => Buffer.from(s));
  if (buscados.length === 0) return;
  const con = [];
  for (const fichero of await ficherosDe(dir)) {
    const contenido = await readFile(fichero);
    if (buscados.some((b) => contenido.includes(b))) con.push(path.relative(dir, fichero));
  }
  if (con.length > 0) {
    throw new Error(
      `el valor de ${VARIABLE} aparece en lo construido (${con.join(', ')}): no se empaqueta. ` +
        'Las credenciales de desarrollo solo se leen con import.meta.env.DEV.',
    );
  }
}
