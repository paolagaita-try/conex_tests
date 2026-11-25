<script lang="ts" module>
  /**
   * Acción secundaria de una pantalla.
   *
   * La unión es discriminada a propósito: el tipo **obliga** a que toda acción marcada como
   * grave escriba su consecuencia. Pintar un botón rojo sin decir qué pasa al pulsarlo
   * asusta sin informar.
   *
   * Vive en el cimiento —y no en el catálogo del prototipo, de donde salió— porque la
   * declaración tiene que ser la misma para la pantalla de la galería y para la pantalla
   * ejecutable. Si cada una tuviera la suya, la consecuencia que se le enuncia al usuario
   * podría divergir entre lo aprobado y lo construido, y ningún test lo vería.
   */
  export type AccionSecundaria =
    | { etiqueta: string; grave?: false }
    | { etiqueta: string; grave: true; consecuencia: string };
</script>

<script lang="ts">
  /**
   * La fila de acciones de una pantalla, con la confirmación de lo grave incluida.
   *
   * ## De dónde viene
   *
   * Una revisión de usabilidad encontró `Declinar` —que rechaza la
   * solicitud de una persona— pintado como acción **secundaria**, igual que
   * «Guardar», y ejecutándose al primer clic. El cimiento lo arregló en la galería de
   * prototipos; este componente saca ese arreglo de la galería para que lo herede cada
   * pantalla ejecutable, en vez de que cada una lo reimplemente y una se lo salte.
   *
   * ## Por qué no es `window.confirm`
   *
   * El diálogo nativo no se puede redactar («OK / Cancelar» no dice qué se acepta), no
   * hereda el sistema de identidad visual, deja fuera al lector de pantalla del documento y
   * **bloquea la ventana entera**, lo que rompe cualquier sesión de automatización —
   * incluida la verificación visual con la que este proyecto cierra el gate de fidelidad.
   *
   * ## Qué se confirma y qué no
   *
   * Lo grave pide confirmación; lo reversible se ejecuta y ya. Confirmar todo enseña a
   * confirmar sin leer, que es la forma habitual de perder la protección.
   */
  import { tick } from 'svelte';
  import Aviso from './Aviso.svelte';
  import Boton from './Boton.svelte';

  interface Props {
    /** Etiqueta de la acción principal (la que cumple el propósito de la pantalla). */
    principal: string;
    /**
     * `id` del formulario que envía la acción principal cuando la barra vive FUERA de él.
     *
     * La barra es el pie del área de trabajo, no de una columna: dentro de la rejilla se salía
     * del viewport en cuanto el panel de contexto era más largo que el formulario.
     */
    formulario?: string;
    /** La alternativa, si la hay. Si es grave, pasa por confirmación. */
    secundaria?: AccionSecundaria;
    /** Mientras está ocupado no se puede pulsar dos veces (evita el doble envío). */
    ocupado?: boolean;
    /**
     * La pantalla aún no puede cumplir su propósito (p. ej. no tiene los datos del caso): la acción
     * principal no se pulsa. A diferencia de `ocupado`, no anuncia trabajo en curso.
     */
    deshabilitado?: boolean;
    /** Sin `onprincipal`, el botón principal es `submit` y lo recoge el formulario. */
    onprincipal?: () => void;
    /** Se llama cuando la secundaria procede: al primer clic si es leve, tras confirmar si es grave. */
    onsecundaria?: () => void;
    /**
     * La pantalla pide la confirmación por su cuenta, porque la gravedad la decide **el
     * resultado elegido**, no el botón pulsado.
     */
    confirmacionPendiente?: boolean;
    /**
     * La consecuencia grave que declara **la pantalla**, para cuando la gravedad no cuelga de
     * una acción secundaria sino del RESULTADO elegido. Es el caso de una bandeja de
     * revisión: su dictamen grave —`vetar`— se elige en el desplegable del contrato
     * y no tiene botón propio, así que no hay `secundaria` de la que derivar nada.
     *
     * Se acompaña siempre de `confirmacionPendiente`: esta prop dice QUÉ se confirma, aquella
     * CUÁNDO.
     */
    graveExterno?: { etiqueta: string; consecuencia: string };
    /**
     * La pantalla ya intercepta la secundaria por su RESULTADO, así que el botón no abre su
     * propia confirmación: encadenaría dos diálogos para la misma decisión, y confirmar dos
     * veces enseña a confirmar sin leer.
     *
     * Se **declara**; no se infiere. Antes se deducía de `onconfirmar !== undefined`, y eso
     * apagaba la confirmación del botón en cuanto la pantalla tenía **dos** gravedades
     * distintas —una por control (`devolver`), otra por resultado (`declinar`)—, con lo que
     * `Declinar` se ejecutaba al primer clic, sin diálogo y en silencio. Lo midió una
     * verificación adversarial con una sonda sobre el DOM, con la suite en verde.
     *
     * El valor por defecto es el seguro: si no se dice nada, el botón grave confirma.
     */
    secundariaConfirmaLaPantalla?: boolean;
    /** Qué hacer al confirmar una petición externa. */
    onconfirmar?: () => void;
    /** Qué hacer al cancelarla. */
    oncancelar?: () => void;
  }

  const {
    principal,
    formulario,
    secundaria,
    ocupado = false,
    deshabilitado = false,
    onprincipal,
    onsecundaria,
    confirmacionPendiente = false,
    graveExterno,
    secundariaConfirmaLaPantalla = false,
    onconfirmar,
    oncancelar,
  }: Props = $props();


  /**
   * La acción secundaria, pero solo cuando su consecuencia es grave. Se resuelve aquí y no
   * en el marcado para que el tipo garantice que la advertencia existe.
   */
  const grave = $derived.by(() => {
    // La pantalla manda: es el único sitio que sabe QUÉ resultado va a persistir, y la
    // gravedad la decide el resultado, no el control por el que se pide.
    //
    // Antes ganaba la secundaria, y eso hacía `graveExterno` **inalcanzable** en cualquier
    // pantalla cuya secundaria fuese grave — es decir, en toda bandeja de decisión con `devolver`.
    // El modelo de una sola gravedad servía para una revisión (una acción grave, sin botón propio) y no
    // para las bandejas con DOS: una por control (`devolver`) y otra por resultado
    // (`declinar`). Vivían con un apaño —`secundaria={graveEnCurso ?? DEVOLVER}`— cuyo coste
    // midió una sonda sobre el DOM renderizado: durante el diálogo de `declinar`,
    // el botón secundario deshabilitado **se rerotulaba** de «Devolver» a
    // «Declinar». El rótulo mentía porque el rótulo y la gravedad salían del mismo sitio.
    //
    // Ahora se separan: `graveExterno` dice qué consecuencia enunciar, `secundaria` solo pone
    // el botón y su rótulo. Cuando no hay gravedad externa, la secundaria grave sigue
    // sirviéndola, que es el caso de una sola gravedad.
    // Si el panel lo abrió el botón, se enuncia la consecuencia del BOTÓN — si no, una pantalla
    // con dos gravedades confirmaría «devolver» enseñando el texto de «declinar».
    if (confirmandoLocal && secundaria?.grave === true) return secundaria;
    if (graveExterno) return graveExterno;
    if (secundaria?.grave === true) return secundaria;
    return undefined;
  });

  /**
   * Confirmación pedida **desde fuera**, por la consecuencia y no por el botón.
   *
   * La confirmación colgaba del botón secundario, y eso dejaba viva la puerta de al lado: en una
   * pantalla donde el resultado se elige en un desplegable, escoger el valor grave y pulsar el
   * botón principal llegaba a la misma consecuencia irreversible sin diálogo. Lo grave es el
   * **resultado**, no el control por el que se pide.
   */
  let confirmandoLocal = $state(false);
  const confirmando = $derived(confirmandoLocal || confirmacionPendiente);
  let panelConfirmacion = $state<HTMLElement | undefined>(undefined);
  let disparador = $state<HTMLElement | undefined>(undefined);

  function pulsarSecundaria() {
    if (secundaria === undefined) return;
    // Una acción secundaria grave SIEMPRE pasa por su confirmación.
    //
    // Antes esto dependía de `onconfirmar === undefined`, con el argumento de no encadenar dos
    // diálogos «para la misma decisión». Pero no son la misma decisión: la gravedad del control
    // (`devolver`) y la del resultado (`declinar`) son independientes, y una pantalla puede
    // tener las dos. En cuanto las tenía, la presencia de la prop apagaba la confirmación del
    // botón y `Declinar` se ejecutaba al PRIMER CLIC, sin diálogo y en silencio.
    //
    // Lo midió una verificación adversarial con una sonda sobre el DOM: añadió
    // `resultadoGrave` a una ficha que además tenía secundaria grave y la suite siguió en
    // verde. Inferir permiso de la presencia de una prop es exactamente lo que no puede hacer
    // un cimiento del que cuelga una acción irreversible.
    if (secundaria.grave === true && !secundariaConfirmaLaPantalla) {
      abrirConfirmacion();
      return;
    }
    onsecundaria?.();
  }

  function abrirConfirmacion() {
    confirmandoLocal = true;
  }

  /**
   * El foco se lleva al panel **por cualquiera de las dos vías**, no solo por el botón.
   *
   * Sin esto, quien navega con teclado o lector de pantalla actúa y no se entera de que apareció
   * una advertencia más abajo. Estaba resuelto dentro de `abrirConfirmacion()`, es decir, solo
   * cuando la confirmación la dispara el botón secundario — y la vía que existe precisamente
   * para que la gravedad cuelgue del **resultado** (`confirmacionPendiente`) se quedaba sin la
   * protección que sí tenía la vieja. Lo midió una verificación adversarial, que prefirió declararlo a que su test
   * fingiera cubrirlo.
   *
   * Vivir en un efecto sobre `confirmando` cierra la clase: da igual quién abra el panel.
   */
  $effect(() => {
    if (!confirmando) return;
    void tick().then(() => panelConfirmacion?.focus());
  });

  function confirmar() {
    if (grave === undefined) return;
    // Manda quién ABRIÓ el panel, no quién gana la precedencia: si la confirmación la disparó el
    // botón secundario, lo que se ejecuta es la secundaria, aunque la pantalla declare además
    // una gravedad por resultado.
    if (confirmandoLocal) {
      confirmandoLocal = false;
      onsecundaria?.();
      return;
    }
    if (confirmacionPendiente) onconfirmar?.();
  }

  async function cancelar() {
    confirmandoLocal = false;
    oncancelar?.();
    // El foco vuelve al botón del que salió: quien se arrepiente no aparece al principio de
    // la página buscando dónde estaba.
    await tick();
    disparador?.querySelector<HTMLButtonElement>('button')?.focus();
  }

  /** Cerrar la confirmación con la tecla de escape, como cualquier diálogo. */
  function alTeclear(evento: KeyboardEvent) {
    if (evento.key === 'Escape') void cancelar();
  }
