/**
 * Lenguaje de negocio: lo que el kit sirve CRUDO —códigos, logins, roles técnicos, `detalle` de la
 * importación, la moneda como código— se traduce en la aplicación. Cada caso parte del crudo real del kit
 * (los mismos textos que escribe `Importador.groovy`), no de un texto ya limpio.
 */
import { describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/svelte';
import { afterEach } from 'vitest';
import Parametros from './Parametros.svelte';
import { eventoDeTraza } from './historial';
import { construirVistaPrevia, detalleLegible } from './importar';
import { valorLegible } from './formatos';
import { esNodoTecnico, nombreDeRol, sujetoLegible } from './nombres';
import { filtrar, SIN_FILTROS } from './traza';
import { DEFINICIONES, kitDeEjemplo } from './ejemplo';
import { hashDe } from './ruta';
import type { EntradaDeTraza } from './tipos';

afterEach(cleanup);

const MONTO = { tipoDato: 'MONTO' as const, unidad: 'USD' };

describe('importación: el detalle crudo del kit en lenguaje de negocio', () => {
  const def = DEFINICIONES.find((d) => d.codigo === 'porcentaje_beca');
  it.each([
    ['codigo: código repetido: ya está en la fila 3', 'Código repetido: ya está en la fila 3'],
    ['definicion: no existe una definición activa «x»', 'No existe una definición activa «x»'],
    ['etiqueta «Web» → «Sitio web» · orden 1 → 9', 'Cambia el nombre de «Web» a «Sitio web» · Cambia la posición de 1 a 9'],
    ['datos.etiqueta: es obligatorio', 'Nombre: es obligatorio'],
    ['se desactiva, no se borra', 'Se da de baja (no se borra)'],
    ['coincide con lo guardado', 'Sin cambios: ya coincide con lo guardado'],
    ['queda como propuesta: impacto alto', 'Queda como propuesta: otra persona tiene que aprobarla'],
    ['CONFLICTO: guardado por ana en 2026-09-01', 'Otra persona lo cambió mientras tanto'],
  ])('%s', (crudo, legible) => {
    expect(detalleLegible(crudo, def)).toBe(legible);
  });

  it('un valor con su unidad, no «1600000.00»', () => {
    const d = DEFINICIONES.find((x) => x.tipoDato === 'MONTO') ?? def;
    expect(detalleLegible('valor 1500000.00 → 1600000.00', d)).not.toContain('1600000.00');
  });

  it('la fila de un parámetro (código «*») no enseña asteriscos y el crudo no se cuela', () => {
    const vm = construirVistaPrevia(
      { resumen: { altas: 0, cambios: 1, bajas: 0, sinCambios: 0, propuestas: 0, errores: 0 }, huella: 'h', filas: [{ fila: 2, clase: 'CAMBIO', definicion: 'porcentaje_beca', proceso: '*', actividad: '*', codigoPadre: '*', codigo: '*', detalle: 'valor 35 → 30' }] },
      DEFINICIONES,
    );
    expect(vm.filas[0]!.opcion).not.toContain('*');
    expect(vm.filas[0]!.detalle).not.toMatch(/^valor /);
  });
});

describe('moneda y roles', () => {
  it('el código de la moneda se lee como símbolo: US$, no «USD»', () => {
    expect(valorLegible(MONTO, '1500000.00')).toMatch(/^US\$/);
    expect(valorLegible(MONTO, '1500000.00')).not.toContain('USD');
  });
  it('un código de moneda desconocido se separa del número', () => {
    expect(valorLegible({ tipoDato: 'MONTO', unidad: 'CHF' }, '10')).toMatch(/^CHF /);
  });
  it.each([
    ['member', 'Miembro'],
    ['superAdministradorParametros', 'Superadministración de parámetros'],
    ['jefeEvaluacion', 'Jefe evaluacion'],
  ])('%s → %s', (crudo, legible) => expect(nombreDeRol(crudo)).toBe(legible));
});

describe('traza: una propuesta de delegación', () => {
  const entrada: EntradaDeTraza = {
    id: 5, fechaHora: '2026-09-27T14:30:00.000Z', usuario: 'sara', rolesVigentes: null, accion: 'PROPONER',
    claveNegocio: 'delegacion|GRUPO_ROL|/academia/evaluacion|jefeEvaluacion|Becas de estudio'.replace('|jefeEvaluacion|', '|'),
    valorAnterior: null, valorNuevo: null, motivo: 'm', origen: 'PANTALLA', lote: null, hashAnterior: 'a', hash: 'b',
  };
  it('no cita el código interno «delegacion» y deja espacio entre las partes', () => {
    const e = eventoDeTraza(entrada, { nombres: { sara: 'Sara Parametros' }, definiciones: DEFINICIONES });
    expect(e.texto).toContain('propuso delegar Permisos');
    expect(e.texto).not.toContain('delegacion');
    expect(e.texto).not.toMatch(/cambiar«/);
  });
  it('una frase de cambio de valor lleva espacio entre el verbo y el nombre', () => {
    const e = eventoDeTraza({ ...entrada, claveNegocio: 'porcentaje_beca|*|*|*|*', valorNuevo: { valorPropuesto: { datos: { valor: '30' } } } }, { nombres: {}, definiciones: DEFINICIONES });
    expect(e.partes.map((p) => (p.t === 'texto' || p.t === 'fuerte' ? p.texto : '')).join('')).toMatch(/propuso cambiar «/);
  });
});

describe('nueva delegación: personas y roles en lenguaje de negocio', () => {
  it('las personas por su nombre y los roles sin nombres técnicos', async () => {
    location.hash = hashDe({ vista: 'nuevaDelegacion' });
    render(Parametros, { kit: kitDeEjemplo({ perfil: 'superadministracion' }) });
    await fireEvent.click(await screen.findByRole('radio', { name: 'Un rol' }).catch(() => screen.getByText('Un rol')));
    await fireEvent.input(screen.getByRole('combobox', { name: /^Rol/ }), { target: { value: 'je' } });
    await screen.findAllByRole('option', { name: /Jefe evaluacion/ });
    const roles = [...within(screen.getByRole('listbox', { name: /Rol/ })).getAllByRole('option')].map((o) => o.textContent ?? '');
    expect(roles.join('|')).toContain('Jefe evaluacion');
    expect(roles.join('|')).not.toMatch(/member|jefeEvaluacion|superAdministradorParametros/);
  });
});

describe('grupos y sujetos de delegación', () => {
  it.each([
    ['/academia/evaluacion/curso', 'Academia › Evaluacion › Curso'],
    ['jefeEvaluacion en /academia/evaluacion', 'Academia › Evaluacion · Jefe evaluacion'],
    ['Becas', 'Becas'],
  ])('%s → %s', (crudo, legible) => expect(sujetoLegible(crudo)).toBe(legible));
});

describe('traza: el filtro «Hasta» incluye ese día', () => {
  it('deja fuera lo posterior y conserva lo del propio día', () => {
    const e = (cuandoIso: string) => ({ cuandoIso }) as never;
    const r = filtrar([e('2026-09-01T10:00:00Z'), e('2026-09-02T23:59:00Z'), e('2026-09-03T00:01:00Z')], { ...SIN_FILTROS, hasta: '2026-09-02' });
    expect(r.map((x) => (x as unknown as { cuandoIso: string }).cuandoIso)).toEqual(['2026-09-01T10:00:00Z', '2026-09-02T23:59:00Z']);
  });
});

describe('el prefijo de un campo de monto', () => {
  it('«USD» se lee US$ también al editar', async () => {
    const { simboloDeMoneda } = await import('./formatos');
    expect(simboloDeMoneda('USD')).toBe('US$');
    expect(simboloDeMoneda(null)).toBe('US$');
  });
});

describe('nodos técnicos del motor', () => {
  it.each([['Fin'], ['inicio'], ['CALCULAR TOPE, FIN'], ['Fin del proceso']])('«%s» no se ofrece como actividad', (n) => expect(esNodoTecnico(n)).toBe(true));
  it.each([['F8 Aprobar beca completa (Comite academico)'], ['Decision academica (3 salidas)'], ['F0 Inicio de solicitud por canal']])('«%s» sí', (n) => expect(esNodoTecnico(n)).toBe(false));
});
