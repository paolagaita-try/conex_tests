<script lang="ts">
  /**
   * El campo de un valor de parámetro (`p05`): el control que corresponde a su tipo, con la unidad a la
   * vista. Números, montos y porcentajes van con prefijo o sufijo («US$», «%», «meses»); un sí/no, con el
   * interruptor del cimiento; una fecha, con el campo de fecha; un texto, con el campo de texto.
   *
   * El valor viaja como TEXTO: este campo no convierte lo tecleado en número, así que no usa
   * `CampoConAfijo`, cuya API es numérica. Conserva lo que ese widget garantiza: etiqueta asociada, ayuda y
   * error por `aria-describedby`, `aria-invalid`, la unidad anunciada UNA vez y objetivos de 44 px.
   */
  import Campo from '$lib/ui/Campo.svelte';
  import Entrada from '$lib/ui/Entrada.svelte';
  import Interruptor from '$lib/ui/Interruptor.svelte';
  import { MAXIMO_LOGO } from '$lib/parametros/marca';

  interface Props {
    id: string;
    etiqueta: string;
    /** El valor como se teclea («30», «1500000», «true», «2026-10-31»). */
    valor: string;
    tipoDato: string;
    prefijo?: string;
    sufijo?: string;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    prueba?: string;
    /**
     * El valor es una imagen (el logo de la marca): en vez de teclear un `data:` de decenas de miles de caracteres,
     * se elige el archivo y el campo lo convierte. El servidor vuelve a validar tipo, tamaño y contenido; esto solo
     * evita que la persona tenga que fabricar la cadena a mano.
     */
    imagen?: boolean;
  }

  let { id, etiqueta, valor = $bindable(), tipoDato, prefijo = '', sufijo = '', ayuda, error = null, obligatorio = false, deshabilitado = false, prueba, imagen = false }: Props = $props();

  let errorDeImagen = $state<string | null>(null);
  const hayImagen = $derived(valor.startsWith('data:image/'));

  function elegirImagen(e: Event & { currentTarget: HTMLInputElement }): void {
    errorDeImagen = null;
    const archivo = e.currentTarget.files?.[0];
    if (!archivo) return;
    if (archivo.type !== 'image/png' && archivo.type !== 'image/svg+xml') {
      errorDeImagen = 'El logo debe ser un archivo PNG o SVG.';
      e.currentTarget.value = '';
      return;
    }
    const lector = new FileReader();
    lector.onload = () => {
      const url = String(lector.result ?? '');
      if (url.length > MAXIMO_LOGO) {
        errorDeImagen = 'El logo es demasiado grande: el máximo son 100 KB.';
        return;
      }
      valor = url;
    };
    lector.onerror = () => (errorDeImagen = 'No se pudo leer el archivo.');
    lector.readAsDataURL(archivo);
  }

  const numerico = $derived(['ENTERO', 'DECIMAL', 'PORCENTAJE', 'MONTO'].includes(tipoDato));
  const unidad = $derived(prefijo || sufijo);
  let encendido = $state<boolean | null>(valor === 'true');
  $effect(() => {
    if (tipoDato === 'BOOLEANO') valor = encendido ? 'true' : 'false';
  });
</script>

