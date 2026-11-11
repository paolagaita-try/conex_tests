<script lang="ts">
  /**
   * Carga de archivos. Para los campos FILE del contrato.
   *
   * El journey del proceso manda los inputs FILE a `null`: la carga real de archivos es de
   * los formularios, y este componente es esa carga.
   *
   * Convierte el archivo al formato que espera un input FILE del contrato Bonita
   * (`{ nombre, contenido }` en base64) para que la pantalla no tenga que hacerlo.
   */
  import Campo from './Campo.svelte';
  import type { ArchivoContrato } from '$lib/bonita/tipos';

  interface Props {
    id: string;
    etiqueta: string;
    valor: ArchivoContrato | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    /** Tipos aceptados, en el formato del atributo `accept`. */
    acepta?: string;
    /** Tamaño máximo en megabytes. Es un límite [PARAM] del proyecto. */
    maximoMb?: number;
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
    acepta = '.pdf,.jpg,.jpeg,.png',
    maximoMb = 10,
    prueba,
  }: Props = $props();

  let errorLocal = $state<string | null>(null);
  const errorMostrado = $derived(error ?? errorLocal);

  function base64De(archivo: File): Promise<string> {
    return new Promise((resolver, rechazar) => {
      const lector = new FileReader();
      lector.onerror = () => rechazar(new Error('No se pudo leer el archivo'));
      lector.onload = () => {
        const resultado = String(lector.result);
        // `data:<tipo>;base64,<contenido>` → el contrato solo quiere el contenido.
        resolver(resultado.slice(resultado.indexOf(',') + 1));
      };
      lector.readAsDataURL(archivo);
    });
  }

  async function alElegir(evento: Event): Promise<void> {
    errorLocal = null;
    const entrada = evento.target as HTMLInputElement;
    const archivo = entrada.files?.[0];
    if (!archivo) {
      valor = null;
      return;
    }
    if (archivo.size > maximoMb * 1024 * 1024) {
      errorLocal = `El archivo supera el máximo de ${maximoMb} MB`;
      entrada.value = '';
      valor = null;
      return;
    }
    try {
      valor = { nombre: archivo.name, contenido: await base64De(archivo) };
    } catch {
      errorLocal = 'No se pudo leer el archivo';
      valor = null;
    }
  }

  function quitar(): void {
    valor = null;
    errorLocal = null;
  }
</script>

<Campo {id} {etiqueta} {ayuda} error={errorMostrado} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <input
      data-testid={prueba}
      {id}
      type="file"
      accept={acepta}
      disabled={deshabilitado}
      onchange={alElegir}
      aria-describedby={describedBy}
      aria-invalid={invalid}
      aria-required={obligatorio}
    />
    {#if valor}
      <!-- `aria-live` porque la confirmación aparece sin que el usuario navegue. -->
      <p class="elegido" aria-live="polite">
        <span>{valor.nombre}</span>
        <button type="button" onclick={quitar} disabled={deshabilitado}>
          Quitar<span class="oculto"> el archivo {valor.nombre}</span>
        </button>
      </p>
    {/if}
  {/snippet}
</Campo>

<style>
  input[type='file'] {
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem);
    font: inherit;
    font-size: var(--texto-sm, 0.875rem);
    border: 1px dashed var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
    background: var(--color-superficie, #faf9fc);
  }
  input[type='file']:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  input[aria-invalid='true'] {
    border-color: var(--color-error, #b3261e);
  }
  .elegido {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--esp-2, 0.5rem);
    margin: var(--esp-1, 0.25rem) 0 0;
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font-size: var(--texto-sm, 0.875rem);
    background: var(--color-primario-suave, #f3e8ff);
    border-radius: var(--radio-sm, 4px);
  }
  .elegido button {
    min-height: var(--objetivo-min, 44px);
    padding-inline: var(--esp-2, 0.5rem);
    font: inherit;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-primario-fuerte, #581c87);
    background: none;
    border: none;
    text-decoration: underline;
    cursor: pointer;
  }
  .elegido button:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }
  /* Texto solo para lectores de pantalla: el botón dice «Quitar», pero quien no ve la
     fila necesita saber QUÉ se quita. */
  .oculto {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
