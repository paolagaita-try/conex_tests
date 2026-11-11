/** La subida de archivos del contrato: multipart al servlet de subida, con token, y su referencia temporal. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RECURSO_DE_SUBIDA, subirArchivo, subirArchivosDe, tipoDeContenido } from './archivos';
import { ErrorDeBonita } from './tipos';

const ARCHIVO = { nombre: 'soporte.pdf', contenido: btoa('%PDF-1.4') };

/** Un `fetch` que da el token por la sesión y responde la subida con `subida`. */
function plataforma(subida: () => Response) {
  const llamadas: { url: string; init?: RequestInit }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (entrada: string | URL, init?: RequestInit) => {
      const url = String(entrada);
      llamadas.push({ url, init });
      if (url.includes('/system/session/')) {
        return new Response('{}', { status: 200, headers: { 'X-Bonita-API-Token': 'tok-1' } });
      }
      return subida();
    }),
  );
  return llamadas;
}

afterEach(() => vi.unstubAllGlobals());

describe('subirArchivo()', () => {
  it('sube en multipart con el token y devuelve { filename, tempPath, contentType }', async () => {
    const llamadas = plataforma(
      () =>
        new Response(JSON.stringify({ filename: 'soporte.pdf', tempPath: 'tmp_1.pdf', contentType: 'application/pdf' }), {
          status: 200,
        }),
    );
    const ref = await subirArchivo(ARCHIVO);
    expect(ref).toEqual({ filename: 'soporte.pdf', tempPath: 'tmp_1.pdf', contentType: 'application/pdf' });
    const subida = llamadas.find((l) => l.url.endsWith(`/API${RECURSO_DE_SUBIDA}`));
    expect(subida?.url).toBe('/bonita/API/formFileUpload');
    expect(subida?.init?.method).toBe('POST');
    expect((subida?.init?.headers as Record<string, string>)['X-Bonita-API-Token']).toBe('tok-1');
    const cuerpo = subida?.init?.body as FormData;
    const parte = cuerpo.get('file') as File;
    expect(parte.name).toBe('soporte.pdf');
    expect(parte.type).toBe('application/pdf');
    expect(parte.size).toBe('%PDF-1.4'.length); // el contenido, decodificado del base64
  });

  it('sin contentType en la respuesta, lo toma del nombre', async () => {
    plataforma(() => new Response(JSON.stringify({ filename: 'a.png', tempPath: 'tmp_2.png' }), { status: 200 }));
    expect((await subirArchivo({ nombre: 'a.png', contenido: btoa('x') })).contentType).toBe('image/png');
  });

  it('una subida rechazada, o sin la referencia, lanza: no se adjunta nada en silencio', async () => {
    plataforma(() => new Response('no', { status: 500 }));
    await expect(subirArchivo(ARCHIVO)).rejects.toBeInstanceOf(ErrorDeBonita);
    plataforma(() => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await expect(subirArchivo(ARCHIVO)).rejects.toThrow(/tempPath/);
  });

  it('sin red, lanza con estado 0', async () => {
    vi.stubGlobal('fetch', vi.fn(async (entrada: string | URL) => {
      if (String(entrada).includes('/system/session/')) return new Response('{}', { status: 200 });
      throw new TypeError('sin red');
    }));
    await expect(subirArchivo(ARCHIVO)).rejects.toMatchObject({ estado: 0 });
  });
});

describe('subirArchivosDe()', () => {
  it('sube solo los campos FILE con archivo y los devuelve por ruta', async () => {
    const subir = vi.fn(async (a: { nombre: string }) => ({ filename: a.nombre, tempPath: `tmp_${a.nombre}`, contentType: 'x' }));
    const subidos = await subirArchivosDe(
      [
        { ruta: 'datos.adjunto', tipo: 'FILE' },
        { ruta: 'datos.otro', tipo: 'FILE' },
        { ruta: 'datos.nota', tipo: 'TEXT' },
      ],
      { 'datos.adjunto': ARCHIVO, 'datos.otro': null, 'datos.nota': 'hola' },
      subir,
    );
    expect(subir).toHaveBeenCalledTimes(1);
    expect(subidos).toEqual({ 'datos.adjunto': { filename: 'soporte.pdf', tempPath: 'tmp_soporte.pdf', contentType: 'x' } });
  });

  it('si una subida falla, falla todo', async () => {
    const subir = vi.fn(async () => {
      throw new Error('caída');
    });
    await expect(subirArchivosDe([{ ruta: 'a', tipo: 'FILE' }], { a: ARCHIVO }, subir)).rejects.toThrow('caída');
  });
});

describe('tipoDeContenido()', () => {
  it('por extensión, y binario si no se conoce', () => {
    expect(tipoDeContenido('X.JPG')).toBe('image/jpeg');
    expect(tipoDeContenido('sin-extension')).toBe('application/octet-stream');
  });
});
