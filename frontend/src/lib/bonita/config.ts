/**
 * Configuración de la conexión con Bonita.
 *
 *  - Ni la dirección del servidor ni las credenciales de desarrollo están EN EL CÓDIGO:
 *    en desarrollo salen de las variables `VITE_*` (ver `.env.example`); en producción
 *    no hay credenciales en absoluto, se usa la sesión del portal.
 *  - El entorno NO se detecta por el puerto (el runtime local y el servidor de
 *    desarrollo son configurables). Se detecta por lo único que de verdad distingue
 *    los dos casos: estar servido **dentro** del contexto de Bonita.
 */

/** Prefijo del contexto de la aplicación Bonita. */
const BASE_URL = '/bonita';

/**
 * ¿El formulario está servido por Bonita (producción) o por el servidor de
 * desarrollo?
 *
 * Una custom page desplegada siempre se sirve bajo el contexto `/bonita/` — como
 * `/bonita/portal/resource/...`. El servidor de desarrollo sirve desde la raíz y
 * únicamente hace de proxy de las llamadas a la API. El criterio es por tanto la
 * ruta, nunca el puerto.
 */
export function estaServidoPorBonita(): boolean {
  if (typeof window === 'undefined') return false;
  return window.location.pathname.includes(`${BASE_URL}/`);
}

/** Complemento de `estaServidoPorBonita`, para leerlo en positivo. */
export function esEntornoDeDesarrollo(): boolean {
  return !estaServidoPorBonita();
}

/** Construye la URL de un recurso de la API REST de Bonita. */
export function urlApi(recurso: string): string {
  const limpio = recurso.startsWith('/') ? recurso : `/${recurso}`;
  return `${BASE_URL}/API${limpio}`;
}

/** URL del servicio de autenticación (solo se usa en desarrollo). */
export function urlLogin(): string {
  return `${BASE_URL}/loginservice`;
}

/**
 * Credenciales de desarrollo, tomadas del entorno. Nunca hay credenciales en el
 * código ni valores por defecto que pudieran acabar en un despliegue: si faltan,
 * devuelve `null` y quien llame decide (la sesión del portal no las necesita).
 *
 * Solo en el servidor de desarrollo (`import.meta.env.DEV`): en un build Vite la
 * sustituye por `false` y elimina la rama entera, así que el valor de
 * `VITE_BONITA_DEV_PASSWORD` no llega a ningún ZIP aunque esté exportado en la
 * shell que construye (`build-form.js` lo comprueba además sobre lo construido).
 */
export function credencialesDeDesarrollo(): { usuario: string; clave: string } | null {
  if (!import.meta.env.DEV) return null;
  const usuario = import.meta.env.VITE_BONITA_DEV_USER;
  const clave = import.meta.env.VITE_BONITA_DEV_PASSWORD;
  if (!usuario || !clave) return null;
  return { usuario, clave };
}

/**
 * ¿El formulario está embebido en un marco del portal de Bonita?
 *
 * La plataforma sirve las custom pages dentro de un iframe (doc
 * `pages-and-forms:pages-development`), cuyo identificador empieza por
 * `bonitaframe`. Saberlo importa para no anidar el portal dentro de sí mismo al
 * navegar después de enviar el formulario.
 */
export function estaEnMarcoDeBonita(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const marco = window.frameElement as HTMLIFrameElement | null;
    if (marco?.id) return marco.id.startsWith('bonitaframe');
  } catch {
    // Restricción de origen cruzado: no se puede inspeccionar el marco, pero la
    // existencia de un padre distinto ya indica que estamos embebidos.
    return window.parent !== window.self;
  }
  return false;
}

/** Lee un parámetro de la dirección actual. */
export function parametroDeUrl(nombre: string): string | null {
  if (typeof window === 'undefined') return null;
  // Bonita compone direcciones donde el parámetro puede venir tras `/`, `?` o `&`
  // (por ejemplo `.../content/?id=123`), así que no basta con URLSearchParams.
  const patron = new RegExp(`[/?&]${nombre}=([^&#]*)($|[&#])`);
  const coincidencia = window.location.href.match(patron);
  if (coincidencia?.[1]) return decodeURIComponent(coincidencia[1]);
  return new URLSearchParams(window.location.search).get(nombre);
}
