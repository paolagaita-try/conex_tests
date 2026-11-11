/**
 * El módulo de parámetros SIMULADO para las pruebas de pantalla: lo que `GET parametros/valores` responde a
 * las pantallas que piden sus listas al módulo. Datos ficticios. Vive en `src/pruebas/` y no en `src/lib/`:
 * un instrumento de prueba en `lib` viajaría en cada ZIP.
 *
 * Los plazos son de ejemplo (5 a 20 días para el tipo `anual`; el tipo `horas` no tiene plazos).
 */
import { fireEvent, screen, waitFor } from '@testing-library/svelte';

export const PLAZOS_ANUALES = ['5', '10', '15', '20'] as const;

const json = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), { status, headers: { 'Content-Type': 'application/json' } });

/** La respuesta del módulo si `url` es una lectura suya; `null` si no lo es. `fallo` hace que todas fallen. */
export function respuestaDelModulo(url: string, fallo?: number): Response | null {
  if (!url.includes('/extension/parametros/valores')) return null;
  if (fallo) return json({ motivo: 'X' }, fallo);
  const q = new URL(url, 'http://x').searchParams;
  const definicion = q.get('definicion') ?? '';
  const padre = q.get('padre') ?? '';
  if (definicion === 'plazos_por_tipo') {
    const codigos = padre === 'anual' ? PLAZOS_ANUALES : [];
    return json({
      definicion,
      clase: 'LISTA',
      tipoDato: 'TEXTO',
      opciones: codigos.map((c, i) => ({ codigo: c, etiqueta: `${c} días`, ayuda: null, orden: i + 1, valor: null })),
    });
  }
  return json({ motivo: 'NO_EXISTE' }, 404);
}

/** Elige un plazo en el campo «Plazo aprobado», sea cual sea el control (desplegable o fichas). */
export async function elegirPlazo(codigo: string): Promise<void> {
  const control = await waitFor(() => {
    const el = screen.getByLabelText(/Plazo aprobado/i);
    if (el instanceof HTMLSelectElement && el.disabled) throw new Error('el plazo aún carga');
    return el;
  });
  if (control instanceof HTMLSelectElement) {
    await fireEvent.change(control, { target: { value: codigo } });
    return;
  }
  const ficha = [...control.querySelectorAll('[role="radio"]')].find((r) => r.textContent?.trim() === `${codigo} días`);
  if (!ficha) throw new Error(`el plazo ${codigo} no está entre las opciones`);
  await fireEvent.click(ficha);
}

/** Un lector sin red con las mismas respuestas del doble de `fetch` (para montar `CamposDeContrato` a solas). */
export const lectorDelModulo: import('$lib/parametros/opciones').LectorDeValores = async (peticion) => {
  const r = respuestaDelModulo(
    `/extension/parametros/valores?definicion=${peticion.definicion}&tarea=${peticion.tarea}` + (peticion.padre ? `&padre=${peticion.padre}` : ''),
  );
  if (!r || r.status !== 200) throw new Error(`el doble del módulo no conoce «${peticion.definicion}»`);
  const { entenderValores } = await import('$lib/parametros/opciones');
  return entenderValores(await r.json(), peticion.definicion);
};

/** Espera a que ninguna lista ni máximo siga cargando: una foto del DOM tomada antes mediría la carga, no la acción. */
export async function moduloCargado(): Promise<void> {
  await waitFor(() => {
    if (/Cargando opciones|Cargando el máximo/.test(document.body.textContent ?? '')) throw new Error('el módulo aún carga');
  });
}

/** Los rótulos que el doble del módulo sirve para los plazos (los mismos que pinta el campo): datos del servidor. */
export const ETIQUETAS_DE_PLAZO: readonly string[] = PLAZOS_ANUALES.map((c) => `${c} días`);
