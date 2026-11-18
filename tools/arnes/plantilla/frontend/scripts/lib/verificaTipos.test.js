import { describe, expect, it } from 'vitest';
import { verificarTipos } from './verificaTipos.js';

/**
 * «No compila» tiene que significar «no se construye».
 *
 * La barrera de origen de las cifras es un TIPO: `importe(numeroCalculado)` no compila… pero el
 * build de Vite no verifica tipos (transpila y ya), así que sin esta pieza el ZIP se producía
 * igual con el error dentro. Estos casos ejercitan la pieza con subprocesos REALES —el comando
 * de verdad, no un doble—; el A/B sobre la pantalla con un mutante está en la evidencia de la
 * tarea 1.4.
 */
const nodo = (codigo) => [process.execPath, '-e', codigo];

describe('verificarTipos', () => {
  it('si la verificación sale limpia, deja seguir', () => {
    expect(() => verificarTipos({ comando: nodo('process.exit(0)') })).not.toThrow();
  });

  it('si falla, aborta diciendo que la pantalla NO se construye, con la salida del comando', () => {
    const comando = nodo(
      "console.log('src/forms/x/X.svelte:12 Argument of type number is not assignable to Dinero'); process.exit(1)",
    );

    expect(() => verificarTipos({ comando })).toThrow(/NO se construye[\s\S]*not assignable to Dinero/);
  });

  it('la salida de error también se enseña: nunca en silencio', () => {
    const comando = nodo("console.error('Unused @ts-expect-error directive'); process.exit(1)");

    expect(() => verificarTipos({ comando })).toThrow(/Unused @ts-expect-error directive/);
  });

  it('si el comando ni siquiera arranca, es un fallo, no un «no había nada que verificar»', () => {
    expect(() => verificarTipos({ comando: ['/no/existe/svelte-check'] })).toThrow(
      /no se pudo ejecutar la verificación de tipos/,
    );
  });

  it('por defecto corre el script `check` del proyecto (el que lleva --tsconfig)', () => {
    // No se ejecuta aquí (tarda segundos y ya corre en el barrido): se comprueba QUÉ correría.
    // Un `svelte-check` a pelo no mira los `.ts` (lección de `check_barrera_tipos`), así que el
    // comando tiene que ser el script del proyecto, no uno escrito en este fichero.
    let corrido;
    verificarTipos({ ejecutar: (comando) => ((corrido = comando), { status: 0, stdout: '', stderr: '' }) });
    expect(corrido.slice(-3)).toEqual(['run', '--silent', 'check']);
  });
});
