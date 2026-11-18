/**
 * La verificación de tipos, como compuerta del build .
 *
 * La barrera de origen de las cifras es un tipo marcado: `importe(numeroCalculado)` es un
 * error de compilación. Pero Vite no verifica tipos —transpila y empaqueta—, así que hasta
 * ahora el ZIP se producía igual con el error dentro y «no compila» solo significaba «alguien
 * lo verá si corre `npm run check`». Esta pieza hace que signifique «no se construye».
 *
 * Corre el script `check` del proyecto, no un `svelte-check` escrito aquí: el comando con el
 * que se mide es parte de la medición, y sin `--tsconfig` svelte-check no mira los `.ts`
 * (lo vigila `check_barrera_tipos`). Si falla, aborta con su salida; nunca en silencio.
 */

import { spawnSync } from 'node:child_process';
import process from 'node:process';

/** `npm run check` con el mismo npm que lanzó el build, si lo lanzó npm. */
function comandoDelProyecto() {
  const npm = process.env.npm_execpath;
  return npm && npm.endsWith('.js')
    ? [process.execPath, npm, 'run', '--silent', 'check']
    : ['npm', 'run', '--silent', 'check'];
}

function ejecutarDeVerdad([ejecutable, ...argumentos], cwd) {
  return spawnSync(ejecutable, argumentos, { cwd, encoding: 'utf8' });
}

/**
 * Lanza si la verificación de tipos no sale limpia (o si no se pudo ejecutar).
 *
 * @param {{ cwd?: string, comando?: string[], ejecutar?: Function }} [opciones]
 */
export function verificarTipos({ cwd, comando = comandoDelProyecto(), ejecutar = ejecutarDeVerdad } = {}) {
  const r = ejecutar(comando, cwd);
  const legible = comando.join(' ');
  if (r.error) {
    throw new Error(`no se pudo ejecutar la verificación de tipos (${legible}): ${r.error.message}`);
  }
  if (r.status !== 0) {
    const salida = `${r.stdout ?? ''}${r.stderr ?? ''}`.trim();
    throw new Error(
      `la verificación de tipos falló (${legible}, rc=${r.status ?? r.signal}): la pantalla NO se construye.\n${salida}`,
    );
  }
}
