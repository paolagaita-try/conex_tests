/**
 * El modelo de una LISTA en un ámbito (pantallas `p02-lista*`): qué opciones se ven, de dónde
 * vienen, qué se puede hacer con ellas y cómo quedará en el formulario. Lógica pura: recibe los datos
 * CRUDOS del kit y devuelve un modelo sin números sueltos (textos, sí/no y recuentos marcados), que es
 * lo único que llega a la vista (ver `inicio.ts`).
 */
import { recuentoDe, type Recuento } from '$lib/bonita/marcas';
import { widgetPorDefecto, type Widget } from '$lib/ui/widgetPorDefecto';
import {
  type Ambito,
  actividadesConVersionPropia,
  ambitoDeLista,
  esGlobal,
  filasEn,
  filasOrdenadas,
  huerfanos,
  listaResuelta,
  mismoAmbito,
  opcionesNuevasDelOrigen,
} from './ambitos';
import { puedeEditarEn, type Capacidades } from './capacidades';
import { esNodoTecnico, nombreDeActividad, nombreDeGrupo, nombreDeProceso, nombreDeRol, nombresUnicos, sujetoLegible } from './nombres';
import * as T from './textos';
import { TODO, type Editor, type Fila, type Proceso, type ValoresAdministracion } from './tipos';

/** Los lugares de una lista, como texto: la auditoría del origen no admite que se conviertan al pintar. */
export const POSICIONES: readonly string[] = [
  '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '96', '97', '98', '99',
];

export type ModoDeLista = 'propia' | 'heredada' | 'vacia';

export interface MigaDeAmbito {
  rotulo: string;
  ambito: Ambito;
  actual: boolean;
}

export interface OpcionVM {
  /** `codigoPadre|codigo`: lo que la vista devuelve al editar o ordenar. */
  clave: string;
  codigo: string;
  etiqueta: string;
  ayuda: string;
  activa: boolean;
  /** «1», «2», …: el lugar en la lista. */
  posicion: string;
  puedeSubir: boolean;
  puedeBajar: boolean;
}

export interface AmbitoHijo {
  ambito: Ambito;
  nombre: string;
  /** Tiene su propia versión de la lista. */
  propia: boolean;
}

export interface PadreVM {
  codigo: string;
  etiqueta: string;
  /** Cuántas opciones activas tiene su lista hija. */
  cuantas: Recuento;
}

export interface CampoDeVistaPrevia {
  id: string;
  etiqueta: string;
  widget: Widget;
  opciones: Array<{ valor: string; etiqueta: string }>;
  elegida: string | null;
}

export interface ListaVM {
  codigo: string;
  nombre: string;
  descripcion: string;
  impactoAlto: boolean;
  ambito: Ambito;
  migas: MigaDeAmbito[];
  modo: ModoDeLista;
  /** Chip de procedencia: «Lista propia de esta actividad», «Lista del proceso», «Heredada»… */
  procedencia: string;
  /** De dónde se hereda («Becas de estudio · todo el proceso»), si se hereda. */
  heredaDe: string;
  /** La persona puede editar en ESTE ámbito. */
  puedeEditar: boolean;
  /** Crear versión propia: heredada, con ámbito de actividad o proceso, y con permiso. */
  puedeCrearVersionPropia: boolean;
  /** Volver a heredar: propia en un ámbito que tiene de dónde heredar, y con permiso. */
  puedeVolverAHeredar: boolean;
  padres: PadreVM[] | null;
  padreElegido: string | null;
  opciones: OpcionVM[];
  total: Recuento;
  activas: Recuento;
  /** Cascada: el padre elegido no tiene opciones (es correcto: el campo no aparece). */
  sinHijas: boolean;
  /** Etiqueta del padre elegido, para el aviso de «sin duraciones». */
  etiquetaDelPadre: string;
  huerfanas: Array<{ etiqueta: string; padre: string }>;
  /** Opciones que el origen ganó desde que se copió (T-k), en lenguaje de negocio. */
  nuevasDelOrigen: Recuento;
  /** Actividades del proceso y si tienen versión propia (solo en el ámbito del proceso). */
  actividades: AmbitoHijo[];
  vistaPrevia: CampoDeVistaPrevia[];
  /** «Superadministración · Luis Gil, delegado de Becas de estudio»… */
  quienEdita: string[];
  definicion: Array<{ rotulo: string; valor: string; codigo?: boolean }>;
}

