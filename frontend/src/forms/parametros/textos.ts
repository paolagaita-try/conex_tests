/**
 * TODO el texto de la aplicación de parámetros, declarado UNA vez.
 *
 * Voz de negocio: ni códigos ni nombres de tareas del motor como dato principal, ni «No hay datos»,
 * ni JSON. Los vacíos y los errores hablan en humano. Los recuentos llegan marcados (`Recuento`): este
 * módulo es el único que los convierte en texto (`recuento()` del cimiento).
 */
import { sumaDeRecuentos, type Recuento } from '$lib/bonita/marcas';
import { recuento } from '$lib/ui/formato';

// ─── Marco de la aplicación ───────────────────────────────────────────────────────────────────────

export const TITULO_DE_LA_PAGINA = 'Parámetros de negocio';
export const CARGANDO = 'Consultando los parámetros…';
export const REINTENTAR = 'Reintentar';
export const ERROR_TITULO = 'No pudimos consultar los parámetros.';
export const ERROR_CUERPO = 'Inténtalo de nuevo en unos segundos.';
/**
 * Compuerta de familia: si la API `parametros` responde 403, la aplicación solo dice esto. Neutro a
 * propósito: no nombra procesos, actividades ni administradores.
 */
export const NO_DISPONIBLE_TITULO = 'Esta aplicación no está disponible para tu usuario.';
export const NO_DISPONIBLE_CUERPO = 'Si crees que deberías tener acceso, avisa a quien administra la plataforma.';

export const saludo = (nombre?: string | null) => (nombre ? `Hola, ${nombre}` : 'Hola');

export const PESTANAS = {
  parametros: 'Parámetros',
  aprobaciones: 'Aprobaciones',
  permisos: 'Permisos',
  traza: 'Traza',
} as const;
export const NOMBRE_DE_LAS_SECCIONES = 'Secciones de Parámetros';

export const CHIP_SUPERADMINISTRACION = 'Superadministración';
export const chipDelegado = (procesos: string) => `Delegado · ${procesos}`;

export function titularDeSuperadministracion(pendientes: Recuento): string {
  if (pendientes === 0) return 'Nada espera tu aprobación por ahora.';
  if (pendientes === 1) return '1 cambio espera tu aprobación.';
  return `${recuento(pendientes)} cambios esperan tu aprobación.`;
}
export const titularDelDelegado = (procesos: string) => `Puedes editar los parámetros de ${procesos}.`;
export const TITULAR_DE_CONSULTA = 'Puedes consultar los parámetros vigentes.';

// ─── Inicio ───────────────────────────────────────────────────────────────────────────────────────

export const BUSCAR_ROTULO = 'Buscar un parámetro o una lista';
export const BUSCAR_PISTA = 'Buscar por nombre: duración, pago, beca…';
export const QUE_MOSTRAR = 'Qué mostrar';
export const SEGMENTOS_DE_SUPERADMINISTRACION = { todo: 'Todo', listas: 'Listas', parametros: 'Parámetros' } as const;
export const SEGMENTOS_DEL_DELEGADO = { editable: 'Lo que puedo editar', todo: 'Todo' } as const;
export const IMPORTAR_CSV = 'Importar CSV';
export const EXPORTAR = 'Exportar';

export const GRUPO_GLOBALES = 'Globales · valen para todos los procesos';
export const GRUPO_GLOBALES_SOLO_LECTURA = 'Globales · solo lectura';
export const GRUPO_GLOBALES_CONSULTA = 'Globales';

export const PROCESO_SIN_PARAMETROS_TITULO = 'Este proceso aún no tiene parámetros.';
export const PROCESO_SIN_PARAMETROS_CUERPO =
  'Cuando su equipo lo conecte al módulo, sus listas y parámetros aparecerán aquí sin cambiar esta aplicación.';

export const sinResultadosTitulo = (q: string) => `Nada coincide con «${q}».`;
export const SIN_RESULTADOS_CUERPO =
  'Busca por el nombre que usa el negocio —«duración», «pago», «beca»—, no por el código técnico. Si el proceso que buscas aún no está conectado al módulo, sus parámetros no aparecerán todavía.';
export const VER_TODOS = 'Ver todos los parámetros';

export const TUS_PERMISOS = 'Tus permisos';
export const TUS_PERMISOS_COLA = 'Lo demás lo ves en solo lectura. Si necesitas más, pídeselo a la superadministración.';
export const MODO_CONSULTA_TITULO = 'Estás en modo consulta';
export const MODO_CONSULTA_CUERPO =
  'Puedes ver los valores vigentes y su historial. Para cambiar algo necesitas una delegación sobre el proceso; pídesela a la superadministración.';

export const CHIP_IMPACTO_ALTO = 'Impacto alto';
export const CHIP_POR_APROBAR_SUPERADMINISTRACION = 'Cambio por aprobar';
export const CHIP_POR_APROBAR = 'Por aprobar';
export const CHIP_SOLO_LECTURA = 'Solo lectura';
export const CHIP_HEREDADA = 'Heredada';
export const VER = 'Ver';

const plural = (n: Recuento, uno: string, varios: string) => (n === 1 ? `1 ${uno}` : `${recuento(n)} ${varios}`);

export const opciones = (n: Recuento) => plural(n, 'opción', 'opciones');
export const conInactivas = (activas: Recuento, inactivas: Recuento) => {
  const base = opciones(sumaDeRecuentos(activas, inactivas));
  if (inactivas === 0) return base;
  return `${base}, ${plural(inactivas, 'inactiva', 'inactivas')}`;
};
export const versionPropiaEn = (n: Recuento) => `Versión propia en ${plural(n, 'actividad', 'actividades')}`;
export const valoresPorPadre = (n: Recuento) => plural(n, 'valor', 'valores');

export const TIPO_LISTA = 'Lista';
export const TIPO_PARAMETRO = 'Parámetro';
export const tipoListaEnCascada = (padre: string) => `Lista en cascada de ${padre}`;
export const tipoParametroPorPadre = (padre: string) => `Parámetro por ${padre}`;
export const deEllaDependen = (nombres: string) => `de ella dependen ${nombres}`;

