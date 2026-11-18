import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import axe from 'axe-core';
import Campo from './Campo.svelte';
import Entrada from './Entrada.svelte';
import AreaTexto from './AreaTexto.svelte';
import Seleccion from './Seleccion.svelte';
import Casilla from './Casilla.svelte';
import CargaArchivo from './CargaArchivo.svelte';
import Boton from './Boton.svelte';
import MarcaCabecera from './MarcaCabecera.svelte';
import Seguimiento from './Seguimiento.svelte';
import VisorDocumentos from './VisorDocumentos.svelte';
import { tecleado } from '$pruebas/tecleado';
import {
  Autocompletar,
  Calendario,
  CampoConAfijo,
  Interruptor,
  OpcionesEnFicha,
  widgetPorDefecto,
} from './index';

/**
 * Accesibilidad de los componentes base.
 *
 * El driver estaba cerrado como «default de la plataforma» porque lo traían los widgets de
 * UI Designer. Al sustituirlos por componentes propios, ese default desapareció
 * y la responsabilidad es nuestra: se exige aquí, en la galería, con test, para que todos
 * los formularios lo hereden en lugar de descubrirlo con todas las pantallas hechas.
 *
 * Lo que se verifica de cada control:
 *  1. su etiqueta está ASOCIADA (se puede obtener por su texto, que es como lo hace un
 *     lector de pantalla) — no basta con que el texto esté al lado;
 *  2. lo obligatorio y el estado de error están en el DOM (`aria-required`,
 *     `aria-invalid`), no solo en el color;
 *  3. el mensaje de error está vinculado al control (`aria-describedby`) y se anuncia;
 *  4. axe-core no encuentra ninguna infracción.
 */

async function infracciones(contenedor: HTMLElement): Promise<string[]> {
  const resultado = await axe.run(contenedor, {
    // Reglas que necesitan la página completa (contraste con fondo real, landmarks,
    // orden de encabezados) no aplican a un componente aislado: se miden sobre la
    // pantalla renderizada, en el gate de fidelidad.
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    rules: { 'color-contrast': { enabled: false }, region: { enabled: false } },
  });
  return resultado.violations.map((v) => `${v.id}: ${v.help}`);
}

