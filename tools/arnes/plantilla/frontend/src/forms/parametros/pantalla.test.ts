/**
 * La aplicación de parámetros, probada como se ejecuta: el contenedor real con un `Kit` de ejemplo.
 * Mide lo que se puede medir sin runtime (en pantalla); el 403 de la API y la
 * fidelidad contra el prototipo se miden contra el runtime.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import { FalloDelKit } from './kit';
import * as csv from './csv';
import { kitDeEjemplo, type PerfilDeEjemplo } from './ejemplo';
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

async function abrir(perfil: PerfilDeEjemplo, opciones: Parameters<typeof kitDeEjemplo>[0] extends infer O ? Partial<O> : never = {}) {
  const kit = kitDeEjemplo({ perfil, ...opciones });
  const espiado = Object.fromEntries(Object.entries(kit).map(([k, v]) => [k, typeof v === 'function' ? vi.fn(v as (...a: unknown[]) => unknown) : v]));
  render(Parametros, { kit: espiado as unknown as typeof kit });
  return { kit: espiado as unknown as Record<string, ReturnType<typeof vi.fn>> };
}

describe('la superadministración ve todo lo que puede ajustar', () => {
  it('saluda, enseña el titular y los grupos por ámbito con lo que ve cada fila', async () => {
    await abrir('superadministracion');
    expect(await screen.findByText('Hola, Marta Rivas')).toBeInTheDocument();
    expect(screen.getByText('1 cambio espera tu aprobación.')).toBeInTheDocument();
    expect(screen.getByText(T.GRUPO_GLOBALES)).toBeInTheDocument();
    expect(screen.getByText('Becas de estudio · todo el proceso')).toBeInTheDocument();
    expect(screen.getByText('Inscripción a cursos · todo el proceso')).toBeInTheDocument();
    expect(screen.getByText(T.PROCESO_SIN_PARAMETROS_TITULO)).toBeInTheDocument();

    const porcentaje = screen.getByTestId('fila-porcentaje_beca');
    expect(within(porcentaje).getByText('Porcentaje máximo de beca')).toBeInTheDocument();
    expect(porcentaje.textContent).toContain('Parámetro · 35 %');
    expect(within(porcentaje).getByText(T.CHIP_IMPACTO_ALTO)).toBeInTheDocument();
    expect(within(porcentaje).getByText(T.CHIP_POR_APROBAR_SUPERADMINISTRACION)).toBeInTheDocument();

    const tipos = screen.getByTestId('fila-tipos_identificacion');
    expect(tipos.textContent).toContain('Lista · 3 opciones');

    const vias = screen.getByTestId('fila-vias_pago');
    expect(vias.textContent).toContain('Lista · 4 opciones, 1 inactiva');
  });

  it('muestra el contador de Aprobaciones y las cuatro pestañas de la superadministración', async () => {
    await abrir('superadministracion');
    await screen.findByText('Hola, Marta Rivas');
    const pestanas = screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim());
    expect(pestanas).toEqual(['Parámetros', 'Aprobaciones 1', 'Permisos', 'Traza']);
  });

  it('el filtro «Listas» quita los parámetros y «Parámetros» quita las listas', async () => {
    await abrir('superadministracion');
    await screen.findByText('Hola, Marta Rivas');
    await fireEvent.click(screen.getByRole('button', { name: T.SEGMENTOS_DE_SUPERADMINISTRACION.listas }));
    expect(screen.queryByTestId('fila-porcentaje_beca')).toBeNull();
    expect(screen.getByTestId('fila-tipos_identificacion')).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('button', { name: T.SEGMENTOS_DE_SUPERADMINISTRACION.parametros }));
    expect(screen.queryByTestId('fila-tipos_identificacion')).toBeNull();
    expect(screen.getByTestId('fila-porcentaje_beca')).toBeInTheDocument();
  });

  it('no pinta ningún código técnico como dato principal ni JSON', async () => {
    await abrir('superadministracion');
    await screen.findByText('Hola, Marta Rivas');
    const texto = document.body.textContent ?? '';
    for (const codigo of ['porcentaje_beca', 'tope_coordinador', 'vias_pago', 'persistenceVersion', '{"']) {
      expect(texto).not.toContain(codigo);
    }
    // ni los nombres del motor: «F10 Verificar integridad…»
    expect(texto).not.toMatch(/\bF1\d\b/);
  });
});

describe('la búsqueda no encuentra nada', () => {
  it('enseña el vacío aprobado, sin nombres técnicos, y la forma de volver a ver todo', async () => {
    await abrir('superadministracion');
    await screen.findByText('Hola, Marta Rivas');
    await fireEvent.input(screen.getByLabelText(T.BUSCAR_ROTULO), { target: { value: 'posgrado' } });
    const vacio = await screen.findByTestId('sin-resultados');
    expect(vacio.textContent).toContain('Nada coincide con «posgrado».');
    expect(vacio.textContent).toContain('no por el código técnico');
    expect(screen.queryByTestId('fila-porcentaje_beca')).toBeNull();
    for (const prohibido of ['persistence', 'porcentaje_beca', 'null', 'undefined']) expect(vacio.textContent).not.toContain(prohibido);

    await fireEvent.click(screen.getByRole('button', { name: T.VER_TODOS }));
    expect(screen.queryByTestId('sin-resultados')).toBeNull();
    expect(screen.getByTestId('fila-porcentaje_beca')).toBeInTheDocument();
  });

  it('buscar por el nombre que usa el negocio encuentra la lista', async () => {
    await abrir('superadministracion');
    await screen.findByText('Hola, Marta Rivas');
    await fireEvent.input(screen.getByLabelText(T.BUSCAR_ROTULO), { target: { value: 'PAGO' } });
    await waitFor(() => expect(screen.queryByTestId('fila-porcentaje_beca')).toBeNull());
    expect(screen.getByTestId('fila-vias_pago')).toBeInTheDocument();
  });
});

describe('el delegado ve lo suyo y lo global en solo lectura', () => {
  it('«Tus permisos» dice el proceso, el alcance y la vigencia; lo global va en solo lectura', async () => {
    await abrir('delegado');
    expect(await screen.findByText('Hola, Luis Gil')).toBeInTheDocument();
    expect(screen.getByText('Puedes editar los parámetros de Becas de estudio.')).toBeInTheDocument();
    const aviso = screen.getByText(T.TUS_PERMISOS).closest('.caja') as HTMLElement;
    expect(aviso.textContent).toContain('Becas de estudio');
    expect(aviso.textContent).toContain(T.TODAS_SUS_ACTIVIDADES);
    expect(aviso.textContent).toContain(T.SIN_FECHA_DE_FIN);
    expect(aviso.textContent).toContain('Lo demás lo ves en solo lectura');

    const global = screen.getByTestId('fila-tipos_identificacion');
    expect(within(global).getByText(T.CHIP_SOLO_LECTURA)).toBeInTheDocument();
    expect(global.textContent).toContain(T.VER);
    const suya = screen.getByTestId('fila-porcentaje_beca');
    expect(within(suya).queryByText(T.CHIP_SOLO_LECTURA)).toBeNull();
  });

  it('ve Aprobaciones y Traza, pero no Permisos; y no ve «Importar CSV»', async () => {
    await abrir('delegado');
    await screen.findByText('Hola, Luis Gil');
    const pestanas = screen.getAllByRole('tab').map((t) => t.textContent?.replace(/\s+/g, ' ').trim());
    expect(pestanas.some((p) => p?.startsWith('Aprobaciones'))).toBe(true);
    expect(pestanas).toContain('Traza');
    expect(pestanas).not.toContain('Permisos');
    expect(screen.queryByRole('button', { name: T.IMPORTAR_CSV })).toBeNull();
  });
});

describe('la persona becaria no entra por la dirección directa', () => {
  it('ante un 403 de la API la aplicación dice que no está disponible, sin nombrar nada, y no pide nada más', async () => {
    const { kit } = await abrir('cliente');
    expect(await screen.findByTestId('no-disponible')).toBeInTheDocument();
    expect(screen.getByText(T.NO_DISPONIBLE_TITULO)).toBeInTheDocument();
    const texto = document.body.textContent ?? '';
    for (const nombre of ['Becas', 'Becas', 'pago', 'Marta', 'Jorge', 'F10', 'Comité', 'Porcentaje']) expect(texto).not.toContain(nombre);
    // La primera lectura es el catálogo: rechazado, no se pide ni un valor, ni propuestas, ni traza.
    expect(kit.definiciones).toHaveBeenCalledTimes(1);
    for (const lectura of ['valores', 'propuestas', 'traza', 'procesos', 'editores']) expect(kit[lectura]).not.toHaveBeenCalled();
    // y no hay controles de la aplicación
    expect(screen.queryAllByRole('tab')).toHaveLength(0);
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('un fallo que NO es la compuerta (servidor caído) sale como error con «Reintentar», no como «no disponible»', async () => {
    await abrir('superadministracion', { fallos: { definiciones: new FalloDelKit('SERVIDOR') } });
    expect(await screen.findByText(T.ERROR_TITULO)).toBeInTheDocument();
    expect(screen.queryByTestId('no-disponible')).toBeNull();
    expect(screen.getByRole('button', { name: T.REINTENTAR })).toBeInTheDocument();
  });
});

describe('un usuario en modo consulta exporta lo que ve', () => {
  it('ve el aviso de consulta, ningún control de edición y exporta un CSV en lenguaje de negocio', async () => {
    await abrir('consulta');
    expect(await screen.findByText('Hola, Pedro Almonte')).toBeInTheDocument();
    expect(screen.getByText(T.MODO_CONSULTA_TITULO)).toBeInTheDocument();
    expect(screen.getByText(T.TITULAR_DE_CONSULTA)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: T.IMPORTAR_CSV })).toBeNull();
    const pestanas = screen.getAllByRole('tab').map((t) => t.textContent?.trim());
    expect(pestanas).toEqual(['Parámetros', 'Traza']);

    await fireEvent.click(screen.getByRole('button', { name: T.EXPORTAR }));
    expect(csv.descargar).toHaveBeenCalledTimes(1);
    const [nombre, contenido] = (csv.descargar as unknown as { mock: { calls: string[][] } }).mock.calls[0];
    expect(nombre).toBe(T.NOMBRE_DEL_FICHERO_DE_PARAMETROS);
    const lineas = contenido.replace(/^﻿/, '').trim().split('\r\n');
    expect(lineas[0]).toBe(T.COLUMNAS_DE_EXPORTACION.join(','));
    expect(lineas.some((l) => l.startsWith('Globales,Tipos de identificación,Lista,3 opciones'))).toBe(true);
    expect(lineas.some((l) => l.includes('Porcentaje máximo de beca,Parámetro,35 %'))).toBe(true);
    for (const tecnico of ['porcentaje_beca', 'persistence', '{', 'codigoPadre', 'null']) expect(contenido).not.toContain(tecnico);
  });

  it('exporta solo lo que se ve con el filtro y la búsqueda actuales', async () => {
    await abrir('superadministracion');
    await screen.findByText('Hola, Marta Rivas');
    await fireEvent.input(screen.getByLabelText(T.BUSCAR_ROTULO), { target: { value: 'sedes' } });
    await fireEvent.click(screen.getByRole('button', { name: T.EXPORTAR }));
    const contenido = (csv.descargar as unknown as { mock: { calls: string[][] } }).mock.calls[0][1];
    expect(contenido).toContain('Sedes');
    expect(contenido).not.toContain('Porcentaje máximo de beca');
  });
});

describe('navegación', () => {
  it('desde una lista o desde importar, pulsar la pestaña «Parámetros» (la activa) vuelve al inicio', async () => {
    location.hash = '#/importar';
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion' }) });
    await screen.findByTestId('vista-importar');
    await fireEvent.click(screen.getByRole('tab', { name: T.PESTANAS.parametros }));
    expect(await screen.findByText('Hola, Marta Rivas')).toBeInTheDocument();
  });

  it('la cabecera lleva el acceso al home de las aplicaciones, en cualquier vista', async () => {
    location.hash = '#/importar';
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion' }) });
    await screen.findByTestId('vista-importar');
    const enlace = screen.getByRole('link', { name: 'Todas mis aplicaciones' });
    expect(enlace.getAttribute('href')).toBe('/bonita/');
    expect(within(screen.getByRole('navigation', { name: 'Sesión' })).getByRole('link', { name: 'Todas mis aplicaciones' })).toBe(enlace);
  });
});
