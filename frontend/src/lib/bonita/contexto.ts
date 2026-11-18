/**
 * Contexto que la plataforma pasa al formulario por la dirección con la que lo abre.
 *
 * Núcleo heredado de la plantilla interna. Se conserva su heurística por longitud
 * del identificador para el caso en que la plataforma solo aporte `id`: los
 * identificadores de definición de proceso son largos (del orden de 19 dígitos) y
 * los de tarea, cortos.
 */

import { parametroDeUrl } from './config';
import type { ContextoBonita, TipoDeFormulario } from './tipos';

/** Umbral de longitud que separa un id de proceso de un id de tarea. */
const LONGITUD_ID_PROCESO = 10;

/** Lee el contexto de la dirección actual. */
export function leerContexto(): ContextoBonita {
  const idTareaExplicito = parametroDeUrl('taskId');
  const idProcesoExplicito = parametroDeUrl('processId');
  const idGenerico = parametroDeUrl('id');

  let idTarea = idTareaExplicito;
  let idProceso = idProcesoExplicito;

  if (!idTarea && !idProceso && idGenerico) {
    if (idGenerico.length > LONGITUD_ID_PROCESO) idProceso = idGenerico;
    else idTarea = idGenerico;
  }

  let tipo: TipoDeFormulario = 'desconocido';
  if (idTarea && !idProceso) tipo = 'tarea';
  else if (idProceso && !idTarea) tipo = 'instanciacion';

  return {
    idTarea,
    idProceso,
    idCaso: parametroDeUrl('caseId'),
    tipo,
  };
}
