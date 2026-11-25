/**
 * Cómo se escribe un valor de parámetro y una fecha en esta aplicación.
 *
 * Los valores llegan como TEXTO canónico del kit (`"35"`, `"1500000.00"`, `"2026-10-31"`) y se
 * escriben con operaciones de texto: la auditoría del origen de las cifras no admite que
 * una pantalla convierta un número en texto, y un parámetro no es una cifra del expediente sino el
 * dato que el negocio fijó. Tampoco hay `NumberFormat` ni el separador de miles de una expresión
 * regular: el cimiento es quien formatea cifras, y este módulo no lo imita (`check_formateadores_de_cifras`).
 *
 * Las fechas sí pasan por `Intl.DateTimeFormat`, que el custodio admite; son un reloj, no una cifra
 * (entradas de `NO_SON_CIFRAS` de este fichero).
 */
import { SIN_DATO } from '$lib/ui/formato';
import type { Definicion } from './tipos';

/** La moneda por defecto de un monto cuando la definición no declara su unidad. */
const MONEDA = 'US$';
/** El kit sirve el código de la moneda («USD»); el negocio la lee con su símbolo. Una desconocida se enseña tal cual, separada. */
const SIMBOLOS_DE_MONEDA: Readonly<Record<string, string>> = { USD: 'US$', EUR: '€' };
export function simboloDeMoneda(unidad: string | null | undefined): string {
  if (!unidad) return MONEDA;
  return SIMBOLOS_DE_MONEDA[unidad.toUpperCase()] ?? (/^[A-Za-z]+$/.test(unidad) ? `${unidad} ` : unidad);
}
const SIMBOLO_DE_PORCENTAJE = '%';
const UNA_MILESIMA = 3;

/** «1500000» → «1,500,000» sin expresiones regulares ni números: se corta de a tres desde la derecha. */
function agrupar(entero: string): string {
  const grupos: string[] = [];
  for (let fin = entero.length; fin > 0; fin -= UNA_MILESIMA) {
    grupos.unshift(entero.slice(Math.max(0, fin - UNA_MILESIMA), fin));
  }
  return grupos.join(',');
}

/** El número canónico escrito para leerse: miles agrupados y sin ceros finales en los decimales. */
export function numeroLegible(canonico: string): string {
  const negativo = canonico.startsWith('-');
  const [entero, fraccion = ''] = (negativo ? canonico.slice(1) : canonico).split('.');
  const util = fraccion.replace(/0+$/, '');
  const cuerpo = util ? `${agrupar(entero)}.${util}` : agrupar(entero);
  return negativo ? `-${cuerpo}` : cuerpo;
}

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'] as const;

/** «2026-10-31» → «31 oct 2026». Lo que no es una fecha canónica se devuelve tal cual. */
export function fechaLegible(canonica: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(canonica);
  if (!m) return canonica;
  const mes = MESES[Number(m[2]) - 1];
  if (!mes) return canonica;
  return [m[3].replace(/^0/, ''), mes, m[1]].join(' ');
}

/** Un valor de parámetro como lo lee el negocio: «35 %», «US$1,500,000», «36 semanas», «31 oct 2026». */
export function valorLegible(definicion: Pick<Definicion, 'tipoDato' | 'unidad'>, valor: string | null): string {
  if (valor === null || valor === '') return SIN_DATO;
  // Una imagen guardada como `data:` (el logo de la marca) no se lee como texto: decenas de miles de caracteres de
  // base64 rompen la ficha, la lista y el historial. Se dice qué es (sin cifras: el peso no cambia ninguna decisión).
  const imagen = /^data:image\/(png|svg\+xml);base64,/.exec(valor);
  if (imagen) return `Imagen cargada · ${imagen[1] === 'png' ? 'PNG' : 'SVG'}`;
  switch (definicion.tipoDato) {
    case 'PORCENTAJE':
      return [numeroLegible(valor), definicion.unidad ?? SIMBOLO_DE_PORCENTAJE].join(' ');
    case 'MONTO':
      // La moneda va pegada al número y viene de la definición: es un dato, no una plantilla.
      return [simboloDeMoneda(definicion.unidad), numeroLegible(valor)].join('');
    case 'ENTERO':
    case 'DECIMAL':
      return definicion.unidad ? [numeroLegible(valor), definicion.unidad].join(' ') : numeroLegible(valor);
    case 'FECHA':
      return fechaLegible(valor);
    case 'BOOLEANO':
      return valor === 'true' ? 'Sí' : 'No';
    default:
      return valor;
  }
}

