/**
 * Permisos, importación y traza, probados como se ejecutan: el contenedor
 * real con un doble del kit. Lo que el doble NO prueba —la matriz de permisos, el candado de la cadena, la
 * verificación real— lo miden las pruebas del módulo y el journey.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { FalloDelKit } from './kit';
import * as csv from './csv';
import { ACT_COMITE, ACT_PAGO, DELEGACIONES, kitDeEjemplo, PROCESO, type OpcionesDelKit, type PerfilDeEjemplo } from './ejemplo';
import { hashDe, type Ruta } from './ruta';
import * as T from './textos';
import type { Delegacion } from './tipos';

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

async function abrir(ruta: Ruta, perfil: PerfilDeEjemplo = 'superadministracion', extra: Partial<OpcionesDelKit> = {}) {
  location.hash = hashDe(ruta);
  const kit = kitDeEjemplo({ perfil, ...extra });
  render(Parametros, { kit });
  await screen.findAllByRole('tab');
  return kit;
}
const motivo = (m: string) => fireEvent.input(screen.getAllByLabelText(/Motivo/).at(-1)!, { target: { value: m } });

const delegacion = (extra: Partial<Delegacion>): Delegacion => ({ ...DELEGACIONES[0], ...extra });
const MANANA = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

describe('permisos', () => {
  it('lista las vigentes y las vencidas o revocadas, con a quién, sobre qué y hasta cuándo', async () => {
    await abrir({ vista: 'permisos' }, 'superadministracion', {
      delegaciones: [
        delegacion({ sujetoUsuarioId: 7 }),
        delegacion({ sujetoUsuarioId: 8, actividades: [ACT_PAGO], vigenteHasta: MANANA }),
        delegacion({ sujetoUsuarioId: 1, activo: false }),
      ],
    });
    const tabla = await screen.findByTestId('tabla-de-permisos');
    const filas = within(tabla).getAllByTestId('delegacion');
    expect(filas).toHaveLength(2);
    expect(filas[0].textContent).toContain('Luis Gil');
    expect(filas[0].textContent).toContain('Becas de estudio · todo el proceso');
    expect(filas[0].textContent).toContain('Sin fecha de fin');
    expect(filas[1].textContent).toContain('Ana Pérez');
    expect(filas[1].textContent).toContain('Verificar los soportes y preparar el pago');
    expect(filas[1].textContent).toContain(T.VENCE_MANANA);
    expect(screen.getByRole('button', { name: /Vigentes · 2/ })).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: /Vencidas y revocadas · 1/ }));
    expect(within(screen.getByTestId('tabla-de-permisos')).getAllByTestId('delegacion')).toHaveLength(1);
    expect(screen.getByText(T.REVOCAR_TIENE_EFECTO_INMEDIATO)).toBeInTheDocument();
  });

  it('revocar pide motivo y mueve la delegación a vencidas y revocadas', async () => {
    const kit = await abrir({ vista: 'permisos' });
    await screen.findByTestId('tabla-de-permisos');
    await fireEvent.click(screen.getByRole('button', { name: T.REVOCAR }));
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(kit.escrituras.filter((e) => e.operacion === 'revocar')).toHaveLength(0);
    await motivo('Cambió de puesto.');
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    await waitFor(() => expect(kit.escrituras.filter((e) => e.operacion === 'revocar')).toHaveLength(1));
    expect(kit.escrituras.at(-1)?.datos).toMatchObject({ motivo: 'Cambió de puesto.' });
    await waitFor(() => expect(screen.getByRole('button', { name: /Vigentes · 0/ })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Vencidas y revocadas · 1/ })).toBeInTheDocument();
  });

  it('tras la revocación el guardado de quien tenía la sesión abierta se rechaza con una explicación', async () => {
    const kit = await abrir({ vista: 'definicion', definicion: 'vias_pago', ambito: { proceso: PROCESO, actividad: ACT_PAGO }, pestana: 'valores' }, 'delegado', {
      fallos: { cambiar: new FalloDelKit('SIN_PERMISO') },
    });
    await screen.findByTestId('vista-lista');
    await fireEvent.click(within(screen.getByTestId('opcion-cheque')).getByRole('button', { name: T.EDITAR }));
    await fireEvent.input(screen.getByLabelText(/Nombre que ve el formulario/), { target: { value: 'Cheque de caja' } });
    await motivo('Ajuste.');
    await fireEvent.click(screen.getByRole('button', { name: T.GUARDAR_CAMBIO }));
    expect(await screen.findByText(T.FALLO_SIN_PERMISO)).toBeInTheDocument();
    expect((await kit.valores('vias_pago')).filas.find((f) => f.codigo === 'cheque')?.etiqueta).toBe('Cheque de administración');
  });

  it('prorrogar una delegación que vence mañana la deja como propuesta y mantiene su fecha', async () => {
    const kit = await abrir({ vista: 'permisos' }, 'superadministracion', { delegaciones: [delegacion({ vigenteHasta: MANANA })] });
    await screen.findByTestId('tabla-de-permisos');
    expect(screen.getByText(T.VENCE_MANANA)).toBeInTheDocument();
    const fechaAntes = screen.getByTestId('delegacion').textContent;
    await fireEvent.click(screen.getByRole('button', { name: T.PRORROGAR }));
    const campo = within(screen.getByTestId('confirmacion-permiso')).getByLabelText(new RegExp(T.NUEVA_FECHA));
    await fireEvent.input(campo, { target: { value: '31/12/2030' } });
    await fireEvent.blur(campo);
    await motivo('Cobertura del cierre anual.');
    await fireEvent.click(screen.getByTestId('confirmar-permiso'));
    await waitFor(() => expect(kit.escrituras.filter((e) => e.operacion === 'delegar')).toHaveLength(1));
    const d = (kit.escrituras.find((e) => e.operacion === 'delegar')?.datos as { d: { vigenteHasta: string } }).d;
    expect(d.vigenteHasta).toMatch(/^2030-12-31/);
    // La delegación vigente no cambió de fecha: la prórroga espera su aprobación.
    expect(screen.getByTestId('delegacion').textContent).toBe(fechaAntes);
    expect((await kit.propuestas('PENDIENTE')).propuestas.some((p) => p.accion === 'DELEGAR')).toBe(true);
  });

  it('delegar un rol dentro de un grupo sobre dos actividades queda como propuesta', async () => {
    const kit = await abrir({ vista: 'permisos' });
    await screen.findByTestId('tabla-de-permisos');
    await fireEvent.click(screen.getByTestId('delegar'));
    const vista = await screen.findByTestId('vista-nueva-delegacion');
    expect(vista.textContent).toContain(T.QUE_PODRAN_HACER);
    expect(vista.textContent).toContain(T.QUE_NO_PODRAN_HACER);
    // Sin completar nada no se envía.
    await fireEvent.click(screen.getByTestId('enviar-delegacion'));
    expect(await screen.findByText(T.ERROR_ELIGE_GRUPO)).toBeInTheDocument();
    expect(kit.escrituras.filter((e) => e.operacion === 'delegar')).toHaveLength(0);

    await fireEvent.input(screen.getByRole('combobox', { name: /Grupo/ }), { target: { value: 'evaluacion' } });
    await fireEvent.click(await screen.findByRole('option', { name: 'Academia › Evaluacion' }));
    await fireEvent.input(screen.getByRole('combobox', { name: /^Rol/ }), { target: { value: 'Jefe' } });
    await fireEvent.click(await screen.findByRole('option', { name: 'Jefe evaluacion' }));
    await fireEvent.click(screen.getByLabelText(T.INCLUIR_SUBGRUPOS));
    await fireEvent.change(screen.getByLabelText(/^Proceso/), { target: { value: PROCESO } });
    await fireEvent.click(screen.getByRole('radio', { name: T.ALCANCE_ALGUNAS }));
    const acts = within(screen.getByTestId('actividades'));
    await fireEvent.click(acts.getByLabelText('Aprobar beca completa'));
    await fireEvent.click(acts.getByLabelText('Aprobar beca extraordinaria'));
    await motivo('Cobertura del cierre anual: Evaluación ajusta sus parámetros.');
    await fireEvent.click(screen.getByTestId('enviar-delegacion'));

    await waitFor(() => expect(kit.escrituras.filter((e) => e.operacion === 'delegar')).toHaveLength(1));
    const d = (kit.escrituras.find((e) => e.operacion === 'delegar')?.datos as { d: Record<string, unknown> }).d;
    expect(d).toMatchObject({ tipoSujeto: 'GRUPO_ROL', sujetoGrupoId: 11, sujetoRolId: 21, incluyeSubgrupos: true, proceso: PROCESO });
    expect(d.actividades).toEqual(expect.arrayContaining([expect.stringContaining('Comite academico'), expect.stringContaining('Decanato')]));
    // Visible como propuesta en Aprobaciones (la de otra persona superadministradora la aprobará).
    const propuesta = (await kit.propuestas('PENDIENTE')).propuestas.find((p) => p.accion === 'DELEGAR');
    expect(propuesta?.motivo).toContain('Cobertura del cierre anual');
    expect(await screen.findByTestId('vista-permisos')).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('tab', { name: /Aprobaciones/ }));
    const propias = await screen.findByTestId('grupo-propias');
    expect(propias.textContent).toContain('Permisos');
  });

  it('una persona delegada no ve la pestaña Permisos y la dirección directa no le abre nada ni consulta delegaciones', async () => {
    location.hash = hashDe({ vista: 'permisos' });
    const kit = kitDeEjemplo({ perfil: 'delegado' });
    const espia = vi.spyOn(kit, 'delegaciones');
    render(Parametros, { kit });
    expect(await screen.findByTestId('seccion-no-disponible')).toBeInTheDocument();
    expect(screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim())).not.toContain('Permisos');
    expect(espia).not.toHaveBeenCalled();
  });

  it('la consulta tampoco abre importar por la dirección directa', async () => {
    location.hash = hashDe({ vista: 'importar' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'consulta' }) });
    expect(await screen.findByTestId('seccion-no-disponible')).toBeInTheDocument();
  });
});

const subir = async (texto: string) => {
  const input = await screen.findByTestId('fichero-csv');
  await fireEvent.change(input, { target: { files: [new File([texto], 'duraciones.csv', { type: 'text/csv' })] } });
};
const CSV_CON_DE_TODO = 'definicion,codigo,etiqueta,activo\nvias_pago,leasing,Arrendamiento,\nvias_pago,cheque,Cheque certificado,\nvias_pago,efectivo,,no\nvias_pago,transferencia,Transferencia a la cuenta del becario,\nvias_pago,leasing,Otra vez,\n';
const CSV_LIMPIO = 'definicion,codigo,etiqueta,activo\nvias_pago,leasing,Arrendamiento,\nvias_pago,cheque,Cheque certificado,\nporcentaje_beca,*,30,\n';

describe('importar', () => {
  it('la vista previa enseña los recuentos por tipo, la fila con error explicada y la baja como desactivación, sin aplicar nada', async () => {
    const kit = await abrir({ vista: 'importar' });
    await subir(CSV_CON_DE_TODO);
    const resumen = await screen.findByTestId('resumen-de-importacion');
    expect(resumen.textContent).toContain('1 alta');
    expect(resumen.textContent).toContain('1 cambio');
    expect(resumen.textContent).toContain('1 baja');
    expect(resumen.textContent).toContain('1 sin cambios');
    expect(screen.getByTestId('filas-de-importacion').textContent).toContain('Se da de baja (no se borra)');
    expect(screen.getByText(T.erroresTitulo(1 as never))).toBeInTheDocument();
    expect(screen.getByRole('alert', { hidden: true }) ?? true).toBeTruthy();
    expect(document.body.textContent).toContain('Código repetido: ya está en la fila');
    // El crudo del kit no se cuela: ni el nombre interno del campo ni la fila sin explicar.
    expect(document.body.textContent).not.toMatch(/codigo: |definicion: /);
    // Con errores no se confirma, y no se aplicó nada.
    expect(screen.queryByTestId('confirmar-importacion')).toBeNull();
    expect(kit.escrituras.filter((e) => e.operacion === 'importar')).toHaveLength(0);
  });

  it('un fichero limpio se confirma con motivo; las filas de impacto alto quedan como propuesta', async () => {
    const kit = await abrir({ vista: 'importar' });
    await subir(CSV_LIMPIO);
    await screen.findByTestId('resumen-de-importacion');
    expect(screen.getByTestId('confirmar-importacion').textContent).toContain('Importar 3 cambios');
    await fireEvent.click(screen.getByTestId('confirmar-importacion'));
    expect(await screen.findByText(T.ERROR_MOTIVO)).toBeInTheDocument();
    expect(kit.escrituras.filter((e) => e.operacion === 'importar')).toHaveLength(0);
    await fireEvent.input(screen.getByLabelText(new RegExp(T.MOTIVO_DE_LA_IMPORTACION)), { target: { value: 'Nuevas duraciones aprobadas en comité.' } });
    await fireEvent.click(screen.getByTestId('confirmar-importacion'));
    expect(await screen.findByTestId('importacion-aplicada')).toBeInTheDocument();
    expect(screen.getByTestId('importacion-aplicada').textContent).toContain(T.IMPORTACION_PROPUESTAS);
    expect(document.body.textContent).toContain('IMP-2026-1020-01');
    expect(kit.escrituras.find((e) => e.operacion === 'importar')?.datos).toMatchObject({ motivo: 'Nuevas duraciones aprobadas en comité.' });
  });

  it('si lo guardado cambió desde la vista previa, se enseña la nueva sin aplicar nada', async () => {
    const vistaNueva = { resumen: { altas: 0, cambios: 0, bajas: 0, sinCambios: 1, propuestas: 0, errores: 0 }, filas: [{ fila: 2, clase: 'SIN_CAMBIOS' as const, definicion: 'vias_pago', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: 'cheque', detalle: 'coincide' }], huella: 'otra' };
    await abrir({ vista: 'importar' }, 'superadministracion', { fallos: { importar: new FalloDelKit('CONFLICTO', null, null, null, null, vistaNueva) } });
    await subir(CSV_LIMPIO);
    await screen.findByTestId('resumen-de-importacion');
    await fireEvent.input(screen.getByLabelText(new RegExp(T.MOTIVO_DE_LA_IMPORTACION)), { target: { value: 'Motivo.' } });
    await fireEvent.click(screen.getByTestId('confirmar-importacion'));
    expect(await screen.findByText(T.IMPORTACION_CAMBIO_TITULO)).toBeInTheDocument();
    expect(screen.queryByTestId('importacion-aplicada')).toBeNull();
  });

  it('un fichero que el kit no entiende se dice en lenguaje de negocio', async () => {
    await abrir({ vista: 'importar' }, 'superadministracion', { fallos: { vistaPreviaDeImportacion: new FalloDelKit('VALIDACION', 'csv', 'columna desconocida') } });
    await subir('x');
    expect(await screen.findByText(T.CSV_RECHAZADO)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('columna desconocida');
  });
});

/** El filtro «Persona» busca en el servidor mientras se escribe y filtra por el USUARIO de la persona elegida. */
async function filtrarPorPersona(texto: string, opcion: RegExp): Promise<void> {
  await fireEvent.input(screen.getByRole('combobox', { name: /Persona/ }), { target: { value: texto } });
  await fireEvent.click(await screen.findByRole('option', { name: opcion }));
  await waitFor(() => expect(screen.getByTestId('eventos').textContent).not.toContain('Marta Rivas'));
}

