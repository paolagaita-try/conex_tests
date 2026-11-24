/**
 * Lectura de las opciones vigentes de una lista (o del valor de un parámetro) del módulo de
 * parámetros, para pintar un campo de formulario.
 *
 * ## Qué hace y qué NO hace
 *
 * Pide `GET extension/parametros/valores?definicion&tarea&padre` y devuelve lo que el servidor
 * resolvió. **El ámbito, la familia y la visibilidad los decide el servidor a partir de la tarea**:
 * este módulo no manda proceso, actividad ni familia, y no filtra nada por su cuenta. Un formulario de
 * instanciación no tiene tarea: manda `instanciacion` = el id de la definición del proceso (que la plataforma le
 * pasa al abrirlo), y el servidor deduce de ella el proceso y la familia del actor iniciador.
 *
 * ## Si la lectura falla
 *
 * Lanza `LecturaFallida`. Quien pinta el campo muestra un aviso y bloquea el envío; **nunca**
 * degrada a texto libre, que es exactamente el defecto que el módulo de parámetros corrige. Por eso la respuesta se
 * lee con rigor: una forma inesperada es un fallo (`formato`), no una lista vacía que el formulario
 * pintaría como «no hay opciones» sin avisar.
 *
 * ## Sin cifras
 *
 * El valor de un parámetro (un tope) viaja como el TEXTO decimal que el servidor sirvió; este módulo
 * no lo convierte ni lo formatea: formatear cifras es de la galería (`$lib/ui/formato`).
 */

import { peticion, TIEMPO_MAXIMO_DE_CONSULTA_MS } from '$lib/bonita/cliente';

/** Una opción vigente de una lista, tal como la sirve el módulo. */
export interface OpcionVigente {
  readonly codigo: string;
  readonly etiqueta: string;
  readonly ayuda?: string;
}

/** Lo que el servidor resolvió para una definición. */
export type ValoresLeidos =
  | { readonly clase: 'LISTA'; readonly opciones: readonly OpcionVigente[] }
  | { readonly clase: 'PARAMETRO'; readonly valor: string | null; readonly unidad?: string };

export interface PeticionDeValores {
  /** Código de la definición (`tipo_de_permiso`). */
  readonly definicion: string;
  /**
   * Identificador de la tarea abierta: de ella deduce el servidor proceso, actividad y familia. Sin
   * tarea (una bandeja, la marca del proyecto) el servidor solo sirve definiciones de visibilidad CLIENTE,
   * en el ámbito global: nunca una interna.
   */
  readonly tarea?: string;
  /**
   * Formulario de instanciación (sin tarea): el id de la definición del proceso. El servidor deduce de él el proceso
   * y la familia del iniciador, y exige que quien llama pueda iniciarlo. Con `tarea`, no viaja.
   */
  readonly instanciacion?: string;
  /** Código del padre cuando la definición cuelga de otra lista (`anual`). */
  readonly padre?: string;
}

/** Quién lee: la real contra la API, o un doble en las pruebas. */
export type LectorDeValores = (peticion: PeticionDeValores) => Promise<ValoresLeidos>;

export type MotivoDeFallo = 'sin-respuesta' | 'no-disponible' | 'formato';

/** La lectura no se pudo completar. El motivo es para quien depura; la persona ve un aviso neutro. */
export class LecturaFallida extends Error {
  constructor(
    readonly motivo: MotivoDeFallo,
    readonly definicion: string,
    detalle?: string,
  ) {
    super(`No se pudo leer «${definicion}» del módulo de parámetros (${motivo})${detalle ? `: ${detalle}` : ''}`);
    this.name = 'LecturaFallida';
  }
}

function esObjeto(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function opcionDe(crudo: unknown, definicion: string, i: number): OpcionVigente {
  if (!esObjeto(crudo) || typeof crudo.codigo !== 'string' || !crudo.codigo || typeof crudo.etiqueta !== 'string') {
    throw new LecturaFallida('formato', definicion, `la opción ${i} no trae código y etiqueta`);
  }
  const ayuda = typeof crudo.ayuda === 'string' && crudo.ayuda.trim() ? crudo.ayuda : undefined;
  return ayuda === undefined
    ? { codigo: crudo.codigo, etiqueta: crudo.etiqueta }
    : { codigo: crudo.codigo, etiqueta: crudo.etiqueta, ayuda };
}

/** Entiende la respuesta del servidor; cualquier forma que no conozca es un fallo, no un vacío. */
export function entenderValores(crudo: unknown, definicion: string): ValoresLeidos {
  if (!esObjeto(crudo) || crudo.definicion !== definicion) {
    throw new LecturaFallida('formato', definicion, 'la respuesta no corresponde a la definición pedida');
  }
  if (crudo.clase === 'LISTA') {
    if (!Array.isArray(crudo.opciones)) throw new LecturaFallida('formato', definicion, 'una lista sin `opciones`');
    const opciones = crudo.opciones.map((o, i) => opcionDe(o, definicion, i));
    if (new Set(opciones.map((o) => o.codigo)).size !== opciones.length) {
      throw new LecturaFallida('formato', definicion, 'la lista trae códigos repetidos');
    }
    return { clase: 'LISTA', opciones };
  }
  if (crudo.clase === 'PARAMETRO') {
    const valor = crudo.valor;
    if (valor !== null && valor !== undefined && typeof valor !== 'string') {
      throw new LecturaFallida('formato', definicion, 'el valor del parámetro no viene como texto');
    }
    const unidad = typeof crudo.unidad === 'string' ? crudo.unidad : undefined;
    return unidad === undefined
      ? { clase: 'PARAMETRO', valor: valor ?? null }
      : { clase: 'PARAMETRO', valor: valor ?? null, unidad };
  }
  throw new LecturaFallida('formato', definicion, `clase desconocida «${String(crudo.clase)}»`);
}

/** La dirección de la lectura. Estos parámetros son los únicos que el servidor acepta (tarea O instanciación). */
export function rutaDeValores({ definicion, tarea, instanciacion, padre }: PeticionDeValores): string {
  const consulta = new URLSearchParams({ definicion });
  if (tarea !== undefined && tarea !== '') consulta.set('tarea', tarea);
  else if (instanciacion !== undefined && instanciacion !== '') consulta.set('instanciacion', instanciacion);
  if (padre !== undefined && padre !== '') consulta.set('padre', padre);
  return `/extension/parametros/valores?${consulta.toString()}`;
}

/** El lector real: la API de Bonita, con el mismo tiempo máximo que las demás consultas. */
export const leerValores: LectorDeValores = async (p) => {
  let crudo: unknown;
  try {
    crudo = await peticion<unknown>(rutaDeValores(p), { tiempoMaximoMs: TIEMPO_MAXIMO_DE_CONSULTA_MS });
  } catch (causa) {
    const estado = (causa as { estado?: unknown })?.estado;
    throw new LecturaFallida(estado === 0 || estado === undefined ? 'sin-respuesta' : 'no-disponible', p.definicion);
  }
  return entenderValores(crudo, p.definicion);
};
