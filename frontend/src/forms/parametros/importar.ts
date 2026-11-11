/**
 * El modelo de la vista previa de una importación (`p08-importar`): recuentos por clase,
 * filas explicadas y si se puede confirmar. Los recuentos se CUENTAN de las filas (no se copian del
 * resumen del servidor): así salen marcados (`Recuento`) y no pueden contradecir a la tabla.
 */
import { recuentoDe, type Recuento } from '$lib/bonita/marcas';
import { valorLegible } from './formatos';
import type { Usos } from './kit';
import * as T from './textos';
import { TODO, type ClaseDeFilaImportada, type Definicion, type FilaImportada, type ValoresAdministracion, type VistaPreviaDeImportacion } from './tipos';

export interface FilaImportadaVM {
  clave: string;
  clase: ClaseDeFilaImportada;
  etiquetaDeClase: string;
  tono: 'exito' | 'marca' | 'atencion' | 'neutro' | 'error';
  lista: string;
  opcion: string;
  detalle: string;
}

export interface VistaPreviaVM {
  altas: Recuento;
  cambios: Recuento;
  bajas: Recuento;
  sinCambios: Recuento;
  propuestas: Recuento;
  errores: Recuento;
  /** Cuántas filas producen algo al confirmar. */
  aAplicar: Recuento;
  filas: FilaImportadaVM[];
  /** Los errores, en una frase cada uno. */
  explicacionDeErrores: string[];
  /** Se puede confirmar: sin errores y con algo que aplicar. */
  confirmable: boolean;
}

const CAMPOS_DE_IMPORTACION: Readonly<Record<string, string>> = {
  codigoPadre: 'Opción padre',
  actividad: 'Actividad',
  activo: 'Estado',
  valor: 'Valor',
  etiqueta: 'Nombre',
  ayuda: 'Ayuda',
  orden: 'Posición',
  proceso: 'Proceso',
};

const mayuscula = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** Un trozo del `detalle` del kit («valor 35 → 30», «etiqueta «A» → «B»») dicho como lo diría una persona. */
function trozoLegible(t: string, def: Definicion | undefined): string {
  let m = /^nueva(?:, con el valor (.+))?$/.exec(t);
  if (m) return m[1] ? `Opción nueva, con el valor ${def ? valorLegible(def, m[1]) : m[1]}` : 'Opción nueva';
  m = /^etiqueta «(.*)» → «(.*)»$/.exec(t);
  if (m) return `Cambia el nombre de «${m[1]}» a «${m[2]}»`;
  if (t === 'ayuda cambiada') return 'Cambia el texto de ayuda';
  m = /^orden (.+) → (.+)$/.exec(t);
  if (m) return `Cambia la posición de ${m[1]} a ${m[2]}`;
  m = /^valor (.*) → (.*)$/.exec(t);
  if (m) return `Cambia el valor de ${def ? valorLegible(def, m[1]) : m[1]} a ${def ? valorLegible(def, m[2]) : m[2]}`;
  if (t === 'se reactiva') return 'Se vuelve a activar';
  if (t === 'se desactiva, no se borra') return 'Se da de baja (no se borra)';
  if (t === 'queda como propuesta: impacto alto') return 'Queda como propuesta: otra persona tiene que aprobarla';
  if (t === 'coincide con lo guardado') return 'Sin cambios: ya coincide con lo guardado';
  if (/^CONFLICTO/.test(t)) return 'Otra persona lo cambió mientras tanto';
  if (t === 'SIN_PERMISO') return 'No tienes permiso para esta fila';
  if (t === 'NO_EXISTE') return 'Ya no existe';
  const campo = /^(?:datos\.)?([A-Za-z]+): (.*)$/.exec(t);
  // «codigo: código repetido…» y «definicion: no existe…» ya dicen de qué hablan: se quita el nombre interno del campo.
  if (campo && (campo[1] === 'codigo' || campo[1] === 'definicion')) return mayuscula(campo[2]!);
  if (campo && CAMPOS_DE_IMPORTACION[campo[1]!]) return `${CAMPOS_DE_IMPORTACION[campo[1]!]}: ${campo[2]}`;
  return mayuscula(t);
}

/** El `detalle` crudo del kit en lenguaje de negocio: sin nombres de campo internos ni cifras sueltas del motor. */
export function detalleLegible(detalle: string, def: Definicion | undefined): string {
  return detalle.split(' · ').map((t) => trozoLegible(t.trim(), def)).join(' · ');
}

const delaClase = (filas: FilaImportada[], c: ClaseDeFilaImportada) => filas.filter((f) => f.clase === c);

/** Lee de un CSV cuántas etiquetas dice por opción: `definicion|codigoPadre|codigo` → etiqueta (para nombrar una opción NUEVA, que aún no existe en las listas leídas). */
export function etiquetasDelCsv(csv: string): Record<string, string> {
  const lineas = csv.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  const cabecera = (lineas[0] ?? '').split(',').map((c) => c.trim());
  const col = (n: string) => cabecera.indexOf(n);
  const [iDef, iPadre, iCod, iEt] = [col('definicion'), col('codigoPadre'), col('codigo'), col('etiqueta')];
  const salida: Record<string, string> = {};
  if (iDef < 0 || iCod < 0 || iEt < 0) return salida;
  for (const l of lineas.slice(1)) {
    const c = l.split(',').map((x) => x.trim());
    const et = c[iEt] ?? '';
    if (et !== '') salida[[(c[iDef] ?? '').toLowerCase(), iPadre >= 0 && (c[iPadre] ?? '') !== '' ? (c[iPadre] ?? '').toLowerCase() : TODO, (c[iCod] ?? '').toLowerCase()].join('|')] = et;
  }
  return salida;
}

