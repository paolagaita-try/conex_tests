/**
 * El modelo de un PARÁMETRO en un ámbito (pantallas `p05-parametro*`): qué valor rige aquí y de
 * dónde viene (la cadena de herencia), qué se puede cambiar, si hay un cambio esperando aprobación y qué
 * otra persona propuso antes. Lógica pura sobre datos CRUDOS; devuelve un modelo sin números sueltos.
 */
import { recuentoDe, type Recuento } from '$lib/bonita/marcas';
import { type Ambito, esGlobal, filasEn, listaResuelta, parametroResuelto } from './ambitos';
import { puedeEditarEn, type Capacidades } from './capacidades';
import { cuando, simboloDeMoneda, valorLegible, valorParaEditar } from './formatos';
import { etiquetaDe, migasDe, quienEditaLegible, type MigaDeAmbito } from './lista';
import { nombreDeActividad, nombreDeProceso } from './nombres';
import * as T from './textos';
import { rangoLegible } from './valores';
import { TODO, type Editor, type Fila, type Propuesta, type Proceso, type ValoresAdministracion } from './tipos';

export interface NodoDeHerencia {
  clave: string;
  donde: string;
  cuanto: string;
  nota: string;
  estado: 'base' | 'aplica' | 'hereda';
  ambito: Ambito | null;
}

export interface PendienteVM {
  /** Lo que se propuso, con su unidad. */
  propuesto: string;
  actual: string;
  /** Nombre para mostrar de quien lo propuso. */
  quien: string;
  cuando: string;
  motivo: string;
  esPropia: boolean;
}

export interface PadreDeParametro {
  codigo: string;
  etiqueta: string;
  valor: string;
}

export interface ParametroVM {
  codigo: string;
  nombre: string;
  descripcion: string;
  impactoAlto: boolean;
  ambito: Ambito;
  migas: MigaDeAmbito[];
  procedencia: string;
  cadena: NodoDeHerencia[];
  /** El valor vigente que rige aquí, con su unidad («35 %»). */
  vigente: string;
  /** El valor propio de este ámbito para editar (sin unidad); vacío si hereda. */
  paraEditar: string;
  /** El tipo de dato, para elegir el control. */
  tipoDato: string;
  /** Delante o detrás del número: «US$» antes, «%» o «meses» después. */
  prefijo: string;
  sufijo: string;
  rango: string;
  puedeEditar: boolean;
  /** Hay una propuesta pendiente: el valor no se edita hasta que se apruebe, rechace o retire. */
  pendiente: PendienteVM | null;
  padres: PadreDeParametro[] | null;
  padreElegido: string | null;
  etiquetaDelPadre: string;
  quienEdita: string[];
  definicion: Array<{ rotulo: string; valor: string; codigo?: boolean }>;
  /** Cuántos ámbitos más del proceso heredan este valor. */
  heredanDelProceso: Recuento;
}

export interface DatosDeParametro {
  valores: ValoresAdministracion;
  padre: ValoresAdministracion | null;
  ambito: Ambito;
  procesos: Proceso[];
  capacidades: Capacidades;
  editores: Editor[];
  pendientes: Propuesta[];
  nombres: Record<string, string>;
  padreElegido?: string | null;
  ahora?: Date;
}

const unidadesDe = (tipo: string, unidad: string | null): { prefijo: string; sufijo: string } => {
  if (tipo === 'MONTO') return { prefijo: simboloDeMoneda(unidad), sufijo: '' };
  if (tipo === 'PORCENTAJE') return { prefijo: '', sufijo: unidad ?? '%' };
  return { prefijo: '', sufijo: unidad ?? '' };
};

export function pendienteDe(todas: Propuesta[], definicion: string, a: Ambito, padre: string): Propuesta | null {
  return (
    todas.find(
      (p) => p.estado === 'PENDIENTE' && p.definicion === definicion && p.proceso === a.proceso && p.actividad === a.actividad && p.codigoPadre === padre,
    ) ?? null
  );
}

