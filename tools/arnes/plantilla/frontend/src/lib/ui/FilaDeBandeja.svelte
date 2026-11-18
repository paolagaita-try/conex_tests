<script lang="ts">
  /**
   * Una fila de bandeja: «ficha legible en un vistazo».
   *
   * Título del catálogo · una línea de meta («2026-000123 · Camila P. · hace 2 h») · chevron.
   * Alto ≥ 56 px, radio `--radio-xl`. Es un **botón**, no un `<div>` con `onclick`: se abre con
   * teclado y un lector de pantalla la anuncia como lo que es.
   *
   * No decide qué pintar: el título y la meta llegan ya traducidos por la bandeja de cada familia
   * (nunca el `name` del motor). Si la tarea la tomó otra persona, se dice y no se ofrece botón
   * de tomar (§3.5: la bandeja no asigna ni libera).
   */
  interface Props {
    titulo: string;
    /** Piezas de la línea secundaria; se unen con « · ». */
    meta?: string[];
    /** Quién la tiene tomada, si no es quien mira. */
    atendidaPor?: string | null;
    /** La fila abierta ahora mismo en el panel de detalle. */
    seleccionada?: boolean;
    onabrir?: () => void;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  const { titulo, meta = [], atendidaPor = null, seleccionada = false, onabrir, prueba }: Props =
    $props();
</script>

<button
  type="button"
  class="fila"
  class:seleccionada
  aria-current={seleccionada ? 'true' : undefined}
  data-testid={prueba}
  onclick={() => onabrir?.()}
>
  <span class="texto">
    <span class="titulo">{titulo}</span>
    {#if meta.length > 0}
      <span class="meta">{meta.join(' · ')}</span>
    {/if}
    {#if atendidaPor}
      <span class="tomada">Tomada por {atendidaPor}</span>
    {/if}
  </span>
  <span class="chevron" aria-hidden="true">›</span>
</button>

<style>
  .fila {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--esp-4, 1rem);
    inline-size: 100%;
    min-height: 56px;
    padding: var(--esp-3, 0.75rem) var(--esp-5, 1.5rem);
    font: inherit;
    text-align: start;
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-xl, 24px);
    cursor: pointer;
    transition:
      background-color var(--transicion, 150ms),
      border-color var(--transicion, 150ms);
  }

  .fila:hover {
    background: var(--color-superficie, #faf9fc);
  }

  .fila:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }

  /* La abierta se distingue por el borde, no por color de fondo de marca. */
  .seleccionada {
    border-color: var(--color-primario, #6b21a8);
    background: var(--color-superficie, #faf9fc);
  }

  .texto {
    display: flex;
    flex-direction: column;
    gap: var(--esp-1, 0.25rem);
    min-inline-size: 0;
  }

  .titulo {
    font-size: var(--texto-md, 1rem);
    font-weight: var(--peso-medio, 500);
    line-height: var(--linea-apretada, 1.25);
  }

  .meta,
  .tomada {
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  .chevron {
    flex: none;
    font-size: var(--texto-xl, 1.5rem);
    line-height: 1;
    color: var(--color-texto-suave, #5f5b66);
  }
</style>
