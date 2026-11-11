/**
 * Datos FICTICIOS de la aplicación de parámetros: los de las pantallas aprobadas `p01…p11`.
 * Los usa la galería viva para pintar las mismas vistas reales y los tests para ejercitarlas, así que
 * lo que se aprobó y lo que se mide parten del mismo ejemplo. Ninguna cifra sale de aquí como texto:
 * son los valores canónicos que devolvería el kit.
 */
import { TRAZA_REAL } from './trazaReal.fixture';
import type { Sesion } from '$lib/bonita/bandeja';
import type { FiltrosDeTraza, Kit, Membresia, ResultadoDeEscritura, Usos } from './kit';
import { FalloDelKit } from './kit';
import { ROL_DE_SUPERADMINISTRACION } from './capacidades';
import type {
  Definicion,
  Delegacion,
  Editor,
  EntradaDeTraza,
  Fila,
  PeticionDeCambio,
  Propuesta,
  Proceso,
  ValoresAdministracion,
  VistaPreviaDeImportacion,
} from './tipos';

export const PROCESO = 'Becas de estudio';
export const OTRO_PROCESO = 'Inscripción a cursos';
export const ACT_PAGO = 'F10 Verificar los soportes y preparar el pago (Tesoreria academica)';
export const ACT_COMITE = 'F8 Aprobar beca completa (Comite academico)';
export const ACT_DECANATO = 'F8 Aprobar beca extraordinaria (Decanato)';
export const ACT_COORDINACION = 'F8 Aprobar media beca (Coordinacion academica)';
export const ACT_EVALUACION = 'F8 Revisar una solicitud dudosa (Evaluacion academica)';

export const PROCESOS: Proceso[] = [
  { proceso: PROCESO, actividades: [ACT_EVALUACION, ACT_COORDINACION, ACT_COMITE, ACT_DECANATO, ACT_PAGO] },
  { proceso: OTRO_PROCESO, actividades: [] },
];

const definicion = (d: Partial<Definicion> & Pick<Definicion, 'codigo' | 'nombre' | 'clase' | 'tipoDato'>): Definicion => ({
  descripcion: null,
  unidad: null,
  minimo: null,
  maximo: null,
  decimales: null,
  dependeDe: '*',
  impacto: 'NORMAL',
  fallback: null,
  origen: 'SEMILLA',
  visibilidad: 'INTERNA',
  activo: true,
  persistenceVersion: 1,
  ...d,
});

export const DEFINICIONES: Definicion[] = [
  definicion({ codigo: 'tipos_identificacion', nombre: 'Tipos de identificación', clase: 'LISTA', tipoDato: 'TEXTO', descripcion: 'Documento con el que se identifica la persona becaria.' }),
  definicion({ codigo: 'sedes', nombre: 'Sedes', clase: 'LISTA', tipoDato: 'TEXTO' }),
  definicion({ codigo: 'aulas', nombre: 'Aulas', clase: 'LISTA', tipoDato: 'TEXTO', dependeDe: 'sedes' }),
  definicion({
    codigo: 'porcentaje_beca',
    nombre: 'Porcentaje máximo de beca',
    clase: 'PARAMETRO',
    tipoDato: 'PORCENTAJE',
    unidad: '%',
    minimo: '20',
    maximo: '60',
    decimales: 1,
    impacto: 'ALTO',
    fallback: '30',
    descripcion: 'Parte de la matrícula que cubre la beca como máximo. Por encima, el expediente se declina o escala.',
  }),
  definicion({
    codigo: 'tope_coordinador',
    nombre: 'Tope de aprobación del coordinador',
    clase: 'PARAMETRO',
    tipoDato: 'MONTO',
    unidad: 'US$',
    minimo: '100000',
    maximo: '10000000',
    decimales: 0,
    impacto: 'ALTO',
    fallback: '1000000',
    descripcion: 'Importe máximo de beca que puede aprobar un coordinador. Por encima, el expediente escala al decano.',
  }),
  definicion({
    codigo: 'tope_decano',
    nombre: 'Tope de aprobación del decano',
    clase: 'PARAMETRO',
    tipoDato: 'MONTO',
    unidad: 'US$',
    decimales: 0,
    impacto: 'ALTO',
    fallback: '5000000',
    descripcion: 'Importe máximo de beca que puede aprobar el decano.',
  }),
  definicion({ codigo: 'modalidades', nombre: 'Modalidades', clase: 'LISTA', tipoDato: 'TEXTO' }),
  definicion({
    codigo: 'duraciones_modalidad',
    nombre: 'Duraciones por modalidad',
    clase: 'LISTA',
    tipoDato: 'TEXTO',
    dependeDe: 'modalidades',
    descripcion: 'Las duraciones, en semanas, que se pueden ofrecer para cada modalidad.',
  }),
  definicion({
    codigo: 'tope_beca_modalidad',
    nombre: 'Tope de beca por modalidad',
    clase: 'PARAMETRO',
    tipoDato: 'MONTO',
    unidad: 'US$',
    decimales: 0,
    dependeDe: 'modalidades',
  }),
  definicion({ codigo: 'nivel_academico', nombre: 'Nivel académico', clase: 'LISTA', tipoDato: 'TEXTO' }),
  definicion({ codigo: 'uso_de_la_beca', nombre: 'Uso de la beca', clase: 'LISTA', tipoDato: 'TEXTO' }),
  definicion({
    codigo: 'vias_pago',
    nombre: 'Vías de pago',
    clase: 'LISTA',
    tipoDato: 'TEXTO',
    descripcion: 'Cómo se entrega el dinero de una operación aprobada. La elige Back-office al preparar el pago.',
  }),
];

let versionDeFila = 1;
const fila = (
  def: string,
  proceso: string,
  actividad: string,
  codigo: string,
  etiqueta: string | null,
  extra: Partial<Fila> = {},
): Fila => ({
  definicion: def,
  proceso,
  actividad,
  codigoPadre: '*',
  codigo,
  etiqueta,
  ayuda: null,
  orden: null,
  valor: null,
  activo: true,
  copiadoDe: '*',
  codigosOrigen: null,
  persistenceVersion: versionDeFila++,
  ...extra,
});

const lista = (def: string, proceso: string, actividad: string, items: Array<[string, string, Partial<Fila>?]>): Fila[] =>
  items.map(([codigo, etiqueta, extra], i) => fila(def, proceso, actividad, codigo, etiqueta, { orden: i + 1, ...extra }));

