/**
 * Las escrituras de la aplicación, antes de llegar al kit. Aquí viven las dos reglas
 * que hacen de esta pantalla la mitad humana de la traza auditable:
 *
 *  - **Todo guardado pide un motivo**, y un guardado sin motivo NO llama a la API: la pantalla lo dice y no
 *    se escribe nada. El servidor también lo exige; esto es la primera barrera,
 *    no la única.
 *  - **Los datos crudos con su versión viven aquí**, no en la vista: la vista devuelve una clave y un texto
 *    y quien construye la petición es este módulo, con la `persistenceVersion` que leyó (bloqueo optimista).
 *
 * Cada función devuelve un `Resultado` ya explicado en lenguaje de negocio; nunca lanza hacia la vista.
 */
import { FalloDelKit, type Kit } from './kit';
import { explicar, type Explicacion } from './fallos';
import { type Ambito } from './ambitos';
import * as T from './textos';
import { TODO, type Fila, type PeticionDeCambio, type ValoresAdministracion } from './tipos';

/**
 * Lo que pasó al escribir. Un CONFLICTO lleva además QUIÉN guardó antes y CUÁNDO (`conflicto`), para que
 * la pantalla lo cuente en humano (p05--conflicto) en vez de decir solo «hubo un error».
 */
export type Resultado =
  | { ok: true; propuesta: boolean }
  | { ok: false; explicacion: Explicacion; conflicto?: { por: string | null; en: string | null } };

export const bien = (propuesta = false): Resultado => ({ ok: true, propuesta });
export const mal = (explicacion: Explicacion, conflicto?: { por: string | null; en: string | null }): Resultado =>
  conflicto ? { ok: false, explicacion, conflicto } : { ok: false, explicacion };

/** El motivo vacío (o solo espacios) no se escribe en la traza. */
export function falloDeMotivo(motivo: string): Explicacion | null {
  return motivo.trim() === '' ? { campo: 'motivo', mensaje: T.ERROR_MOTIVO } : null;
}

/** Ejecuta una petición de cambio y la deja explicada. Un cambio de impacto alto vuelve como propuesta. */
export async function ejecutar(kit: Kit, peticion: PeticionDeCambio, yo?: string): Promise<Resultado> {
  const sinMotivo = falloDeMotivo(peticion.motivo);
  if (sinMotivo) return mal(sinMotivo);
  try {
    const r = await kit.cambiar({ ...peticion, motivo: peticion.motivo.trim() });
    return bien(!r.aplicado);
  } catch (e) {
    return mal(explicar(e, yo), e instanceof FalloDelKit && e.clase === 'CONFLICTO' ? { por: e.guardadoPor, en: e.guardadoEn } : undefined);
  }
}

const claveDe = (f: Fila) => [f.codigoPadre, f.codigo].join('|');

/** La fila de una opción por su clave `codigoPadre|codigo` en un ámbito. */
export function filaDe(valores: ValoresAdministracion, ambito: Ambito, clave: string): Fila | undefined {
  return valores.filas.find((f) => f.proceso === ambito.proceso && f.actividad === ambito.actividad && claveDe(f) === clave);
}

interface Base {
  valores: ValoresAdministracion;
  ambito: Ambito;
  motivo: string;
}

export function peticionEditar(b: Base & { clave: string; etiqueta: string; ayuda: string }): PeticionDeCambio | Explicacion {
  const f = filaDe(b.valores, b.ambito, b.clave);
  if (!f) return { campo: 'general', mensaje: T.FALLO_NO_EXISTE };
  if (b.etiqueta.trim() === '') return { campo: 'etiqueta', mensaje: T.ERROR_ETIQUETA };
  return {
    accion: 'EDITAR',
    definicion: b.valores.definicion.codigo,
    ambito: b.ambito,
    codigoPadre: f.codigoPadre,
    codigo: f.codigo,
    datos: { etiqueta: b.etiqueta.trim(), ayuda: b.ayuda.trim() === '' ? null : b.ayuda.trim() },
    persistenceVersion: f.persistenceVersion,
    motivo: b.motivo,
  };
}

