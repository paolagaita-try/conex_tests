/**
 * Capturas PNG de cada formulario con datos simulados (`?demo=1`, solo en `vite` dev). Sin Bonita ni HubSpot.
 * Uso: node scripts/capturas.mjs [carpeta-destino]   (por defecto ../capturas-formularios, fuera de git; las capturas no se suben al repo)
 */
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { chromium } from '@playwright/test';

const destino = path.resolve(process.argv[2] ?? '../capturas-formularios');
mkdirSync(destino, { recursive: true });
const FORMULARIOS = ['frm10ValidarSolicitud', 'frm20DisenarPropuesta', 'frmOverview'];
const vite = path.resolve('node_modules/vite/bin/vite.js');

async function servir(form, puerto) {
  const proc = spawn(process.execPath, [vite, '--port', String(puerto), '--strictPort'], {
    env: { ...process.env, FORM_ID: form },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  await new Promise((ok, mal) => {
    const t = setTimeout(() => mal(new Error(`vite no arrancó para ${form}`)), 60_000);
    proc.stdout.on('data', (d) => String(d).includes('Local') && (clearTimeout(t), ok()));
  });
  return proc;
}

const navegador = await chromium.launch();
let puerto = Number(process.env.PUERTO ?? 5191);
for (const form of FORMULARIOS) {
  const proc = await servir(form, puerto);
  try {
    for (const [nombre, ancho] of [['escritorio', 1366], ['movil', 390]]) {
      const pagina = await navegador.newPage({ viewport: { width: ancho, height: 900 }, deviceScaleFactor: 1 });
      await pagina.goto(`http://localhost:${puerto}/?demo=1&taskId=1&caseId=1`, { waitUntil: 'networkidle' });
      await pagina.getByRole('heading', { level: 1 }).filter({ hasText: 'Automatizar' }).waitFor();
      await pagina.screenshot({ path: path.join(destino, `${form}-${nombre}.png`), fullPage: true });
      if (nombre === 'escritorio' && form !== 'frmOverview') {
        // Estado con errores de validación visibles.
        await pagina.locator('button[type=submit]').click();
        await pagina.screenshot({ path: path.join(destino, `${form}-errores.png`), fullPage: true });
      }
      await pagina.close();
    }
  } finally {
    proc.kill();
  }
  puerto += 1;
}
await navegador.close();
console.log(`capturas en ${destino}`);
