/**
 * El modelo de una lista: de dónde viene lo que se ve, qué se puede hacer y cómo quedará en el
 * formulario. Con los datos ficticios de `p02` y la expectativa escrita aquí.
 */
import { describe, expect, it } from 'vitest';
import { capacidadesDe, CONSULTA, ROL_DE_SUPERADMINISTRACION } from './capacidades';
import { construirLista, migasDe, type DatosDeLista } from './lista';
import {
  ACT_DECANATO,
  ACT_COMITE,
  ACT_PAGO,
  DEFINICIONES,
  FILAS,
  PROCESO,
  PROCESOS,
  valoresDeEjemplo,
} from './ejemplo';
import type { Ambito } from './ambitos';
import type { Fila } from './tipos';

const SUPER = capacidadesDe('marta.rivas', [{ rol: ROL_DE_SUPERADMINISTRACION, grupo: '/academia/evaluacion' }], []);
const DELEGADO = capacidadesDe('luis.gil', [], [{ tipo: 'USUARIO', sujeto: 'luis.gil', proceso: PROCESO, actividades: [] }]);

function datos(codigo: string, ambito: Ambito, extra: Partial<DatosDeLista> = {}): DatosDeLista {
  const v = valoresDeEjemplo(codigo);
  const padre = v.definicion.dependeDe === '*' ? null : valoresDeEjemplo(v.definicion.dependeDe);
  return { valores: v, padre, ambito, procesos: PROCESOS, capacidades: SUPER, editores: [], nombres: {}, ...extra };
}

const VIAS: Ambito = { proceso: PROCESO, actividad: ACT_PAGO };
const DURACIONES_PROCESO: Ambito = { proceso: PROCESO, actividad: '*' };
const DURACIONES_COMITE: Ambito = { proceso: PROCESO, actividad: ACT_COMITE };
const DURACIONES_DECANATO: Ambito = { proceso: PROCESO, actividad: ACT_DECANATO };

describe('migas de ámbito', () => {
  it('Global › proceso › actividad, con la última como lugar actual', () => {
    const m = migasDe(VIAS);
    expect(m.map((x) => x.rotulo)).toEqual(['Global', 'Becas de estudio', 'Verificar los soportes y preparar el pago']);
    expect(m.map((x) => x.actual)).toEqual([false, false, true]);
  });
  it('el ámbito global es solo «Global»', () => {
    expect(migasDe({ proceso: '*', actividad: '*' }).map((x) => x.rotulo)).toEqual(['Global']);
  });
});

describe('una lista con versión propia (p02-lista)', () => {
  const l = construirLista(datos('vias_pago', VIAS));

  it('enseña las cuatro opciones, tres activas, en su orden, con la inactiva marcada', () => {
    expect(l.modo).toBe('propia');
    expect(l.total).toBe(4);
    expect(l.activas).toBe(3);
    expect(l.opciones.map((o) => o.etiqueta)).toEqual([
      'Transferencia a la cuenta del becario',
      'Cheque de administración',
      'Pago en caja',
      'Bono prepago',
    ]);
    expect(l.opciones.map((o) => o.activa)).toEqual([true, true, true, false]);
    expect(l.opciones.map((o) => o.posicion)).toEqual(['1', '2', '3', '4']);
    expect(l.procedencia).toBe('Lista propia de esta actividad');
  });

  it('la primera no sube y la última no baja', () => {
    expect(l.opciones.map((o) => o.puedeSubir)).toEqual([false, true, true, true]);
    expect(l.opciones.map((o) => o.puedeBajar)).toEqual([true, true, true, false]);
  });

  it('la vista previa usa el widget de la regla por defecto con SOLO las activas (3 → fichas)', () => {
    expect(l.vistaPrevia).toHaveLength(1);
    expect(l.vistaPrevia[0].widget).toBe('fichas');
    expect(l.vistaPrevia[0].opciones.map((o) => o.etiqueta)).toEqual([
      'Transferencia a la cuenta del becario',
      'Cheque de administración',
      'Pago en caja',
    ]);
  });

  it('una lista de más de 5 activas se previsualiza como desplegable y de más de 15 con buscador', () => {
    const base = valoresDeEjemplo('vias_pago');
    const fila = (i: number): Fila => ({ ...base.filas[0], codigo: `c${i}`, etiqueta: `Opción ${i}`, orden: i, persistenceVersion: i });
    const con = (n: number) => construirLista(datos('vias_pago', VIAS, { valores: { ...base, filas: Array.from({ length: n }, (_, i) => fila(i)) } }));
    expect(con(5).vistaPrevia[0].widget).toBe('fichas');
    expect(con(6).vistaPrevia[0].widget).toBe('desplegable');
    expect(con(15).vistaPrevia[0].widget).toBe('desplegable');
    expect(con(16).vistaPrevia[0].widget).toBe('autocompletar');
  });

  it('un delegado del proceso puede editar; la consulta no', () => {
    expect(construirLista(datos('vias_pago', VIAS, { capacidades: DELEGADO })).puedeEditar).toBe(true);
    expect(construirLista(datos('vias_pago', VIAS, { capacidades: CONSULTA })).puedeEditar).toBe(false);
  });

  it('«volver a heredar» solo en un ámbito que tiene de dónde heredar y con permiso', () => {
    expect(l.puedeVolverAHeredar).toBe(true);
    expect(construirLista(datos('vias_pago', VIAS, { capacidades: CONSULTA })).puedeVolverAHeredar).toBe(false);
    expect(construirLista(datos('tipos_identificacion', { proceso: '*', actividad: '*' })).puedeVolverAHeredar).toBe(false);
  });
});

