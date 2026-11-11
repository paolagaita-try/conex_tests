/**
 * Las consultas de la bandeja: con filtro siempre, paginadas por `Content-Range`, y sin
 * disfrazar un error de «nada pendiente».
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  actoresDelProceso,
  consulta,
  esSesionInterna,
  miembrosDelActor,
  misExpedientes,
  perteneceAAlgunActor,
  misTareas,
  procesosQuePuedoIniciar,
  quienSoy,
  tareasListasDelCaso,
} from './bandeja';
import { ErrorDeBonita } from './tipos';

/** Un `fetch` que responde por ruta y recuerda qué se le pidió. */
function plataforma(rutas: Record<string, () => Response>) {
  const pedidas: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (entrada: string | URL) => {
      const url = String(entrada);
      pedidas.push(url);
      const clave = Object.keys(rutas).find((k) => url.includes(k));
      if (!clave) return new Response('[]', { status: 404 });
      return rutas[clave]();
    }),
  );
  return pedidas;
}

const lista = (cuerpo: unknown, total?: number) =>
  new Response(JSON.stringify(cuerpo), {
    status: 200,
    headers: total === undefined ? {} : { 'Content-Range': `0-19/${total}` },
  });

afterEach(() => vi.unstubAllGlobals());

describe('consulta()', () => {
  it('no construye una consulta sin filtro', () => {
    expect(() => consulta('/bpm/humanTask', {})).toThrow(/sin filtro/);
    expect(() => consulta('/bpm/case', { user_id: '' })).toThrow(/sin filtro/);
  });

  it('codifica cada filtro como f=clave=valor, con página, tamaño, orden y despliegue', () => {
    expect(
      consulta('/bpm/humanTask', { state: 'ready', user_id: '42' }, { orden: 'reached_state_date ASC', despliega: ['processId'] }),
    ).toBe('/bpm/humanTask?p=0&c=20&f=state%3Dready&f=user_id%3D42&d=processId&o=reached_state_date%20ASC');
  });
});

describe('misTareas', () => {
  it('pide las tareas listas de la persona, de la más antigua a la más reciente, con el total', async () => {
    const pedidas = plataforma({
      '/bpm/humanTask': () => lista([{ id: '1', name: 'Aprobar …', caseId: '18', state: 'ready' }], 57),
    });
    const pagina = await misTareas('42');
    expect(pedidas[0]).toContain('/bonita/API/bpm/humanTask?');
    expect(pedidas[0]).toContain('f=state%3Dready');
    expect(pedidas[0]).toContain('f=user_id%3D42');
    // Sin `o=`: el motor 2025.2-u0 responde 500 al ordenar por reached_state_date (medido).
    expect(pedidas[0]).not.toContain('o=');
    expect(pagina.elementos).toHaveLength(1);
    expect(pagina.total).toBe(57);
  });

  it('ordena en cliente: la que más espera va primero', async () => {
    plataforma({
      '/bpm/humanTask': () =>
        lista([
          { id: 'b', reached_state_date: '2026-09-22 10:00:00.000' },
          { id: 'a', reached_state_date: '2026-09-21 10:00:00.000' },
          { id: 'c', reached_state_date: '2026-09-22 12:00:00.000' },
        ]),
    });
    expect((await misTareas('42')).elementos.map((t) => t.id)).toEqual(['a', 'b', 'c']);
  });

  it('sin Content-Range, el total es desconocido (null), no cero', async () => {
    plataforma({ '/bpm/humanTask': () => lista([]) });
    expect((await misTareas('42')).total).toBeNull();
  });

  it('un 500 se propaga como ErrorDeBonita: nunca una lista vacía', async () => {
    plataforma({ '/bpm/humanTask': () => new Response('{}', { status: 500 }) });
    await expect(misTareas('42')).rejects.toBeInstanceOf(ErrorDeBonita);
  });
});

describe('tareasListasDelCaso', () => {
  it('filtra por el caso y por estado listo', async () => {
    const pedidas = plataforma({ '/bpm/humanTask': () => lista([{ id: '2', name: 'x', caseId: '18' }]) });
    const ts = await tareasListasDelCaso('18');
    expect(pedidas[0]).toContain('f=caseId%3D18');
    expect(pedidas[0]).toContain('f=state%3Dready');
    expect(ts.map((t) => t.id)).toEqual(['2']);
  });
});

describe('misExpedientes', () => {
  it('vivos: /bpm/case filtrado por la persona, normalizando ids a cadena', async () => {
    const pedidas = plataforma({
      '/bpm/case': () => lista([{ id: 18, state: 'started', start: '2026-09-22', started_by: 4, processDefinitionId: 99 }], 1),
    });
    const { elementos, total } = await misExpedientes('42');
    expect(pedidas[0]).toContain('/bonita/API/bpm/case?');
    expect(pedidas[0]).toContain('f=user_id%3D42');
    expect(total).toBe(1);
    expect(elementos[0]).toMatchObject({ id: '18', started_by: '4', processDefinitionId: '99', archivado: false, sourceObjectId: null });
  });

  it('cerrados: /bpm/archivedCase, conservando el id que tuvo el caso en vida', async () => {
    const pedidas = plataforma({
      '/bpm/archivedCase': () => lista([{ id: 500, sourceObjectId: 18, state: 'completed', start: 's', started_by: 4, processDefinitionId: 99, end_date: 'e' }]),
    });
    const { elementos } = await misExpedientes('42', { cerrados: true });
    expect(pedidas[0]).toContain('/bonita/API/bpm/archivedCase?');
    expect(elementos[0]).toMatchObject({ id: '500', sourceObjectId: '18', archivado: true, end_date: 'e' });
  });
});

