/**
 * El modelo del inicio: lo que la persona puede ajustar, agrupado por ámbito.
 *
 * Es lógica pura: recibe lo que la API devolvió (datos CRUDOS, con versiones y números) y devuelve
 * grupos y filas ya decididos y ya escritos en lenguaje de negocio (a qué grupo pertenece cada lista o
 * parámetro, si es de solo lectura, si tiene un cambio por aprobar). La vista solo pinta.
 *
 * **Regla de la aplicación (auditoría del origen de las cifras): a un componente nunca llega un
 * objeto que lleve un `number` suelto** (`persistenceVersion`, `decimales`, `orden`…): lo pintaría él.
 * Las vistas reciben estos modelos —texto, sí/no y recuentos marcados— y devuelven CLAVES; quien guarda
 * los datos crudos y sus versiones es el contenedor.
 */
import { recuentoDe, type Recuento } from '$lib/bonita/marcas';
import { type Ambito, esGlobal, filasEn, GLOBAL } from './ambitos';
import { puedeEditarEn, type Capacidades } from './capacidades';
import { cuando, paraBuscar, valorLegible } from './formatos';
import { nombreDeActividad, nombreDeProceso } from './nombres';
import * as T from './textos';
import { TODO, type Clase, type Definicion, type Fila, type Propuesta, type Proceso, type ValoresAdministracion } from './tipos';

export type FiltroDeTipo = 'todo' | 'listas' | 'parametros' | 'editable';

export interface UltimoCambio {
  /** Nombre para mostrar de quien lo hizo. */
  usuario: string;
  fechaHora: string;
}

/** Los datos crudos del inicio: lo que devolvió el kit. */
export interface DatosDelInicio {
  definiciones: Definicion[];
  valores: Record<string, ValoresAdministracion>;
  procesos: Proceso[];
  pendientes: Propuesta[];
  ultimos: Record<string, UltimoCambio>;
}

/** Una fila del inicio, ya escrita para leerse. Sin números sueltos. */
export interface FilaDeInicio {
  /** Identidad estable: definición y ámbito. */
  clave: string;
  codigo: string;
  nombre: string;
  ambito: Ambito;
  clase: Clase;
  impactoAlto: boolean;
  /** «Lista», «Lista en cascada de Sedes», «Parámetro». */
  tipo: string;
  /** «3 opciones», «4 opciones, 1 inactiva», «35 %». */
  contenido: string;
  /** «Aulas»: las listas que dependen de esta, o vacío. */
  dependientes: string;
  /** «Marta Rivas, 12 ago», o vacío. */
  ultimo: string;
  porAprobar: boolean;
  /** En cuántas actividades hay versión propia (solo en el ámbito del proceso). */
  conVersionPropia: Recuento;
  soloLectura: boolean;
}

export interface GrupoDeInicio {
  clave: string;
  ambito: Ambito;
  titulo: string;
  /** El proceso no tiene ninguna lista ni parámetro todavía. */
  sinParametros: boolean;
  /** La persona puede editar en este ámbito. */
  editable: boolean;
  filas: FilaDeInicio[];
}

export interface Inicio {
  grupos: GrupoDeInicio[];
  /** Cuántas filas se ven con el filtro y la búsqueda actuales. */
  visibles: Recuento;
  /** Cuántas hay en total, sin filtro: distingue «nada coincide» de «todavía no hay nada». */
  total: Recuento;
}

const claveDe = (codigo: string, a: Ambito) => [codigo, a.proceso, a.actividad].join('|');

export function tituloDelGrupo(a: Ambito, perfil: Capacidades['perfil']): string {
  if (esGlobal(a)) {
    if (perfil === 'delegado') return T.GRUPO_GLOBALES_SOLO_LECTURA;
    return perfil === 'consulta' ? T.GRUPO_GLOBALES_CONSULTA : T.GRUPO_GLOBALES;
  }
  if (a.actividad === TODO) return [nombreDeProceso(a.proceso), 'todo el proceso'].join(' · ');
  return [nombreDeProceso(a.proceso), nombreDeActividad(a.actividad)].join(' · ');
}

function tipoDe(d: Definicion, padre: Definicion | undefined): string {
  if (d.clase === 'LISTA') return padre ? T.tipoListaEnCascada(padre.nombre) : T.TIPO_LISTA;
  return padre ? T.tipoParametroPorPadre(padre.nombre) : T.TIPO_PARAMETRO;
}

function filaDe(
  d: Definicion,
  a: Ambito,
  datos: DatosDelInicio,
  filas: Fila[],
  capacidades: Capacidades,
  porCodigo: Record<string, Definicion>,
  ahora: Date,
): FilaDeInicio {
  const propias = filasEn(filas, a);
  const activas = propias.filter((f) => f.activo);
  const inactivas = propias.filter((f) => !f.activo);
  const conPadre = propias.filter((f) => f.codigoPadre !== TODO && f.activo);
  const sinPadre = propias.find((f) => f.codigoPadre === TODO && f.activo);
  const conVersion =
    a.actividad === TODO && a.proceso !== TODO
      ? [...new Set(filas.filter((f) => f.proceso === a.proceso && f.actividad !== TODO).map((f) => f.actividad))]
      : [];
  const padre = d.dependeDe !== TODO ? porCodigo[d.dependeDe] : undefined;
  const ultimo = datos.ultimos[d.codigo];
  let contenido: string;
  if (d.clase === 'LISTA') contenido = T.conInactivas(recuentoDe(activas), recuentoDe(inactivas));
  else if (sinPadre?.valor != null) contenido = valorLegible(d, sinPadre.valor);
  else contenido = T.valoresPorPadre(recuentoDe(conPadre));
  return {
    clave: claveDe(d.codigo, a),
    codigo: d.codigo,
    nombre: d.nombre,
    ambito: a,
    clase: d.clase,
    impactoAlto: d.impacto === 'ALTO',
    tipo: tipoDe(d, padre),
    contenido,
    dependientes: datos.definiciones
      .filter((x) => x.dependeDe === d.codigo)
      .map((x) => x.nombre)
      .join(', '),
    ultimo: ultimo ? [ultimo.usuario, cuando(ultimo.fechaHora, ahora)].join(', ') : '',
    porAprobar: datos.pendientes.some((p) => p.definicion === d.codigo && p.proceso === a.proceso && p.actividad === a.actividad),
    conVersionPropia: recuentoDe(conVersion),
    soloLectura: !puedeEditarEn(capacidades, a),
  };
}

