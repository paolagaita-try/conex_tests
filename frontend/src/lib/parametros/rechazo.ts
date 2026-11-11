/**
 * Cuando el servidor devuelve una tarea porque un valor ya no vale.
 *
 * ## El camino
 *
 * Al terminar la tarea, un paso del proceso (`*_validarCatalogo`) comprueba en el SERVIDOR cada valor de catálogo contra
 * lo vigente y contra el tope. Si algo ya no vale, el caso vuelve a la MISMA tarea (una instancia nueva, con el formulario
 * vacío) y deja el veredicto en el expediente. Esta pieza hace las dos cosas que la pantalla necesita al reabrirse:
 *
 *  1. **Decir por qué** — lee `GET extension/consultas/validacion?caso=` (lista cerrada: campo + motivo neutro; el servidor
 *     no manda cifras, listas ni fases) y lo traduce a una frase por campo, junto al campo.
 *  2. **No perder lo tecleado** — una tarea nueva nace vacía, así que al enviar se guarda lo tecleado en el navegador
 *     (`guardarParaReintento`) y, si el caso volvió con un rechazo, se recupera (`recuperarParaReintento`). Si NO hay
 *     rechazo, se borra (`olvidarReintento`): lo guardado solo vive mientras puede hacer falta.
 *
 * ## Qué NO hace
 *
 *  · No valida nada ni decide qué vale: el cliente solo cuenta lo que el servidor dijo. Una pantalla que filtrara aquí
 *    sería la barrera «UI-only» que el módulo de parámetros prohíbe.
 *  · No lee las variables del proceso ni el BDM: es una consulta de la extensión.
 *  · No persiste archivos ni objetos: solo valores escalares (misma regla que el borrador de una captura, y por la misma razón).
 *  · Si la consulta falla NO inventa un «todo bien»: devuelve `null` (no se pudo comprobar) y la pantalla lo dice.
 *
 * ## Privacidad de lo guardado
 *
 * Valores tecleados, nada más, con caducidad corta (`VIGENCIA_REINTENTO_HORAS`) y barrido por criterio al abrir. Un
 * reintento dura lo que tarda una persona en volver a la tarea que le devolvieron, no un día.
 */

import { peticion, TIEMPO_MAXIMO_DE_CONSULTA_MS } from '$lib/bonita/cliente';
import type { ValoresDelFormulario } from '$lib/ui/valores';

/** Los motivos con los que el servidor devuelve un valor (vocabulario cerrado, `ConsultaValidacion.MOTIVOS`). */
export const MOTIVOS = ['sin-elegir', 'no-vigente', 'sobre-tope', 'sin-comprobar'] as const;
export type Motivo = (typeof MOTIVOS)[number];

export interface Rechazo {
  /** Campo del contrato (`plazoAprobado`), o vacío si el servidor no pudo decir cuál. */
  readonly campo: string;
  readonly motivo: Motivo;
}

const RECURSO = '/extension/consultas/validacion';

/** ¿Es esto una respuesta con la forma exacta? Una forma inesperada no es «sin rechazos»: es «no se pudo comprobar». */
export function entenderRechazos(crudo: unknown): readonly Rechazo[] | null {
  if (!crudo || typeof crudo !== 'object' || Array.isArray(crudo)) return null;
  const filas = (crudo as { rechazos?: unknown }).rechazos;
  if (!Array.isArray(filas)) return null;
  const salida: Rechazo[] = [];
  for (const f of filas) {
    if (!f || typeof f !== 'object') return null;
    const { campo, motivo } = f as { campo?: unknown; motivo?: unknown };
    if (typeof campo !== 'string' || typeof motivo !== 'string') return null;
    if (!(MOTIVOS as readonly string[]).includes(motivo)) return null;
    salida.push({ campo, motivo: motivo as Motivo });
  }
  return salida;
}

/**
 * Lo que el servidor dice de la última validación de este caso: la lista de rechazos (vacía = nada que avisar) o `null` si
 * no se pudo comprobar (sin caso, sin respuesta, error del servidor, forma inesperada).
 */
export async function leerRechazos(idCaso: string | undefined | null): Promise<readonly Rechazo[] | null> {
  if (!idCaso) return null;
  try {
    const crudo = await peticion<unknown>(`${RECURSO}?caso=${encodeURIComponent(idCaso)}`, {
      tiempoMaximoMs: TIEMPO_MAXIMO_DE_CONSULTA_MS,
    });
    return entenderRechazos(crudo);
  } catch {
    return null;
  }
}

