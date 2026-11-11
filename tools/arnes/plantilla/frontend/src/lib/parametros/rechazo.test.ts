import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  abrirTareaConRechazo,
  FRASE_SIN_COMPROBAR,
  entenderRechazos,
  guardarParaReintento,
  leerRechazos,
  olvidarReintento,
  purgarReintentos,
  recuperarParaReintento,
  rechazosParaLaPantalla,
  textoDelRechazo,
  MOTIVOS,
  VIGENCIA_REINTENTO_HORAS,
} from './rechazo';

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { 'Content-Type': 'application/json' } });

describe('entenderRechazos: la forma exacta o «no se pudo comprobar»', () => {
  it('lee la lista cerrada', () => {
    expect(entenderRechazos({ rechazos: [{ campo: 'plazoAprobado', motivo: 'no-vigente' }] })).toEqual([
      { campo: 'plazoAprobado', motivo: 'no-vigente' },
    ]);
    expect(entenderRechazos({ rechazos: [] })).toEqual([]);
  });
  it.each([
    ['sin la lista', {}],
    ['la lista no es lista', { rechazos: 'x' }],
    ['un motivo fuera del vocabulario', { rechazos: [{ campo: 'a', motivo: 'el umbral es 5' }] }],
    ['un campo que no es texto', { rechazos: [{ campo: 1, motivo: 'no-vigente' }] }],
    ['un elemento que no es objeto', { rechazos: ['x'] }],
    ['no es objeto', 'x'],
    ['null', null],
    ['un arreglo', []],
  ])('%s → null (no se afirma que no hay rechazo)', (_c, crudo) => {
    expect(entenderRechazos(crudo)).toBeNull();
  });
});

describe('leerRechazos', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('pide el caso a la consulta de la extensión y devuelve lo que el servidor dijo', async () => {
    const f = vi.fn(async () => json({ rechazos: [{ campo: 'plazoDeEntrega', motivo: 'no-vigente' }] }));
    vi.stubGlobal('fetch', f);
    expect(await leerRechazos('77')).toEqual([{ campo: 'plazoDeEntrega', motivo: 'no-vigente' }]);
    expect(String((f.mock.calls[0] as unknown[])[0])).toContain('/extension/consultas/validacion?caso=77');
  });
  it('sin caso no pregunta', async () => {
    const f = vi.fn();
    vi.stubGlobal('fetch', f);
    expect(await leerRechazos(undefined)).toBeNull();
    expect(await leerRechazos('')).toBeNull();
    expect(f).not.toHaveBeenCalled();
  });
  it.each([403, 404, 500])('un %s no es «sin rechazos»: es null', async (estado) => {
    vi.stubGlobal('fetch', vi.fn(async () => json({}, estado)));
    expect(await leerRechazos('77')).toBeNull();
  });
  it('una red caída es null', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('red'); }));
    expect(await leerRechazos('77')).toBeNull();
  });
});

describe('las frases: neutras y completas', () => {
  it('una por cada motivo, con y sin etiqueta, sin cifras ni nombres internos', () => {
    for (const m of MOTIVOS) {
      for (const e of ['Plazo aprobado', undefined]) {
        const t = textoDelRechazo(m, e);
        expect(t.length).toBeGreaterThan(10);
        expect(t).not.toMatch(/\d/);
        expect(t).not.toMatch(/tope_|umbral|catálogo|catalogo|lista de|fase|alerta|F\d/i);
        if (e) expect(t).toContain(`«${e}»`);
      }
    }
  });
  it('el texto exacto de cada motivo (la igualdad, no la ausencia de palabras)', () => {
    expect(textoDelRechazo('sin-elegir', 'Plazo')).toBe('Elija una opción en «Plazo».');
    expect(textoDelRechazo('no-vigente', 'Plazo')).toBe('La opción elegida en «Plazo» ya no está disponible. Elija otra.');
    expect(textoDelRechazo('sobre-tope', 'Monto')).toBe('El valor de «Monto» supera el máximo permitido para la opción elegida. Ajústelo.');
    expect(textoDelRechazo('sin-comprobar', 'Monto')).toBe('No se pudo comprobar «Monto». Revise el valor y vuelva a enviar.');
  });
});

