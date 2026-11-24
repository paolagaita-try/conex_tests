<script lang="ts">
  /**
   * El vacío con voz humana: «Nada pendiente por ahora. Cuando llegue un
   * expediente aparecerá aquí.» — nunca una lista en blanco ni un «No hay datos».
   *
   * Es `role="status"`: se anuncia sin interrumpir. Un **error** no va aquí: va en `<Aviso
   * tono="error">` con *Reintentar*, porque una lista vacía disfrazada de «nada pendiente» es
   * lo que la bandeja tiene prohibido decir cuando en realidad no pudo consultar.
   *
   * Los enunciados los pone la bandeja de cada familia desde su catálogo; aquí no hay ninguno.
   */
  import type { Snippet } from 'svelte';

  interface Props {
    titulo: string;
    detalle?: string;
    /** Una acción opcional (p. ej. «Nueva solicitud» cuando no hay expedientes). */
    children?: Snippet;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
  }

  const { titulo, detalle, children, prueba }: Props = $props();
</script>

<div class="vacio" role="status" data-testid={prueba}>
  <p class="titulo">{titulo}</p>
  {#if detalle}<p class="detalle">{detalle}</p>{/if}
  {#if children}
    <div class="accion">{@render children()}</div>
  {/if}
</div>

<style>
  .vacio {
    padding: var(--esp-7, 3rem) var(--esp-5, 1.5rem);
    text-align: center;
    border: 1px dashed var(--color-borde, #e4e1e8);
    border-radius: var(--radio-xl, 24px);
  }

  .titulo {
    margin: 0;
    font-size: var(--texto-lg, 1.125rem);
    font-weight: var(--peso-medio, 500);
    color: var(--color-texto, #1c1b1f);
  }

  .detalle {
    max-inline-size: var(--ancho-lectura, 34rem);
    margin: var(--esp-2, 0.5rem) auto 0;
    font-size: var(--texto-md, 1rem);
    line-height: var(--linea-normal, 1.5);
    color: var(--color-texto-suave, #5f5b66);
  }

  .accion {
    margin-block-start: var(--esp-5, 1.5rem);
  }
</style>
