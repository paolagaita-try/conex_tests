import { recuentoDe, type Recuento } from '$lib/bonita/marcas';

/**
 * Un recuento para un test: lo produce la MISMA productora que la pantalla, desde una lista de ese
 * tamaño. Un número a secas ya no entra en los textos de las bandejas ni en el contador de una pestaña.
 */
export const cuantos = (n: number): Recuento => recuentoDe(Array.from({ length: n }));