export interface DatosDeLista {
  valores: ValoresAdministracion;
  /** La lista madre completa, si esta depende de otra. */
  padre: ValoresAdministracion | null;
  ambito: Ambito;
  procesos: Proceso[];
  capacidades: Capacidades;
  editores: Editor[];
  /** Nombre para mostrar por nombre de inicio de sesión. */
  nombres: Record<string, string>;
  /** La opción madre elegida (cascada). */
  padreElegido?: string | null;
}

/** Las migas de un ámbito: Global › proceso › actividad. */
export function migasDe(a: Ambito): MigaDeAmbito[] {
  const migas: MigaDeAmbito[] = [{ rotulo: T.GLOBAL, ambito: { proceso: TODO, actividad: TODO }, actual: esGlobal(a) }];
  if (a.proceso !== TODO) {
    migas.push({ rotulo: nombreDeProceso(a.proceso), ambito: { proceso: a.proceso, actividad: TODO }, actual: a.actividad === TODO });
  }
  if (a.proceso !== TODO && a.actividad !== TODO) migas.push({ rotulo: nombreDeActividad(a.actividad), ambito: a, actual: true });
  return migas;
}

const claveDe = (f: Fila) => [f.codigoPadre, f.codigo].join('|');

export const etiquetaDe = (f: Fila): string => f.etiqueta ?? f.codigo;

/** «Superadministración», «Luis Gil · Becas de estudio», «/academia/operaciones · Preparar pago»… */
export function quienEditaLegible(editores: Editor[], nombres: Record<string, string>): string[] {
  const distintos = nombresUnicos(nombres);
  const frases = editores.map((e) => {
    if (e.tipo === 'SUPERADMINISTRACION') return T.SUPERADMINISTRACION;
    // Cada tipo de editor se dice a SU manera: un rol delegado («jefeEvaluacionBis») no es una ruta de grupo ni un login.
    const sujeto = e.sujeto ?? '';
    const quien =
      e.tipo === 'USUARIO' ? (distintos[sujeto] ?? sujeto)
      : e.tipo === 'ROL' ? nombreDeRol(sujeto)
      : e.tipo === 'GRUPO' ? nombreDeGrupo(sujeto)
      : sujetoLegible(sujeto);
    const donde =
      e.proceso === undefined
        ? ''
        : (e.actividades ?? []).length === 0
          ? nombreDeProceso(e.proceso)
          : (e.actividades ?? []).map(nombreDeActividad).join(', ');
    return [quien, donde].filter(Boolean).join(' · ');
  });
  // Dos editores que se leen igual (`jefeEvaluacion` y `jefe_evaluacion`, dos homónimos) se distinguen por lo que los identifica.
  const veces = new Map<string, number>();
  for (const f of frases) veces.set(f, (veces.get(f) ?? 0) + 1);
  return frases.map((f, i) => ((veces.get(f) ?? 0) > 1 ? `${f} (${editores[i]?.sujeto ?? ''})` : f));
}

function vistaPreviaDe(nombre: string, codigoPadre: string | null, datos: DatosDeLista, opciones: OpcionVM[]): CampoDeVistaPrevia[] {
  const activas = opciones.filter((o) => o.activa);
  const campos: CampoDeVistaPrevia[] = [];
  const padre = datos.padre;
  if (padre) {
    const hermanas = listaResuelta(padre.filas, datos.ambito);
    campos.push({
      id: 'previa-padre',
      etiqueta: padre.definicion.nombre,
      widget: widgetPorDefecto({ clase: 'lista', opciones: recuentoDe(hermanas) }),
      opciones: hermanas.map((f) => ({ valor: f.codigo, etiqueta: etiquetaDe(f) })),
      elegida: codigoPadre,
    });
    if (activas.length === 0) return campos;
  }
  campos.push({
    id: 'previa-lista',
    etiqueta: nombre,
    widget: widgetPorDefecto({ clase: 'lista', opciones: recuentoDe(activas) }),
    opciones: activas.map((o) => ({ valor: o.codigo, etiqueta: o.etiqueta })),
    elegida: padre ? null : (activas[0]?.codigo ?? null),
  });
  return campos;
}

