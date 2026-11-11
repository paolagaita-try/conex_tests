/**
 * El modelo del inicio: qué grupos y qué filas ve cada perfil. Con los datos ficticios de
 * `p01`, `p10` y `p11` y la expectativa escrita aquí, no importada del módulo.
 */
import { describe, expect, it } from 'vitest';
import { cadenaDe, GLOBAL } from './ambitos';
import { capacidadesDe, CONSULTA, puedeEditarEn } from './capacidades';
import { construirInicio, type DatosDelInicio } from './inicio';
import { ACT_PAGO, DEFINICIONES, FILAS, OTRO_PROCESO, PROCESO, PROCESOS, PROPUESTAS } from './ejemplo';
import { ROL_DE_SUPERADMINISTRACION } from './capacidades';

const datos: DatosDelInicio = {
  definiciones: DEFINICIONES,
  valores: Object.fromEntries(DEFINICIONES.map((d) => [d.codigo, { definicion: d, filas: FILAS[d.codigo] ?? [] }])),
  procesos: PROCESOS,
  pendientes: PROPUESTAS,
  ultimos: {},
};
const SUPER = capacidadesDe('marta.rivas', [{ rol: ROL_DE_SUPERADMINISTRACION, grupo: '/academia/evaluacion' }], []);
const DELEGADO = capacidadesDe('luis.gil', [], [{ tipo: 'USUARIO', sujeto: 'luis.gil', proceso: PROCESO, actividades: [], vigenteHasta: null }]);

const titulos = (i: ReturnType<typeof construirInicio>) => i.grupos.map((g) => g.titulo);
const nombres = (i: ReturnType<typeof construirInicio>) => i.grupos.flatMap((g) => g.filas.map((f) => f.nombre));

describe('capacidades de la sesión', () => {
  it('el rol de superadministración, con su nombre exacto, es superadministración', () => {
    expect(SUPER.perfil).toBe('superadministracion');
    expect(capacidadesDe('x', [{ rol: 'superAdministradorParametrosX', grupo: '/a' }], []).perfil).toBe('consulta');
  });

  it('una delegación a la persona la hace delegada de ESE proceso y de nada más', () => {
    expect(DELEGADO.perfil).toBe('delegado');
    expect(puedeEditarEn(DELEGADO, { proceso: PROCESO, actividad: ACT_PAGO })).toBe(true);
    expect(puedeEditarEn(DELEGADO, { proceso: OTRO_PROCESO, actividad: '*' })).toBe(false);
    expect(puedeEditarEn(DELEGADO, GLOBAL)).toBe(false);
  });

  it('una delegación de actividades no alcanza al resto del proceso ni al ámbito del proceso', () => {
    const c = capacidadesDe('x', [], [{ tipo: 'USUARIO', sujeto: 'x', proceso: PROCESO, actividades: [ACT_PAGO] }]);
    expect(puedeEditarEn(c, { proceso: PROCESO, actividad: ACT_PAGO })).toBe(true);
    expect(puedeEditarEn(c, { proceso: PROCESO, actividad: '*' })).toBe(false);
  });

  it('grupo con subgrupos usa la frontera «/»: /academia/evaluacion casa con /academia/evaluacion/curso y no con /academia/evaluaciones-op', () => {
    const e = [{ tipo: 'GRUPO' as const, sujeto: '/academia/evaluacion', incluyeSubgrupos: true, proceso: PROCESO, actividades: [] }];
    expect(capacidadesDe('x', [{ rol: 'member', grupo: '/academia/evaluacion/curso' }], e).perfil).toBe('delegado');
    expect(capacidadesDe('x', [{ rol: 'member', grupo: '/academia/evaluaciones-op' }], e).perfil).toBe('consulta');
    const sin = [{ ...e[0], incluyeSubgrupos: false }];
    expect(capacidadesDe('x', [{ rol: 'member', grupo: '/academia/evaluacion/curso' }], sin).perfil).toBe('consulta');
  });

  it('«rol en grupo» exige las dos cosas', () => {
    const e = [{ tipo: 'GRUPO_ROL' as const, sujeto: 'Jefe de evaluación en /academia/evaluacion', incluyeSubgrupos: false, proceso: PROCESO, actividades: [] }];
    expect(capacidadesDe('x', [{ rol: 'Jefe de evaluación', grupo: '/academia/evaluacion' }], e).perfil).toBe('delegado');
    expect(capacidadesDe('x', [{ rol: 'Analista', grupo: '/academia/evaluacion' }], e).perfil).toBe('consulta');
    expect(capacidadesDe('x', [{ rol: 'Jefe de evaluación', grupo: '/academia/ops' }], e).perfil).toBe('consulta');
  });

  it('sin nada que lo case, la persona queda en consulta (el caso más conservador)', () => {
    expect(capacidadesDe('x', [], [{ tipo: 'USUARIO', sujeto: 'otra.persona', proceso: PROCESO, actividades: [] }])).toEqual(CONSULTA);
  });
});

describe('el ámbito y su cadena', () => {
  it('actividad → proceso → global', () => {
    expect(cadenaDe({ proceso: PROCESO, actividad: ACT_PAGO })).toEqual([
      { proceso: PROCESO, actividad: ACT_PAGO },
      { proceso: PROCESO, actividad: '*' },
      GLOBAL,
    ]);
    expect(cadenaDe(GLOBAL)).toEqual([GLOBAL]);
  });
});

