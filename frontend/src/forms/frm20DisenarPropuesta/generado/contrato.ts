// GENERADO por el arnés desde docs/07-bonita/contratos.md y docs/07-bonita/matriz-formularios.md.
// NO SE EDITA A MANO: cambia la documentación y corre `tools/arnes.sh generar`. Lo propio de la pantalla
// va en los ficheros de la carpeta del formulario (el esqueleto), que el generador no vuelve a tocar.

import type { ArchivoSubido } from '$lib/bonita/archivos';
import type { Lectura } from '$lib/bonita/caso';
import type { ValorDeCampo, ValoresDelFormulario } from '$lib/ui/valores';

/** Identidad del formulario: su id en la matriz, su página, su tarea, su contrato y su proceso. */
export const FORMULARIO = { id: "frm_20_disenarPropuesta", pagina: "frm20DisenarPropuesta", tipo: "tarea", tarea: "20_disenarPropuesta", contrato: "ctr_20_disenarPropuesta", proceso: "GestionPreventa", version: "1.5" } as const;

/** Todos los inputs del contrato, en su orden: el cuerpo los lleva siempre. */
export const ENTRADAS = ["valoracionOperaciones", "urlPptaPreventa", "linkRepoPreventa", "notaPropuesta", "adjuntos"] as const;

/** El cuerpo que se envía al motor (`execution` / `instantiation`). */
export type CuerpoDelContrato = {
  valoracionOperaciones: string | null;
  urlPptaPreventa: string | null;
  linkRepoPreventa: string | null;
  notaPropuesta: string | null;
  adjuntos: ArchivoSubido[] | null;
};

/** El cuerpo con todo input a `null`. */
export const CUERPO_VACIO: CuerpoDelContrato = {
  valoracionOperaciones: null,
  urlPptaPreventa: null,
  linkRepoPreventa: null,
  notaPropuesta: null,
  adjuntos: null,
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
  { ruta: "valoracionOperaciones", grupo: "datos", nombre: "valoracionOperaciones", etiqueta: "Valoración de operaciones", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "sí", requeridoSiempre: true, constraint: "La valoración de operaciones debe ser un enlace que empiece por http:// o https://" },
  { ruta: "urlPptaPreventa", grupo: "datos", nombre: "urlPptaPreventa", etiqueta: "URL propuesta (presentación)", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "sí", requeridoSiempre: true, constraint: "La URL de la propuesta debe empezar por http:// o https://" },
  { ruta: "linkRepoPreventa", grupo: "datos", nombre: "linkRepoPreventa", etiqueta: "Link repositorio preventa", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "sí", requeridoSiempre: true, constraint: "El enlace al repositorio debe empezar por http:// o https://" },
  { ruta: "notaPropuesta", grupo: "datos", nombre: "notaPropuesta", etiqueta: "Nota de propuesta", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "no", requeridoSiempre: false, constraint: "" },
  { ruta: "adjuntos", grupo: "datos", nombre: "adjuntos", etiqueta: "Adjuntos", tipo: "FILE", tipoContrato: "FILE", multiple: true, obligatorio: "no", requeridoSiempre: false, constraint: "" },
];

/**
 * Los datos de solo lectura del caso que la pantalla muestra («Datos que carga al abrir»): `atributo` es el del
 * objeto raíz del caso que devuelve la extensión de lecturas del caso (`$lib/bonita/caso`); `null` si `lee`
 * no es `Objeto.atributo`.
 */
export const LECTURAS: readonly Lectura[] = [
  { etiqueta: "Ticket", lee: "Preventa.ticketId`, `ctx.ticket.*", atributo: null },
  { etiqueta: "Negocio", lee: "ctx.deal.*", atributo: null },
  { etiqueta: "Empresa", lee: "ctx.company.*", atributo: null },
  { etiqueta: "Contactos", lee: "ctx.contacts[]", atributo: null },
  { etiqueta: "Validación", lee: "Preventa.resultadoValidacion`, `Preventa.conceptoViabilidad`, `Preventa.notaValidacion`, `Preventa.supuestos`, `Preventa.fechaValidacion", atributo: null },
];

/** Un texto; vacío o de otro tipo, `null`. */
function texto(v: ValorDeCampo): string | null {
  return typeof v === 'string' && v !== '' ? v : null;
}

/** Un input simple múltiple: el valor como lista de uno, o vacía. */
function lista<T>(v: T | null): T[] {
  return v === null ? [] : [v];
}

/**
 * El cuerpo del contrato desde los valores del formulario (por ruta) y los archivos ya subidos (por ruta, de
 * `subirArchivosDe`). Lleva TODO input del contrato: el que la matriz no usa va a `null`, porque el motor
 * responde 400 si falta uno. Un FILE viaja como su referencia subida `{ filename, tempPath, contentType }`.
 */
export function cuerpoDelContrato(
  valores: ValoresDelFormulario,
  subidos: Readonly<Record<string, ArchivoSubido>> = {},
): CuerpoDelContrato {
  return {
    valoracionOperaciones: texto(valores["valoracionOperaciones"]),
    urlPptaPreventa: texto(valores["urlPptaPreventa"]),
    linkRepoPreventa: texto(valores["linkRepoPreventa"]),
    notaPropuesta: texto(valores["notaPropuesta"]),
    adjuntos: lista(subidos["adjuntos"] ?? null),
  };
}
