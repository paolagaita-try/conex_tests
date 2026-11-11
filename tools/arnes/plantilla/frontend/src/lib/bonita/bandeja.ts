/**
 * Consultas de la bandeja: quién soy, qué tengo por hacer, mis casos y
 * qué puedo iniciar. Las usan las dos bandejas —la interna y la de quien inicia el caso— y por eso
 * viven en el cimiento y no en la carpeta de una pantalla.
 *
 * Tres reglas, ninguna de estilo:
 *
 * 1. **Ninguna consulta sale sin filtro**. `GET /bpm/humanTask` sin `f=` devuelve las
 *    tareas de todo el mundo; `GET /bpm/case` sin `f=`, todos los casos. Aquí eso no es una
 *    convención: `consulta()` **lanza en tiempo de ejecución** si no hay filtro, y toda
 *    `peticionPaginada(...)` de la bandeja debe pasar por `consulta()` (una URL cruda no
 *    cumple la regla, la esquiva). La segunda barrera —qué se pinta— la ponen los catálogos generados de cada
 *    familia (`tareasCliente.ts`, `tareasInternas.ts`), no este fichero.
 * 2. **Un error es un error.** Estas funciones no devuelven una lista vacía cuando la API
 *    falla: propagan el `ErrorDeBonita` para que la bandeja muestre «no pudimos consultar» con
 *    *Reintentar*. Una lista vacía disfrazada de «nada pendiente» es la mentira más cómoda que
 *    puede decir una bandeja (§3.3, paso 8).
 * 3. **Se pagina por `Content-Range`**, que es donde la plataforma dice el total.
 */

import { peticion, peticionPaginada, type Pagina } from './cliente';

/** La persona de la sesión, según la propia plataforma. */
export interface Sesion {
  /** `user_id` del motor: es lo que filtra las consultas. */
  id: string;
  /** Nombre de inicio de sesión (`ana.perez`). */
  usuario: string;
  /** Nombre para saludar («Ana Analista»); cae al de inicio de sesión si no hay otro. */
  nombre: string;
  /** Cargo de la persona en Bonita (`job_title`), si lo tiene. */
  cargo?: string;
  /** Ruta del icono del usuario en Bonita (`icons/default/icon_user.png` si nunca subió uno). */
  icono?: string;
}

/** Una tarea humana tal como la lista el motor (solo lo que la bandeja usa). */
export interface TareaDeBandeja {
  id: string;
  /** El `name` del flow node del BPMN. **Nunca se pinta**: se cruza contra el catálogo. */
  name: string;
  displayName: string;
  caseId: string;
  rootCaseId: string;
  processId: string;
  state: string;
  /** `'0'` si nadie la tomó; si es otra persona, la bandeja lo dice y no ofrece botón. */
  assigned_id: string;
  /** Cuándo quedó lista: es lo que ordena y agrupa (Hoy / Ayer / Antes). */
  reached_state_date: string;
}

/** Un caso —vivo o archivado— tal como lo lista el motor. */
export interface CasoDeBandeja {
  id: string;
  state: string;
  start: string;
  end_date: string | null;
  started_by: string;
  processDefinitionId: string;
  /** En `archivedCase`, el id que tuvo el caso mientras vivía; es el que conoce el BDM. */
  sourceObjectId: string | null;
  archivado: boolean;
}

/** Una definición de proceso que la persona puede instanciar. */
export interface ProcesoIniciable {
  id: string;
  name: string;
  displayName: string;
  version: string;
}

interface SesionDelMotor {
  user_id: string;
  user_name: string;
}

interface UsuarioDelMotor {
  firstname?: string;
  lastname?: string;
  userName?: string;
  job_title?: string;
  icon?: string;
}

interface CasoDelMotor {
  id: string;
  state: string;
  start: string;
  end_date?: string | null;
  started_by: string;
  processDefinitionId: string;
  sourceObjectId?: string | null;
}

/** Tamaño de página por defecto: el de la Task List nativa. */
export const POR_PAGINA = 20;

/**
 * Compone la consulta de un recurso con sus filtros. **Exige al menos uno**: una
 * consulta sin filtro no es un descuido, es una lista de todo lo de todos.
 */
