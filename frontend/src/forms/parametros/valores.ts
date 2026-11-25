/**
 * Validar y escribir el valor de un parámetro: lo que la persona teclea se lee como
 * TEXTO canónico («30», «1500000.5»), se comprueba contra el rango y los decimales de la definición y
 * viaja al kit como texto. El kit vuelve a validar (`Validacion.valor`): esto evita un viaje y dice el
 * rango en lenguaje de negocio.
 *
 * Aquí los números solo se COMPARAN (rango); nunca se convierten en texto: lo que se escribe sale de
 * `valorLegible`, que trabaja el texto canónico.
 */
import { valorLegible, valorParaEditar } from './formatos';
import type { Definicion } from './tipos';

export type ValidacionDeValor = { ok: true; canonico: string } | { ok: false; mensaje: string };

const SOLO_NUMEROS = 'Escribe solo números, con punto para los decimales.';
const ENTERO_SOLAMENTE = 'Escribe un número entero.';

const DECIMALES_EN_PALABRAS = ['sin decimales', 'un decimal', 'dos decimales', 'tres decimales', 'cuatro decimales', 'cinco decimales'] as const;

const esNumerico = (d: Pick<Definicion, 'tipoDato'>): boolean => ['ENTERO', 'DECIMAL', 'PORCENTAJE', 'MONTO'].includes(d.tipoDato);

/** «Entre 20 % y 60 %, con un decimal como máximo.»: lo permitido, con la unidad a la vista. */
export function rangoLegible(d: Definicion): string {
  const partes: string[] = [];
  if (d.minimo !== null && d.maximo !== null) partes.push(`Entre ${valorLegible(d, d.minimo)} y ${valorLegible(d, d.maximo)}`);
  else if (d.minimo !== null) partes.push(`Como mínimo ${valorLegible(d, d.minimo)}`);
  else if (d.maximo !== null) partes.push(`Como máximo ${valorLegible(d, d.maximo)}`);
  if (d.decimales !== null && d.tipoDato !== 'ENTERO') {
    const palabras = DECIMALES_EN_PALABRAS[d.decimales];
    partes.push(d.decimales === 0 ? 'sin decimales' : `con ${palabras} como máximo`);
  }
  return partes.length === 0 ? '' : `${partes.join(', ')}.`;
}

/** Lee lo tecleado: miles con «,» y punto decimal. «2.350.000» no se adivina. */
function aCanonico(texto: string): string | null {
  const t = texto.trim();
  if (/^-?\d+(\.\d+)?$/.test(t)) return t;
  if (/^-?\d{1,3}(,\d{3})+(\.\d+)?$/.test(t)) return t.replace(/,/g, '');
  return null;
}

export function validarValor(d: Definicion, entrada: string): ValidacionDeValor {
  const t = entrada.trim();
  if (t === '') return { ok: false, mensaje: 'Escribe el nuevo valor.' };
  if (d.tipoDato === 'TEXTO') return { ok: true, canonico: t };
  if (d.tipoDato === 'BOOLEANO') return t === 'true' || t === 'false' ? { ok: true, canonico: t } : { ok: false, mensaje: 'Elige sí o no.' };
  if (d.tipoDato === 'FECHA') return /^\d{4}-\d{2}-\d{2}$/.test(t) ? { ok: true, canonico: t } : { ok: false, mensaje: 'Elige una fecha válida.' };
  if (!esNumerico(d)) return { ok: false, mensaje: SOLO_NUMEROS };

  const canonico = aCanonico(t);
  if (canonico === null) return { ok: false, mensaje: SOLO_NUMEROS };
  const decimalesEscritos = canonico.split('.')[1]?.length ?? 0;
  if (d.tipoDato === 'ENTERO' && decimalesEscritos > 0) return { ok: false, mensaje: ENTERO_SOLAMENTE };
  const fueraDeDecimales = d.decimales !== null && decimalesEscritos > d.decimales;
  const n = Number(canonico);
  const fueraDeRango = (d.minimo !== null && n < Number(d.minimo)) || (d.maximo !== null && n > Number(d.maximo));
  if (fueraDeRango || fueraDeDecimales) {
    return { ok: false, mensaje: rangoLegible(d) || SOLO_NUMEROS };
  }
  return { ok: true, canonico };
}

/** El valor para el campo de edición: sin unidad ni ceros finales. */
export const valorDeEdicion = valorParaEditar;