describe('procesosQuePuedoIniciar', () => {
  it('pide solo lo habilitado que la persona puede iniciar', async () => {
    const pedidas = plataforma({ '/bpm/process': () => lista([{ id: '7', name: 'SolicitudVacaciones', displayName: 'Vacaciones', version: '1.0' }]) });
    const ps = await procesosQuePuedoIniciar('42');
    expect(pedidas[0]).toContain('f=user_id%3D42');
    expect(pedidas[0]).toContain('f=activationState%3DENABLED');
    expect(ps).toHaveLength(1);
  });
});

describe('quienSoy', () => {
  it('compone el nombre desde identity/user y conserva el de sesión', async () => {
    plataforma({
      '/system/session': () => lista({ user_id: 4, user_name: 'ana.perez' }),
      '/identity/user/4': () => lista({ firstname: 'Ana', lastname: 'Pérez', userName: 'ana.perez' }),
    });
    expect(await quienSoy()).toEqual({ id: '4', usuario: 'ana.perez', nombre: 'Ana Pérez' });
  });

  it('sin permiso para leer el usuario, saluda por el nombre de sesión', async () => {
    plataforma({
      '/system/session': () => lista({ user_id: 4, user_name: 'ana.perez' }),
      '/identity/user/4': () => new Response('', { status: 403 }),
    });
    expect((await quienSoy()).nombre).toBe('ana.perez');
  });

  it('sin sesión (401) se propaga: la bandeja recarga y la plataforma manda al login', async () => {
    plataforma({ '/system/session': () => new Response('', { status: 401 }) });
    await expect(quienSoy()).rejects.toMatchObject({ estado: 401 });
  });
});

describe('compuerta de familia · actores del proceso', () => {
  const ACTORES = [
    { id: '5', name: 'Solicitante', displayName: 'Solicitante', process_id: '9' },
    { id: '3', name: 'Revisor de solicitudes', displayName: 'Analista', process_id: '9' },
  ];
  const MIEMBROS: Record<string, { id: string; actor_id: string; user_id: string }[]> = {
    '5': [{ id: 'a', actor_id: '5', user_id: '1' }, { id: 'b', actor_id: '5', user_id: '2' }],
    '3': [{ id: 'c', actor_id: '3', user_id: '4' }],
  };
  function conActores() {
    return plataforma({
      '/bpm/process': () => lista([{ id: '9', name: 'SolicitudVacaciones', displayName: 'V', version: '1.0' }]),
      '/bpm/actor?': () => lista(ACTORES),
      '/bpm/actorMember?': () => lista([]), // sobrescrito abajo por actor
    });
  }

  it('actoresDelProceso y miembrosDelActor consultan SIEMPRE con filtro', async () => {
    const pedidas = conActores();
    await actoresDelProceso('9');
    await miembrosDelActor('3');
    expect(pedidas[0]).toContain('/bpm/actor?');
    expect(pedidas[0]).toContain('f=process_id%3D9');
    expect(pedidas[1]).toContain('/bpm/actorMember?');
    expect(pedidas[1]).toContain('f=actor_id%3D3');
    expect(pedidas[1]).toContain('f=member_type%3DUSER');
  });

  it('perteneceAAlgunActor: solo cuenta la membresía en los actores buscados', () => {
    const m = new Map(Object.entries(MIEMBROS));
    expect(perteneceAAlgunActor('4', ACTORES, m, ['Revisor de solicitudes'])).toBe(true);
    expect(perteneceAAlgunActor('1', ACTORES, m, ['Revisor de solicitudes'])).toBe(false);
    // Ser «Solicitante» no convierte en interno aunque el actor exista.
    expect(perteneceAAlgunActor('2', ACTORES, m, ['Revisor de solicitudes'])).toBe(false);
    expect(perteneceAAlgunActor('2', ACTORES, m, ['Solicitante'])).toBe(true);
  });

  it('esSesionInterna: la solicitante no lo es; la revisora sí; y un 403 en actorMember se propaga', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (entrada: string | URL) => {
        const url = String(entrada);
        if (url.includes('/bpm/process?')) return lista([{ id: '9', name: 'O', displayName: 'O', version: '1.0' }]);
        if (url.includes('/bpm/actor?')) return lista(ACTORES);
        const id = decodeURIComponent(url).match(/actor_id=(\d+)/)?.[1] ?? '';
        return lista(MIEMBROS[id] ?? []);
      }),
    );
    expect(await esSesionInterna({ id: '1' }, ['Revisor de solicitudes'])).toBe(false);
    expect(await esSesionInterna({ id: '4' }, ['Revisor de solicitudes'])).toBe(true);

    plataforma({ '/bpm/process': () => lista([{ id: '9' }]), '/bpm/actor?': () => lista(ACTORES), '/bpm/actorMember?': () => new Response('', { status: 403 }) });
    await expect(esSesionInterna({ id: '4' }, ['Revisor de solicitudes'])).rejects.toBeInstanceOf(ErrorDeBonita);
  });
});
