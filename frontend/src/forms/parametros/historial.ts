/**
 * La traza, contada en lenguaje de negocio (pantallas `p04` y `p09`):
 * cada eslabón de la cadena —quién, cuándo, qué, antes → después y motivo— como una frase que lee
 * quien audita, sin JSON, sin identificadores y sin la huella (que se verifica, no se lee).
 *
 * El eslabón guarda la FILA completa antes y después (`valorAnterior`, `valorNuevo`), así que la frase
 * se compone comparando las dos. Una acción que este módulo no conoce se cuenta con un verbo genérico
 * («hizo un cambio»), nunca se esconde: una entrada de la traza que no se lee no existe para el auditor.
 */
import { cuandoCompleto, valorLegible } from './formatos';
import { sujetoDeDelegacion, type SujetosPorId } from './aprobaciones';
import { nombreDeActividad, nombreDeProceso, nombresUnicos } from './nombres';
import * as T from './textos';
import { TODO, type Definicion, type EntradaDeTraza } from './tipos';

export type Parte =
  | { t: 'texto'; texto: string }
  | { t: 'fuerte'; texto: string }
  | { t: 'cambio'; antes: string; despues: string }
  | { t: 'chip'; tono: 'neutro' | 'marca' | 'exito' | 'atencion' | 'error'; texto: string };

export interface EventoVM {
  clave: string;
  /** El instante, ISO, para el atributo `datetime`. */
  cuandoIso: string;
  cuando: string;
  /** Nombre para mostrar de quien lo hizo. */
  quien: string;
  /** Quién lo hizo, por su usuario (la identidad: dos personas se pueden llamar igual). */
  usuario: string;
  partes: Parte[];
  motivo: string;
  /** «desde la pantalla», «por importación», «al desplegar el proceso». */
  origen: string;
  /** Lo que el filtro «Acción» de la traza distingue. */
  categoria: CategoriaDeAccion;
  /** Para filtrar por lista o parámetro. */
  nombreDeLaDefinicion: string;
  /** La frase empieza por quién (casi siempre); «La definición llegó con el proceso…» no. */
  conQuien: boolean;
  /** Texto plano de la frase, para exportar. */
  texto: string;
  /** El cambio en texto plano («35 % → 30 %»), para exportar. */
  cambio: string;
}

export type CategoriaDeAccion = 'cambios' | 'aprobaciones' | 'permisos' | 'rechazados' | 'importaciones' | 'otros';

export interface ContextoDeHistorial {
  nombres: Record<string, string>;
  definiciones: Definicion[];
  /** Quién es cada id de persona, grupo o rol (solo la superadministración los puede buscar). */
  sujetos?: SujetosPorId;
}

type Obj = Record<string, unknown>;
const esObjeto = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);
const texto = (v: unknown): string => (typeof v === 'string' ? v : '');

/** Las filas que guarda un eslabón: una lista de filas, una fila, o `{ filas: [...] }` (al aprobar). */
export function filasDe(v: unknown): Obj[] {
  if (Array.isArray(v)) return v.filter(esObjeto);
  if (esObjeto(v)) {
    if (Array.isArray(v.filas)) return v.filas.filter(esObjeto);
    // Al aprobar, el kit real guarda `filas` como UN objeto (la fila aplicada), no como lista.
    if (esObjeto(v.filas)) return [v.filas];
    return [v];
  }
  return [];
}

const CATEGORIAS: Record<string, CategoriaDeAccion> = {
  CREAR: 'cambios',
  EDITAR: 'cambios',
  DESACTIVAR: 'cambios',
  REACTIVAR: 'cambios',
  ORDENAR: 'cambios',
  CREAR_VERSION_PROPIA: 'cambios',
  VOLVER_A_HEREDAR: 'cambios',
  CREAR_DEFINICION: 'cambios',
  EDITAR_DEFINICION: 'cambios',
  PROPONER: 'cambios',
  APROBAR: 'aprobaciones',
  RECHAZAR: 'aprobaciones',
  RETIRAR: 'aprobaciones',
  DELEGAR: 'permisos',
  REVOCAR: 'permisos',
  IMPORTAR: 'importaciones',
};

export const categoriaDe = (accion: string): CategoriaDeAccion => CATEGORIAS[accion] ?? 'otros';

/** «porcentaje_beca|Proceso|*|*|*» → sus cinco partes. */
export function partesDeLaClave(clave: string): { definicion: string; proceso: string; actividad: string; padre: string; codigo: string } {
  const [definicion = '', proceso = TODO, actividad = TODO, padre = TODO, codigo = TODO] = clave.split('|');
  return { definicion, proceso, actividad, padre, codigo };
}

