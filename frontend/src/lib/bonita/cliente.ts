/**
 * Cliente de la API REST de Bonita.
 *
 * Núcleo heredado de la plantilla interna: gestión de sesión y del token de
 * protección contra falsificación de peticiones (CSRF), que la plataforma exige en
 * toda escritura.
 *
 * Cuando el formulario está desplegado como custom page, la sesión ya existe (la
 * abrió el portal) y el token viaja en la cookie `X-Bonita-API-Token`. En
 * desarrollo hay que autenticarse primero, y solo entonces existe el token.
 */

import {
  credencialesDeDesarrollo,
  esEntornoDeDesarrollo,
  urlApi,
  urlLogin,
} from './config';
import { avisarAlContenedor } from './marco';
import { ErrorDeBonita, type Contrato } from './tipos';
import type { Recuento } from '$lib/bonita/marcas';
import { codigoHttpDe } from '$lib/bonita/marcas';

let tokenEnMemoria: string | null = null;

/** Lee el token CSRF de la cookie que deja la plataforma. */
function tokenDeCookie(): string | null {
  if (typeof document === 'undefined') return null;
  const coincidencia = document.cookie.match(/(?:^|;\s*)X-Bonita-API-Token=([^;]+)/);
  return coincidencia ? decodeURIComponent(coincidencia[1]) : null;
}

/**
 * Obtiene el token CSRF. Prefiere la cookie (es lo que hay en producción) y, si no
 * está, lo pide a la API de sesión, que lo devuelve en una cabecera de respuesta.
 */
export async function obtenerToken(): Promise<string | null> {
  const deCookie = tokenDeCookie();
  if (deCookie) {
    tokenEnMemoria = deCookie;
    return deCookie;
  }
  if (tokenEnMemoria) return tokenEnMemoria;

  const respuesta = await fetch(urlApi('/system/session/unusedId'), {
    credentials: 'include',
  });
  if (!respuesta.ok) return null;
  tokenEnMemoria =
    respuesta.headers.get('X-Bonita-API-Token') ?? tokenDeCookie() ?? null;
  return tokenEnMemoria;
}

/** Descarta el token en memoria (por ejemplo, tras un 401). */
export function olvidarToken(): void {
  tokenEnMemoria = null;
}

interface OpcionesDePeticion {
  metodo?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  cuerpo?: unknown;
  /** Las escrituras exigen el token CSRF; las lecturas no. */
  requiereToken?: boolean;
  /**
   * Tiempo máximo de espera. Sin él, una petición colgada dejaba la
   * pantalla cargando para siempre, sin aviso. Con él, la petición se corta al vencer y **todo**
   * fallo de transporte —red caída o servidor que no contesta— sale como `ErrorDeBonita` con
   * estado 0 («sin respuesta»), para que la pantalla lo diga en vez de confundirlo con «no existe».
   */
  tiempoMaximoMs?: number;
}

/**
 * Pasado este tiempo sin respuesta, una consulta se da por fallida.
 * Uno solo para las dos familias: la consulta cliente y la interna esperan lo mismo.
 */
export const TIEMPO_MAXIMO_DE_CONSULTA_MS = 15_000;

/** El error normalizado de una respuesta que no fue bien (lee el detalle del cuerpo). */
async function errorDe(recurso: string, respuesta: Response): Promise<ErrorDeBonita> {
  let detalle: unknown;
  try {
    detalle = await respuesta.json();
  } catch {
    detalle = await respuesta.text().catch(() => undefined);
  }
  return new ErrorDeBonita(
    `La API de Bonita respondió ${respuesta.status} en ${recurso}`,
    codigoHttpDe(respuesta) ?? 0,
    detalle,
  );
}

/**
 * Ejecuta una petición contra la API REST de Bonita.
 *
 * Es UNA sola función `async`, sin capas por debajo, a propósito: cada capa añade microtareas y
 * las pantallas ya construidas cuentan con que el 204 llegue en las mismas que hoy (lo midió el
 * test de una pantalla al intentar factorizar esto con la lectura paginada).
 */
