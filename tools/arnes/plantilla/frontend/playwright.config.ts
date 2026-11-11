import { defineConfig, devices } from '@playwright/test';

/**
 * Pruebas e2e de los formularios contra el runtime REAL (el bundle del journey), no contra un servidor de desarrollo.
 *
 * No hay `webServer`: el runtime no lo levanta npm, lo levanta `tools/run-journey.sh`, que después de Newman lanza
 * `tools/playwright.sh` con `PORT` y `WORKDIR_ESPERADO`. Para correrlas a mano: `tools/run-journey.sh --mantener`
 * y, con el runtime vivo, `PORT=8096 npm run test:e2e` desde `frontend/`.
 */
const PUERTO = process.env.PORT ?? '8096';

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/apoyo/arranque-global.ts',
  // Secuencial a propósito: los casos comparten el runtime y las bandejas de los usuarios. Con paralelismo, una
  // prueba toma la tarea que otra esperaba y el fallo parece del producto.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  outputDir: 'test-results',
  use: {
    // La barra final es necesaria: las rutas de las pruebas son relativas («API/bpm/…»).
    baseURL: `http://localhost:${PUERTO}/bonita/`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // El vídeo es entregable: sirve para enseñar el recorrido de la tarea.
    video: 'on',
    actionTimeout: 15_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
