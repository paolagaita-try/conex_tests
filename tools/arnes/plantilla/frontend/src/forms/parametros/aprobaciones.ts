/**
 * El modelo de Aprobaciones (pantallas `p06-aprobaciones*`): lo que espera tu
 * aprobación, lo que propusiste tú y lo resuelto recientemente, cada propuesta con su antes → después, su
 * motivo y quién y cuándo. Lógica pura sobre datos CRUDOS; devuelve textos y sí/no.
 *
 * El doble control es de DATOS, no de pantalla: `puedesAprobar` y `esPropia` los calcula el servidor para
 * quien llama (quien propone no aprueba, tampoco la superadministración). Aquí solo se leen.
 */
import { cuando, cuandoCompleto, fechaLegible, valorLegible } from './formatos';
import { nombreDeActividad, nombreDeProceso, nombresUnicos } from './nombres';
import * as T from './textos';
import { TODO, type Definicion, type EstadoPropuesta, type Propuesta } from './tipos';

/** A quién se puede delegar, tal como lo devuelve la búsqueda de la organización (identificador y nombre). */
export interface SujetosPorId {
  usuario: Array<{ id: number; nombre: string }>;
  grupo: Array<{ id: number; nombre: string }>;
  rol: Array<{ id: number; nombre: string }>;
}

export interface PropuestaVM {
  /** Identidad estable de la propuesta para la selección: definición, ámbito y cuándo se propuso. */
  clave: string;
  /** El código de la definición (para pedir sus usos); vacío en una delegación. */
  definicion: string;
  nombre: string;
  /** «Becas de estudio · todo el proceso». */
  ambito: string;
  impactoAlto: boolean;
  esDelegacion: boolean;
  /** Lo que había y lo que se propone, ya escrito con su unidad. */
  antes: string;
  despues: string;
  /** «Cambio de valor», «Desactivar una opción», «Delegar permisos»… */
  accion: string;
  quien: string;
  /** «hoy 10:31». */
  cuando: string;
  /** «29 sep 2026 · 10:31». */
  cuandoCompleto: string;
  motivo: string;
  esPropia: boolean;
  puedeAprobar: boolean;
  estado: EstadoPropuesta;
  /** Quién resolvió y su comentario, si ya está resuelta. */
  resueltaPor: string;
  comentario: string;
  /** Las líneas de una delegación (a quién, sobre qué, hasta cuándo). */
  detalle: string[];
}

export interface Aprobaciones {
  esperan: PropuestaVM[];
  propias: PropuestaVM[];
  resueltas: PropuestaVM[];
}

type Obj = Record<string, unknown>;
const texto = (v: unknown): string => (typeof v === 'string' ? v : '');

const TIPOS_DE_SUJETO = { USUARIO: 'Una persona', GRUPO: 'Un grupo', ROL: 'Un rol', GRUPO_ROL: 'Un rol dentro de un grupo' } as const;

export function sujetoDeDelegacion(datos: Obj, sujetos: SujetosPorId): string {
  const id = (v: unknown): number | null => (typeof v === 'number' ? v : null);
  const nombre = (m: Array<{ id: number; nombre: string }>, v: unknown, generico: string): string => {
    const i = id(v);
    return (i !== null ? m.find((x) => x.id === i)?.nombre : undefined) ?? generico;
  };
  const tipo = texto(datos.tipoSujeto);
  const subgrupos = datos.incluyeSubgrupos === true ? ` ${T.CON_SUBGRUPOS}` : '';
  if (tipo === 'USUARIO') return nombre(sujetos.usuario, datos.sujetoUsuarioId, T.UNA_PERSONA);
  if (tipo === 'GRUPO') return nombre(sujetos.grupo, datos.sujetoGrupoId, T.UN_GRUPO) + subgrupos;
  if (tipo === 'ROL') return nombre(sujetos.rol, datos.sujetoRolId, T.UN_ROL);
  // Con nombres genéricos dentro de la frase van en minúscula: «un rol en un grupo».
  return `${nombre(sujetos.rol, datos.sujetoRolId, T.UN_ROL.toLowerCase())} en ${nombre(sujetos.grupo, datos.sujetoGrupoId, T.UN_GRUPO.toLowerCase())}${subgrupos}`;
}

/** Lo que dice una propuesta de delegación, línea a línea. */
export function lineasDeDelegacion(p: Propuesta, sujetos: SujetosPorId): string[] {
  const d = p.valorPropuesto.datos as Obj;
  const actividades = Array.isArray(d.actividades) ? d.actividades.filter((a): a is string => typeof a === 'string') : [];
  const hasta = texto(d.vigenteHasta);
  const tipo = TIPOS_DE_SUJETO[texto(d.tipoSujeto) as keyof typeof TIPOS_DE_SUJETO] ?? T.UNA_PERSONA;
  const quien = sujetoDeDelegacion(d, sujetos);
  return [
    // Sin nombres a mano (quien no es superadministración) el sujeto ES el tipo: no se dice dos veces.
    quien === tipo ? tipo : `${tipo}: ${quien}`,
    `${nombreDeProceso(p.proceso)} · ${actividades.length === 0 ? T.TODO_EL_PROCESO : actividades.map(nombreDeActividad).join(', ')}`,
    hasta ? T.hastaEl(fechaLegible(hasta.slice(0, 10))) : T.SIN_FECHA_DE_FIN,
  ];
}

