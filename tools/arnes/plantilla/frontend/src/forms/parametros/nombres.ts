/**
 * Los nombres que la aplicación enseña: lenguaje de negocio, nunca el `name` de un
 * proceso o de una tarea del motor como dato principal.
 *
 * - Un proceso o una actividad que el catálogo conoce se enseña con su título de negocio.
 * - Los que no (un proceso recién desplegado, un nodo sin pantalla) se enseñan LIMPIOS: sin el código de
 *   fase («F7 »), sin lo que va entre paréntesis (actor, conector) y con la primera en mayúscula. Los
 *   nombres del motor van sin tildes; no se inventan.
 */
import { TODO } from './tipos';

/**
 * Procesos conocidos: nombre del motor → título de negocio. Vacío en la plantilla: el proyecto añade aquí un proceso
 * cuyo nombre del motor no se lea bien limpio. Un proceso nuevo no necesita entrar aquí.
 */
const PROCESOS_CONOCIDOS: Readonly<Record<string, string>> = {};

/** Quita el código de fase y los paréntesis de un nombre del motor, y deja la primera en mayúscula. */
export function limpiarNombreDelMotor(nombre: string): string {
  const sinCodigo = nombre.replace(/^F\d+(?:-F\d+)?[a-z]?\s+/i, '');
  const sinParentesis = sinCodigo.replace(/\s*\([^)]*\)\s*$/, '').trim();
  const base = sinParentesis || nombre.trim();
  return base.charAt(0).toUpperCase() + base.slice(1);
}

export function nombreDeProceso(proceso: string): string {
  if (proceso === TODO) return 'Globales';
  return PROCESOS_CONOCIDOS[proceso] ?? limpiarNombreDelMotor(proceso.replace(/[_]+/g, ' '));
}

/** Un nodo técnico del motor (inicio, fin) no es una actividad en la que alguien trabaje: no se ofrece para delegar ni para una versión propia. */
export function esNodoTecnico(actividad: string): boolean {
  const limpio = limpiarNombreDelMotor(actividad).toLowerCase().trim();
  return limpio === 'fin' || limpio === 'inicio' || /,\s*fin$/.test(limpio) || /^fin\b/.test(limpio);
}

export function nombreDeActividad(actividad: string): string {
  if (actividad === TODO) return 'Todo el proceso';
  return limpiarNombreDelMotor(actividad);
}

/** «Becas de estudio · Preparar pago»: el ámbito completo, para una línea. */
export function nombreDeAmbito(proceso: string, actividad: string): string {
  if (proceso === TODO) return 'Globales';
  if (actividad === TODO) return [nombreDeProceso(proceso), 'todo el proceso'].join(' · ');
  return [nombreDeProceso(proceso), nombreDeActividad(actividad)].join(' · ');
}

/** Roles técnicos de la organización → nombre de negocio: «member» no es un rol que alguien elija. */
const ROLES_CONOCIDOS: Readonly<Record<string, string>> = {
  member: 'Miembro',
  superAdministradorParametros: 'Superadministración de parámetros',
};

/** «jefeEvaluacion» → «Jefe evaluacion»; «member» → «Miembro». Un nombre que ya se lee bien se respeta. */
export function nombreDeRol(rol: string): string {
  const conocido = ROLES_CONOCIDOS[rol];
  if (conocido) return conocido;
  const partido = rol.replace(/([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])/g, '$1 $2').replace(/[_-]+/g, ' ').trim();
  const bajo = partido === partido.toUpperCase() ? partido : partido.charAt(0).toUpperCase() + partido.slice(1).toLowerCase();
  return bajo;
}

/** «/academia/evaluacion/curso» → «Academia › Evaluacion › Curso»: la ruta de la organización no es un nombre de negocio. */
export function nombreDeGrupo(ruta: string): string {
  if (!ruta.startsWith('/')) return ruta;
  const tramos = ruta.split('/').filter(Boolean);
  return tramos.length === 0 ? ruta : tramos.map((t) => t.charAt(0).toUpperCase() + t.slice(1)).join(' › ');
}

/** El sujeto de una delegación o de un editor tal como lo sirve el kit («jefeEvaluacion en /academia/evaluacion») en lenguaje de negocio. */
export function sujetoLegible(sujeto: string): string {
  const grupoRol = /^(.+) en (\/.*)$/.exec(sujeto);
  if (grupoRol) return `${nombreDeGrupo(grupoRol[2]!)} · ${nombreDeRol(grupoRol[1]!)}`;
  return nombreDeGrupo(sujeto);
}

const LETRAS: readonly string[] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];

/**
 * Personas, grupos o roles que se leen igual NO se pueden elegir por su nombre: dos «Ana Ruiz» serían una sola
 * (la primera) y una clave repetida rompe la lista. Si un nombre se repite, cada uno se distingue con su `extra`
 * (login, ruta o nombre técnico); si aun así coinciden, con una letra. El que no se repite se queda tal cual.
 * Devuelve el mismo orden y los mismos `id`.
 */
export function etiquetasUnicas(items: ReadonlyArray<{ id: number; nombre: string; extra: string }>): Array<{ id: number; nombre: string }> {
  const veces = new Map<string, number>();
  for (const i of items) veces.set(i.nombre, (veces.get(i.nombre) ?? 0) + 1);
  const conExtra = items.map((i) => ({ id: i.id, nombre: (veces.get(i.nombre) ?? 0) > 1 && i.extra !== '' ? `${i.nombre} · ${i.extra}` : i.nombre }));
  const vistas = new Map<string, number>();
  for (const i of conExtra) vistas.set(i.nombre, (vistas.get(i.nombre) ?? 0) + 1);
  const usadas = new Map<string, number>();
  return conExtra.map((i) => {
    if ((vistas.get(i.nombre) ?? 0) <= 1) return i;
    const n = usadas.get(i.nombre) ?? 0;
    usadas.set(i.nombre, n + 1);
    return { id: i.id, nombre: `${i.nombre} · ${LETRAS[n] ?? '?'}` };
  });
}

/** Dos personas con el mismo nombre en un texto («Sara Parametros aprobó… propuesto por Sara Parametros») se distinguen por su usuario. */
export function nombresUnicos(nombres: Readonly<Record<string, string>>): Record<string, string> {
  const veces = new Map<string, number>();
  for (const n of Object.values(nombres)) veces.set(n, (veces.get(n) ?? 0) + 1);
  return Object.fromEntries(Object.entries(nombres).map(([login, n]) => [login, (veces.get(n) ?? 0) > 1 && login !== n ? `${n} (${login})` : n]));
}
