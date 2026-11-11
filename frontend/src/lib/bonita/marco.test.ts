/**
 * El protocolo del marco, medido en las dos puntas.
 *
 * **La expectativa no sale del tipo de `marco.ts`**: sale de las formas que espera la Task List
 * nativa de la plataforma (`FORMAS`, abajo). Comparar el emisor con su propio tipo sería
 * tautológico; la expectativa se deriva de OTRA fuente.
 *
 * Lo que se mide:
 *  - el emisor (`ejecutarTarea` / `instanciarProceso` de `cliente.ts`) avisa con la forma exacta
 *    declarada tras el 204/200 y tras un rechazo, con `targetOrigin` del propio origen, y **solo**
 *    dentro de un marco de la plataforma;
 *  - el receptor (`escucharAlMarco`) descarta otro origen y otra forma, acepta cadena y objeto,
 *    y deja de escuchar al cancelar.
 *
 * Quitar `avisarAlContenedor` de `ejecutarTarea` pone este fichero en rojo.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  avisarAlContenedor,
  escucharAlMarco,
  esMensajeDelMarco,
  urlDelFormularioDeInstanciacion,
  urlDelFormularioDeTarea,
  urlDelResumenDeCaso,
  type MensajeDelMarco,
} from './marco';
import { ejecutarTarea, instanciarProceso } from './cliente';
import { ErrorDeBonita } from './tipos';

/**
 * Las formas «formulario → bandeja» que espera la Task List nativa (medido en `custompage_tasklist` v1.1.0 de
 * 2025.2-u0, `tasks-app.js`), con los campos que cada una lleva además de `action` y `message`.
 */
const FORMAS: { action: string; message: string; campos: string[] }[] = [
  { action: 'Submit task', message: 'success', campos: ['taskId'] },
  { action: 'Submit task', message: 'error', campos: ['taskId', 'status'] },
  { action: 'Start process', message: 'success', campos: ['caseId'] },
];

/** Se «entra» en un marco de la plataforma: `window.frameElement` con id `bonitaframe…`. */
function dentroDelMarco(si: boolean): void {
  Object.defineProperty(window, 'frameElement', {
    value: si ? { id: 'bonitaframe0' } : null,
    configurable: true,
  });
}

let enviados: { datos: unknown; origen: unknown }[] = [];

beforeEach(() => {
  enviados = [];
  vi.spyOn(window.parent, 'postMessage').mockImplementation((datos: unknown, origen?: unknown) => {
    enviados.push({ datos, origen });
  });
  document.cookie = 'X-Bonita-API-Token=token-de-prueba';
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  dentroDelMarco(false);
});

function respuesta(estado: number, cuerpo?: unknown): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status: estado,
    headers: cuerpo === undefined ? {} : { 'Content-Type': 'application/json' },
  });
}

function mensajeEnviado(indice = 0): MensajeDelMarco {
  const e = enviados[indice];
  expect(e, 'no se emitió ningún mensaje al contenedor').toBeDefined();
  expect(typeof e.datos, 'el mensaje viaja como cadena JSON, como acepta la nativa').toBe('string');
  return JSON.parse(e.datos as string);
}

describe('las formas de la plataforma son la vara', () => {
  const formas = FORMAS;

  it('declara exactamente tres formas de formulario → bandeja', () => {
    expect(formas.map((f) => `${f.action}/${f.message}`).sort()).toEqual(
      ['Start process/success', 'Submit task/error', 'Submit task/success'].sort(),
    );
  });

  it('el validador acepta cada forma declarada y rechaza la que no está', () => {
    for (const f of formas) {
      const m: Record<string, unknown> = { action: f.action, message: f.message };
      for (const c of f.campos) m[c] = c === 'status' ? 500 : '1';
      expect(esMensajeDelMarco(m), `${f.action}/${f.message}`).toBe(true);
    }
    expect(esMensajeDelMarco({ action: 'Start process', message: 'error', caseId: '1' })).toBe(false);
    expect(esMensajeDelMarco({ action: 'Submit task', message: 'success' })).toBe(false);
    expect(esMensajeDelMarco({ action: 'Submit task', message: 'success', taskId: '' })).toBe(false);
    expect(esMensajeDelMarco('Submit task')).toBe(false);
    expect(esMensajeDelMarco(null)).toBe(false);
  });
});

