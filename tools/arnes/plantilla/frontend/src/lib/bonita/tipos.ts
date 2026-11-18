/** Tipos de la frontera con Bonita. */

/** Qué clase de formulario es, según el contexto con el que se abrió. */
import type { CodigoHttp } from '$lib/bonita/marcas';

export type TipoDeFormulario = 'tarea' | 'instanciacion' | 'desconocido';

/** Contexto que la plataforma pasa al formulario por la dirección. */
export interface ContextoBonita {
  /** Identificador de la tarea humana a ejecutar (formulario de tarea). */
  idTarea: string | null;
  /** Identificador de la definición del proceso (formulario de instanciación). */
  idProceso: string | null;
  /** Identificador del caso, cuando la plataforma lo aporta. */
  idCaso: string | null;
  tipo: TipoDeFormulario;
}

/** Una entrada del contrato, tal como la expone la API REST de Bonita. */
export interface EntradaDeContrato {
  name: string;
  description: string | null;
  type: string;
  multiple: boolean;
  inputs?: EntradaDeContrato[];
}

/** Contrato de una tarea o de la instanciación de un proceso. */
export interface Contrato {
  inputs: EntradaDeContrato[];
}

/**
 * Un archivo tal como lo espera un input de tipo FILE del contrato Bonita.
 *
 * El journey del proceso manda los inputs FILE a `null` a propósito: la carga real de
 * documentos es de los formularios.
 */
export interface ArchivoContrato {
  /** Nombre del archivo, tal como lo subió el usuario. */
  nombre: string;
  /** Contenido en base64. */
  contenido: string;
}

/** Error de la API REST de Bonita, normalizado. */
export class ErrorDeBonita extends Error {
  constructor(
    message: string,
    readonly estado: CodigoHttp | 0,
    readonly cuerpo?: unknown,
  ) {
    super(message);
    this.name = 'ErrorDeBonita';
  }
}
