<script lang="ts" module>
  import type { Recuento } from '$lib/bonita/marcas';
  import { recuento } from './formato';

  /** Una pestaña: su identificador, su rótulo y, si procede, cuántas cosas esperan detrás. */
  export interface Pestana {
    id: string;
    rotulo: string;
    /**
     * Se pinta como contador junto al rótulo (los «3» de «Por hacer (3)»). Un `Recuento`: un número
     * cualquiera no entra, así que el contador no puede pintar una cifra que nadie contó.
     */
    contador?: Recuento | null;
  }
</script>

<script lang="ts">
  /**
   * Los momentos de una bandeja.
   *
   * Es un `tablist` de verdad: cada pestaña es un `tab` con `aria-selected`, las flechas mueven el
   * foco y solo la activa está en el orden de tabulación (patrón WAI-ARIA «Tabs»). El color de
   * marca aparece **solo** en el indicador de la activa y en el contador: el resto es tinta.
   *
   * Los rótulos los pone la bandeja de cada familia desde su catálogo cerrado; este componente no
   * conoce ninguno.
   */
  interface Props {
    pestanas: Pestana[];
    /** `id` de la pestaña activa. */
    activa: string;
    /** Nombre accesible de la lista (`aria-label`). */
    nombre?: string;
    onchange?: (id: string) => void;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  const { pestanas, activa, nombre = 'Secciones', onchange, prueba }: Props = $props();

  let botones: Record<string, HTMLButtonElement | undefined> = $state({});

  function elegir(id: string): void {
    if (id !== activa) onchange?.(id);
  }

  /** Flechas y Home/End: el foco se mueve entre pestañas y la elección sigue al foco. */
  function alTeclear(evento: KeyboardEvent, indice: number): void {
    const n = pestanas.length;
    let destino: number | null = null;
    if (evento.key === 'ArrowRight') destino = (indice + 1) % n;
    else if (evento.key === 'ArrowLeft') destino = (indice - 1 + n) % n;
    else if (evento.key === 'Home') destino = 0;
    else if (evento.key === 'End') destino = n - 1;
    if (destino === null) return;
    evento.preventDefault();
    const id = pestanas[destino].id;
    botones[id]?.focus();
    elegir(id);
  }
</script>

<div class="pestanas" role="tablist" aria-label={nombre} data-testid={prueba}>
  {#each pestanas as p, i (p.id)}
    <button
      type="button"
      role="tab"
      id="pestana-{p.id}"
      aria-selected={p.id === activa}
      tabindex={p.id === activa ? 0 : -1}
      class:activa={p.id === activa}
      bind:this={botones[p.id]}
      onclick={() => elegir(p.id)}
      onkeydown={(e) => alTeclear(e, i)}
    >
      <span class="rotulo">{p.rotulo}</span>
      {#if p.contador !== undefined && p.contador !== null && p.contador > 0}
        <span class="contador" aria-label="{recuento(p.contador)} pendientes">{recuento(p.contador)}</span>
      {/if}
    </button>
  {/each}
</div>

<style>
  .pestanas {
    display: flex;
    gap: var(--esp-2, 0.5rem);
    border-block-end: 1px solid var(--color-borde, #e4e1e8);
    margin-block-end: var(--esp-5, 1.5rem);
  }

  button {
    display: inline-flex;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    margin-block-end: -1px;
    font: inherit;
    font-size: var(--texto-md, 1rem);
    font-weight: var(--peso-medio, 500);
    color: var(--color-texto-suave, #5f5b66);
    background: transparent;
    border: 0;
    border-block-end: 3px solid transparent;
    cursor: pointer;
    transition: color var(--transicion, 150ms);
  }

  button:hover {
    color: var(--color-texto, #1c1b1f);
  }

  button:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
    border-radius: var(--radio-sm, 4px);
  }

  /* El único sitio con color de marca: el indicador de la activa. */
  .activa {
    color: var(--color-texto, #1c1b1f);
    border-block-end-color: var(--color-primario, #6b21a8);
  }

  .contador {
    min-inline-size: 1.5rem;
    padding: 0 var(--esp-2, 0.5rem);
    font-size: var(--texto-xs, 0.75rem);
    font-weight: var(--peso-fuerte, 600);
    line-height: 1.5rem;
    text-align: center;
    color: var(--color-texto-inverso, #fff);
    background: var(--color-primario, #6b21a8);
    border-radius: var(--radio-completo, 999px);
  }
</style>
