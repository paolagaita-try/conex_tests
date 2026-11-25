/**
 * Quién es una persona, un grupo o un rol POR SU ID (la búsqueda del kit solo devuelve 20): se pregunta a la API de
 * identidad de Bonita (`organization_visualization`). Vive AQUÍ y no en el cimiento porque tocar `src/lib` desfasa los ZIP de
 * todas las pantallas (R1). Un id es un identificador, no una cifra del expediente: este fichero es el ÚNICO donde un id se
 * escribe en una ruta, y está declarado como excepción de formateadores (`excepcionesDeCifras.ts`).
 */
import { peticion, TIEMPO_MAXIMO_DE_CONSULTA_MS } from '$lib/bonita/cliente';

const ESPERA = { tiempoMaximoMs: TIEMPO_MAXIMO_DE_CONSULTA_MS };
const IDENTIFICADOR: Intl.NumberFormatOptions = { useGrouping: false, maximumFractionDigits: 0 };
const texto = (o: Record<string, unknown>, k: string): string | null => (typeof o[k] === 'string' && o[k] !== '' ? (o[k] as string) : null);

/** «4», no «4,0» ni «4,000». */
function idEnRuta(id: number): string {
  return Number.isInteger(id) && id >= 0 ? new Intl.NumberFormat('es-US', IDENTIFICADOR).format(id) : '';
}

export async function nombreDeSujetoPorId(tipo: 'usuario' | 'grupo' | 'rol', id: number): Promise<{ nombre: string; extra: string } | null> {
  const clave = idEnRuta(id);
  if (clave === '') return null;
  try {
    if (tipo === 'usuario') {
      const u = (await peticion<unknown>(`/identity/user/${clave}`, ESPERA)) as Record<string, unknown>;
      const nombre = [texto(u, 'firstname'), texto(u, 'lastname')].filter(Boolean).join(' ').trim();
      const login = texto(u, 'userName') ?? '';
      return login === '' && nombre === '' ? null : { nombre: nombre || login, extra: login };
    }
    if (tipo === 'rol') {
      const r = (await peticion<unknown>(`/identity/role/${clave}`, ESPERA)) as Record<string, unknown>;
      const tecnico = texto(r, 'name') ?? '';
      return tecnico === '' ? null : { nombre: texto(r, 'displayName') || tecnico, extra: tecnico };
    }
    const g = (await peticion<unknown>(`/identity/group/${clave}`, ESPERA)) as Record<string, unknown>;
    const ruta = `${texto(g, 'parentPath') ?? ''}/${texto(g, 'name') ?? ''}`.replace(/\/{2,}/g, '/');
    return texto(g, 'name') === null ? null : { nombre: texto(g, 'displayName') || ruta, extra: ruta };
  } catch {
    return null;
  }
}
