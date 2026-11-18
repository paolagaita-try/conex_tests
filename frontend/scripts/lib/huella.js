/**
 * Huella de las fuentes que entran en el paquete de un formulario.
 *
 * Existe por un falso verde que se repitió: `mvn package` NO recompila el front, solo copia
 * los ZIP que encuentre en `dist-zips`. Se arregla una pantalla, se relanza el runtime
 * entero, todo sale verde… y lo que se está mirando es la versión anterior. Pasó el
 * 2026-09-09 (una pantalla arreglada que seguía sirviendo la vieja) y volvió a pasar el
 * 2026-09-10 midiendo contraste en el navegador, con la trampa ya documentada en el README
 * del proyecto. Una nota en prosa no lo impidió, así que aquí hay mecánica: el empaquetador
 * estampa qué fuentes empaquetó y un custodio de CI lo recalcula y lo compara.
 *
 * La huella se calcula igual en Node y en Python: sha256 sobre, para cada fichero en orden
 * de ruta relativa (POSIX), `ruta \0 bytes \0`. Sin JSON, sin fechas, sin orden del sistema
 * de ficheros: dos implementaciones distintas tienen que llegar al mismo número.
 *
 * Qué entra: la carpeta del formulario, todo `src/lib` (los componentes y los tokens que
 * comparte), la fuente de diseño `src/forms/_prototipos` (sus enunciados se inlinean en los
 * bundles que los importan) y **`forms.manifest.json`**. Qué NO: los ficheros de prueba —no viajan en el
 * bundle, y contarlos obligaría a reempaquetar por cambiar un test— ni `node_modules`, ni la
 * salida de build.
 *
 * El manifiesto entra porque de él salen el NOMBRE del recurso, sus PERMISOS REST y su
 * FAMILIA: es decir, la identidad y la superficie de acceso del paquete, no solo su pintura.
 * Se descubrió que faltaba de la peor manera posible: durante un experimento se le añadió un
 * permiso a un formulario, se reempaquetó y se desplegó… y la suite siguió en verde, porque
 * la huella solo miraba `src/`. Un guard que no cubre el fichero que decide los permisos no
 * es un guard. Se toma el fichero completo y no la entrada del formulario: comparar un
 * fragmento de JSON exigiría canonicalizarlo igual en Node y en Python (orden de claves,
 * espaciado), y esa clase de acuerdo se rompe en silencio. Editar el manifiesto obliga a
 * reempaquetar todos los formularios — es rara y consecuente, así que sale barato.
 */
import { createHash } from 'node:crypto';
import path from 'node:path';
import fs from 'fs-extra';

/** Un fichero de prueba no entra en el paquete: no debe mover la huella. */
const ES_PRUEBA = /\.(test|spec)\.[jt]sx?$/;
/**
 * Carpetas que no son fuente y pueden aparecer dentro de `src/forms/<id>` (una caché de vitest con
 * cwd en el módulo deja `node_modules/.vite/`). El docstring de arriba ya decía «ni node_modules»
 * y el código no lo hacía. Un custodio externo que recalcule la huella debe usar la misma lista.
 */
const CARPETAS_EXCLUIDAS = new Set(['node_modules', '.vite']);

async function listar(directorio, raiz, acumulado) {
  if (!(await fs.pathExists(directorio))) return acumulado;
  for (const entrada of (await fs.readdir(directorio, { withFileTypes: true })).sort((a, b) =>
    a.name < b.name ? -1 : 1,
  )) {
    const completa = path.join(directorio, entrada.name);
    if (entrada.isDirectory()) {
      if (CARPETAS_EXCLUIDAS.has(entrada.name)) continue;
      await listar(completa, raiz, acumulado);
    } else if (entrada.isFile() && !ES_PRUEBA.test(entrada.name)) {
      acumulado.push(path.relative(raiz, completa).split(path.sep).join('/'));
    }
  }
  return acumulado;
}

/** Rutas (relativas a la raíz del front, POSIX, ordenadas) que definen el paquete de `id`. */
export async function fuentesDe(raiz, id) {
  const rutas = [];
  await listar(path.join(raiz, 'src', 'forms', id), raiz, rutas);
  await listar(path.join(raiz, 'src', 'lib'), raiz, rutas);
  // La fuente de diseño también viaja: las pantallas importan sus enunciados aprobados de
  // `_prototipos/catalogo.ts` y Vite los INLINEA en el bundle (verificado con unzip | grep). Sin esta línea, cambiar lo que una pantalla DICE no desfasaba su ZIP — el hueco
  // exacto que este guard existe para cerrar. Entra entera, como `src/lib`: sobreinvalidar es
  // barato (build:all) y decidir qué pantalla importa qué exigiría resolver imports igual en
  // Node y en Python, acuerdo que se rompe en silencio.
  if (id !== '_prototipos') {
    await listar(path.join(raiz, 'src', 'forms', '_prototipos'), raiz, rutas);
  }
  if (await fs.pathExists(path.join(raiz, 'forms.manifest.json'))) {
    rutas.push('forms.manifest.json');
  }
  return rutas.sort();
}

/** sha256 de esas fuentes. Algoritmo reproducible en Python. */
export async function huellaDeFuentes(raiz, id) {
  const hash = createHash('sha256');
  for (const relativa of await fuentesDe(raiz, id)) {
    hash.update(relativa, 'utf-8');
    hash.update('\0');
    hash.update(await fs.readFile(path.join(raiz, relativa)));
    hash.update('\0');
  }
  return hash.digest('hex');
}