const SEDES: Array<[string, string]> = [
  ['sede-capital', 'Sede Capital'], ['sede-norte', 'Sede Norte'], ['sede-sur', 'Sede Sur'], ['sede-este', 'Sede Este'],
  ['sede-oeste', 'Sede Oeste'], ['sede-centro', 'Sede Centro'], ['sede-costa', 'Sede Costa'], ['sede-montana', 'Sede Montaña'],
];

export const FILAS: Record<string, Fila[]> = {
  tipos_identificacion: lista('tipos_identificacion', '*', '*', [['documento', 'Documento de identidad'], ['pasaporte', 'Pasaporte'], ['nif', 'Número fiscal']]),
  sedes: lista('sedes', '*', '*', SEDES),
  aulas: [
    ...lista('aulas', '*', '*', [['norte-a1', 'Aula Norte 1'], ['norte-a2', 'Aula Norte 2']]).map((f) => ({ ...f, codigoPadre: 'sede-norte' })),
    ...lista('aulas', '*', '*', [['sur-a1', 'Aula Sur 1']]).map((f) => ({ ...f, codigoPadre: 'sede-sur' })),
  ],
  porcentaje_beca: [
    fila('porcentaje_beca', '*', '*', '*', null, { valor: '40' }),
    fila('porcentaje_beca', PROCESO, '*', '*', null, { valor: '35' }),
  ],
  tope_coordinador: [fila('tope_coordinador', PROCESO, '*', '*', null, { valor: '1500000' })],
  tope_decano: [fila('tope_decano', PROCESO, '*', '*', null, { valor: '5000000' })],
  modalidades: lista('modalidades', PROCESO, '*', [['curso', 'Curso en línea'], ['taller', 'Taller presencial']]),
  duraciones_modalidad: [
    ...lista('duraciones_modalidad', PROCESO, '*', [['12', '12 semanas'], ['24', '24 semanas'], ['36', '36 semanas'], ['48', '48 semanas'], ['60', '60 semanas']]).map((f) => ({ ...f, codigoPadre: 'curso' })),
    ...lista('duraciones_modalidad', PROCESO, ACT_COMITE, [['12', '12 semanas'], ['24', '24 semanas'], ['72', '72 semanas']], ).map((f) => ({
      ...f,
      codigoPadre: 'curso',
      copiadoDe: [PROCESO, '*'].join('|'),
      codigosOrigen: JSON.stringify(['curso|12', 'curso|24']),
    })),
  ],
  tope_beca_modalidad: [
    fila('tope_beca_modalidad', PROCESO, '*', '*', null, { codigoPadre: 'curso', valor: '20000' }),
    fila('tope_beca_modalidad', PROCESO, '*', '*', null, { codigoPadre: 'taller', valor: '5000' }),
  ],
  nivel_academico: lista('nivel_academico', PROCESO, '*', [['grado', 'Grado'], ['maestria', 'Maestría'], ['doctorado', 'Doctorado'], ['otro', 'Otro']]),
  uso_de_la_beca: lista('uso_de_la_beca', PROCESO, '*', [['matricula', 'Matrícula'], ['materiales', 'Materiales'], ['transporte', 'Transporte'], ['otro', 'Otro']]),
  vias_pago: lista('vias_pago', PROCESO, ACT_PAGO, [
    ['transferencia', 'Transferencia a la cuenta del becario'],
    ['cheque', 'Cheque de administración'],
    ['efectivo', 'Pago en caja'],
    ['prepago', 'Bono prepago', { activo: false }],
  ]),
};

/** Las filas de un código, con la misma identidad que devolvería el kit. */
export const valoresDeEjemplo = (codigo: string): ValoresAdministracion => {
  const def = DEFINICIONES.find((d) => d.codigo === codigo);
  if (!def) throw new FalloDelKit('NO_EXISTE');
  return { definicion: def, filas: FILAS[codigo] ?? [] };
};

/** «00»…«59» como texto escrito (no calculado): instantes distintos para las propuestas de relleno. */
const DOS_CIFRAS: readonly string[] = '00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59'.split(' ');

const LOGINS_DE_RELLENO: readonly string[] = 'persona.a persona.b persona.c persona.d persona.e persona.f persona.g persona.h persona.i persona.j persona.k persona.l persona.m persona.n persona.o persona.p persona.q persona.r persona.s persona.t'.split(' ');

const propuesta = (id: number, p: Partial<Propuesta>): Propuesta => ({
  id,
  definicion: 'porcentaje_beca',
  proceso: PROCESO,
  actividad: '*',
  codigoPadre: '*',
  codigo: '*',
  accion: 'EDITAR',
  valorAnterior: [{ valor: '35' }],
  valorPropuesto: { accion: 'EDITAR', definicion: 'porcentaje_beca', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: '*', datos: { valor: '30' } },
  proponente: 'marta.rivas',
  motivo: 'Acuerdo CA-2026-14: el consejo académico reduce el porcentaje de beca de los cursos.',
  estado: 'PENDIENTE',
  aprobador: null,
  comentario: null,
  creadaEn: '2026-09-29T14:32:00.000Z',
  resueltaEn: null,
  persistenceVersion: 0,
  esPropia: false,
  puedesAprobar: true,
  ...p,
});

/** Lo pendiente visto por Marta (superadministración): lo suyo y lo de Luis. */
export const PROPUESTAS: Propuesta[] = [
  propuesta(1, { esPropia: true, puedesAprobar: false }),
  propuesta(2, {
    definicion: 'tope_coordinador',
    accion: 'EDITAR',
    valorAnterior: [{ valor: '1500000' }],
    valorPropuesto: { accion: 'EDITAR', definicion: 'tope_coordinador', proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo: '*', datos: { valor: '1650000' } },
    proponente: 'luis.gil',
    motivo: 'Acta del consejo académico 2026-09: actualizar los topes de aprobación por la inflación acumulada.',
    creadaEn: '2026-09-29T14:31:00.000Z',
    esPropia: false,
    puedesAprobar: true,
  }),
];

export const RESUELTAS: Propuesta[] = [
  propuesta(3, { definicion: 'tope_decano', estado: 'APROBADA', aprobador: 'jorge.pena', proponente: 'marta.rivas', resueltaEn: '2026-08-03T15:00:00.000Z', creadaEn: '2026-08-03T14:00:00.000Z', puedesAprobar: false }),
  propuesta(4, { estado: 'RECHAZADA', aprobador: 'jorge.pena', comentario: 'Falta el acta.', resueltaEn: '2026-07-28T15:00:00.000Z', creadaEn: '2026-07-28T14:00:00.000Z', puedesAprobar: false }),
];

