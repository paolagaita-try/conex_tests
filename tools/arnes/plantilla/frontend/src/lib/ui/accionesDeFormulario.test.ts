/**
 * La gravedad puede no tener botón propio.
 *
 * `confirmacionPendiente` existe para que la confirmación colgara del RESULTADO que se
 * va a persistir y no del control por el que se pide. Pero el derivado `grave` seguía saliendo
 * **solo** de la acción secundaria, así que el mecanismo únicamente funcionaba en pantallas que
 * además tuvieran una secundaria grave: con `confirmacionPendiente: true` y sin secundaria, el
 * panel no se pintaba y la consecuencia irreversible se cursaba sin diálogo.
 *
 * Lo destapó una bandeja de revisión: su dictamen grave —`vetar`— se elige en el desplegable del
 * contrato y no tiene botón propio. La primera pantalla subió a la galería la mitad del mecanismo
 * que ella necesitaba.
 *
 * Verificado por mutación: revertir el derivado a `if (secundaria === undefined) return undefined`
 * pone en rojo el primer test (el panel deja de pintarse) y deja verde el segundo, que es el que
 * fija que las bandejas de decisión no cambian de comportamiento.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import AccionesDeFormulario from './AccionesDeFormulario.svelte';

const VETAR = { etiqueta: 'Vetar', consecuencia: 'Cierra el expediente sin posibilidad de retomarlo.' };

describe('AccionesDeFormulario · gravedad declarada por la pantalla', () => {
  it('pinta la confirmación sin acción secundaria, con la consecuencia que declara la pantalla', () => {
    const { getByRole } = render(AccionesDeFormulario, {
      props: { principal: 'Registrar dictamen', confirmacionPendiente: true, graveExterno: VETAR },
    });

    const panel = getByRole('group', { name: /Confirmar: Vetar/ });
    expect(panel).toBeTruthy();
    expect(panel.textContent).toMatch(/Cierra el expediente sin posibilidad de retomarlo/);
  });

  /**
   * Cuando hay DOS gravedades, manda la que declara la pantalla.
   *
   * Este test afirmaba lo contrario —«la secundaria sigue mandando: el externo no la pisa»— y
   * esa precedencia hacía `graveExterno` **inalcanzable** en cualquier pantalla cuya secundaria
   * fuese grave, que son todas las de decisión con `devolver`. El componente soportaba una
   * gravedad por pantalla; las bandejas tienen dos, una por control (`devolver`) y otra por
   * resultado (`declinar`).
   *
   * Vivían con un apaño —`secundaria={graveEnCurso ?? DEVOLVER}`— y una sonda midió su coste
   * sobre el DOM renderizado: durante el diálogo de `declinar`, el botón secundario
   * deshabilitado **se rerotulaba** de «Devolver» a «Declinar». El rótulo mentía
   * porque el rótulo y la gravedad salían del mismo sitio.
   *
   * Se separan: `graveExterno` dice qué consecuencia enunciar; `secundaria`, qué botón pintar.
   */
  it('con dos gravedades manda la que declara la pantalla, y el botón conserva su rótulo', () => {
    const { getByRole } = render(AccionesDeFormulario, {
      props: {
        principal: 'Aprobar',
        secundaria: {
          etiqueta: 'Devolver a subsanación',
          grave: true,
          consecuencia: 'Devuelve el expediente al solicitante.',
        },
        confirmacionPendiente: true,
        graveExterno: VETAR,
      },
    });

    // La consecuencia que se enuncia es la del RESULTADO que se va a persistir…
    const panel = getByRole('group', { name: /Confirmar: Vetar/ });
    expect(panel.textContent).toMatch(/Cierra el expediente sin posibilidad de retomarlo/);
    expect(panel.textContent).not.toMatch(/Devuelve el expediente al solicitante/);

    // …y el botón secundario sigue diciendo lo que hace, no lo que se está confirmando.
    expect(getByRole('button', { name: /Devolver a subsanación/ })).toBeTruthy();
  });

  it('sin gravedad externa, la secundaria grave sigue sirviendo la suya', () => {
    // El caso de UNA sola gravedad, que es el de las pantallas sin resultado en desplegable.
    const { getByRole } = render(AccionesDeFormulario, {
      props: {
        principal: 'Aprobar',
        secundaria: {
          etiqueta: 'Declinar',
          grave: true,
          consecuencia: 'Rechaza la solicitud.',
        },
        confirmacionPendiente: true,
      },
    });

    const panel = getByRole('group', { name: /Confirmar: Declinar/ });
    expect(panel.textContent).toMatch(/Rechaza la solicitud/);
  });

  it('sin gravedad de ninguna clase no hay panel, aunque la pantalla pida confirmación', () => {
    const { queryByRole } = render(AccionesDeFormulario, {
      props: { principal: 'Guardar', confirmacionPendiente: true },
    });

    expect(queryByRole('group', { name: /Confirmar/ })).toBeNull();
  });
});

