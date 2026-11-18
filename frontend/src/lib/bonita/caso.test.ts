/** Los datos de solo lectura salen de la extensión de lecturas del caso, nunca de /API/bdm. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cargarLecturas, idCasoDe, leerCaso, NO_LEIDO, SIN_VALOR, textoDeLectura } from './caso';
import type { ContextoBonita } from './tipos';

const TAREA: ContextoBonita = { idTarea: '20', idProceso: null, idCaso: null, tipo: 'tarea' };
const LECTURAS = [
  { etiqueta: 'Número', lee: 'Registro.numero', atributo: 'numero' },
  { etiqueta: 'Días', lee: 'Registro.dias', atributo: 'dias' },
  { etiqueta: 'Variable', lee: 'pv numero', atributo: null },
];

function plataforma(rutas: Record<string, () => Response>) {
  const pedidas: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (entrada: string | URL) => {
      const url = String(entrada);
      pedidas.push(url);
      const clave = Object.keys(rutas).find((k) => url.includes(k));
      return clave ? rutas[clave]() : new Response('{}', { status: 404 });
    }),
  );
  return pedidas;
}

const json = (cuerpo: unknown, status = 200) => new Response(JSON.stringify(cuerpo), { status });

afterEach(() => vi.unstubAllGlobals());

describe('lecturas del caso', () => {
  it('lee el caso de la tarea por la extensión y muestra cada atributo', async () => {
    const pedidas = plataforma({
      '/bpm/humanTask/20': () => json({ id: '20', caseId: '7' }),
      '/extension/consultas/caso': () => json({ numero: 'R-7', dias: 5 }),
    });
    expect(await cargarLecturas(LECTURAS, TAREA)).toEqual(['R-7', '5', NO_LEIDO]);
    expect(pedidas).toContain('/bonita/API/extension/consultas/caso?caseId=7');
    expect(pedidas.some((u) => u.includes('/API/bdm'))).toBe(false);
  });

  it('el caseId de la dirección gana; en un resumen, el id de la dirección es el caso', async () => {
    expect(await idCasoDe({ ...TAREA, idCaso: '9' })).toBe('9');
    window.history.replaceState(null, '', '/?id=31');
    expect(await idCasoDe({ idTarea: '31', idProceso: null, idCaso: null, tipo: 'tarea' }, true)).toBe('31');
    window.history.replaceState(null, '', '/');
  });

  it('una lectura que falla lanza (la pantalla lo dice); sin caso, también', async () => {
    plataforma({ '/bpm/humanTask/20': () => json({ caseId: '7' }), '/extension/consultas/caso': () => json({}, 500) });
    await expect(cargarLecturas(LECTURAS, TAREA)).rejects.toThrow(/500/);
    await expect(cargarLecturas(LECTURAS, { idTarea: null, idProceso: null, idCaso: null, tipo: 'desconocido' })).rejects.toThrow(
      /qué caso/,
    );
  });

  it('el texto de cada dato', () => {
    expect(textoDeLectura({ a: true }, { etiqueta: 'A', lee: 'X.a', atributo: 'a' })).toBe('sí');
    expect(textoDeLectura({}, { etiqueta: 'A', lee: 'X.a', atributo: 'a' })).toBe(SIN_VALOR);
    expect(textoDeLectura({ a: { b: 1 } }, { etiqueta: 'A', lee: 'X.a', atributo: 'a' })).toBe('{"b":1}');
  });

  it('leerCaso codifica el caso', async () => {
    const pedidas = plataforma({ '/extension/consultas/caso': () => json({}) });
    await leerCaso('a b');
    expect(pedidas).toEqual(['/bonita/API/extension/consultas/caso?caseId=a%20b']);
  });
});
