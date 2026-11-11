/**
 * El nombre de la marca del proyecto, tal como lo declara el tema (`--marca-nombre`), o `undefined` fuera del navegador.
 *
 * Vive aquí, y no en la muestra de marca, porque la muestra es una EXCEPCIÓN de la barrera de cifras y una excepción no
 * lee el DOM: lo que necesita de él es esta cadena, y nada más.
 */
export function nombreDeLaMarca(): string | undefined {
  if (typeof window === 'undefined') return undefined;
  const valor = getComputedStyle(document.documentElement)
    .getPropertyValue('--marca-nombre')
    .trim()
    .replace(/^['"]|['"]$/g, '');
  return valor || undefined;
}