export function construirLista(datos: DatosDeLista): ListaVM {
  const { definicion: d, filas } = datos.valores;
  const a = datos.ambito;
  const origen = ambitoDeLista(filas, a);
  const modo: ModoDeLista = origen === null ? 'vacia' : mismoAmbito(origen, a) ? 'propia' : 'heredada';
  const puedeEditar = puedeEditarEn(datos.capacidades, a);

  // La cascada: los padres son las opciones activas de la lista madre en ESTE ámbito.
  const padresOpciones = datos.padre ? listaResuelta(datos.padre.filas, a) : [];
  const ambitoDeLasFilas = origen ?? a;
  const padres: PadreVM[] | null = datos.padre
    ? padresOpciones.map((p) => {
        const hijasActivas = filasOrdenadas(filas, ambitoDeLasFilas, p.codigo).filter((f) => f.activo);
        return { codigo: p.codigo, etiqueta: etiquetaDe(p), cuantas: recuentoDe(hijasActivas) };
      })
    : null;
  const elegidoPedido = datos.padreElegido ?? null;
  const padreElegido = padres ? ((padres.find((p) => p.codigo === elegidoPedido) ?? padres[0])?.codigo ?? null) : null;
  const etiquetaDelPadre = padres?.find((p) => p.codigo === padreElegido)?.etiqueta ?? '';

  const delPadre = padreElegido ?? TODO;
  const visibles = filasOrdenadas(filas, ambitoDeLasFilas, delPadre);
  const opciones: OpcionVM[] = visibles.map((f, i) => ({
    clave: claveDe(f),
    codigo: f.codigo,
    etiqueta: etiquetaDe(f),
    ayuda: f.ayuda ?? '',
    activa: f.activo,
    posicion: POSICIONES[i] ?? '',
    puedeSubir: i > 0,
    puedeBajar: i < visibles.length - 1,
  }));

  const activas = opciones.filter((o) => o.activa);
  const procesoDeActividades = a.proceso !== TODO && a.actividad === TODO ? a.proceso : null;
  const declaradas = procesoDeActividades ? (datos.procesos.find((p) => p.proceso === procesoDeActividades)?.actividades ?? []) : [];
  const propias = procesoDeActividades ? actividadesConVersionPropia(filas, procesoDeActividades) : [];
  const actividades: AmbitoHijo[] = procesoDeActividades
    ? [...new Set([...declaradas, ...propias])].filter((act) => propias.includes(act) || !esNodoTecnico(act)).map((act) => ({
        ambito: { proceso: procesoDeActividades, actividad: act },
        nombre: nombreDeActividad(act),
        propia: propias.includes(act),
      }))
    : [];

  const procedencia =
    modo === 'heredada'
      ? T.CHIP_HEREDADA
      : esGlobal(a)
        ? T.LISTA_GLOBAL
        : a.actividad === TODO
          ? T.LISTA_DEL_PROCESO
          : T.LISTA_PROPIA_DE_LA_ACTIVIDAD;

  const sinFilasPropias = filasEn(filas, a).length === 0;
  const nuevas = modo === 'propia' ? opcionesNuevasDelOrigen(filas, a) : [];
  return {
    codigo: d.codigo,
    nombre: d.nombre,
    descripcion: d.descripcion ?? '',
    impactoAlto: d.impacto === 'ALTO',
    ambito: a,
    migas: migasDe(a),
    modo,
    procedencia,
    heredaDe: origen && modo === 'heredada' ? [nombreDeProceso(origen.proceso), origen.actividad === TODO ? 'todo el proceso' : nombreDeActividad(origen.actividad)].join(' · ') : '',
    puedeEditar,
    puedeCrearVersionPropia: puedeEditar && modo === 'heredada' && !esGlobal(a),
    puedeVolverAHeredar: puedeEditar && modo === 'propia' && !esGlobal(a) && !sinFilasPropias,
    padres,
    padreElegido,
    opciones,
    total: recuentoDe(opciones),
    activas: recuentoDe(activas),
    sinHijas: padres !== null && padreElegido !== null && activas.length === 0,
    etiquetaDelPadre,
    huerfanas: huerfanos(filas, ambitoDeLasFilas, padresOpciones.map((p) => p.codigo)).map((f) => ({
      etiqueta: etiquetaDe(f),
      padre: f.codigoPadre,
    })),
    nuevasDelOrigen: recuentoDe(nuevas),
    actividades,
    vistaPrevia: vistaPreviaDe(d.nombre, padreElegido, datos, opciones),
    quienEdita: quienEditaLegible(datos.editores, datos.nombres),
    definicion: [
      { rotulo: T.ROTULO_CODIGO, valor: d.codigo, codigo: true },
      { rotulo: T.ROTULO_TIPO, valor: d.clase === 'LISTA' ? T.TIPO_LISTA : T.TIPO_PARAMETRO },
      { rotulo: T.ROTULO_IMPACTO, valor: d.impacto === 'ALTO' ? T.IMPACTO_ALTO_DOBLE_CONTROL : T.IMPACTO_NORMAL },
      { rotulo: T.ROTULO_ORIGEN, valor: d.origen === 'SEMILLA' ? T.LLEGO_CON_EL_PROCESO : T.CREADA_EN_LA_APLICACION },
    ],
  };
}
