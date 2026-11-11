<script lang="ts">
  /**
   * El nombre de un documento de soporte, como enlace de descarga cuando hay contenido.
   *
   * El binario que aportó la persona
   * vive como documento de proceso y el BDM guarda su `contentStorageId`. Este componente es la
   * única forma autorizada de pintar ese enlace en las pantallas internas, para que la
   * dirección salga de UN sitio (`urlDeDescargaDeDocumento`) y no de varios recorridos parecidos.
   *
   * Sin `contentStorageId` —un documento registrado sin contenido— se pinta solo el nombre, sin
   * enlace: no se inventa una descarga que devolvería un 404.
   *
   * El `data-testid` se deriva del tipo (`descarga-<tipo>`), como los controles por documento de
   * una captura: es plantilla, así que un inventario literal de testids no lo ve; lo ejercita la suite E2E y el test unitario de este componente.
   */
  import { urlDeDescargaDeDocumento } from '$lib/bonita/documentos';

  interface Props {
    documento: {
      tipo: string;
      nombreArchivo: string;
      contentStorageId?: string | null;
    };
  }

  const { documento }: Props = $props();
  const url = $derived(urlDeDescargaDeDocumento(documento));
  const nombre = $derived(documento.nombreArchivo?.trim() || documento.tipo);
</script>

{#if url}
  <a
    href={url}
    data-testid={`descarga-${documento.tipo}`}
    download={documento.nombreArchivo}
    target="_blank"
    rel="noopener noreferrer"
    class="enlace"
  >
    {nombre}
  </a>
{:else}
  <span class="sin-contenido">{nombre}</span>
{/if}

<style>
  .enlace {
    color: var(--color-primario, #6b21a8);
    text-decoration: underline;
    text-underline-offset: 0.15em;
    font-family: var(--fuente-mono, monospace);
    font-size: var(--texto-sm, 0.875rem);
    word-break: break-all;
  }

  .enlace:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }

  .sin-contenido {
    font-family: var(--fuente-mono, monospace);
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    word-break: break-all;
  }
</style>
