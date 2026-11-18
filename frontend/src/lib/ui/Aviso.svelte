<script lang="ts">
  /**
   * Aviso al usuario: resultado de un envío, error de la plataforma o dato de contexto.
   *
   * El tono elige el rol accesible, y eso importa: un error se anuncia de inmediato
   * (`role="alert"`, que interrumpe), mientras que una confirmación se anuncia sin
   * interrumpir (`role="status"`).
   *
   * CUIDADO: un aviso mostrado en un canal de cliente NUNCA debe revelar revisiones
   * internas ni el estado interno del caso. El estado neutro es una regla de visibilidad,
   * no una omisión.
   */
  import type { Snippet } from 'svelte';

  interface Props {
    tono?: 'informacion' | 'exito' | 'aviso' | 'error';
    titulo?: string;
    children: Snippet;
  }

  const { tono = 'informacion', titulo, children }: Props = $props();
  const rol = $derived(tono === 'error' ? 'alert' : 'status');
</script>

<div class="caja {tono}" role={rol}>
  {#if titulo}<p class="titulo">{titulo}</p>{/if}
  <div class="cuerpo">{@render children()}</div>
</div>

<style>
  .caja {
    padding: var(--esp-3, 0.75rem) var(--esp-4, 1rem);
    margin-block-end: var(--esp-4, 1rem);
    border-inline-start: 3px solid;
    border-radius: var(--radio-sm, 4px);
    font-size: var(--texto-sm, 0.875rem);
  }
  .titulo {
    margin: 0 0 var(--esp-1, 0.25rem);
    font-weight: var(--peso-fuerte, 600);
  }
  .cuerpo :global(p) {
    margin: 0;
  }
  .informacion {
    border-color: var(--color-primario, #6b21a8);
    background: var(--color-primario-suave, #f3e8ff);
    color: var(--color-texto, #1c1b1f);
  }
  .exito {
    border-color: var(--color-exito, #1b6b3a);
    background: var(--color-exito-suave, #e7f4ec);
    color: var(--color-exito, #1b6b3a);
  }
  .aviso {
    border-color: var(--color-aviso, #8a5a00);
    background: var(--color-aviso-suave, #fdf3e2);
    color: var(--color-aviso, #8a5a00);
  }
  .error {
    border-color: var(--color-error, #b3261e);
    background: var(--color-error-suave, #fdeceb);
    color: var(--color-error, #b3261e);
  }
</style>
