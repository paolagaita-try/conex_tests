/**
 * Un rechazo del kit, en lenguaje de negocio. El servidor dice el MOTIVO (`SIN_PERMISO`,
 * `CONFLICTO`, `VALIDACION`, `NO_EXISTE`) y, en una validación, el campo; la pantalla decide la frase.
 * El detalle técnico del servidor no llega nunca a la pantalla: se usa para saber QUÉ campo falló y,
 * a lo sumo, para distinguir un código repetido de uno inválido.
 */
import { FalloDelKit } from './kit';
import { cuandoCompleto } from './formatos';
import * as T from './textos';

export type CampoDeFormulario = 'motivo' | 'etiqueta' | 'ayuda' | 'codigo' | 'valor' | 'comentario' | 'fecha' | 'general';

export interface Explicacion {
  campo: CampoDeFormulario;
  mensaje: string;
  /** La escritura pudo haberse aplicado: la respuesta no llegó o el servidor falló sin decir. Hay que releer antes de repetir. */
  desconocido?: boolean;
}

const CAMPOS: Record<string, CampoDeFormulario> = {
  motivo: 'motivo',
  'datos.etiqueta': 'etiqueta',
  'datos.ayuda': 'ayuda',
  codigo: 'codigo',
  'datos.valor': 'valor',
  comentario: 'comentario',
  vigenteHasta: 'fecha',
  'datos.vigenteHasta': 'fecha',
};

/** `yo` es el usuario de la sesión: un conflicto contra uno mismo no es «otra persona» (el cambio ya se guardó). */
export function explicar(e: unknown, yo?: string): Explicacion {
  if (!(e instanceof FalloDelKit)) return { campo: 'general', mensaje: T.FALLO_GENERAL };
  switch (e.clase) {
    case 'SIN_PERMISO':
      return { campo: 'general', mensaje: T.FALLO_SIN_PERMISO };
    case 'CONFLICTO':
      // Contra uno mismo: NO se afirma que el cambio de ahora se guardó (puede ser una propuesta pendiente o un cambio anterior).
      if (yo && e.guardadoPor === yo) return { campo: 'general', mensaje: T.conflictoPropio(e.guardadoEn ? cuandoCompleto(e.guardadoEn) : '') };
      return { campo: 'general', mensaje: T.FALLO_CONFLICTO };
    case 'NO_EXISTE':
      return { campo: 'general', mensaje: T.FALLO_NO_EXISTE };
    case 'VALIDACION': {
      const campo = CAMPOS[e.campo ?? ''] ?? 'general';
      const detalle = e.detalle ?? '';
      if (campo === 'motivo') return { campo, mensaje: T.ERROR_MOTIVO };
      if (campo === 'etiqueta') return { campo, mensaje: T.ERROR_ETIQUETA };
      if (campo === 'comentario') return { campo, mensaje: T.ERROR_COMENTARIO };
      if (campo === 'codigo') return { campo, mensaje: /ya existe|repetid|duplicad/i.test(detalle) ? T.ERROR_CODIGO_REPETIDO : T.ERROR_CODIGO };
      if (campo === 'valor') return { campo, mensaje: T.ERROR_VALOR_FUERA_DE_RANGO };
      return { campo: 'general', mensaje: T.FALLO_REVISA };
    }
    default:
      // SIN_RESPUESTA, SERVIDOR, FORMA: «no se cambió nada» solo lo prueba un 4xx. Aquí el servidor pudo haberlo aplicado.
      return { campo: 'general', mensaje: T.FALLO_DESCONOCIDO, desconocido: true };
  }
}
