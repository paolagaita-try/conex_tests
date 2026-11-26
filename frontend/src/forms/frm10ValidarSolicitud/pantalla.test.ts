/** Pruebas de la pantalla `frm_10_validarSolicitud` con datos simulados (sin Bonita ni HubSpot). */
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Frm10ValidarSolicitud from './Frm10ValidarSolicitud.svelte';
import { ENTRADAS, type CuerpoDelContrato } from './generado/contrato';
import { CONCEPTOS_VIABLE, erroresDePantalla } from './validacion';
import { CASO_EJEMPLO, CONTEXTO_EJEMPLO } from '$lib/preventa/ejemplo';
import { infraccionesAxe } from '$pruebas/axe';

const cargar = vi.fn(async () => ({ caso: CASO_EJEMPLO, hubspot: CONTEXTO_EJEMPLO }));
const BOTON = { name: 'Enviar validación' };

async function pintar(enviar = vi.fn(async (_c: unknown) => undefined)) {
  const r = render(Frm10ValidarSolicitud, { props: { enviar, cargar } });
  await screen.findByRole('heading', { level: 1, name: /Automatizar la radicación/ });
  return { ...r, enviar };
}

describe('pantalla frm_10_validarSolicitud', () => {
  it('pinta el encabezado y los paneles de solo lectura con la precarga', async () => {
    const { container } = await pintar();
    expect(screen.getByText('Alta')).toBeInTheDocument();
    expect(screen.getByText('laura.preventa')).toBeInTheDocument();
    for (const p of ['ticket', 'negocio', 'empresa', 'contactos', 'comercial']) {
      expect(container.querySelector(`[data-panel="${p}"]`), p).not.toBeNull();
    }
    expect(screen.getByText('mariana.rios@acme.example')).toBeInTheDocument();
  });

  it('explica qué pasa con cada resultado', async () => {
    await pintar();
    expect(screen.getByText(/pasa a Diseño de la propuesta/)).toBeInTheDocument();
    expect(screen.getByText(/En espera información del lead/)).toBeInTheDocument();
    expect(screen.getByText(/cerrado por viabilidad/)).toBeInTheDocument();
  });

  it('no envía sin resultado ni nota, y marca los errores', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.getByText('Elija el resultado de la validación.')).toBeInTheDocument();
    expect(screen.getByText('La nota de validación es obligatoria.')).toBeInTheDocument();
  });

  it('con «viable» exige el concepto; con «bloqueado» no hay selector y se envía sin concepto', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'ok' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.getByText(/Si la solicitud es viable, el concepto debe ser/)).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('radio', { name: /^Bloqueado/ }));
    expect(screen.queryByRole('combobox', { name: /Concepto de viabilidad/ })).toBeNull();
    expect(await screen.findByTestId('concepto-fijado')).toHaveTextContent('Requiere más información');
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    expect(enviar.mock.calls[0][0]).toEqual({
      resultado: 'bloqueado',
      conceptoViabilidad: null,
      notaValidacion: 'ok',
      supuestos: null,
    });
  });

  it('con «viable» el selector ofrece solo «Aprobado (Viable)» y «Aprobado con Condiciones»', async () => {
    await pintar();
    expect(screen.queryByRole('combobox', { name: /Concepto de viabilidad/ })).toBeNull();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    const selector = (await screen.findByRole('combobox', { name: /Concepto de viabilidad/ })) as HTMLSelectElement;
    const opciones = [...selector.options].map((o) => o.value).filter((v) => v !== '');
    expect(opciones).toEqual(['Aprobado (Viable)', 'Aprobado con Condiciones']);
    expect([...CONCEPTOS_VIABLE]).toEqual(opciones);
  });

  it('envía viable con «Aprobado (Viable)» y todas las entradas del contrato', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.change(await screen.findByRole('combobox', { name: /Concepto de viabilidad/ }), {
      target: { value: 'Aprobado (Viable)' },
    });
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'Requerimiento claro' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    const cuerpo = enviar.mock.calls[0][0] as Record<string, unknown>;
    expect(Object.keys(cuerpo).sort()).toEqual([...ENTRADAS].sort());
    expect(cuerpo).toEqual({
      resultado: 'viable',
      conceptoViabilidad: 'Aprobado (Viable)',
      notaValidacion: 'Requerimiento claro',
      supuestos: null,
    });
    expect(await screen.findByText('Validación enviada')).toBeInTheDocument();
  });

  it('«Aprobado con Condiciones» sin condiciones no se envía; con condiciones sí', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.change(await screen.findByRole('combobox', { name: /Concepto de viabilidad/ }), {
      target: { value: 'Aprobado con Condiciones' },
    });
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'Revisado con el comercial' } });
    const condiciones = await screen.findByRole('textbox', { name: /^Condiciones/ });
    expect(condiciones).toHaveAttribute('aria-required', 'true');
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.getByText(/escriba las condiciones/)).toBeInTheDocument();
    await fireEvent.input(condiciones, { target: { value: 'Entrega del volumen real' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    expect(enviar.mock.calls[0][0]).toEqual({
      resultado: 'viable',
      conceptoViabilidad: 'Aprobado con Condiciones',
      notaValidacion: 'Revisado con el comercial',
      supuestos: 'Entrega del volumen real',
    });
  });

  it('«no viable» no muestra selector: el proceso fija «No Viable (Rechazado)» y se envía no_viable sin concepto', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.change(await screen.findByRole('combobox', { name: /Concepto de viabilidad/ }), {
      target: { value: 'Aprobado (Viable)' },
    });
    await fireEvent.click(screen.getByRole('radio', { name: /^No viable/ }));
    expect(screen.queryByRole('combobox', { name: /Concepto de viabilidad/ })).toBeNull();
    expect(await screen.findByTestId('concepto-fijado')).toHaveTextContent('No Viable (Rechazado)');
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'Fuera de oferta' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    expect(enviar.mock.calls[0][0]).toEqual({
      resultado: 'no_viable',
      conceptoViabilidad: null,
      notaValidacion: 'Fuera de oferta',
      supuestos: null,
    });
  });

  it('muestra el error del motor', async () => {
    await pintar(
      vi.fn(async () => {
        throw new Error('Contrato rechazado');
      }),
    );
    await fireEvent.click(screen.getByRole('radio', { name: /^Bloqueado/ }));
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'x' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(await screen.findByRole('alert')).toHaveTextContent('Contrato rechazado');
  });

  it('si la precarga falla lo dice y no deja enviar', async () => {
    render(Frm10ValidarSolicitud, {
      props: { enviar: vi.fn(), cargar: () => Promise.reject(new Error('HubSpot no responde')) },
    });
    expect(await screen.findByText(/HubSpot no responde/)).toBeInTheDocument();
    expect(screen.getByRole('button', BOTON)).toBeDisabled();
  });

  it('axe: sin infracciones de accesibilidad (al abrir, con «viable» + condiciones y con «bloqueado»)', async () => {
    const { container } = await pintar();
    expect(await infraccionesAxe(container)).toEqual([]);
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.change(await screen.findByRole('combobox', { name: /Concepto de viabilidad/ }), {
      target: { value: 'Aprobado con Condiciones' },
    });
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(await infraccionesAxe(container)).toEqual([]);
    await fireEvent.click(screen.getByRole('radio', { name: /^Bloqueado/ }));
    expect(await infraccionesAxe(container)).toEqual([]);
  });
});