export const NOMBRES: Record<string, string> = {
  'marta.rivas': 'Marta Rivas',
  'luis.gil': 'Luis Gil',
  'ana.perez': 'Ana Pérez',
  'jorge.pena': 'Jorge Peña',
  'pedro.almonte': 'Pedro Almonte',
  'olga.negocio': 'Olga Negocio',
  'zeta.ultima': 'Zoe Ultima',
  'carla.ruiz': 'Carla Ruiz',
  'super.parametros': 'Sara Parametros',
  'super.parametros2': 'Sergio Parametros',
};

const traza = (id: number, accion: string, usuario: string, fechaHora: string, clave: string, anterior: unknown, nuevo: unknown, motivo: string): EntradaDeTraza => ({
  id,
  fechaHora,
  usuario,
  rolesVigentes: [],
  accion,
  claveNegocio: clave,
  valorAnterior: anterior,
  valorNuevo: nuevo,
  motivo,
  origen: 'PANTALLA',
  lote: null,
  hashAnterior: ['a', fechaHora].join(''),
  hash: ['b', fechaHora].join(''),
});

export const TRAZA: EntradaDeTraza[] = [
  traza(9, 'PROPONER', 'marta.rivas', '2026-09-29T14:32:00.000Z', 'porcentaje_beca|' + PROCESO + '|*|*|*', [{ valor: '35' }], { datos: { valor: '30' } }, 'Acuerdo CA-2026-14'),
  traza(8, 'DESACTIVAR', 'ana.perez', '2026-09-27T14:32:00.000Z', ['vias_pago', PROCESO, ACT_PAGO, '*', 'prepago'].join('|'), [{ etiqueta: 'Bono prepago', activo: true }], [{ etiqueta: 'Bono prepago', activo: false }], 'El bono prepago se retiró del catálogo de pagos (memo CP-2026-31).'),
  traza(7, 'EDITAR', 'ana.perez', '2026-09-27T14:30:00.000Z', ['vias_pago', PROCESO, ACT_PAGO, '*', 'efectivo'].join('|'), [{ etiqueta: 'Efectivo' }], [{ etiqueta: 'Pago en caja' }], 'Unificar el nombre con la carta de pago.'),
  traza(6, 'APROBAR', 'jorge.pena', '2026-09-01T13:40:00.000Z', 'porcentaje_beca|' + PROCESO + '|*|*|*', [{ valor: '38' }], [{ valor: '35' }], 'Política de becas 2026'),
];

export const DELEGACIONES: Delegacion[] = [
  {
    persistenceVersion: 1,
    tipoSujeto: 'USUARIO',
    sujetoUsuarioId: 7,
    sujetoGrupoId: null,
    sujetoRolId: null,
    sujetoRuta: 'luis.gil',
    incluyeSubgrupos: false,
    proceso: PROCESO,
    actividades: [],
    vigenteDesde: '2026-08-01T00:00:00.000Z',
    vigenteHasta: null,
    activo: true,
    otorgadoPor: 'marta.rivas',
    motivo: 'Cobertura del cierre anual',
  },
];

// ─── Un kit de mentira, con los tres perfiles de las pantallas aprobadas ─────────────────────────────

export type PerfilDeEjemplo = 'superadministracion' | 'delegado' | 'consulta' | 'cliente';

const SESIONES: Record<PerfilDeEjemplo, Sesion> = {
  superadministracion: { id: '1', usuario: 'marta.rivas', nombre: 'Marta Rivas' },
  delegado: { id: '7', usuario: 'luis.gil', nombre: 'Luis Gil' },
  consulta: { id: '9', usuario: 'pedro.almonte', nombre: 'Pedro Almonte' },
  cliente: { id: '2', usuario: 'cliente.demo', nombre: 'Camila Prospecto' },
};

export interface OpcionesDelKit {
  perfil: PerfilDeEjemplo;
  /** Para probar un fallo: la clase con la que falla cada lectura. */
  fallos?: Partial<Record<keyof Kit, FalloDelKit>>;
  /** Los usos que sirve el doble; con una función, cambian con lo escrito (`escrituras` = cuántas van). */
  usos?: Usos | null | ((definicion: string, escrituras: number) => Usos);
  /** Las delegaciones con las que abre (por defecto, la de Luis Gil). */
  delegaciones?: Delegacion[];
  /** La verificación de la cadena encuentra una entrada manipulada. */
  cadenaRota?: boolean;
  /**
   * Como el kit real: `verificar(false)` solo comprueba lo posterior al último punto verificado. Una entrada
   * INTERIOR manipulada (anterior a ese punto) solo la ve `verificar(true)`; una POSTERIOR la ven las dos.
   */
  manipulacion?: 'interior' | 'posterior';
  /** La traza tiene una entrada antigua de alguien que ninguna otra pantalla ha tenido que nombrar. */
  usuarioAjeno?: boolean;
  /** Añade a la traza las entradas CAPTURADAS del kit real (delegaciones de cada tipo de sujeto). */
  trazaReal?: boolean;
  /** Escrituras que el servidor APLICA pero cuya respuesta nunca llega (`SIN_RESPUESTA`). */
  escrituraSinRespuesta?: Array<'cambiar' | 'decidir' | 'delegar' | 'revocar' | 'importar'>;
  /** Tras escribir, la lectura COMPLETA de propuestas cae y la de pendientes no. */
  completasFallanTrasEscritura?: boolean;
  /** Personas y roles que se leen igual (dos «Ana Ruiz», `jefeEvaluacion`/`jefe_evaluacion`) y dos personas con el mismo nombre en la traza. */
  homonimos?: boolean;
  /** Propuestas retiradas más nuevas que las demás: con más de 100 en total, la primera página del kit no trae las pendientes. */
  relleno?: number;
  /** Más de 20 personas en la organización: `organizacion` devuelve 20 como el kit, `nombreDeSujeto` las resuelve todas. */
  muchasPersonas?: boolean;
  /** Entradas de traza MÁS NUEVAS que las de siempre (de otra lista y otra persona): las de siempre quedan en la 3.ª página del kit. */
  muchasEntradas?: number;
  /** Propuestas PENDIENTES de otras personas (todas aprobables): con más de 100, la primera página del kit no las trae todas. */
  rellenoPendientes?: number;
  /** Entradas de traza y propuestas que el caso añade tal cual (por ejemplo, una delegación a la persona 21). */
  trazaAdicional?: EntradaDeTraza[];
  propuestasAdicionales?: Propuesta[];
  /** La traza todavía no tiene entradas: verificar la cadena no comprueba nada. */
  cadenaVacia?: boolean;
  /** Lecturas que fallan SOLO después de que la persona escribió algo (la escritura sí se aplica): B2 gemela. */
  fallaTrasEscritura?: Array<keyof Kit>;
  /** El conflicto que el kit devuelve lo provocó la propia persona de la sesión. */
  conflictoConmigo?: boolean;
  /** Una lectura que funciona las primeras veces y luego falla: cuántas llamadas OK antes del fallo. */
  fallaDespuesDe?: Partial<Record<keyof Kit, number>>;
  /** Propuestas de ejemplo que NO existen al abrir (se publican después con `publicarPropuesta`). */
  sinPropuestas?: number[];
}

