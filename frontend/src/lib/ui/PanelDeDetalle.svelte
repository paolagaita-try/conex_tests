<script lang="ts">
  /**
   * El detalle de lo que se abrió en la bandeja: a la derecha en escritorio, a
   * pantalla completa con «← Volver» en móvil. Lo que va dentro lo decide la bandeja de cada
   * familia (contexto del expediente, recorrido, documentos, el marco con la pantalla).
   *
   * «Una pantalla, una decisión»: este panel no añade acciones propias; la única acción principal
   * es la de la pantalla que se carga dentro.
   */
  import type { Snippet } from 'svelte';

  interface Props {
    titulo: string;
    subtitulo?: string;
    /** Rótulo del botón de volver (móvil): el nombre del momento del que se viene. */
    rotuloVolver?: string;
    /** Si se pasa, se pinta el botón de volver y se llama al pulsarlo. */
    onvolver?: () => void;
    children: Snippet;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  const { titulo, subtitulo, rotuloVolver = 'Volver', onvolver, children, prueba }: Props =
    $props();

  const idTitulo = `detalle-${Math.random().toString(36).slice(2, 8)}`;
</script>

<section class="panel" aria-labelledby={idTitulo} data-testid={prueba}>
  <header class="cabecera">
    <!-- «Volver» en la MISMA línea que el título: apilados se comían 44 px del área de trabajo
         (medido el 2026-09-23: 453 px de 898 se iban en cabeceras y al marco le quedaban 400). -->
    <div class="linea">
      {#if onvolver}
        <button type="button" class="volver" onclick={() => onvolver()}>
          <span aria-hidden="true">←</span>
          {rotuloVolver}
        </button>
      {/if}
      <h2 id={idTitulo}>{titulo}</h2>
      {#if subtitulo}<span class="subtitulo">{subtitulo}</span>{/if}
    </div>
  </header>
  <div class="cuerpo">
    {@render children()}
  </div>
</section>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    min-inline-size: 0;
    /* Cuando la bandeja acota su alto (área de trabajo única), el panel cede: encoge hasta el
       hueco disponible en vez de empujar el documento hacia abajo. Suelto no cambia nada. */
    min-block-size: 0;
    /* El tema del portal pone `section { margin-bottom: 20px }`: dejaba 20 px de hueco bajo el
       marco y el área no llegaba al borde inferior de la ventana. */
    margin: 0;
    border-inline-start: 1px solid var(--color-borde, #e4e1e8);
    padding-inline-start: var(--esp-5, 1.5rem);
  }

  .cabecera {
    margin-block-end: var(--esp-1, 0.25rem);
  }

  .linea {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0 var(--esp-3, 0.75rem);
  }

  h2 {
    margin: 0;
    font-size: var(--texto-lg, 1.125rem);
    font-weight: var(--peso-medio, 500);
    line-height: var(--linea-apretada, 1.25);
    color: var(--color-texto, #1c1b1f);
  }

  .subtitulo {
    margin: 0;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  .volver {
    display: inline-flex;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    min-height: var(--objetivo-min, 44px);
    padding: 0 var(--esp-2, 0.5rem);
    font: inherit;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    background: transparent;
    border: 0;
    border-radius: var(--radio-sm, 4px);
    cursor: pointer;
  }

  .volver:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }

  .cuerpo {
    display: flex;
    flex-direction: column;
    gap: var(--esp-2, 0.5rem);
    min-inline-size: 0;
    /* El cuerpo se queda con el alto que sobre bajo la cabecera y se lo pasa a su hijo
       flexible (el marco). `min-block-size: 0` evita el suelo implícito del contenido. */
    flex: 1 1 auto;
    min-block-size: 0;
  }

  /* Bajo el corte, el panel ocupa la pantalla: la bandeja decide cuál de los dos se ve. */
  @media (max-width: 60rem) {
    .panel {
      border-inline-start: 0;
      padding-inline-start: 0;
    }
  }
</style>
