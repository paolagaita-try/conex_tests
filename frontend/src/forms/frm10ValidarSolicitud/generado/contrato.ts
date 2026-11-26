// GENERADO por el arnés desde docs/07-bonita/contratos.md y docs/07-bonita/matriz-formularios.md.
// NO SE EDITA A MANO: cambia la documentación y corre `tools/arnes.sh generar`. Lo propio de la pantalla
// va en los ficheros de la carpeta del formulario (el esqueleto), que el generador no vuelve a tocar.

import type { Lectura } from '$lib/bonita/caso';
import type { ValorDeCampo, ValoresDelFormulario } from '$lib/ui/valores';

/** Identidad del formulario: su id en la matriz, su página, su tarea, su contrato y su proceso. */
export const FORMULARIO = { id: "frm_10_validarSolicitud", pagina: "frm10ValidarSolicitud", tipo: "tarea", tarea: "10_validarSolicitud", contrato: "ctr_10_validarSolicitud", proceso: "GestionPreventa", version: "1.5" } as const;

/** Todos los inputs del contrato, en su orden: el cuerpo los lleva siempre. */
export const ENTRADAS = ["resultado", "conceptoViabilidad", "notaValidacion", "supuestos"] as const;

/** El cuerpo que se envía al motor (`execution` / `instantiation`). */
export type CuerpoDelContrato = {
  resultado: string | null;
  conceptoViabilidad: string | null;
  notaValidacion: string | null;
  supuestos: string | null;
};

/** El cuerpo con todo input a `null`. */
export const CUERPO_VACIO: CuerpoDelContrato = {
  resultado: null,
  conceptoViabilidad: null,
  notaValidacion: null,
  supuestos: null,
};

/** Un campo del contrato, con la forma que consume `CamposDeContrato`. */
export interface CampoDeContrato {
  readonly ruta: string;
  readonly grupo: string;
  readonly nombre: string;
  /** La columna «Campo» de la matriz de formularios. */
  readonly etiqueta: string;
  readonly tipo: 'TEXT' | 'DECIMAL' | 'INTEGER' | 'BOOLEAN' | 'DATE' | 'FILE';
  /** El tipo del input en el contrato (decide cómo viaja en el cuerpo). */
  readonly tipoContrato: string;
  readonly multiple: boolean;
  readonly obligatorio: string;
  readonly requeridoSiempre: boolean;
  readonly constraint: string;
  readonly catalogo?: string;
  readonly widget?: 'fichas' | 'desplegable' | 'autocompletar';
  readonly depende?: string;
  readonly tope?: string;
}

/** Los campos de la matriz que escriben en el contrato, en el orden de la matriz. */
export const CAMPOS: readonly CampoDeContrato[] = [
  { ruta: "resultado", grupo: "datos", nombre: "resultado", etiqueta: "Resultado", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "sí", requeridoSiempre: true, constraint: "∈ {viable, bloqueado, no_viable}; El resultado debe ser viable, bloqueado o no viable" },
  { ruta: "notaValidacion", grupo: "datos", nombre: "notaValidacion", etiqueta: "Nota de validación", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "sí", requeridoSiempre: true, constraint: "La nota de validación es obligatoria" },
  { ruta: "supuestos", grupo: "datos", nombre: "supuestos", etiqueta: "Supuestos (condiciones)", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "no", requeridoSiempre: false, constraint: "Si el concepto es Aprobado con Condiciones, escriba las condiciones en los supuestos" },
];

/**
 * Los datos de solo lectura del caso que la pantalla muestra («Datos que carga al abrir»): `atributo` es el del
 * objeto raíz del caso que devuelve la extensión de lecturas del caso (`$lib/bonita/caso`); `null` si `lee`
 * no es `Objeto.atributo`.
 */
export const LECTURAS: readonly Lectura[] = [
  { etiqueta: "Ticket", lee: "Preventa.ticketId`, `ctx.ticket.subject`, `ctx.ticket.content`, `ctx.ticket.hs_ticket_priority`, `ctx.ticket.hs_pipeline_stage", atributo: null },
  { etiqueta: "Todas las propiedades del ticket", lee: "ctx.ticket.*", atributo: null },
  { etiqueta: "Negocio", lee: "`ctx.deal.dealname`, `ctx.deal.amount`, `ctx.deal.dealstage`, `ctx.deal.*` (MEDDPICC y demás)", atributo: null },
  { etiqueta: "Empresa", lee: "ctx.company.name`, `ctx.company.domain`, `ctx.company.*", atributo: null },
  { etiqueta: "Contactos", lee: "ctx.contacts[].firstname`, `lastname`, `email`, `phone`, `jobtitle", atributo: null },
  { etiqueta: "Comercial / owner", lee: "ctx.owner", atributo: null },
  { etiqueta: "Consultora asignada", lee: "Preventa.consultor`, `Preventa.fechaAsignacion", atributo: null },
  { etiqueta: "Validación anterior", lee: "Preventa.resultadoValidacion`, `Preventa.notaValidacion`, `Preventa.fechaValidacion", atributo: null },
];

/** Un texto; vacío o de otro tipo, `null`. */
function texto(v: ValorDeCampo): string | null {
  return typeof v === 'string' && v !== '' ? v : null;
}

/**
 * El cuerpo del contrato desde los valores del formulario (por ruta) y los archivos ya subidos (por ruta, de
 * `subirArchivosDe`). Lleva TODO input del contrato: el que la matriz no usa va a `null`, porque el motor
 * responde 400 si falta uno. Un FILE viaja como su referencia subida `{ filename, tempPath, contentType }`.
 * Los inputs de solo lectura sin campos (conceptoViabilidad) los pone la pantalla en `externos`.
 */
export function cuerpoDelContrato(
  valores: ValoresDelFormulario,
  _subidos: Readonly<Record<string, never>> = {},
  externos: Partial<CuerpoDelContrato> = {},
): CuerpoDelContrato {
  return {
    resultado: texto(valores["resultado"]),
    conceptoViabilidad: externos.conceptoViabilidad ?? null,
    notaValidacion: texto(valores["notaValidacion"]),
    supuestos: texto(valores["supuestos"]),
  };
}
