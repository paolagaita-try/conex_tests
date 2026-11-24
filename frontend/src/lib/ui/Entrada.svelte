<script lang="ts">
  /**
   * Entrada de una línea. Cubre los tipos TEXT, DECIMAL, INTEGER y DATE del contrato.
   *
   * `tipo` no se elige a gusto: se deriva del tipo del campo en el contrato de la tarea,
   * que es la fuente única. Ver `generado/contrato.ts` de cada formulario.
   */
  import Campo from './Campo.svelte';
  import type { NumeroTecleado } from '$lib/ui/valores';

  interface Props {
    id: string;
    etiqueta: string;
    /**
     * Un número, solo TECLEADO: lo pone el propio `<input>` al enlazar su valor, que es lo que
     * escribió la persona. Una pantalla no puede pasar aquí un número calculado.
     */
    valor: string | NumeroTecleado | null | undefined;
    tipo?: 'text' | 'number' | 'date' | 'email' | 'tel';
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    soloLectura?: boolean;
    /** Paso para valores numéricos (por ejemplo, 0.01 en un importe). */
    paso?: string;
    marcador?: string;
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
    tipo = 'text',
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    soloLectura = false,
    paso,
    marcador,
    prueba,
  }: Props = $props();
</script>

<Campo {id} {etiqueta} {ayuda} {error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <input
      data-testid={prueba}
      {id}
      type={tipo}
      bind:value={valor}
      step={paso}
      placeholder={marcador}
      disabled={deshabilitado}
      readonly={soloLectura}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-required={obligatorio}
    />
  {/snippet}
</Campo>

<style>
  input {
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font: inherit;
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
    transition: border-color var(--transicion, 150ms);
  }
  input:hover:not(:disabled):not([readonly]) {
    border-color: var(--color-texto-suave, #5f5b66);
  }
  /* Foco visible siempre: es requisito de accesibilidad, no decoración. */
  input:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  input[aria-invalid='true'] {
    border-color: var(--color-error, #b3261e);
  }
  input:disabled {
    background: var(--color-superficie, #faf9fc);
    color: var(--color-texto-suave, #5f5b66);
    cursor: not-allowed;
  }
</style>