// ─── Exportación ──────────────────────────────────────────────────────────────────────────────────

export const COLUMNAS_DE_EXPORTACION = ['Dónde vale', 'Nombre', 'Tipo', 'Valor u opciones', 'Último cambio', 'Impacto', 'Por aprobar'] as const;
export const NOMBRE_DEL_FICHERO_DE_PARAMETROS = 'parametros-vigentes.csv';
export const IMPACTO_NORMAL = 'Normal';
export const IMPACTO_ALTO = 'Alto';
export const SI = 'Sí';
export const NO = 'No';

// ─── Tus permisos (delegado) ───────────────────────────────────────────────────────────────────────

export const PUEDES_EDITAR = 'Puedes editar las listas y parámetros de';
export const TODAS_SUS_ACTIVIDADES = 'en todas sus actividades';
export const soloEn = (actividades: string) => `solo en ${actividades}`;
export const SIN_FECHA_DE_FIN = 'sin fecha de fin';
export const hastaEl = (fecha: string) => `hasta el ${fecha}`;

// ─── Rechazos del kit, en negocio ────────────────────────────────────────────────────────────────

export const FALLO_GENERAL = 'No pudimos guardar. Inténtalo de nuevo; no se cambió nada.';
export const FALLO_SIN_PERMISO = 'Ya no tienes permiso para hacer este cambio. No se guardó nada; si crees que es un error, pídeselo a la superadministración.';
export const FALLO_CONFLICTO = 'Otra persona cambió esto mientras lo editabas. Recarga y vuelve a intentarlo: no se guardó nada.';
export const FALLO_NO_EXISTE = 'Esto ya no existe. Vuelve al inicio y búscalo de nuevo.';
export const FALLO_REVISA = 'Revisa lo que escribiste: el cambio no se aceptó y no se guardó nada.';
export const ERROR_MOTIVO = 'Escribe el motivo del cambio: queda en la traza junto con tu nombre.';
export const ERROR_ETIQUETA = 'Escribe el nombre que verá el formulario.';
export const ERROR_COMENTARIO = 'El comentario es obligatorio si rechazas.';
export const ERROR_CODIGO = 'Escribe un código con minúsculas, números, «_» o «-», sin espacios.';
export const ERROR_CODIGO_REPETIDO = 'Ya hay una opción con ese código en esta lista.';
export const ERROR_VALOR_FUERA_DE_RANGO = 'El valor no está dentro de lo permitido.';

// ─── Lista ───────────────────────────────────────────────────────────────────────────────

export const GLOBAL = 'Global';
export const SUPERADMINISTRACION = 'Superadministración';
export const TODOS_LOS_PARAMETROS = 'Todos los parámetros';
export const LISTA_GLOBAL = 'Lista global';
export const LISTA_DEL_PROCESO = 'Lista del proceso';
export const LISTA_PROPIA_DE_LA_ACTIVIDAD = 'Lista propia de esta actividad';
export const ROTULO_AMBITO = 'Ámbito';
export const ROTULO_CODIGO = 'Código';
export const ROTULO_TIPO = 'Tipo';
export const ROTULO_IMPACTO = 'Impacto';
export const ROTULO_ORIGEN = 'Origen';
export const IMPACTO_ALTO_DOBLE_CONTROL = 'Alto · doble control';
export const LLEGO_CON_EL_PROCESO = 'Llegó con el proceso';
export const CREADA_EN_LA_APLICACION = 'Creada en esta aplicación';

// ─── Historial y traza, en frases ───────────────────────────────────

export const SISTEMA = 'Sistema';
export const ORIGEN_PANTALLA = 'desde la pantalla';
export const ORIGEN_CSV = 'por importación';
export const ORIGEN_SEMILLA = 'al desplegar el proceso';
export const ORIGEN_RESTABLECIMIENTO = 'al restablecer la demostración';
export const CHIP_SEMILLA = 'Semilla';

export const hist = {
  creoLaDefinicion: 'creó la definición',
  anadioLaOpcion: 'añadió la opción',
  fijoElValor: (nombre: string) => `fijó el valor de «${nombre}» en`,
  en: 'en',
  cambioElNombre: 'cambió el nombre de una opción:',
  cambioElValorDe: 'cambió el valor de',
  edito: 'editó',
  desactivo: 'desactivó',
  reactivo: 'reactivó',
  cambioElOrdenDe: 'cambió el orden de',
  creoUnaVersionPropia: 'creó una versión propia de',
  para: 'para',
  aPartirDeLaListaDelProceso: ' a partir de la lista del proceso',
  volvioAHeredar: 'volvió a heredar',
  cambioLaDefinicionDe: 'cambió la definición de',
  propusoCambiar: 'propuso cambiar',
  propusoDelegar: 'propuso delegar',
  aproboDelegar: 'aprobó delegar',
  rechazoDelegar: 'rechazó delegar',
  retiroDelegar: 'retiró su propuesta de delegar',
  aprobo: 'aprobó el cambio de',
  propuestoPor: (nombre: string) => `propuesto por ${nombre}`,
  rechazo: 'rechazó el cambio de',
  retiro: 'retiró su propuesta sobre',
  delego: 'delegó',
  revoco: 'revocó',
  permisos: 'Permisos',
  unaPersona: 'una persona',
  importo: 'importó cambios en',
  variasListas: 'varias listas',
  llegoConElProceso: 'La definición llegó con el proceso',
  restablecio: 'Se restablecieron los valores de la demostración.',
  hizoUnCambio: 'hizo un cambio en',
} as const;

