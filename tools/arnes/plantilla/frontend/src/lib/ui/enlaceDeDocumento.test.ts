/**
 * El documento aportado se puede DESCARGAR desde las pantallas internas.
 *
 * El enlace cuelga de `contentStorageId` —la referencia al documento de proceso que dejan las
 * operations del proceso— y de nada más: sin referencia no hay enlace, y con ella la dirección
 * es exactamente la de `documentDownload` del portal. Verificado por mutación: quitar el `href`
 * o pintar el enlace también sin `contentStorageId` pone en rojo uno de los dos primeros.
 */
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import EnlaceDeDocumento from './EnlaceDeDocumento.svelte';

describe('EnlaceDeDocumento', () => {
  it('con contentStorageId pinta un enlace de descarga con la dirección del portal y su testid por tipo', () => {
    const { getByTestId } = render(EnlaceDeDocumento, {
      props: { documento: { tipo: 'justificante', nombreArchivo: 'justificante.png', contentStorageId: '42' } },
    });
    const enlace = getByTestId('descarga-justificante') as HTMLAnchorElement;
    expect(enlace.tagName).toBe('A');
    expect(enlace.getAttribute('href')).toBe(
      '/bonita/portal/documentDownload?fileName=justificante.png&contentStorageId=42',
    );
    expect(enlace.getAttribute('download')).toBe('justificante.png');
    expect(enlace.textContent?.trim()).toBe('justificante.png');
  });

  it('sin contentStorageId pinta el nombre sin enlace: no se inventa una descarga', () => {
    const { queryByTestId, getByText, container } = render(EnlaceDeDocumento, {
      props: { documento: { tipo: 'carta_trabajo', nombreArchivo: 'carta.pdf', contentStorageId: null } },
    });
    expect(queryByTestId('descarga-carta_trabajo')).toBeNull();
    expect(container.querySelector('a')).toBeNull();
    expect(getByText('carta.pdf')).toBeTruthy();
  });

  it('sin nombre de archivo enseña el tipo, para que la fila no quede muda', () => {
    const { getByText } = render(EnlaceDeDocumento, {
      props: { documento: { tipo: 'estados_cuenta', nombreArchivo: '', contentStorageId: null } },
    });
    expect(getByText('estados_cuenta')).toBeTruthy();
  });
});
