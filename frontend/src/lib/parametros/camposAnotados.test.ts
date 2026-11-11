import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, waitFor } from '@testing-library/svelte';
import CamposDeContrato from '$lib/ui/CamposDeContrato.svelte';
import { LecturaFallida, type LectorDeValores, type PeticionDeValores, type ValoresLeidos } from './opciones';
import { tecleadoDeEjemplo } from '$lib/ui/valores';

/**
 * Los campos anotados del contrato: el formulario pide las opciones al módulo con el
 * id de la TAREA, pinta el widget que dicta la regla por defecto y, si la lectura falla, no se vuelve
 * texto libre. Se mide por el DOM renderizado (lo que ve la persona) y por lo que se le pregunta al
 * módulo (lo que sale de la pantalla), no por las funciones internas.
 *
 * `lector` es un doble del módulo: la lectura real (`GET parametros/valores`) se mide contra el
 * runtime en el journey, no aquí. Lo que sí prueba este fichero es lo que la pantalla HACE con lo que
 * el módulo le responde, incluido cuando no responde.
 */

type Campo = {
  ruta: string; grupo: string; nombre: string; tipo: 'TEXT' | 'DECIMAL' | 'INTEGER' | 'BOOLEAN' | 'DATE' | 'FILE';
  multiple: boolean; obligatorio: string; requeridoSiempre: boolean; constraint: string;
  catalogo?: string; widget?: 'fichas' | 'desplegable' | 'autocompletar'; depende?: string; tope?: string;
};

const campo = (ruta: string, tipo: Campo['tipo'], constraint: string, extra: Partial<Campo> = {}): Campo => {
  const [grupo, nombre] = ruta.split('.');
  return { ruta, grupo, nombre, tipo, multiple: false, obligatorio: 'sí', requeridoSiempre: true, constraint, ...extra };
};

const ACTIVIDAD = campo('solicitud.motivoAusencia', 'TEXT', '∈ catálogo motivo_ausencia', { catalogo: 'motivo_ausencia' });
const PLAZO = campo('solicitud.plazoSolicitado', 'INTEGER', '∈ catálogo plazos_por_tipo; depende: solicitud.tipo', {
  catalogo: 'plazos_por_tipo', depende: 'solicitud.tipo',
});
const MONTO = campo('solicitud.anticipoSolicitado', 'DECIMAL', '> 0; tope: tope_importe_por_tipo; depende: solicitud.tipo', {
  tope: 'tope_importe_por_tipo', depende: 'solicitud.tipo',
});

const lista = (...codigos: string[]): ValoresLeidos => ({
  clase: 'LISTA',
  opciones: codigos.map((c) => ({ codigo: c, etiqueta: c.replace(/_/g, ' ').replace(/^./, (x) => x.toUpperCase()) })),
});
const muchas = (n: number): ValoresLeidos => lista(...Array.from({ length: n }, (_, i) => `op_${String(i + 1).padStart(2, '0')}`));

function lectorDe(respuestas: Record<string, ValoresLeidos | Error | ((p: PeticionDeValores) => ValoresLeidos | Error)>) {
  const llamadas: PeticionDeValores[] = [];
  const lector: LectorDeValores = vi.fn(async (p) => {
    llamadas.push(p);
    const r = respuestas[p.definicion];
    const v = typeof r === 'function' ? r(p) : r;
    if (v === undefined) throw new LecturaFallida('no-disponible', p.definicion);
    if (v instanceof Error) throw v;
    return v;
  });
  return { lector, llamadas };
}

afterEach(() => cleanup());

/** El control del campo YA con sus opciones (no el marcador deshabilitado «Cargando opciones…»). */
async function controlCargado(porId: (id: string) => HTMLElement, testid: string): Promise<HTMLElement> {
  let el: HTMLElement | undefined;
  await waitFor(() => {
    el = porId(testid);
    expect((el as HTMLSelectElement).disabled).not.toBe(true);
  });
  return el as HTMLElement;
}