export const VOLVER_A_TODOS = 'Todos los parámetros';
export const SECCIONES_DE_LA_LISTA = 'Secciones de la lista';
export const SECCIONES_DEL_PARAMETRO = 'Secciones del parámetro';
export const PESTANA_VALORES = 'Valores';
export const PESTANA_VALOR = 'Valor';
export const PESTANA_DONDE_SE_USA = 'Dónde se usa';
export const PESTANA_HISTORIAL = 'Historial';
export const ANADIR_OPCION = 'Añadir opción';
export const ANADIR_OPCION_ROTULO = '+ Añadir opción';
export const COLUMNA_ORDEN = 'Orden';
export const COLUMNA_OPCION = 'Opción';
export const COLUMNA_CODIGO = 'Código';
export const COLUMNA_ESTADO = 'Estado';
export const COLUMNA_VIENE_DE = 'Viene de';
export const COLUMNA_ACCIONES = 'Acciones';
export const CHIP_ACTIVA = 'Activa';
export const CHIP_INACTIVA = 'Inactiva';
export const EDITAR = 'Editar';
export const DESACTIVAR = 'Desactivar';
export const REACTIVAR = 'Reactivar';
export const SUBIR = 'Subir';
export const BAJAR = 'Bajar';
export const subirA = (nombre: string) => `Subir ${nombre}`;
export const bajarA = (nombre: string) => `Bajar ${nombre}`;
export const VOLVER_A_HEREDAR = 'Volver a heredar';
export const CREAR_VERSION_PROPIA = 'Crear versión propia';
export const IR_A_LA_LISTA_DEL_PROCESO = 'Ir a la lista del proceso';
export const opcionesYActivas = (total: Recuento, activas: Recuento) =>
  `${opciones(total)} · ${activas === 1 ? '1 activa' : `${recuento(activas)} activas`}`;
export const PRODUCTO_ROTULO = 'Elige para qué opción de la lista madre ves y editas los valores';
export const elegirPadre = (nombreDeLaMadre: string) => `${nombreDeLaMadre}:`;
export const padreConCuantas = (etiqueta: string, cuantas: Recuento) => `${etiqueta} · ${recuento(cuantas)}`;

export const heredaTitulo = (de: string) => `Esta actividad usa la lista de «${de}»`;
export const HEREDA_CUERPO =
  'Si creas una versión propia, esta actividad dejará de ver la lista del proceso y usará solo la suya. Empieza como una copia exacta que puedes ajustar; la lista del proceso no cambia.';
export const HEREDADA_SE_EDITA_EN_EL_ORIGEN = 'Mientras la lista sea heredada, se edita en su origen: cualquier cambio allí se verá aquí.';
export const nuevasDelOrigen = (n: Recuento) =>
  n === 1 ? 'El origen tiene 1 opción nueva desde que copiaste esta lista.' : `El origen tiene ${recuento(n)} opciones nuevas desde que copiaste esta lista.`;
export const NUEVAS_DEL_ORIGEN_AYUDA = 'Tu versión propia no las ofrece: si las quieres, añádelas aquí o vuelve a heredar la lista del proceso.';
export const sinHijasTitulo = (padre: string) => `${padre} no tiene opciones en esta lista`;
export const sinHijasCuerpo = (padre: string, campo: string) =>
  `Es correcto si ${padre} no usa esta lista. En el formulario, al elegir ${padre.toLowerCase()} el campo «${campo}» no aparece.`;
export const huerfanasTitulo = 'Hay opciones cuyo padre ya no existe';
export const huerfanasCuerpo = (nombres: string) =>
  `No se ofrecen en ningún formulario: ${nombres}. Vuelve a activar su opción madre o desactívalas.`;
export const SIN_OPCIONES = 'Esta lista aún no tiene opciones.';

export const VISTA_PREVIA = 'Así se verá en el formulario';
export const VISTA_PREVIA_AYUDA = 'La vista previa cambia mientras escribes.';
export const VISTA_PREVIA_REGLA = 'Con 2 a 5 opciones el formulario las muestra como fichas; con más, como desplegable; con más de 15, con buscador.';
export const OPCION_VACIA = 'Elige una opción';
export const QUIEN_PUEDE_EDITAR = 'Quién puede editar esto';
export const VER_PERMISOS = 'Ver permisos';
export const DEFINICION = 'Definición';

export const EDITAR_OPCION = (nombre: string) => `Editar «${nombre}»`;
export const NUEVA_OPCION = 'Nueva opción';
export const CAMPO_NOMBRE = 'Nombre que ve el formulario';
export const CAMPO_CODIGO = 'Código';
export const CODIGO_BLOQUEADO = 'No se puede cambiar una vez creada la opción: los formularios y las reglas la identifican por él.';
export const CODIGO_NUEVO_AYUDA = 'Minúsculas, números, «_» o «-». No podrás cambiarlo después.';
export const CAMPO_AYUDA = 'Texto de ayuda (opcional)';
export const AYUDA_PLACEHOLDER = 'Aparece debajo de la opción en el formulario';
export const CAMPO_MOTIVO = 'Motivo del cambio';
export const MOTIVO_AYUDA = 'Queda en la traza junto con tu nombre, la hora y el valor anterior. Lo leerá auditoría.';
export const GUARDAR_CAMBIO = 'Guardar cambio';
export const CANCELAR = 'Cancelar';
export const IMPACTO_NORMAL_SE_APLICA = 'Impacto normal: se aplica al guardar.';
export const GUARDANDO = 'Guardando…';

export const desactivarTitulo = (nombre: string) => `¿Desactivar «${nombre}»?`;
export const DESACTIVAR_CUERPO = 'Dejará de ofrecerse en los formularios desde ese momento. Los expedientes que ya la eligieron la conservan y la siguen mostrando; nada se borra y se puede reactivar cuando quieras.';
export const DESACTIVAR_OPCION = 'Desactivar opción';
export const reactivarTitulo = (nombre: string) => `¿Reactivar «${nombre}»?`;
export const REACTIVAR_CUERPO = 'Volverá a ofrecerse en los formularios desde ese momento.';
export const REACTIVAR_OPCION = 'Reactivar opción';
export const crearVersionTitulo = 'Crear una versión propia';
export const CREAR_VERSION_CUERPO = 'Esta actividad tendrá una copia exacta de la lista del proceso y dejará de ver sus cambios. La lista del proceso no cambia.';
export const volverAHeredarTitulo = '¿Volver a heredar la lista del proceso?';
export const VOLVER_A_HEREDAR_CUERPO = 'La versión propia de esta actividad se desactiva (no se borra) y vuelve a verse la lista del proceso, con sus cambios.';
export const VOLVER_A_HEREDAR_ACCION = 'Volver a heredar';
export const ORDEN_SIN_GUARDAR = 'Cambiaste el orden. Guárdalo con su motivo o descártalo.';
export const GUARDAR_ORDEN = 'Guardar el orden';
export const DESCARTAR = 'Descartar';
export const GUARDADO = 'Guardado.';
export const ENVIADO_A_APROBACION = 'Este cambio es de impacto alto: quedó como propuesta y otra persona tiene que aprobarlo.';

