/**
 * Componentes base de los formularios (la galería).
 *
 * Cubren los seis tipos de campo que usan los contratos de tarea (TEXT, DECIMAL,
 * INTEGER, BOOLEAN, DATE, FILE) más la acción y el aviso, que son transversales. Cada
 * pantalla los compone; ninguna reimplementa un control, porque la accesibilidad se
 * verifica aquí una vez y se hereda.
 *
 * | Tipo del contrato | Componente                          |
 * |-------------------|-------------------------------------|
 * | TEXT (corto)      | `Entrada` (tipo="text")             |
 * | TEXT (conjunto)   | `Seleccion`                         |
 * | TEXT (largo)      | `AreaTexto`                         |
 * | DECIMAL / INTEGER | `Entrada` (tipo="number")           |
 * | BOOLEAN           | `Casilla`                           |
 * | DATE              | `Entrada` (tipo="date")             |
 * | FILE              | `CargaArchivo`                      |
 */
export { default as Campo } from './Campo.svelte';
export { default as Entrada } from './Entrada.svelte';
export { default as AreaTexto } from './AreaTexto.svelte';
export { default as Seleccion } from './Seleccion.svelte';
export { default as Casilla } from './Casilla.svelte';
export { default as CargaArchivo } from './CargaArchivo.svelte';
export { default as Boton } from './Boton.svelte';
export { default as EnvioImplicito } from './EnvioImplicito.svelte';
export { default as Aviso } from './Aviso.svelte';

/**
 * Presentación compartida por las pantallas del solicitante: la marca (que se pinta desde
 * los tokens del tema, nunca incrustada) y el recorrido de la solicitud. Viven aquí, en la
 * galería, para que todos los formularios las hereden en vez de reinventarlas.
 */
export { default as MarcaCabecera } from './MarcaCabecera.svelte';
export { default as Seguimiento } from './Seguimiento.svelte';

/**
 * Pinta los campos de un contrato de tarea eligiendo el control por su tipo. Es lo que
 * sostiene «0 campos huérfanos» en la capa visual: la pantalla no los lista a mano.
 */
export { default as CamposDeContrato } from './CamposDeContrato.svelte';

/**
 * Visor documental de solo lectura con carrusel: lo usan las pantallas internas que
 * deciden mirando los documentos del caso. Sin dependencias: el navegador ya trae visor de PDF.
 */
export { default as VisorDocumentos } from './VisorDocumentos.svelte';
export type { DocumentoVisible } from './VisorDocumentos.svelte';

/**
 * El nombre de un documento de soporte como enlace de descarga: la dirección sale del
 * `contentStorageId` que las operations del proceso dejan en el BDM. Sin referencia, solo el
 * nombre. Lo usan las bandejas internas que listan `documentosSoporte`.
 */
export { default as EnlaceDeDocumento } from './EnlaceDeDocumento.svelte';

/**
 * La fila de acciones de una pantalla, con la confirmación de lo grave dentro. Vive en la
 * galería porque la consecuencia que se le enuncia
 * al usuario tiene que ser la misma en la pantalla aprobada y en la construida, y eso solo
 * se garantiza si las dos usan el mismo componente y la misma declaración.
 */
export { default as AccionesDeFormulario } from './AccionesDeFormulario.svelte';
export type { AccionSecundaria } from './AccionesDeFormulario.svelte';

/**
 * Las piezas de la bandeja única, reutilizables por las dos familias: los tres
 * momentos como pestañas, la fila legible en un vistazo, el vacío con voz humana, el panel de
 * detalle, el marco donde se abre cada pantalla y la cabecera con la marca y la sesión. La bandeja
 * de cada familia las compone con su proyección visible, sin reescribir ninguna.
 */
export { default as Pestanas } from './Pestanas.svelte';
export type { Pestana } from './Pestanas.svelte';
export { default as FilaDeBandeja } from './FilaDeBandeja.svelte';
export { default as EstadoVacio } from './EstadoVacio.svelte';
export { default as PanelDeDetalle } from './PanelDeDetalle.svelte';
export { default as MarcoDeFormulario } from './MarcoDeFormulario.svelte';
export { default as CabeceraDeSesion } from './CabeceraDeSesion.svelte';
export { default as LanzadorDeApps } from './LanzadorDeApps.svelte';
export { default as MenuDeCuenta } from './MenuDeCuenta.svelte';

export type { Opcion } from './Seleccion.svelte';

/**
 * Los widgets del sistema de diseño: el control que corresponde a cada dato
 * según la regla de widget por defecto. Propios de la galería y sin librerías de UI de
 * terceros, para que su accesibilidad —teclado, rol y estado, foco visible, 44 px— se verifique
 * aquí una vez. `CamposDeContrato` los cablea a los contratos.
 */
export { default as Calendario } from './Calendario.svelte';
export { default as OpcionesEnFicha } from './OpcionesEnFicha.svelte';
export type { OpcionEnFicha } from './OpcionesEnFicha.svelte';
export { default as Interruptor } from './Interruptor.svelte';
export { default as CampoConAfijo } from './CampoConAfijo.svelte';
export { default as Autocompletar } from './Autocompletar.svelte';

/**
 * Qué widget pinta cada dato: una sola regla, para que ninguna pantalla la reescriba.
 * El widget que declare el contrato gana.
 */
export { widgetPorDefecto, WIDGETS } from './widgetPorDefecto';
export type { Widget, DescripcionDelDato } from './widgetPorDefecto';

/** Lo que la persona teclea, con su tipo, y cómo se escribe una cifra en pantalla. */
export * from './valores';
export * from './formato';
