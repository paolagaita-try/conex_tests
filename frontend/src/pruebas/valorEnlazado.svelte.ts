/**
 * Un `valor` ENLAZADO y reactivo para montar un componente con `$bindable` en un test, como lo
 * haría una pantalla con `bind:valor` sobre su `$state`.
 *
 * Por qué hace falta: con un getter/setter sobre una variable normal el componente ESCRIBE el
 * valor (el test lo lee) pero nunca se repinta al leerlo, porque la fuente no es reactiva. Lo
 * destapó la primera versión del test de `OpcionesEnFicha`: el clic elegía y la ficha
 * seguía sin marcar — un rojo del arnés, no del componente.
 *
 * Vive en `src/pruebas` (alias `$pruebas`, solo en vitest): no viaja al ZIP.
 */
export function conValorEnlazado<T, P extends object>(props: P, inicial: T) {
  let valor = $state(inicial);
  const enlazadas = Object.defineProperty({ ...props }, 'valor', {
    get: () => valor,
    set: (v: T) => {
      valor = v;
    },
    enumerable: true,
    // Svelte envuelve las props en un proxy: una propiedad no configurable rompe su trampa.
    configurable: true,
  }) as P & { valor: T };
  return { props: enlazadas, valor: () => valor, fijar: (v: T) => (valor = v) };
}
