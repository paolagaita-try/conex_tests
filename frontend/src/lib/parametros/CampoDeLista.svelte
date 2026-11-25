<script lang="ts">
  /**
   * Un campo de lista cuyas opciones vigentes salen del módulo de parámetros.
   *
   * ## Qué decide y qué no
   *
   * - **Las opciones** las pide a `GET parametros/valores` con el id de la **tarea**: el servidor deduce
   *   de ella el proceso, la actividad y la familia (§3.3). Aquí no se filtra nada por visibilidad.
   * - **El control** lo dicta `widgetPorDefecto` por el número de opciones vigentes (2 a 5 fichas,
   *   6 a 15 desplegable, más de 15 autocompletar) salvo que el contrato declare otro (`widget:`).
   * - **La cascada** (`depende:`): con padre, pide las opciones de ese padre; si el padre cambia, las
   *   vuelve a pedir y, si el valor elegido ya no está entre ellas, lo vacía. Una lista hija sin
   *   opciones para ese padre **desaparece** (un tipo sin plazos no pinta el campo de plazo), no se pinta vacía.
   *
   * ## Si la lectura falla, NO hay texto libre
   *
   * Un fallo (red, 403, forma inesperada) pinta un aviso y un botón para reintentar, y le dice a quien
   * monta la pantalla —con `alProblema`— que el envío está bloqueado. Jamás se degrada a una caja de
   * texto: es exactamente el defecto que el módulo de parámetros corrige. Tampoco se muestra el motivo técnico: el
   * canal de cliente no ve nombres de definición, de tarea ni de fase.
   */
  import { untrack } from 'svelte';
  // Directo a cada componente, no por el índice: `$lib/ui` exporta `CamposDeContrato`, que importa este
  // fichero, y un ciclo de módulos deja un componente `undefined` según quién se evalúe primero.
  import Aviso from '$lib/ui/Aviso.svelte';
  import Autocompletar from '$lib/ui/Autocompletar.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import OpcionesEnFicha, { type OpcionEnFicha } from '$lib/ui/OpcionesEnFicha.svelte';
  import Seleccion, { type Opcion } from '$lib/ui/Seleccion.svelte';
  import { widgetPorDefecto, type Widget } from '$lib/ui/widgetPorDefecto';
  import { LecturaFallida, leerValores, type LectorDeValores, type OpcionVigente } from './opciones';

  type Carga =
    | { estado: 'espera-padre' }
    | { estado: 'cargando' }
    | { estado: 'lista'; opciones: readonly OpcionVigente[] }
    | { estado: 'error' };

  interface Props {
    id: string;
    prueba?: string;
    etiqueta: string;
    /** Código de la definición (`tipo_de_permiso`). */
    catalogo: string;
    /** Identificador de la tarea abierta; sin él no hay con qué pedir (y se avisa, no se inventa). */
    tarea: string | null | undefined;
    /** Formulario de instanciación (sin tarea): el id de la definición del proceso con el que pedir. */
    instanciacion?: string | null;
    /** Código del padre elegido (`anual`); `undefined` si la lista no depende de otra. */
    depende?: boolean;
    padre?: string;
    /** Widget declarado por el contrato (`widget:`); gana sobre la regla por defecto. */
    widget?: Widget;
    valor: string | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    lector?: LectorDeValores;
    /** Avisa a quien monta la pantalla de lo que impide enviar (`null` = nada). */
    alProblema?: (problema: string | null) => void;
  }

  let {
    id,
    prueba,
    etiqueta,
    catalogo,
    tarea,
    instanciacion,
    depende = false,
    padre,
    widget,
    valor = $bindable(),
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    lector = leerValores,
    alProblema,
  }: Props = $props();

  let carga = $state<Carga>({ estado: 'cargando' });
  let intento = $state(0);

  $effect(() => {
    // Lo que dispara una lectura nueva: la tarea, la definición, el padre y el reintento. El valor
    // elegido NO (se lee sin suscribirse): elegir una opción no debe volver a pedir la lista.
    const idTarea = tarea;
    const idInstanciacion = instanciacion;
    const codigo = catalogo;
    const codigoPadre = padre;
    const conPadre = depende;
    void intento;
    if (!idTarea && !idInstanciacion) {
      carga = { estado: 'error' };
      return;
    }
    if (conPadre && !codigoPadre) {
      carga = { estado: 'espera-padre' };
      return;
    }
    carga = { estado: 'cargando' };
    let vigente = true;
    lector({
      definicion: codigo,
      tarea: idTarea || undefined,
      instanciacion: idTarea ? undefined : idInstanciacion || undefined,
      padre: conPadre ? codigoPadre : undefined,
    })
      .then((leido) => {
        if (!vigente) return;
        if (leido.clase !== 'LISTA') throw new LecturaFallida('formato', codigo, 'se esperaba una lista');
        carga = { estado: 'lista', opciones: leido.opciones };
        const actual = untrack(() => valor);
        if (actual && !leido.opciones.some((o) => o.codigo === actual)) valor = '';
      })
      .catch(() => {
        if (vigente) carga = { estado: 'error' };
      });
    return () => {
      vigente = false;
    };
  });

  const opciones = $derived(carga.estado === 'lista' ? carga.opciones : null);
  // Una lista hija sin opciones para su padre no se pinta.
  const oculto = $derived(depende && opciones !== null && opciones.length === 0);
  // Una lista madre sin opciones vigentes no se puede elegir: eso es un fallo, no una pantalla vacía.
  const sinOpciones = $derived(!depende && opciones !== null && opciones.length === 0);

  const problema = $derived.by((): string | null => {
    if (oculto) return null;
    if (carga.estado === 'error') {
      return `No se pudieron cargar las opciones de «${etiqueta}». No se puede enviar hasta que vuelvan a estar disponibles.`;
    }
    if (control.contratoRoto) {
      return `El campo «${etiqueta}» no se puede mostrar. No se puede enviar hasta que se corrija.`;
    }
    if (sinOpciones) {
      return `No hay opciones vigentes para «${etiqueta}». No se puede enviar hasta que haya al menos una.`;
    }
    if (carga.estado === 'cargando') {
      return `Las opciones de «${etiqueta}» se están cargando.`;
    }
    return null;
  });

  // Solo `problema` dispara el aviso: `alProblema` suele ser una función nueva en cada pintado de quien
  // monta la pantalla, y suscribirse a ella volvería a avisar sin que nada hubiera cambiado.
  $effect(() => {
    const p = problema;
    untrack(() => alProblema?.(p));
  });
  // Al desaparecer el campo, su problema desaparece con él.
  $effect(() => () => untrack(() => alProblema?.(null)));

  /** El control que corresponde al número de opciones, o lo que declaró el contrato. */
  const WIDGETS_DE_LISTA: readonly Widget[] = ['fichas', 'desplegable', 'autocompletar'];
  /**
   * El control, o por qué no hay ninguno. Un `widget:` que no sirve para una lista (un interruptor, un
   * calendario), o que ni existe, es un error del CONTRATO que el custodio caza antes de desplegar; si
   * aun así llega, no se pinta otra cosa a escondidas: el campo avisa y el envío queda bloqueado.
   */
  const control = $derived.by((): { widget: Widget | null; contratoRoto: boolean } => {
    if (opciones === null || opciones.length === 0) return { widget: null, contratoRoto: false };
    try {
      const elegido = widgetPorDefecto({ clase: 'lista', opciones: opciones.length }, widget);
      return WIDGETS_DE_LISTA.includes(elegido) ? { widget: elegido, contratoRoto: false } : { widget: null, contratoRoto: true };
    } catch {
      return { widget: null, contratoRoto: true };
    }
  });

  const comoOpciones = $derived<Opcion[]>((opciones ?? []).map((o) => ({ valor: o.codigo, etiqueta: o.etiqueta })));
  const comoFichas = $derived<OpcionEnFicha[]>(
    (opciones ?? []).map((o) => (o.ayuda ? { valor: o.codigo, etiqueta: o.etiqueta, detalle: o.ayuda } : { valor: o.codigo, etiqueta: o.etiqueta })),
  );
