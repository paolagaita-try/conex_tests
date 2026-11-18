<script lang="ts">
  /** Una lectura que falló se dice como fallo, con salida: un dato que falta no es un cero (B2). */
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import * as T from '../textos';

  interface Props {
    onreintentar?: () => void;
    prueba?: string;
    titulo?: string;
    cuerpo?: string;
  }
  const { onreintentar, prueba = 'error-de-lectura', titulo = T.ERROR_DE_LECTURA_TITULO, cuerpo = T.ERROR_DE_LECTURA_CUERPO }: Props = $props();
</script>

<div data-testid={prueba}>
  <Aviso tono="error" {titulo}>
    <p>{cuerpo}</p>
    {#if onreintentar}<p><Boton variante="secundario" onclick={onreintentar} prueba="reintentar">{T.REINTENTAR}</Boton></p>{/if}
  </Aviso>
</div>
