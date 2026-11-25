/** Pruebas de la pantalla `frm_10_validarSolicitud` con datos simulados (sin Bonita ni HubSpot). */
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Frm10ValidarSolicitud from './Frm10ValidarSolicitud.svelte';
import { ENTRADAS, type CuerpoDelContrato } from './generado/contrato';
import { CONCEPTOS, erroresDePantalla } from './validacion';
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

  it('exige el concepto si es viable o no viable, no si está bloqueado', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'ok' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.getByText(/concepto de viabilidad es obligatorio si/)).toBeInTheDocument();
    await fireEvent.click(screen.getByRole('radio', { name: /^Bloqueado/ }));
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
  });

  it('el concepto es un selector con exactamente las cuatro opciones de HubSpot', async () => {
    await pintar();
    const selector = screen.getByRole('combobox', { name: /Concepto de viabilidad/ }) as HTMLSelectElement;
    const opciones = [...selector.options].map((o) => o.value).filter((v) => v !== '');
    expect(opciones).toEqual([
      'Aprobado (Viable)',
      'Aprobado con Condiciones',
      'No Viable (Rechazado)',
      'Requiere más información',
    ]);
    expect([...CONCEPTOS]).toEqual(opciones);
  });

  it('envía todas las entradas del contrato y muestra el éxito (viable con condiciones)', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^Viable/ }));
    await fireEvent.change(screen.getByRole('combobox', { name: /Concepto de viabilidad/ }), {
      target: { value: 'Aprobado con Condiciones' },
    });
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'Revisado con el comercial' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    const cuerpo = enviar.mock.calls[0][0] as Record<string, unknown>;
    expect(Object.keys(cuerpo).sort()).toEqual([...ENTRADAS].sort());
    expect(cuerpo).toEqual({
      resultado: 'viable',
      conceptoViabilidad: 'Aprobado con Condiciones',
      notaValidacion: 'Revisado con el comercial',
      supuestos: null,
    });
    expect(await screen.findByText('Validación enviada')).toBeInTheDocument();
  });

  it('«no viable» envía no_viable (el valor del contrato) con «No Viable (Rechazado)» elegido solo', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^No viable/ }));
    expect((screen.getByRole('combobox', { name: /Concepto de viabilidad/ }) as HTMLSelectElement).value).toBe('No Viable (Rechazado)');
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'Fuera de oferta' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    expect(enviar.mock.calls[0][0]).toEqual({
      resultado: 'no_viable',
      conceptoViabilidad: 'No Viable (Rechazado)',
      notaValidacion: 'Fuera de oferta',
      supuestos: null,
    });
  });

  it('«no viable» con otro concepto no se envía (espeja conceptoViabilidad_noViable)', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^No viable/ }));
    await fireEvent.change(screen.getByRole('combobox', { name: /Concepto de viabilidad/ }), {
      target: { value: 'Aprobado (Viable)' },
    });
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'x' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.getByText(/el concepto debe ser No Viable \(Rechazado\)/)).toBeInTheDocument();
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

  it('axe: sin infracciones de accesibilidad', async () => {
    const { container } = await pintar();
    expect(await infraccionesAxe(container)).toEqual([]);
  });
});

describe('validación de frm_10_validarSolicitud (espeja las constraints del contrato)', () => {
  const base: CuerpoDelContrato = { resultado: 'viable', conceptoViabilidad: 'Aprobado (Viable)', notaValidacion: 'n', supuestos: null };
  it('acepta las cuatro opciones con «viable» y ninguna con «bloqueado»', () => {
    for (const c of CONCEPTOS) expect(erroresDePantalla({ ...base, conceptoViabilidad: c })).toEqual({});
    expect(erroresDePantalla({ ...base, resultado: 'bloqueado', conceptoViabilidad: null })).toEqual({});
  });
  it('rechaza un concepto fuera de las cuatro opciones (texto libre o mayúsculas distintas)', () => {
    for (const c of ['Viable con DocFly', 'aprobado (viable)', 'Aprobado']) {
      expect(erroresDePantalla({ ...base, conceptoViabilidad: c }).conceptoViabilidad).toMatch(/debe ser Aprobado \(Viable\)/);
    }
  });
  it('«no viable» exige «No Viable (Rechazado)»', () => {
    expect(erroresDePantalla({ ...base, resultado: 'no_viable', conceptoViabilidad: 'No Viable (Rechazado)' })).toEqual({});
    expect(
      erroresDePantalla({ ...base, resultado: 'no_viable', conceptoViabilidad: 'Requiere más información' }).conceptoViabilidad,
    ).toMatch(/no es viable/);
  });
  it('rechaza el antiguo valor «no viable» con espacio (el contrato espera no_viable)', () => {
    expect(erroresDePantalla({ ...base, resultado: 'no viable', conceptoViabilidad: 'No Viable (Rechazado)' }).resultado).toBeDefined();
  });
});
