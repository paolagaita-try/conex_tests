<script lang="ts">
  /** Botón de acción. */
  import type { Snippet } from 'svelte';

  interface Props {
    tipo?: 'button' | 'submit' | 'reset';
    variante?: 'primario' | 'secundario' | 'peligro';
    deshabilitado?: boolean;
    /** Mientras está ocupado no se puede pulsar dos veces (evita el doble envío). */
    ocupado?: boolean;
    children: Snippet;
    onclick?: (evento: MouseEvent) => void;
    /**
     * Nombre estable para la automatización (`data-testid`), derivado del contrato por
     * `CamposDeContrato` No se inventa por pantalla: es una interfaz
     * declarada entre el producto y sus pruebas, del mismo tipo que un contrato.
     */
    prueba?: string;
    /**
     * `id` del formulario que envía, cuando el botón **no** es descendiente suyo.
     *
     * Hace falta porque la barra de acciones vive al pie del área de trabajo, fuera de la
     * rejilla de dos columnas, porque dentro de la columna del formulario se salía del viewport
     * en cuanto el panel de contexto era más largo (medido en el portal real: `accion-principal`
     * en top −131 al desplazar al final). El atributo `form` es lo que permite sacarla sin que
     * deje de enviar.
     */
    formulario?: string;
  }

  const {
    tipo = 'button',
    variante = 'primario',
    deshabilitado = false,
    ocupado = false,
    children,
    onclick,
    formulario,
    prueba,
  }: Props = $props();
</script>

<button
  data-testid={prueba}
  type={tipo}
  form={formulario}
  class={variante}
  disabled={deshabilitado || ocupado}
  aria-busy={ocupado}
  {onclick}
>
  {@render children()}
</button>

<style>
  button {
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-5, 1.5rem);
    font: inherit;
    font-size: var(--texto-md, 1rem);
    font-weight: var(--peso-medio, 500);
    border: 1px solid transparent;
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
    transition: background-color var(--transicion, 150ms);
  }
  button:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }
  button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
  .primario {
    color: var(--color-texto-inverso, #fff);
    background: var(--color-primario, #6b21a8);
  }
  .primario:hover:not(:disabled) {
    background: var(--color-primario-fuerte, #581c87);
  }
  .secundario {
    color: var(--color-primario-fuerte, #581c87);
    background: var(--color-fondo, #fff);
    border-color: var(--color-borde-control, #79747e);
  }
  .secundario:hover:not(:disabled) {
    background: var(--color-primario-suave, #f3e8ff);
  }
  .peligro {
    color: var(--color-texto-inverso, #fff);
    background: var(--color-error, #b3261e);
  }
</style>
