<script lang="ts">
  /**
   * Interruptor — patrón «Switch» de WAI-ARIA APG.
   *
   * Para un sí/no que describe un ESTADO («Persona ya registrada»), según la regla de widget
   * por defecto. Un consentimiento NO va aquí: va en `Casilla`, porque aceptar tiene que
   * ser un acto explícito y un interruptor encendido por defecto no lo es.
   *
   * Es un `<button role="switch" aria-checked>`: su nombre es la etiqueta de `Campo` —lo que
   * activa—, nunca «sí» o «no»; el «Sí/No» visible está oculto al lector porque el estado ya lo
   * anuncia `aria-checked`. Espacio y Enter son la activación NATIVA del botón: no se añade un
   * `keydown` propio, que en el navegador se sumaría a la nativa y conmutaría dos veces.
   */
  import Campo from './Campo.svelte';

  interface Props {
    id: string;
    etiqueta: string;
    valor: boolean | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    /** Lo que se ve junto a la pista en cada estado. */
    textoEncendido?: string;
    textoApagado?: string;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  let {
    id,
    etiqueta,
    valor = $bindable(),
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    textoEncendido = 'Sí',
    textoApagado = 'No',
    prueba,
  }: Props = $props();

  const encendido = $derived(valor === true);

  function conmutar() {
    if (deshabilitado) return;
    valor = !encendido;
  }
</script>

<Campo {id} {etiqueta} {ayuda} {error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <button
      data-testid={prueba}
      {id}
      type="button"
      role="switch"
      class="interruptor"
      class:encendido
      aria-checked={encendido}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-required={obligatorio}
      disabled={deshabilitado}
      onclick={conmutar}
    >
      <span class="pista" aria-hidden="true"><span class="perilla"></span></span>
      <span class="estado" aria-hidden="true">{encendido ? textoEncendido : textoApagado}</span>
    </button>
  {/snippet}
</Campo>

<style>
  .interruptor {
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    gap: var(--esp-3, 0.75rem);
    min-block-size: var(--objetivo-min, 44px);
    min-inline-size: var(--objetivo-min, 44px);
    padding: 0 var(--esp-2, 0.5rem) 0 0;
    font: inherit;
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto, #1c1b1f);
    background: transparent;
    border: 0;
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
  }
  .interruptor:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }
  .interruptor:disabled {
    color: var(--color-texto-suave, #5f5b66);
    cursor: not-allowed;
  }
  /* El límite de la pista es el de un control (WCAG 1.4.11, 3:1): `--color-borde-control`. */
  .pista {
    position: relative;
    flex: none;
    inline-size: 2.75rem;
    block-size: 1.5rem;
    background: var(--color-superficie, #faf9fc);
    border: 2px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-completo, 999px);
    transition: background var(--transicion, 150ms);
  }
  .perilla {
    position: absolute;
    inset-block-start: 2px;
    inset-inline-start: 2px;
    inline-size: 1rem;
    block-size: 1rem;
    background: var(--color-borde-control, #79747e);
    border-radius: var(--radio-completo, 999px);
    transition: transform var(--transicion, 150ms);
  }
  .encendido .pista {
    background: var(--color-primario, #6b21a8);
    border-color: var(--color-primario, #6b21a8);
  }
  .encendido .perilla {
    background: var(--color-fondo, #fff);
    transform: translateX(1.25rem);
  }
  [aria-invalid='true'] .pista {
    border-color: var(--color-error, #b3261e);
  }
  .interruptor:disabled .pista {
    opacity: 0.6;
  }
</style>
