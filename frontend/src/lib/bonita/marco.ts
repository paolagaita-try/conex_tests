/**
 * El marco: cómo una pantalla embebida le dice a su bandeja que terminó.
 *
 * La bandeja de cada familia abre el formulario de una tarea **dentro de sí misma**, en un
 * `<iframe>`, por la dirección corta que resuelve el motor (`/bonita/portal/form/taskInstance/{id}`).
 * Para saber que la pantalla envió, no sondea al motor: escucha el mismo mensaje `postMessage`
 * que espera la Task List nativa de la plataforma (*medido* en `custompage_tasklist` v1.1.0 de
 * 2025.2-u0: `tasks-app.js` actúa sobre `{ action: 'Submit task', message: 'success' | 'error' }`).
 *
 * Es el **único protocolo propio** de los formularios, y tiene una sola dirección:
 *
 *     formulario → bandeja   { action: 'Submit task',   message: 'success', taskId }
 *                            { action: 'Submit task',   message: 'error',   taskId, status }
 *                            { action: 'Start process', message: 'success', caseId }
 *     bandeja → formulario   (nada: la bandeja solo carga y escucha)
 *
 * Dos reglas que no son de estilo:
 *
 * 1. **Se emite desde el único punto por el que pasan todas las pantallas** (`ejecutarTarea` e
 *    `instanciarProceso` en `cliente.ts`), y solo si la pantalla está en un marco de la plataforma
 *    (`estaEnMarcoDeBonita()`). Ningún `.svelte` cambia —la intercepción
 *    va donde pasan todas las vías—, y las pantallas siguen funcionando solas, en E2E y en la Task
 *    List nativa mientras convivan.
 * 2. **Un mensaje no es una orden.** La bandeja descarta lo que no venga de su propio origen o no
 *    tenga esta forma, y tras un `success` **re-consulta** al motor: no marca nada como hecho
 *    «porque se lo dijeron».
 *
 * Lo vigila `marco.test.ts`: quitar la emisión lo pone en rojo.
 */

import { estaEnMarcoDeBonita } from './config';

/** Lo que una pantalla le dice a su bandeja. Exactamente estas tres formas, ninguna más. */
export type MensajeDelMarco =
  | { action: 'Submit task'; message: 'success'; taskId: string }
  | { action: 'Submit task'; message: 'error'; taskId: string; status?: number }
  | { action: 'Start process'; message: 'success'; caseId: string };

/** Prefijo del contexto de la plataforma (el mismo que usa `config.ts`). */
const BASE_URL = '/bonita';

/**
 * Dirección corta del formulario de una tarea: la resuelve el **motor** contra el `formMapping`
 * absoluto de la página. Es exactamente por donde entra la
 * Task List nativa y el page object E2E: construir la URL del recurso a mano saltaría ese eslabón.
 */
export function urlDelFormularioDeTarea(idTarea: string): string {
  return `${BASE_URL}/portal/form/taskInstance/${encodeURIComponent(idTarea)}`;
}

/** Dirección corta del formulario de instanciación de un proceso, por nombre y versión. */
export function urlDelFormularioDeInstanciacion(nombre: string, version: string): string {
  return `${BASE_URL}/portal/form/process/${encodeURIComponent(nombre)}/${encodeURIComponent(version)}`;
}

/** Dirección corta del resumen de un caso (la página de overview que el `formMapping` resuelva). */
export function urlDelResumenDeCaso(idCaso: string): string {
  return `${BASE_URL}/portal/form/processInstance/${encodeURIComponent(idCaso)}`;
}

function esId(valor: unknown): valor is string {
  return typeof valor === 'string' && valor.length > 0;
}

/**
 * ¿Tiene esto la forma del protocolo? Se valida **la forma**, no solo el `action`: un objeto con
 * `action: 'Submit task'` y sin `taskId` no es un mensaje del marco, es ruido con el nombre puesto.
 */
export function esMensajeDelMarco(valor: unknown): valor is MensajeDelMarco {
  if (typeof valor !== 'object' || valor === null) return false;
  const m = valor as Record<string, unknown>;
  if (m.action === 'Submit task') {
    if (!esId(m.taskId)) return false;
    if (m.message === 'success') return true;
    if (m.message === 'error') return m.status === undefined || typeof m.status === 'number';
    return false;
  }
  if (m.action === 'Start process') {
    return m.message === 'success' && esId(m.caseId);
  }
  return false;
}

/**
 * Avisa a la bandeja que contiene a esta pantalla. Devuelve `true` si el aviso salió.
 *
 * Solo se emite dentro de un marco de la plataforma: una pantalla abierta sola no tiene a quién
 * avisar, y `postMessage` a uno mismo sería un mensaje que nadie pidió. Viaja como cadena JSON,
 * que es lo que la Task List nativa acepta además del objeto (*medido*), y con `targetOrigin` del
 * propio origen: nunca `'*'`, porque el contenido nombra una tarea y un caso.
 */
export function avisarAlContenedor(mensaje: MensajeDelMarco): boolean {
  if (typeof window === 'undefined') return false;
  if (!estaEnMarcoDeBonita()) return false;
  if (!esMensajeDelMarco(mensaje)) return false;
  try {
    window.parent.postMessage(JSON.stringify(mensaje), window.location.origin);
    return true;
  } catch {
    // Un padre de otro origen rechaza el `targetOrigin`: la pantalla sigue funcionando sola.
    return false;
  }
}

/**
 * Escucha los mensajes del marco y devuelve la función que deja de escuchar.
 *
 * Se descarta, sin excepción y sin aviso, todo lo que (a) no venga del propio origen o (b) no tenga
 * la forma del protocolo. Acepta cadena JSON u objeto, como la nativa. Lo que llega al callback es
 * un `MensajeDelMarco` válido, siempre.
 */
export function escucharAlMarco(callback: (mensaje: MensajeDelMarco) => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const receptor = (evento: MessageEvent): void => {
    if (evento.origin !== window.location.origin) return;
    let datos: unknown = evento.data;
    if (typeof datos === 'string') {
      try {
        datos = JSON.parse(datos);
      } catch {
        return;
      }
    }
    if (!esMensajeDelMarco(datos)) return;
    callback(datos);
  };
  window.addEventListener('message', receptor);
  return () => window.removeEventListener('message', receptor);
}