/** Solo el número (sin unidad), para un campo de edición: «35», «1500000». */
export function valorParaEditar(valor: string | null): string {
  if (valor === null) return '';
  return valor.includes('.') ? valor.replace(/\.?0+$/, '') : valor;
}

// ─── Fechas y horas ──────────────────────────────────────────────────────────────────────────────

const FECHA_NUMERICA = new Intl.DateTimeFormat('es-US', { day: 'numeric', month: 'numeric', year: 'numeric' });
const HORA = new Intl.DateTimeFormat('es-US', { hour: '2-digit', minute: '2-digit', hour12: false });

/**
 * El ÚNICO sitio donde una hora se vuelve texto en esta aplicación: un reloj, no una cifra del expediente
 * (entrada de `NO_SON_CIFRAS` para este fichero).
 */
function escribir(formato: Intl.DateTimeFormat, fecha: Date): string {
  return formato.format(fecha);
}

/**
 * El día, el mes (siempre «ene…dic», igual que el diseño aprobado, y no la abreviatura de cada ICU) y el año de una fecha,
 * leídos de sus partes: nunca se convierte un número en texto.
 */
function partesDeLaFecha(fecha: Date): { dia: string; mes: string; anio: string } {
  const partes = FECHA_NUMERICA.formatToParts(fecha);
  const de = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? '';
  return { dia: de('day'), mes: MESES[Number(de('month')) - 1] ?? '', anio: de('year') };
}

const leer = (iso: string): Date | null => {
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
};

/** ¿Son el mismo día del calendario? Compara partes de la fecha, sin escribir ninguna. */
function mismoDia(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** «hoy 10:31» · «3 ago» · «3 ago 2025»: cuándo, para una línea de lista. */
export function cuando(iso: string, ahora: Date = new Date()): string {
  const fecha = leer(iso);
  if (fecha === null) return iso;
  if (mismoDia(fecha, ahora)) return ['hoy', escribir(HORA, fecha)].join(' ');
  const { dia, mes, anio } = partesDeLaFecha(fecha);
  return fecha.getFullYear() === ahora.getFullYear() ? [dia, mes].join(' ') : [dia, mes, anio].join(' ');
}

/** «hoy 09:12»: la hora de ahora, para decir «verificada hoy 09:12». */
export function horaDeHoy(ahora: Date = new Date()): string {
  return ['hoy', escribir(HORA, ahora)].join(' ');
}

/** «27 sep 2026 · 10:32»: cuándo, con el año y la hora, para el historial y la traza. */
export function cuandoCompleto(iso: string): string {
  const fecha = leer(iso);
  if (fecha === null) return iso;
  const { dia, mes, anio } = partesDeLaFecha(fecha);
  return [[dia, mes, anio].join(' '), escribir(HORA, fecha)].join(' · ');
}

/** «27 sep 2026» sin hora. */
export function soloFecha(iso: string): string {
  const fecha = leer(iso);
  if (fecha === null) return iso;
  const { dia, mes, anio } = partesDeLaFecha(fecha);
  return [dia, mes, anio].join(' ');
}

/** ¿Esta fecha de fin cae mañana? (para «Vence mañana»). */
export function venceManana(hastaIso: string | null, ahora: Date = new Date()): boolean {
  const hasta = hastaIso === null ? null : leer(hastaIso);
  if (hasta === null) return false;
  const manana = new Date(ahora);
  manana.setDate(manana.getDate() + 1);
  return mismoDia(hasta, manana);
}

/** El texto sin tildes y en minúsculas: para buscar «pago» y encontrar «Pagó». */
export function paraBuscar(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}