/**
 * Quien navega con teclado o lector de pantalla tiene que enterarse de que apareció el panel.
 *
 * Se prueban las DOS vías porque el foco vivía dentro de `abrirConfirmacion()`, o sea que solo
 * lo recibía quien llegaba por el botón secundario. La vía que existe precisamente para que la
 * gravedad cuelgue del RESULTADO —`confirmacionPendiente`— se quedaba sin la protección que sí
 * tenía la vieja: la puerta nueva, sin la cerradura de la antigua.
 *
 * Lo encontró una verificación adversarial, que prefirió declararlo abierto a que su test fingiera cubrirlo.
 */
describe('AccionesDeFormulario · el foco va al panel por cualquiera de las dos vías', () => {
  it('por el botón secundario grave', async () => {
    const { getByRole } = render(AccionesDeFormulario, {
      props: {
        principal: 'Aprobar',
        secundaria: { etiqueta: 'Declinar', grave: true, consecuencia: 'Rechaza la solicitud.' },
      },
    });

    await fireEvent.click(getByRole('button', { name: /Declinar/ }));
    await tick();

    expect(document.activeElement).toBe(getByRole('group', { name: /Confirmar: Declinar/ }));
  });

  it('y cuando la gravedad la declara la pantalla, sin botón propio', async () => {
    const { getByRole } = render(AccionesDeFormulario, {
      props: { principal: 'Registrar dictamen', confirmacionPendiente: true, graveExterno: VETAR },
    });
    await tick();

    expect(document.activeElement).toBe(getByRole('group', { name: /Confirmar: Vetar/ }));
  });
});

/**
 * Dos gravedades a la vez: una por el control y otra por el resultado.
 *
 * La confirmación del botón dependía de `onconfirmar === undefined`, o sea de que **existiera
 * otra prop**. En cuanto una pantalla declaraba las dos gravedades —`devolver` por el botón,
 * `declinar` por el resultado—, esa presencia apagaba el diálogo del botón y la acción
 * irreversible se ejecutaba **al primer clic, en silencio**. Lo midió una verificación
 * adversarial con una sonda sobre el DOM: la suite seguía en verde.
 *
 * Inferir permiso de la presencia de una prop es lo que no puede hacer una galería de la que
 * cuelga una acción irreversible. Ahora la delegación se **declara**
 * (`secundariaConfirmaLaPantalla`) y el valor por defecto es el seguro.
 */