export function consulta(
  recurso: string,
  filtros: Record<string, string>,
  opciones: { pagina?: number; porPagina?: number; orden?: string; despliega?: string[] } = {},
): string {
  const entradas = Object.entries(filtros).filter(([, v]) => v !== undefined && v !== '');
  if (entradas.length === 0) {
    throw new Error(`Consulta sin filtro a ${recurso}: la bandeja no lista lo de todo el mundo`);
  }
  const partes = [
    `p=${opciones.pagina ?? 0}`,
    `c=${opciones.porPagina ?? POR_PAGINA}`,
    ...entradas.map(([k, v]) => `f=${encodeURIComponent(`${k}=${v}`)}`),
    ...(opciones.despliega ?? []).map((d) => `d=${encodeURIComponent(d)}`),
  ];
  if (opciones.orden) partes.push(`o=${encodeURIComponent(opciones.orden)}`);
  return `${recurso}?${partes.join('&')}`;
}

/** Quién está en la sesión. Sin sesión, la plataforma responde 401 y eso se propaga. */
export async function quienSoy(): Promise<Sesion> {
  const sesion = await peticion<SesionDelMotor>('/system/session/unusedId');
  const id = String(sesion.user_id);
  let nombre = sesion.user_name;
  let cargo: string | undefined;
  let icono: string | undefined;
  try {
    const u = await peticion<UsuarioDelMotor>(`/identity/user/${encodeURIComponent(id)}`);
    const completo = [u?.firstname, u?.lastname].filter(Boolean).join(' ').trim();
    if (completo) nombre = completo;
    cargo = u?.job_title?.trim() || undefined;
    icono = u?.icon || undefined;
  } catch {
    // Sin permiso para leer el usuario se saluda por el nombre de sesión: no es un error.
  }
  return { id, usuario: sesion.user_name, nombre, cargo, icono };
}

/**
 * Lo que la persona tiene por hacer: las tareas **listas** del *pool* de sus actores y las
 * asignadas a ella, de la más antigua a la más reciente —lo que más espera va primero—.
 */
export async function misTareas(
  idUsuario: string,
  opciones: { pagina?: number; porPagina?: number } = {},
): Promise<Pagina<TareaDeBandeja>> {
  // Sin `o=`: el motor 2025.2-u0 responde **500** a `o=reached_state_date ASC|DESC` en
  // `humanTask` (medido con curl el 2026-09-22, en mayúsculas también), así que el orden «lo que
  // más espera va primero» se aplica aquí, sobre la página recibida. Límite declarado: ordena
  // dentro de la página (`c=20`), no entre páginas.
  const pagina = await peticionPaginada<TareaDeBandeja>(
    consulta('/bpm/humanTask', { state: 'ready', user_id: idUsuario }, { ...opciones, despliega: ['processId'] }),
  );
  const t = (v: string) => Date.parse((v ?? '').includes('T') ? v : (v ?? '').replace(' ', 'T')) || 0;
  pagina.elementos.sort((a, b) => t(a.reached_state_date) - t(b.reached_state_date));
  return pagina;
}

/** Las tareas listas de un caso, de quien sea: para decir «espera a <actor>» en Expedientes. */
export async function tareasListasDelCaso(idCaso: string): Promise<TareaDeBandeja[]> {
  const { elementos } = await peticionPaginada<TareaDeBandeja>(
    consulta('/bpm/humanTask', { state: 'ready', caseId: idCaso }, { porPagina: 5 }),
  );
  return elementos;
}

/**
 * Los casos en los que la persona participa. `cerrados` consulta los archivados, que el motor
 * guarda en un recurso distinto (`archivedCase`) con otro identificador (`sourceObjectId`).
 */
