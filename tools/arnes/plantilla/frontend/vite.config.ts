import { defineConfig, loadEnv } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'node:path';

/**
 * Build POR FORMULARIO: un paquete con N entradas, no N paquetes.
 *
 * El formulario a construir se elige con la variable de entorno FORM_ID, y cada
 * formulario es una mini-aplicación con su propio `index.html` en
 * `src/forms/<FORM_ID>/`. Así el hash de assets, el `outDir` y el ZIP resultante
 * quedan aislados por formulario: compilar uno NUNCA pisa el paquete de otro.
 *
 * CONFIGURACIÓN POR ENTORNO — nada de direcciones ni credenciales en el código.
 *
 *   BONITA_URL   dirección del runtime Bonita          (def. http://localhost:8096, el bundle de run-journey.sh)
 *   DEV_PORT     puerto del servidor de desarrollo     (def. 4200)
 *   FORM_ID      formulario a construir o servir       (def. _semilla)
 *
 * Salen del entorno del proceso o de `frontend/.env` (copia de `.env.example`); el entorno
 * manda. `envDir` fija esa carpeta: sin él Vite buscaría el `.env` en `root`, la carpeta del
 * formulario, y `.env.example` no serviría. Las `VITE_*` de desarrollo solo las lee el
 * servidor de desarrollo (`credencialesDeDesarrollo`, con `import.meta.env.DEV`).
 */
const ENV_DIR = import.meta.dirname;

export default defineConfig(({ mode }) => {
  const entorno = { ...loadEnv(mode, ENV_DIR, ''), ...process.env };
  const BONITA_URL = entorno.BONITA_URL || 'http://localhost:8096';
  const DEV_PORT = Number(entorno.DEV_PORT || 4200);
  const FORM_ID = entorno.FORM_ID || '_semilla';

  const formRoot = resolve(import.meta.dirname, 'src/forms', FORM_ID);

  return {
    root: formRoot,
    envDir: ENV_DIR,
    // Rutas relativas: la custom page se sirve bajo /bonita/portal/resource/... y su
    // índice vive en `resources/`, así que ningún recurso puede depender de la raíz
    // del servidor. Con `base: './'` no hace falta reescribir el HTML tras el build.
    base: './',
    plugins: [svelte({ configFile: resolve(import.meta.dirname, 'svelte.config.js') })],
    resolve: {
      alias: {
        $lib: resolve(import.meta.dirname, 'src/lib'),
      },
    },
    server: {
      port: DEV_PORT,
      // El núcleo importa desde fuera del root del formulario (src/lib): en desarrollo
      // hay que autorizar explícitamente ese acceso al sistema de archivos.
      fs: { allow: [resolve(import.meta.dirname)] },
      proxy: {
        '/bonita': {
          target: BONITA_URL,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: resolve(import.meta.dirname, 'dist', FORM_ID),
      emptyOutDir: true,
      // El hasheo satisface el cache busting que la plataforma exige a quien no usa
      // UI Designer (doc runtime:live-update): sin él, el navegador sirve la versión
      // vieja del formulario tras una actualización.
      rollupOptions: {
        output: {
          entryFileNames: 'js/[name]-[hash].js',
          chunkFileNames: 'js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const name = assetInfo.names?.[0] ?? '';
            if (name.endsWith('.css')) return 'css/[name]-[hash][extname]';
            return 'assets/[name]-[hash][extname]';
          },
        },
      },
    },
  };
});