describe('el widget lo dicta la regla por defecto, con las opciones del módulo', () => {
  it('pide la lista con el id de la tarea y sin padre, y pinta SOLO esas opciones', async () => {
    const { lector, llamadas } = lectorDe({ motivo_ausencia: lista('descanso', 'viaje', 'familia', 'otro', 'estudios', 'salud') });
    const { findByRole, container } = render(CamposDeContrato, { props: { campos: [ACTIVIDAD], valores: {}, tarea: '77', lector } });

    const select = await findByRole('combobox');
    expect(select.tagName).toBe('SELECT');
    // 6 opciones → desplegable; las opciones son exactamente las del módulo (más la vacía).
    const textos = [...container.querySelectorAll('option')].map((o) => o.textContent?.trim());
    expect(textos).toEqual(['Seleccione una opción', 'Descanso', 'Viaje', 'Familia', 'Otro', 'Estudios', 'Salud']);
    expect(llamadas).toEqual([{ definicion: 'motivo_ausencia', tarea: '77', padre: undefined }]);
  });

  it.each([
    [2, 'radiogroup'],
    [5, 'radiogroup'],
    [6, 'select'],
    [15, 'select'],
    [16, 'combobox-texto'],
    [40, 'combobox-texto'],
  ])('con %i opciones el control es %s (2–5 fichas, 6–15 desplegable, más de 15 autocompletar)', async (n, esperado) => {
    const { lector } = lectorDe({ motivo_ausencia: muchas(n) });
    const { getByTestId } = render(CamposDeContrato, { props: { campos: [ACTIVIDAD], valores: {}, tarea: '1', lector } });
    const control = await controlCargado(getByTestId, 'campo-solicitud-motivoAusencia');
    if (esperado === 'radiogroup') expect(control.getAttribute('role')).toBe('radiogroup');
    else if (esperado === 'select') expect(control.tagName).toBe('SELECT');
    else {
      expect(control.getAttribute('role')).toBe('combobox');
      expect(control.tagName).toBe('INPUT');
    }
  });

  it('un widget declarado por el contrato gana sobre la regla por defecto', async () => {
    const { lector } = lectorDe({ motivo_ausencia: muchas(3) });
    const declarado = { ...ACTIVIDAD, widget: 'desplegable' as const };
    const { getByTestId } = render(CamposDeContrato, { props: { campos: [declarado], valores: {}, tarea: '1', lector } });
    expect((await controlCargado(getByTestId, 'campo-solicitud-motivoAusencia')).tagName).toBe('SELECT');
  });

  it.each(['afijo', 'calendario', 'interruptor', 'no_existe'])(
    'un widget «%s» que no sirve para una lista es un error del contrato: avisa, no pinta otra cosa',
    async (widget) => {
      const { lector } = lectorDe({ motivo_ausencia: muchas(3) });
      const mal = { ...ACTIVIDAD, widget } as unknown as Campo;
      const { findByRole, container } = render(CamposDeContrato, { props: { campos: [mal], valores: {}, tarea: '1', lector } });
      expect((await findByRole('alert')).textContent).toContain('no se puede mostrar');
      expect(container.querySelector('select, input, [role="radiogroup"]')).toBeNull();
    },
  );

  it('mientras llegan las opciones el campo está deshabilitado y lo dice (no es una caja vacía)', async () => {
    let resolver!: (v: ValoresLeidos) => void;
    const lector: LectorDeValores = () => new Promise((r) => (resolver = r));
    const { getByTestId, findByText } = render(CamposDeContrato, { props: { campos: [ACTIVIDAD], valores: {}, tarea: '1', lector } });
    const select = getByTestId('campo-solicitud-motivoAusencia') as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    expect(select.textContent).toContain('Cargando opciones');
    resolver(muchas(7));
    await waitFor(() => expect((getByTestId('campo-solicitud-motivoAusencia') as HTMLSelectElement).disabled).toBe(false));
    expect(await findByText('Op 01')).toBeTruthy();
  });
});

