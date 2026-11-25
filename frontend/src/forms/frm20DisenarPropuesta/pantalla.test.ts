/** Pruebas de la pantalla `frm_20_disenarPropuesta` con datos simulados (sin Bonita ni HubSpot). */
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import Frm20DisenarPropuesta from './Frm20DisenarPropuesta.svelte';
import { ENTRADAS } from './generado/contrato';
import { CASO_EJEMPLO, CONTEXTO_EJEMPLO } from '$lib/preventa/ejemplo';
import { infraccionesAxe } from '$pruebas/axe';

const cargar = async () => ({ caso: CASO_EJEMPLO, hubspot: CONTEXTO_EJEMPLO });
const subir = vi.fn(async (f: File) => ({ filename: f.name, tempPath: `tmp_${f.name}`, contentType: 'application/pdf' }));
const BOTON = { name: 'Enviar propuesta' };

async function pintar(enviar = vi.fn(async (_c: unknown) => undefined)) {
  const r = render(Frm20DisenarPropuesta, { props: { enviar, cargar, subir } });
  await screen.findByRole('heading', { level: 1, name: /Automatizar la radicación/ });
  return { ...r, enviar };
}
async function llenar(url = 'https://slides.example/p1') {
  await fireEvent.input(screen.getByLabelText(/Valoración de operaciones/), { target: { value: '3 personas, 8 semanas' } });
  await fireEvent.input(screen.getByLabelText(/URL propuesta/), { target: { value: url } });
  await fireEvent.input(screen.getByLabelText(/Link repositorio/), { target: { value: 'https://drive.example/carpeta' } });
}

describe('pantalla frm_20_disenarPropuesta', () => {
  it('muestra la validación previa y los paneles de contexto', async () => {
    const { container } = await pintar();
    expect(screen.getByText('Resultado de la validación')).toBeInTheDocument();
    expect(container.querySelector('[data-panel="negocio"]')).not.toBeNull();
  });

  it('rechaza URLs no válidas', async () => {
    const { enviar } = await pintar();
    await llenar('slides sin protocolo');
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(enviar).not.toHaveBeenCalled();
    expect(screen.getByText(/URL válida que empiece por http/)).toBeInTheDocument();
  });

  it('añade archivos (selector y arrastrar-y-soltar), los lista, quita y sube al enviar', async () => {
    const { enviar, container } = await pintar();
    await llenar();
    const a = new File(['a'], 'arquitectura.pdf', { type: 'application/pdf' });
    const b = new File(['bb'], 'estimacion.xlsx');
    await fireEvent.change(container.querySelector('#campo-adjuntos')!, { target: { files: [a] } });
    await fireEvent.drop(container.querySelector('.zona')!, { dataTransfer: { files: [b, a] } });
    expect(container.querySelectorAll('.adjuntos li')).toHaveLength(2);
    await fireEvent.click(screen.getByRole('button', { name: 'Quitar estimacion.xlsx' }));
    await fireEvent.click(screen.getByRole('button', BOTON));
    await waitFor(() => expect(enviar).toHaveBeenCalledOnce());
    const cuerpo = enviar.mock.calls[0][0] as Record<string, unknown>;
    expect(Object.keys(cuerpo).sort()).toEqual([...ENTRADAS].sort());
    expect(cuerpo.adjuntos).toEqual([
      { filename: 'arquitectura.pdf', tempPath: 'tmp_arquitectura.pdf', contentType: 'application/pdf' },
    ]);
    expect(cuerpo.urlPptaPreventa).toBe('https://slides.example/p1');
    expect(await screen.findByText('Propuesta enviada')).toBeInTheDocument();
  });

  it('sin adjuntos envía una lista vacía y muestra errores del motor', async () => {
    const enviar = vi.fn(async (_c: unknown) => {
      throw new Error('Motor caído');
    });
    await pintar(enviar);
    await llenar();
    await fireEvent.click(screen.getByRole('button', BOTON));
    expect(await screen.findByRole('alert')).toHaveTextContent('Motor caído');
    expect(enviar.mock.calls[0][0]).toMatchObject({ adjuntos: [] });
  });

  it('axe: sin infracciones de accesibilidad', async () => {
    const { container } = await pintar();
    expect(await infraccionesAxe(container)).toEqual([]);
  });
});