export async function misExpedientes(
  idUsuario: string,
  opciones: { cerrados?: boolean; pagina?: number; porPagina?: number } = {},
): Promise<Pagina<CasoDeBandeja>> {
  const recurso = opciones.cerrados ? '/bpm/archivedCase' : '/bpm/case';
  const { elementos, total } = await peticionPaginada<CasoDelMotor>(
    consulta(
      recurso,
      { user_id: idUsuario },
      { pagina: opciones.pagina, porPagina: opciones.porPagina, despliega: ['processDefinitionId'] },
    ),
  );
  return {
    total,
    elementos: elementos.map((c) => ({
      id: String(c.id),
      state: c.state,
      start: c.start,
      end_date: c.end_date ?? null,
      started_by: String(c.started_by),
      processDefinitionId: String(c.processDefinitionId),
      sourceObjectId: c.sourceObjectId === undefined ? null : String(c.sourceObjectId),
      archivado: Boolean(opciones.cerrados),
    })),
  };
}

/** Un actor del proceso, tal como lo lista el motor. */
export interface ActorDelProceso {
  id: string;
  name: string;
  displayName: string;
  process_id: string;
}

/** Un miembro de un actor (solo usuarios: `member_type=USER`). */
export interface MiembroDeActor {
  id: string;
  actor_id: string;
  user_id: string;
}

/** Los actores de un proceso desplegado. */
export async function actoresDelProceso(idProceso: string): Promise<ActorDelProceso[]> {
  const { elementos } = await peticionPaginada<ActorDelProceso>(
    consulta('/bpm/actor', { process_id: idProceso }, { porPagina: 50 }),
  );
  return elementos;
}

/** Los usuarios mapeados directamente a un actor (el mapeo de actores del `.conf`). */
export async function miembrosDelActor(idActor: string): Promise<MiembroDeActor[]> {
  const { elementos } = await peticionPaginada<MiembroDeActor>(
    consulta('/bpm/actorMember', { actor_id: idActor, member_type: 'USER' }, { porPagina: 50 }),
  );
  return elementos;
}

/** ¿Es la persona miembro de alguno de estos actores? Pura: recibe lo ya consultado. */
export function perteneceAAlgunActor(
  idUsuario: string,
  actores: readonly ActorDelProceso[],
  miembrosPorActor: ReadonlyMap<string, readonly MiembroDeActor[]>,
  nombresDeActor: readonly string[],
): boolean {
  const buscados = new Set(nombresDeActor);
  return actores.some(
    (a) =>
      buscados.has(a.name) &&
      (miembrosPorActor.get(String(a.id)) ?? []).some((m) => String(m.user_id) === idUsuario),
  );
}

/**
 * Compuerta de familia: ¿la sesión es de un actor de `nombresDeActor`?
 *
 * Si la organización tiene UN grupo y UN rol (`identity/membership` devuelve lo mismo para
 * todos), la membresía no dice nada. Lo que sí modela la familia es
 * el **mapeo de actores** del proceso, que el motor expone a cualquier usuario del perfil base
 * por `bpm/actor` (`process_visualization`) y `bpm/actorMember` (medido en 2025.2-u0 con
 * usuarios de las dos familias: 200 todos). Es una barrera de
 * presentación, no de acceso: quien conozca la URL sigue alcanzando la
 * app; lo que esta compuerta impide es que la bandeja consulte y pinte.
 */
export async function esSesionInterna(
  yo: { id: string },
  nombresDeActor: readonly string[],
): Promise<boolean> {
  const { elementos: procesos } = await peticionPaginada<ProcesoIniciable>(
    consulta('/bpm/process', { activationState: 'ENABLED' }, { porPagina: 10 }),
  );
  for (const p of procesos) {
    const actores = (await actoresDelProceso(String(p.id))).filter((a) => nombresDeActor.includes(a.name));
    const miembros = new Map<string, MiembroDeActor[]>();
    await Promise.all(actores.map(async (a) => miembros.set(String(a.id), await miembrosDelActor(String(a.id)))));
    if (perteneceAAlgunActor(yo.id, actores, miembros, nombresDeActor)) return true;
  }
  return false;
}

/** Los procesos que esta persona puede instanciar (actor iniciador y proceso habilitado). */
export async function procesosQuePuedoIniciar(idUsuario: string): Promise<ProcesoIniciable[]> {
  const { elementos } = await peticionPaginada<ProcesoIniciable>(
    consulta('/bpm/process', { user_id: idUsuario, activationState: 'ENABLED' }, { porPagina: 10 }),
  );
  return elementos;
}
