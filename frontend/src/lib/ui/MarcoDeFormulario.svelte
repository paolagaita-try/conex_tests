<script lang="ts">
  /**
   * El marco donde la bandeja abre una pantalla: un `<iframe>` con `title`, que
   * escucha el protocolo del marco mientras está montado y deja de escuchar al desmontarse.
   *
   * La dirección la resuelve el **motor** (`/bonita/portal/form/taskInstance/{id}`): este
   * componente no construye rutas de recurso. Y no interpreta el mensaje: se lo entrega a la
   * bandeja ya validado (origen y forma, en `escucharAlMarco`), y es la bandeja quien decide
   * re-consultar. Es el mismo mecanismo que la Task List nativa de 2025.2 (*medido*).
   *
   * Alto: el defecto sigue siendo fijo (`70vh`) para quien lo use suelto —la galería—, pero la
   * bandeja le pasa `alto="100%"` y entonces el marco **llena** el hueco que le deja su
   * contenedor y es el ÚNICO scroller del área de trabajo. Es la elección que resolvió la
   * medición: con el alto fijo, el
   * formulario nacía en y=915 sobre un viewport de 800 —por debajo del pliegue— y la rueda hacía
   * tres cosas distintas según dónde estuviera el puntero.
   */
  import { onMount } from 'svelte';
  import { escucharAlMarco, type MensajeDelMarco } from '$lib/bonita/marco';

  interface Props {
    /** Dirección corta que resuelve el motor (ver `urlDelFormularioDeTarea`). */
    src: string;
    /** Título accesible del marco: qué pantalla es la que hay dentro. */
    titulo: string;
    /** Alto del marco (CSS). */
    alto?: string;
    /** Llega cuando la pantalla de dentro avisa (forma y origen ya validados). */
    onmensaje?: (mensaje: MensajeDelMarco) => void;
    /** El documento del marco terminó de cargar. */
    oncargado?: () => void;
    /**
     * La pantalla NO cargó (el servidor devolvió un error, o lo que llegó no es una pantalla
     * nuestra).
     *
     * Hace falta porque un `<iframe>` con respuesta 500 dispara `load` igual que con 200: sin
     * mirar dentro, el marco enseñaba la página de error del servidor como si fuera la tarea.
     * Lo destapó una verificación adversarial: «el aviso ocupa el sitio del formulario» no
     * tenía implementación ninguna.
     */
    onerror?: () => void;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  const { src, titulo, alto = '70vh', onmensaje, oncargado, onerror, prueba }: Props = $props();

  onMount(() => escucharAlMarco((m) => onmensaje?.(m)));

  /**
   * Al cargar, el foco entra en el primer control de la pantalla.
   *
   * Quien abre una tarea va a escribir en ella: sin esto, el teclado se queda en la bandeja y
   * hay que tabular hasta cruzar el marco. Mismo origen (la pantalla vive en el mismo servidor),
   * así que se puede; si algún día no lo fuera, el `try` lo deja pasar sin romper nada.
   * No roba el foco al montar la bandeja: solo cuando el marco termina de cargar, que es
   * consecuencia de que alguien haya pulsado una fila.
   */
  /**
   * ¿Lo que cargó es una pantalla nuestra?
   *
   * Todas montan en `#app` (su `index.html` lo declara), así que su ausencia distingue la página
   * de error del servidor de una pantalla de verdad. Mismo origen, igual que `enfocarLoPrimero`;
   * si algún día no lo fuera, no se puede mirar dentro y se da por buena —el marco no puede
   * inventarse un error que no ha visto—.
   */
  function cargoUnaPantalla(marco: HTMLIFrameElement): boolean {
    try {
      const doc = marco.contentDocument;
      if (!doc) return true;
      // `#app` viene en el HTML servido, así que su presencia solo distingue «documento nuestro»
      // de «página de error del servidor». Lo que dice si la pantalla MONTÓ es que tenga hijos:
      // con el JS caído (deploy desfasado, CSP, una excepción al montar) el marco enseñaba una
      // caja en blanco de 482 px y nadie avisaba. Lo midió la 2.ª verificación adversarial.
      const app = doc.querySelector('#app');
      return app !== null && app.childElementCount > 0;
    } catch {
      return true;
    }
  }

  function enfocarLoPrimero(marco: HTMLIFrameElement): void {
    try {
      const doc = marco.contentDocument;
      const primero = doc?.querySelector<HTMLElement>(
        'input:not([type="hidden"]), select, textarea, [contenteditable="true"]',
      );
      primero?.focus({ preventScroll: true });
    } catch {
      // Origen cruzado: no se puede mirar dentro. Se queda como estaba.
    }
  }
</script>

<!-- El `id` empieza por `bonitaframe` A PROPÓSITO: es lo que `estaEnMarcoDeBonita()` (config.ts) mira
     en `window.frameElement.id` para decidir si la pantalla está embebida, y de eso cuelga la emisión
     del protocolo. Medido en 2025.2-u0 (2026-09-22): sin id, la pantalla ejecutaba la tarea y la
     bandeja no se enteraba — la tarea salía `completed` y la fila seguía ahí. -->
<iframe
  id="bonitaframe-marco"
  class="marco"
  {src}
  title={titulo}
  style:block-size={alto}
  data-testid={prueba}
  onload={(e) => {
    const marco = e.currentTarget as HTMLIFrameElement;
    if (!cargoUnaPantalla(marco)) {
      onerror?.();
      return;
    }
    enfocarLoPrimero(marco);
    oncargado?.();
  }}
></iframe>

<style>
  .marco {
    display: block;
    inline-size: 100%;
    /* Con `alto="100%"` el marco es un hijo flexible: cede su alto al contenedor acotado en vez
       de imponer el suyo. `min-block-size: 0` es lo que permite ENCOGER dentro de un flex. */
    flex: 1 1 auto;
    min-block-size: 0;
    /* Sin caja: embebido a pantalla completa, un borde redondeado lo convertía en «una ventana
       dentro de la ventana» y el scroll parecía de otro documento. Solo queda la línea de
       arriba, que separa la cabecera fija del contenido que corre por debajo. */
    border: 0;
    background: var(--color-fondo, #fff);
  }
</style>