function ambitoLegible(proceso: string, actividad: string): string {
  if (proceso === TODO) return T.GLOBAL.toLowerCase();
  if (actividad === TODO) return `${nombreDeProceso(proceso)}`;
  return nombreDeActividad(actividad);
}

const ORIGENES: Record<string, string> = {
  PANTALLA: T.ORIGEN_PANTALLA,
  CSV: T.ORIGEN_CSV,
  SEMILLA: T.ORIGEN_SEMILLA,
  RESTABLECIMIENTO: T.ORIGEN_RESTABLECIMIENTO,
};

function nombreDeFila(f: Obj | undefined): string {
  return texto(f?.etiqueta) || texto(f?.codigo);
}

/** La delegación de una entrada, en cualquiera de las formas en que el kit la guarda: la fila (`filas`, o la fila sola), la propuesta (`valorPropuesto.datos`) o la clave. */
export function datosDeDelegacion(e: EntradaDeTraza): Obj | null {
  const nuevo = esObjeto(e.valorNuevo) ? e.valorNuevo : {};
  const anterior = esObjeto(e.valorAnterior) ? e.valorAnterior : {};
  const deLaPropuesta = (v: Obj): Obj | null => (esObjeto(v.valorPropuesto) && esObjeto(v.valorPropuesto.datos) ? (v.valorPropuesto.datos as Obj) : null);
  const candidatos: unknown[] = [esObjeto(nuevo.filas) ? nuevo.filas : null, deLaPropuesta(nuevo), deLaPropuesta(anterior), filasDe(e.valorNuevo)[0], filasDe(e.valorAnterior)[0]];
  return (candidatos.find((c) => esObjeto(c) && typeof c.tipoSujeto === 'string') as Obj | undefined) ?? null;
}

/** Los datos de delegación de varias entradas (las que no hablan de una se omiten). */
export const delegacionesDe = (entradas: readonly EntradaDeTraza[]): Obj[] => entradas.flatMap((e) => { const d = datosDeDelegacion(e); return d ? [d] : []; });

/** ¿La entrada habla de una delegación? Por la clave, por la acción o por la propuesta que se decide (RECHAZAR/RETIRAR llevan la clave `*|proceso|…`). */
function esDelegacion(e: EntradaDeTraza, definicion: string): boolean {
  if (definicion === 'delegacion' || e.accion === 'DELEGAR' || e.accion === 'REVOCAR') return true;
  const propuesta = (v: unknown): boolean => esObjeto(v) && (v.accion === 'DELEGAR' || (esObjeto(v.propuesta) && v.propuesta.accion === 'DELEGAR'));
  return propuesta(e.valorNuevo) || propuesta(e.valorAnterior);
}

/** A quién nombra una entrada: quien la hizo y, al aprobar, quien propuso. Hay que resolver sus nombres antes de pintarla. */
export function usuariosDeLaEntrada(e: EntradaDeTraza): string[] {
  const propuesta = esObjeto(e.valorNuevo) && esObjeto(e.valorNuevo.propuesta) ? texto((e.valorNuevo.propuesta as Obj).proponente) : '';
  return [e.usuario, propuesta].filter((u) => u !== '');
}

const aMinuscula = (s: string): string => (/^(Una? |Un )/.test(s) ? s.charAt(0).toLowerCase() + s.slice(1) : s);

