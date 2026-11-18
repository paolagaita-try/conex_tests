/** Lo que se exporta del inicio: las filas visibles, en lenguaje de negocio. */
import { aCsv } from './csv';
import type { Inicio } from './inicio';
import * as T from './textos';

export function inicioACsv(inicio: Inicio): string {
  const filas = inicio.grupos.flatMap((g) =>
    g.filas.map((f) => [
      g.titulo,
      f.nombre,
      f.tipo,
      f.contenido,
      f.ultimo,
      f.impactoAlto ? T.IMPACTO_ALTO : T.IMPACTO_NORMAL,
      f.porAprobar ? T.SI : T.NO,
    ]),
  );
  return aCsv(T.COLUMNAS_DE_EXPORTACION, filas);
}