describe('traza', () => {
  it('filtrar por una persona deja solo sus entradas, en lenguaje de negocio, sin forma de editar o borrar', async () => {
    await abrir({ vista: 'traza' });
    const eventos = await screen.findByTestId('eventos');
    expect(eventos.textContent).toContain('Ana Pérez');
    expect(eventos.textContent).toContain('Marta Rivas');
    await filtrarPorPersona('Ana', /Ana Pérez/);
    const solo = screen.getByTestId('eventos');
    expect(solo.textContent).toContain('Ana Pérez');
    expect(solo.textContent).not.toContain('Marta Rivas');
    expect(solo.textContent).toContain('Motivo:');
    expect(solo.textContent).not.toMatch(/persistenceVersion|"etiqueta"|\{/);
    expect(screen.queryByRole('button', { name: /editar|borrar|eliminar|suprimir/i })).toBeNull();
    expect(screen.getByText(T.entradasTitulo(2 as never))).toBeInTheDocument();
  });

  it('el filtro por acción y por lista o parámetro combinan', async () => {
    await abrir({ vista: 'traza' });
    await screen.findByTestId('eventos');
    await fireEvent.change(screen.getByLabelText(T.FILTRO_ACCION), { target: { value: 'aprobaciones' } });
    expect(screen.getByTestId('eventos').textContent).toContain('aprobó');
    expect(screen.getByTestId('eventos').textContent).not.toContain('desactivó');
    await fireEvent.change(screen.getByLabelText(T.FILTRO_ACCION), { target: { value: 'todas' } });
    await fireEvent.input(screen.getByLabelText(T.FILTRO_QUE), { target: { value: 'pago' } });
    expect(screen.getByTestId('eventos').textContent).toContain('desactivó');
    expect(screen.getByTestId('eventos').textContent).not.toContain('aprobó');
    await fireEvent.input(screen.getByLabelText(T.FILTRO_QUE), { target: { value: 'nada que ver' } });
    expect(await screen.findByTestId('traza-vacia')).toBeInTheDocument();
  });

  it('una entrada interior manipulada: dice que la cadena no es coherente y desde qué entrada', async () => {
    await abrir({ vista: 'traza' }, 'superadministracion', { cadenaRota: true });
    await fireEvent.click(await screen.findByTestId('verificar'));
    const r = await screen.findByTestId('resultado-de-verificacion');
    expect(screen.getByText(T.CADENA_ROTA_TITULO)).toBeInTheDocument();
    expect(r.textContent).toContain('Deja de casar desde la entrada del 27 sep 2026');
  });

  it('cadena íntegra: «coherente desde la última verificación» y enuncia lo que detecta y lo que no', async () => {
    await abrir({ vista: 'traza' });
    await fireEvent.click(await screen.findByTestId('verificar'));
    const r = await screen.findByTestId('resultado-de-verificacion');
    expect(screen.getByText(T.CADENA_COHERENTE_TITULO)).toBeInTheDocument();
    expect(r.textContent).toContain('detecta una edición o un borrado en medio de la cadena');
    expect(r.textContent).toContain('no detecta una reescritura completa ni el recorte de las últimas entradas');
  });

  it('exportar la traza filtrada descarga solo lo que se ve, sin columnas técnicas ni JSON', async () => {
    await abrir({ vista: 'traza' });
    await screen.findByTestId('eventos');
    await filtrarPorPersona('Ana', /Ana Pérez/);
    await fireEvent.click(screen.getByTestId('exportar-traza'));
    await waitFor(() => expect(csv.descargar).toHaveBeenCalled());
    const [nombre, contenido] = (csv.descargar as unknown as { mock: { calls: string[][] } }).mock.calls[0];
    expect(nombre).toBe(T.NOMBRE_DEL_FICHERO_DE_TRAZA);
    expect(contenido).toContain('Ana Pérez');
    expect(contenido).not.toContain('Marta Rivas');
    expect(contenido.replace(/^﻿/, '').split('\r\n')[0]).toBe(T.COLUMNAS_DE_HISTORIAL.join(','));
    for (const tecnico of ['persistence', 'hash', '{', 'claveNegocio']) expect(contenido).not.toContain(tecnico);
  });

  it('la consulta ve y exporta la traza pero no la verifica (decisión pendiente, lo más conservador)', async () => {
    await abrir({ vista: 'traza' }, 'consulta');
    await screen.findByTestId('eventos');
    expect(screen.queryByTestId('verificar')).toBeNull();
    expect(screen.getByTestId('exportar-traza')).toBeInTheDocument();
  });
});

void ACT_COMITE;
