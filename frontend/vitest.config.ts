import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

/**
 * Configuración de la suite unitaria.
 *
 * Deliberadamente NO extiende `vite.config.ts`: ese config fija `root` en la
 * carpeta del formulario que se está construyendo (FORM_ID), lo que dejaría fuera
 * del alcance de los tests el núcleo compartido y los demás formularios.
 */
export default defineConfig({
  plugins: [svelte({ hot: false, configFile: resolve(import.meta.dirname, 'svelte.config.js') })],
  resolve: {
    alias: {
      $lib: resolve(import.meta.dirname, 'src/lib'),
      // Utilidades que SOLO usan los tests. Viven fuera de `src/lib` y su alias existe
      // únicamente aquí —a propósito—: `vite.config.ts` no lo declara, así que si una
      // pantalla llegara a importarlas, el build de producción falla en vez de colarlas en
      // el bundle. La regla que esto hace cumplir es «en `src/lib` solo va lo que puede
      // viajar al ZIP»: la huella de cada ZIP cubre `src/lib` entero, y con el helper
      // ahí dentro, tocar un instrumento de prueba desfasaría todas las pantallas a la vez.
      $pruebas: resolve(import.meta.dirname, 'src/pruebas'),
    },
    // Los componentes se prueban compilados para el navegador, no para SSR.
    conditions: ['browser'],
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [resolve(import.meta.dirname, 'src/test/setup.ts')],
    // `scripts/` entra a propósito: la identidad del recurso y su descriptor se
    // construyen ahí, y un fallo en esa lógica sobrescribe un formulario con otro
    // en el runtime, en silencio.
    include: ['src/**/*.{test,spec}.{ts,js}', 'scripts/**/*.{test,spec}.{ts,js}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: ['src/lib/**/*.{ts,svelte}', 'src/forms/**/*.{ts,svelte}'],
    },
  },
});