/** La frase de un rechazo. Neutra por diseño: no nombra listas, umbrales, fases ni cifras. */
export function textoDelRechazo(motivo: Motivo, etiqueta?: string): string {
  const campo = etiqueta ? `«${etiqueta}»` : 'un campo';
  switch (motivo) {
    case 'sin-elegir':
      return `Elija una opción en ${campo}.`;
    case 'no-vigente':
      return `La opción elegida en ${campo} ya no está disponible. Elija otra.`;
    case 'sobre-tope':
      return `El valor de ${campo} supera el máximo permitido para la opción elegida. Ajústelo.`;
    case 'sin-comprobar':
      return `No se pudo comprobar ${campo}. Revise el valor y vuelva a enviar.`;
  }
}

export interface RechazosParaLaPantalla {
  /** El motivo por campo del formulario, con la ruta `grupo.campo` que usa `CamposDeContrato` (que pone la frase junto al campo). */
  readonly porRuta: Record<string, Motivo>;
  /** Las frases que no se pudieron atar a un campo de ESTA pantalla (campo vacío o desconocido), sin repetirse. */
  readonly generales: readonly string[];
}

/** Ata cada rechazo a su campo por el nombre del contrato (`plazoAprobado` ↔ `decision.plazoAprobado`). */
export function rechazosParaLaPantalla(rechazos: readonly Rechazo[], rutas: readonly string[]): RechazosParaLaPantalla {
  const porRuta: Record<string, Motivo> = {};
  const generales: string[] = [];
  for (const r of rechazos) {
    const ruta = rutas.find((k) => r.campo !== '' && k.split('.').pop() === r.campo);
    if (ruta === undefined) {
      const frase = textoDelRechazo(r.motivo);
      if (!generales.includes(frase)) generales.push(frase);
    } else {
      porRuta[ruta] = r.motivo;
    }
  }
  return { porRuta, generales };
}

// ─── Lo tecleado, mientras puede hacer falta ───────────────────────────────────────────────────────

/** Cuánto vive lo guardado. Es el tiempo de volver a la tarea devuelta, no de un borrador de trabajo. */
export const VIGENCIA_REINTENTO_HORAS = 2;
const VIGENCIA_REINTENTO_MS = VIGENCIA_REINTENTO_HORAS * 3_600_000;
const PREFIJO = 'ep033-reintento-';

interface Guardado {
  valores: ValoresDelFormulario;
  guardadoEn: string;
}

function clave(tarea: string, caso: string): string {
  return `${PREFIJO}${tarea}-${caso}`;
}

