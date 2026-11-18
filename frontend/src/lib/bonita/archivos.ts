/**
 * Subida de los archivos de un contrato.
 *
 * Un input FILE del contrato no viaja con el contenido del archivo: el formulario lo sube antes al servlet de subida de
 * formularios (`POST /bonita/API/formFileUpload`, multipart con el campo `file` y el token CSRF, recurso
 * `API/formFileUpload` de los permisos de usuario) y la plataforma responde con la referencia temporal
 * `{ filename, tempPath, contentType }`. Esa referencia es lo que el contrato lee al ejecutar la tarea o instanciar el
 * proceso; mandar `{ nombre, contenido }` no adjunta nada.
 *
 * `CargaArchivo` deja en los valores del formulario el archivo leído (`ArchivoContrato`, en base64); la pantalla lo
 * sube al enviar con `subirArchivosDe`. Si una subida falla, se lanza: la pantalla no envía y lo dice.
 */

import { obtenerToken } from './cliente';
import { urlApi } from './config';
import { codigoHttpDe } from './marcas';
import { ErrorDeBonita, type ArchivoContrato } from './tipos';
import type { ValoresDelFormulario } from '$lib/ui/valores';

/** La referencia temporal que devuelve la subida y que lee un input FILE del contrato. */
export interface ArchivoSubido {
  readonly filename: string;
  readonly tempPath: string;
  readonly contentType: string;
}

/** El recurso de la subida (bajo `/bonita/API`). */
export const RECURSO_DE_SUBIDA = '/formFileUpload';

const TIPOS_POR_EXTENSION: Readonly<Record<string, string>> = {
  pdf: 'application/pdf',
  png: 'image/png',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  gif: 'image/gif',
  txt: 'text/plain',
  csv: 'text/csv',
};

/** El tipo de contenido por la extensión del nombre; si no se conoce, binario genérico. */
export function tipoDeContenido(nombre: string): string {
  const extension = nombre.split('.').pop()?.toLowerCase() ?? '';
  return TIPOS_POR_EXTENSION[extension] ?? 'application/octet-stream';
}

function blobDe(archivo: ArchivoContrato): Blob {
  const binario = atob(archivo.contenido);
  const bytes = new Uint8Array(binario.length);
  for (let i = 0; i < binario.length; i += 1) bytes[i] = binario.charCodeAt(i);
  return new Blob([bytes], { type: tipoDeContenido(archivo.nombre) });
}

function esTexto(v: unknown): v is string {
  return typeof v === 'string' && v !== '';
}

/** Sube un archivo y devuelve su referencia temporal. Lanza `ErrorDeBonita` si la subida no fue bien. */
export async function subirArchivo(archivo: ArchivoContrato): Promise<ArchivoSubido> {
  const datos = new FormData();
  datos.append('file', blobDe(archivo), archivo.nombre);
  const cabeceras: Record<string, string> = {};
  const token = await obtenerToken();
  if (token) cabeceras['X-Bonita-API-Token'] = token;
  let respuesta: Response;
  try {
    respuesta = await fetch(urlApi(RECURSO_DE_SUBIDA), {
      method: 'POST',
      credentials: 'include',
      headers: cabeceras,
      body: datos,
    });
  } catch (causa) {
    throw new ErrorDeBonita(`Sin respuesta al subir «${archivo.nombre}»`, 0, causa);
  }
  const estado = codigoHttpDe(respuesta) ?? 0;
  if (!respuesta.ok) {
    throw new ErrorDeBonita(`La subida de «${archivo.nombre}» respondió ${respuesta.status}`, estado);
  }
  const cuerpo: unknown = await respuesta.json().catch(() => null);
  const ref = (cuerpo ?? {}) as Record<string, unknown>;
  if (!esTexto(ref.filename) || !esTexto(ref.tempPath)) {
    throw new ErrorDeBonita(
      `La subida de «${archivo.nombre}» no devolvió la referencia { filename, tempPath, contentType }`,
      estado,
      cuerpo,
    );
  }
  return {
    filename: ref.filename,
    tempPath: ref.tempPath,
    contentType: esTexto(ref.contentType) ? ref.contentType : tipoDeContenido(archivo.nombre),
  };
}

function esArchivo(v: unknown): v is ArchivoContrato {
  return (
    typeof v === 'object' &&
    v !== null &&
    typeof (v as ArchivoContrato).nombre === 'string' &&
    typeof (v as ArchivoContrato).contenido === 'string'
  );
}

/**
 * Sube los archivos de los campos FILE que tienen valor y devuelve su referencia por ruta. Los campos sin archivo no
 * aparecen (el cuerpo los manda a `null`). La primera subida que falla hace fallar todo: no se envía a medias.
 */
export async function subirArchivosDe(
  campos: readonly { readonly ruta: string; readonly tipo: string }[],
  valores: ValoresDelFormulario,
  subir: (archivo: ArchivoContrato) => Promise<ArchivoSubido> = subirArchivo,
): Promise<Record<string, ArchivoSubido>> {
  const subidos: Record<string, ArchivoSubido> = {};
  for (const campo of campos) {
    const valor = valores[campo.ruta];
    if (campo.tipo !== 'FILE' || !esArchivo(valor)) continue;
    subidos[campo.ruta] = await subir(valor);
  }
  return subidos;
}
