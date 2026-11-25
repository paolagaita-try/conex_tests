<script lang="ts">
  /**
   * Casilla de verificación. Para los campos BOOLEAN del contrato.
   *
   * A menudo sostiene algo con consecuencias legales: un consentimiento (sin él el flujo no
   * sigue). Por eso la etiqueta es siempre visible y asociada, y el estado se anuncia:
   * un consentimiento que el usuario no pueda leer y confirmar no es un consentimiento.
   */
  interface Props {
    id: string;
    etiqueta: string;
    valor: boolean | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
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
    prueba,
  }: Props = $props();

  const idAyuda = $derived(ayuda ? `${id}-ayuda` : undefined);
  const idError = $derived(error ? `${id}-error` : undefined);
  const describedBy = $derived([idAyuda, idError].filter(Boolean).join(' ') || undefined);
</script>

<div class="casilla" class:con-error={!!error}>
  <div class="fila">
    <input
      data-testid={prueba}
      {id}
      type="checkbox"
      bind:checked={valor}
      disabled={deshabilitado}
      aria-describedby={describedBy}
      aria-invalid={!!error}
      aria-required={obligatorio}
    />
    <label for={id}>
      {etiqueta}
      {#if obligatorio}<span class="marca" aria-hidden="true">*</span>{/if}
    </label>
  </div>
  {#if ayuda}
    <p class="ayuda" id={idAyuda}>{ayuda}</p>
  {/if}
  {#if error}
    <p class="error" id={idError} role="alert">{error}</p>
  {/if}
</div>

<style>
  .casilla {
    margin-block-end: var(--esp-4, 1rem);
  }
  .fila {
    display: flex;
    align-items: flex-start;
    gap: var(--esp-2, 0.5rem);
    /* El objetivo táctil abarca la fila completa, no solo el cuadrito. */
    min-height: var(--objetivo-min, 44px);
    align-content: center;
  }
  input {
    inline-size: 1.25rem;
    block-size: 1.25rem;
    margin-block-start: 0.15rem;
    accent-color: var(--color-primario, #6b21a8);
    flex: none;
  }
  input:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }
  label {
    font-size: var(--texto-sm, 0.875rem);
    line-height: var(--linea-normal, 1.5);
    color: var(--color-texto, #1c1b1f);
    cursor: pointer;
  }
  .marca {
    color: var(--color-error, #b3261e);
  }
  .ayuda,
  .error {
    margin: var(--esp-1, 0.25rem) 0 0 1.75rem;
    font-size: var(--texto-xs, 0.75rem);
  }
  .ayuda {
    color: var(--color-texto-suave, #5f5b66);
  }
  .error {
    color: var(--color-error, #b3261e);
    font-weight: 500;
  }
</style>
