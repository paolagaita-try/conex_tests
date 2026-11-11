/**
 * Aritmética de fechas del `Calendario` — SIN zona horaria.
 *
 * Una fecha de negocio (la de inicio de un permiso, la vigencia de un parámetro) es un día del calendario,
 * no un instante. Por eso se opera con `{a, m, d}` enteros y `Date.UTC`, y nunca con
 * `new Date('aaaa-mm-dd')` leído en hora local: en una zona GMT-4 ese 2 de octubre es el 1 a
 * las 20:00, y el calendario pintaría el día anterior.
 *
 * La semana va de lunes a domingo, como el calendario aprobado. En pantalla la
 * fecha se escribe `dd/mm/aaaa`; al contrato viaja en ISO `aaaa-mm-dd`, el mismo valor que hoy
 * entrega `Entrada tipo="date"`.
 */

/** Un día del calendario. `m` va de 1 a 12. */
export interface Dia {
  a: number;
  m: number;
  d: number;
}

/**
 * Lo que restringe la elección, recibido COMO DATO : leerlo de los
 * parámetros es de la pantalla, no del componente.
 */
/** Un día de la semana: 0 = domingo … 6 = sábado. Un tipo cerrado: un número cualquiera no es un día. */
export type DiaDeLaSemana = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export interface Restricciones {
  /** ISO `aaaa-mm-dd`, incluido. */
  minimo?: string;
  /** ISO `aaaa-mm-dd`, incluido. */
  maximo?: string;
  noHabiles?: {
    /** 0 = domingo … 6 = sábado. */
    diasDeLaSemana?: readonly DiaDeLaSemana[];
    /** Feriados, en ISO. */
    fechas?: readonly string[];
  };
}

export type MotivoNoElegible = 'antes' | 'despues' | 'no-habil';

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
] as const;

/** Índice 0 = domingo, como `Date.getUTCDay()`. */
export const DIAS_DE_LA_SEMANA = [
  'domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado',
] as const;

const MS_POR_DIA = 86_400_000;

function aNumero(dia: Dia): number {
  return Date.UTC(dia.a, dia.m - 1, dia.d) / MS_POR_DIA;
}

function deNumero(n: number): Dia {
  const f = new Date(n * MS_POR_DIA);
  return { a: f.getUTCFullYear(), m: f.getUTCMonth() + 1, d: f.getUTCDate() };
}

function diasDelMes(a: number, m: number): number {
  return new Date(Date.UTC(a, m, 0)).getUTCDate();
}

/** El día existe en el calendario (no hay 31 de febrero ni mes 13). */
function crear(a: number, m: number, d: number): Dia | null {
  if (!Number.isInteger(a) || !Number.isInteger(m) || !Number.isInteger(d)) return null;
  if (m < 1 || m > 12 || d < 1 || d > diasDelMes(a, m)) return null;
  return { a, m, d };
}

const dos = (n: number) => String(n).padStart(2, '0');

/** Lo que escribe la persona: `dd/mm/aaaa` (día y mes admiten una cifra). */
export function deTexto(texto: string): Dia | null {
  const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(texto.trim());
  return m ? crear(Number(m[3]), Number(m[2]), Number(m[1])) : null;
}

export function aTexto(dia: Dia): string {
  return `${dos(dia.d)}/${dos(dia.m)}/${dia.a}`;
}

/** El valor del contrato: `aaaa-mm-dd`. */
export function deIso(iso: string): Dia | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  return m ? crear(Number(m[1]), Number(m[2]), Number(m[3])) : null;
}

export function aIso(dia: Dia): string {
  return `${dia.a}-${dos(dia.m)}-${dos(dia.d)}`;
}

export function iguales(x: Dia, y: Dia): boolean {
  return x.a === y.a && x.m === y.m && x.d === y.d;
}

/** Negativo si `x` va antes que `y`, 0 si son el mismo día. */
export function comparar(x: Dia, y: Dia): number {
  return aNumero(x) - aNumero(y);
}

/** 0 = domingo … 6 = sábado. */
/** Los días de la semana en el orden de `getUTCDay()`: indexar aquí da el tipo cerrado sin forjarlo con un `as`. */
const INDICES_DE_DIA = [0, 1, 2, 3, 4, 5, 6] as const;

export function diaDeLaSemana(dia: Dia): DiaDeLaSemana {
  return INDICES_DE_DIA[new Date(Date.UTC(dia.a, dia.m - 1, dia.d)).getUTCDay()] ?? 0;
}

/** «29 sep»: el pie del calendario (diseño aprobado). */
export function diaCorto(dia: Dia): string {
  return `${dia.d} ${MESES[dia.m - 1].slice(0, 3)}`;
}

