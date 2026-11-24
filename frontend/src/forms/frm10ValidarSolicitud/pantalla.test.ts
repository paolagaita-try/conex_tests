/** Pruebas de la pantalla `frm_10_validarSolicitud` con datos simulados (sin Bonita ni HubSpot). */
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Frm10ValidarSolicitud from './Frm10ValidarSolicitud.svelte';
import { ENTRADAS } from './generado/contrato';
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

  it('envía todas las entradas del contrato y muestra el éxito', async () => {
    const { enviar } = await pintar();
    await fireEvent.click(screen.getByRole('radio', { name: /^No viable/ }));
    await fireEvent.input(screen.getByLabelText(/Concepto de viabilidad/), { target: { value: 'Fuera de oferta' } });
    await fireEvent.input(screen.getByRole('textbox', { name: /Nota de validación/ }), { target: { value: 'Revisado con el comercial' } });
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    const cuerpo = enviar.mock.calls[0][0] as Record<string, unknown>;
    expect(Object.keys(cuerpo).sort()).toEqual([...ENTRADAS].sort());
    expect(cuerpo).toEqual({
      resultado: 'no viable',
      conceptoViabilidad: 'Fuera de oferta',
      notaValidacion: 'Revisado con el comercial',
      supuestos: null,
    });
    expect(await screen.findByText('Validación enviada')).toBeInTheDocument();
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
