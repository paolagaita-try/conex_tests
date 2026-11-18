/**
 * La dirección de descarga de un documento de proceso, o `null` si no hay nada que descargar.
 *
 * El binario vive como documento de proceso y el BDM guarda su `contentStorageId`. La plataforma lo sirve por
 * `portal/documentDownload`, que es la misma `url` que devuelve `GET /API/bpm/caseDocument`: se construye igual,
 * relativa al portal, para que funcione desde cualquier página sin conocer el host. Un documento sin
 * `contentStorageId` (registrado sin contenido) no tiene enlace, y no se inventa uno.
 */
export function urlDeDescargaDeDocumento(
  documento: { nombreArchivo?: string | null; contentStorageId?: string | null } | null | undefined,
): string | null {
  const clave = documento?.contentStorageId;
  if (clave == null || String(clave).trim() === '') return null;
  const nombre = documento?.nombreArchivo?.trim() || 'documento';
  return (
    '/bonita/portal/documentDownload?fileName=' +
    encodeURIComponent(nombre) +
    '&contentStorageId=' +
    encodeURIComponent(String(clave))
  );
}
