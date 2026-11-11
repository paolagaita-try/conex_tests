import { numeroTecleado, type NumeroTecleado } from '$lib/ui/valores';

/**
 * Un número tecleado para un test: lo produce el MISMO lector que la pantalla, desde el texto que
 * habría escrito la persona. Un número a secas ya no entra en `valores` ni en un widget numérico.
 */
export const tecleado = (n: number): NumeroTecleado => {
  const leido = numeroTecleado(String(n));
  if (leido === null) throw new Error(`«${n}» no es un número que se pueda teclear`);
  return leido;
};