export async function peticion<T>(
  recurso: string,
  opciones: OpcionesDePeticion = {},
): Promise<T> {
  const { metodo = 'GET', cuerpo, requiereToken = metodo !== 'GET', tiempoMaximoMs } = opciones;
  const cabeceras: Record<string, string> = {};

  if (requiereToken) {
    const token = await obtenerToken();
    if (token) cabeceras['X-Bonita-API-Token'] = token;
  }
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';

  const init: RequestInit = {
    method: metodo,
    credentials: 'include',
    headers: cabeceras,
    body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
  };
  let respuesta: Response;
  if (tiempoMaximoMs === undefined) {
    respuesta = await fetch(urlApi(recurso), init);
  } else {
    const controlador = new AbortController();
    const reloj = setTimeout(() => controlador.abort(), tiempoMaximoMs);
    try {
      respuesta = await fetch(urlApi(recurso), { ...init, signal: controlador.signal });
    } catch (causa) {
      throw new ErrorDeBonita(`Sin respuesta de la API de Bonita en ${recurso}`, 0, causa);
    } finally {
      clearTimeout(reloj);
    }
  }

  if (!respuesta.ok) throw await errorDe(recurso, respuesta);

  // Las ejecuciones de tarea responden 204 sin cuerpo.
  if (respuesta.status === 204) return undefined as T;
  const texto = await respuesta.text();
  return (texto ? JSON.parse(texto) : undefined) as T;
}

/** Una página de resultados y, si la plataforma lo dice, cuántos hay en total. */
export interface Pagina<T> {
  elementos: T[];
  /**
   * Total de la consulta según `Content-Range` (`p-q/total`); `null` si no vino. Es un `Recuento`:
   * lo declara la plataforma, y solo `peticionPaginada` —su lector declarado— lo marca.
   */
  total: Recuento | null;
}

/**
 * Lee una lista paginada de la API (solo lecturas: sin token). La plataforma devuelve el total
 * en la cabecera `Content-Range: 0-19/57` (doc `rest-api-overview`, «Paginación»), no en el
 * cuerpo: sin leerla, una bandeja no sabe si hay más páginas ni cuántos pendientes anunciar.
 */
export async function peticionPaginada<T>(recurso: string): Promise<Pagina<T>> {
  const respuesta = await fetch(urlApi(recurso), { credentials: 'include' });
  if (!respuesta.ok) throw await errorDe(recurso, respuesta);
  const texto = await respuesta.text();
  const cuerpo: unknown = texto ? JSON.parse(texto) : [];
  const elementos = (Array.isArray(cuerpo) ? cuerpo : []) as T[];
  const rango = respuesta.headers.get('Content-Range') ?? '';
  const total = rango.match(/\/(\d+)\s*$/);
  return { elementos, total: total ? (Number(total[1]) as Recuento) : null };
}

/**
 * Autentica en desarrollo. En producción no hace nada: la sesión es la del portal
 * y este formulario no maneja credenciales.
 */
export async function autenticarEnDesarrollo(): Promise<void> {
  if (!esEntornoDeDesarrollo()) return;
  const credenciales = credencialesDeDesarrollo();
  if (!credenciales) {
    throw new Error(
      'Faltan las credenciales de desarrollo: define VITE_BONITA_DEV_USER y ' +
        'VITE_BONITA_DEV_PASSWORD en tu .env (ver .env.example).',
    );
  }
  const cuerpo = new URLSearchParams({
    username: credenciales.usuario,
    password: credenciales.clave,
    redirect: 'false',
  });
  const respuesta = await fetch(urlLogin(), {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: cuerpo.toString(),
  });
  if (!respuesta.ok) {
    throw new ErrorDeBonita('No se pudo autenticar en Bonita', codigoHttpDe(respuesta) ?? 0);
  }
  olvidarToken();
  await obtenerToken();
}

/** ¿Hay una sesión válida ahora mismo? */
export async function haySesion(): Promise<boolean> {
  try {
    const respuesta = await fetch(urlApi('/system/session/unusedId'), {
      credentials: 'include',
    });
    return respuesta.ok;
  } catch {
    return false;
  }
}