export const ULTIMA_MODIFICACION = 'Última modificación';
export const SIN_CAMBIOS_REGISTRADOS = 'Todavía no hay cambios registrados desde que llegó con el proceso.';
export const OPCIONES_INACTIVAS_AYUDA = 'Las opciones inactivas no se ofrecen, pero los expedientes que ya las usan las siguen mostrando.';

// Dónde se usa
export const USOS_NO_DISPONIBLE_TITULO = 'Esta vista aún no está disponible en este despliegue.';
export const USOS_NO_DISPONIBLE_CUERPO =
  'Se arma a partir de los usos que registran los procesos y los formularios al leer la lista. Cuando el módulo los sirva, aparecerán aquí sin configurar nada.';
export const USOS_VACIO_TITULO = 'Todavía nadie ha usado esta lista.';
export const USOS_VACIO_CUERPO = 'Cuando un formulario o un proceso la lea, aparecerá aquí.';
export const EXPEDIENTES_QUE_LA_USAN = 'Expedientes que la usan';
export const COLUMNA_GUARDADOS = 'Guardados';
export const COLUMNA_EN_CURSO = 'En curso';
export const USOS_AYUDA = 'Esta vista se arma sola a partir de los formularios desplegados y los expedientes guardados: si otro proceso empieza a usar la lista, aparecerá aquí sin configurar nada.';
export const TIPO_DE_USO = { FORMULARIO: 'Formulario', DOCUMENTO: 'Documento generado', REGLA: 'Regla del proceso' } as const;

// Historial
export const PERIODOS = { noventa: 'Últimos 90 días', anio: 'Este año', todo: 'Todo' } as const;
export const CADENA_COHERENTE = '✓ Cadena coherente';
export const EXPORTAR_CSV = 'Exportar CSV';
export const HISTORIAL_VACIO_TITULO = 'No hay cambios en este periodo.';
export const HISTORIAL_VACIO_CUERPO = 'Prueba con «Todo» para ver el historial completo.';
export const HISTORIAL_AYUDA =
  'La aplicación no permite editar ni borrar la traza, tampoco a la superadministración. Cada entrada lleva una huella encadenada con la anterior: la verificación detecta ediciones o borrados en medio de la cadena, no una reescritura completa hecha directamente en la base de datos.';
export const HISTORIAL_RECHAZOS_AYUDA = 'Los intentos rechazados se registran aparte, fuera de la cadena.';
export const MOTIVO_ROTULO = 'Motivo:';
export const CARGANDO_HISTORIAL = 'Consultando el historial…';
export const VER_MAS = 'Ver entradas más antiguas';
export const NOMBRE_DEL_FICHERO_DE_HISTORIAL = 'historial.csv';
export const COLUMNAS_DE_HISTORIAL = ['Cuándo', 'Quién', 'Qué', 'Cambio', 'Motivo'] as const;
export const VERSIONES_PROPIAS = 'Versiones propias';
export const TIENE_VERSION_PROPIA = 'tiene versión propia';
export const HEREDA_ESTA = 'hereda esta lista';

// ─── Parámetro ───────────────────────────────────────────────────────────────────────────

export const ROTULO_RANGO = 'Rango';
export const VALOR_BASE_DE_LA_ORGANIZACION = 'Valor base de la organización';
export const APLICA_AQUI_LO_EDITAS_AHORA = 'Aplica aquí · lo editas ahora';
export const aplicaAquiPorAprobar = (propuesto: string) => `Aplica aquí · ${propuesto} por aprobar`;
export const VALOR_DEL_PROCESO = 'Valor propio del proceso';
export const HEREDA_DEL_GLOBAL = 'Hereda del valor global';
export const HEREDA_DEL_PROCESO = 'Hereda del proceso';
export const HEREDAN_DEL_PROCESO = 'Heredan del proceso';
export const VALOR_GLOBAL = 'Valor global';
export const VALOR_PROPIO_DEL_PROCESO = 'Valor propio de este proceso';
export const VALOR_PROPIO_DE_LA_ACTIVIDAD = 'Valor propio de esta actividad';
export const HEREDADO = 'Hereda su valor';
export const QUE_VALOR_APLICA = 'Qué valor aplica en cada sitio';
export const QUE_VALOR_APLICA_AYUDA = 'Gana el más específico: una actividad con valor propio manda sobre el proceso, y el proceso sobre el global.';
export const CADENA_DE_HERENCIA = 'Cadena de herencia';
export const NUEVO_VALOR = 'Nuevo valor';
export const VALOR = 'Valor';
export const campoValor = (nombre: string, donde: string) => `${nombre} para ${donde}`;
export const REVISAR_EL_CAMBIO = 'Revisar el cambio';
export const IMPACTO_ALTO_NECESITA_APROBACION = 'Impacto alto: el cambio necesita la aprobación de otra persona.';
export const VALOR_AYUDA_MOTIVO_APROBADOR = 'Lo verá quien apruebe el cambio y quedará en la traza.';
export const ENVIAR_A_APROBACION = 'Enviar a aprobación';
export const VOLVER_A_EDITAR = 'Volver a editar';
export const mientrasNadieLoApruebe = (actual: string) => `Mientras nadie lo apruebe, sigue valiendo ${actual}.`;
export const CUANDO_OTRA_PERSONA_LO_APRUEBE =
  'Cuando otra persona con permiso lo apruebe, los expedientes que se decidan desde ese momento usarán el valor nuevo. Los que ya se decidieron conservan el valor con el que se decidieron.';