/** «4 de octubre». */
export function diaYMes(dia: Dia): string {
  return `${dia.d} de ${MESES[dia.m - 1]}`;
}

/** «4 de octubre de 2026». */
export function fechaLarga(dia: Dia): string {
  return `${diaYMes(dia)} de ${dia.a}`;
}

/** «viernes, 2 de octubre de 2026»: el nombre accesible de un día de la rejilla. */
export function nombreCompleto(dia: Dia): string {
  return `${DIAS_DE_LA_SEMANA[diaDeLaSemana(dia)]}, ${fechaLarga(dia)}`;
}

/** «octubre de 2026»: la cabecera del mes. */
export function nombreDelMes(a: number, m: number): string {
  return `${MESES[m - 1]} de ${a}`;
}

export function sumarDias(dia: Dia, n: number): Dia {
  return deNumero(aNumero(dia) + n);
}

/** Suma meses conservando el día, recortado al último del mes destino (31 ene + 1 → 28 feb). */
export function sumarMeses(dia: Dia, n: number): Dia {
  const total = dia.a * 12 + (dia.m - 1) + n;
  const a = Math.floor(total / 12);
  const m = total - a * 12 + 1;
  return { a, m, d: Math.min(dia.d, diasDelMes(a, m)) };
}

/** El lunes de su semana. */
export function inicioDeSemana(dia: Dia): Dia {
  return sumarDias(dia, -((diaDeLaSemana(dia) + 6) % 7));
}

/** El domingo de su semana. */
export function finDeSemana(dia: Dia): Dia {
  return sumarDias(inicioDeSemana(dia), 6);
}

/** Las semanas (lunes–domingo) que pintan el mes, con los días de los meses vecinos. */
export function rejillaDelMes(a: number, m: number): Dia[][] {
  const ultimo = { a, m, d: diasDelMes(a, m) };
  const semanas: Dia[][] = [];
  for (let lunes = inicioDeSemana({ a, m, d: 1 }); comparar(lunes, ultimo) <= 0; lunes = sumarDias(lunes, 7)) {
    semanas.push(Array.from({ length: 7 }, (_, i) => sumarDias(lunes, i)));
  }
  return semanas;
}

/** Por qué un día no se puede elegir, o `null` si se puede. El rango se mira antes que lo hábil. */
export function motivoNoElegible(dia: Dia, r: Restricciones): MotivoNoElegible | null {
  const minimo = r.minimo ? deIso(r.minimo) : null;
  const maximo = r.maximo ? deIso(r.maximo) : null;
  if (minimo && comparar(dia, minimo) < 0) return 'antes';
  if (maximo && comparar(dia, maximo) > 0) return 'despues';
  if (r.noHabiles?.diasDeLaSemana?.includes(diaDeLaSemana(dia))) return 'no-habil';
  if (r.noHabiles?.fechas?.includes(aIso(dia))) return 'no-habil';
  return null;
}

export const MENSAJE_FORMATO = 'Escribe la fecha como dd/mm/aaaa.';

/** El rango permitido dicho en una frase, o `null` si no hay rango. */
function mensajeDeRango(r: Restricciones): string | null {
  const minimo = r.minimo ? deIso(r.minimo) : null;
  const maximo = r.maximo ? deIso(r.maximo) : null;
  if (minimo && maximo) {
    return `Elige una fecha entre el ${fechaLarga(minimo)} y el ${fechaLarga(maximo)}.`;
  }
  if (minimo) return `Elige una fecha desde el ${fechaLarga(minimo)}.`;
  if (maximo) return `Elige una fecha hasta el ${fechaLarga(maximo)}.`;
  return null;
}

/**
 * El error de lo tecleado, o `null` si vale. El vacío no es error aquí: la obligatoriedad la
 * decide la pantalla (como en el resto de los campos del cimiento).
 */
export function mensajeDeError(texto: string, r: Restricciones): string | null {
  if (texto.trim() === '') return null;
  const dia = deTexto(texto);
  if (!dia) return MENSAJE_FORMATO;
  const motivo = motivoNoElegible(dia, r);
  if (motivo === 'antes' || motivo === 'despues') return mensajeDeRango(r);
  if (motivo === 'no-habil') {
    const deSemana = r.noHabiles?.diasDeLaSemana?.includes(diaDeLaSemana(dia));
    const cual = deSemana ? DIAS_DE_LA_SEMANA[diaDeLaSemana(dia)] : 'feriado';
    return `El ${diaYMes(dia)} es ${cual}: elige un día hábil.`;
  }
  return null;
}
