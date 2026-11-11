// GENERADO por el arnés desde docs/07-bonita/contratos.md y docs/07-bonita/matriz-formularios.md.
// NO SE EDITA A MANO: cambia la documentación y corre `tools/arnes.sh generar`. Lo propio de la pantalla
// va en los ficheros de la carpeta del formulario (el esqueleto), que el generador no vuelve a tocar.

import { z } from 'zod';
import type { CuerpoDelContrato } from './contrato';

const OBLIGATORIO = 'Este dato es obligatorio.';
const OPCION = 'Elija una de las opciones.';
const ENTERO = 'Escriba un número entero.';

/**
 * El esquema del cuerpo del contrato: la obligatoriedad de la matriz, las opciones cerradas y los enteros.
 * Lo que la matriz no usa debe ir a `null`. Las constraints del contrato las valida el motor al enviar.
 */
export const esquema = z.object({
  mensaje: z.string({ required_error: OBLIGATORIO, invalid_type_error: OBLIGATORIO }).min(1, OBLIGATORIO),
}) satisfies z.ZodType<CuerpoDelContrato>;

/** Los mensajes, para las reglas propias de la pantalla (`validacion.ts`). */
export const MENSAJES = { OBLIGATORIO, OPCION, ENTERO } as const;
