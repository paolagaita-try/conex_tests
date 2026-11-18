/**
 * Qué puede hacer la persona de la sesión, para PINTAR. No autoriza nada: quien escribe lo
 * decide el servidor en cada petición (D7 del kit, `Autorizacion.groovy`). Aquí se reproduce su criterio
 * con lo que la API deja ver, y si no se puede decidir, la persona queda en **consulta**, que es el caso
 * más conservador. Un desfase entre esto y el servidor se traduce en un 403 explicado, nunca en un
 * permiso concedido.
 *
 * - superadministración: el rol `superAdministradorParametros` en cualquier grupo, con el nombre exacto;
 * - delegado: alguna delegación VIGENTE de `parametros/editores` que case con la persona (usuario por su
 *   nombre de inicio de sesión; grupo y rol por sus membresías; los subgrupos por la frontera «/»);
 * - consulta: el resto de la familia interna.
 */
import type { Membresia } from './kit';
import { TODO, type Editor } from './tipos';
import type { Ambito } from './ambitos';

export const ROL_DE_SUPERADMINISTRACION = 'superAdministradorParametros';

export type Perfil = 'superadministracion' | 'delegado' | 'consulta';

/** Una delegación que alcanza a la persona, tal como se enseña en «Tus permisos». */
export interface PermisoPropio {
  proceso: string;
  /** Vacío = todo el proceso. */
  actividades: string[];
  vigenteHasta: string | null;
}

export interface Capacidades {
  perfil: Perfil;
  permisos: PermisoPropio[];
}

export const CONSULTA: Capacidades = { perfil: 'consulta', permisos: [] };

export function esSuperadministracion(membresias: Membresia[]): boolean {
  return membresias.some((m) => m.rol === ROL_DE_SUPERADMINISTRACION);
}

const enGrupo = (m: Membresia, grupo: string, conSubgrupos: boolean): boolean =>
  m.grupo === grupo || (conSubgrupos && m.grupo.startsWith(`${grupo}/`));

/** ¿Esta delegación (vista por nombres) alcanza a quien tiene estas membresías? */
export function alcanzaA(e: Editor, usuario: string, membresias: Membresia[]): boolean {
  if (e.tipo === 'SUPERADMINISTRACION' || e.sujeto === undefined) return false;
  const subgrupos = e.incluyeSubgrupos === true;
  switch (e.tipo) {
    case 'USUARIO':
      return e.sujeto === usuario;
    case 'GRUPO':
      return membresias.some((m) => enGrupo(m, e.sujeto as string, subgrupos));
    case 'ROL':
      return membresias.some((m) => m.rol === e.sujeto);
    case 'GRUPO_ROL': {
      // El kit lo escribe «<rol> en <grupo>».
      const corte = e.sujeto.indexOf(' en ');
      if (corte < 0) return false;
      const rol = e.sujeto.slice(0, corte);
      const grupo = e.sujeto.slice(corte + 4);
      return membresias.some((m) => m.rol === rol && enGrupo(m, grupo, subgrupos));
    }
    default:
      return false;
  }
}

/** Las capacidades de la persona a partir de sus membresías y de los editores de cada definición. */
export function capacidadesDe(usuario: string, membresias: Membresia[], editores: Editor[]): Capacidades {
  if (esSuperadministracion(membresias)) return { perfil: 'superadministracion', permisos: [] };
  const propios: PermisoPropio[] = [];
  const vistos = new Set<string>();
  for (const e of editores) {
    if (!alcanzaA(e, usuario, membresias) || e.proceso === undefined) continue;
    const actividades = [...(e.actividades ?? [])].sort();
    const clave = [e.proceso, actividades.join('|'), e.vigenteHasta ?? ''].join('#');
    if (vistos.has(clave)) continue;
    vistos.add(clave);
    propios.push({ proceso: e.proceso, actividades, vigenteHasta: e.vigenteHasta ?? null });
  }
  return propios.length > 0 ? { perfil: 'delegado', permisos: propios } : CONSULTA;
}

/** ¿Puede editar en este ámbito? La superadministración, todo; un delegado, dentro de su proceso y sus actividades. */
export function puedeEditarEn(c: Capacidades, a: Ambito): boolean {
  if (c.perfil === 'superadministracion') return true;
  if (c.perfil !== 'delegado' || a.proceso === TODO) return false;
  return c.permisos.some((p) => p.proceso === a.proceso && (p.actividades.length === 0 || (a.actividad !== TODO && p.actividades.includes(a.actividad))));
}

/** ¿Se le ofrece la pestaña Permisos? Solo a la superadministración. */
export const veLosPermisos = (c: Capacidades): boolean => c.perfil === 'superadministracion';

/** ¿Se le ofrece Aprobaciones? A quien puede escribir en algún ámbito: la superadministración y los delegados. */
export const veLasAprobaciones = (c: Capacidades): boolean => c.perfil !== 'consulta';