export const DONDE_APLICA = 'Dónde aplica';
export const VALOR_GLOBAL_NO_CAMBIA = 'Valor global';
export const noCambia = (v: string) => `${v} · no cambia`;
export const DOBLE_CONTROL_TITULO = 'Doble control';
export const DOBLE_CONTROL_CUERPO =
  'Los parámetros de impacto alto no cambian con una sola persona: quien propone no puede aprobar. Quienes tienen permiso sobre este ámbito lo verán en Aprobaciones.';
export const HAY_UN_CAMBIO_ESPERANDO = 'Hay un cambio esperando aprobación';
export const propusisteTu = (antes: string, despues: string, cuando: string) => ({ antes, despues, cuando });
export const SIGUE_VALIENDO = 'sigue valiendo';
export const VER_EN_APROBACIONES = 'Ver en Aprobaciones';
export const RETIRAR_MI_PROPUESTA = 'Retirar mi propuesta';
export const NO_SE_PUEDE_EDITAR_MIENTRAS =
  'No se puede editar mientras haya un cambio pendiente: primero se aprueba, se rechaza o se retira.';
export const OTRA_PERSONA_CAMBIO_TITULO = 'Otra persona cambió este valor mientras lo editabas';
export const TU_PROPUESTA_NO_SE_ENVIO = 'Tu propuesta no se envió, para no pisar la suya.';
export const REVISAR_SU_PROPUESTA = 'Revisar su propuesta';
export const CARGAR_EL_VALOR_ACTUAL = 'Cargar el valor actual';
export const LO_QUE_TENIAS_ESCRITO = 'Lo que tenías escrito (no se ha guardado)';
export const TU_MOTIVO = 'Tu motivo';
export const LO_CONSERVAMOS = 'Lo conservamos para que puedas reutilizarlo si sigue haciendo falta.';
export const GUARDAR_VALOR = 'Guardar cambio';
export const IMPACTO_NORMAL_AL_GUARDAR = 'Impacto normal: se aplica al guardar.';
export const SIN_VALOR_PROPIO = 'Todavía no tiene un valor propio aquí: hereda el de arriba.';
export const VALORES_POR_OPCION = 'Valor por opción';
export const elegirValorDe = (nombre: string) => `${nombre}:`;

// ─── Aprobaciones ────────────────────────────────────────────────────────────────

export const ESPERAN_TU_APROBACION = 'Esperan tu aprobación';
export const PROPUESTOS_POR_TI = 'Propuestos por ti';
export const RESUELTOS_RECIENTEMENTE = 'Resueltos recientemente';
export const CAMBIOS_POR_APROBAR = 'Cambios por aprobar';
export const NADA_PARA_APROBAR_TITULO = 'Nada espera tu aprobación.';
export const NADA_PARA_APROBAR_CUERPO = 'Cuando alguien proponga un cambio de impacto alto que puedas aprobar, aparecerá aquí.';
export const PROPUESTO_POR = 'Propuesto por';
export const CUANDO = 'Cuándo';
export const MOTIVO_DE_QUIEN_PROPONE = 'Motivo de quien lo propone';
export const TU_COMENTARIO = 'Tu comentario';
export const COMENTARIO_AYUDA = '(obligatorio si rechazas)';
export const COMENTARIO_PLACEHOLDER = 'Por ejemplo: verificado contra el acta del consejo firmada el 26 sep.';
export const APROBAR_Y_APLICAR = 'Aprobar y aplicar';
export const RECHAZAR = 'Rechazar';
export const APROBAR_AYUDA = 'Al aprobar, el cambio se aplica al instante y la traza guarda las dos firmas: quién lo propuso y quién lo aprobó.';
export const LA_PROPUSISTE_TU_TITULO = 'Este cambio lo propusiste tú';
export const LA_PROPUSISTE_TU_CUERPO =
  'Otra persona con permiso sobre este ámbito tiene que aprobarlo: es el doble control de los cambios de impacto alto.';
export const NO_PUEDES_APROBAR_LO_TUYO = 'No puedes aprobar tus propios cambios.';
export const APROBADO_Y_APLICADO = 'Aprobado y aplicado. La traza guardó las dos firmas.';
export const RECHAZADO_QUEDA_EN_LA_TRAZA = 'Rechazado. El parámetro conserva su valor y tu comentario queda en la traza.';
export const PROPUESTA_RETIRADA = 'Propuesta retirada.';
export const SELECCIONA_UNA = 'Elige un cambio de la lista para ver su detalle.';
export const ACTIVIDAD_AYUDA_NO_DISPONIBLE = '';
export const CAMBIO_DE_TEXTO = 'Cambio de texto';
export const UNA_PERSONA = 'Una persona';
export const UN_GRUPO = 'Un grupo';
export const UN_ROL = 'Un rol';
export const CON_SUBGRUPOS = '(con subgrupos)';
export const TODO_EL_PROCESO = 'Todo el proceso';
export const estadoResuelto = (estado: string) => (estado === 'APROBADA' ? 'Aprobada' : estado === 'RECHAZADA' ? 'Rechazada' : 'Retirada');

// ─── Permisos ────────────────────────────────────────────────────────────────────────────

export const hastaElTexto = (fecha: string) => `Hasta el ${fecha}`;
export const SIN_FECHA_DE_FIN_MAYUS = 'Sin fecha de fin';
export const PERMISOS_VIGENTES = 'Vigentes';
export const PERMISOS_VENCIDAS = 'Vencidas y revocadas';
export const DELEGAR = 'Delegar';
export const SUPERADMIN_PUEDE_TODO_TITULO = 'La superadministración puede todo';
export const SUPERADMIN_PUEDE_TODO_CUERPO =
  'La tienen quienes tienen el rol «Superadministrador de parámetros» en la organización de Bonita. Aquí se delega la administración de procesos concretos. Un delegado edita dentro de su ámbito, pero no puede delegar ni tocar valores globales.';