export function eventoDeTraza(e: EntradaDeTraza, contexto: ContextoDeHistorial): EventoVM {
  const ctx = { ...contexto, nombres: nombresUnicos(contexto.nombres) };
  const k = partesDeLaClave(e.claveNegocio);
  const def = ctx.definiciones.find((d) => d.codigo === k.definicion);
  const deleg = esDelegacion(e, k.definicion);
  // Ni el código interno ni «delegacion» se cuentan nunca: una delegación es «Permisos»; lo que el catálogo no conoce, «una definición».
  const nombreDef = deleg ? T.hist.permisos : (def?.nombre ?? T.UNA_DEFINICION);
  const quien = e.origen === 'SEMILLA' || e.origen === 'RESTABLECIMIENTO' ? T.SISTEMA : (ctx.nombres[e.usuario] ?? e.usuario);
  const antes = filasDe(e.valorAnterior)[0];
  const despues = filasDe(e.valorNuevo)[0];
  const valor = (v: unknown): string => (def ? valorLegible(def, typeof v === 'string' ? v : null) : texto(v));
  const lista = def?.clase === 'LISTA';
  const donde = ambitoLegible(k.proceso, k.actividad);
  const partes: Parte[] = [];
  const dice = (s: string) => partes.push({ t: 'texto', texto: s });
  const fuerte = (s: string) => partes.push({ t: 'fuerte', texto: s });
  const cambio = (a: string, d: string) => partes.push({ t: 'cambio', antes: a, despues: d });
  let planoDelCambio = '';

  if (deleg) {
    // Una delegación se cuenta igual venga como venga: fila, propuesta o clave (nunca ids ni `|`).
    const d = datosDeDelegacion(e);
    const sujetos = ctx.sujetos ?? { usuario: [], grupo: [], rol: [] };
    const sujeto = d ? aMinuscula(sujetoDeDelegacion(d, sujetos)) : T.hist.unaPersona;
    const propuesta = esObjeto(e.valorNuevo) && esObjeto(e.valorNuevo.propuesta) ? (e.valorNuevo.propuesta as Obj) : {};
    const proceso = texto(d?.proceso) || (esObjeto(e.valorNuevo) && esObjeto(e.valorNuevo.valorPropuesto) ? texto((e.valorNuevo.valorPropuesto as Obj).proceso) : '') || (esObjeto(e.valorAnterior) && esObjeto(e.valorAnterior.valorPropuesto) ? texto((e.valorAnterior.valorPropuesto as Obj).proceso) : '');
    const verbo: Record<string, string> = {
      PROPONER: T.hist.propusoDelegar,
      APROBAR: T.hist.aproboDelegar,
      RECHAZAR: T.hist.rechazoDelegar,
      RETIRAR: T.hist.retiroDelegar,
      DELEGAR: T.hist.delego,
      REVOCAR: T.hist.revoco,
    };
    dice(verbo[e.accion] ?? T.hist.hizoUnCambio);
    fuerte(T.hist.permisos);
    dice(` · ${sujeto}`);
    if (proceso !== '' && proceso !== TODO) dice(` → ${nombreDeProceso(proceso)}`);
    const proponente = texto(propuesta.proponente);
    if (e.accion === 'APROBAR' && proponente) dice(`, ${T.hist.propuestoPor(ctx.nombres[proponente] ?? T.UNA_PERSONA.toLowerCase())}`);
    dice('.');
    if (e.accion === 'PROPONER') partes.push({ t: 'chip', tono: 'marca', texto: T.CHIP_POR_APROBAR });
  } else switch (e.accion) {
    case 'CREAR_DEFINICION':
      dice(T.hist.creoLaDefinicion);
      fuerte(`«${nombreDef}»`);
      dice('.');
      break;
    case 'CREAR':
      dice(lista ? T.hist.anadioLaOpcion : T.hist.fijoElValor(nombreDef));
      if (lista) fuerte(`«${nombreDeFila(despues)}»`);
      else fuerte(valor(despues?.valor));
      dice(`${T.hist.en} ${donde}.`);
      break;
    case 'EDITAR': {
      const etiquetaCambia = texto(antes?.etiqueta) !== texto(despues?.etiqueta) && texto(despues?.etiqueta) !== '';
      const valorCambia = texto(antes?.valor) !== texto(despues?.valor);
      if (lista && etiquetaCambia) {
        dice(T.hist.cambioElNombre);
        cambio(texto(antes?.etiqueta), texto(despues?.etiqueta));
        planoDelCambio = `${texto(antes?.etiqueta)} → ${texto(despues?.etiqueta)}`;
      } else if (valorCambia) {
        dice(T.hist.cambioElValorDe);
        fuerte(`«${nombreDef}»`);
        dice(':');
        cambio(valor(antes?.valor), valor(despues?.valor));
        planoDelCambio = `${valor(antes?.valor)} → ${valor(despues?.valor)}`;
      } else {
        dice(T.hist.edito);
        fuerte(`«${nombreDeFila(despues) || nombreDef}»`);
        dice('.');
      }
      break;
    }
    case 'DESACTIVAR':
      dice(T.hist.desactivo);
      fuerte(`«${nombreDeFila(despues) || nombreDeFila(antes) || nombreDef}»`);
      dice('.');
      break;
    case 'REACTIVAR':
      dice(T.hist.reactivo);
      fuerte(`«${nombreDeFila(despues) || nombreDeFila(antes) || nombreDef}»`);
      dice('.');
      break;
    case 'ORDENAR':
      dice(T.hist.cambioElOrdenDe);
      fuerte(`«${nombreDef}»`);
      dice('.');
      break;
    case 'CREAR_VERSION_PROPIA':
      dice(T.hist.creoUnaVersionPropia);
      fuerte(`«${nombreDef}»`);
      dice(`${T.hist.para} `);
      fuerte(donde);
      dice(`${T.hist.aPartirDeLaListaDelProceso}.`);
      break;
    case 'VOLVER_A_HEREDAR':
      dice(T.hist.volvioAHeredar);
      fuerte(`«${nombreDef}»`);
      dice(`${T.hist.en} ${donde}.`);
      break;
    case 'EDITAR_DEFINICION':
      dice(T.hist.cambioLaDefinicionDe);
      fuerte(`«${nombreDef}»`);
      dice('.');
      break;
    case 'PROPONER': {
      const op = esObjeto(despues?.valorPropuesto) ? (despues?.valorPropuesto as Obj) : undefined;
      const datos = esObjeto(op?.datos) ? (op?.datos as Obj) : undefined;
      dice(T.hist.propusoCambiar);
      fuerte(`«${nombreDef}»`);
      if (datos && 'valor' in datos) {
        dice(':');
        cambio(valor(antes?.valor), valor(datos.valor));
        planoDelCambio = `${valor(antes?.valor)} → ${valor(datos.valor)}`;
      } else dice('.');
      partes.push({ t: 'chip', tono: 'marca', texto: T.CHIP_POR_APROBAR });
      break;
    }
    case 'APROBAR': {
      const firmas = esObjeto(e.valorNuevo) && esObjeto(e.valorNuevo.propuesta) ? (e.valorNuevo.propuesta as Obj) : {};
      const proponente = texto(firmas.proponente);
      dice(T.hist.aprobo);
      fuerte(`«${nombreDef}»`);
      if (despues && antes && texto(antes.valor) !== texto(despues.valor)) {
        dice(':');
        cambio(valor(antes.valor), valor(despues.valor));
        planoDelCambio = `${valor(antes.valor)} → ${valor(despues.valor)}`;
      }
      if (proponente) dice(` ${T.hist.propuestoPor(ctx.nombres[proponente] ?? proponente)}.`);
      else dice('.');
      break;
    }
    case 'RECHAZAR':
      dice(T.hist.rechazo);
      fuerte(`«${nombreDef}»`);
      dice('.');
      break;
    case 'RETIRAR':
      dice(T.hist.retiro);
      fuerte(`«${nombreDef}»`);
      dice('.');
      break;
    case 'IMPORTAR':
      dice(T.hist.importo);
      fuerte(`«${nombreDef === '*' || nombreDef === '' ? T.hist.variasListas : nombreDef}»`);
      if (e.lote) dice(` (${e.lote}).`);
      else dice('.');
      break;
    case 'SEMILLA':
      dice(T.hist.llegoConElProceso);
      fuerte(nombreDeProceso(k.proceso));
      dice('.');
      partes.push({ t: 'chip', tono: 'neutro', texto: T.CHIP_SEMILLA });
      break;
    case 'RESTABLECER_SEMILLA':
      dice(T.hist.restablecio);
      break;
    default:
      dice(T.hist.hizoUnCambio);
      fuerte(`«${nombreDef}»`);
      dice('.');
  }

  // Un texto pegado a lo siguiente no se lee («propuso cambiar«x»»): se separa salvo ante puntuación.
  partes.forEach((p, i) => {
    const sig = partes[i + 1];
    if ((p.t !== 'texto' && p.t !== 'fuerte') || !sig || (sig.t !== 'texto' && sig.t !== 'fuerte')) return;
    if (/\s$/.test(p.texto) || /^[\s.,:;]/.test(sig.texto)) return;
    p.texto += ' ';
  });
  const plano = partes
    .map((p) => (p.t === 'cambio' ? `${p.antes} → ${p.despues}` : p.t === 'chip' ? ` [${p.texto}]` : p.texto))
    .join('')
    .replace(/\s+([.,:])/g, '$1')
    .replace(/\s{2,}/g, ' ');
  return {
    clave: [e.hash, e.fechaHora, e.claveNegocio].join('@'),
    cuandoIso: e.fechaHora,
    cuando: cuandoCompleto(e.fechaHora),
    quien,
    usuario: e.usuario,
    partes,
    motivo: e.motivo,
    origen: ORIGENES[e.origen] ?? '',
    categoria: categoriaDe(e.accion),
    nombreDeLaDefinicion: nombreDef,
    conQuien: e.accion !== 'SEMILLA' && e.accion !== 'RESTABLECER_SEMILLA',
    texto: plano,
    cambio: planoDelCambio,
  };
}

export type Periodo = 'noventa' | 'anio' | 'todo';

const DIA_EN_MS = 24 * 60 * 60 * 1000;
const NOVENTA_DIAS_EN_MS = 90 * DIA_EN_MS;

/** Solo lo de un periodo, medido contra `ahora`. Una fecha ilegible se conserva: nunca se esconde una entrada. */
export function dentroDelPeriodo(e: EventoVM, periodo: Periodo, ahora: Date): boolean {
  if (periodo === 'todo') return true;
  const cuando = new Date(e.cuandoIso);
  if (Number.isNaN(cuando.getTime())) return true;
  if (periodo === 'anio') return cuando.getFullYear() === ahora.getFullYear();
  return ahora.getTime() - cuando.getTime() <= NOVENTA_DIAS_EN_MS;
}