const copia = <T,>(x: T): T => JSON.parse(JSON.stringify(x)) as T;

/** Los instantes de las escrituras del doble, uno por minuto, escritos y no calculados. */
const INSTANTES: readonly string[] = [
  '2026-10-20T12:00:00.000Z', '2026-10-20T12:01:00.000Z', '2026-10-20T12:02:00.000Z', '2026-10-20T12:03:00.000Z', '2026-10-20T12:04:00.000Z', '2026-10-20T12:05:00.000Z', '2026-10-20T12:06:00.000Z', '2026-10-20T12:07:00.000Z', '2026-10-20T12:08:00.000Z', '2026-10-20T12:09:00.000Z', '2026-10-20T12:10:00.000Z', '2026-10-20T12:11:00.000Z', '2026-10-20T12:12:00.000Z', '2026-10-20T12:13:00.000Z', '2026-10-20T12:14:00.000Z', '2026-10-20T12:15:00.000Z', '2026-10-20T12:16:00.000Z', '2026-10-20T12:17:00.000Z', '2026-10-20T12:18:00.000Z', '2026-10-20T12:19:00.000Z', '2026-10-20T12:20:00.000Z', '2026-10-20T12:21:00.000Z', '2026-10-20T12:22:00.000Z', '2026-10-20T12:23:00.000Z', '2026-10-20T12:24:00.000Z', '2026-10-20T12:25:00.000Z', '2026-10-20T12:26:00.000Z', '2026-10-20T12:27:00.000Z', '2026-10-20T12:28:00.000Z', '2026-10-20T12:29:00.000Z', '2026-10-20T12:30:00.000Z', '2026-10-20T12:31:00.000Z', '2026-10-20T12:32:00.000Z', '2026-10-20T12:33:00.000Z', '2026-10-20T12:34:00.000Z', '2026-10-20T12:35:00.000Z', '2026-10-20T12:36:00.000Z', '2026-10-20T12:37:00.000Z', '2026-10-20T12:38:00.000Z', '2026-10-20T12:39:00.000Z',
];

/**
 * Clasifica un CSV de ejemplo como lo haría el kit, con lo mínimo: columnas `definicion,codigo,etiqueta,activo`.
 * Una fila repetida es un ERROR, una definición de impacto alto es PROPUESTA, un código nuevo es ALTA, uno
 * que ya existe es CAMBIO (o BAJA si `activo` es «no») y, si coincide, SIN_CAMBIOS. La huella es el propio texto.
 */
/** El número de la fila, como TEXTO (el kit lo dice así: «ya está en la fila 3»). */
const FILAS_DE_CSV: readonly string[] = ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];
function clasificarCsv(csv: string): VistaPreviaDeImportacion {
  const lineas = csv.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  const vistas = new Set<string>();
  const filas = lineas.slice(1).map((l, i) => {
    const [definicion = '', codigo = '', etiqueta = '', activo = ''] = l.split(',').map((x) => x.trim());
    const base = { fila: i + 2, definicion, proceso: PROCESO, actividad: '*', codigoPadre: '*', codigo };
    const def = DEFINICIONES.find((d) => d.codigo === definicion);
    if (!def) return { ...base, clase: 'ERROR' as const, detalle: `definicion: no existe una definición activa «${definicion}»` };
    const clave = definicion + '|' + codigo;
    if (vistas.has(clave)) return { ...base, clase: 'ERROR' as const, detalle: 'codigo: código repetido: ya está en la fila ' + (FILAS_DE_CSV[i - 1] ?? '2') };
    vistas.add(clave);
    const hay = (FILAS[definicion] ?? []).find((f) => f.codigo === codigo);
    if (def.impacto === 'ALTO') return { ...base, clase: 'PROPUESTA' as const, detalle: 'queda como propuesta: impacto alto' };
    if (!hay) return { ...base, clase: 'ALTA' as const, detalle: 'nueva' };
    if (activo.toLowerCase() === 'no') return { ...base, clase: 'BAJA' as const, detalle: 'se desactiva, no se borra' };
    if (etiqueta !== '' && etiqueta !== hay.etiqueta) return { ...base, clase: 'CAMBIO' as const, detalle: 'etiqueta «' + (hay.etiqueta ?? '') + '» → «' + etiqueta + '»' };
    return { ...base, clase: 'SIN_CAMBIOS' as const, detalle: 'coincide con lo guardado' };
  });
  const cuenta = (c: string) => filas.filter((f) => f.clase === c).length;
  return {
    resumen: { altas: cuenta('ALTA'), cambios: cuenta('CAMBIO'), bajas: cuenta('BAJA'), sinCambios: cuenta('SIN_CAMBIOS'), propuestas: cuenta('PROPUESTA'), errores: cuenta('ERROR') },
    filas,
    huella: csv,
  };
}

/**
 * Un `Kit` que contesta con los datos de ejemplo, sin red, y que **recuerda lo que se escribe**: es un
 * DOBLE del servidor, no el servidor. Reproduce solo lo que la pantalla necesita para probarse —motivo
 * obligatorio, bloqueo optimista por `persistenceVersion`, propuesta en impacto alto— y deja en `escrituras`
 * cada petición tal como llegó. La fidelidad del doble al kit real la miden las pruebas del módulo y el journey.
 */