describe('la lectura falla y el campo NO se vuelve texto libre', () => {
  it.each([
    ['el módulo responde 403/500', new LecturaFallida('no-disponible', 'motivo_ausencia')],
    ['no hay red', new LecturaFallida('sin-respuesta', 'motivo_ausencia')],
    ['la respuesta es ilegible', new LecturaFallida('formato', 'motivo_ausencia')],
  ])('si %s: aviso visible, ningún campo de texto, y nada de la causa técnica', async (_caso, fallo) => {
    const { lector } = lectorDe({ motivo_ausencia: fallo });
    const { findByRole, container, queryByRole } = render(CamposDeContrato, {
      props: { campos: [ACTIVIDAD], valores: {}, tarea: '77', lector },
    });
    const aviso = await findByRole('alert');
    expect(aviso.textContent).toContain('No se pudieron cargar las opciones de «Motivo ausencia»');
    expect(aviso.textContent).toContain('No se puede enviar');
    // El defecto que el módulo corrige: una caja de texto donde debía haber una lista.
    expect(container.querySelector('input[type="text"], input:not([type]), textarea')).toBeNull();
    expect(queryByRole('textbox')).toBeNull();
    expect(queryByRole('combobox')).toBeNull();
    // El aviso no nombra la definición, la tarea ni el motivo técnico.
    expect(aviso.textContent).not.toMatch(/motivo_ausencia|403|500|formato|no-disponible|sin-respuesta|77/);
  });

  it('sin id de tarea no hay con qué pedir: avisa y bloquea, no inventa una lista', async () => {
    const { lector } = lectorDe({ motivo_ausencia: muchas(3) });
    const { findByRole } = render(CamposDeContrato, { props: { campos: [ACTIVIDAD], valores: {}, lector } });
    expect((await findByRole('alert')).textContent).toContain('No se pudieron cargar');
    expect(lector).not.toHaveBeenCalled();
  });

  it('en el formulario de instanciación (sin tarea) pide con el id de la definición del proceso', async () => {
    const { lector, llamadas } = lectorDe({ motivo_ausencia: muchas(6), tope_importe_por_tipo: { clase: 'PARAMETRO', valor: '100' } });
    const sinDepender = { ...MONTO, depende: undefined };
    const { findByRole } = render(CamposDeContrato, {
      props: { campos: [ACTIVIDAD, sinDepender], valores: {}, instanciacion: '6152430123456789012', lector },
    });
    expect((await findByRole('combobox')).tagName).toBe('SELECT');
    await waitFor(() => expect(llamadas).toHaveLength(2));
    expect(llamadas).toEqual([
      { definicion: 'motivo_ausencia', tarea: undefined, instanciacion: '6152430123456789012', padre: undefined },
      { definicion: 'tope_importe_por_tipo', tarea: undefined, instanciacion: '6152430123456789012', padre: undefined },
    ]);
  });

  it('una lista madre sin ninguna opción vigente no se puede elegir: es un fallo, no una pantalla vacía', async () => {
    const { lector } = lectorDe({ motivo_ausencia: lista() });
    const { findByRole } = render(CamposDeContrato, { props: { campos: [ACTIVIDAD], valores: {}, tarea: '1', lector } });
    expect((await findByRole('alert')).textContent).toContain('No hay opciones vigentes para «Motivo ausencia»');
  });

  it('Reintentar vuelve a pedir y, si ahora responde, el campo se recupera', async () => {
    let intentos = 0;
    const lector: LectorDeValores = vi.fn(async (p) => {
      intentos += 1;
      if (intentos === 1) throw new LecturaFallida('sin-respuesta', p.definicion);
      return muchas(7);
    });
    const { findByRole, findByTestId, getByTestId } = render(CamposDeContrato, {
      props: { campos: [ACTIVIDAD], valores: {}, tarea: '1', lector },
    });
    await findByRole('alert');
    (getByTestId('campo-solicitud-motivoAusencia-reintentar') as HTMLButtonElement).click();
    expect((await findByTestId('campo-solicitud-motivoAusencia')).tagName).toBe('SELECT');
    expect(intentos).toBe(2);
  });
});

