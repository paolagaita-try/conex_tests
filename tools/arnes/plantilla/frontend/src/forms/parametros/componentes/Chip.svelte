<script lang="ts">
  /**
   * Un chip de estado (pantalla aprobada `p01…p09`): «Impacto alto», «Activa», «Cambio por aprobar».
   * El tono lo da el significado, nunca el adorno: éxito = aplicado o activo, atención = pide mirar,
   * error = rechazado o desactivar, marca = propio de este ámbito. Los colores salen de los tokens; los
   * estilos viven en `estilos.css` bajo `.pa`.
   */
  import type { Snippet } from 'svelte';

  interface Props {
    tono?: 'neutro' | 'marca' | 'exito' | 'atencion' | 'error';
    children: Snippet;
    /** Nombre estable para la automatización (`data-testid`). */
    prueba?: string;
  }

  const { tono = 'neutro', children, prueba }: Props = $props();
</script>

<span class="chip {tono}" data-testid={prueba}>{@render children()}</span>
