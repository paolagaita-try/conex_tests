/**
 * Lectura de los datos del caso que una pantalla muestra en solo lectura («Datos que carga al abrir» de la matriz de
 * formularios, campos con `lee`).
 *
 * Se leen SIEMPRE por la extensión REST de lecturas del caso (`GET /bonita/API/extension/consultas/caso?caseId=<id>`),
 * que devuelve el objeto raíz del caso como JSON, nunca por `/API/bdm`. Cada campo `lee` nombra `Objeto.atributo`: su
 * valor es el atributo de ese objeto. Lo que no es `Objeto.atributo` (una process variable, una consulta) no sale de esta
 * lectura y se dice, no se pinta vacío.
 */

import { peticion, tareaHumana, TIEMPO_MAXIMO_DE_CONSULTA_MS } from './cliente';
import { parametroDeUrl } from './config';
import type { ContextoBonita } from './tipos';

/** Un dato de solo lectura de la pantalla (lo genera el arnés en `generado/contrato.ts`). */
export interface Lectura {
  readonly etiqueta: string;
  /** Lo que nombra la matriz: `Objeto.atributo`, `pv variable`… */
  readonly lee: string;
  /** El atributo del objeto del caso, si `lee` es `Objeto.atributo`; si no, `null`. */
  readonly atributo: string | null;
}

/** El objeto raíz del caso, tal como lo devuelve la extensión. */
export type ObjetoDelCaso = Readonly<Record<string, unknown>>;

/** Lo que se muestra de un dato que esta lectura no trae (no es `Objeto.atributo`). */
export const NO_LEIDO = 'No disponible en la lectura del caso';
/** Lo que se muestra de un atributo sin valor en el caso. */
export const SIN_VALOR = '—';

/** Lee el objeto raíz del caso por la extensión de lecturas del caso. */
export function leerCaso(idCaso: string): Promise<ObjetoDelCaso> {
  return peticion<ObjetoDelCaso>(`/extension/consultas/caso?caseId=${encodeURIComponent(idCaso)}`, {
    tiempoMaximoMs: TIEMPO_MAXIMO_DE_CONSULTA_MS,
  });
}

/**
 * El caso de la pantalla: el `caseId` de la dirección si lo trae; en un resumen de caso, el `id` de la dirección (el
 * portal abre el overview con el id del caso); en una tarea, el caso de la tarea (el portal solo pasa su `id`).
 */
export async function idCasoDe(contexto: ContextoBonita, resumen = false): Promise<string | null> {
  if (contexto.idCaso) return contexto.idCaso;
  if (resumen) return parametroDeUrl('id');
  if (contexto.idTarea) return String((await tareaHumana(contexto.idTarea)).caseId);
  return null;
}

/** El texto de un dato del caso, para mostrarlo. */
export function textoDeLectura(objeto: ObjetoDelCaso, lectura: Lectura): string {
  if (lectura.atributo === null) return NO_LEIDO;
  const valor = objeto[lectura.atributo];
  if (valor === null || valor === undefined || valor === '') return SIN_VALOR;
  if (typeof valor === 'boolean') return valor ? 'sí' : 'no';
  if (typeof valor === 'string' || typeof valor === 'number') return String(valor);
  return JSON.stringify(valor);
}

/**
 * Carga los datos de solo lectura de la pantalla, en el orden de `lecturas`. Lanza si no hay caso o si la lectura
 * falla: la pantalla lo dice en vez de enseñar datos vacíos.
 */
export async function cargarLecturas(
  lecturas: readonly Lectura[],
  contexto: ContextoBonita,
  resumen = false,
  leer: (idCaso: string) => Promise<ObjetoDelCaso> = leerCaso,
): Promise<string[]> {
  const idCaso = await idCasoDe(contexto, resumen);
  if (!idCaso) throw new Error('La pantalla no sabe de qué caso es: no llegó el caso ni la tarea en la dirección.');
  const objeto = await leer(idCaso);
  return lecturas.map((l) => textoDeLectura(objeto ?? {}, l));
}