describe('validación de frm_10_validarSolicitud (espeja las constraints del contrato)', () => {
  const base: CuerpoDelContrato = { resultado: 'viable', conceptoViabilidad: 'Aprobado (Viable)', notaValidacion: 'n', supuestos: null };
  it('«viable» acepta solo «Aprobado (Viable)» y «Aprobado con Condiciones» (conceptoViabilidad_viable)', () => {
    expect(erroresDePantalla(base)).toEqual({});
    expect(erroresDePantalla({ ...base, conceptoViabilidad: 'Aprobado con Condiciones', supuestos: 'c' })).toEqual({});
    for (const c of ['Requiere más información', 'No Viable (Rechazado)', '', null, 'aprobado (viable)', 'Viable con DocFly']) {
      expect(erroresDePantalla({ ...base, conceptoViabilidad: c }).conceptoViabilidad).toMatch(/Si la solicitud es viable/);
    }
  });
  it('«Aprobado con Condiciones» exige las condiciones (supuestos_siCondiciones)', () => {
    for (const s of [null, '', '   ']) {
      expect(erroresDePantalla({ ...base, conceptoViabilidad: 'Aprobado con Condiciones', supuestos: s }).supuestos).toMatch(/condiciones/);
    }
  });
  it('«bloqueado» admite vacío o «Requiere más información» (conceptoViabilidad_bloqueado)', () => {
    const b = { ...base, resultado: 'bloqueado' };
    expect(erroresDePantalla({ ...b, conceptoViabilidad: null })).toEqual({});
    expect(erroresDePantalla({ ...b, conceptoViabilidad: 'Requiere más información' })).toEqual({});
    expect(erroresDePantalla({ ...b, conceptoViabilidad: 'Aprobado (Viable)' }).conceptoViabilidad).toMatch(/Requiere más información/);
  });
  it('«no viable» admite vacío o «No Viable (Rechazado)» (conceptoViabilidad_noViable)', () => {
    const n = { ...base, resultado: 'no_viable' };
    expect(erroresDePantalla({ ...n, conceptoViabilidad: null })).toEqual({});
    expect(erroresDePantalla({ ...n, conceptoViabilidad: 'No Viable (Rechazado)' })).toEqual({});
    expect(erroresDePantalla({ ...n, conceptoViabilidad: 'Requiere más información' }).conceptoViabilidad).toMatch(/No Viable \(Rechazado\)/);
  });
  it('rechaza el antiguo valor «no viable» con espacio (el contrato espera no_viable)', () => {
    expect(erroresDePantalla({ ...base, resultado: 'no viable', conceptoViabilidad: null }).resultado).toBeDefined();
  });
});