const ACCIONES: Record<string, string> = {
  EDITAR: 'Cambio de valor',
  CREAR: 'Valor nuevo',
  DESACTIVAR: 'Desactivar una opción',
  REACTIVAR: 'Reactivar una opción',
  ORDENAR: 'Cambio de orden',
  CREAR_VERSION_PROPIA: 'Versión propia',
  VOLVER_A_HEREDAR: 'Volver a heredar',
  EDITAR_DEFINICION: 'Cambio de la definición',
  DELEGAR: 'Delegar permisos',
  REVOCAR: 'Revocar permisos',
};

function antesYDespues(p: Propuesta, def: Definicion | undefined): { antes: string; despues: string } {
  const anterior = p.valorAnterior[0] as Obj | undefined;
  const datos = p.valorPropuesto.datos as Obj;
  const valor = (v: unknown): string => (def ? valorLegible(def, typeof v === 'string' ? v : null) : texto(v));
  switch (p.valorPropuesto.accion) {
    case 'EDITAR':
      if ('valor' in datos) return { antes: valor(anterior?.valor), despues: valor(datos.valor) };
      if ('etiqueta' in datos) return { antes: texto(anterior?.etiqueta), despues: texto(datos.etiqueta) };
      return { antes: '—', despues: T.CAMBIO_DE_TEXTO };
    case 'CREAR':
      return { antes: '—', despues: 'valor' in datos ? valor(datos.valor) : texto(datos.etiqueta) };
    case 'DESACTIVAR':
      return { antes: T.CHIP_ACTIVA, despues: T.CHIP_INACTIVA };
    case 'REACTIVAR':
      return { antes: T.CHIP_INACTIVA, despues: T.CHIP_ACTIVA };
    default:
      return { antes: '—', despues: ACCIONES[p.valorPropuesto.accion] ?? p.valorPropuesto.accion };
  }
}

export function propuestaVM(p: Propuesta, definiciones: Definicion[], nombres: Record<string, string>, sujetos: SujetosPorId, ahora: Date): PropuestaVM {
  const delegacion = p.valorPropuesto.accion === 'DELEGAR' || p.valorPropuesto.accion === 'REVOCAR';
  const def = definiciones.find((d) => d.codigo === p.definicion);
  const { antes, despues } = delegacion ? { antes: '—', despues: ACCIONES[p.valorPropuesto.accion] ?? '' } : antesYDespues(p, def);
  const ambito =
    p.proceso === TODO ? T.GLOBAL : p.actividad === TODO ? [nombreDeProceso(p.proceso), T.TODO_EL_PROCESO.toLowerCase()].join(' · ') : [nombreDeProceso(p.proceso), nombreDeActividad(p.actividad)].join(' · ');
  return {
    clave: [p.definicion, p.proceso, p.actividad, p.codigoPadre, p.codigo, p.creadaEn].join('|'),
    definicion: delegacion ? '' : p.definicion,
    nombre: delegacion ? T.hist.permisos : (def?.nombre ?? p.definicion),
    ambito,
    impactoAlto: def?.impacto === 'ALTO' || delegacion,
    esDelegacion: delegacion,
    antes,
    despues,
    accion: ACCIONES[p.valorPropuesto.accion] ?? p.valorPropuesto.accion,
    quien: nombres[p.proponente] ?? p.proponente,
    cuando: cuando(p.creadaEn, ahora),
    cuandoCompleto: cuandoCompleto(p.creadaEn),
    motivo: p.motivo,
    esPropia: p.esPropia,
    puedeAprobar: p.puedesAprobar,
    estado: p.estado,
    resueltaPor: p.aprobador ? (nombres[p.aprobador] ?? p.aprobador) : '',
    comentario: p.comentario ?? '',
    detalle: delegacion ? lineasDeDelegacion(p, sujetos) : [],
  };
}

export function construirAprobaciones(
  todas: Propuesta[],
  definiciones: Definicion[],
  nombres: Record<string, string>,
  sujetos: SujetosPorId,
  ahora: Date = new Date(),
): Aprobaciones {
  const distintos = nombresUnicos(nombres);
  const vm = (p: Propuesta) => propuestaVM(p, definiciones, distintos, sujetos, ahora);
  const pendientes = todas.filter((p) => p.estado === 'PENDIENTE');
  const recientes = (a: Propuesta, b: Propuesta) => (b.resueltaEn ?? b.creadaEn).localeCompare(a.resueltaEn ?? a.creadaEn);
  return {
    esperan: pendientes.filter((p) => p.puedesAprobar).map(vm),
    propias: pendientes.filter((p) => p.esPropia).map(vm),
    resueltas: todas
      .filter((p) => p.estado !== 'PENDIENTE')
      .sort(recientes)
      .slice(0, LIMITE_DE_RESUELTAS)
      .map(vm),
  };
}

const LIMITE_DE_RESUELTAS = 10;

/** La línea de meta de una fila de la lista: «35 % → 30 % · Marta Rivas, hoy 10:32». */
export function metaDe(p: PropuestaVM): string {
  if (p.estado === 'PENDIENTE') return `${p.antes} → ${p.despues} · ${p.esPropia ? p.cuando : `${p.quien}, ${p.cuando}`}`;
  const verbo = p.estado === 'APROBADA' ? 'Aprobado' : p.estado === 'RECHAZADA' ? 'Rechazado' : 'Retirado';
  return `${verbo}${p.resueltaPor ? ` por ${p.resueltaPor}` : ''} · ${p.cuando}`;
}
