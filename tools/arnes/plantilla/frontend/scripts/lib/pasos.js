/**
 * Los pasos del build de un formulario, en orden.
 *
 * La verificación de tipos va SIEMPRE, también con `--solo-empaquetar`: empaquetar el `dist` que ya hay sin verificar
 * los tipos publicaba un ZIP cuyo fuente podía no compilar —la barrera de origen de las cifras es un tipo, así que «no
 * compila» tiene que seguir significando «no se construye» aunque no se recompile—.
 *
 * @param {readonly string[]} argumentos los de la línea de órdenes
 * @returns {('verificar-tipos' | 'compilar' | 'empaquetar')[]}
 */
export function pasosDelBuild(argumentos) {
  const soloEmpaquetar = argumentos.includes('--solo-empaquetar');
  return ['verificar-tipos', ...(soloEmpaquetar ? [] : ['compilar']), 'empaquetar'];
}
