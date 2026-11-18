/**
 * B4 con datos REALES del kit (claves y formas capturadas del runtime, no inventadas): ningún texto que la
 * aplicación pinta —frase, quién, motivo, atributos, CSV exportado, vista previa de importación— contiene un
 * id, un código de definición ni un `|`, para cada tipo de sujeto de una delegación y cada acción sobre ella.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import Parametros from './Parametros.svelte';
import * as csv from './csv';
import { eventoDeTraza, usuariosDeLaEntrada, type EventoVM } from './historial';
import { construirVistaPrevia, etiquetasDelCsv } from './importar';
import { usosVM } from './usos';
import { quienEditaLegible } from './lista';
import { DEFINICIONES, kitDeEjemplo } from './ejemplo';
import { hashDe } from './ruta';
import { DEFINICIONES_DE_LA_CAPTURA, TRAZA_REAL, TRAZA_REAL_ACCIONES } from './trazaReal.fixture';
import { trazaACsv } from './traza';
import { DEFINICIONES_REALES, PREVIA_REAL, VALORES_REALES } from './valoresReales.fixture';
import type { Definicion, ValoresAdministracion, VistaPreviaDeImportacion } from './tipos';

vi.mock('./csv', async (original) => {
  const real = await original<typeof import('./csv')>();
  return { ...real, descargar: vi.fn(() => true) };
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const SUJETOS = {
  usuario: [{ id: 4, nombre: 'Ana Ruiz' }],
  grupo: [{ id: 2, nombre: 'Academia' }],
  rol: [{ id: 2, nombre: 'Superadministración de parámetros' }],
};
const SIN_SUJETOS = { usuario: [], grupo: [], rol: [] };

/** Todo lo que el evento enseña, junto. */
const superficies = (e: EventoVM): string[] => [
  e.texto, e.quien, e.cambio, e.motivo, e.origen, e.nombreDeLaDefinicion,
  ...e.partes.map((p) => (p.t === 'cambio' ? `${p.antes} ${p.despues}` : p.texto)),
];

/** Lo que NUNCA debe verse: `|`, el código de la clave, una cifra pegada a «·»/«:» (un id o un par grupo:rol). */
const FUGAS = [/\|/, /delegacion/i, /\d+:\d+/, /·\s*\d+(?!\s*%)\b/, /\*/];

describe('delegaciones reales de cada tipo de sujeto: ningún texto lleva ids, códigos ni «|»', () => {
  for (const [rotulo, sujetos] of [['con nombres (superadministración)', SUJETOS], ['sin nombres (quien no puede buscarlos)', SIN_SUJETOS]] as const) {
    it(rotulo, () => {
      expect(TRAZA_REAL.length).toBeGreaterThanOrEqual(10);
      for (const entrada of TRAZA_REAL) {
        const e = eventoDeTraza(entrada, { nombres: { 'super.parametros': 'Sara Parametros', 'super.parametros2': 'Sergio Parametros' }, definiciones: DEFINICIONES, sujetos });
        for (const t of superficies(e)) for (const f of FUGAS) expect(t, `${entrada.accion} ${entrada.claveNegocio} → «${t}»`).not.toMatch(f);
        expect(e.nombreDeLaDefinicion).toBe('Permisos');
        expect(e.texto).toContain('Permisos');
      }
    });
  }

  it('cuenta a quién, sobre qué y qué se hizo, con la persona y el grupo por su nombre', () => {
    const frase = (accion: string, tipo: string) => {
      const entrada = TRAZA_REAL.find((x) => x.accion === accion && (x.claveNegocio.includes(`|${tipo}|`) || tipo === '*'))!;
      return eventoDeTraza(entrada, { nombres: { 'super.parametros': 'Sara Parametros', 'super.parametros2': 'Sergio Parametros' }, definiciones: DEFINICIONES, sujetos: SUJETOS }).texto;
    };
    expect(frase('PROPONER', 'USUARIO')).toContain('propuso delegar Permisos · Ana Ruiz → Becas de estudio');
    expect(frase('PROPONER', 'GRUPO_ROL')).toContain('Superadministración de parámetros en Academia');
    expect(frase('PROPONER', 'ROL')).toContain('Superadministración de parámetros');
    expect(frase('APROBAR', 'USUARIO')).toBe('aprobó delegar Permisos · Ana Ruiz → Becas de estudio, propuesto por Sara Parametros.');
    // RECHAZAR y RETIRAR llevan la clave `*|proceso|…`: el sujeto sale de la propuesta que se decide.
    expect(frase('RECHAZAR', '*')).toContain('rechazó delegar Permisos · Superadministración de parámetros → Becas de estudio');
    expect(frase('RETIRAR', '*')).toContain('retiró su propuesta de delegar Permisos · Academia (con subgrupos) → Becas de estudio');
    expect(frase('REVOCAR', 'GRUPO_ROL')).toContain('revocó Permisos');
  });

  it('sin poder buscar nombres, dice «una persona», no el id', () => {
    const e = eventoDeTraza(TRAZA_REAL.find((x) => x.accion === 'PROPONER' && x.claveNegocio.includes('|USUARIO|'))!, { nombres: {}, definiciones: DEFINICIONES, sujetos: SIN_SUJETOS });
    expect(e.texto).toContain('una persona');
  });
});

