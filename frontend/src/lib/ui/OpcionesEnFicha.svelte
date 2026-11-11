<script lang="ts" module>
  /** Una opción en ficha: su valor, su rótulo y, si ayuda a decidir, una línea de detalle. */
  export interface OpcionEnFicha {
    valor: string;
    etiqueta: string;
    detalle?: string;
  }
</script>

<script lang="ts">
  /**
   * Opciones en ficha — patrón «Radio Group» de WAI-ARIA APG.
   *
   * Para las listas de 2 a 5 opciones: se ven todas sin abrir
   * nada y cada ficha es un objetivo táctil de 44 px. Es un `radiogroup` nombrado por la etiqueta
   * de `Campo` (que lo nombra como GRUPO) y cada ficha un `radio` con `aria-checked`.
   *
   * Por qué no `<input type="radio">` nativos: el criterio pide `aria-checked` literal
   * y jsdom no implementa las flechas de un grupo nativo, así que el teclado del AC solo se habría
   * podido medir en el navegador. Con el patrón APG se prueba en el ciclo corto y además en Chromium.
   *
   * Teclado: Tab entra en la elegida (o en la primera), las flechas mueven el foco Y eligen, con
   * vuelta; Espacio elige la que tiene el foco.
   */
  import { tick } from 'svelte';
  import Campo from './Campo.svelte';

  interface Props {
    id: string;
    etiqueta: string;
    valor: string | null | undefined;
    opciones: readonly OpcionEnFicha[];
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    /**
     * `fila` reparte las fichas en el ancho (opciones cortas, como «Producto» en el diseño
     * aprobado); `columna` las apila (opciones con detalle). El teclado es el mismo en las dos.
     */
    disposicion?: 'columna' | 'fila';
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  let {
    id,
    etiqueta,
    valor = $bindable(),
    opciones,
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    disposicion = 'columna',
    prueba,
  }: Props = $props();

  let fichas: (HTMLElement | undefined)[] = $state([]);

  /** La que entra en el orden de tabulación: la elegida o, sin elegida, la primera. */
  const indiceEnfocable = $derived(Math.max(0, opciones.findIndex((o) => o.valor === valor)));

  async function elegir(indice: number) {
    if (deshabilitado) return;
    valor = opciones[indice].valor;
    await tick();
    fichas[indice]?.focus();
  }

  function alTeclear(evento: KeyboardEvent, indice: number) {
    const n = opciones.length;
    let destino: number | null = null;
    if (evento.key === 'ArrowRight' || evento.key === 'ArrowDown') destino = (indice + 1) % n;
    else if (evento.key === 'ArrowLeft' || evento.key === 'ArrowUp') destino = (indice - 1 + n) % n;
    else if (evento.key === ' ') destino = indice;
    if (destino === null) return;
    evento.preventDefault();
    void elegir(destino);
  }
</script>

<Campo {id} {etiqueta} {ayuda} {error} {obligatorio} grupo>
  {#snippet children({ describedBy, invalid, etiquetadoPor })}
    <div
      class="fichas"
      class:en-fila={disposicion === 'fila'}
      data-disposicion={disposicion}
      role="radiogroup"
      {id}
      data-testid={prueba}
      aria-labelledby={etiquetadoPor}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-required={obligatorio}
      aria-disabled={deshabilitado || undefined}
    >
      {#each opciones as opcion, i (opcion.valor)}
        {@const elegida = opcion.valor === valor}
        <div
          class="ficha"
          class:elegida
          role="radio"
          aria-checked={elegida}
          aria-labelledby="{id}-{i}-rotulo"
          aria-describedby={opcion.detalle ? `${id}-${i}-detalle` : undefined}
          aria-disabled={deshabilitado || undefined}
          tabindex={!deshabilitado && i === indiceEnfocable ? 0 : -1}
          bind:this={fichas[i]}
          onclick={() => elegir(i)}
          onkeydown={(e) => alTeclear(e, i)}
        >
          <span class="marca" aria-hidden="true"></span>
          <span class="texto">
            <span class="rotulo" id="{id}-{i}-rotulo">{opcion.etiqueta}</span>
            {#if opcion.detalle}
              <span class="detalle" id="{id}-{i}-detalle">{opcion.detalle}</span>
            {/if}
          </span>
        </div>
      {/each}
    </div>
  {/snippet}
</Campo>

<style>
  .fichas {
    display: grid;
    gap: var(--esp-2, 0.5rem);
  }
  .fichas.en-fila {
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
  }
  .ficha {
    display: flex;
    align-items: center;
    gap: var(--esp-3, 0.75rem);
    min-block-size: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
    transition: border-color var(--transicion, 150ms);
  }
  .ficha:hover:not([aria-disabled='true']) {
    border-color: var(--color-texto-suave, #5f5b66);
  }
  .ficha:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  .ficha.elegida {
    border-color: var(--color-primario, #6b21a8);
    background: var(--color-primario-suave, #f3e8ff);
  }
  .ficha[aria-disabled='true'] {
    color: var(--color-texto-suave, #5f5b66);
    background: var(--color-superficie, #faf9fc);
    cursor: not-allowed;
  }
  [aria-invalid='true'] > .ficha {
    border-color: var(--color-error, #b3261e);
  }
  /* El punto de radio: la elección se ve también por FORMA, no solo por color. */
  .marca {
    flex: none;
    inline-size: 1.125rem;
    block-size: 1.125rem;
    border: 2px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-completo, 999px);
  }
  .elegida .marca {
    border-color: var(--color-primario, #6b21a8);
    box-shadow: inset 0 0 0 4px var(--color-fondo, #fff);
    background: var(--color-primario, #6b21a8);
  }
  .texto {
    display: flex;
    flex-direction: column;
  }
  .rotulo {
    font-size: var(--texto-md, 1rem);
  }
  .detalle {
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }
</style>