{#if imagen}
  <Campo {id} {etiqueta} {ayuda} error={error ?? errorDeImagen} {obligatorio}>
    {#snippet children({ describedBy, invalid })}
      <div class="logo">
        {#if hayImagen}
          <img class="vista-previa" src={valor} alt="Vista previa del logo" data-testid="logo-vista-previa" />
        {:else}
          <span class="sin-logo">Sin logo</span>
        {/if}
        <input
          {id}
          data-testid={prueba}
          type="file"
          accept="image/png,image/svg+xml"
          onchange={elegirImagen}
          disabled={deshabilitado}
          aria-describedby={describedBy}
          aria-invalid={invalid}
        />
        {#if hayImagen}
          <button type="button" class="quitar" disabled={deshabilitado} onclick={() => { valor = 'none'; errorDeImagen = null; }} data-testid="quitar-logo">Quitar el logo</button>
        {/if}
      </div>
    {/snippet}
  </Campo>
{:else if numerico}
  <Campo {id} {etiqueta} {ayuda} {error} {obligatorio}>
    {#snippet children({ describedBy, invalid })}
      {@const idUnidad = `${id}-unidad`}
      <div class="grupo-control">
        {#if prefijo}<span class="afijo" aria-hidden="true">{prefijo}</span>{/if}
        <input
          {id}
          data-testid={prueba}
          inputmode="decimal"
          autocomplete="off"
          bind:value={valor}
          disabled={deshabilitado}
          aria-describedby={[describedBy, unidad ? idUnidad : undefined].filter(Boolean).join(' ') || undefined}
          aria-invalid={invalid}
          aria-required={obligatorio}
        />
        {#if sufijo}<span class="afijo" aria-hidden="true">{sufijo}</span>{/if}
      </div>
      {#if unidad}<span id={idUnidad} hidden>en {unidad}</span>{/if}
    {/snippet}
  </Campo>
{:else if tipoDato === 'BOOLEANO'}
  <Interruptor {id} {etiqueta} bind:valor={encendido} {ayuda} {error} {deshabilitado} prueba={prueba} />
{:else if tipoDato === 'FECHA'}
  <Entrada {id} {etiqueta} bind:valor tipo="date" {ayuda} {error} {obligatorio} {deshabilitado} {prueba} />
{:else}
  <Entrada {id} {etiqueta} bind:valor {ayuda} {error} {obligatorio} {deshabilitado} {prueba} />
{/if}

<style>
  .logo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--esp-3, 0.75rem);
  }
  /* El contenedor del campo se ajusta a su contenido: sin un ancho propio, la vista previa, el selector y «Quitar»
     se apilan en vertical. En pantalla estrecha se vuelven a apilar solos (flex-wrap). */
  @media (min-width: 40rem) {
    .logo {
      min-inline-size: 36rem;
    }
  }
  .vista-previa {
    block-size: 3rem;
    inline-size: auto;
    min-inline-size: 3rem;
    max-inline-size: 12rem;
    object-fit: contain;
    padding: var(--esp-2, 0.5rem);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-md, 8px);
  }
  .sin-logo {
    color: var(--color-texto-suave, #5f5b66);
  }
  /* El estilo global de `input` lo estira al 100 %, y entonces empuja la vista previa y «Quitar» a otra línea. */
  .logo input[type='file'] {
    inline-size: auto;
    flex: 0 1 auto;
    min-block-size: var(--objetivo-min, 44px);
    font: inherit;
  }
  .quitar {
    min-block-size: var(--objetivo-min, 44px);
    padding: 0 var(--esp-3, 0.75rem);
    font: inherit;
    color: var(--color-primario, #6b21a8);
    background: transparent;
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
  }
  .grupo-control {
    display: flex;
    align-items: stretch;
    max-inline-size: 18rem;
  }
  input {
    flex: 1 1 auto;
    min-inline-size: 0;
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font: inherit;
    font-size: var(--texto-md, 1rem);
    font-variant-numeric: tabular-nums;
    text-align: end;
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    box-sizing: border-box;
  }
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
  .afijo {
    display: inline-flex;
    align-items: center;
    padding: 0 var(--esp-3, 0.75rem);
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto-suave, #5f5b66);
    background: var(--color-superficie, #faf9fc);
    border: 1px solid var(--color-borde-control, #79747e);
    white-space: nowrap;
    box-sizing: border-box;
  }
  .grupo-control > :first-child {
    border-start-start-radius: var(--radio-md, 8px);
    border-end-start-radius: var(--radio-md, 8px);
  }
  .grupo-control > :last-child {
    border-start-end-radius: var(--radio-md, 8px);
    border-end-end-radius: var(--radio-md, 8px);
  }
  .grupo-control > .afijo:first-child {
    border-inline-end: 0;
  }
  .grupo-control > .afijo:last-child {
    border-inline-start: 0;
  }
</style>
