import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/svelte';
import CamposDeContrato from './CamposDeContrato.svelte';

import { CONTRATOS, DECISION, RAMAS, REGISTRO, type CampoDeContrato } from '$pruebas/contratosDeEjemplo';
import type { ValoresDelFormulario } from '$lib/ui/valores';
import { lectorDelModulo } from '$pruebas/moduloDeParametros';

/**
 * El contrato dicho en el idioma del usuario — hallazgos de una revisión de usabilidad.
 *
 * Lo que se medía en pantalla, delante de quien aprueba:
 *
 *     Obligatorio sí al aprobar · > 0; DECIMAL (long no aplica a contratos de task — doc
 *     contracts)
 *
 * y los cuatro campos condicionales de la decisión visibles a la vez, con el usuario
 * deduciendo cuáles le tocaban.
 *
 * Los campos de entrada son contratos con la forma de los generados (`$pruebas/contratosDeEjemplo`),
 * con las formas difíciles que traen los reales. Y se verifica por el DOM renderizado,
 * que es lo que ve la persona, no por las funciones internas del componente.
 *
 * Svelte avisa aquí de `binding_property_non_reactive`: el estado de los campos lo pasa un
 * objeto plano porque un `.test.ts` no puede declarar runas. Es propio del test, no del
 * componente —en la pantalla real `valores` es `$state`—, y por eso el cambio de valores se
 * provoca con `rerender`, que sí atraviesa los props.
 */

type Campo = CampoDeContrato;

/**
 * Un estado con TODO elegido: la primera opción de cada conjunto cerrado y toda casilla
 * marcada. Sirve para forzar la aparición de los campos condicionales — un test que solo
 * mirase la pantalla recién abierta no vería nunca la ayuda de los campos que se revelan.
 */
function todoElegido(campos: readonly Campo[]): ValoresDelFormulario {
  const valores: ValoresDelFormulario = {};
  for (const campo of campos) {
    const conjunto = campo.constraint.match(/∈\s*\{([^}]+)\}/);
    if (conjunto) valores[campo.ruta] = conjunto[1].split(',')[0].trim();
    else if (campo.tipo === 'BOOLEAN') valores[campo.ruta] = true;
  }
  return valores;
}

/**
 * Una elección por cada valor posible de cada conjunto del contrato.
 *
 * Lineal, no cartesiano: se varía un campo de conjunto cada vez y los demás se dejan en su
 * primera opción. Basta para que **todo** campo condicional se pinte al menos una vez, que
 * es lo que el barrido de jerga necesita para no ser una red declarada que nadie ejecuta.
 */
function variantesDeEleccion(campos: readonly Campo[]): ValoresDelFormulario[] {
  const base = todoElegido(campos);
  const variantes = [base];
  for (const campo of campos) {
    const conjunto = campo.constraint.match(/∈\s*\{([^}]+)\}/);
    if (!conjunto) continue;
    for (const valor of conjunto[1].split(',').map((v) => v.trim()).filter(Boolean)) {
      if (base[campo.ruta] === valor) continue;
      variantes.push({ ...base, [campo.ruta]: valor });
    }
  }
  return variantes;
}


