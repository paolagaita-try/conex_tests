<script lang="ts">
  /**
   * Selección de una opción. Para campos TEXT del contrato cuya constraint es un conjunto
   * cerrado (`∈ {aprobar, aprobar_condicionado, declinar, escalar}`, por ejemplo).
   *
   * Las opciones vienen del contrato o de un parámetro `[PARAM]` del proyecto: nunca se
   * escriben a mano en la pantalla, porque entonces habría dos verdades.
   */
  import Campo from './Campo.svelte';

  export interface Opcion {
    valor: string;
    etiqueta: string;
  }

  interface Props {
    id: string;
    etiqueta: string;
    valor: string | null | undefined;
    opciones: readonly Opcion[];
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    /** Texto de la opción vacía. Sin él, el primer valor quedaría elegido «por descuido». */
    vacio?: string;
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
    opciones,
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    vacio = 'Seleccione…',
    prueba,
  }: Props = $props();
</script>

<Campo {id} {etiqueta} {ayuda} {error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <select
      data-testid={prueba}
      {id}
      bind:value={valor}
      disabled={deshabilitado}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-required={obligatorio}
    >
      <option value={null}>{vacio}</option>
      {#each opciones as opcion (opcion.valor)}
        <option value={opcion.valor}>{opcion.etiqueta}</option>
      {/each}
    </select>
  {/snippet}
</Campo>

<style>
  select {
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font: inherit;
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
  }
  select:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  select[aria-invalid='true'] {
    border-color: var(--color-error, #b3261e);
  }
  select:disabled {
    background: var(--color-superficie, #faf9fc);
    cursor: not-allowed;
  }
</style>