</script>

{#if oculto}
  <!-- La lista no aplica a este padre: el campo no se pinta (sin hueco ni etiqueta suelta). -->
{:else if carga.estado === 'error' || sinOpciones || control.contratoRoto}
  <!-- Sin control que etiquetar: un grupo con su rótulo y el aviso. Una <label for> hacia nada es un
       defecto de accesibilidad, y un campo de texto aquí sería el defecto que el módulo de parámetros corrige. -->
  <div class="grupo" role="group" aria-labelledby={`${id}-rotulo`} data-testid={prueba ? `${prueba}-aviso` : undefined}>
    <span class="rotulo" id={`${id}-rotulo`}>{etiqueta}{obligatorio ? ' *' : ''}</span>
    <Aviso tono="error" titulo="No se pueden mostrar las opciones">
      {problema}
      {#if carga.estado === 'error'}
        <Boton variante="secundario" prueba={prueba ? `${prueba}-reintentar` : undefined} onclick={() => (intento += 1)}>Reintentar</Boton>
      {/if}
    </Aviso>
  </div>
{:else if carga.estado === 'espera-padre'}
  <Seleccion {id} {prueba} {etiqueta} opciones={[]} bind:valor {ayuda} {error} {obligatorio} deshabilitado vacio="Elija primero la opción de la que depende" />
{:else if carga.estado === 'cargando'}
  <Seleccion {id} {prueba} {etiqueta} opciones={[]} bind:valor {ayuda} {error} {obligatorio} deshabilitado vacio="Cargando opciones…" />
{:else if control.widget === 'fichas'}
  <OpcionesEnFicha {id} {prueba} {etiqueta} opciones={comoFichas} bind:valor {ayuda} {error} {obligatorio} {deshabilitado} />
{:else if control.widget === 'autocompletar'}
  <Autocompletar {id} {prueba} {etiqueta} opciones={comoOpciones} bind:valor {ayuda} {error} {obligatorio} {deshabilitado} />
{:else}
  <!-- `desplegable`: 6 a 15 opciones, o 0 y 1 (no hay elección que enseñar en fichas). -->
  <Seleccion {id} {prueba} {etiqueta} opciones={comoOpciones} bind:valor {ayuda} {error} {obligatorio} {deshabilitado} vacio="Seleccione una opción" />
{/if}

<style>
  .grupo {
    display: grid;
    gap: var(--esp-1, 0.25rem);
  }
  .rotulo {
    font-size: var(--texto-sm, 0.875rem);
    font-weight: var(--peso-fuerte, 600);
  }
</style>