export function peticionAnadir(b: Base & { codigoPadre: string | null; codigo: string; etiqueta: string; ayuda: string }): PeticionDeCambio | Explicacion {
  if (b.etiqueta.trim() === '') return { campo: 'etiqueta', mensaje: T.ERROR_ETIQUETA };
  if (b.codigo.trim() === '') return { campo: 'codigo', mensaje: T.ERROR_CODIGO };
  return {
    accion: 'CREAR',
    definicion: b.valores.definicion.codigo,
    ambito: b.ambito,
    codigoPadre: b.codigoPadre ?? TODO,
    codigo: b.codigo.trim().toLowerCase(),
    datos: { etiqueta: b.etiqueta.trim(), ...(b.ayuda.trim() === '' ? {} : { ayuda: b.ayuda.trim() }) },
    motivo: b.motivo,
  };
}

export function peticionDeEstado(b: Base & { clave: string; activar: boolean }): PeticionDeCambio | Explicacion {
  const f = filaDe(b.valores, b.ambito, b.clave);
  if (!f) return { campo: 'general', mensaje: T.FALLO_NO_EXISTE };
  return {
    accion: b.activar ? 'REACTIVAR' : 'DESACTIVAR',
    definicion: b.valores.definicion.codigo,
    ambito: b.ambito,
    codigoPadre: f.codigoPadre,
    codigo: f.codigo,
    persistenceVersion: f.persistenceVersion,
    motivo: b.motivo,
  };
}

/** El nuevo orden de una lista: exactamente las opciones del ámbito (y de un padre), con la versión leída de cada una. */
export function peticionOrdenar(b: Base & { codigoPadre: string | null; ordenNuevo: string[] }): PeticionDeCambio | Explicacion {
  const padre = b.codigoPadre ?? TODO;
  const enAmbito = b.valores.filas.filter((f) => f.proceso === b.ambito.proceso && f.actividad === b.ambito.actividad && f.codigoPadre === padre);
  const orden = b.ordenNuevo.map((codigo) => ({ codigo, persistenceVersion: enAmbito.find((f) => f.codigo === codigo)?.persistenceVersion }));
  return {
    accion: 'ORDENAR',
    definicion: b.valores.definicion.codigo,
    ambito: b.ambito,
    codigoPadre: padre,
    datos: { orden },
    motivo: b.motivo,
  };
}

export function peticionDeAmbito(b: Base & { accion: 'CREAR_VERSION_PROPIA' | 'VOLVER_A_HEREDAR' }): PeticionDeCambio {
  return { accion: b.accion, definicion: b.valores.definicion.codigo, ambito: b.ambito, motivo: b.motivo };
}

/** Para pasar una petición o una explicación (error de validación previa) por el mismo camino. */
export async function pedir(kit: Kit, p: PeticionDeCambio | Explicacion, yo?: string): Promise<Resultado> {
  if ('accion' in p) return ejecutar(kit, p, yo);
  return mal(p);
}

/**
 * Fijar el valor de un PARÁMETRO en un ámbito: si el ámbito ya tiene fila propia se EDITA (con la versión leída);
 * si hereda, se CREA un valor propio. En impacto alto el kit lo convierte en propuesta (doble control).
 */
export function peticionDeValor(b: Base & { codigoPadre: string | null; valor: string }): PeticionDeCambio | Explicacion {
  const padre = b.codigoPadre ?? TODO;
  const propia = b.valores.filas.find(
    (f) => f.proceso === b.ambito.proceso && f.actividad === b.ambito.actividad && f.codigoPadre === padre && f.codigo === TODO,
  );
  const base = { definicion: b.valores.definicion.codigo, ambito: b.ambito, codigoPadre: padre, codigo: TODO, motivo: b.motivo };
  if (propia) {
    return { accion: 'EDITAR', ...base, datos: { valor: b.valor }, persistenceVersion: propia.persistenceVersion };
  }
  return { accion: 'CREAR', ...base, datos: { valor: b.valor } };
}