function almacen(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

function escalares(valores: ValoresDelFormulario): ValoresDelFormulario {
  const limpio: ValoresDelFormulario = {};
  for (const [k, v] of Object.entries(valores)) {
    if (v === null || ['string', 'number', 'boolean'].includes(typeof v)) limpio[k] = v;
  }
  return limpio;
}

/** Sin predicado de tipo: uno pondría una marca sin copiar una ruta, y eso blanquearía la cifra. */
function esGuardadoValido(v: unknown): boolean {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return false;
  const g = v as Record<string, unknown>;
  if (Object.keys(g).sort().join() !== 'guardadoEn,valores') return false;
  if (typeof g.valores !== 'object' || g.valores === null || Array.isArray(g.valores)) return false;
  if (!Object.values(g.valores as Record<string, unknown>).every((x) => x === null || ['string', 'number', 'boolean'].includes(typeof x))) {
    return false;
  }
  return typeof g.guardadoEn === 'string' && !Number.isNaN(Date.parse(g.guardadoEn));
}

function vigente(guardadoEn: string, ahora: number): boolean {
  const marca = Date.parse(guardadoEn);
  return !Number.isNaN(marca) && marca <= ahora && ahora - marca < VIGENCIA_REINTENTO_MS;
}

/** Guarda lo tecleado al enviar. Silencioso ante cualquier fallo: no guardarlo no debe romper el envío. */
export function guardarParaReintento(tarea: string, caso: string | undefined | null, valores: ValoresDelFormulario): boolean {
  const s = almacen();
  if (!s || !caso) return false;
  try {
    s.setItem(clave(tarea, caso), JSON.stringify({ valores: escalares(valores), guardadoEn: new Date().toISOString() }));
    return true;
  } catch {
    return false;
  }
}

/** Lo guardado de este caso y esta tarea, o `null` si no hay, no tiene la forma o caducó (y entonces se borra). */
export function recuperarParaReintento(tarea: string, caso: string | undefined | null): ValoresDelFormulario | null {
  const s = almacen();
  if (!s || !caso) return null;
  try {
    const bruto = s.getItem(clave(tarea, caso));
    if (!bruto) return null;
    const leido: unknown = JSON.parse(bruto);
    if (esGuardadoValido(leido) && vigente(String((leido as { guardadoEn?: unknown }).guardadoEn), Date.now())) return (leido as Guardado).valores;
  } catch {
    /* ilegible: se borra abajo */
  }
  olvidarReintento(tarea, caso);
  return null;
}

/** Borra lo guardado de este caso y esta tarea (cuando no hay rechazo que lo justifique). */
export function olvidarReintento(tarea: string, caso: string | undefined | null): void {
  const s = almacen();
  if (!s || !caso) return;
  try {
    s.removeItem(clave(tarea, caso));
  } catch {
    /* nada que hacer */
  }
}

/** Barrido por criterio al abrir: mueren los caducados y los ilegibles; el vigente de otro caso sobrevive. */
export function purgarReintentos(): number {
  const s = almacen();
  if (!s) return 0;
  let limpiadas = 0;
  try {
    const ahora = Date.now();
    const claves: string[] = [];
    for (let i = 0; i < s.length; i++) {
      const k = s.key(i);
      if (k && k.startsWith(PREFIJO)) claves.push(k);
    }
    for (const k of claves) {
      let vive = false;
      try {
        const leido: unknown = JSON.parse(s.getItem(k) ?? '');
        vive = esGuardadoValido(leido) && vigente(String((leido as { guardadoEn?: unknown }).guardadoEn), ahora);
      } catch {
        vive = false;
      }
      if (!vive) {
        s.removeItem(k);
        limpiadas++;
      }
    }
  } catch {
    /* un almacenamiento inaccesible no rompe la pantalla */
  }
  return limpiadas;
}

// ─── Lo que una pantalla hace al abrirse ────────────────────────────────────────────────────────────

/** La frase cuando no se pudo saber si la tarea volvió: honesta y sin alarmar. */
export const FRASE_SIN_COMPROBAR =
  'No se pudo comprobar si esta tarea volvió por algún valor. Revise todos los campos antes de enviar.';

/** El título del aviso cuando la tarea volvió. */
export const TITULO_DEVUELTA = 'Esta tarea volvió para revisar algunos valores';

export interface AperturaDeTarea {
  /** `devuelta`: el servidor la devolvió; `normal`: no hay rechazo; `sin-comprobar`: no se pudo preguntar. */
  readonly estado: 'normal' | 'devuelta' | 'sin-comprobar';
  /** `estado === 'devuelta'`, ya resuelto: las pantallas con un catálogo cerrado de textos no escriben literales. */
  readonly devuelta: boolean;
  /** `estado === 'sin-comprobar'`. */
  readonly sinComprobar: boolean;
  /** Los valores a pintar: los iniciales, o los tecleados antes si la tarea volvió. Solo claves que la pantalla ya tiene. */
  readonly valores: ValoresDelFormulario;
  readonly motivos: Record<string, Motivo>;
  readonly generales: readonly string[];
}

/**
 * Lo que hace una pantalla al abrir su tarea: barrer lo caducado, preguntar al servidor y decidir si recupera lo tecleado.
 * Una sola lectura (no se re-lee después: una respuesta tardía no pisa lo que la persona ya escribió).
 */
export async function abrirTareaConRechazo(args: {
  readonly tarea: string;
  readonly caso: string | undefined | null;
  /** Las rutas `grupo.campo` que esta pantalla pinta: solo ellas se recuperan y solo a ellas se ata un rechazo. */
  readonly rutas: readonly string[];
  readonly iniciales: ValoresDelFormulario;
}): Promise<AperturaDeTarea> {
  purgarReintentos();
  const rechazos = await leerRechazos(args.caso);
  if (rechazos === null) return { estado: 'sin-comprobar', devuelta: false, sinComprobar: true, valores: args.iniciales, motivos: {}, generales: [FRASE_SIN_COMPROBAR] };
  if (rechazos.length === 0) {
    olvidarReintento(args.tarea, args.caso);
    return { estado: 'normal', devuelta: false, sinComprobar: false, valores: args.iniciales, motivos: {}, generales: [] };
  }
  const guardados = recuperarParaReintento(args.tarea, args.caso) ?? {};
  const valores: ValoresDelFormulario = { ...args.iniciales };
  for (const k of args.rutas) if (k in guardados) valores[k] = guardados[k];
  const { porRuta, generales } = rechazosParaLaPantalla(rechazos, args.rutas);
  return { estado: 'devuelta', devuelta: true, sinComprobar: false, valores, motivos: porRuta, generales };
}
