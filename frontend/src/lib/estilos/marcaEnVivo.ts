/**
 * Aplica la marca del proyecto que el módulo de parámetros sirve (nombre, logo y colores) sobre los tokens por
 * defecto. Se importa por efecto desde el `main.ts` de cada pantalla, igual que `enMarco`: la lectura
 * arranca con el documento y nunca bloquea ni rompe la pantalla (ver `$lib/parametros/marca`).
 */
import { cargarMarca } from '$lib/parametros/marca';

void cargarMarca();
