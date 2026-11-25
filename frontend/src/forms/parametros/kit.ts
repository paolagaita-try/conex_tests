/**
 * La única puerta de la aplicación hacia el kit de parámetros.
 *
 * - Habla **solo** con `extension/parametros/*` (más la sesión y las membresías de la organización,
 *   que sirven para pintar y nunca para autorizar). No lee `/API/bdm` —a propósito— ni nombres
 *   de tarea del motor.
 * - **Valida la forma** de lo que llega: lo que no cuadra es un `FalloDelKit` de clase `FORMA`, no
 *   un `undefined` que se pinta tres pantallas después.
 * - Traduce los rechazos del servidor a una clase cerrada (`SIN_PERMISO`, `CONFLICTO`, `VALIDACION`,
 *   `NO_EXISTE`, `SIN_RESPUESTA`, `SERVIDOR`): la pantalla decide la frase, el detalle técnico no llega.
 * - Cada llamada escribe su recurso como LITERAL y su método en la propia llamada: es lo que permite a
 *   `check_permisos_llamados` cruzar lo llamado con lo declarado en el manifiesto (un `peticion(recurso)`
 *   con el recurso en una variable es un recurso sin custodia).
 * - Las páginas de la traza se piden por TEXTO (`PAGINAS`): la auditoría del origen de las cifras
 * no admite que esta carpeta convierta un número en texto.
 *
 * `Kit` es una interfaz para que la galería viva pinte las mismas vistas con datos de ejemplo.
 */
import type { Sesion } from '$lib/bonita/bandeja';
import type {
  Definicion,
  Delegacion,
  Editor,
  ImportacionAplicada,
  ListaDePropuestas,
  MotivoDeRechazo,
  PaginaDeTraza,
  PeticionDeCambio,
  Propuesta,
  Proceso,
  ResultadoDeBusqueda,
  ValoresAdministracion,
  VerificacionDeCadena,
  VistaPreviaDeImportacion,
} from './tipos';

export type ClaseDeFallo = MotivoDeRechazo | 'SIN_RESPUESTA' | 'SERVIDOR' | 'FORMA';

/** Un fallo del kit ya clasificado. El `detalle` es del servidor y se usa para el campo, no se pinta tal cual. */
export class FalloDelKit extends Error {
  constructor(
    readonly clase: ClaseDeFallo,
    readonly campo: string | null = null,
    readonly detalle: string | null = null,
    readonly guardadoPor: string | null = null,
    readonly guardadoEn: string | null = null,
    /** En un CONFLICTO de importación, la vista nueva. */
    readonly vistaNueva: VistaPreviaDeImportacion | null = null,
  ) {
    super(`kit de parámetros: ${clase}`);
    this.name = 'FalloDelKit';
  }
}


export interface FiltrosDeTraza {
  usuario?: string;
  claveNegocio?: string;
  /** ISO-8601 con zona. */
  desde?: string;
  hasta?: string;
}

/** Lo que el resultado de escribir dice: aplicado, o dejado como propuesta de impacto alto. */
export type ResultadoDeEscritura =
  | { aplicado: true; filas: Array<{ codigo: string; persistenceVersion: number }> }
  | { aplicado: false; propuesta: { id: number; estado: string } };

/** Los usos registrados de una definición (contrato pedido al kit). */
export interface Usos {
  /** `tipo` es lo que el kit sirvió: uno que la app no conoce se pinta como «Otro uso». */
  lugares: Array<{ tipo: string; titulo: string; detalle: string }>;
  /**
   * Por opción: expedientes guardados y en curso, como texto decimal. `codigo` es SIEMPRE el real y completo (único;
   * hasta 255 caracteres): es la clave de la fila, no el texto que se pinta. Las filas FUERA de la lista de la definición llevan
   * `fueraDeLista` y una `etiqueta` para pintar (≤ 64 con «…», y `truncado`); la de los expedientes que aún no eligieron lleva
   * `sinElegir` (solo modalidad y nivel académico) y código vacío.
   */
  expedientes: Array<{ codigo: string; guardados: string; enCurso: string; etiqueta?: string; truncado?: boolean; fueraDeLista?: boolean; sinElegir?: boolean }>;
  /** El resto de códigos fuera de la lista (el kit sirve 50): NO es una fila de `expedientes`. `agrupados` es un número de códigos. */
  otros?: { guardados: string; enCurso: string };
}

export interface Kit {
  sesion(): Promise<Sesion>;
  /** Las membresías de la persona en la organización: para saber qué pintar, no para autorizar. */
  membresias(idUsuario: string): Promise<Membresia[]>;
  /** El nombre para mostrar de una persona por su nombre de inicio de sesión. */
  nombreDe(usuario: string): Promise<string>;
  procesos(): Promise<Proceso[]>;
  definiciones(): Promise<Definicion[]>;
  valores(definicion: string): Promise<ValoresAdministracion>;
  propuestas(estado?: string, pagina?: number): Promise<ListaDePropuestas>;
  editores(definicion: string): Promise<Editor[]>;
  traza(filtros: FiltrosDeTraza, pagina: number): Promise<PaginaDeTraza>;
  verificar(completa: boolean): Promise<VerificacionDeCadena>;
  delegaciones(): Promise<Delegacion[]>;
  organizacion(tipo: 'usuario' | 'grupo' | 'rol', q: string): Promise<ResultadoDeBusqueda[]>;
  /** Quién es una persona, grupo o rol POR SU ID (la búsqueda del kit solo devuelve 20): `null` si no se pudo saber. */
  nombreDeSujeto(tipo: 'usuario' | 'grupo' | 'rol', id: number): Promise<{ nombre: string; extra: string } | null>;
  cambiar(peticion: PeticionDeCambio): Promise<ResultadoDeEscritura>;
  decidir(propuesta: Propuesta, decision: 'APROBAR' | 'RECHAZAR' | 'RETIRAR', comentario: string): Promise<void>;
  vistaPreviaDeImportacion(csv: string): Promise<VistaPreviaDeImportacion>;
  importar(csv: string, motivo: string, huella: string): Promise<ImportacionAplicada>;
  delegar(datos: DatosDeDelegacion, motivo: string): Promise<ResultadoDeEscritura>;
  revocar(d: Delegacion, motivo: string): Promise<void>;
  /** `GET parametros/usos`. Si falla, lanza: la pantalla dice «no pudimos leer», nunca «nadie la usa». */
  usos(definicion: string): Promise<Usos>;
}

export interface Membresia {
  rol: string;
  grupo: string;
}

export interface DatosDeDelegacion {
  tipoSujeto: 'USUARIO' | 'GRUPO' | 'ROL' | 'GRUPO_ROL';
  sujetoUsuarioId?: number;
  sujetoGrupoId?: number;
  sujetoRolId?: number;
  incluyeSubgrupos: boolean;
  proceso: string;
  actividades: string[];
  vigenteDesde?: string;
  vigenteHasta?: string;
}