export const COLUMNA_A_QUIEN = 'A quién';
export const COLUMNA_SOBRE_QUE = 'Sobre qué';
export const COLUMNA_VIGENCIA = 'Vigencia';
export const COLUMNA_OTORGADA_POR = 'Otorgada por';
export const INCLUYE_SUBGRUPOS = 'Incluye subgrupos';
export const VENCE_MANANA = 'Vence mañana';
export const PRORROGAR = 'Prorrogar';
export const REVOCAR = 'Revocar';
export const REVOCAR_TIENE_EFECTO_INMEDIATO = 'Revocar tiene efecto inmediato, también para quien tenga la sesión abierta. Otorgar y revocar quedan en la traza.';
export const LIMITE_DE_LA_ORGANIZACION =
  'Los cambios de membresía en la organización de Bonita no dejan fila en la traza de esta aplicación: se hacen en la organización.';
export const SIN_DELEGACIONES_TITULO = 'No hay delegaciones vigentes.';
export const SIN_DELEGACIONES_CUERPO = 'Cuando delegues la administración de un proceso a alguien, aparecerá aquí.';
export const SIN_VENCIDAS_TITULO = 'Ninguna delegación ha vencido ni se ha revocado.';
export const revocarTitulo = (quien: string) => `¿Revocar el permiso de ${quien}?`;
export const REVOCAR_CUERPO = 'Dejará de poder editar desde su siguiente petición, aunque tenga la sesión abierta. Lo que ya cambió se queda como está.';
export const REVOCAR_ACCION = 'Revocar permiso';
export const prorrogarTitulo = (quien: string) => `Prorrogar el permiso de ${quien}`;
export const PRORROGAR_CUERPO = 'La prórroga es una ampliación: queda como propuesta para otra persona superadministradora y la delegación mantiene su fecha hasta que se apruebe.';
export const PRORROGAR_ACCION = 'Enviar la prórroga';
export const NUEVA_FECHA = 'Nueva fecha de fin';
export const PRORROGA_ENVIADA = 'La prórroga quedó como propuesta: otra persona superadministradora tiene que aprobarla.';
export const REVOCADA = 'Permiso revocado.';
export const DELEGACION_ENVIADA = 'La delegación quedó como propuesta: otra persona superadministradora tiene que aprobarla en Aprobaciones.';
export const NUEVA_DELEGACION = 'Nueva delegación';
export const NUEVA_DELEGACION_SUBTITULO = 'Da a otras personas la administración de un proceso o de algunas de sus actividades.';
export const VOLVER_A_PERMISOS = 'Permisos';
export const LEYENDA_A_QUIEN = 'A quién';
export const LEYENDA_SOBRE_QUE = 'Sobre qué';
export const LEYENDA_CUANTO_TIEMPO = 'Durante cuánto tiempo';
export const TIPO_DESTINATARIO = 'Tipo de destinatario';
export const DESTINATARIOS = { USUARIO: 'Una persona', GRUPO: 'Un grupo', ROL: 'Un rol', GRUPO_ROL: 'Un rol dentro de un grupo' } as const;
export const CAMPO_PERSONA = 'Persona';
export const CAMPO_GRUPO = 'Grupo';
export const CAMPO_ROL = 'Rol';
export const INCLUIR_SUBGRUPOS = 'Incluir los subgrupos del grupo elegido';
export const CAMPO_PROCESO = 'Proceso';
export const ALCANCE = 'Alcance';
export const ALCANCE_TODO = 'Todo el proceso';
export const ALCANCE_ALGUNAS = 'Solo algunas actividades';
export const ACTIVIDADES_AYUDA = 'Las actividades salen del proceso desplegado: si se añade una, aparecerá aquí.';
export const VIGENCIA = 'Vigencia';
export const VIGENCIA_SIN_FIN = 'Sin fecha de fin';
export const VIGENCIA_HASTA = 'Hasta una fecha';
export const CAMPO_HASTA = 'Hasta';
export const QUE_PODRAN_HACER = 'Qué podrán hacer';
export const QUE_PODRAN_HACER_1 = 'Editar valores de las listas y parámetros del proceso o de las actividades elegidas.';
export const QUE_PODRAN_HACER_2 = 'Proponer cambios de impacto alto y aprobar los de otras personas.';
export const QUE_NO_PODRAN_HACER = 'Qué no podrán hacer';
export const QUE_NO_PODRAN_HACER_1 = 'Delegar a otros, tocar valores globales ni crear definiciones nuevas.';
export const QUE_NO_PODRAN_HACER_2 = 'Aprobar sus propios cambios.';
export const DELEGACION_LIMITE_UNA_SUPERADMIN =
  'Una delegación nueva la aprueba otra persona superadministradora: si solo hay una, no se podrá aprobar.';
export const ERROR_ELIGE_PERSONA = 'Elige a quién delegas.';
export const ERROR_ELIGE_GRUPO = 'Elige un grupo.';
export const ERROR_ELIGE_ROL = 'Elige un rol.';
export const ERROR_ELIGE_ACTIVIDAD = 'Elige al menos una actividad.';
export const ERROR_ELIGE_FECHA = 'Elige la fecha de fin.';
export const ERROR_ELIGE_PROCESO = 'Elige un proceso.';
export const ENTRADA_VACIA_ORGANIZACION = 'Escribe para buscar.';

// ─── Importar ─────────────────────────────────────────────────────────────────

