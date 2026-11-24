/**
 * Precarga del caso de preventa: la REST API extension `preventa/contexto` (bonita-project/extensions/
 * preventa-contexto-api-extension) devuelve `{ticket, deal, company, contacts, owner}` leídos de HubSpot.
 * Del proyecto (no generado).
 */
import { peticion } from '$lib/bonita/cliente';
import { idCasoDe, leerCaso } from '$lib/bonita/caso';
import type { ContextoBonita } from '$lib/bonita/tipos';

export interface ObjetoHubspot {
  readonly id: string;
  readonly properties: Readonly<Record<string, string | null>>;
}

export interface OwnerHubspot {
  readonly id?: string;
  readonly email?: string | null;
  readonly firstName?: string | null;
  readonly lastName?: string | null;
  readonly userId?: number | string | null;
}

export interface ContextoPreventa {
  readonly ticket: ObjetoHubspot;
  readonly deal: ObjetoHubspot | null;
  readonly company: ObjetoHubspot | null;
  readonly contacts: readonly ObjetoHubspot[];
  readonly owner: OwnerHubspot | null;
}

/** Lo que la pantalla sabe del caso en Bonita (objeto de negocio Preventa). */
export type DatosDelCaso = Readonly<Record<string, unknown>>;

const ID_VALIDO = /^[A-Za-z0-9-]{1,40}$/;

/** Lee la precarga de HubSpot del ticket. */
export function cargarContexto(ticketId: string): Promise<ContextoPreventa> {
  if (!ID_VALIDO.test(ticketId)) return Promise.reject(new Error('El identificador del ticket no es válido.'));
  return peticion<ContextoPreventa>(`/extension/preventa/contexto?ticketId=${encodeURIComponent(ticketId)}`);
}

/**
 * Lee el objeto de negocio `Preventa` del caso por la extensión de lecturas del caso del arnés
 * (`extension/consultas/caso`), nunca por la API del BDM directa (regla de check_formularios).
 */
export async function leerPreventa(contexto: ContextoBonita): Promise<DatosDelCaso> {
  const idCaso = await idCasoDe(contexto);
  if (!idCaso) throw new Error("La pantalla no se abrió desde su tarea o su caso en el portal.");
  return leerCaso(idCaso);
}

/** Texto legible de una propiedad (vacío → guion largo). */
export function valor(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—';
  return String(v);
}

/** Etiqueta legible de una clave de HubSpot (`hs_ticket_priority` → «Ticket priority»). */
export function etiquetaDe(clave: string): string {
  const limpia = clave.replace(/^hs_/, '').replace(/_/g, ' ').trim();
  return limpia.charAt(0).toUpperCase() + limpia.slice(1);
}

export const PRIORIDADES: Readonly<Record<string, string>> = { HIGH: 'Alta', MEDIUM: 'Media', LOW: 'Baja' };

/** Nombre completo del owner o del contacto. */
export function nombreDe(p: { firstName?: string | null; lastName?: string | null } | null): string {
  if (!p) return '—';
  return [p.firstName, p.lastName].filter(Boolean).join(' ') || '—';
}

/** Cuando HubSpot devuelve una fecha ISO, se pinta en local. */
export function fecha(v: unknown): string {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(v)) return valor(v);
  const d = new Date(v);
  return Number.isNaN(d.getTime())
    ? v
    : d.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: v.length > 10 ? 'short' : undefined });
}

export interface Precarga {
  readonly caso: DatosDelCaso;
  readonly hubspot: ContextoPreventa;
}

/** El objeto `Preventa` del caso y, con su `ticketId`, la precarga de HubSpot. */
export async function precargar(contexto: ContextoBonita): Promise<Precarga> {
  const caso = await leerPreventa(contexto);
  const ticketId = typeof caso.ticketId === 'string' ? caso.ticketId : String(caso.ticketId ?? '');
  return { caso, hubspot: await cargarContexto(ticketId) };
}

/** Una URL http(s) bien formada. */
export function esUrl(v: string | null | undefined): boolean {
  if (!v) return false;
  try {
    const u = new URL(v);
    return (u.protocol === 'http:' || u.protocol === 'https:') && u.hostname.includes('.');
  } catch {
    return false;
  }
}
