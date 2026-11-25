/**
 * Lo que los contenedores comparten con la aplicación: el cliente del kit, lo leído al abrir
 * y cómo refrescarlo tras una escritura. Viaja por el CONTEXTO de Svelte y no por props: lo leído lleva
 * versiones y números sueltos, y la auditoría del origen de las cifras no admite que un
 * componente reciba un valor que podría pintarlos. Las vistas, en cambio, solo reciben modelos de texto.
 */
import { getContext, setContext } from 'svelte';
import type { Kit } from './kit';
import type { Contexto } from './carga';

export interface Aplicacion {
  kit: Kit;
  /** Lo leído al abrir, siempre el vigente (reactivo). */
  contexto: () => Contexto;
  /**
   * Vuelve a leer una definición y lo pendiente tras una escritura aplicada. NUNCA lanza: si la lectura falla,
   * la escritura sigue siendo buena y la aplicación avisa «guardado, pero no pudimos actualizar la vista».
   */
  refrescar: (definicion: string) => Promise<void>;
  /** Vuelve a leer UNA definición al abrirla: lo leído al arrancar puede estar viejo (otra sesión cambió algo). Nunca lanza: si falla, la aplicación lo avisa. */
  releer: (definicion: string) => Promise<void>;
  /**
   * Una lectura posterior a una escritura falló: deja el aviso con su reintento. `null` retira SOLO el de esa
   * `clave` (cada lectura es dueña de su aviso: que una funcione no borra el de otra que sigue vieja).
   */
  avisarRefresco: (clave: string, reintentar: (() => Promise<void>) | null) => void;
}

const CLAVE = Symbol('aplicacion-de-parametros');

export const ofrecer = (a: Aplicacion): void => {
  setContext(CLAVE, a);
};

export function usarAplicacion(): Aplicacion {
  const a = getContext<Aplicacion | undefined>(CLAVE);
  if (!a) throw new Error('Los contenedores de la aplicación de parámetros viven dentro de <Parametros>');
  return a;
}