describe('una lista heredada (p02-lista--heredada)', () => {
  const l = construirLista(datos('duraciones_modalidad', DURACIONES_DECANATO));

  it('hereda del proceso, dice de dónde y ofrece crear una versión propia', () => {
    expect(l.modo).toBe('heredada');
    expect(l.procedencia).toBe('Heredada');
    expect(l.heredaDe).toBe('Becas de estudio · todo el proceso');
    expect(l.puedeCrearVersionPropia).toBe(true);
    expect(l.puedeVolverAHeredar).toBe(false);
  });

  it('enseña las opciones del origen (curso: 12 a 60)', () => {
    expect(l.padreElegido).toBe('curso');
    expect(l.opciones.map((o) => o.codigo)).toEqual(['12', '24', '36', '48', '60']);
  });

  it('un delegado sin permiso en ese ámbito no puede crear la versión', () => {
    const c = capacidadesDe('x', [], [{ tipo: 'USUARIO', sujeto: 'x', proceso: PROCESO, actividades: [ACT_PAGO] }]);
    expect(construirLista(datos('duraciones_modalidad', DURACIONES_DECANATO, { capacidades: c })).puedeCrearVersionPropia).toBe(false);
  });
});

describe('cascada (p02-lista--cascada)', () => {
  const l = construirLista(datos('duraciones_modalidad', DURACIONES_PROCESO));

  it('los padres son las opciones de la lista madre, con cuántas hijas activas tiene cada una', () => {
    expect(l.padres?.map((p) => [p.etiqueta, p.cuantas])).toEqual([
      ['Curso en línea', 5],
      ['Taller presencial', 0],
    ]);
    expect(l.padreElegido).toBe('curso');
  });

  it('elegir una modalidad sin duraciones es correcto: sin hijas, y el campo no aparece', () => {
    const t = construirLista(datos('duraciones_modalidad', DURACIONES_PROCESO, { padreElegido: 'taller' }));
    expect(t.padreElegido).toBe('taller');
    expect(t.sinHijas).toBe(true);
    expect(t.etiquetaDelPadre).toBe('Taller presencial');
    expect(t.opciones).toEqual([]);
    // La vista previa sigue enseñando el campo madre: la hija no aparece.
    expect(t.vistaPrevia.map((c) => c.id)).toEqual(['previa-padre']);
  });

  it('señala las versiones propias del proceso: una actividad tiene la suya, las demás heredan', () => {
    expect(l.actividades.find((a) => a.ambito.actividad === ACT_COMITE)?.propia).toBe(true);
    expect(l.actividades.find((a) => a.ambito.actividad === ACT_DECANATO)?.propia).toBe(false);
  });

  it('los hijos cuyo padre ya no existe en el ámbito se señalan como huérfanos', () => {
    const v = valoresDeEjemplo('duraciones_modalidad');
    const huerfana: Fila = { ...v.filas[0], codigo: '99', etiqueta: '99 semanas', codigoPadre: 'posgrado', persistenceVersion: 777 };
    const m = construirLista(datos('duraciones_modalidad', DURACIONES_PROCESO, { valores: { ...v, filas: [...v.filas, huerfana] } }));
    expect(m.huerfanas).toEqual([{ etiqueta: '99 semanas', padre: 'posgrado' }]);
    expect(l.huerfanas).toEqual([]);
  });
});

describe('una versión propia envejece (T-k)', () => {
  it('avisa de cuántas opciones nuevas tiene el origen desde que se copió', () => {
    const l = construirLista(datos('duraciones_modalidad', DURACIONES_COMITE));
    expect(l.modo).toBe('propia');
    // se copió con curso|12 y curso|24; el proceso tiene además 36, 48 y 60.
    expect(l.nuevasDelOrigen).toBe(3);
  });

  it('una versión propia sin constancia de su origen no avisa de nada', () => {
    const v = valoresDeEjemplo('vias_pago');
    expect(construirLista(datos('vias_pago', VIAS, { valores: v })).nuevasDelOrigen).toBe(0);
  });
});

describe('lo que enseña de la definición', () => {
  it('quién puede editar, sin identificadores', () => {
    const l = construirLista(
      datos('vias_pago', VIAS, {
        editores: [
          { tipo: 'SUPERADMINISTRACION' },
          { tipo: 'USUARIO', sujeto: 'luis.gil', proceso: PROCESO, actividades: [] },
          { tipo: 'GRUPO', sujeto: '/academia/operaciones', incluyeSubgrupos: true, proceso: PROCESO, actividades: [ACT_PAGO] },
        ],
        nombres: { 'luis.gil': 'Luis Gil' },
      }),
    );
    expect(l.quienEdita).toEqual([
      'Superadministración',
      'Luis Gil · Becas de estudio',
      'Academia › Operaciones · Verificar los soportes y preparar el pago',
    ]);
  });

  it('la ficha de la definición guarda el código aparte, en segundo plano', () => {
    const l = construirLista(datos('vias_pago', VIAS));
    const codigo = l.definicion.find((d) => d.rotulo === 'Código');
    expect(codigo).toEqual({ rotulo: 'Código', valor: 'vias_pago', codigo: true });
    expect(l.definicion.find((d) => d.rotulo === 'Origen')?.valor).toBe('Llegó con el proceso');
  });

  it('el catálogo de ejemplo tiene definiciones de lista y de parámetro', () => {
    expect(DEFINICIONES.some((d) => d.clase === 'PARAMETRO')).toBe(true);
    expect(Object.keys(FILAS).length).toBeGreaterThan(5);
  });
});