export const IMPORTAR_TITULO = 'Importar desde CSV';
export const IMPORTAR_SUBTITULO = 'Revisa lo que va a cambiar antes de aplicarlo. Nada se toca hasta que confirmes.';
export const PASOS = ['1 · Subir el fichero', '2 · Revisar los cambios', '3 · Confirmar'] as const;
export const PASOS_ROTULO = 'Pasos';
export const ELEGIR_FICHERO = 'Elige un fichero CSV';
export const FICHERO_AYUDA = 'Columnas: definicion, proceso, actividad, codigoPadre, codigo, etiqueta, ayuda, orden, valor, activo.';
export const CAMBIAR_FICHERO = 'Cambiar fichero';
export const FICHERO_ILEGIBLE = 'No pudimos leer el fichero. Comprueba que sea un CSV de texto.';
export const CSV_RECHAZADO = 'El fichero no se pudo leer entero. Revísalo y vuelve a subirlo: no se aplicó nada.';
export const CLASES_DE_IMPORTACION = {
  ALTA: ['Alta', 'exito', 'Opciones nuevas que se añaden.'],
  CAMBIO: ['Cambio', 'marca', 'Opciones existentes con otro nombre u orden.'],
  BAJA: ['Baja', 'atencion', 'Se desactiva, no se borra: los expedientes que la usan la conservan.'],
  SIN_CAMBIOS: ['Sin cambios', 'neutro', 'Coinciden con lo que ya hay.'],
  PROPUESTA: ['Por aprobar', 'marca', 'Son de impacto alto: quedan como propuesta para otra persona.'],
  ERROR: ['Error', 'error', 'Filas que no se pueden importar.'],
} as const;
export const plural_altas = (n: Recuento) => (n === 1 ? '1 alta' : `${recuento(n)} altas`);
export const plural_cambios = (n: Recuento) => (n === 1 ? '1 cambio' : `${recuento(n)} cambios`);
export const plural_bajas = (n: Recuento) => (n === 1 ? '1 baja' : `${recuento(n)} bajas`);
export const plural_sin = (n: Recuento) => (n === 1 ? '1 sin cambios' : `${recuento(n)} sin cambios`);
export const plural_propuestas = (n: Recuento) => (n === 1 ? '1 por aprobar' : `${recuento(n)} por aprobar`);
export const erroresTitulo = (n: Recuento) => (n === 1 ? '1 fila tiene un error y no se importará' : `${recuento(n)} filas tienen un error y no se importarán`);
export const ERRORES_CUERPO = 'Corrige el fichero y vuelve a subirlo: un fichero con errores no se confirma.';
export const COLUMNA_QUE_PASA = 'Qué pasa';
export const COLUMNA_LISTA = 'Lista o parámetro';
export const COLUMNA_DETALLE = 'Detalle';
export const MOTIVO_DE_LA_IMPORTACION = 'Motivo de la importación';
export const MOTIVO_IMPORTACION_AYUDA = 'Todo el lote queda en la traza con un mismo identificador.';
export const importarN = (n: Recuento) => (n === 1 ? 'Importar 1 cambio' : `Importar ${recuento(n)} cambios`);
export const NADA_QUE_IMPORTAR = 'No hay ningún cambio que aplicar en este fichero.';
export const importacionAplicada = (lote: string) => `Importación ${lote} aplicada.`;
export const IMPORTACION_PROPUESTAS = 'Las filas de impacto alto quedaron como propuesta en Aprobaciones.';
export const IMPORTACION_CAMBIO_TITULO = 'Lo que se iba a importar cambió desde la vista previa';
export const IMPORTACION_CAMBIO_CUERPO = 'Revisa la vista previa nueva y confirma otra vez: no se aplicó nada.';

// ─── Traza ──────────────────────────────────────────────────────────────────────

export const FILTRAR_LA_TRAZA = 'Filtrar la traza';
export const FILTRO_PERSONA = 'Persona';
export const FILTRO_QUE = 'Lista o parámetro';
export const FILTRO_ACCION = 'Acción';
export const FILTRO_DESDE = 'Desde';
export const FILTRO_HASTA = 'Hasta';
export const TODAS = 'Todas';
export const CUALQUIERA = 'Cualquiera';
export const ACCIONES_DE_TRAZA = { todas: 'Todas', cambios: 'Cambios de valor', aprobaciones: 'Aprobaciones', permisos: 'Permisos', importaciones: 'Importaciones' } as const;
export const entradasTitulo = (n: Recuento) => (n === 1 ? '1 entrada' : `${recuento(n)} entradas`);
export const TRAZA_COLUMNAS = { cuando: 'Cuándo', quien: 'Quién', que: 'Qué', cambio: 'Cambio', motivo: 'Motivo' } as const;
export const TRAZA_VACIA_TITULO = 'Ninguna entrada coincide con esos filtros.';
export const TRAZA_VACIA_CUERPO = 'Prueba con menos filtros.';
export const TRAZA_AYUDA =
  'Cada entrada guarda el valor anterior y el nuevo completos, la hora del servidor y los roles que tenía la persona en ese momento. La aplicación no permite editarla ni borrarla.';
export const VERIFICAR_LA_CADENA = 'Verificar la cadena';
export const CADENA_COHERENTE_TITULO = '✓ Cadena coherente';
export const CADENA_COHERENTE_CUERPO = 'Se comprobó toda la cadena y cada entrada coincide con su huella.';
export const LO_QUE_DETECTA = 'La verificación detecta una edición o un borrado en medio de la cadena; no detecta una reescritura completa ni el recorte de las últimas entradas hechos directamente en la base de datos.';
export const CADENA_ROTA_TITULO = 'La cadena no es coherente';
export const cadenaRotaCuerpo = (cuando: string, que: string) => `Deja de casar desde la entrada del ${cuando}${que ? ` (${que})` : ''}. Una entrada interior no es la original.`;
export const VERIFICANDO = 'Verificando…';
export const NOMBRE_DEL_FICHERO_DE_TRAZA = 'traza.csv';

// Un dato que no se pudo leer no es un cero (B2): estado de error explícito en cada lectura.
export const ERROR_DE_LECTURA_TITULO = 'No pudimos cargar esto.';
export const ERROR_DE_LECTURA_CUERPO = 'No es que no haya nada: la lectura falló. Inténtalo de nuevo.';
export const ERROR_EDITORES = 'No pudimos leer quién puede editar esto.';
export const ERROR_CADENA = 'No pudimos verificar la cadena en este momento.';
export const ERROR_VERIFICAR = 'La verificación no se pudo completar: no sabemos si la cadena es coherente.';
export const CADENA_SIN_ENTRADAS_TITULO = 'No hay entradas que verificar';
export const CADENA_SIN_ENTRADAS_CUERPO = 'La traza todavía no tiene entradas, así que no hay nada que comprobar.';
export const UNA_DEFINICION = 'una definición';
export const CADENA_NO_COHERENTE_CHIP = 'La cadena no es coherente';
export const EL_PARAMETRO_ENTERO = '(el valor del parámetro)';
export const DESACTIVAR_SIN_USOS = 'El módulo todavía no informa dónde se usa esta opción ni qué expedientes la eligieron: confírmalo antes de desactivarla.';
export const DESACTIVAR_USOS_ERROR = 'No pudimos leer dónde se usa esta opción. Cierra este diálogo y vuelve a intentarlo antes de desactivarla.';
export const DESACTIVAR_SE_USA_EN = 'Se usa en:';
export const DESACTIVAR_NINGUN_LUGAR = 'ningún lugar registrado';
export const DESACTIVAR_EXPEDIENTES = (guardados: string, enCurso: string) =>
  `${guardados} ${guardados === '1' ? 'expediente guardado la eligió' : 'expedientes guardados la eligieron'}, ${enCurso} ${enCurso === '1' ? 'sigue' : 'siguen'} en curso.`;