describe('AccionesDeFormulario · dos gravedades a la vez', () => {
  const DECLINAR = {
    etiqueta: 'Declinar',
    grave: true as const,
    consecuencia: 'Cierra el expediente sin posibilidad de retomarlo.',
  };

  it('un solo clic en la secundaria grave NO ejecuta nada', async () => {
    let ejecutada = false;
    const { getByRole } = render(AccionesDeFormulario, {
      props: {
        principal: 'Registrar',
        secundaria: DECLINAR,
        onsecundaria: () => { ejecutada = true; },
        graveExterno: VETAR,
        onconfirmar: () => {},
      },
    });

    await fireEvent.click(getByRole('button', { name: /^Declinar$/ }));

    expect(ejecutada, 'se ejecutó una acción irreversible sin diálogo').toBe(false);
  });

  it('y el panel enuncia la consecuencia del BOTÓN, no la del resultado', async () => {
    const { getByRole } = render(AccionesDeFormulario, {
      props: {
        principal: 'Registrar',
        secundaria: DECLINAR,
        onsecundaria: () => {},
        graveExterno: VETAR,
        onconfirmar: () => {},
      },
    });

    await fireEvent.click(getByRole('button', { name: /^Declinar$/ }));

    const panel = getByRole('group', { name: /Confirmar: Declinar/ });
    expect(panel.textContent).toMatch(/sin posibilidad de retomarlo/);
  });

  it('salvo que la pantalla declare que ella confirma: entonces delega y no hay dos diálogos', async () => {
    let ejecutada = false;
    const { getByRole, queryByRole } = render(AccionesDeFormulario, {
      props: {
        principal: 'Registrar',
        secundaria: DECLINAR,
        onsecundaria: () => { ejecutada = true; },
        secundariaConfirmaLaPantalla: true,
      },
    });

    await fireEvent.click(getByRole('button', { name: /^Declinar$/ }));

    expect(ejecutada).toBe(true);
    expect(queryByRole('group', { name: /Confirmar/ })).toBeNull();
  });
});

/**
 * Fijar la barra al pie no puede abrir una segunda puerta a lo irreversible.
 *
 * La lección —la confirmación cuelga del RESULTADO que se va a persistir, no del
 * control por el que se pide— se re-mide aquí porque el área de trabajo única cambia **dónde**
 * está el botón: ahora está siempre a la vista, que es justo la condición en la que un atajo
 * pasa desapercibido. Lo que se comprueba es que la vía nueva no existe: con la gravedad
 * declarada por la pantalla, pulsar la acción principal desde la barra fija NO ejecuta nada
 * hasta confirmar, y la barra sigue siendo UNA.
 */
describe('AccionesDeFormulario · la barra fija no añade una vía a lo grave', () => {
  it('mientras se confirma, la acción principal de la barra está deshabilitada', async () => {
    // Medido al escribir este test: el componente NO bloquea la ejecución —eso lo hace la
    // pantalla, que es donde vive la intercepción—; lo que el componente garantiza es
    // que, con el panel abierto, en la pantalla hay UNA sola decisión pendiente y el botón
    // principal no se puede volver a pulsar. Afirmar aquí que «no ejecuta» habría sido afirmar
    // de este componente una garantía que es de otro.
    const { getByTestId, getByRole } = render(AccionesDeFormulario, {
      props: { principal: 'Registrar dictamen', confirmacionPendiente: true, graveExterno: VETAR },
    });
    await tick();

    expect(getByRole('group', { name: /Confirmar/ })).toBeTruthy();
    expect(getByTestId('accion-principal')).toBeDisabled();
  });

  it('la barra es una sola: fijarla no duplica la acción principal', () => {
    const { getAllByTestId } = render(AccionesDeFormulario, {
      props: { principal: 'Registrar entrega' },
    });

    expect(getAllByTestId('accion-principal')).toHaveLength(1);
  });
});

describe('AccionesDeFormulario · la pantalla puede deshabilitar la acción principal', () => {
  it('con `deshabilitado` el botón principal no se pulsa y no dice que está ocupado', () => {
    const { getByTestId } = render(AccionesDeFormulario, {
      props: { principal: 'Enviar', deshabilitado: true },
    });
    const boton = getByTestId('accion-principal') as HTMLButtonElement;
    expect(boton.disabled).toBe(true);
    expect(boton.getAttribute('aria-busy')).toBe('false');
  });

  it('sin `deshabilitado` el botón principal se pulsa', () => {
    const { getByTestId } = render(AccionesDeFormulario, { props: { principal: 'Enviar' } });
    expect((getByTestId('accion-principal') as HTMLButtonElement).disabled).toBe(false);
  });
});
