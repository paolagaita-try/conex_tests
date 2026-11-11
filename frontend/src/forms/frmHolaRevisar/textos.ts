/**
 * Textos de la pantalla «Revisar el saludo» (`frm_holaRevisar`). Este fichero es del proyecto: el arnés lo escribió
 * una vez y no lo vuelve a tocar.
 */
export const TEXTOS = {
  titulo: 'Revisar el saludo',
  accion: 'Enviar',
  enviado: 'Listo',
  enviadoDetalle: 'Recibimos sus datos.',
  error: 'No se pudo enviar',
  sinContexto: 'La pantalla no se abrió desde su tarea o su proceso en el portal.',
  errorGenerico: 'Ocurrió un error inesperado.',
  cargando: 'Cargando…',
  errorLectura: 'No se pudieron cargar los datos del caso',
  sinDatosNoSeEnvia: 'Sin los datos del caso no se puede enviar. Vuelva a abrir la pantalla.',
  subidaFallida: 'No se pudo subir un archivo; no se envió nada.',
} as const;

/** Etiquetas propias por ruta del contrato; sin una, se usa la «Campo» de la matriz (`generado/contrato.ts`). */
export const ETIQUETAS: Readonly<Record<string, string>> = {};
