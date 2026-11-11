/**
 * Un parámetro y Aprobaciones, probados como se ejecutan: el contenedor real con un doble del
 * kit que aplica el doble control (quien propone no aprueba) y el bloqueo optimista. Lo que el doble NO prueba
 * —que el kit real se comporte así— lo miden las pruebas del módulo y el journey.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { FalloDelKit } from './kit';
import { kitDeEjemplo, PROCESO, type OpcionesDelKit, type PerfilDeEjemplo } from './ejemplo';
import { hashDe, type Ruta } from './ruta';
import * as T from './textos';

vi.mock('./csv', async (original) => {
  const real = await original<typeof import('./csv')>();
  return { ...real, descargar: vi.fn(() => true) };
});

beforeEach(() => {
  location.hash = '';
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const EN_PROCESO = { proceso: PROCESO, actividad: '*' };

async function abrir(ruta: Ruta, perfil: PerfilDeEjemplo = 'superadministracion', extra: Partial<OpcionesDelKit> = {}) {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil, ...extra });
  render(Parametros, { kit });
  await screen.findByTestId(ruta.vista === 'aprobaciones' ? 'vista-aprobaciones' : 'vista-parametro').catch(() => undefined);
  return kit;
}
const parametro = (definicion: string) => ({ vista: 'definicion' as const, definicion, ambito: EN_PROCESO, pestana: 'valores' as const });

const escribirValor = (v: string) => fireEvent.input(screen.getByTestId('campo-valor'), { target: { value: v } });
const escribirMotivo = (m: string) => fireEvent.input(screen.getByLabelText(/Motivo del cambio/), { target: { value: m } });

describe('enviar a aprobación un cambio ya revisado', () => {
  it('la cadena de herencia dice qué vale en cada sitio y de dónde viene', async () => {
    await abrir(parametro('porcentaje_beca'), 'superadministracion', { sinPropuestas: [1] });
    const cadena = screen.getByTestId('cadena');
    expect(cadena.textContent).toContain('40 %');
    expect(cadena.textContent).toContain('35 %');
    expect(cadena.textContent).toContain('Valor base de la organización');
    expect(cadena.textContent).toContain(T.APLICA_AQUI_LO_EDITAS_AHORA);
    expect(cadena.textContent).toContain(T.HEREDAN_DEL_PROCESO);
    expect(screen.getByText(T.CHIP_IMPACTO_ALTO)).toBeInTheDocument();
    // El rango permitido se dice de entrada, en la ayuda del campo.
    expect(screen.getByText('Entre 20 % y 60 %, con un decimal como máximo.')).toBeInTheDocument();
  });

  it('se revisa el efecto antes de enviar y, al enviar, queda «Cambio por aprobar» sin dejar de valer 35 %', async () => {
    const kit = await abrir(parametro('porcentaje_beca'), 'superadministracion', { sinPropuestas: [1] });
    await escribirValor('30');
    await escribirMotivo('Acuerdo CA-2026-14: el consejo académico reduce el tope.');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));

    // La revisión enseña el efecto y el aviso del doble control; todavía no se escribió nada.
    const revision = await screen.findByTestId('revision');
    expect(revision.textContent).toContain('Enviar a aprobación');
    expect(within(revision).getAllByText('35 %').length).toBeGreaterThan(0);
    expect(screen.getByTestId('valor-propuesto').textContent).toBe('30 %');
    expect(revision.textContent).toContain('Mientras nadie lo apruebe, sigue valiendo 35 %.');
    expect(revision.textContent).toContain('conservan el valor con el que se decidieron');
    expect(screen.getByText(T.DOBLE_CONTROL_TITULO)).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);

    await fireEvent.click(screen.getByTestId('enviar-a-aprobacion'));
    await waitFor(() => expect(screen.queryByTestId('revision')).toBeNull());
    expect(kit.escrituras).toHaveLength(1);
    expect(kit.escrituras[0].datos).toMatchObject({ accion: 'EDITAR', definicion: 'porcentaje_beca', codigo: '*', datos: { valor: '30' }, motivo: 'Acuerdo CA-2026-14: el consejo académico reduce el tope.' });

    // Pendiente: sigue valiendo 35 %, el campo no se edita y se ofrece retirar.
    expect(screen.getByText(T.CHIP_POR_APROBAR_SUPERADMINISTRACION)).toBeInTheDocument();
    expect(screen.getByTestId('aviso-pendiente').textContent).toMatch(/Propusiste\s*35 %\s*30 %/);
    expect(screen.getByTestId('aviso-pendiente').textContent).toContain('sigue valiendo 35 %');
    expect(screen.getByTestId('campo-valor')).toBeDisabled();
    expect(screen.getByText(T.NO_SE_PUEDE_EDITAR_MIENTRAS)).toBeInTheDocument();
    expect(screen.getByTestId('retirar')).toBeInTheDocument();
    expect(screen.queryByTestId('revisar-cambio')).toBeNull();
  });

  it('«Volver a editar» conserva lo escrito', async () => {
    const kit = await abrir(parametro('porcentaje_beca'), 'superadministracion', { sinPropuestas: [1] });
    await escribirValor('30');
    await escribirMotivo('Circular.');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    await fireEvent.click(await screen.findByTestId('volver-a-editar'));
    expect((screen.getByTestId('campo-valor') as HTMLInputElement).value).toBe('30');
    expect((screen.getByLabelText(/Motivo del cambio/) as HTMLTextAreaElement).value).toBe('Circular.');
    expect(kit.escrituras).toHaveLength(0);
  });

  it('sin motivo no se revisa ni se envía nada', async () => {
    const kit = await abrir(parametro('porcentaje_beca'), 'superadministracion', { sinPropuestas: [1] });
    await escribirValor('30');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(screen.queryByTestId('revision')).toBeNull();
    expect(kit.escrituras).toHaveLength(0);
  });

  it('un parámetro de impacto normal se guarda sin diálogo de revisión', async () => {
    const kit = await abrir(parametro('tope_beca_modalidad'), 'superadministracion');
    // por modalidad: el primero (curso) con su valor propio
    await escribirValor('2500000');
    await escribirMotivo('Ajuste de la modalidad.');
    await fireEvent.click(screen.getByTestId('guardar-valor'));
    await waitFor(() => expect(kit.escrituras).toHaveLength(1));
    expect(screen.queryByTestId('revision')).toBeNull();
    expect(kit.escrituras[0].datos).toMatchObject({ accion: 'EDITAR', codigoPadre: 'curso', datos: { valor: '2500000' } });
  });
});

describe('un valor fuera del rango de la definición', () => {
  it('el campo muestra el rango permitido, no deja continuar y no se crea ninguna propuesta', async () => {
    const kit = await abrir(parametro('porcentaje_beca'), 'superadministracion', { sinPropuestas: [1] });
    await escribirValor('65');
    await escribirMotivo('Circular.');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    const campo = screen.getByTestId('campo-valor');
    await waitFor(() => expect(campo).toHaveAttribute('aria-invalid', 'true'));
    expect(screen.getAllByText('Entre 20 % y 60 %, con un decimal como máximo.').length).toBeGreaterThan(0);
    expect(screen.queryByTestId('revision')).toBeNull();
    expect(kit.escrituras).toHaveLength(0);
  });

  it('un valor que no es número tampoco', async () => {
    const kit = await abrir(parametro('porcentaje_beca'), 'superadministracion', { sinPropuestas: [1] });
    await escribirValor('mucho');
    await escribirMotivo('Circular.');
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    expect(await screen.findByText('Escribe solo números, con punto para los decimales.')).toBeInTheDocument();
    expect(kit.escrituras).toHaveLength(0);
  });
});

describe('otra persona propuso antes sobre el mismo parámetro', () => {
  it('no se envía, se cuenta quién propuso y cuándo, y se conserva lo escrito', async () => {
    const kit = await abrir(parametro('tope_coordinador'), 'superadministracion', { sinPropuestas: [2] });
    await escribirValor('1800000');
    await escribirMotivo('Ajuste por inflación acumulada 2025–2026 aprobado en consejo académico.');

    // Mientras la persona escribe, Luis envía la suya.
    kit.publicarPropuesta(2);
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    await fireEvent.click(await screen.findByTestId('enviar-a-aprobacion'));

    const aviso = await screen.findByTestId('conflicto');
    expect(aviso.textContent).toContain('Luis Gil propuso');
    expect(aviso.textContent).toMatch(/US\$1,500,000\s*US\$1,650,000/);
    expect(aviso.textContent).toContain('Tu propuesta no se envió, para no pisar la suya');
    expect(screen.getByText(T.OTRA_PERSONA_CAMBIO_TITULO)).toBeInTheDocument();

    // Lo escrito se conserva, solo lectura, para reutilizarlo.
    expect((screen.getByTestId('valor-escrito') as HTMLInputElement).value).toBe('1800000');
    expect((screen.getByLabelText(T.TU_MOTIVO) as HTMLTextAreaElement).value).toBe('Ajuste por inflación acumulada 2025–2026 aprobado en consejo académico.');
    expect(screen.getByText(T.LO_CONSERVAMOS)).toBeInTheDocument();

    // No se creó ninguna propuesta nueva (la del doble sigue siendo la única).
    expect((await kit.propuestas('PENDIENTE')).propuestas.filter((p) => p.definicion === 'tope_coordinador')).toHaveLength(1);

    // Puede revisar la ajena o cargar el valor actual.
    expect(screen.getByTestId('revisar-su-propuesta')).toBeInTheDocument();
    await fireEvent.click(screen.getByTestId('cargar-valor-actual'));
    await waitFor(() => expect(screen.queryByTestId('conflicto')).toBeNull());
    expect((screen.getByTestId('campo-valor') as HTMLInputElement).value).toBe('1500000');
  });

  it('«Revisar su propuesta» lleva a Aprobaciones', async () => {
    const kit = await abrir(parametro('tope_coordinador'), 'superadministracion', { sinPropuestas: [2] });
    await escribirValor('1800000');
    await escribirMotivo('Ajuste.');
    kit.publicarPropuesta(2);
    await fireEvent.click(screen.getByTestId('revisar-cambio'));
    await fireEvent.click(await screen.findByTestId('enviar-a-aprobacion'));
    await fireEvent.click(await screen.findByTestId('revisar-su-propuesta'));
    expect(await screen.findByTestId('vista-aprobaciones')).toBeInTheDocument();
  });
});

describe('otra persona aprueba el cambio', () => {
  it('abre el cambio con su antes → después, motivo y quién lo propuso; al aprobar se aplica y el contador baja', async () => {
    const kit = await abrir({ vista: 'aprobaciones' });
    // Contador antes: 1 (el de Luis); el de la propia Marta no cuenta.
    expect(screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim())).toContain('Aprobaciones 1');
    const esperan = screen.getByTestId('grupo-esperan');
    expect(esperan.textContent).toContain('Tope de aprobación del coordinador');
    const detalle = screen.getByTestId('detalle-de-aprobacion');
    expect(detalle.textContent).toContain('US$1,500,000');
    expect(detalle.textContent).toContain('US$1,650,000');
    expect(detalle.textContent).toContain('Luis Gil');
    expect(detalle.textContent).toContain('Acta del consejo académico 2026-09');
    expect(detalle.textContent).toContain('Al aprobar, el cambio se aplica al instante');

    await fireEvent.click(screen.getByTestId('aprobar'));
    await waitFor(() => expect(kit.escrituras.some((e) => e.operacion === 'decidir')).toBe(true));
    expect(kit.escrituras.find((e) => e.operacion === 'decidir')?.datos).toMatchObject({ decision: 'APROBAR' });

    expect(await screen.findByText(T.APROBADO_Y_APLICADO)).toBeInTheDocument();
    // Aplicado al instante: el valor cambió, las dos firmas están en la traza y el contador bajó.
    expect((await kit.valores('tope_coordinador')).filas[0].valor).toBe('1650000');
    const entrada = (await kit.traza({}, 0)).elementos.find((e) => e.accion === 'APROBAR');
    expect(JSON.stringify(entrada?.valorNuevo)).toContain('luis.gil');
    expect(JSON.stringify(entrada?.valorNuevo)).toContain('marta.rivas');
    await waitFor(() => expect(screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim())).toContain('Aprobaciones'));
    expect(screen.queryByTestId('grupo-esperan')).toBeNull();
    expect(screen.getByTestId('grupo-resueltas').textContent).toContain('Tope de aprobación del coordinador');
  });
});

describe('otra persona rechaza el cambio', () => {
  it('rechazar sin comentario no llega a la API: el comentario es obligatorio y el cambio sigue pendiente', async () => {
    const kit = await abrir({ vista: 'aprobaciones' });
    await fireEvent.click(screen.getByTestId('rechazar'));
    expect(await screen.findByText(T.ERROR_COMENTARIO)).toBeInTheDocument();
    expect(kit.escrituras.filter((e) => e.operacion === 'decidir')).toHaveLength(0);
    expect(screen.getByTestId('grupo-esperan').textContent).toContain('Tope de aprobación del coordinador');
    // Un comentario de solo espacios tampoco vale.
    await fireEvent.input(screen.getByLabelText(/Tu comentario/), { target: { value: '   ' } });
    await fireEvent.click(screen.getByTestId('rechazar'));
    expect(kit.escrituras.filter((e) => e.operacion === 'decidir')).toHaveLength(0);
  });

  it('con comentario: el parámetro conserva su valor, el rechazo queda en la traza y el contador baja', async () => {
    const kit = await abrir({ vista: 'aprobaciones' });
    await fireEvent.input(screen.getByLabelText(/Tu comentario/), { target: { value: 'Falta el acta firmada.' } });
    await fireEvent.click(screen.getByTestId('rechazar'));
    expect(await screen.findByText(T.RECHAZADO_QUEDA_EN_LA_TRAZA)).toBeInTheDocument();
    expect(kit.escrituras.find((e) => e.operacion === 'decidir')?.datos).toMatchObject({ decision: 'RECHAZAR', comentario: 'Falta el acta firmada.' });
    expect((await kit.valores('tope_coordinador')).filas[0].valor).toBe('1500000');
    const entrada = (await kit.traza({}, 0)).elementos.find((e) => e.accion === 'RECHAZAR');
    expect(entrada?.motivo).toBe('Falta el acta firmada.');
    expect(screen.queryByTestId('grupo-esperan')).toBeNull();
  });
});

describe('nadie aprueba lo que propuso', () => {
  it('en un cambio propio «Aprobar y aplicar» va deshabilitado, con su explicación, y solo se puede retirar', async () => {
    const kit = await abrir({ vista: 'aprobaciones' }, 'delegado');
    // Luis ve el de Marta para aprobar y el suyo como propio.
    expect(screen.getByTestId('grupo-propias').textContent).toContain('Tope de aprobación del coordinador');
    await fireEvent.click(within(screen.getByTestId('grupo-propias')).getByRole('button', { name: /Tope de aprobación del coordinador/ }));
    const deshabilitado = await screen.findByTestId('aprobar-deshabilitado');
    expect(deshabilitado).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByText(T.NO_PUEDES_APROBAR_LO_TUYO)).toBeInTheDocument();
    expect(screen.getByText(T.LA_PROPUSISTE_TU_TITULO)).toBeInTheDocument();
    expect(screen.queryByTestId('aprobar')).toBeNull();
    expect(screen.queryByTestId('rechazar')).toBeNull();
    await fireEvent.click(deshabilitado);
    expect(kit.escrituras.filter((e) => e.operacion === 'decidir')).toHaveLength(0);
    expect(screen.getByTestId('retirar-propuesta')).toBeInTheDocument();
  });

  it('retirar lo propio lo cierra y el valor no cambia', async () => {
    const kit = await abrir({ vista: 'aprobaciones' }, 'delegado');
    await fireEvent.click(within(screen.getByTestId('grupo-propias')).getByRole('button', { name: /Tope de aprobación del coordinador/ }));
    await fireEvent.click(await screen.findByTestId('retirar-propuesta'));
    expect(await screen.findByText(T.PROPUESTA_RETIRADA)).toBeInTheDocument();
    expect(kit.escrituras.find((e) => e.operacion === 'decidir')?.datos).toMatchObject({ decision: 'RETIRAR' });
    expect((await kit.valores('tope_coordinador')).filas[0].valor).toBe('1500000');
  });

  it('si la orden de aprobar llega igualmente, la API la rechaza: el cambio sigue pendiente y se explica', async () => {
    // El servidor revocó el permiso mientras la pantalla seguía abierta: ofrece «Aprobar», el servidor dice que no.
    const kit = await abrir({ vista: 'aprobaciones' }, 'superadministracion', { fallos: { decidir: new FalloDelKit('SIN_PERMISO') } });
    await fireEvent.click(screen.getByTestId('aprobar'));
    expect(await screen.findByText(T.FALLO_SIN_PERMISO)).toBeInTheDocument();
    expect(screen.getByTestId('grupo-esperan').textContent).toContain('Tope de aprobación del coordinador');
    expect((await kit.valores('tope_coordinador')).filas[0].valor).toBe('1500000');
  });

  it('el doble del servidor rechaza al proponente que aprueba lo suyo (la regla B4 que la pantalla obedece)', async () => {
    const kit = kitDeEjemplo({ perfil: 'superadministracion' });
    const suya = (await kit.propuestas('PENDIENTE')).propuestas.find((p) => p.proponente === 'marta.rivas')!;
    await expect(kit.decidir(suya, 'APROBAR', '')).rejects.toMatchObject({ clase: 'SIN_PERMISO' });
  });
});

describe('quién puede qué en Aprobaciones', () => {
  it('la consulta no tiene la pestaña Aprobaciones', async () => {
    location.hash = '';
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'consulta' }) });
    await screen.findByText('Hola, Pedro Almonte');
    expect(screen.getAllByRole('tab').map((t) => t.textContent?.trim())).not.toContain('Aprobaciones');
  });

  it('con nada que aprobar, lo dice en humano', async () => {
    await abrir({ vista: 'aprobaciones' }, 'superadministracion', { sinPropuestas: [1, 2, 3, 4] });
    expect(await screen.findByTestId('aprobaciones-vacio')).toBeInTheDocument();
    expect(screen.getByText(T.NADA_PARA_APROBAR_TITULO)).toBeInTheDocument();
  });
});