describe('la Traza y su CSV con las entradas reales', () => {
  it('la pantalla, sus atributos y el CSV exportado no llevan ids, códigos ni «|»', async () => {
    location.hash = hashDe({ vista: 'traza' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion', trazaReal: true }) });
    await screen.findByTestId('eventos');
    // Los nombres se resuelven tras pintar: se espera a que el proponente de una aprobación deje de ser «una persona».
    await waitFor(() => expect(screen.getByTestId('eventos').textContent).toContain('propuesto por Sara Parametros'));
    const lista = screen.getByTestId('eventos');
    // La hora («14:22») no es un par grupo:rol: se mira todo lo demás.
    const sinHoras = lista.cloneNode(true) as HTMLElement;
    sinHoras.querySelectorAll('time').forEach((t) => t.remove());
    const atributos = [...lista.querySelectorAll('[title],[aria-label],[alt]')].map((n) => `${n.getAttribute('title')} ${n.getAttribute('aria-label')} ${n.getAttribute('alt')}`);
    for (const t of [sinHoras.textContent ?? '', ...atributos]) for (const f of [/\|/, /delegacion/i, /\d+:\d+/]) expect(t).not.toMatch(f);
    expect(lista.textContent).toContain('Permisos');
    // Los ids de las claves reales (4, 2, 2:2) se resuelven con lo que la superadministración puede buscar.
    expect(lista.textContent).toContain('Carla Ruiz');
    expect(lista.textContent).toContain('Analista becas en Academia');
    expect(lista.textContent).toContain('propuesto por Sara Parametros');
    await fireEvent.click(screen.getByTestId('exportar-traza'));
    const llamadas = vi.mocked(csv.descargar).mock.calls;
    expect(llamadas.length).toBe(1);
    const fichero = String(llamadas[0]![1]);
    // Cada fila del CSV empieza por su fecha-hora; el resto no lleva pares grupo:rol, `|` ni códigos.
    const sinFechas = fichero.replace(/^\d+ \w+ \d{4} · \d+:\d+,/gm, '');
    for (const f of [/\|/, /delegacion/i, /·\s*\d+:\d+/]) expect(sinFechas).not.toMatch(f);
    expect(fichero).not.toMatch(/\.\[/); // «[Por aprobar]» separado de la frase
    expect(fichero).toContain('Permisos');
    expect(fichero).toContain('propuesto por Sara Parametros');
  });
});

describe('a quién nombra una entrada real', () => {
  it('al aprobar, quien hizo el cambio y quien lo propuso: hay que resolver los dos nombres', () => {
    const aprobar = TRAZA_REAL.find((x) => x.accion === 'APROBAR')!;
    expect(usuariosDeLaEntrada(aprobar).sort()).toEqual(['super.parametros', 'super.parametros2']);
  });
});

describe('vista previa de importación con las filas reales del kit', () => {
  const valores = VALORES_REALES as unknown as Record<string, ValoresAdministracion>;
  const filas = construirVistaPrevia(PREVIA_REAL as unknown as VistaPreviaDeImportacion, DEFINICIONES_REALES as unknown as Definicion[], valores).filas;

  it('la columna Opción dice «Curso en línea / 12 semanas», no «curso · 12»', () => {
    expect(filas.length).toBe(3);
    expect(filas[0]!.opcion).toBe('Curso en línea / 12 semanas');
    for (const f of filas) {
      expect(f.opcion).not.toMatch(/·|\*|^\w+ \/ \d+$/);
      expect(f.detalle).toContain('Cambia el nombre de');
    }
  });

  it('sin los valores leídos cae al código que la persona escribió, nunca a un id', () => {
    const sinValores = construirVistaPrevia(PREVIA_REAL as unknown as VistaPreviaDeImportacion, DEFINICIONES_REALES as unknown as Definicion[], {}).filas;
    expect(sinValores[0]!.opcion).toBe('curso / 12');
  });
});

describe('quién puede editar: editores de cada tipo, con las formas del kit', () => {
  const E = (tipo: 'USUARIO' | 'GRUPO' | 'ROL' | 'GRUPO_ROL', sujeto: string) => ({ tipo, sujeto, proceso: 'Becas de estudio', actividades: [] as string[], vigenteHasta: null, incluyeSubgrupos: false });
  const frases = quienEditaLegible(
    [E('ROL', 'jefeEvaluacionBis'), E('GRUPO', '/academia/evaluacion/curso'), E('GRUPO_ROL', 'jefeEvaluacion en /academia/evaluacion'), E('USUARIO', 'sin.nombre'), E('USUARIO', 'ana.perez')],
    { 'ana.perez': 'Ana Pérez' },
  );
  it('un rol delegado no sale con su nombre técnico, un grupo no sale con su ruta', () => {
    expect(frases[0]).toContain('Jefe evaluacion bis');
    expect(frases[1]).toContain('Academia › Evaluacion › Curso');
    expect(frases[2]).toContain('Academia › Evaluacion · Jefe evaluacion');
    expect(frases[4]).toContain('Ana Pérez');
  });
  it('ninguna frase lleva nombres técnicos de rol ni rutas', () => {
    for (const f of frases.slice(0, 3)) for (const mala of [/jefeEvaluacion/, /\//, /_/]) expect(f).not.toMatch(mala);
  });
});

describe('opción nueva y tipo de uso desconocido', () => {
  it('una opción nueva en la vista previa sale por la etiqueta del CSV, no por su código', () => {
    const csv = 'definicion,proceso,actividad,codigoPadre,codigo,etiqueta\nduraciones_por_modalidad_sintetico,*,*,curso,72,72 semanas\n';
    const previa = { resumen: { altas: 1, cambios: 0, bajas: 0, sinsambios: 0 }, huella: 'h', filas: [{ fila: 2, clase: 'ALTA', definicion: 'duraciones_por_modalidad_sintetico', proceso: '*', actividad: '*', codigoPadre: 'curso', codigo: '72', detalle: 'nueva' }] };
    const f = construirVistaPrevia(previa as unknown as VistaPreviaDeImportacion, DEFINICIONES_REALES as unknown as Definicion[], VALORES_REALES as unknown as Record<string, ValoresAdministracion>, etiquetasDelCsv(csv)).filas;
    expect(f[0]!.opcion).toBe('Curso en línea / 72 semanas');
  });
  it('un tipo de uso que el módulo no conoce no pinta «undefined»', () => {
    const vm = usosVM({ lugares: [{ tipo: 'NOTIFICACION', titulo: 'Aviso al cliente', detalle: 'x' }], expedientes: [] }, new Map(), new Set());
    expect(vm.lugares[0]!.tipo).toBe('Otro uso');
    expect(JSON.stringify(vm)).not.toContain('undefined');
  });
});

describe('quién puede editar con editores que se leen igual', () => {
  const E = (tipo: 'USUARIO' | 'ROL', sujeto: string) => ({ tipo, sujeto, proceso: 'Proceso sintetico de parametros', actividades: [] as string[], vigenteHasta: null });
  it('dos roles que se humanizan igual no dan dos líneas idénticas, y los homónimos tampoco', () => {
    const f = quienEditaLegible([{ tipo: 'SUPERADMINISTRACION' } as never, E('ROL', 'jefeEvaluacion'), E('ROL', 'jefe_evaluacion'), E('USUARIO', 'ana.ruiz'), E('USUARIO', 'ana.ruiz2')], { 'ana.ruiz': 'Ana Ruiz', 'ana.ruiz2': 'Ana Ruiz' });
    expect(new Set(f).size).toBe(f.length);
    expect(f[0]).toBe('Superadministración');
    expect(f[1]).toContain('(jefeEvaluacion)');
    expect(f[3]).not.toBe(f[4]);
  });
});

describe('cada acción real sobre un valor, una lista o una importación se lee con sus datos', () => {
  const ctx = { nombres: { 'super.parametros': 'Sara Parametros', 'super.parametros2': 'Sergio Parametros' }, definiciones: DEFINICIONES_DE_LA_CAPTURA as unknown as Definicion[], sujetos: SIN_SUJETOS };
  const eventos = TRAZA_REAL_ACCIONES.map((e) => eventoDeTraza(e, ctx));

  it('hay una entrada real de cada acción (si falta una, la captura se quedó corta)', () => {
    const acciones = new Set(TRAZA_REAL_ACCIONES.map((e) => e.accion));
    for (const a of ['APROBAR', 'RECHAZAR', 'RETIRAR', 'PROPONER', 'EDITAR', 'CREAR', 'DESACTIVAR', 'REACTIVAR', 'ORDENAR', 'CREAR_VERSION_PROPIA', 'VOLVER_A_HEREDAR']) expect(acciones.has(a), a).toBe(true);
  });

  it('aprobar un valor dice «antes → después» con las dos cifras: nunca «—» donde hay dato', () => {
    const i = TRAZA_REAL_ACCIONES.findIndex((e) => e.accion === 'APROBAR');
    const e = eventos[i]!;
    expect(e.texto).toMatch(/US\$[\d,]+ → US\$[\d,]+/);
    expect(e.cambio).toMatch(/^US\$[\d,]+ → US\$[\d,]+$/);
    expect(e.texto).not.toContain('—');
    expect(e.cambio).not.toContain('—');
  });

  it('ninguna frase ni cambio lleva «—» ni «undefined» ni «[object» ni «|»', () => {
    for (const [i, e] of eventos.entries()) for (const t of [e.texto, e.cambio, e.quien, e.nombreDeLaDefinicion]) expect(t, `${TRAZA_REAL_ACCIONES[i]!.accion} → «${t}»`).not.toMatch(/—|undefined|\[object|\|/);
  });

  it('el CSV de esas entradas tampoco lleva «—» donde hay dato', () => {
    const csv = trazaACsv(eventos);
    expect(csv).not.toContain('—');
  });
});
