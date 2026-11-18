/**
 * La huella tiene que moverse con lo que viaja en el bundle, y solo con eso.
 *
 * Si la huella no cambiara al tocar un componente compartido, un custodio de huellas daría
 * verde sobre un ZIP viejo y volveríamos al falso verde que este mecanismo existe para
 * cerrar (2026-09-09 y 2026-09-10). Y si cambiara al tocar un test, obligaría a reempaquetar
 * todas las pantallas por cambiar una aserción: el guard se volvería ruido y alguien lo
 * apagaría.
 */
import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import path from 'node:path';
import os from 'node:os';
import fs from 'fs-extra';
import { fuentesDe, huellaDeFuentes } from './huella.js';

let raiz;

async function escribir(relativa, contenido) {
  const destino = path.join(raiz, relativa);
  await fs.ensureDir(path.dirname(destino));
  await fs.writeFile(destino, contenido);
}

beforeEach(async () => {
  raiz = await fs.mkdtemp(path.join(os.tmpdir(), 'huella-'));
  await escribir('src/forms/f1/index.html', '<html></html>');
  await escribir('src/forms/f1/Pantalla.svelte', '<h1>hola</h1>');
  await escribir('src/lib/estilos/tokens.css', ':root { --color-borde-control: #79747e; }');
  await escribir('src/lib/ui/Entrada.svelte', 'border: 1px solid var(--color-borde-control);');
});

afterEach(async () => {
  await fs.remove(raiz);
});

describe('huella de las fuentes de un formulario', () => {
  it('es estable: dos cálculos seguidos dan el mismo número', async () => {
    expect(await huellaDeFuentes(raiz, 'f1')).toBe(await huellaDeFuentes(raiz, 'f1'));
  });

  it('cambia al tocar un componente COMPARTIDO — es el caso que nos mordió', async () => {
    const antes = await huellaDeFuentes(raiz, 'f1');
    await escribir('src/lib/ui/Entrada.svelte', 'border: 1px solid var(--color-borde);');
    expect(await huellaDeFuentes(raiz, 'f1')).not.toBe(antes);
  });

  it('cambia al tocar los tokens, que es de donde salía el borde invisible', async () => {
    const antes = await huellaDeFuentes(raiz, 'f1');
    await escribir('src/lib/estilos/tokens.css', ':root { --color-borde-control: #e4e1e8; }');
    expect(await huellaDeFuentes(raiz, 'f1')).not.toBe(antes);
  });

  it('cambia al tocar la propia pantalla', async () => {
    const antes = await huellaDeFuentes(raiz, 'f1');
    await escribir('src/forms/f1/Pantalla.svelte', '<h1>adios</h1>');
    expect(await huellaDeFuentes(raiz, 'f1')).not.toBe(antes);
  });

  it('NO cambia al añadir o editar un fichero de prueba: no viaja en el bundle', async () => {
    const antes = await huellaDeFuentes(raiz, 'f1');
    await escribir('src/lib/ui/entrada.test.ts', 'it("algo", () => {});');
    await escribir('src/forms/f1/pantalla.spec.ts', 'it("otra", () => {});');
    expect(await huellaDeFuentes(raiz, 'f1')).toBe(antes);
  });

  it('no depende del orden del sistema de ficheros: las rutas van ordenadas y en POSIX', async () => {
    const rutas = await fuentesDe(raiz, 'f1');
    expect(rutas).toEqual([...rutas].sort());
    expect(rutas.every((r) => !r.includes('\\'))).toBe(true);
    expect(rutas).toContain('src/lib/estilos/tokens.css');
  });

  it('cambia al tocar el manifiesto: de ahí salen el nombre, los PERMISOS y la familia', async () => {
    await escribir('forms.manifest.json', JSON.stringify({ formularios: [{ id: 'f1', permisos: [] }] }));
    const antes = await huellaDeFuentes(raiz, 'f1');
    await escribir(
      'forms.manifest.json',
      JSON.stringify({ formularios: [{ id: 'f1', permisos: ['GET|portal/page'] }] }),
    );
    expect(await huellaDeFuentes(raiz, 'f1')).not.toBe(antes);
  });

  it('ignora las fuentes de OTRO formulario: cada paquete responde por lo suyo', async () => {
    const antes = await huellaDeFuentes(raiz, 'f1');
    await escribir('src/forms/f2/Pantalla.svelte', '<h1>ajena</h1>');
    expect(await huellaDeFuentes(raiz, 'f1')).toBe(antes);
  });
});
