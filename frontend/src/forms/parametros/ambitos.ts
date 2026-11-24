/**
 * El ámbito y su herencia, del lado del cliente (`Resolucion.groovy` del kit).
 *
 * Es el MISMO modelo que aplica el servidor, escrito para pintar: actividad → proceso → global, gana el
 * más específico. En una LISTA el ámbito que tiene al menos una opción activa **reemplaza la lista
 * entera**, también para las opciones de cada padre; en un PARÁMETRO cada valor hereda por separado
 * (por opción del padre). El servidor sigue decidiendo qué se aplica: esto solo evita pintar una
 * mentira sobre qué valdría.
 */
import { TODO, type Fila } from './tipos';

export interface Ambito {
  proceso: string;
  actividad: string;
}

export const GLOBAL: Ambito = { proceso: TODO, actividad: TODO };

export const mismoAmbito = (a: Ambito, b: Ambito): boolean => a.proceso === b.proceso && a.actividad === b.actividad;

export const esGlobal = (a: Ambito): boolean => mismoAmbito(a, GLOBAL);

/** Los ámbitos candidatos, del más específico al global. */
export function cadenaDe(a: Ambito): Ambito[] {
  const cadena: Ambito[] = [];
  if (a.actividad !== TODO) cadena.push({ proceso: a.proceso, actividad: a.actividad });
  if (a.proceso !== TODO) cadena.push({ proceso: a.proceso, actividad: TODO });
  cadena.push(GLOBAL);
  return cadena;
}

export const filasEn = (filas: Fila[], a: Ambito): Fila[] =>
  filas.filter((f) => f.proceso === a.proceso && f.actividad === a.actividad);

const activasEn = (filas: Fila[], a: Ambito): Fila[] => filasEn(filas, a).filter((f) => f.activo);

const porOrden = (a: Fila, b: Fila): number => (a.orden ?? 0) - (b.orden ?? 0) || a.codigo.localeCompare(b.codigo);

/** El ámbito cuya lista entera se usa en `a`, o `null` si ninguno tiene opciones activas. */
export function ambitoDeLista(filas: Fila[], a: Ambito): Ambito | null {
  return cadenaDe(a).find((c) => activasEn(filas, c).length > 0) ?? null;
}

/** Las opciones activas de la lista resuelta en `a` para un padre (o `'*'`), en su orden. */
export function listaResuelta(filas: Fila[], a: Ambito, padre: string = TODO): Fila[] {
  const origen = ambitoDeLista(filas, a);
  if (origen === null) return [];
  return activasEn(filas, origen)
    .filter((f) => f.codigoPadre === padre)
    .sort(porOrden);
}

/** El valor activo más específico de un parámetro para un padre (o `'*'`), con el ámbito de donde viene. */
export function parametroResuelto(filas: Fila[], a: Ambito, padre: string = TODO): { fila: Fila; de: Ambito } | null {
  for (const c of cadenaDe(a)) {
    const fila = activasEn(filas, c).find((f) => f.codigoPadre === padre);
    if (fila) return { fila, de: c };
  }
  return null;
}

/** Todas las filas (activas e inactivas) de un ámbito para un padre, en su orden: lo que se edita. */
export function filasOrdenadas(filas: Fila[], a: Ambito, padre: string = TODO): Fila[] {
  return filasEn(filas, a)
    .filter((f) => f.codigoPadre === padre)
    .sort(porOrden);
}

/** Los códigos de los padres que tienen filas en `a` (cascada): las pestañas por modalidad. */
export function padresConFilas(filas: Fila[], a: Ambito): string[] {
  return [...new Set(filasEn(filas, a).map((f) => f.codigoPadre))].filter((p) => p !== TODO).sort();
}

/** Los ámbitos de un proceso que tienen versión propia de esta definición (filas propias de la actividad). */
export function actividadesConVersionPropia(filas: Fila[], proceso: string): string[] {
  return [...new Set(filas.filter((f) => f.proceso === proceso && f.actividad !== TODO).map((f) => f.actividad))].sort();
}

/**
 * Cuántas opciones nuevas tiene el origen desde que se copió la versión propia (T-k): los códigos
 * activos del origen que no estaban en `codigosOrigen`. Una versión propia sin constancia de su origen
 * no avisa de nada.
 */
export function opcionesNuevasDelOrigen(filas: Fila[], propio: Ambito): string[] {
  const propias = filasEn(filas, propio);
  const copiadas = propias.find((f) => f.copiadoDe !== TODO && f.codigosOrigen !== null);
  if (!copiadas || copiadas.codigosOrigen === null) return [];
  let guardados: unknown;
  try {
    guardados = JSON.parse(copiadas.codigosOrigen);
  } catch {
    return [];
  }
  if (!Array.isArray(guardados)) return [];
  const desde = copiadas.copiadoDe.split('|');
  const origen: Ambito = { proceso: desde[0] ?? TODO, actividad: desde[1] ?? TODO };
  const clave = (f: Fila) => (f.codigoPadre === TODO ? f.codigo : [f.codigoPadre, f.codigo].join('|'));
  const antes = new Set(guardados.filter((x): x is string => typeof x === 'string'));
  return [...new Set(activasEn(filas, origen).map(clave))].filter((c) => !antes.has(c)).sort();
}

/**
 * Los hijos de una cascada cuyo padre ya no existe activo en el ámbito (T-j): huérfanos que la
 * aplicación señala en vez de esconder. `padresActivos` son los códigos activos de la lista madre.
 */
export function huerfanos(filas: Fila[], a: Ambito, padresActivos: string[]): Fila[] {
  const vivos = new Set(padresActivos);
  return filasEn(filas, a).filter((f) => f.codigoPadre !== TODO && !vivos.has(f.codigoPadre));
}