/** Contrato de una tarea humana. */
export function contratoDeTarea(idTarea: string): Promise<Contrato> {
  return peticion<Contrato>(`/bpm/userTask/${idTarea}/contract`);
}

/** Una tarea humana, con la referencia al caso al que pertenece. */
export interface TareaHumana {
  id: string;
  name: string;
  displayName: string;
  caseId: string;
  rootCaseId: string;
  state: string;
  assigned_id: string;
}

/**
 * Lee la tarea humana para saber, entre otras cosas, **de qué caso es**.
 *
 * Hace falta porque el portal, al abrir una pantalla como formulario de su tarea, pasa
 * únicamente el `id` de la tarea en la dirección — **no el `caseId`** (medido en 2025.2-u0).
 * Sin este salto, una pantalla que necesita los datos del caso no tiene con qué encontrarlo.
 */
export function tareaHumana(idTarea: string): Promise<TareaHumana> {
  return peticion<TareaHumana>(`/bpm/humanTask/${idTarea}`);
}

/** Contrato de instanciación de un proceso. */
export function contratoDeProceso(idProceso: string): Promise<Contrato> {
  return peticion<Contrato>(`/bpm/process/${idProceso}/contract`);
}

/**
 * Ejecuta una tarea humana con el cuerpo de su contrato. `asignar` hace que la
 * plataforma asigne la tarea al usuario de la sesión antes de ejecutarla.
 *
 * Tras el 204 —y también tras un rechazo— **avisa a la bandeja que la contiene**
 * (protocolo del marco, `marco.ts`), si es que hay una: es el único punto por el que pasan todas las pantallas, así que la
 * emisión vive aquí y ningún `.svelte` tiene que acordarse. Fuera de un marco no se emite nada
 * y la pantalla sigue pintando su propio acuse.
 */
export function ejecutarTarea(
  idTarea: string,
  datos: Record<string, unknown>,
  asignar = true,
): Promise<void> {
  const sufijo = asignar ? '?assign=true' : '';
  const ejecucion = peticion<void>(`/bpm/userTask/${idTarea}/execution${sufijo}`, {
    metodo: 'POST',
    cuerpo: datos,
  });
  // La emisión cuelga de la promesa ORIGINAL como reacción lateral, y se devuelve esa misma
  // promesa: así el aviso sale en el mismo tick en que la pantalla recibe el 204 (justo antes
  // de su continuación) y **no se añade ninguna microtarea** al que llama. Envolverla en otra
  // función `async` o encadenar `.then` sí las añadía, y una pantalla ya construida lo notó:
  // su test encontraba el aviso informativo donde esperaba el de éxito
  // (medido dos veces, con cada variante). El rechazo lo sigue recibiendo la pantalla por la
  // promesa original; el manejador lateral no lo vuelve a lanzar para no duplicarlo.
  ejecucion.then(
    () => {
      avisarAlContenedor({ action: 'Submit task', message: 'success', taskId: idTarea });
    },
    (e: unknown) => {
      avisarAlContenedor({
        action: 'Submit task',
        message: 'error',
        taskId: idTarea,
        status: e instanceof ErrorDeBonita ? e.estado : undefined,
      });
    },
  );
  return ejecucion;
}

/**
 * Instancia un proceso con el cuerpo de su contrato de instanciación, y avisa a la bandeja
 * que contiene a la pantalla de arranque (mismo mecanismo que `ejecutarTarea`).
 */
export function instanciarProceso(
  idProceso: string,
  datos: Record<string, unknown>,
): Promise<{ caseId: string }> {
  const instanciacion = peticion<{ caseId: string }>(`/bpm/process/${idProceso}/instantiation`, {
    metodo: 'POST',
    cuerpo: datos,
  });
  // Misma forma que `ejecutarTarea`: reacción lateral, promesa original de vuelta.
  instanciacion.then(
    (caso) => {
      avisarAlContenedor({ action: 'Start process', message: 'success', caseId: String(caso.caseId) });
    },
    () => {
      // El rechazo lo recibe la pantalla por la promesa original; aquí no se relanza.
    },
  );
  return instanciacion;
}