/** ¿La fila entra en el filtro de tipo y en la búsqueda? */
function coincide(f: FilaDeInicio, filtro: FiltroDeTipo, busqueda: string): boolean {
  if (filtro === 'listas' && f.clase !== 'LISTA') return false;
  if (filtro === 'parametros' && f.clase !== 'PARAMETRO') return false;
  if (filtro === 'editable' && f.soloLectura) return false;
  const q = paraBuscar(busqueda).trim();
  if (!q) return true;
  return paraBuscar([f.nombre, nombreDeProceso(f.ambito.proceso), nombreDeActividad(f.ambito.actividad)].join(' ')).includes(q);
}

export function construirInicio(
  datos: DatosDelInicio,
  capacidades: Capacidades,
  filtro: FiltroDeTipo = 'todo',
  busqueda = '',
  ahora: Date = new Date(),
): Inicio {
  const porCodigo = Object.fromEntries(datos.definiciones.map((d) => [d.codigo, d]));
  const filasDe = (d: Definicion): Fila[] => datos.valores[d.codigo]?.filas ?? [];
  // Los ámbitos con filas, por definición.
  const ambitosVistos = new Map<string, Ambito>();
  for (const d of datos.definiciones) {
    for (const f of filasDe(d)) ambitosVistos.set([f.proceso, f.actividad].join('|'), { proceso: f.proceso, actividad: f.actividad });
  }
  const nombresDeProcesos = new Set<string>([...datos.procesos.map((p) => p.proceso), ...[...ambitosVistos.values()].map((a) => a.proceso)]);
  nombresDeProcesos.delete(TODO);

  const actividadesDe = (proceso: string): string[] => {
    const declaradas = datos.procesos.find((p) => p.proceso === proceso)?.actividades ?? [];
    const conFilas = [...ambitosVistos.values()].filter((a) => a.proceso === proceso && a.actividad !== TODO).map((a) => a.actividad);
    return [...new Set([...declaradas, ...conFilas])];
  };

  const ambitosOrdenados: Ambito[] = [GLOBAL];
  for (const p of [...nombresDeProcesos].sort((a, b) => nombreDeProceso(a).localeCompare(nombreDeProceso(b)))) {
    ambitosOrdenados.push({ proceso: p, actividad: TODO });
    for (const act of actividadesDe(p)) ambitosOrdenados.push({ proceso: p, actividad: act });
  }

  const todos: GrupoDeInicio[] = [];
  for (const a of ambitosOrdenados) {
    const definiciones = datos.definiciones
      .filter((d) => filasEn(filasDe(d), a).length > 0)
      // Un parámetro con valor propio en algún proceso se administra ahí: su valor global (el «valor base
      // de la academia») se llega por la cadena de herencia y no repite la fila en «Globales» (p01).
      .filter((d) => !(esGlobal(a) && d.clase === 'PARAMETRO' && filasDe(d).some((f) => f.proceso !== TODO)))
      .sort((x, y) => x.nombre.localeCompare(y.nombre));
    const filas = definiciones.map((d) => filaDe(d, a, datos, filasDe(d), capacidades, porCodigo, ahora));
    const soloLectura = !puedeEditarEn(capacidades, a);
    todos.push({
      clave: [a.proceso, a.actividad].join('|'),
      ambito: a,
      titulo: tituloDelGrupo(a, capacidades.perfil),
      sinParametros: false,
      editable: !soloLectura,
      filas,
    });
  }

  // Un proceso sin ninguna fila en ninguno de sus ámbitos: se enseña como «aún no tiene parámetros».
  const procesosSinNada = [...nombresDeProcesos].filter((p) => !todos.some((g) => g.ambito.proceso === p && g.filas.length > 0));

  const conFiltro = filtro !== 'todo' || busqueda.trim() !== '';
  let grupos = todos
    .map((g) => ({ ...g, filas: g.filas.filter((f) => coincide(f, filtro, busqueda)) }))
    .filter((g) => g.filas.length > 0);

  // El delegado ve primero lo suyo y lo global en solo lectura al final.
  if (capacidades.perfil === 'delegado') {
    grupos = [...grupos.filter((g) => g.editable), ...grupos.filter((g) => !g.editable)];
  }

  // Un proceso sin parámetros solo le dice algo a quien puede conectarlo: la superadministración.
  if (!conFiltro && capacidades.perfil === 'superadministracion') {
    for (const p of procesosSinNada.sort()) {
      const a: Ambito = { proceso: p, actividad: TODO };
      grupos.push({
        clave: [p, TODO].join('|'),
        ambito: a,
        titulo: tituloDelGrupo(a, capacidades.perfil),
        sinParametros: true,
        editable: puedeEditarEn(capacidades, a),
        filas: [],
      });
    }
  }

  const filasVisibles = grupos.flatMap((g) => g.filas);
  const filasTotales = todos.flatMap((g) => g.filas);
  return { grupos, visibles: recuentoDe(filasVisibles), total: recuentoDe(filasTotales) };
}
