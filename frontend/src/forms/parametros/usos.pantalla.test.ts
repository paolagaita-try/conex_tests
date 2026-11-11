/**
 * «Dónde se usa» con el contrato REAL de `GET parametros/usos`: códigos fuera de la lista de hasta 255 caracteres, la
 * fila «sin elegir», el resto agrupado en `otros`, y códigos que son nombres del prototipo de JavaScript o HTML. Ninguno rompe
 * la tabla, se pinta como otra cosa ni se pierde.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { kitDeEjemplo } from './ejemplo';
import { hashDe } from './ruta';
import PanelDeUsos from './componentes/PanelDeUsos.svelte';
import { crearKit } from './api';
import { usosVM } from './usos';
import { construirVistaPrevia } from './importar';
import { FalloDelKit, type Usos } from './kit';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const LARGO = `largo_${'x'.repeat(249)}`; // 255 caracteres exactos
const usos: Usos = {
  lugares: [{ tipo: 'FORMULARIO', titulo: 'Preparar el pago', detalle: 'Se usó 3 veces.' }],
  expedientes: [
    { codigo: 'transferencia', guardados: '198', enCurso: '11' },
    { codigo: 'constructor', guardados: '7', enCurso: '1', fueraDeLista: true, etiqueta: 'constructor' },
    { codigo: '__proto__', guardados: '5', enCurso: '0', fueraDeLista: true, etiqueta: '__proto__' },
    { codigo: '<script>alert(1)</script>', guardados: '2', enCurso: '0', fueraDeLista: true, etiqueta: '<script>alert(1)</script>' },
    { codigo: LARGO, guardados: '1', enCurso: '0', fueraDeLista: true, etiqueta: `${LARGO.slice(0, 64)}…`, truncado: true },
    { codigo: '', guardados: '40', enCurso: '9', sinElegir: true },
  ],
  otros: { guardados: '5225', enCurso: '12' },
};
const etiquetas = new Map<string, string>([['transferencia', 'Transferencia a la cuenta del becario']]);

describe('filas de «Dónde se usa» con lo que el kit sirve de verdad', () => {
  const vm = usosVM(usos, etiquetas, new Set());

  it('un código que se llama como algo del prototipo se pinta como lo que es', () => {
    const opciones = vm.expedientes.map((e) => e.opcion);
    expect(opciones).toContain('constructor');
    expect(opciones).toContain('__proto__');
    for (const o of opciones) expect(o).not.toMatch(/function Object|\[object Object\]|native code/);
  });

  it('un código muy largo se pinta con su etiqueta recortada, no entero', () => {
    const fila = vm.expedientes.find((e) => e.codigo === LARGO)!;
    expect(fila.opcion.length).toBeLessThanOrEqual(65);
    expect(fila.opcion.endsWith('…')).toBe(true);
    expect(fila.codigo.length).toBe(255); // el código completo sigue ahí (título), único
  });

  it('la fila de quienes aún no eligieron se lee «Sin elegir»', () => {
    expect(vm.expedientes.find((e) => e.codigo === '')!.opcion).toBe('Sin elegir');
  });

  it('las claves son los códigos reales: únicas', () => {
    expect(new Set(vm.expedientes.map((e) => e.clave)).size).toBe(vm.expedientes.length);
  });

  it('la tabla los pinta: etiqueta en la fila, código completo en el título, «otros» como fila agregada, y un <script> como texto', () => {
    render(PanelDeUsos, { usos: vm });
    const tabla = screen.getByTestId('usos-expedientes');
    expect(tabla.textContent).toContain('Transferencia a la cuenta del becario');
    expect(tabla.textContent).toContain('Sin elegir');
    expect(tabla.textContent).not.toContain(LARGO); // el código de 255 caracteres no sale en la fila…
    expect(tabla.querySelector(`td[title="${LARGO}"]`)).not.toBeNull(); // …está en el título
    expect(tabla.querySelector('script')).toBeNull();
    expect(tabla.textContent).toContain('<script>alert(1)</script>');
    const otros = within(screen.getByTestId('usos-otros'));
    expect(otros.getByText('Otros códigos fuera de la lista (agrupados)')).toBeInTheDocument();
    expect(screen.getByTestId('usos-otros').textContent).toContain('5225');
  });

  it('con solo «otros» tampoco dice «nadie la usa»', () => {
    render(PanelDeUsos, { usos: usosVM({ lugares: [], expedientes: [], otros: { guardados: '10', enCurso: '1' } }, new Map(), new Set()) });
    expect(screen.queryByTestId('usos-vacio')).toBeNull();
    expect(screen.getByTestId('usos-otros')).toBeInTheDocument();
  });
});

describe('el cliente lee la respuesta real de GET parametros/usos', () => {
  it('conserva etiqueta, truncado, fueraDeLista, sinElegir y otros; ignora `agrupados`; un tipo nuevo pasa tal cual', async () => {
    const cuerpo = {
      lugares: [{ tipo: 'NOTIFICACION', titulo: 'Aviso', detalle: 'x' }],
      expedientes: [
        { codigo: 'a', guardados: '1', enCurso: '2' },
        { codigo: LARGO, guardados: '3', enCurso: '4', fueraDeLista: true, etiqueta: `${LARGO.slice(0, 64)}…`, truncado: true },
        { codigo: '', guardados: '5', enCurso: '6', sinElegir: true },
      ],
      otros: { guardados: '7', enCurso: '8', agrupados: 12 },
    };
    vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify(/parametros\/usos/.test(String(url)) ? cuerpo : {}), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const r = await crearKit().usos('modalidad_sintetico');
    expect(r.lugares[0]).toEqual({ tipo: 'NOTIFICACION', titulo: 'Aviso', detalle: 'x' });
    expect(r.expedientes[1]).toMatchObject({ codigo: LARGO, fueraDeLista: true, truncado: true, etiqueta: `${LARGO.slice(0, 64)}…` });
    expect(r.expedientes[2]).toMatchObject({ codigo: '', sinElegir: true });
    expect(r.otros).toEqual({ guardados: '7', enCurso: '8' });
    expect((vi.mocked(fetch).mock.calls[0]![0] as string)).toContain('/extension/parametros/usos?definicion=modalidad_sintetico');
  });

  it('una respuesta con la forma rota lanza (la pantalla dice «no pudimos leer»), no inventa un vacío', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ lugares: 'no', expedientes: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    await expect(crearKit().usos('x')).rejects.toBeTruthy();
  });
});

describe('la baja dice qué expedientes la usan; la aprobación dice dónde se usa', () => {
  const DEFS = [{ codigo: 'vias_pago', nombre: 'Vías de pago' }] as never;
  const previa = { resumen: { altas: 0, cambios: 0, bajas: 1, sinCambios: 0, propuestas: 0, errores: 0 }, huella: 'h', filas: [{ fila: 2, clase: 'BAJA', definicion: 'vias_pago', proceso: '*', actividad: '*', codigoPadre: '*', codigo: 'efectivo', detalle: 'se desactiva, no se borra' }] } as never;
  const conExpedientes: Usos = { lugares: [], expedientes: [{ codigo: 'efectivo', guardados: '73', enCurso: '4' }] };

  it('la fila de baja enseña cuántos expedientes guardados y en curso usan la opción', () => {
    const f = construirVistaPrevia(previa, DEFS, {}, {}, new Map([['vias_pago', conExpedientes]])).filas[0]!;
    expect(f.detalle).toContain('La usan 73 expedientes guardados y 4 en curso.');
  });
  it('si el kit no cuenta esa lista, dice que no lo sabe (no afirma «0»)', () => {
    const f = construirVistaPrevia(previa, DEFS, {}, {}, new Map([['vias_pago', { lugares: [], expedientes: [] }]])).filas[0]!;
    expect(f.detalle).toContain('no sabemos cuántos la usan');
    expect(f.detalle).not.toMatch(/La usan 0/);
  });
  it('si la lectura de usos falla, lo dice', () => {
    expect(construirVistaPrevia(previa, DEFS, {}, {}, new Map([['vias_pago', 'error']])).filas[0]!.detalle).toContain('No pudimos leer qué expedientes la usan');
  });
});

describe('en pantalla, con el doble del kit', () => {
  const rica: Usos = { lugares: [{ tipo: 'REGLA', titulo: 'Tramo de aprobación', detalle: 'Se usó 9 veces.' }], expedientes: [{ codigo: 'efectivo', guardados: '73', enCurso: '4' }] };

  it('Aprobaciones: la propuesta abierta dice dónde se usa y, sin conteo por parámetro, que el módulo no lo informa', async () => {
    location.hash = hashDe({ vista: 'aprobaciones' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', usos: { lugares: rica.lugares, expedientes: [] } }) });
    const panel = await screen.findByTestId('usos-de-la-aprobacion', {}, { timeout: 3000 });
    await waitFor(() => expect(panel.textContent).toContain('Tramo de aprobación'));
    expect(screen.getByTestId('expedientes-afectados-sin-dato')).toBeInTheDocument();
  });

  it('Aprobaciones: si la lectura de usos falla, lo dice (no un vacío)', async () => {
    location.hash = hashDe({ vista: 'aprobaciones' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', fallos: { usos: new FalloDelKit('SERVIDOR') } }) });
    const panel = await screen.findByTestId('usos-de-la-aprobacion', {}, { timeout: 3000 });
    await waitFor(() => expect(panel.textContent).toContain('No pudimos leer dónde se usa'));
  });

  it('Importar: la fila de baja de una opción en uso enseña sus expedientes', async () => {
    location.hash = hashDe({ vista: 'importar' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', usos: rica }) });
    const csv = 'definicion,codigo,etiqueta,activo\nvias_pago,efectivo,,no\n';
    await fireEvent.change(await screen.findByTestId('fichero-csv'), { target: { files: [new File([csv], 'a.csv', { type: 'text/csv' })] } });
    await waitFor(() => expect(screen.getByTestId('filas-de-importacion').textContent).toContain('La usan 73 expedientes guardados y 4 en curso.'));
  });

  it('Importar: si la lectura de usos falla, la baja lo dice (no inventa «0 expedientes»)', async () => {
    location.hash = hashDe({ vista: 'importar' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', fallos: { usos: new FalloDelKit('SERVIDOR') } }) });
    const csv = 'definicion,codigo,etiqueta,activo\nvias_pago,efectivo,,no\n';
    await fireEvent.change(await screen.findByTestId('fichero-csv'), { target: { files: [new File([csv], 'a.csv', { type: 'text/csv' })] } });
    await waitFor(() => expect(screen.getByTestId('filas-de-importacion').textContent).toContain('No pudimos leer qué expedientes la usan'));
    expect(screen.getByTestId('filas-de-importacion').textContent).not.toMatch(/La usan 0/);
  });
});