export function construirParametro(datos: DatosDeParametro): ParametroVM {
  const { definicion: d, filas } = datos.valores;
  const a = datos.ambito;
  const ahora = datos.ahora ?? new Date();

  const padresOpciones = datos.padre ? listaResuelta(datos.padre.filas, a) : [];
  const delPadre = datos.padre ? (padresOpciones.find((p) => p.codigo === datos.padreElegido) ?? padresOpciones[0])?.codigo ?? null : null;
  const padreCodigo = delPadre ?? TODO;
  const etiquetaDelPadre = padresOpciones.find((p) => p.codigo === padreCodigo)?.etiqueta ?? '';

  const resuelto = parametroResuelto(filas, a, padreCodigo);
  const propia = filasEn(filas, a).find((f) => f.codigoPadre === padreCodigo && f.activo) ?? null;
  const pend = pendienteDe(datos.pendientes, d.codigo, a, padreCodigo);

  // La cadena: de lo más general a lo más específico, con lo que rige en cada punto.
  const nodos: NodoDeHerencia[] = [];
  const valorEn = (ambito: Ambito): Fila | undefined => filasEn(filas, ambito).find((f) => f.codigoPadre === padreCodigo && f.activo);
  const global = valorEn({ proceso: TODO, actividad: TODO });
  if (global || esGlobal(a)) {
    nodos.push({
      clave: 'global',
      donde: T.GLOBAL,
      cuanto: valorLegible(d, global?.valor ?? null),
      nota: T.VALOR_BASE_DE_LA_ORGANIZACION,
      estado: esGlobal(a) ? 'aplica' : 'base',
      ambito: { proceso: TODO, actividad: TODO },
    });
  }
  if (a.proceso !== TODO) {
    const delProceso = valorEn({ proceso: a.proceso, actividad: TODO });
    const esEste = a.actividad === TODO;
    nodos.push({
      clave: 'proceso',
      donde: nombreDeProceso(a.proceso),
      cuanto: valorLegible(d, (delProceso ?? global)?.valor ?? null),
      nota: esEste ? (pend ? T.aplicaAquiPorAprobar(valorLegible(d, valorPropuesto(pend))) : T.APLICA_AQUI_LO_EDITAS_AHORA) : delProceso ? T.VALOR_DEL_PROCESO : T.HEREDA_DEL_GLOBAL,
      estado: esEste ? 'aplica' : delProceso ? 'base' : 'hereda',
      ambito: { proceso: a.proceso, actividad: TODO },
    });
  }
  if (a.proceso !== TODO && a.actividad !== TODO) {
    nodos.push({
      clave: 'actividad',
      donde: nombreDeActividad(a.actividad),
      cuanto: valorLegible(d, resuelto?.fila.valor ?? null),
      nota: propia ? (pend ? T.aplicaAquiPorAprobar(valorLegible(d, valorPropuesto(pend))) : T.APLICA_AQUI_LO_EDITAS_AHORA) : T.HEREDA_DEL_PROCESO,
      estado: propia ? 'aplica' : 'hereda',
      ambito: a,
    });
  }
  // Lo que hereda del ámbito actual: las actividades del proceso sin valor propio.
  const hijas =
    a.proceso !== TODO && a.actividad === TODO
      ? (datos.procesos.find((p) => p.proceso === a.proceso)?.actividades ?? []).filter(
          (act) => !filas.some((f) => f.proceso === a.proceso && f.actividad === act && f.codigoPadre === padreCodigo && f.activo),
        )
      : [];
  if (hijas.length > 0) {
    nodos.push({
      clave: 'hereda',
      donde: hijas.slice(0, 2).map(nombreDeActividad).join(', '),
      cuanto: valorLegible(d, resuelto?.fila.valor ?? null),
      nota: T.HEREDAN_DEL_PROCESO,
      estado: 'hereda',
      ambito: null,
    });
  }

  const { prefijo, sufijo } = unidadesDe(d.tipoDato, d.unidad);
  const quien = pend ? (datos.nombres[pend.proponente] ?? pend.proponente) : '';
  const procedencia = propia
    ? esGlobal(a)
      ? T.VALOR_GLOBAL
      : a.actividad === TODO
        ? T.VALOR_PROPIO_DEL_PROCESO
        : T.VALOR_PROPIO_DE_LA_ACTIVIDAD
    : T.HEREDADO;

  return {
    codigo: d.codigo,
    nombre: d.nombre,
    descripcion: d.descripcion ?? '',
    impactoAlto: d.impacto === 'ALTO',
    ambito: a,
    migas: migasDe(a),
    procedencia,
    cadena: nodos,
    vigente: valorLegible(d, resuelto?.fila.valor ?? null),
    paraEditar: propia ? valorParaEditar(propia.valor) : '',
    tipoDato: d.tipoDato,
    prefijo,
    sufijo,
    rango: rangoLegible(d),
    puedeEditar: puedeEditarEn(datos.capacidades, a),
    pendiente: pend
      ? {
          propuesto: valorLegible(d, valorPropuesto(pend)),
          actual: valorLegible(d, resuelto?.fila.valor ?? null),
          quien,
          cuando: cuando(pend.creadaEn, ahora),
          motivo: pend.motivo,
          esPropia: pend.esPropia,
        }
      : null,
    padres: datos.padre
      ? padresOpciones.map((p) => ({
          codigo: p.codigo,
          etiqueta: etiquetaDe(p),
          valor: valorLegible(d, parametroResuelto(filas, a, p.codigo)?.fila.valor ?? null),
        }))
      : null,
    padreElegido: delPadre,
    etiquetaDelPadre,
    quienEdita: quienEditaLegible(datos.editores, datos.nombres),
    definicion: [
      { rotulo: T.ROTULO_CODIGO, valor: d.codigo, codigo: true },
      { rotulo: T.ROTULO_TIPO, valor: tipoLegible(d.tipoDato) },
      ...(rangoSimple(d) ? [{ rotulo: T.ROTULO_RANGO, valor: rangoSimple(d) }] : []),
      { rotulo: T.ROTULO_IMPACTO, valor: d.impacto === 'ALTO' ? T.IMPACTO_ALTO_DOBLE_CONTROL : T.IMPACTO_NORMAL },
    ],
    heredanDelProceso: recuentoDe(hijas),
  };
}

/** El valor que propone una propuesta (`datos.valor` de la operación guardada). */
export function valorPropuesto(p: Propuesta): string | null {
  const v = p.valorPropuesto.datos.valor;
  return typeof v === 'string' ? v : null;
}

const TIPOS: Record<string, string> = {
  TEXTO: 'Texto',
  ENTERO: 'Número entero',
  DECIMAL: 'Número',
  PORCENTAJE: 'Porcentaje',
  MONTO: 'Monto',
  FECHA: 'Fecha',
  BOOLEANO: 'Sí o no',
};
const tipoLegible = (t: string): string => TIPOS[t] ?? t;

function rangoSimple(d: ValoresAdministracion['definicion']): string {
  if (d.minimo === null && d.maximo === null) return '';
  const a = valorLegible(d, d.minimo);
  const b = valorLegible(d, d.maximo);
  return d.minimo !== null && d.maximo !== null ? `${a} – ${b}` : d.minimo !== null ? `desde ${a}` : `hasta ${b}`;
}