</script>

<!-- Mientras se confirma, la fila se deshabilita para que en la pantalla haya UNA sola
     decisión pendiente. -->
<div class="acciones barra">
  <Boton
    prueba="accion-principal"
    tipo={onprincipal ? 'button' : 'submit'}
    {formulario}
    deshabilitado={confirmando || deshabilitado}
    {ocupado}
    onclick={onprincipal}
  >
    {principal}
  </Boton>
  {#if secundaria}
    <!-- El envoltorio existe solo para devolver el foco a este botón al cancelar;
         `display: contents` lo deja fuera de la maquetación de la fila. -->
    <span class="disparador" bind:this={disparador}>
      <Boton
        prueba="accion-secundaria"
        tipo="button"
        variante={grave ? 'peligro' : 'secundario'}
        deshabilitado={confirmando || ocupado}
        onclick={pulsarSecundaria}
      >
        {secundaria.etiqueta}
      </Boton>
    </span>
  {/if}
</div>

{#if grave && confirmando}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <!-- El panel recibe el foco a propósito (`tabindex="-1"`) para anunciar la advertencia a
       quien navega con teclado o lector de pantalla; el `onkeydown` solo cierra con Escape,
       que es lo que se espera de un diálogo. No es un control: los controles son los dos
       botones de dentro. -->
  <div
    class="confirmacion"
    data-testid="confirmacion"
    bind:this={panelConfirmacion}
    tabindex="-1"
    role="group"
    aria-label={`Confirmar: ${grave.etiqueta}`}
    aria-describedby="consecuencia-grave"
    onkeydown={alTeclear}
  >
    <Aviso tono="error" titulo={`¿Seguro que quieres ${grave.etiqueta.toLowerCase()}?`}>
      <p id="consecuencia-grave">{grave.consecuencia}</p>
    </Aviso>
    <div class="acciones">
      <!-- La confirmación nombra lo que hace, no dice «Aceptar»: quien la lee no tiene que
           recordar qué botón pulsó hace tres segundos. -->
      <Boton prueba="confirmacion-aceptar" variante="peligro" {ocupado} onclick={confirmar}>
        Sí, {grave.etiqueta.toLowerCase()}
      </Boton>
      <Boton
        prueba="confirmacion-cancelar"
        variante="secundario"
        deshabilitado={ocupado}
        onclick={cancelar}
      >
        No, volver atrás
      </Boton>
    </div>
  </div>
{/if}

<style>
  .acciones {
    display: flex;
    flex-wrap: wrap;
    gap: var(--esp-3, 0.75rem);
    align-items: center;
  }

  /* La barra que CIERRA el trabajo va siempre a la vista: pegada al fondo del scroller, con
     fondo propio y una línea que la separa de lo que pasa por debajo. Medido:
     `accion-principal` nacía en y=1885 sobre un viewport de 800 — quien rellenaba el
     formulario no tenía a la vista el botón con el que termina. El diálogo de
     confirmación NO es sticky: se lee donde se abre, junto a la consecuencia. */
  .barra {
    /* NO se empuja al fondo con `margin-block-start: auto`. Se probó, y arreglaba el caso largo a
       costa del corto: con el formulario corto dejaba 133 px de vacío entre el último campo y la
       barra — «flotando sobre vacío», que es justo lo que hay que evitar. El caso largo se
       resuelve donde estaba el problema: la barra vive FUERA de la rejilla, como pie del área de
       trabajo, y entonces `sticky` la sostiene hasta el final del scroll. */
    position: sticky;
    inset-block-end: 0;
    z-index: 1;
    margin-block-start: var(--esp-4, 1rem);
    padding-block: var(--esp-3, 0.75rem);
    background: var(--color-fondo, #fff);
    border-block-start: 1px solid var(--color-borde, #e4e1e8);
  }
  .disparador {
    display: contents;
  }
  /* La confirmación se abre en la propia pantalla, enmarcada en el color de error, para
     que la advertencia y la decisión se lean juntas. Al recibir el foco se marca con el
     mismo color: el borde de foco morado del sistema aquí diría «acción normal».
     Los tokens son los de la galería: se movieron con el componente,
     no se re-eligieron. */
  .confirmacion {
    margin-block-start: var(--esp-4, 1rem);
    padding: var(--esp-4, 1rem);
    border: 1px solid var(--color-error, #b3261e);
    border-radius: var(--radio-lg, 16px);
  }

  .confirmacion:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-error, #b3261e);
    outline-offset: var(--esp-1, 0.25rem);
  }
</style>