describe('inicio de la superadministración (p01)', () => {
  const i = construirInicio(datos, SUPER);

  it('agrupa por ámbito: globales, el proceso y su actividad, y un proceso sin parámetros al final', () => {
    expect(titulos(i)[0]).toBe('Globales · valen para todos los procesos');
    expect(titulos(i)).toContain('Becas de estudio · todo el proceso');
    expect(titulos(i)).toContain('Becas de estudio · Verificar los soportes y preparar el pago');
    expect(titulos(i).at(-1)).toBe('Inscripción a cursos · todo el proceso');
  });

  it('un proceso descubierto del motor sin parámetros aparece como «sin parámetros»', () => {
    const g = i.grupos.find((x) => x.ambito.proceso === OTRO_PROCESO);
    expect(g?.sinParametros).toBe(true);
    expect(g?.filas).toEqual([]);
  });

  it('cada fila trae lo que el inicio enseña, ya escrito: tipo, contenido, impacto alto y cambio por aprobar', () => {
    const filas = i.grupos.flatMap((g) => g.filas);
    const porcentaje = filas.find((f) => f.codigo === 'porcentaje_beca' && f.ambito.proceso === PROCESO);
    expect(porcentaje?.tipo).toBe('Parámetro');
    expect(porcentaje?.contenido).toBe('35 %');
    expect(porcentaje?.impactoAlto).toBe(true);
    expect(porcentaje?.porAprobar).toBe(true);
    const vias = filas.find((f) => f.codigo === 'vias_pago');
    expect(vias?.contenido).toBe('4 opciones, 1 inactiva');
    const duraciones = filas.find((f) => f.codigo === 'duraciones_modalidad' && f.ambito.actividad === '*');
    expect(duraciones?.tipo).toBe('Lista en cascada de Modalidades');
    expect(duraciones?.conVersionPropia).toBe(1);
    const sedes = filas.find((f) => f.codigo === 'sedes');
    expect(sedes?.dependientes).toBe('Aulas');
  });

  it('un parámetro con valor propio en un proceso no repite su valor global en «Globales»', () => {
    const globales = i.grupos.find((g) => g.ambito.proceso === '*');
    expect(globales?.filas.map((f) => f.codigo)).not.toContain('porcentaje_beca');
  });

  it('las filas llevan las claves que las vistas devuelven, sin ningún número suelto', () => {
    const filas = i.grupos.flatMap((g) => g.filas);
    for (const f of filas) {
      expect(typeof f.clave).toBe('string');
      for (const v of Object.values(f)) expect(typeof v === 'number' && !Number.isInteger(v)).toBe(false);
    }
    expect(new Set(filas.map((f) => f.clave)).size).toBe(filas.length);
  });

  it('el filtro de listas deja solo listas y el de parámetros solo parámetros', () => {
    expect(nombres(construirInicio(datos, SUPER, 'listas')).includes('Porcentaje máximo de beca')).toBe(false);
    expect(nombres(construirInicio(datos, SUPER, 'parametros'))).toEqual(
      expect.arrayContaining(['Porcentaje máximo de beca', 'Tope de aprobación del coordinador']),
    );
    expect(nombres(construirInicio(datos, SUPER, 'parametros')).includes('Sedes')).toBe(false);
  });

  it('buscar sin tildes ni mayúsculas encuentra por el nombre de negocio', () => {
    expect(nombres(construirInicio(datos, SUPER, 'todo', 'PAGO'))).toEqual(['Vías de pago']);
    expect(nombres(construirInicio(datos, SUPER, 'todo', 'identificacion'))).toEqual(['Tipos de identificación']);
  });

  it('buscar algo que no existe deja 0 visibles pero conserva el total (para decir «nada coincide»)', () => {
    const v = construirInicio(datos, SUPER, 'todo', 'posgrado');
    expect(v.visibles).toBe(0);
    expect(v.total).toBeGreaterThan(0);
    expect(v.grupos).toEqual([]);
  });

  it('con filtro o búsqueda activos no se enseñan los procesos sin parámetros', () => {
    expect(construirInicio(datos, SUPER, 'listas').grupos.some((g) => g.sinParametros)).toBe(false);
  });
});

describe('inicio del delegado (p10) y de la consulta (p11)', () => {
  it('el delegado ve primero lo que puede editar y al final lo global en solo lectura', () => {
    const i = construirInicio(datos, DELEGADO);
    const ultimo = i.grupos.at(-1);
    expect(ultimo?.titulo).toBe('Globales · solo lectura');
    expect(ultimo?.filas.every((f) => f.soloLectura)).toBe(true);
    expect(i.grupos[0].editable).toBe(true);
  });

  it('«lo que puedo editar» quita lo global', () => {
    const i = construirInicio(datos, DELEGADO, 'editable');
    expect(i.grupos.some((g) => g.ambito.proceso === '*')).toBe(false);
  });

  it('un proceso sin parámetros no se enseña a quien no puede conectarlo (delegado y consulta)', () => {
    expect(construirInicio(datos, DELEGADO).grupos.some((g) => g.sinParametros)).toBe(false);
    expect(construirInicio(datos, CONSULTA).grupos.some((g) => g.sinParametros)).toBe(false);
  });

  it('la consulta lo ve todo en solo lectura', () => {
    const i = construirInicio(datos, CONSULTA);
    expect(i.grupos.flatMap((g) => g.filas).every((f) => f.soloLectura)).toBe(true);
  });
});