describe('CamposDeContrato · la ayuda que se muestra', () => {
  it('no vuelca en la pantalla la nota de implementación del contrato', () => {
    // Los días aprobados traen «> 0; DECIMAL (long no aplica a contratos de task — doc
    // contracts)». Se pinta con la decisión ya tomada para que el campo esté visible.
    const { container, queryByText } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: { 'decision.resultado': 'aprobar' } },
    });

    const texto = container.textContent ?? '';
    expect(texto).toContain('Días aprobados');
    expect(texto).not.toContain('long no aplica');
    expect(texto).not.toContain('DECIMAL');
    expect(texto).not.toContain('doc contracts');
    // Y no queda un resto de la notación: sin nada que decir, el campo va sin ayuda.
    expect(queryByText(/> 0/)).toBeNull();
  });

  it('dice el límite de un texto en caracteres, con el separador de miles del español', () => {
    // «≤ 2000» es notación; «Máximo 2.000 caracteres» es lo que necesita saber quien
    // escribe la justificación.
    const { getByText, queryByText } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: {} },
    });

    expect(getByText('Máximo 2.000 caracteres')).toBeTruthy();
    expect(queryByText(/≤/)).toBeNull();
  });

  it('escribe la condición de obligatoriedad como se habla, sin el «sí» de la columna', () => {
    // El plazo aprobado es una lista del módulo; con tarea y lector el campo existe (cargando) y lleva su ayuda.
    const { getAllByText, getByText, queryByText } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: { 'decision.resultado': 'aprobar' }, tarea: '8', lector: lectorDelModulo, ramas: RAMAS },
    });

    // Los días y el anticipo: los dos campos que el contrato exige «sí al aprobar» sin más.
    expect(getAllByText('Obligatorio al aprobar')).toHaveLength(2);
    // La rama se conserva mientras no sepamos de qué rama es el caso.
    expect(getByText('Obligatorio al aprobar (anual)')).toBeTruthy();
    expect(queryByText(/Obligatorio sí/)).toBeNull();
  });

  it('traduce la obligatoriedad condicional inversa en vez de volcarla literal', () => {
    // Un contrato puede escribir la obligatoriedad de `observacion` como «no (sí si no
    // completado)»: la respuesta a la pregunta de la columna, con la excepción entre
    // paréntesis. Volcada tal cual, la persona lee «Obligatorio no (sí si no completado)»,
    // que además de ilegible dice lo contrario de lo que pasa: ese campo SÍ es obligatorio en
    // el caso que importa —cuando el registro no se completa y hay que documentar por qué—.
    const observacion = REGISTRO.find((c) => c.nombre === 'observacion')!;
    const { container } = render(CamposDeContrato, {
      props: { campos: [observacion], valores: {} },
    });

    const ayuda = container.textContent ?? '';
    expect(ayuda).not.toContain('no (sí si');
    expect(ayuda).toContain('Obligatorio si no completado');
  });

  it('no muestra ayuda donde el contrato no tiene constraint («—»)', () => {
    const campos = [
      {
        ruta: 'registro.completado',
        grupo: 'registro',
        nombre: 'completado',
        tipo: 'BOOLEAN',
        multiple: false,
        obligatorio: 'sí',
        requeridoSiempre: true,
        constraint: '—',
      },
    ] as const;

    const { queryByText } = render(CamposDeContrato, { props: { campos, valores: {} } });
    expect(queryByText('—')).toBeNull();
  });

  it('conserva el motivo de una casilla y descarta la cita de la regla', () => {
    const campos = [
      {
        ruta: 'entrega.conformidadValidada',
        grupo: 'entrega',
        nombre: 'conformidadValidada',
        tipo: 'BOOLEAN',
        multiple: false,
        obligatorio: 'sí',
        requeridoSiempre: true,
        constraint: 'debe ser `true` (entrega a la persona, RN-20)',
      },
    ] as const;

    const { getByText, queryByText } = render(CamposDeContrato, { props: { campos, valores: {} } });
    expect(getByText('Debe marcarla (entrega a la persona)')).toBeTruthy();
    expect(queryByText(/RN-20/)).toBeNull();
  });

  it('ninguna pantalla deja escapar jerga del interior', () => {
    // Barrido sobre los contratos de ejemplo, con todo elegido para que ningún campo
    // condicional se quede sin pintar. La expectativa NO sale del componente: es la lista
    // de marcas de implementación que la revisión encontró y que jamás debe verse.
    const JERGA = [
      /\blong\b/i,
      /\bDECIMAL\b/,
      /\bINTEGER\b/,
      /\bBOOLEAN\b/,
      // El nombre del almacén de datos del motor: la ayuda de un campo filtraba
      // «≤ 255 (límite del campo BDM)» a la pantalla de quien decide.
      /\bBDM\b/i,
      /\bdoc contracts?\b/i,
      /\bJSON\b/,
      /\[PARAM\]/,
      // Identificadores de reglas o decisiones («RN-12»).
      /\b[A-Z]{2,4}-\d/,
      /`/,
      /∈/,
      /≤/,
      /≥/,
      /Obligatorio sí/,
    ];

    for (const [pantalla, campos] of Object.entries(CONTRATOS)) {
      // Una sola pasada con la PRIMERA opción de cada conjunto dejaba la red inerte para
      // los campos condicionales: la decisión pinta «motivoExcepcion» solo al derivar por
      // excepción, y con `resultado: 'aprobar'` ese campo —y su constraint
      // «≤ 255 (límite del campo BDM)»— no se renderizaba nunca. La marca se colaba a la
      // pantalla con el test en verde. Se recorre cada valor de cada conjunto para que
      // todo campo condicional llegue a pintarse al menos una vez.
      for (const valores of variantesDeEleccion(campos)) {
        const { container, unmount } = render(CamposDeContrato, { props: { campos, valores } });
        const texto = container.textContent ?? '';
        for (const marca of JERGA) {
          expect(marca.test(texto), `«${pantalla}» muestra ${marca} en «${texto}»`).toBe(false);
        }
        unmount();
      }
    }
  });
});

describe('CamposDeContrato · los campos condicionales', () => {
  it('no pinta el campo que aún no aplica y lo pinta cuando la decisión lo pide', async () => {
    const { queryByLabelText, getByLabelText, rerender } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: {} },
    });

    // Sin decidir: solo lo que el contrato exige siempre.
    expect(getByLabelText(/Resultado/)).toBeTruthy();
    expect(queryByLabelText(/Días aprobados/)).toBeNull();
    expect(queryByLabelText(/Anticipo aprobado/)).toBeNull();

    await rerender({ valores: { 'decision.resultado': 'aprobar' } });

    expect(getByLabelText(/Días aprobados/)).toBeTruthy();
    expect(getByLabelText(/Anticipo aprobado/)).toBeTruthy();
  });

  it('mantiene oculto lo que la decisión tomada no pide', async () => {
    const { queryByLabelText, rerender } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: { 'decision.resultado': 'rechazar' } },
    });

    expect(queryByLabelText(/Días aprobados/)).toBeNull();

    // `aprobar_condicionado` también es aprobar: ahí las cifras hacen falta.
    await rerender({ valores: { 'decision.resultado': 'aprobar_condicionado' } });
    expect(queryByLabelText(/Días aprobados/)).toBeTruthy();
  });

  it('sin saber la rama del caso no oculta por rama: no inventa el dato que no recibió', () => {
    const { getByLabelText } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: { 'decision.resultado': 'aprobar' }, ramas: RAMAS },
    });

    expect(getByLabelText(/Plazo aprobado/)).toBeTruthy();
    expect(getByLabelText(/Horas aprobadas/)).toBeTruthy();
  });

  it('con la rama conocida deja solo la rama del caso', () => {
    const { getByLabelText, queryByLabelText } = render(CamposDeContrato, {
      props: {
        campos: DECISION,
        valores: { 'decision.resultado': 'aprobar' },
        ramas: RAMAS,
        producto: 'anual',
      },
    });

    expect(getByLabelText(/Plazo aprobado/)).toBeTruthy();
    expect(queryByLabelText(/Horas aprobadas/)).toBeNull();
  });

  it('sin ramas declaradas, un paréntesis no oculta nada aunque llegue la rama del caso', () => {
    const { getByLabelText } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: { 'decision.resultado': 'aprobar' }, producto: 'anual' },
    });

    expect(getByLabelText(/Horas aprobadas/)).toBeTruthy();
  });

  it('nunca oculta un campo que el contrato exige siempre, diga lo que diga su texto', () => {
    // La red de seguridad de «0 campos huérfanos»: con `requeridoSiempre` no hay
    // condición que valga, ni aunque el texto se parezca a una.
    const campos = [
      {
        ruta: 'revision.observaciones',
        grupo: 'revision',
        nombre: 'observaciones',
        tipo: 'TEXT',
        multiple: false,
        obligatorio: 'sí al aprobar',
        requeridoSiempre: true,
        constraint: '≤ 2000',
      },
    ] as const;

    const { getByLabelText } = render(CamposDeContrato, { props: { campos, valores: {} } });
    expect(getByLabelText(/Observaciones/)).toBeTruthy();
  });

  it('no oculta una condición que ningún campo del grupo puede decidir', () => {
    // «sí por perfil» no es una condición evaluable aquí; ocultar por lo que no se sabe
    // dejaría un campo del contrato fuera de la pantalla para siempre.
    const campos = [
      {
        ruta: 'documentos.archivo',
        grupo: 'documentos',
        nombre: 'archivo',
        tipo: 'FILE',
        multiple: true,
        obligatorio: 'sí por perfil',
        requeridoSiempre: false,
        constraint: '—',
      },
    ] as const;

    const { getByLabelText } = render(CamposDeContrato, { props: { campos, valores: {} } });
    expect(getByLabelText(/Archivo/)).toBeTruthy();
  });
});

describe('CamposDeContrato · el título del grupo', () => {
  it('escribe el grupo del contrato en español, con su tilde', () => {
    const { getByText, queryByText } = render(CamposDeContrato, {
      props: { campos: DECISION, valores: {} },
    });

    expect(getByText('Decisión')).toBeTruthy();
    expect(queryByText('Decision')).toBeNull();
  });
});
