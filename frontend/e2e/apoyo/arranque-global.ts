import { execFileSync } from 'node:child_process';
import { basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PUERTO, quienEscucha } from './bonita';

/** El paso posterior al despliegue del proyecto (`tools/arnes.sh perfiles`), el mismo que corre `run-journey.sh`. */
const PERFILES = fileURLToPath(new URL('../../../tools/perfiles.py', import.meta.url));

/**
 * Antes de la primera prueba:
 *  1. comprobar QUIÉN escucha el puerto. Un `200` no identifica a quién responde: con dos runtimes en la misma
 *     máquina, la suite mediría el artefacto del vecino y saldría verde. `run-journey.sh` declara su carpeta en
 *     `WORKDIR_ESPERADO`; sin ella (una corrida a mano) solo se exige que alguien escuche.
 *  2. asegurar, de forma idempotente, que los usuarios de la organización tienen el perfil User del portal: un
 *     artefacto Community no puede llevar ese mapeo, y sin él el portal no abre la aplicación. No se mapea aquí: se
 *     reutiliza el paso posterior al despliegue `tools/perfiles.py` (útil si el runtime se levantó a mano).
 */
export default async function globalSetup(): Promise<void> {
  const escucha = quienEscucha();
  if (!escucha) throw new Error(`[e2e] nadie escucha el puerto ${PUERTO}: levanta el runtime con tools/run-journey.sh --mantener`);
  const esperado = process.env.WORKDIR_ESPERADO;
  // Se compara el nombre de la carpeta (único por corrida): la ruta completa llega con `//` o `/private/var` según quién la escriba.
  if (esperado && !escucha.cmd.includes(basename(esperado))) {
    throw new Error(`[e2e] el puerto ${PUERTO} no es del runtime esperado (${esperado}): ${escucha.cmd.slice(0, 120)}`);
  }
  process.stderr.write(`[e2e] runtime verificado: pid ${escucha.pid}\n`);

  execFileSync('python3', [PERFILES, '--url', `http://localhost:${PUERTO}/bonita`], { stdio: ['ignore', 'inherit', 'inherit'] });
}
