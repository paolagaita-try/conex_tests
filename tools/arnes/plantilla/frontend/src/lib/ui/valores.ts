/**
 * Lo que la persona TECLEA en un formulario, con su tipo.
 *
 * ## Por qué
 *
 * Los `valores` de cada pantalla eran `Record<string, unknown>`, y lo que hay en ellos lo pinta un `<input>`. Un número
 * escrito ahí por la pantalla —`valores['decision.diasAprobados'] = umbral`— se pintaba en el campo sin pasar por
 * ningún formato ni por ningún control de su origen: el campo no es una plantilla, y `unknown` no dice que sea un número.
 *
 * ## Cómo
 *
 * Un número solo entra en `valores` con la marca `NumeroTecleado`, y la marca solo la ponen los LECTORES de lo que la
 * persona escribió: el `<input>` de `Entrada` al enlazar su valor, `numeroTecleado()` (lo que `CampoConAfijo` lee de su
 * texto), el borrador que el navegador guardó de lo ya tecleado y, solo en la galería, sus datos de ejemplo. Un número
 * calculado no la tiene: `valores[ruta] = 25000000` no compila.
 *
 * Los widgets reciben su valor ESTRECHADO por `typeof` (`comoTexto`, `comoBooleano`…), nunca con `as`: un `as` que
 * estrecha `texto | Dinero` a `Dinero` blanquea un `'25000000'`, porque `Intl` formatea las cadenas numéricas.
 */

import type { ArchivoContrato } from '$lib/bonita/tipos';

declare const deTecleado: unique symbol;

/** Un número que TECLEÓ la persona (o que el navegador guardó de lo que tecleó). No es una cifra del expediente. */
export type NumeroTecleado = number & { readonly [deTecleado]: typeof deTecleado };

/** Lo que puede valer un campo del formulario. Un número, solo tecleado. */
export type ValorDeCampo = string | boolean | NumeroTecleado | ArchivoContrato | null | undefined;

/** Los valores del formulario por ruta (`grupo.campo`). La pantalla es dueña de su estado. */
export type ValoresDelFormulario = Record<string, ValorDeCampo>;

/** Miles con «,» bien agrupados, o sin agrupar; punto decimal (`es-US`, el `LOCALE` de `formato.ts`). «2.350.000» no se adivina. */
const NUMERO_ESCRITO = /^-?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$/;

/**
 * El LECTOR del número que la persona escribió en un texto: «2,350,000.50» → 2350000.5; lo que no es un número escrito
 * así, `null`. Es lo único, junto al `<input>`, que pone la marca.
 */
export function numeroTecleado(texto: string): NumeroTecleado | null {
  const limpio = texto.trim();
  return NUMERO_ESCRITO.test(limpio) ? (Number(limpio.replaceAll(',', '')) as NumeroTecleado) : null;
}

/** El valor de un campo de texto (o de fecha, o de una lista de opciones), para su widget. */
export function comoTexto(v: ValorDeCampo): string | null | undefined {
  return typeof v === 'string' || v === null ? v : undefined;
}

/** El valor de una `Entrada`, que puede ser de texto o numérica. */
export function comoTextoONumero(v: ValorDeCampo): string | NumeroTecleado | null | undefined {
  return typeof v === 'string' || typeof v === 'number' || v === null ? v : undefined;
}

/** El valor de una casilla. */
export function comoBooleano(v: ValorDeCampo): boolean | null | undefined {
  return typeof v === 'boolean' || v === null ? v : undefined;
}

/** El valor de una carga de archivo. */
export function comoArchivo(v: ValorDeCampo): ArchivoContrato | null | undefined {
  return typeof v === 'object' ? v : undefined;
}

/** El texto de un campo, para el contrato: la cadena que tiene, o vacío. Un número no se convierte aquí. */
export function textoDe(v: ValorDeCampo): string {
  return typeof v === 'string' ? v : '';
}

/**
 * Un número de EJEMPLO puesto en un widget como si la persona lo hubiera tecleado: solo la galería y la muestra de
 * marca, que no tienen expediente ni persona (lector con ámbito acotado). Solo admite un LITERAL
 * —`tecleadoDeEjemplo(15)`—: un número calculado no compila, así que ni dentro de su ámbito es una puerta.
 */
export function tecleadoDeEjemplo<N extends number>(n: number extends N ? never : N): NumeroTecleado {
  const literal: number = n;
  return literal as NumeroTecleado;
}
