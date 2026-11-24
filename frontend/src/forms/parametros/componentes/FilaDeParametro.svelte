<script lang="ts" module>
  export interface ChipDeFila {
    tono: 'neutro' | 'marca' | 'exito' | 'atencion' | 'error';
    texto: string;
  }
</script>

<script lang="ts">
  /**
   * Una fila del inicio (`p01`): el nombre de la lista o del parámetro, una línea de meta y, a la
   * derecha, los chips que piden mirar (impacto alto, cambio por aprobar, versión propia) y el chevron.
   * Es un botón —se abre con teclado y un lector la anuncia como lo que es— y la de solo lectura lo dice
   * con «Ver» en lugar del chevron.
   */
  import Flecha from './Flecha.svelte';
  import Chip from './Chip.svelte';

  interface Props {
    titulo: string;
    meta: string;
    chips?: ChipDeFila[];
    soloLectura?: boolean;
    rotuloVer?: string;
    onabrir: () => void;
    prueba?: string;
  }

  const { titulo, meta, chips = [], soloLectura = false, rotuloVer = 'Ver', onabrir, prueba }: Props = $props();
</script>

<button type="button" class="fila" class:solo-lectura={soloLectura} data-testid={prueba} onclick={onabrir}>
  <span class="texto">
    <span class="titulo">{titulo}</span>
    <span class="meta">{meta}</span>
  </span>
  <span class="lado">
    {#each chips as c, i (i)}
      <Chip tono={c.tono}>{c.texto}</Chip>
    {/each}
    <span class="chevron" aria-hidden="true">{#if soloLectura}{rotuloVer}{:else}<Flecha direccion="derecha" />{/if}</span>
  </span>
</button>
