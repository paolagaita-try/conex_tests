/**
 * El modelo de la traza (`p09-traza`): las entradas como frases de negocio con filtros
 * por persona, lista o parámetro, acción y fecha, más la verificación de la cadena con lo que detecta y lo
 * que no. Lógica pura; la vista pinta y no ofrece ninguna forma de editar o borrar una entrada.
 */
import { aCsv } from './csv';
import { cuandoCompleto } from './formatos';
import type { CategoriaDeAccion, EventoVM } from './historial';
import * as T from './textos';
import { partesDeLaClave } from './historial';
import type { VerificacionDeCadena } from './tipos';

export interface FiltrosDeLaVista {
  persona: string;
  lista: string;
  accion: 'todas' | CategoriaDeAccion;
  /** ISO `aaaa-mm-dd` o vacío. */
  desde: string;
  /** ISO `aaaa-mm-dd` o vacío; incluye ese día. */
  hasta: string;
}

export const SIN_FILTROS: FiltrosDeLaVista = { persona: '', lista: '', accion: 'todas', desde: '', hasta: '' };

export function filtrar(eventos: EventoVM[], f: FiltrosDeLaVista): EventoVM[] {
  const lista = f.lista.trim().toLowerCase();
  return eventos.filter(
    (e) =>
      (lista === '' || e.nombreDeLaDefinicion.toLowerCase().includes(lista)) &&
      (f.accion === 'todas' || e.categoria === f.accion) &&
      (f.desde === '' || e.cuandoIso.slice(0, 10) >= f.desde) &&
      (f.hasta === '' || e.cuandoIso.slice(0, 10) <= f.hasta),
  );
}

/** Las personas de la traza por su USUARIO (identidad) con el nombre que se ve: dos «Sara Parametros» son dos. */
export function personasDe(eventos: EventoVM[]): Array<{ usuario: string; nombre: string }> {
  const porUsuario = new Map<string, string>();
  for (const e of eventos) if (!porUsuario.has(e.usuario)) porUsuario.set(e.usuario, e.quien);
  return [...porUsuario].map(([usuario, nombre]) => ({ usuario, nombre })).sort((a, b) => a.nombre.localeCompare(b.nombre));
}

export function trazaACsv(eventos: EventoVM[]): string {
  return aCsv(T.COLUMNAS_DE_HISTORIAL, eventos.map((e) => [e.cuando, e.quien, e.texto, e.cambio, e.motivo]));
}

export interface ResultadoDeVerificacion {
  coherente: boolean;
  titulo: string;
  cuerpo: string;
  /** Lo que la verificación detecta y lo que no: se dice siempre (CRN-14). */
  limites: string;
}

/** `nombreDeDefinicion` traduce el código interno al nombre de negocio: la cadena rota no cita códigos. */
export function resultadoDeVerificacion(v: VerificacionDeCadena, nombreDeDefinicion: (codigo: string) => string = (c) => c): ResultadoDeVerificacion {
  if (v.coherente && !(v.entradas > 0)) {
    // Verificar cero entradas no es haber comprobado una cadena: no se afirma que «coincidan».
    return { coherente: true, titulo: T.CADENA_SIN_ENTRADAS_TITULO, cuerpo: T.CADENA_SIN_ENTRADAS_CUERPO, limites: T.LO_QUE_DETECTA };
  }
  if (v.coherente) {
    return { coherente: true, titulo: T.CADENA_COHERENTE_TITULO, cuerpo: T.CADENA_COHERENTE_CUERPO, limites: T.LO_QUE_DETECTA };
  }
  const k = partesDeLaClave(v.primeraQueNoCasa.claveNegocio);
  return {
    coherente: false,
    titulo: T.CADENA_ROTA_TITULO,
    cuerpo: T.cadenaRotaCuerpo(cuandoCompleto(v.primeraQueNoCasa.fechaHora), k.definicion === '*' || k.definicion === 'delegacion' ? '' : nombreDeDefinicion(k.definicion)),
    limites: T.LO_QUE_DETECTA,
  };
}
