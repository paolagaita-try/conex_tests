// GENERADO por el arnés desde docs/07-bonita/contratos.md y docs/07-bonita/matriz-formularios.md.
// NO SE EDITA A MANO: cambia la documentación y corre `tools/arnes.sh generar`. Lo propio de la pantalla
// va en los ficheros de la carpeta del formulario (el esqueleto), que el generador no vuelve a tocar.

import type { Lectura } from '$lib/bonita/caso';
import type { ValorDeCampo, ValoresDelFormulario } from '$lib/ui/valores';

/** Identidad del formulario: su id en la matriz, su página, su tarea, su contrato y su proceso. */
export const FORMULARIO = { id: "frm_holaRevisar", pagina: "frmHolaRevisar", tipo: "tarea", tarea: "revisar", contrato: "ctr_revisar", proceso: "Hola", version: "1.0" } as const;

/** Todos los inputs del contrato, en su orden: el cuerpo los lleva siempre. */
export const ENTRADAS = ["mensaje"] as const;

/** El cuerpo que se envía al motor (`execution` / `instantiation`). */
export type CuerpoDelContrato = {
  mensaje: string | null;
};

/** El cuerpo con todo input a `null`. */
export const CUERPO_VACIO: CuerpoDelContrato = {
  mensaje: null,
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
  { ruta: "mensaje", grupo: "datos", nombre: "mensaje", etiqueta: "Saludo definitivo", tipo: "TEXT", tipoContrato: "TEXT", multiple: false, obligatorio: "sí", requeridoSiempre: true, constraint: "∈ catálogo saludos; widget: desplegable", catalogo: "saludos", widget: "desplegable" },
];

/**
 * Los datos de solo lectura del caso que la pantalla muestra («Datos que carga al abrir»): `atributo` es el del
 * objeto raíz del caso que devuelve la extensión de lecturas del caso (`$lib/bonita/caso`); `null` si `lee`
 * no es `Objeto.atributo`.
 */
export const LECTURAS: readonly Lectura[] = [
  { etiqueta: "Saludo inicial", lee: "Saludo.mensaje", atributo: "mensaje" },
];

/** Un texto; vacío o de otro tipo, `null`. */
function texto(v: ValorDeCampo): string | null {
  return typeof v === 'string' && v !== '' ? v : null;
}

/**
 * El cuerpo del contrato desde los valores del formulario (por ruta) y los archivos ya subidos (por ruta, de
 * `subirArchivosDe`). Lleva TODO input del contrato: el que la matriz no usa va a `null`, porque el motor
 * responde 400 si falta uno. Un FILE viaja como su referencia subida `{ filename, tempPath, contentType }`.
 */
export function cuerpoDelContrato(
  valores: ValoresDelFormulario,
  _subidos: Readonly<Record<string, never>> = {},
): CuerpoDelContrato {
  return {
    mensaje: texto(valores["mensaje"]),
  };
}