export const conflictoPropio = (cuando: string) =>
  `Ya hay un cambio tuyo sobre esto${cuando ? ` (${cuando})` : ''}: una propuesta pendiente o un cambio reciente. Actualiza la vista y revisa qué quedó guardado antes de volver a intentarlo.`;
export const GUARDADO_SIN_ACTUALIZAR_TITULO = 'Guardado, pero no pudimos actualizar la vista.';
export const GUARDADO_SIN_ACTUALIZAR_CUERPO = 'Tu cambio sí se aplicó. Lo que ves puede estar desactualizado hasta que vuelvas a leerlo.';
export const ERROR_ORGANIZACION = 'No pudimos leer las personas, grupos y roles.';
export const ERROR_ORGANIZACION_CUERPO = 'Sin ellos no podemos mostrar ni crear permisos. El resto de la aplicación funciona. Recarga la página para volver a intentarlo.';
export const RECHAZADA_LA_DELEGACION = 'Rechazada. La delegación no se aplicó; el rechazo queda en la traza con tu comentario.';
export const FALLO_DESCONOCIDO = 'No sabemos si se guardó: la respuesta no llegó. Actualizamos la vista; revísala antes de volver a intentarlo.';
export const FALLO_VISTA_PREVIA = 'No pudimos revisar el fichero. Inténtalo de nuevo: no se aplicó nada.';
export const IMPORTACION_SIN_RESPUESTA = 'No sabemos si la importación se aplicó: la respuesta no llegó. Actualizamos la vista; revisa las listas antes de volver a importar.';
export const TIPO_DE_USO_OTRO = 'Otro uso';
export const TABLA_IMPORTACION = 'Filas de la importación (desplázate con las flechas)';
export const TABLA_OPCIONES = 'Opciones de la lista (desplázate con las flechas)';
export const TABLA_DELEGACIONES = 'Delegaciones (desplázate con las flechas)';
export const TABLA_USOS = 'Expedientes que la usan (desplázate con las flechas)';
export const VALOR_POSIBLEMENTE_VIEJO_TITULO = 'No pudimos leer el valor actual.';
export const VALOR_POSIBLEMENTE_VIEJO_CUERPO = 'Lo que ves es lo último que leímos y puede estar desactualizado: otra persona pudo haberlo cambiado. Reintenta antes de decidir.';
export const BUSCANDO = 'Buscando…';
export const BUSQUEDA_FALLIDA = 'No pudimos buscar. Escribe otra vez o inténtalo de nuevo.';
export const NINGUNA_COINCIDE = 'Ninguna opción coincide.';
export const TODAS_LAS_PERSONAS = 'Todas las personas';
export const entradasCargadas = (n: Recuento) => (n === 1 ? '1 entrada cargada · hay más antiguas' : `${recuento(n)} entradas cargadas · hay más antiguas`);
export const TRAZA_SIGUE_BUSCANDO = 'Ninguna de las entradas cargadas coincide todavía, y quedan más antiguas por leer.';
export const VER_ENTRADAS_MAS_ANTIGUAS = 'Ver entradas más antiguas';
export const exportoParcial = (n: Recuento) => `El CSV lleva las ${recuento(n)} entradas más recientes que coinciden. Hay más antiguas: acota por fechas o por persona para exportarlas.`;
export const HISTORIAL_SIGUE_BUSCANDO = 'No encontramos cambios en lo leído todavía, y quedan entradas más antiguas por revisar.';
export const VER_CAMBIOS_MAS_ANTIGUOS = 'Ver cambios más antiguos';
export const HISTORIAL_TOPE = 'No encontramos cambios de esto entre las 1.000 entradas más recientes de la traza. Puede haber más antiguos: la traza completa está en la sección Traza.';
export const TRAZA_TOPE = 'No encontramos entradas que coincidan entre las 1.000 más recientes. Puede haberlas más antiguas: acota por fechas o por persona para llegar a ellas.';
export const SIN_ELEGIR = 'Sin elegir';
export const OTROS_FUERA_DE_LISTA = 'Otros códigos fuera de la lista (agrupados)';
export const CHIP_FUERA_DE_LISTA = 'Fuera de la lista';
export const DONDE_SE_USA_LO_QUE_DECIDES = 'Dónde se usa';
export const USOS_DE_LA_APROBACION_ERROR = 'No pudimos leer dónde se usa. Decide con cuidado: no sabemos qué toca este cambio.';
export const USOS_NINGUN_LUGAR = 'Ningún proceso lo ha usado todavía.';
export const EXPEDIENTES_EN_CURSO_POR_OPCION = 'Expedientes en curso por opción:';
export const EXPEDIENTES_AFECTADOS_NO_INFORMADOS = 'Cuántos expedientes en curso cambian de camino con este valor: el módulo todavía no lo informa para un parámetro.';
export const BAJA_LA_USAN = (guardados: string, enCurso: string) =>
  `La ${guardados === '1' ? 'usa' : 'usan'} ${guardados} ${guardados === '1' ? 'expediente guardado' : 'expedientes guardados'} y ${enCurso} en curso.`;
export const BAJA_USOS_NO_LEIDOS = 'No pudimos leer qué expedientes la usan.';
export const BAJA_SIN_CONTEO = 'El módulo no cuenta los expedientes de esta lista: no sabemos cuántos la usan.';
