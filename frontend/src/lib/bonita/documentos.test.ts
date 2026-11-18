import { describe, expect, it } from 'vitest';
import { urlDeDescargaDeDocumento } from './documentos';

describe('la dirección de descarga de un documento de proceso', () => {
  it('es la de `documentDownload` del portal, relativa, con el nombre y la clave', () => {
    expect(urlDeDescargaDeDocumento({ nombreArchivo: 'justificante.png', contentStorageId: '42' })).toBe(
      '/bonita/portal/documentDownload?fileName=justificante.png&contentStorageId=42',
    );
  });

  it('escapa el nombre del fichero: un nombre con espacios o «&» no rompe la dirección', () => {
    expect(urlDeDescargaDeDocumento({ nombreArchivo: 'carta de permiso & anexo.pdf', contentStorageId: '7' })).toBe(
      '/bonita/portal/documentDownload?fileName=carta%20de%20permiso%20%26%20anexo.pdf&contentStorageId=7',
    );
  });

  it('sin contentStorageId no hay enlace: un documento registrado sin contenido no inventa uno', () => {
    expect(urlDeDescargaDeDocumento({ nombreArchivo: 'justificante.png', contentStorageId: null })).toBeNull();
    expect(urlDeDescargaDeDocumento({ nombreArchivo: 'justificante.png', contentStorageId: '  ' })).toBeNull();
    expect(urlDeDescargaDeDocumento({ nombreArchivo: 'justificante.png' })).toBeNull();
    expect(urlDeDescargaDeDocumento(null)).toBeNull();
  });

  it('sin nombre de fichero, la descarga sigue siendo posible con un nombre por defecto', () => {
    expect(urlDeDescargaDeDocumento({ nombreArchivo: '', contentStorageId: '9' })).toBe(
      '/bonita/portal/documentDownload?fileName=documento&contentStorageId=9',
    );
  });
});
