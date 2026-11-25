/**
 * «Dónde se usa» (`p03`): los formularios, documentos y reglas que leen una lista y, por opción, los expedientes
 * que la eligieron (`GET parametros/usos`). Recuentos como TEXTO decimal del kit.
 *
 * Contra lo que el kit pueda servir: el código de una fila es SIEMPRE el real y completo (hasta 255 caracteres, único) y es la
 * clave; lo que se PINTA es la etiqueta de la opción, la `etiqueta` recortada de una fila fuera de lista, o «Sin elegir». Las
 * etiquetas se buscan en un `Map`: con un objeto plano, el código `constructor` o `__proto__` resolvería a algo del prototipo.
 */
import type { Usos } from './kit';
import * as T from './textos';

export interface UsosVM {
  lugares: Array<{ clave: string; tipo: string; titulo: string; detalle: string }>;
  expedientes: Array<{ clave: string; opcion: string; /** El código completo, para quien pase el cursor o lea la fila. */ codigo: string; guardados: string; enCurso: string; inactiva: boolean; fuera: boolean }>;
  /** Los códigos fuera de lista que el kit agrupó (no caben en la respuesta): una fila agregada, no varias. */
  otros: { guardados: string; enCurso: string } | null;
}

export function usosVM(usos: Usos, etiquetas: ReadonlyMap<string, string>, inactivas: ReadonlySet<string>): UsosVM {
  return {
    lugares: usos.lugares.map((l) => ({ clave: [l.tipo, l.titulo].join('|'), tipo: (T.TIPO_DE_USO as Readonly<Record<string, string>>)[l.tipo] ?? T.TIPO_DE_USO_OTRO, titulo: l.titulo, detalle: l.detalle })),
    expedientes: usos.expedientes.map((e) => ({
      clave: e.codigo,
      opcion: e.sinElegir ? T.SIN_ELEGIR : (etiquetas.get(e.codigo) ?? e.etiqueta ?? e.codigo),
      codigo: e.codigo,
      guardados: e.guardados,
      enCurso: e.enCurso,
      inactiva: inactivas.has(e.codigo),
      fuera: e.fueraDeLista === true,
    })),
    otros: usos.otros ? { guardados: usos.otros.guardados, enCurso: usos.otros.enCurso } : null,
  };
}

/**
 * Cómo se llama cada opción de una definición: por su código si la fila es una opción de lista, y por el CÓDIGO DEL PADRE cuando la fila
 * es `*` y la opción va en `codigoPadre` (un parámetro por modalidad: `tope_beca_por_modalidad`), con el nombre que la lista PADRE le da
 * («curso» → «Curso en línea»). `Map`, no objeto: un código `constructor` no resuelve al prototipo.
 */
export function etiquetasDeOpciones(
  definicion: string,
  valores: Readonly<Record<string, { filas: ReadonlyArray<{ codigo: string; codigoPadre: string; etiqueta: string | null }> } | undefined>>,
  dependeDe: string,
): ReadonlyMap<string, string> {
  const mapa = new Map<string, string>();
  for (const f of valores[definicion]?.filas ?? []) if (f.codigo !== '*') mapa.set(f.codigo, f.etiqueta ?? f.codigo);
  // la lista padre da el nombre de las opciones que esta definición solo cita por `codigoPadre`
  if (dependeDe !== '*') for (const f of valores[dependeDe]?.filas ?? []) if (f.codigo !== '*' && !mapa.has(f.codigo)) mapa.set(f.codigo, f.etiqueta ?? f.codigo);
  return mapa;
}