describe('Entrada', () => {
  it('asocia su etiqueta al control', () => {
    const { getByLabelText } = render(Entrada, {
      props: { id: 'monto', etiqueta: 'Anticipo solicitado', valor: null, tipo: 'number' },
    });
    expect(getByLabelText(/Anticipo solicitado/)).toBeInstanceOf(HTMLInputElement);
  });

  it('marca la obligatoriedad en el DOM, no solo con un asterisco', () => {
    const { getByLabelText } = render(Entrada, {
      props: { id: 'monto', etiqueta: 'Monto', valor: null, obligatorio: true },
    });
    expect(getByLabelText(/Monto/)).toHaveAttribute('aria-required', 'true');
  });

  it('vincula el error al control y lo anuncia', () => {
    const { getByLabelText, getByRole } = render(Entrada, {
      props: { id: 'monto', etiqueta: 'Monto', valor: null, error: 'Debe ser mayor que 0' },
    });
    const control = getByLabelText(/Monto/);
    expect(control).toHaveAttribute('aria-invalid', 'true');
    const alerta = getByRole('alert');
    expect(alerta).toHaveTextContent('Debe ser mayor que 0');
    expect(control.getAttribute('aria-describedby')).toContain(alerta.id);
  });

  it('vincula también el texto de ayuda', () => {
    const { getByLabelText, getByText } = render(Entrada, {
      props: { id: 'monto', etiqueta: 'Monto', valor: null, ayuda: 'En dólares' },
    });
    const ayuda = getByText('En dólares');
    expect(getByLabelText(/Monto/).getAttribute('aria-describedby')).toContain(ayuda.id);
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(Entrada, {
      props: {
        id: 'monto',
        etiqueta: 'Monto',
        valor: null,
        obligatorio: true,
        ayuda: 'En pesos',
        error: 'Obligatorio',
      },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('Campo como grupo', () => {
  /**
   * Un grupo (opciones en ficha) no es etiquetable: un `<label for>` que apunta a un `div` no le
   * da nombre. Con `grupo`, `Campo` pinta la etiqueta con un id y le pasa al control con qué
   * nombrarse (`aria-labelledby`).
   */
  const grupoDeRadio = createRawSnippet((args: () => { etiquetadoPor?: string; describedBy?: string }) => ({
    render: () =>
      `<div role="radiogroup" aria-labelledby="${args().etiquetadoPor ?? ''}"` +
      ` aria-describedby="${args().describedBy ?? ''}"><div role="radio" aria-checked="false" tabindex="0">Cheque</div></div>`,
  }));

  it('da nombre accesible al grupo con la etiqueta del campo', () => {
    const { getByRole } = render(Campo, {
      props: { id: 'via', etiqueta: 'Modo de disfrute', grupo: true, children: grupoDeRadio },
    });
    expect(getByRole('radiogroup', { name: 'Modo de disfrute' })).toBeTruthy();
  });

  it('el error del grupo queda vinculado al grupo y se anuncia', () => {
    const { getByRole } = render(Campo, {
      props: {
        id: 'via',
        etiqueta: 'Modo de disfrute',
        grupo: true,
        error: 'Elige una vía para continuar.',
        children: grupoDeRadio,
      },
    });
    const alerta = getByRole('alert');
    expect(getByRole('radiogroup').getAttribute('aria-describedby')).toContain(alerta.id);
  });

  it('sin grupo, la etiqueta sigue siendo un <label for> como hasta ahora', () => {
    const control = createRawSnippet(() => ({ render: () => '<input id="monto" />' }));
    const { container } = render(Campo, {
      props: { id: 'monto', etiqueta: 'Monto', children: control },
    });
    expect(container.querySelector('label[for="monto"]')).not.toBeNull();
  });

  it('no tiene infracciones de accesibilidad como grupo', async () => {
    const { container } = render(Campo, {
      props: { id: 'via', etiqueta: 'Modo de disfrute', grupo: true, obligatorio: true, children: grupoDeRadio },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('AreaTexto', () => {
  it('asocia su etiqueta y respeta el límite del contrato', () => {
    const { getByLabelText } = render(AreaTexto, {
      props: { id: 'just', etiqueta: 'Justificación', valor: null, maximo: 2000 },
    });
    const control = getByLabelText(/Justificación/);
    expect(control).toBeInstanceOf(HTMLTextAreaElement);
    expect(control).toHaveAttribute('maxlength', '2000');
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(AreaTexto, {
      props: { id: 'just', etiqueta: 'Justificación', valor: 'texto', maximo: 2000 },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('Seleccion', () => {
  const opciones = [
    { valor: 'aprobar', etiqueta: 'Aprobar' },
    { valor: 'declinar', etiqueta: 'Declinar' },
  ];

  it('asocia su etiqueta y ofrece una opción vacía para no elegir por descuido', () => {
    const { getByLabelText } = render(Seleccion, {
      props: { id: 'res', etiqueta: 'Resultado', valor: null, opciones },
    });
    const control = getByLabelText(/Resultado/) as HTMLSelectElement;
    expect(control).toBeInstanceOf(HTMLSelectElement);
    expect(control.options.length).toBe(3);
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(Seleccion, {
      props: { id: 'res', etiqueta: 'Resultado', valor: null, opciones, obligatorio: true },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('Casilla', () => {
  it('asocia la etiqueta del consentimiento al control', () => {
    // Con consecuencias legales: un consentimiento que el usuario no pueda leer y
    // confirmar no es un consentimiento.
    const { getByLabelText } = render(Casilla, {
      props: {
        id: 'ley',
        etiqueta: 'Autorizo el tratamiento de mis datos (política de privacidad)',
        valor: false,
        obligatorio: true,
      },
    });
    const control = getByLabelText(/política de privacidad/);
    expect(control).toHaveAttribute('type', 'checkbox');
    expect(control).toHaveAttribute('aria-required', 'true');
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(Casilla, {
      props: {
        id: 'consulta',
        etiqueta: 'Autorizo la consulta de mi historial',
        valor: false,
        obligatorio: true,
        error: 'Debe autorizar para continuar',
      },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('CargaArchivo', () => {
  it('asocia su etiqueta al control de archivo', () => {
    const { getByLabelText } = render(CargaArchivo, {
      props: { id: 'ced', etiqueta: 'Justificante', valor: null },
    });
    expect(getByLabelText(/Justificante/)).toHaveAttribute('type', 'file');
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(CargaArchivo, {
      props: { id: 'ced', etiqueta: 'Justificante', valor: null, obligatorio: true, maximoMb: 5 },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('Boton', () => {
  /** Contenido del botón como snippet real de Svelte 5 (no una función cualquiera:
   *  axe detectó correctamente que así el botón quedaba sin texto accesible). */
  const contenido = createRawSnippet(() => ({ render: () => '<span>Enviar</span>' }));

  it('anuncia que está ocupado y no se puede pulsar dos veces', () => {
    const { getByRole } = render(Boton, {
      props: { ocupado: true, children: contenido },
    });
    const boton = getByRole('button');
    expect(boton).toHaveAttribute('aria-busy', 'true');
    expect(boton).toBeDisabled();
  });

  it('tiene texto accesible', () => {
    const { getByRole } = render(Boton, { props: { children: contenido } });
    expect(getByRole('button')).toHaveAccessibleName('Enviar');
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(Boton, { props: { children: contenido } });
    expect(await infracciones(container)).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Presentación del canal de cliente: marca y recorrido.
// Se añaden aquí porque los heredan todos los formularios, igual que los
// controles: si la accesibilidad se rompe en la galería, se rompe en cada pantalla.
// ─────────────────────────────────────────────────────────────────────────────

describe('MarcaCabecera', () => {
  it('expone la marca como texto accesible aunque el logotipo sea una imagen de fondo', () => {
    const { getByRole } = render(MarcaCabecera, { props: { nombre: 'Empresa Aurora' } });
    // El logotipo llega por CSS (`--marca-logo`), así que sin nombre accesible sería
    // invisible para un lector de pantalla.
    expect(getByRole('img', { name: 'Empresa Aurora' })).toBeTruthy();
  });

  it('no deja el logotipo sin nombre cuando el tema no define marca', async () => {
    const { container, getByRole } = render(MarcaCabecera, { props: {} });
    expect(getByRole('img', { name: 'Logotipo del proyecto' })).toBeTruthy();
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('Seguimiento', () => {
  const ETAPAS = [
    { id: 'a', titulo: 'Solicitud recibida', detalle: 'Recibimos su solicitud.' },
    { id: 'b', titulo: 'En análisis', detalle: 'Estamos evaluando su solicitud.' },
    { id: 'c', titulo: 'Decisión' },
  ];

  it('marca la etapa en curso de forma programática, no solo con color', () => {
    const { container } = render(Seguimiento, {
      props: { etapas: ETAPAS, activa: 'b', completadas: ['a'] },
    });
    const actual = container.querySelector('[aria-current="step"]');
    expect(actual?.textContent).toContain('En análisis');
  });

  it('el estado de cada hito viaja como texto, no solo como forma', () => {
    // Quien no percibe el círculo relleno tiene que poder saber qué está hecho.
    const { getByText } = render(Seguimiento, {
      props: { etapas: ETAPAS, activa: 'b', completadas: ['a'] },
    });
    expect(getByText('(Completada)')).toBeTruthy();
    expect(getByText('(En curso)')).toBeTruthy();
    expect(getByText('(Pendiente)')).toBeTruthy();
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(Seguimiento, {
      props: { etapas: ETAPAS, activa: 'b', completadas: ['a'] },
    });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('VisorDocumentos', () => {
  const DOCS = [
    { id: '1', tipo: 'Justificante médico', nombreArchivo: 'justificante.pdf', url: '/doc/1', estado: 'Conforme' },
    { id: '2', tipo: 'Carta de trabajo', nombreArchivo: 'carta.pdf', url: '/doc/2', estado: 'Conforme' },
    { id: '3', tipo: 'Calendario del equipo', nombreArchivo: 'calendario.pdf', url: '/doc/3', estado: 'Pendiente' },
  ];

  it('anuncia la posición como texto, no solo con la miniatura activa', () => {
    const { getByText } = render(VisorDocumentos, { props: { documentos: DOCS } });
    // Quien no ve cuál está resaltada tiene que poder saber en qué documento va.
    expect(getByText(/Documento 1 de 3/)).toBeTruthy();
  });

  it('nombra el documento mostrado para lectores de pantalla', () => {
    const { getByTitle } = render(VisorDocumentos, { props: { documentos: DOCS } });
    expect(getByTitle('Documento: Justificante médico')).toBeTruthy();
  });

  it('la navegación es alcanzable por teclado', () => {
    const { container, getByLabelText } = render(VisorDocumentos, { props: { documentos: DOCS } });
    expect(getByLabelText('Documento anterior')).toBeTruthy();
    expect(getByLabelText('Documento siguiente')).toBeTruthy();
    // Sin tabindex, las flechas del carrusel serían inalcanzables sin ratón.
    expect(container.querySelector('[role="tablist"]')?.getAttribute('tabindex')).toBe('0');
  });

  it('dice con claridad cuándo no hay documentos, en vez de mostrar un marco vacío', () => {
    const { getByText } = render(VisorDocumentos, { props: { documentos: [] } });
    expect(getByText(/todavía no tiene documentos/)).toBeTruthy();
  });

  it('no tiene infracciones de accesibilidad', async () => {
    const { container } = render(VisorDocumentos, { props: { documentos: DOCS } });
    expect(await infracciones(container)).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Widgets del sistema de diseño. Se importan del ÍNDICE del cimiento, que es por donde
// los consumirán las pantallas: un widget sin exportar no existe para ellas.
// ─────────────────────────────────────────────────────────────────────────────

describe('Calendario', () => {
  const base = {
    id: 'fecha',
    etiqueta: 'Fecha de inicio',
    hoy: '2026-09-29',
    minimo: '2026-09-29',
    maximo: '2026-10-29',
    noHabiles: { diasDeLaSemana: [0, 6] as const },
  };

  it('asocia su etiqueta al campo y marca lo obligatorio en el DOM', () => {
    const { getByLabelText } = render(Calendario, {
      props: { ...base, valor: null, obligatorio: true },
    });
    expect(getByLabelText(/Fecha de inicio/)).toHaveAttribute('aria-required', 'true');
  });

  it('no tiene infracciones de accesibilidad cerrado, con ayuda y error', async () => {
    const { container } = render(Calendario, {
      props: { ...base, valor: null, obligatorio: true, ayuda: 'Día hábil', error: 'Obligatorio' },
    });
    expect(await infracciones(container)).toEqual([]);
  });

  it('no tiene infracciones de accesibilidad abierto, con días deshabilitados', async () => {
    const { container, getByRole } = render(Calendario, { props: { ...base, valor: '2026-10-02' } });
    await fireEvent.click(getByRole('button', { name: 'Elegir fecha' }));
    expect(getByRole('grid')).toBeTruthy();
    expect(await infracciones(container)).toEqual([]);
  });

  it('no tiene infracciones de accesibilidad deshabilitado', async () => {
    const { container } = render(Calendario, { props: { ...base, valor: '2026-10-02', deshabilitado: true } });
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('OpcionesEnFicha', () => {
  const opciones = [
    { valor: 'anual', etiqueta: 'Vacaciones anuales' },
    { valor: 'horas', etiqueta: 'Permiso por horas', detalle: 'Con tope de horas' },
  ];

  it('no tiene infracciones de accesibilidad con valor', async () => {
    const { container } = render(OpcionesEnFicha, {
      props: { id: 'producto', etiqueta: 'Tipo de permiso', valor: 'anual', opciones, obligatorio: true },
    });
    expect(await infracciones(container)).toEqual([]);
  });

  it('no tiene infracciones de accesibilidad con error y deshabilitado', async () => {
    const conError = render(OpcionesEnFicha, {
      props: { id: 'p1', etiqueta: 'Tipo de permiso', valor: null, opciones, error: 'Elige un tipo para continuar.' },
    });
    expect(await infracciones(conError.container)).toEqual([]);
    const apagado = render(OpcionesEnFicha, {
      props: { id: 'p2', etiqueta: 'Tipo de permiso', valor: 'horas', opciones, deshabilitado: true },
    });
    expect(await infracciones(apagado.container)).toEqual([]);
  });
});

describe('Interruptor', () => {
  it('no tiene infracciones de accesibilidad encendido, con error y deshabilitado', async () => {
    for (const extra of [{ valor: true }, { valor: null, error: 'Indica si es cliente.' }, { valor: false, deshabilitado: true }]) {
      const { container, unmount } = render(Interruptor, {
        props: { id: 'existente', etiqueta: 'Persona ya registrada', ...extra },
      });
      expect(await infracciones(container)).toEqual([]);
      unmount();
    }
  });
});

describe('CampoConAfijo', () => {
  it('asocia su etiqueta al campo y marca lo obligatorio en el DOM', () => {
    const { getByLabelText } = render(CampoConAfijo, {
      props: { id: 'monto', etiqueta: 'Anticipo solicitado', valor: null, prefijo: '$', obligatorio: true },
    });
    expect(getByLabelText(/Anticipo solicitado/)).toHaveAttribute('aria-required', 'true');
  });

  it('no tiene infracciones de accesibilidad con prefijo, sufijo, error y deshabilitado', async () => {
    for (const extra of [
      { prefijo: '$', valor: tecleado(850000), ayuda: 'Máximo $2,000,000' },
      { sufijo: '%', valor: null, error: 'Supera el máximo de 30 %.' },
      { sufijo: 'meses', valor: tecleado(48), decimales: 0, deshabilitado: true },
    ]) {
      const { container, unmount } = render(CampoConAfijo, {
        props: { id: 'cifra', etiqueta: 'Cifra', ...extra },
      });
      expect(await infracciones(container)).toEqual([]);
      unmount();
    }
  });
});

describe('Autocompletar', () => {
  const opciones = Array.from({ length: 20 }, (_, i) => ({ valor: `a${i}`, etiqueta: `Área ${i}` }));
  const base = { id: 'area', etiqueta: 'Área de estudio', opciones };

  it('no tiene infracciones de accesibilidad cerrado, con valor, error y deshabilitado', async () => {
    for (const extra of [
      { valor: 'a3', obligatorio: true },
      { valor: null, error: 'Elige tu área de estudio.' },
      { valor: 'a3', deshabilitado: true },
    ]) {
      const { container, unmount } = render(Autocompletar, { props: { ...base, ...extra } });
      expect(await infracciones(container)).toEqual([]);
      unmount();
    }
  });

  it('no tiene infracciones de accesibilidad con la lista abierta y una opción activa', async () => {
    const { container, getByRole } = render(Autocompletar, { props: { ...base, valor: null } });
    const campo = getByRole('combobox');
    campo.focus();
    await fireEvent.input(campo, { target: { value: 'area 1' } });
    await fireEvent.keyDown(campo, { key: 'ArrowDown' });
    expect(getByRole('listbox')).toBeTruthy();
    expect(await infracciones(container)).toEqual([]);
  });

  it('no tiene infracciones de accesibilidad con el estado vacío anunciado', async () => {
    const { container, getByRole } = render(Autocompletar, { props: { ...base, valor: null } });
    const campo = getByRole('combobox');
    campo.focus();
    await fireEvent.input(campo, { target: { value: 'astronauta' } });
    expect(getByRole('status')).toHaveTextContent(/astronauta/);
    expect(await infracciones(container)).toEqual([]);
  });
});

describe('la regla de widget por defecto viaja en el índice del cimiento', () => {
  it('es la misma función que consumirán las pantallas', () => {
    expect(widgetPorDefecto({ clase: 'lista', opciones: 20 })).toBe('autocompletar');
  });
});
