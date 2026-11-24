/**
 * El modelo de Permisos (`p07-permisos`): las delegaciones vigentes y las vencidas o revocadas, a
 * quién, sobre qué y hasta cuándo. Lógica pura sobre datos CRUDOS; devuelve textos y sí/no. Una delegación
 * y su modelo viajan juntos (`Par`): la vista devuelve el MODELO y el contenedor recupera el dato crudo,
 * con su versión y sus identificadores, que no llegan nunca a la pantalla.
 */
import type { SujetosPorId } from './aprobaciones';
import { soloFecha, venceManana } from './formatos';
import { esNodoTecnico, nombreDeActividad, nombreDeGrupo, nombreDeProceso } from './nombres';
import * as T from './textos';
import type { Delegacion } from './tipos';

export interface DelegacionVM {
  tipo: string;
  quien: string;
  conSubgrupos: boolean;
  sobreQue: string;
  vigencia: string;
  venceManana: boolean;
  otorgadaPor: string;
  vigente: boolean;
  /** Se puede prorrogar: tiene fecha de fin. */
  puedeProrrogar: boolean;
}

export interface Par {
  vm: DelegacionVM;
  cruda: Delegacion;
}

export interface Permisos {
  vigentes: Par[];
  vencidas: Par[];
}

const TIPOS = { USUARIO: 'Usuario', GRUPO: 'Grupo', ROL: 'Rol', GRUPO_ROL: 'Grupo y rol' } as const;

function nombreDe(lista: Array<{ id: number; nombre: string }>, id: number | null, generico: string): string {
  return (id === null ? undefined : lista.find((x) => x.id === id)?.nombre) ?? generico;
}

export function quienLegible(d: Delegacion, sujetos: SujetosPorId): string {
  const grupo = d.sujetoRuta !== null ? nombreDeGrupo(d.sujetoRuta) : nombreDe(sujetos.grupo, d.sujetoGrupoId, T.UN_GRUPO);
  switch (d.tipoSujeto) {
    case 'USUARIO':
      return nombreDe(sujetos.usuario, d.sujetoUsuarioId, T.UNA_PERSONA);
    case 'GRUPO':
      return grupo;
    case 'ROL':
      return nombreDe(sujetos.rol, d.sujetoRolId, T.UN_ROL);
    default:
      return `${grupo} · ${nombreDe(sujetos.rol, d.sujetoRolId, T.UN_ROL)}`;
  }
}

function vigenciaLegible(d: Delegacion): string {
  const desde = d.vigenteDesde ? soloFecha(d.vigenteDesde) : null;
  const hasta = d.vigenteHasta ? soloFecha(d.vigenteHasta) : null;
  if (desde && hasta) return `${desde} → ${hasta}`;
  if (hasta) return T.hastaElTexto(hasta);
  return T.SIN_FECHA_DE_FIN_MAYUS;
}

/** Vigente: activa y sin vencer. Una revocada (`activo = false`) o una vencida van a la otra pestaña. */
export function estaVigente(d: Delegacion, ahora: Date): boolean {
  if (!d.activo) return false;
  if (d.vigenteHasta === null) return true;
  const fin = new Date(d.vigenteHasta);
  return Number.isNaN(fin.getTime()) || fin > ahora;
}

export function parDe(d: Delegacion, sujetos: SujetosPorId, nombres: Record<string, string>, ahora: Date): Par {
  const vigente = estaVigente(d, ahora);
  return {
    cruda: d,
    vm: {
      tipo: TIPOS[d.tipoSujeto],
      quien: quienLegible(d, sujetos),
      conSubgrupos: d.incluyeSubgrupos,
      sobreQue: [nombreDeProceso(d.proceso), d.actividades.length === 0 ? T.TODO_EL_PROCESO.toLowerCase() : d.actividades.map(nombreDeActividad).join(', ')].join(' · '),
      vigencia: vigenciaLegible(d),
      venceManana: vigente && venceManana(d.vigenteHasta, ahora),
      otorgadaPor: nombres[d.otorgadoPor] ?? d.otorgadoPor,
      vigente,
      puedeProrrogar: vigente && d.vigenteHasta !== null,
    },
  };
}

export function construirPermisos(delegaciones: Delegacion[], sujetos: SujetosPorId, nombres: Record<string, string>, ahora: Date = new Date()): Permisos {
  const pares = delegaciones.map((d) => parDe(d, sujetos, nombres, ahora));
  return { vigentes: pares.filter((p) => p.vm.vigente), vencidas: pares.filter((p) => !p.vm.vigente) };
}

/** El texto del proceso/actividad de una delegación nueva, para el selector. */
export const opcionesDeActividad = (actividades: string[]): Array<{ valor: string; nombre: string }> =>
  actividades.filter((a) => !esNodoTecnico(a)).map((a) => ({ valor: a, nombre: nombreDeActividad(a) }));

