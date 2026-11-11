/**
 * La navegación de la aplicación: una sola página con rutas por `location.hash`, como la
 * bandeja navega dentro de sí misma. Nada de esto sale a la dirección de la plataforma: el portal ve
 * siempre `/bonita/apps/parametros/parametros/`.
 *
 *   #/                          inicio
 *   #/d/<definicion>/<proceso>/<actividad>/<pestana>   una lista o un parámetro en un ámbito
 *   #/aprobaciones              cambios por aprobar
 *   #/permisos · #/permisos/nueva
 *   #/importar
 *   #/traza
 *
 * El proceso y la actividad viajan con los nombres del motor (`*` = todo), codificados; los muestra
 * `nombres.ts`, nunca esta dirección (que la persona no lee).
 */
import { TODO } from './tipos';
import type { Ambito } from './ambitos';

/** Las secciones de la barra de pestañas de la aplicación. */
export type Seccion = 'parametros' | 'aprobaciones' | 'permisos' | 'traza';

export type PestanaDeDefinicion = 'valores' | 'usos' | 'historial';

export type Ruta =
  | { vista: 'inicio' }
  | { vista: 'definicion'; definicion: string; ambito: Ambito; pestana: PestanaDeDefinicion }
  | { vista: 'aprobaciones' }
  | { vista: 'permisos' }
  | { vista: 'nuevaDelegacion' }
  | { vista: 'importar' }
  | { vista: 'traza' };

const PESTANAS: readonly PestanaDeDefinicion[] = ['valores', 'usos', 'historial'];

export function hashDe(ruta: Ruta): string {
  switch (ruta.vista) {
    case 'inicio':
      return '#/';
    case 'definicion':
      return `#/d/${[ruta.definicion, ruta.ambito.proceso, ruta.ambito.actividad, ruta.pestana].map(encodeURIComponent).join('/')}`;
    case 'aprobaciones':
      return '#/aprobaciones';
    case 'permisos':
      return '#/permisos';
    case 'nuevaDelegacion':
      return '#/permisos/nueva';
    case 'importar':
      return '#/importar';
    case 'traza':
      return '#/traza';
  }
}

function descodificar(s: string | undefined): string | null {
  if (s === undefined || s === '') return null;
  try {
    return decodeURIComponent(s);
  } catch {
    return null;
  }
}

/** Lee el hash; lo que no entiende es el inicio (nunca una pantalla en blanco). */
export function leerRuta(hash: string): Ruta {
  const partes = hash.replace(/^#\/?/, '').split('/').filter((p) => p !== '');
  switch (partes[0]) {
    case 'aprobaciones':
      return { vista: 'aprobaciones' };
    case 'permisos':
      return partes[1] === 'nueva' ? { vista: 'nuevaDelegacion' } : { vista: 'permisos' };
    case 'importar':
      return { vista: 'importar' };
    case 'traza':
      return { vista: 'traza' };
    case 'd': {
      const definicion = descodificar(partes[1]);
      const proceso = descodificar(partes[2]) ?? TODO;
      const actividad = descodificar(partes[3]) ?? TODO;
      const pestana = PESTANAS.find((p) => p === descodificar(partes[4])) ?? 'valores';
      if (definicion === null) return { vista: 'inicio' };
      return { vista: 'definicion', definicion, ambito: { proceso, actividad }, pestana };
    }
    default:
      return { vista: 'inicio' };
  }
}
