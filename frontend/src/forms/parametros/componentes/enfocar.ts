/**
 * Teclado (CRN-10): un panel que se ABRE (edición en línea, confirmación) lleva el foco a su primer campo, y al CERRARSE
 * el foco vuelve a lo que lo abrió. Sin esto, abrir un formulario deja el foco en el botón que ya no está y, al guardar,
 * cae al `body`: quien navega con teclado o lector de pantalla se queda sin lugar.
 */
export function enfocarAlMostrar(nodo: HTMLElement): { destroy: () => void } {
  const previo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  queueMicrotask(() => nodo.querySelector<HTMLElement>('input:not([disabled]):not([type=hidden]), textarea:not([disabled]), select:not([disabled])')?.focus());
  return {
    destroy: () => {
      if (previo && previo.isConnected) previo.focus();
      else document.querySelector<HTMLElement>('main.pa h2, main.pa h1')?.focus?.();
    },
  };
}

/** Escape cierra el panel (y devuelve el foco a quien lo abrió). */
export const cerrarConEscape = (cerrar: () => void) => (e: KeyboardEvent): void => {
  if (e.key === 'Escape') {
    e.stopPropagation();
    cerrar();
  }
};