/** Los expedientes que usan la opción que se da de baja (guardados y en curso), o por qué no se sabe. */
function quienLaUsa(f: FilaImportada, usos: Usos | 'error' | undefined): string {
  if (usos === undefined) return ''; // todavía se está leyendo: no se afirma nada
  if (usos === 'error') return T.BAJA_USOS_NO_LEIDOS;
  // Sin ninguna fila de expedientes el módulo no cuenta esta lista: no se afirma «0», se dice que no se sabe.
  if (usos.expedientes.length === 0) return T.BAJA_SIN_CONTEO;
  // La opción es el código de la fila; en un parámetro por modalidad el código es `*` y la opción va en `codigoPadre`.
  const opcion = f.codigo === TODO ? f.codigoPadre : f.codigo;
  const fila = usos.expedientes.find((e) => e.codigo === opcion);
  // La opción no está entre las filas que el kit sirvió: NO se afirma «0» (no lo sabemos), se dice que no se cuenta.
  return fila ? T.BAJA_LA_USAN(fila.guardados, fila.enCurso) : T.BAJA_SIN_CONTEO;
}

export function construirVistaPrevia(
  v: VistaPreviaDeImportacion,
  definiciones: Definicion[],
  valores: Readonly<Record<string, ValoresAdministracion>> = {},
  etiquetasNuevas: Readonly<Record<string, string>> = {},
  /** `GET parametros/usos` de las definiciones con bajas: la baja dice qué expedientes usan la opción. */
  usosDeBajas: ReadonlyMap<string, Usos | 'error'> = new Map(),
): VistaPreviaVM {
  const nombre = (codigo: string) => definiciones.find((d) => d.codigo === codigo)?.nombre ?? codigo;
  /** «Curso en línea / 12 semanas»: la opción y su padre por su NOMBRE, no por sus códigos («curso · 12»). Sin nombre conocido (una opción nueva), el código que la persona escribió. */
  const opcionLegible = (f: FilaImportada): string => {
    if (f.codigo === TODO) return T.EL_PARAMETRO_ENTERO;
    const etiqueta = (def: string, codigo: string, padre: string) =>
      valores[def]?.filas.find((x) => x.codigo === codigo && x.codigoPadre === padre)?.etiqueta ?? null;
    const propia = etiqueta(f.definicion, f.codigo, f.codigoPadre) ?? etiquetasNuevas[[f.definicion, f.codigoPadre, f.codigo].join('|')] ?? f.codigo;
    if (f.codigoPadre === TODO) return propia;
    const padreDef = definiciones.find((d) => d.codigo === f.definicion)?.dependeDe ?? TODO;
    const padre = padreDef === TODO ? null : (etiqueta(padreDef, f.codigoPadre, TODO) ?? null);
    return [padre ?? f.codigoPadre, propia].join(' / ');
  };
  const filas = v.filas.map((f): FilaImportadaVM => {
    const [etiqueta, tono] = T.CLASES_DE_IMPORTACION[f.clase];
    return {
      clave: [f.clase, f.definicion, f.codigoPadre, f.codigo, f.proceso, f.actividad, f.detalle].join('|'),
      clase: f.clase,
      etiquetaDeClase: etiqueta,
      tono,
      lista: nombre(f.definicion),
      opcion: opcionLegible(f),
      detalle: [detalleLegible(f.detalle, definiciones.find((d) => d.codigo === f.definicion)), f.clase === 'BAJA' ? quienLaUsa(f, usosDeBajas.get(f.definicion)) : ''].filter(Boolean).join(' · '),
    };
  });
  const altas = delaClase(v.filas, 'ALTA');
  const cambios = delaClase(v.filas, 'CAMBIO');
  const bajas = delaClase(v.filas, 'BAJA');
  const sin = delaClase(v.filas, 'SIN_CAMBIOS');
  const propuestas = delaClase(v.filas, 'PROPUESTA');
  const errores = delaClase(v.filas, 'ERROR');
  const aplicables = v.filas.filter((f) => ['ALTA', 'CAMBIO', 'BAJA', 'PROPUESTA'].includes(f.clase));
  return {
    altas: recuentoDe(altas),
    cambios: recuentoDe(cambios),
    bajas: recuentoDe(bajas),
    sinCambios: recuentoDe(sin),
    propuestas: recuentoDe(propuestas),
    errores: recuentoDe(errores),
    aAplicar: recuentoDe(aplicables),
    filas,
    explicacionDeErrores: errores.map((f) => `${nombre(f.definicion)} · ${opcionLegible(f)}: ${detalleLegible(f.detalle, undefined)}`),
    confirmable: errores.length === 0 && aplicables.length > 0,
  };
}
