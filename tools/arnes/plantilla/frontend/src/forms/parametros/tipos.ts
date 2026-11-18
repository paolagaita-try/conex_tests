/**
 * Las formas que la API `parametros` del kit devuelve y recibe, tal cual las
 * emiten `parametros-core` y la extensión. Aquí no hay lógica: solo el contrato que `api.ts` valida y
 * el resto de la aplicación consume. Todo lo que parece una cifra viaja como TEXTO canónico
 * (`"35"`, `"1500000.00"`): la auditoría del origen de las cifras no admite que una pantalla
 * pinte un número calculado, y un valor de parámetro no es un número sino el dato que el negocio fijó.
 */

/** El comodín de ámbito del kit: «todo» (T-c). Nunca la cadena vacía. */
export const TODO = '*';

export type Clase = 'LISTA' | 'PARAMETRO';
export type TipoDato = 'TEXTO' | 'ENTERO' | 'DECIMAL' | 'PORCENTAJE' | 'MONTO' | 'FECHA' | 'BOOLEANO';
export type Impacto = 'NORMAL' | 'ALTO';

export interface Definicion {
  codigo: string;
  nombre: string;
  descripcion: string | null;
  clase: Clase;
  tipoDato: TipoDato;
  unidad: string | null;
  minimo: string | null;
  maximo: string | null;
  decimales: number | null;
  dependeDe: string;
  impacto: Impacto;
  fallback: string | null;
  origen: string;
  visibilidad: string;
  activo: boolean;
  persistenceVersion: number;
}

/** Una fila de `KpValorParametro` tal como la lee la administración (sin `persistenceId`). */
export interface Fila {
  definicion: string;
  proceso: string;
  actividad: string;
  codigoPadre: string;
  codigo: string;
  etiqueta: string | null;
  ayuda: string | null;
  orden: number | null;
  valor: string | null;
  activo: boolean;
  copiadoDe: string;
  /** Texto JSON con los códigos activos del origen en el momento de copiar (T-k). */
  codigosOrigen: string | null;
  persistenceVersion: number;
}

export interface ValoresAdministracion {
  definicion: Definicion;
  filas: Fila[];
}

export interface Proceso {
  proceso: string;
  actividades: string[];
}

export type EstadoPropuesta = 'PENDIENTE' | 'APROBADA' | 'RECHAZADA' | 'RETIRADA';

/** La operación que se propuso, tal cual (`valorPropuesto` de la propuesta). */
export interface OperacionPropuesta {
  accion: string;
  definicion: string;
  proceso: string;
  actividad: string;
  codigoPadre: string;
  codigo: string;
  datos: Record<string, unknown>;
}

export interface Propuesta {
  id: number;
  definicion: string;
  proceso: string;
  actividad: string;
  codigoPadre: string;
  codigo: string;
  accion: string;
  valorAnterior: Array<Record<string, unknown>>;
  valorPropuesto: OperacionPropuesta;
  proponente: string;
  motivo: string;
  estado: EstadoPropuesta;
  aprobador: string | null;
  comentario: string | null;
  creadaEn: string;
  resueltaEn: string | null;
  persistenceVersion: number;
  esPropia: boolean;
  puedesAprobar: boolean;
}

export interface ListaDePropuestas {
  /** Cuántas esperan a quien llama (el contador de la pestaña Aprobaciones). */
  paraAprobar: number;
  propias: number;
  total: number;
  propuestas: Propuesta[];
}

export type TipoDeSujeto = 'USUARIO' | 'GRUPO' | 'ROL' | 'GRUPO_ROL';

export interface Delegacion {
  persistenceVersion: number;
  tipoSujeto: TipoDeSujeto;
  sujetoUsuarioId: number | null;
  sujetoGrupoId: number | null;
  sujetoRolId: number | null;
  sujetoRuta: string | null;
  incluyeSubgrupos: boolean;
  proceso: string;
  actividades: string[];
  vigenteDesde: string | null;
  vigenteHasta: string | null;
  activo: boolean;
  otorgadoPor: string;
  motivo: string;
}

/** Quién puede editar una definición (`parametros/editores`): nombres vivos, sin identificadores. */
export interface Editor {
  tipo: 'SUPERADMINISTRACION' | TipoDeSujeto;
  sujeto?: string;
  incluyeSubgrupos?: boolean;
  proceso?: string;
  actividades?: string[];
  vigenteHasta?: string | null;
}

export interface ResultadoDeBusqueda {
  id: number;
  nombre: string;
}

/** Un eslabón de la cadena de la traza. */
export interface EntradaDeTraza {
  id: number;
  fechaHora: string;
  usuario: string;
  rolesVigentes: unknown;
  accion: string;
  claveNegocio: string;
  valorAnterior: unknown;
  valorNuevo: unknown;
  motivo: string;
  origen: string;
  lote: string | null;
  hashAnterior: string;
  hash: string;
}

export interface PaginaDeTraza {
  elementos: EntradaDeTraza[];
  /** La página vino llena: puede haber más antiguas. */
  hayMas: boolean;
}

export type VerificacionDeCadena =
  | { coherente: true; entradas: number; desde: number | null; hasta: number | null }
  | { coherente: false; primeraQueNoCasa: { id: number; fechaHora: string; claveNegocio: string } };

export type ClaseDeFilaImportada = 'ALTA' | 'CAMBIO' | 'BAJA' | 'SIN_CAMBIOS' | 'PROPUESTA' | 'ERROR';

export interface FilaImportada {
  fila: number;
  clase: ClaseDeFilaImportada;
  definicion: string;
  proceso: string;
  actividad: string;
  codigoPadre: string;
  codigo: string;
  detalle: string;
}

export interface ResumenDeImportacion {
  altas: number;
  cambios: number;
  bajas: number;
  sinCambios: number;
  propuestas: number;
  errores: number;
}

export interface VistaPreviaDeImportacion {
  resumen: ResumenDeImportacion;
  filas: FilaImportada[];
  huella: string;
}

export interface ImportacionAplicada {
  lote: string;
  resumen: ResumenDeImportacion;
  filas: FilaImportada[];
}

/** Lo que el servidor dice cuando rechaza algo: el motivo y, si procede, el campo y el detalle. */
export type MotivoDeRechazo = 'SIN_PERMISO' | 'CONFLICTO' | 'VALIDACION' | 'NO_EXISTE';

export interface Aviso {
  tipo?: string;
  [clave: string]: unknown;
}

/** Cada acción de `POST parametros/cambios`. */
export type AccionDeCambio =
  | 'CREAR'
  | 'EDITAR'
  | 'DESACTIVAR'
  | 'REACTIVAR'
  | 'ORDENAR'
  | 'CREAR_VERSION_PROPIA'
  | 'VOLVER_A_HEREDAR'
  | 'EDITAR_DEFINICION'
  | 'CREAR_DEFINICION';

export interface PeticionDeCambio {
  accion: AccionDeCambio;
  definicion: string;
  ambito: { proceso: string; actividad: string };
  codigoPadre?: string;
  codigo?: string;
  datos?: Record<string, unknown>;
  persistenceVersion?: number;
  motivo: string;
}
