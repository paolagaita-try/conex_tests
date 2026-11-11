<script lang="ts">
  /**
   * Área de texto de varias líneas. Para campos TEXT largos del contrato —típicamente
   * las justificaciones de dictamen, que el contrato limita a 2000 caracteres.
   */
  import Campo from './Campo.svelte';

  interface Props {
    id: string;
    etiqueta: string;
    valor: string | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    filas?: number;
    /** Límite del contrato. Se muestra cuánto se ha escrito para que no sorprenda al enviar. */
    maximo?: number;
    /**
     * Nombre estable para la automatización (`data-testid`), derivado del contrato por
     * `CamposDeContrato` No se inventa por pantalla: es una interfaz
     * declarada entre el producto y sus pruebas, del mismo tipo que un contrato.
     */
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
    filas = 4,
    maximo,
    prueba,
  }: Props = $props();

  const usado = $derived((valor ?? '').length);
</script>

<Campo {id} {etiqueta} {ayuda} {error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <textarea
      data-testid={prueba}
      {id}
      rows={filas}
      maxlength={maximo}
      bind:value={valor}
      disabled={deshabilitado}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-required={obligatorio}
    ></textarea>
    {#if maximo}
      <!-- `aria-live` para que quien use lector de pantalla note que se acerca al límite,
           sin interrumpirle en cada tecla. -->
      <p class="cuenta" aria-live="polite">{usado} / {maximo}</p>
    {/if}
  {/snippet}
</Campo>

<style>
  textarea {
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font: inherit;
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
    resize: vertical;
    min-height: calc(var(--objetivo-min, 44px) * 2);
  }
  textarea:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  textarea[aria-invalid='true'] {
    border-color: var(--color-error, #b3261e);
  }
  .cuenta {
    margin: 0;
    align-self: flex-end;
    font-size: var(--texto-xs, 0.75rem);
    color: var(--color-texto-suave, #5f5b66);
    font-variant-numeric: tabular-nums;
  }
</style>