describe('la cascada cambia plazo y tope con el tipo', () => {
  const respuestas = {
    plazos_por_tipo: (p: PeticionDeValores) => (p.padre === 'anual' ? lista('12', '24', '36', '48', '60') : lista()),
    tope_importe_por_tipo: (p: PeticionDeValores): ValoresLeidos => ({
      clase: 'PARAMETRO',
      valor: p.padre === 'anual' ? '2000000.00' : '1000000.00',
      unidad: 'USD',
    }),
  };

  it('con tipo anual: plazos anuales y máximo anual; los dos pedidos CON el padre', async () => {
    const { lector, llamadas } = lectorDe(respuestas);
    const { getByTestId, findByTestId } = render(CamposDeContrato, {
      props: { campos: [PLAZO, MONTO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(getByTestId('campo-solicitud-plazoSolicitado').getAttribute('role')).toBe('radiogroup'));
    await findByTestId('campo-solicitud-anticipoSolicitado');
    expect(llamadas).toEqual(
      expect.arrayContaining([
        { definicion: 'plazos_por_tipo', tarea: '9', padre: 'anual' },
        { definicion: 'tope_importe_por_tipo', tarea: '9', padre: 'anual' },
      ]),
    );
  });

  it('al cambiar el tipo a horas el plazo DESAPARECE y el máximo pasa a ser el de horas', async () => {
    const { lector, llamadas } = lectorDe(respuestas);
    const { rerender, queryByTestId, getByTestId } = render(CamposDeContrato, {
      props: { campos: [PLAZO, MONTO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(getByTestId('campo-solicitud-plazoSolicitado').getAttribute('role')).toBe('radiogroup'));

    await rerender({ campos: [PLAZO, MONTO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'horas' } });

    await waitFor(() => expect(queryByTestId('campo-solicitud-plazoSolicitado')).toBeNull());
    expect(llamadas.some((l) => l.definicion === 'plazos_por_tipo' && l.padre === 'horas')).toBe(true);
    expect(llamadas.some((l) => l.definicion === 'tope_importe_por_tipo' && l.padre === 'horas')).toBe(true);
    // El máximo nuevo se aplica: 1.5 M supera el tope de horas (1 M) pero cabía en el anual (2 M).
    const monto = getByTestId('campo-solicitud-anticipoSolicitado') as HTMLInputElement;
    await waitFor(() => expect(monto.getAttribute('aria-describedby')).toBeTruthy());
    monto.value = '1500000';
    monto.dispatchEvent(new Event('input', { bubbles: true }));
    monto.dispatchEvent(new Event('blur', { bubbles: true }));
    await waitFor(() => expect(document.body.textContent).toContain('Supera el máximo de $1,000,000'));
  });

  it('sin tipo elegido ni dato del caso la cascada espera: no pide nada y lo dice', async () => {
    const { lector, llamadas } = lectorDe(respuestas);
    const { getByTestId } = render(CamposDeContrato, { props: { campos: [PLAZO], valores: {}, tarea: '9', lector } });
    const select = getByTestId('campo-solicitud-plazoSolicitado') as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    expect(select.textContent).toContain('Elija primero');
    expect(llamadas).toEqual([]);
  });

  it('lo que ya estaba elegido y deja de existir para el nuevo padre se vacía, no se conserva en silencio', async () => {
    const { lector } = lectorDe({
      plazos_por_tipo: (p) => (p.padre === 'anual' ? lista('12', '24', '36', '48', '60') : lista('6', '9')),
    });
    const valores = { 'solicitud.plazoSolicitado': '48' };
    const { rerender, getByTestId } = render(CamposDeContrato, {
      props: { campos: [PLAZO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(getByTestId('campo-solicitud-plazoSolicitado').getAttribute('role')).toBe('radiogroup'));
    await rerender({ campos: [PLAZO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'otro' } });
    await waitFor(() => expect((valores as Record<string, unknown>)['solicitud.plazoSolicitado']).toBe(''));
  });

  it('si el máximo no se puede leer, el monto no se pinta como «sin tope»: avisa', async () => {
    const { lector } = lectorDe({ tope_importe_por_tipo: new LecturaFallida('no-disponible', 'tope_importe_por_tipo') });
    const { findByText } = render(CamposDeContrato, {
      props: { campos: [MONTO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    expect(await findByText(/No se pudo comprobar el máximo de «Anticipo solicitado»/, { exact: false })).toBeTruthy();
  });

  it('un tipo sin tope definido tampoco pasa en silencio (fallo cerrado)', async () => {
    const { lector } = lectorDe({ tope_importe_por_tipo: { clase: 'PARAMETRO', valor: null } });
    const { findByText } = render(CamposDeContrato, {
      props: { campos: [MONTO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    expect(await findByText(/No hay un máximo definido para «Anticipo solicitado»/, { exact: false })).toBeTruthy();
  });
});

describe('la cascada nace del campo elegido y no se deja engañar por una respuesta vieja', () => {
  const TIPO = campo('solicitud.tipo', 'TEXT', '∈ catálogo tipo_de_permiso', { catalogo: 'tipo_de_permiso' });
  const plazos = (p: PeticionDeValores): ValoresLeidos => (p.padre === 'anual' ? lista('12', '24', '36') : lista('6', '9'));

  it('lo que la persona eligió en el campo madre manda sobre el dato del caso', async () => {
    const { lector, llamadas } = lectorDe({ tipo_de_permiso: lista('anual', 'horas'), plazos_por_tipo: plazos });
    // El caso dice «anual», pero la persona eligió «horas» en el campo: el padre es lo elegido.
    const valores = { 'solicitud.tipo': 'horas' };
    const { getByTestId } = render(CamposDeContrato, {
      props: { campos: [TIPO, PLAZO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(getByTestId('campo-solicitud-plazoSolicitado').getAttribute('role')).toBe('radiogroup'));
    expect(llamadas.filter((l) => l.definicion === 'plazos_por_tipo')).toEqual([
      { definicion: 'plazos_por_tipo', tarea: '9', padre: 'horas' },
    ]);
  });

  it('elegir otro tipo en el campo vuelve a pedir los plazos con el padre nuevo', async () => {
    const { lector, llamadas } = lectorDe({ tipo_de_permiso: lista('anual', 'horas'), plazos_por_tipo: plazos });
    const valores: Record<string, string> = { 'solicitud.tipo': 'anual' };
    const { rerender, getByTestId } = render(CamposDeContrato, { props: { campos: [TIPO, PLAZO], valores, tarea: '9', lector } });
    await waitFor(() => expect(getByTestId('campo-solicitud-plazoSolicitado').getAttribute('role')).toBe('radiogroup'));
    await rerender({ campos: [TIPO, PLAZO], valores: { 'solicitud.tipo': 'horas' }, tarea: '9', lector });
    await waitFor(() =>
      expect(llamadas.some((l) => l.definicion === 'plazos_por_tipo' && l.padre === 'horas')).toBe(true),
    );
  });

  it('una respuesta que llega TARDE de un padre anterior no pisa la del padre actual', async () => {
    const pendientes: Record<string, (v: ValoresLeidos) => void> = {};
    const lector: LectorDeValores = (p) => new Promise((r) => (pendientes[p.padre ?? ''] = r));
    const { rerender, getByTestId } = render(CamposDeContrato, {
      props: { campos: [PLAZO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(pendientes.anual).toBeTypeOf('function'));
    await rerender({ campos: [PLAZO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'otro' } });
    await waitFor(() => expect(pendientes.otro).toBeTypeOf('function'));
    pendientes.otro(lista('6', '9'));
    await waitFor(() => expect(getByTestId('campo-solicitud-plazoSolicitado').getAttribute('role')).toBe('radiogroup'));
    // La del padre ANTERIOR llega después y es de otro tipo: no puede reemplazar a la vigente.
    pendientes.anual(lista('12', '24', '36', '48', '60', '72', '84'));
    await new Promise((r) => setTimeout(r, 10));
    const fichas = [...document.querySelectorAll('[data-testid="campo-solicitud-plazoSolicitado"] [role="radio"]')];
    expect(fichas.map((t) => t.textContent?.trim())).toEqual(['6', '9']);
  });

  it('un monto que superaba el máximo NUEVO (cambió el tipo) se vacía y se dice por qué', async () => {
    const { lector } = lectorDe({
      tope_importe_por_tipo: (p) => ({ clase: 'PARAMETRO', valor: p.padre === 'anual' ? '2000000.00' : '1000000.00', unidad: 'USD' }),
    });
    const valores = { 'solicitud.anticipoSolicitado': tecleadoDeEjemplo(1500000) };
    const { rerender, getByTestId } = render(CamposDeContrato, {
      props: { campos: [MONTO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(document.body.textContent).not.toContain('Cargando el máximo'));
    expect(document.body.textContent).not.toContain('escríbalo de nuevo');
    await rerender({ campos: [MONTO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'horas' } });
    await waitFor(() => expect(document.body.textContent).toContain('El monto supera el máximo de la opción elegida: escríbalo de nuevo.'));
    expect((valores as Record<string, unknown>)['solicitud.anticipoSolicitado']).toBeNull();
    expect(getByTestId('campo-solicitud-anticipoSolicitado')).toBeTruthy();
  });

  it('un monto que sigue cabiendo bajo el máximo nuevo se conserva', async () => {
    const { lector } = lectorDe({
      tope_importe_por_tipo: (p) => ({ clase: 'PARAMETRO', valor: p.padre === 'anual' ? '2000000.00' : '1000000.00', unidad: 'USD' }),
    });
    const monto = tecleadoDeEjemplo(800000);
    const valores = { 'solicitud.anticipoSolicitado': monto };
    const { rerender } = render(CamposDeContrato, {
      props: { campos: [MONTO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await rerender({ campos: [MONTO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'horas' } });
    await new Promise((r) => setTimeout(r, 20));
    expect((valores as Record<string, unknown>)['solicitud.anticipoSolicitado']).toBe(monto);
    expect(document.body.textContent).not.toContain('escríbalo de nuevo');
  });
});

describe('la ayuda del monto dice «Máximo $X», con el tope que sirve el módulo', () => {
  const topes = (p: PeticionDeValores): ValoresLeidos => ({ clase: 'PARAMETRO', valor: p.padre === 'anual' ? '2000000.00' : '1000000.00', unidad: 'USD' });

  it('el máximo del tipo elegido, con el formato de la galería; y cambia con el tipo', async () => {
    const { lector } = lectorDe({ tope_importe_por_tipo: topes });
    const valores = {};
    const { rerender } = render(CamposDeContrato, { props: { campos: [MONTO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } } });
    await waitFor(() => expect(document.body.textContent).toContain('Máximo $2,000,000'));
    await rerender({ campos: [MONTO], valores, tarea: '9', lector, contexto: { 'solicitud.tipo': 'horas' } });
    await waitFor(() => expect(document.body.textContent).toContain('Máximo $1,000,000'));
    expect(document.body.textContent).not.toContain('Máximo $2,000,000');
  });

  it('sin máximo que decir (lectura caída, tope sin valor o unidad que no es la moneda del proyecto) no pinta ninguna cifra inventada', async () => {
    for (const resp of [undefined, () => ({ clase: 'PARAMETRO', valor: null, unidad: 'USD' }) as ValoresLeidos, () => ({ clase: 'PARAMETRO', valor: '5000000.00', unidad: 'EUR' }) as ValoresLeidos]) {
      const { lector } = lectorDe(resp ? { tope_importe_por_tipo: resp } : {});
      const { unmount } = render(CamposDeContrato, { props: { campos: [MONTO], valores: {}, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } } });
      await new Promise((r) => setTimeout(r, 30));
      expect(document.body.textContent).not.toMatch(/Máximo \$/);
      unmount();
    }
  });
});

describe('la anotación no se cuela en la ayuda que lee la persona', () => {
  it('ni «∈ catálogo», ni «tope:», ni «depende:» ni el código de la definición salen en pantalla', async () => {
    const { lector } = lectorDe({
      motivo_ausencia: muchas(7),
      tope_importe_por_tipo: { clase: 'PARAMETRO', valor: '1000000.00', unidad: 'USD' },
    });
    const { container } = render(CamposDeContrato, {
      props: { campos: [ACTIVIDAD, MONTO], valores: { 'solicitud.anticipoSolicitado': tecleadoDeEjemplo(1) }, tarea: '9', lector, contexto: { 'solicitud.tipo': 'anual' } },
    });
    await waitFor(() => expect(container.querySelector('select')).not.toBeNull());
    const texto = container.textContent ?? '';
    expect(texto).not.toMatch(/catálogo|tope:|depende:|widget:|motivo_ausencia|tope_importe_por_tipo/i);
  });
});

describe('el motivo por el que el servidor devolvió la tarea, junto al campo', () => {
  const montar = (motivos: Record<string, import('./rechazo').Motivo>, valores: Record<string, string | number | boolean | null>) => {
    const { lector } = lectorDe({ plazos_por_tipo: lista('12', '24', '36') });
    return render(CamposDeContrato, {
      campos: [PLAZO], valores, tarea: '42', lector, motivos, contexto: { 'solicitud.tipo': 'anual' },
    } as never);
  };

  it('pone la frase del motivo con la etiqueta del campo, y solo en el campo al que se refiere', async () => {
    const { findByText, queryByText } = montar({ 'solicitud.plazoSolicitado': 'no-vigente' }, { 'solicitud.plazoSolicitado': '36' });
    expect(await findByText('La opción elegida en «Plazo solicitado» ya no está disponible. Elija otra.')).toBeTruthy();
    expect(queryByText(/supera el máximo/)).toBeNull();
  });

  it('un motivo de otro campo no se pinta aquí', async () => {
    const { container } = montar({ 'solicitud.otroCampo': 'no-vigente' }, { 'solicitud.plazoSolicitado': '36' });
    await waitFor(() => expect(container.querySelector('select, [role="radiogroup"]')).not.toBeNull());
    expect(container.textContent).not.toMatch(/ya no está disponible/);
  });

  it('sin motivos no hay frase (el defecto de siempre no cambia)', async () => {
    const { container } = montar({}, { 'solicitud.plazoSolicitado': '36' });
    await waitFor(() => expect(container.querySelector('select, [role="radiogroup"]')).not.toBeNull());
    expect(container.textContent).not.toMatch(/ya no está disponible|Elija otra/);
  });
});
