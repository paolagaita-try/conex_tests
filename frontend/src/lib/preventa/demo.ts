/** Solo en desarrollo (`vite`): `?demo=1` pinta la pantalla con datos simulados, para capturas y revisión. */
import { CASO_EJEMPLO, CONTEXTO_EJEMPLO } from './ejemplo';
import type { Precarga } from './contexto';

export function propsDeDemo(): Record<string, unknown> {
  if (!import.meta.env.DEV || !new URLSearchParams(location.search).has('demo')) return {};
  const etapa = new URLSearchParams(location.search).get('estado');
  return {
    cargar: async (): Promise<Precarga> => ({ caso: CASO_EJEMPLO, hubspot: CONTEXTO_EJEMPLO }),
    enviar: async () => {
      await new Promise((r) => setTimeout(r, 400));
      if (etapa === 'error') throw new Error('Simulación: el motor rechazó el contrato.');
    },
  };
}