describe('rechazosParaLaPantalla: cada rechazo junto a su campo', () => {
  const rutas = ['decision.plazoAprobado', 'decision.diasAprobados'];
  it('ata por el nombre del contrato', () => {
    const r = rechazosParaLaPantalla([{ campo: 'plazoAprobado', motivo: 'no-vigente' }], rutas);
    expect(r.porRuta).toEqual({ 'decision.plazoAprobado': 'no-vigente' });
    expect(r.generales).toEqual([]);
  });
  it('un campo que esta pantalla no tiene o vacío pasa a las frases generales, sin repetirse', () => {
    const r = rechazosParaLaPantalla([{ campo: '', motivo: 'sin-comprobar' }, { campo: 'otro', motivo: 'sin-comprobar' }], rutas);
    expect(r.porRuta).toEqual({});
    expect(r.generales).toEqual([textoDelRechazo('sin-comprobar')]);
  });
  it('un campo cuyo nombre solo coincide por el final NO se ata (Aprobado ≠ plazoAprobado)', () => {
    const r = rechazosParaLaPantalla([{ campo: 'Aprobado', motivo: 'no-vigente' }], rutas);
    expect(r.porRuta).toEqual({});
    expect(r.generales.length).toBe(1);
  });
});

describe('lo tecleado mientras puede hacer falta', () => {
  beforeEach(() => window.localStorage.clear());
  it('se guarda al enviar y vuelve en la misma tarea y el mismo caso', () => {
    expect(guardarParaReintento('f10', '5', { a: 'x', b: true, c: '3', d: null })).toBe(true);
    expect(recuperarParaReintento('f10', '5')).toEqual({ a: 'x', b: true, c: '3', d: null });
  });
  it('no cruza casos ni tareas', () => {
    guardarParaReintento('f10', '5', { a: 'x' });
    expect(recuperarParaReintento('f10', '6')).toBeNull();
    expect(recuperarParaReintento('f1', '5')).toBeNull();
  });
  it('solo escalares: un objeto o un archivo no llega al disco', () => {
    guardarParaReintento('f1', '5', { a: 'x', archivo: { contenido: 'AAAA' } as never, lista: [1] as never });
    expect(window.localStorage.getItem('ep033-reintento-f1-5')).not.toContain('AAAA');
    expect(recuperarParaReintento('f1', '5')).toEqual({ a: 'x' });
  });
  it('olvidar borra', () => {
    guardarParaReintento('f10', '5', { a: 'x' });
    olvidarReintento('f10', '5');
    expect(window.localStorage.length).toBe(0);
  });
  it('caduca: pasado su plazo no revive y se borra del navegador', () => {
    guardarParaReintento('f10', '5', { a: 'x' });
    const k = window.localStorage.key(0)!;
    const viejo = new Date(Date.now() - (VIGENCIA_REINTENTO_HORAS * 3_600_000 + 1000)).toISOString();
    window.localStorage.setItem(k, JSON.stringify({ valores: { a: 'x' }, guardadoEn: viejo }));
    expect(recuperarParaReintento('f10', '5')).toBeNull();
    expect(window.localStorage.length).toBe(0);
  });
  it('una fecha futura o ilegible no cuenta como reciente', () => {
    for (const fecha of [new Date(Date.now() + 3_600_000).toISOString(), 'ayer']) {
      window.localStorage.setItem('ep033-reintento-f10-5', JSON.stringify({ valores: { a: 'x' }, guardadoEn: fecha }));
      expect(recuperarParaReintento('f10', '5')).toBeNull();
    }
  });
  it('una forma con claves de más o corrupta se descarta y se borra', () => {
    window.localStorage.setItem('ep033-reintento-f10-5', JSON.stringify({ valores: {}, guardadoEn: new Date().toISOString(), documentos: ['AAAA'] }));
    expect(recuperarParaReintento('f10', '5')).toBeNull();
    window.localStorage.setItem('ep033-reintento-f10-5', 'no es json');
    expect(recuperarParaReintento('f10', '5')).toBeNull();
    expect(window.localStorage.length).toBe(0);
  });
  it('el barrido mata lo caducado y lo ilegible, y deja el vigente de otro caso', () => {
    guardarParaReintento('f10', '9', { a: 'vivo' });
    window.localStorage.setItem('ep033-reintento-f10-1', 'basura');
    window.localStorage.setItem('ep033-reintento-f10-2', JSON.stringify({ valores: {}, guardadoEn: '2020-01-01T00:00:00Z' }));
    window.localStorage.setItem('otra-cosa', 'intacta');
    expect(purgarReintentos()).toBe(2);
    expect(recuperarParaReintento('f10', '9')).toEqual({ a: 'vivo' });
    expect(window.localStorage.getItem('otra-cosa')).toBe('intacta');
  });
  it('sin caso no guarda ni recupera', () => {
    expect(guardarParaReintento('f10', undefined, { a: 'x' })).toBe(false);
    expect(recuperarParaReintento('f10', null)).toBeNull();
  });
});