describe('emisor · ejecutarTarea', () => {
  it('tras el 204 avisa «Submit task / success» con el taskId, al propio origen', async () => {
    dentroDelMarco(true);
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(204)));

    await ejecutarTarea('233', { decision: {} });

    const m = mensajeEnviado();
    const esperada = FORMAS.find((f) => f.action === 'Submit task' && f.message === 'success')!;
    expect(m).toEqual({ action: esperada.action, message: esperada.message, taskId: '233' });
    for (const c of esperada.campos) expect(m).toHaveProperty(c);
    expect(enviados[0].origen).toBe(window.location.origin);
  });

  it('tras un rechazo avisa «Submit task / error» con el status, y vuelve a lanzar', async () => {
    dentroDelMarco(true);
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(400, { message: 'Expected input' })));

    await expect(ejecutarTarea('233', {})).rejects.toBeInstanceOf(ErrorDeBonita);

    const m = mensajeEnviado();
    expect(m).toEqual({ action: 'Submit task', message: 'error', taskId: '233', status: 400 });
  });

  it('fuera de un marco de la plataforma NO emite nada: la pantalla sigue funcionando sola', async () => {
    dentroDelMarco(false);
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(204)));

    await ejecutarTarea('233', {});

    expect(enviados).toEqual([]);
  });
});

describe('emisor · instanciarProceso', () => {
  it('tras el 200 avisa «Start process / success» con el caseId como cadena', async () => {
    dentroDelMarco(true);
    vi.stubGlobal('fetch', vi.fn(async () => respuesta(200, { caseId: 77 })));

    const caso = await instanciarProceso('4444444444444444', { inicio: {} });

    expect(caso.caseId).toBe(77);
    expect(mensajeEnviado()).toEqual({ action: 'Start process', message: 'success', caseId: '77' });
  });
});

describe('avisarAlContenedor', () => {
  it('rechaza una forma que no es del protocolo aunque esté en un marco', () => {
    dentroDelMarco(true);
    // @ts-expect-error — forma inválida a propósito: el emisor también valida.
    expect(avisarAlContenedor({ action: 'Submit task', message: 'success' })).toBe(false);
    expect(enviados).toEqual([]);
  });
});

describe('receptor · escucharAlMarco', () => {
  function llega(data: unknown, origin = window.location.origin): void {
    window.dispatchEvent(new MessageEvent('message', { data, origin }));
  }

  it('entrega el mensaje válido, venga como cadena o como objeto', () => {
    const recibidos: MensajeDelMarco[] = [];
    const parar = escucharAlMarco((m) => recibidos.push(m));
    llega(JSON.stringify({ action: 'Submit task', message: 'success', taskId: '9' }));
    llega({ action: 'Start process', message: 'success', caseId: '3' });
    parar();
    expect(recibidos).toEqual([
      { action: 'Submit task', message: 'success', taskId: '9' },
      { action: 'Start process', message: 'success', caseId: '3' },
    ]);
  });

  it('descarta otro origen y otra forma, sin lanzar', () => {
    const recibidos: MensajeDelMarco[] = [];
    const parar = escucharAlMarco((m) => recibidos.push(m));
    llega({ action: 'Submit task', message: 'success', taskId: '9' }, 'https://otro.example');
    llega({ action: 'Submit task', message: 'success' });
    llega('esto no es JSON');
    llega({ action: 'Cerrar sesión', message: 'success' });
    parar();
    expect(recibidos).toEqual([]);
  });

  it('deja de escuchar al cancelar', () => {
    const recibidos: MensajeDelMarco[] = [];
    const parar = escucharAlMarco((m) => recibidos.push(m));
    parar();
    llega({ action: 'Submit task', message: 'success', taskId: '9' });
    expect(recibidos).toEqual([]);
  });
});

describe('direcciones cortas que resuelve el motor', () => {
  it('son las de la Task List nativa (medido en 2025.2-u0)', () => {
    expect(urlDelFormularioDeTarea('233')).toBe('/bonita/portal/form/taskInstance/233');
    expect(urlDelFormularioDeInstanciacion('SolicitudVacaciones', '1.0')).toBe(
      '/bonita/portal/form/process/SolicitudVacaciones/1.0',
    );
    expect(urlDelResumenDeCaso('18')).toBe('/bonita/portal/form/processInstance/18');
  });
});