export function kitDeEjemplo(
  opciones: OpcionesDelKit,
): Kit & { escrituras: Array<{ operacion: string; datos: unknown }>; publicarPropuesta: (id: number) => void } {
  const { perfil, fallos = {} } = opciones;
  const escrituras: Array<{ operacion: string; datos: unknown }> = [];
  const filas: Record<string, Fila[]> = copia(FILAS);
  // Con homónimos: dos OPCIONES de la misma lista que se llaman igual y se distinguen solo por su código.
  if (opciones.homonimos) {
    filas.vias_pago!.push(fila('vias_pago', PROCESO, ACT_PAGO, 'aaa_homonimo', 'Empleado privado', { orden: 5 }), fila('vias_pago', PROCESO, ACT_PAGO, 'empleado_privado', 'Empleado privado', { orden: 6 }));
  }
  const nuevasEntradas: EntradaDeTraza[] = Array.from({ length: opciones.muchasEntradas ?? 0 }, (_, i) => traza(500 + i, 'EDITAR', 'jorge.pena', `2026-11-${DOS_CIFRAS[1 + (i % 28)]}T${DOS_CIFRAS[10 + Math.floor(i / 28)]}:00:00.000Z`, 'porcentaje_beca|' + PROCESO + '|*|*|*', [{ valor: '35' }], [{ valor: '36' }], 'Ajuste ' + DOS_CIFRAS[i % 60]));
  const trazas: EntradaDeTraza[] = copia([...nuevasEntradas, ...(opciones.trazaAdicional ?? []), ...(opciones.homonimos ? [...TRAZA, traza(12, 'APROBAR', 'sara.parametros2', '2026-10-01T10:00:00.000Z', 'porcentaje_beca|' + PROCESO + '|*|*|*', [{ valor: '35' }], { filas: [{ valor: '30' }], propuesta: { proponente: 'sara.parametros', aprobador: 'sara.parametros2' } }, 'Circular'), traza(11, 'PROPONER', 'sara.parametros', '2026-10-01T09:00:00.000Z', 'porcentaje_beca|' + PROCESO + '|*|*|*', [{ valor: '35' }], { datos: { valor: '30' } }, 'Circular')] : opciones.trazaReal ? [...TRAZA, ...TRAZA_REAL] : opciones.usuarioAjeno ? [...TRAZA, traza(5, 'EDITAR_DEFINICION', 'olga.negocio', '2026-08-20T10:00:00.000Z', 'porcentaje_beca|*|*|*|*', null, null, 'Ajuste de la descripción')] : TRAZA)]);
  // Con homónimos, una propuesta de OTRA persona que se llama como la de la sesión (marta.rivas2 → «Marta Rivas»).
  const deHomonimo: Propuesta[] = opciones.homonimos ? [{ ...copia(PROPUESTAS[0]!), id: 77, proponente: 'marta.rivas2', creadaEn: '2026-10-02T09:00:00.000Z', esPropia: false }] : [];
  const pendientesDeRelleno: Propuesta[] = Array.from({ length: opciones.rellenoPendientes ?? 0 }, (_, i) => ({ ...copia(PROPUESTAS[1] ?? PROPUESTAS[0]!), id: 3000 + i, estado: 'PENDIENTE' as const, esPropia: false, creadaEn: `2026-09-01T10:${DOS_CIFRAS[i % 60]}:${DOS_CIFRAS[Math.floor(i / 60)]}.000Z` }));
  const todasLasPropuestas: Propuesta[] = copia([...PROPUESTAS, ...pendientesDeRelleno, ...(opciones.propuestasAdicionales ?? []), ...deHomonimo, ...RESUELTAS]);
  const delegacionesVivas: Delegacion[] = copia(opciones.delegaciones ?? DELEGACIONES);
  const ocultas = new Set(opciones.sinPropuestas ?? []);
  const propuestas: Propuesta[] = todasLasPropuestas.filter((p) => !ocultas.has(p.id));
  let reloj = 0;
  const cuenta: Partial<Record<keyof Kit, number>> = {};
  let escribio = false;
  const probar = (operacion: keyof Kit) => {
    if (escribio && opciones.fallaTrasEscritura?.includes(operacion)) throw new FalloDelKit('SERVIDOR');
    if (['cambiar', 'decidir', 'importar', 'delegar', 'revocar'].includes(operacion)) escribio = true;
    const fallo = fallos[operacion];
    if (fallo) throw fallo;
    const llamadas = (cuenta[operacion] = (cuenta[operacion] ?? 0) + 1);
    const tolerancia = opciones.fallaDespuesDe?.[operacion];
    if (tolerancia !== undefined && llamadas > tolerancia) throw new FalloDelKit('SERVIDOR');
    if (perfil === 'cliente') throw new FalloDelKit('SIN_PERMISO');
  };
  const editores: Editor[] = [
    { tipo: 'SUPERADMINISTRACION' },
    { tipo: 'USUARIO', sujeto: 'luis.gil', proceso: PROCESO, actividades: [], vigenteHasta: null },
    // Con homónimos: dos roles que se humanizan igual y dos personas que se llaman igual, delegados sobre lo mismo.
    ...(opciones.homonimos
      ? ([
          { tipo: 'ROL', sujeto: 'jefeEvaluacion', proceso: PROCESO, actividades: [], vigenteHasta: null },
          { tipo: 'ROL', sujeto: 'jefe_evaluacion', proceso: PROCESO, actividades: [], vigenteHasta: null },
          { tipo: 'USUARIO', sujeto: 'ana.ruiz', proceso: PROCESO, actividades: [], vigenteHasta: null },
          { tipo: 'USUARIO', sujeto: 'ana.ruiz2', proceso: PROCESO, actividades: [], vigenteHasta: null },
        ] as Editor[])
      : []),
  ];
  const membresias: Membresia[] =
    perfil === 'superadministracion' ? [{ rol: ROL_DE_SUPERADMINISTRACION, grupo: '/academia/evaluacion' }] : [{ rol: 'member', grupo: '/academia/operaciones' }];
  const quien = SESIONES[perfil].usuario;
  const organizacionCompleta = () => {
    const todo = {
      usuario: [{ id: 4, nombre: 'carla.ruiz' }, { id: 1, nombre: 'marta.rivas' }, { id: 7, nombre: 'luis.gil' }, { id: 8, nombre: 'ana.perez' }],
      grupo: [{ id: 2, nombre: '/academia' }, { id: 11, nombre: '/academia/evaluacion' }, { id: 12, nombre: '/academia/evaluacion/curso' }, { id: 13, nombre: '/academia/operaciones' }],
      rol: [{ id: 2, nombre: 'analistaBecas' }, { id: 20, nombre: 'member' }, { id: 21, nombre: 'jefeEvaluacion' }, { id: 22, nombre: 'superAdministradorParametros' }],
    };
    if (opciones.homonimos) {
      todo.usuario.push({ id: 31, nombre: 'ana.ruiz' }, { id: 32, nombre: 'ana.ruiz2' }, { id: 33, nombre: 'sara.parametros' }, { id: 34, nombre: 'sara.parametros2' });
      todo.rol.push({ id: 41, nombre: 'jefeEvaluacion' }, { id: 42, nombre: 'jefe_evaluacion' });
    }
    if (opciones.muchasPersonas) {
      // 20 personas de relleno y, la última, la que una búsqueda de 20 nunca trae: la persona 21+.
      for (const [i, login] of LOGINS_DE_RELLENO.entries()) todo.usuario.push({ id: 100 + i, nombre: login });
      todo.usuario.push({ id: 200, nombre: 'zeta.ultima' });
    }
    return todo;
  };
  /** Lo que el servidor le dice a ESTA persona de cada propuesta: si es suya y si puede aprobarla. */
  const marcar = (p: Propuesta): Propuesta => ({
    ...p,
    esPropia: p.proponente === quien,
    puedesAprobar:
      p.estado === 'PENDIENTE' && p.proponente !== quien && (perfil === 'superadministracion' || (perfil === 'delegado' && p.proceso === PROCESO)),
  });

  const enAmbito = (f: Fila, a: { proceso: string; actividad: string }) => f.proceso === a.proceso && f.actividad === a.actividad;
  const anotar = (accion: string, clave: string, antes: unknown, despues: unknown, motivo: string) => {
    reloj++;
    trazas.unshift({
      id: 100 + reloj,
      fechaHora: INSTANTES[reloj] ?? INSTANTES[INSTANTES.length - 1],
      usuario: quien,
      rolesVigentes: [],
      accion,
      claveNegocio: clave,
      valorAnterior: antes,
      valorNuevo: despues,
      motivo,
      origen: 'PANTALLA',
      lote: null,
      hashAnterior: 'x',
      hash: ['h', INSTANTES[reloj] ?? ''].join(''),
    });
  };

  async function cambiar(p: PeticionDeCambio): Promise<ResultadoDeEscritura> {
    probar('cambiar');
    escrituras.push({ operacion: 'cambiar', datos: copia(p) });
    if (!p.motivo || p.motivo.trim() === '') throw new FalloDelKit('VALIDACION', 'motivo', 'el motivo es obligatorio');
    const def = DEFINICIONES.find((d) => d.codigo === p.definicion);
    if (!def) throw new FalloDelKit('NO_EXISTE');
    const todas = (filas[p.definicion] ??= []);
    const padre = p.codigoPadre ?? '*';
    const codigo = p.codigo ?? '*';
    const clave = [p.definicion, p.ambito.proceso, p.ambito.actividad, padre, codigo].join('|');
    const buscar = () => todas.find((f) => enAmbito(f, p.ambito) && f.codigoPadre === padre && f.codigo === codigo);
    const conVersion = (f: Fila | undefined): Fila => {
      if (!f) throw new FalloDelKit('VALIDACION', 'codigo', 'no existe');
      if (f.persistenceVersion !== p.persistenceVersion) throw new FalloDelKit('CONFLICTO', null, null, opciones.conflictoConmigo ? quien : 'ana.perez', '2026-10-20T12:00:00.000Z');
      return f;
    };
    if (def.impacto === 'ALTO' && ['EDITAR', 'CREAR', 'DESACTIVAR', 'REACTIVAR'].includes(p.accion)) {
      const f = buscar();
      conVersion(f);
      if (propuestas.some((x) => x.estado === 'PENDIENTE' && x.definicion === p.definicion && x.proceso === p.ambito.proceso && x.actividad === p.ambito.actividad)) {
        throw new FalloDelKit('CONFLICTO', null, null, 'luis.gil', '2026-09-29T14:31:00.000Z');
      }
      const nueva = {
        ...copia(PROPUESTAS[0]),
        id: 50 + propuestas.length,
        definicion: p.definicion,
        proceso: p.ambito.proceso,
        actividad: p.ambito.actividad,
        proponente: quien,
        esPropia: true,
        puedesAprobar: false,
        motivo: p.motivo,
        valorAnterior: [{ valor: f?.valor ?? null }],
        valorPropuesto: { accion: p.accion, definicion: p.definicion, proceso: p.ambito.proceso, actividad: p.ambito.actividad, codigoPadre: padre, codigo, datos: p.datos ?? {} },
      } as Propuesta;
      propuestas.unshift(nueva);
      anotar('PROPONER', clave, [{ valor: f?.valor ?? null }], nueva, p.motivo);
      return { aplicado: false, propuesta: { id: nueva.id, estado: 'PENDIENTE' } };
    }
    switch (p.accion) {
      case 'EDITAR': {
        const f = conVersion(buscar());
        const antes = copia(f);
        if (p.datos && 'etiqueta' in p.datos && typeof p.datos.etiqueta === 'string') f.etiqueta = p.datos.etiqueta;
        if (p.datos && 'ayuda' in p.datos) f.ayuda = (p.datos.ayuda as string | null) ?? null;
        if (p.datos && 'valor' in p.datos) f.valor = p.datos.valor as string;
        f.persistenceVersion++;
        anotar('EDITAR', clave, [antes], [copia(f)], p.motivo);
        break;
      }
      case 'CREAR': {
        if (buscar()) throw new FalloDelKit('VALIDACION', 'codigo', 'ya existe en la lista');
        const etiqueta = typeof p.datos?.etiqueta === 'string' ? p.datos.etiqueta : null;
        const nueva = fila(p.definicion, p.ambito.proceso, p.ambito.actividad, codigo, etiqueta, {
          codigoPadre: padre,
          orden: todas.filter((f) => enAmbito(f, p.ambito) && f.codigoPadre === padre).length + 1,
          ayuda: (p.datos?.ayuda as string | undefined) ?? null,
        });
        todas.push(nueva);
        anotar('CREAR', clave, null, [copia(nueva)], p.motivo);
        break;
      }
      case 'DESACTIVAR':
      case 'REACTIVAR': {
        const f = conVersion(buscar());
        const antes = copia(f);
        f.activo = p.accion === 'REACTIVAR';
        f.persistenceVersion++;
        anotar(p.accion, clave, [antes], [copia(f)], p.motivo);
        break;
      }
      case 'ORDENAR': {
        const pedido = (p.datos?.orden ?? []) as Array<{ codigo: string; persistenceVersion?: number }>;
        pedido.forEach((x, i) => {
          const f = todas.find((y) => enAmbito(y, p.ambito) && y.codigoPadre === padre && y.codigo === x.codigo);
          if (!f || f.persistenceVersion !== x.persistenceVersion) throw new FalloDelKit('CONFLICTO');
          f.orden = i + 1;
          f.persistenceVersion++;
        });
        anotar('ORDENAR', clave, null, null, p.motivo);
        break;
      }
      case 'CREAR_VERSION_PROPIA': {
        const origen = [p.ambito.proceso === '*' ? null : { proceso: p.ambito.proceso, actividad: '*' }, { proceso: '*', actividad: '*' }]
          .filter((x): x is { proceso: string; actividad: string } => x !== null)
          .find((a) => todas.some((f) => enAmbito(f, a) && f.activo));
        if (!origen) throw new FalloDelKit('VALIDACION', 'ambito', 'no hay lista que copiar');
        const copiadas = todas.filter((f) => enAmbito(f, origen));
        const codigosOrigen = JSON.stringify(copiadas.filter((f) => f.activo).map((f) => (f.codigoPadre === '*' ? f.codigo : [f.codigoPadre, f.codigo].join('|'))));
        for (const f of copiadas) {
          todas.push({ ...copia(f), proceso: p.ambito.proceso, actividad: p.ambito.actividad, copiadoDe: [origen.proceso, origen.actividad].join('|'), codigosOrigen, persistenceVersion: versionDeFila++ });
        }
        anotar('CREAR_VERSION_PROPIA', clave, null, null, p.motivo);
        break;
      }
      case 'VOLVER_A_HEREDAR': {
        for (const f of todas.filter((x) => enAmbito(x, p.ambito))) {
          f.activo = false;
          f.persistenceVersion++;
        }
        anotar('VOLVER_A_HEREDAR', clave, null, null, p.motivo);
        break;
      }
      default:
        throw new FalloDelKit('VALIDACION', 'accion', 'no soportada por el doble');
    }
    return { aplicado: true as const, filas: [] };
  }

  const kit: Kit & { escrituras: Array<{ operacion: string; datos: unknown }>; publicarPropuesta: (id: number) => void } = {
    escrituras,
    /** Otra persona propone DESPUÉS de que la pantalla abrió: lo que provoca el conflicto de p05--conflicto. */
    publicarPropuesta: (id: number) => {
      const p = todasLasPropuestas.find((x) => x.id === id);
      if (p && !propuestas.some((x) => x.id === id)) propuestas.unshift(copia(p));
    },
    sesion: async () => SESIONES[perfil],
    membresias: async () => membresias,
    nombreDe: async (u) => (opciones.homonimos && /^(ana\.ruiz2?|sara\.parametros2?|marta\.rivas2)$/.test(u) ? (u.startsWith('ana') ? 'Ana Ruiz' : u.startsWith('marta') ? 'Marta Rivas' : 'Sara Parametros') : (NOMBRES[u] ?? u)),
    procesos: async () => (probar('procesos'), PROCESOS),
    definiciones: async () => (probar('definiciones'), DEFINICIONES),
    valores: async (d) => {
      probar('valores');
      const def = DEFINICIONES.find((x) => x.codigo === d);
      if (!def) throw new FalloDelKit('NO_EXISTE');
      return { definicion: def, filas: copia(filas[d] ?? []) };
    },
    propuestas: async (estado, pagina = 0) => {
      probar('propuestas');
      // Solo la lectura de lo RESUELTO (la de Aprobaciones) cae; la de pendientes (la de la aplicación) funciona: cada una es dueña de su aviso.
      if (opciones.completasFallanTrasEscritura && escribio && estado !== undefined && estado !== 'PENDIENTE') throw new FalloDelKit('SERVIDOR');
      // Como el kit: por fecha DESC y de 100 en 100. `relleno` antepone propuestas retiradas MÁS NUEVAS que las demás.
      const relleno: Propuesta[] = Array.from({ length: opciones.relleno ?? 0 }, (_, i) => ({ ...copia(propuestas[0]!), id: 1000 + i, estado: 'RETIRADA' as const, creadaEn: `2026-12-01T10:${DOS_CIFRAS[i % 60]}:${DOS_CIFRAS[Math.floor(i / 60)]}.000Z` }));
      const todas = [...relleno, ...propuestas].map(marcar).filter((p) => estado === undefined || p.estado === estado);
      const pagina100 = todas.slice(pagina * 100, pagina * 100 + 100);
      return { paraAprobar: todas.filter((p) => p.puedesAprobar).length, propias: todas.filter((p) => p.esPropia && p.estado === 'PENDIENTE').length, total: todas.length, propuestas: copia(pagina100) };
    },
    editores: async () => (probar('editores'), editores),
    traza: async (f: FiltrosDeTraza, pagina = 0) => {
      probar('traza');
      // Como el kit: filtra por usuario y por fechas EN EL SERVIDOR y pagina de 100 en 100 (más nueva primero).
      const todas = trazas.filter((e) => (f.usuario === undefined || e.usuario === f.usuario) && (f.desde === undefined || e.fechaHora >= f.desde) && (f.hasta === undefined || e.fechaHora <= f.hasta));
      const delaPagina = todas.slice(pagina * 100, pagina * 100 + 100);
      return { elementos: copia(delaPagina), hayMas: delaPagina.length >= 100 };
    },
    verificar: async (completa) => {
      probar('verificar');
      const manipulada = opciones.cadenaRota || opciones.manipulacion === 'posterior' || (opciones.manipulacion === 'interior' && completa);
      if (opciones.cadenaVacia) return { coherente: true as const, entradas: 0, desde: null, hasta: null };
      if (opciones.manipulacion === 'interior' && !completa) return { coherente: true as const, entradas: 0, desde: null, hasta: null };
      return manipulada
        ? { coherente: false as const, primeraQueNoCasa: { id: 7, fechaHora: '2026-09-27T14:30:00.000Z', claveNegocio: 'vias_pago|x|y|*|efectivo' } }
        : { coherente: true as const, entradas: 4, desde: 1, hasta: 9 };
    },
    delegaciones: async () => (probar('delegaciones'), copia(delegacionesVivas)),
    organizacion: async (tipo, q) => {
      probar('organizacion');
      const todo = organizacionCompleta();
      // Como el kit: «contiene» sobre el nombre y el usuario, y 20 como máximo (`OrganizacionBonita.MAXIMO`).
      const buscado = q.trim().toLowerCase();
      const coincide = (x: { nombre: string }) => buscado === '' || x.nombre.toLowerCase().includes(buscado) || (NOMBRES[x.nombre] ?? '').toLowerCase().includes(buscado);
      return todo[tipo].filter(coincide).slice(0, 20);
    },
    nombreDeSujeto: async (tipo, id) => {
      probar('nombreDeSujeto');
      const x = organizacionCompleta()[tipo].find((y) => y.id === id);
      return x ? { nombre: tipo === 'usuario' ? (NOMBRES[x.nombre] ?? x.nombre) : x.nombre, extra: x.nombre } : null;
    },
    cambiar,
    decidir: async (p, decision, comentario) => {
      probar('decidir');
      escrituras.push({ operacion: 'decidir', datos: { id: p.id, decision, comentario } });
      const real = propuestas.find((x) => x.id === p.id);
      if (!real) throw new FalloDelKit('NO_EXISTE');
      if (real.estado !== 'PENDIENTE' || real.persistenceVersion !== p.persistenceVersion) {
        throw new FalloDelKit('CONFLICTO', null, null, real.aprobador ?? real.proponente, real.resueltaEn ?? real.creadaEn);
      }
      const propia = real.proponente === quien;
      // Quien propone no aprueba ni rechaza; solo quien propone retira.
      if (decision === 'RETIRAR' ? !propia : propia) throw new FalloDelKit('SIN_PERMISO');
      if (decision !== 'RETIRAR' && !marcar(real).puedesAprobar) throw new FalloDelKit('SIN_PERMISO');
      if (decision === 'RECHAZAR' && comentario.trim() === '') throw new FalloDelKit('VALIDACION', 'comentario', 'el comentario es obligatorio');
      const clave = [real.definicion, real.proceso, real.actividad, real.codigoPadre, real.codigo].join('|');
      let despues: unknown = null;
      if (decision === 'APROBAR') {
        const todas = (filas[real.definicion] ??= []);
        const op = real.valorPropuesto;
        const destino = todas.find((f) => enAmbito(f, { proceso: op.proceso, actividad: op.actividad }) && f.codigoPadre === op.codigoPadre && f.codigo === op.codigo);
        if (destino) {
          destino.valor = op.datos.valor as string;
          destino.persistenceVersion++;
        } else {
          todas.push(fila(op.definicion, op.proceso, op.actividad, op.codigo, null, { codigoPadre: op.codigoPadre, valor: op.datos.valor as string }));
        }
        despues = { filas: [{ valor: op.datos.valor }], propuesta: { proponente: real.proponente, aprobador: quien } };
      }
      real.estado = decision === 'APROBAR' ? 'APROBADA' : decision === 'RECHAZAR' ? 'RECHAZADA' : 'RETIRADA';
      real.aprobador = quien;
      real.comentario = comentario.trim() === '' ? null : comentario.trim();
      real.resueltaEn = INSTANTES[reloj + 1] ?? INSTANTES[INSTANTES.length - 1];
      real.persistenceVersion++;
      anotar(decision, clave, real.valorAnterior, despues, decision === 'APROBAR' ? real.motivo : comentario);
    },
    vistaPreviaDeImportacion: async (csv) => (probar('vistaPreviaDeImportacion'), clasificarCsv(csv)),
    importar: async (csv, motivo, huella) => {
      probar('importar');
      escrituras.push({ operacion: 'importar', datos: { csv, motivo, huella } });
      if (motivo.trim() === '') throw new FalloDelKit('VALIDACION', 'motivo', 'el motivo es obligatorio');
      const vista = clasificarCsv(csv);
      if (huella !== vista.huella) throw new FalloDelKit('CONFLICTO', null, null, null, null, vista);
      // Aplica lo que clasificó como CAMBIO de nombre: la lista leída antes de importar queda vieja y hay que releerla.
      for (const l of csv.replace(/^\uFEFF/, '').trim().split(/\r?\n/).slice(1)) {
        const [definicion = '', codigo = '', etiqueta = ''] = l.split(',').map((x) => x.trim());
        const f = (filas[definicion] ?? []).find((x) => x.codigo === codigo);
        if (f && etiqueta !== '' && etiqueta !== f.etiqueta) {
          f.etiqueta = etiqueta;
          f.persistenceVersion++;
        }
      }
      return { lote: 'IMP-2026-1020-01', resumen: vista.resumen, filas: vista.filas };
    },
    delegar: async (d, motivo) => {
      probar('delegar');
      escrituras.push({ operacion: 'delegar', datos: { d, motivo } });
      const nueva = {
        ...copia(PROPUESTAS[0]),
        id: 80 + propuestas.length,
        definicion: '*',
        proceso: d.proceso,
        actividad: '*',
        accion: 'DELEGAR',
        proponente: quien,
        motivo,
        valorAnterior: [],
        valorPropuesto: { accion: 'DELEGAR', definicion: '*', proceso: d.proceso, actividad: '*', codigoPadre: '*', codigo: '*', datos: { ...d } },
      } as Propuesta;
      propuestas.unshift(nueva);
      return { aplicado: false as const, propuesta: { id: nueva.id, estado: 'PENDIENTE' } };
    },
    revocar: async (d, motivo) => {
      probar('revocar');
      escrituras.push({ operacion: 'revocar', datos: { d, motivo } });
      const viva = delegacionesVivas.find((x) => x.tipoSujeto === d.tipoSujeto && x.sujetoUsuarioId === d.sujetoUsuarioId && x.sujetoGrupoId === d.sujetoGrupoId && x.sujetoRolId === d.sujetoRolId && x.proceso === d.proceso);
      if (viva) viva.activo = false;
    },
    usos: async (definicion) => {
      probar('usos');
      const u = opciones.usos;
      return typeof u === 'function' ? u(definicion, escrituras.length) : (u ?? { lugares: [], expedientes: [] });
    },
  };
  // Escrituras cuya respuesta se pierde: el servidor SÍ las aplicó y a la pantalla no le llega nada (B1).
  const sinRespuesta = opciones.escrituraSinRespuesta ?? [];
  for (const op of ['cambiar', 'decidir', 'delegar', 'revocar', 'importar'] as const) {
    if (!sinRespuesta.includes(op)) continue;
    const original = kit[op] as (...a: never[]) => Promise<unknown>;
    (kit as unknown as Record<string, unknown>)[op] = async (...a: never[]) => {
      await original(...a);
      throw new FalloDelKit('SIN_RESPUESTA');
    };
  }
  return kit;
}