describe('abrirTareaConRechazo: lo que la pantalla hace al abrirse', () => {
  const rutas = ['d.plazo', 'd.nota'];
  const iniciales = { 'd.plazo': '', 'd.nota': '' };
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());
  const servidor = (cuerpo: unknown, estado = 200) => vi.stubGlobal('fetch', vi.fn(async () => json(cuerpo, estado)));

  it('devuelta: recupera lo tecleado, solo en claves que la pantalla tiene, y pone la frase junto al campo', async () => {
    guardarParaReintento('t', '9', { 'd.plazo': '36', 'd.nota': 'hola', 'd.ajena': 'x' });
    servidor({ rechazos: [{ campo: 'plazo', motivo: 'no-vigente' }] });
    const r = await abrirTareaConRechazo({ tarea: 't', caso: '9', rutas, iniciales });
    expect(r.estado).toBe('devuelta');
    expect(r.devuelta).toBe(true);
    expect(r.sinComprobar).toBe(false);
    expect(r.valores).toEqual({ 'd.plazo': '36', 'd.nota': 'hola' });
    expect(r.motivos).toEqual({ 'd.plazo': 'no-vigente' });
  });
  it('devuelta pero sin nada guardado: los valores iniciales', async () => {
    servidor({ rechazos: [{ campo: 'plazo', motivo: 'sin-elegir' }] });
    const r = await abrirTareaConRechazo({ tarea: 't', caso: '9', rutas, iniciales });
    expect(r.valores).toEqual(iniciales);
  });
  it('normal: no hay rechazo, no se recupera nada y lo guardado se BORRA', async () => {
    guardarParaReintento('t', '9', { 'd.plazo': '36' });
    servidor({ rechazos: [] });
    const r = await abrirTareaConRechazo({ tarea: 't', caso: '9', rutas, iniciales });
    expect(r).toEqual({ estado: 'normal', devuelta: false, sinComprobar: false, valores: iniciales, motivos: {}, generales: [] });
    expect(window.localStorage.length).toBe(0);
  });
  it('sin comprobar: dice que no pudo, no recupera ni borra', async () => {
    guardarParaReintento('t', '9', { 'd.plazo': '36' });
    servidor({}, 500);
    const r = await abrirTareaConRechazo({ tarea: 't', caso: '9', rutas, iniciales });
    expect(r.estado).toBe('sin-comprobar');
    expect(r.sinComprobar).toBe(true);
    expect(r.devuelta).toBe(false);
    expect(r.valores).toEqual(iniciales);
    expect(r.generales).toEqual([FRASE_SIN_COMPROBAR]);
    expect(recuperarParaReintento('t', '9')).toEqual({ 'd.plazo': '36' });
  });
  it('no mezcla casos: lo guardado de otro caso no se recupera', async () => {
    guardarParaReintento('t', '8', { 'd.plazo': '84' });
    servidor({ rechazos: [{ campo: 'plazo', motivo: 'no-vigente' }] });
    const r = await abrirTareaConRechazo({ tarea: 't', caso: '9', rutas, iniciales });
    expect(r.valores).toEqual(iniciales);
  });
});
