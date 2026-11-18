<script lang="ts">
  /**
   * Envoltorio de un campo de formulario: etiqueta, ayuda, error y estado accesible.
   *
   * Centraliza la accesibilidad de TODOS los campos porque al abandonar los widgets de UI Designer desapareció el default de la
   * plataforma, así que la accesibilidad es responsabilidad nuestra y se verifica con
   * test en el cimiento — no pantalla por pantalla.
   *
   * Lo que garantiza, y por eso los campos no lo implementan cada uno:
   *  · la etiqueta está ASOCIADA al control (`for`/`id`), no solo colocada al lado;
   *  · la ayuda y el error se anuncian con `aria-describedby`;
   *  · el error marca `aria-invalid` y se emite en un `role="alert"`;
   *  · lo obligatorio se marca en el DOM (`aria-required`) y no solo con un asterisco.
   *
   * Un GRUPO no es etiquetable: un `<label for>` que apunta a un
   * `div` no le da nombre. Con `grupo`, la etiqueta se pinta con un id y el control se nombra con
   * `aria-labelledby={etiquetadoPor}`. Sin `grupo`, el DOM es el de siempre.
   */
  import type { Snippet } from 'svelte';

  interface Props {
    /** Identificador del control. Es lo que ata la etiqueta con el campo. */
    id: string;
    etiqueta: string;
    /** Texto de ayuda. En este proyecto suele venir de la columna del contrato. */
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    /** El control es un grupo sin elemento etiquetable: se nombra por `etiquetadoPor`. */
    grupo?: boolean;
    /** El control, que recibe los identificadores accesibles ya calculados. */
    children: Snippet<
      [{ describedBy: string | undefined; invalid: boolean; etiquetadoPor: string | undefined }]
    >;
  }

  const {
    id,
    etiqueta,
    ayuda,
    error = null,
    obligatorio = false,
    grupo = false,
    children,
  }: Props = $props();

  const idAyuda = $derived(ayuda ? `${id}-ayuda` : undefined);
  const idError = $derived(error ? `${id}-error` : undefined);
  const describedBy = $derived([idAyuda, idError].filter(Boolean).join(' ') || undefined);
  const etiquetadoPor = $derived(grupo ? `${id}-etiqueta` : undefined);
</script>

<div class="campo" class:con-error={!!error}>
  <!-- El rótulo se declara UNA vez y lo pintan las dos ramas: la prosa de la galería es
       una sola, y dos copias del asterisco serían dos verdades. -->
  {#snippet rotulo()}
    {etiqueta}
    {#if obligatorio}
      <!-- El asterisco es decorativo: lo que anuncia la obligatoriedad al lector de
           pantalla es `aria-required` en el propio control. -->
      <span class="marca" aria-hidden="true">*</span>
    {/if}
  {/snippet}
  {#if grupo}
    <span class="etiqueta" id={etiquetadoPor}>{@render rotulo()}</span>
  {:else}
    <label for={id}>{@render rotulo()}</label>
  {/if}

  {#if ayuda}
    <p class="ayuda" id={idAyuda}>{ayuda}</p>
  {/if}

  {@render children({ describedBy, invalid: !!error, etiquetadoPor })}

  {#if error}
    <p class="error" id={idError} role="alert">{error}</p>
  {/if}
</div>

<style>
  .campo {
    display: flex;
    flex-direction: column;
    gap: var(--esp-1, 0.25rem);
    margin-block-end: var(--esp-4, 1rem);
  }
  label,
  .etiqueta {
    font-weight: 600;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto, #1a1a1a);
  }
  .marca {
    color: var(--color-error, #b3261e);
  }
  .ayuda {
    margin: 0;
    font-size: var(--texto-xs, 0.75rem);
    color: var(--color-texto-suave, #5f6368);
  }
  .error {
    margin: 0;
    font-size: var(--texto-xs, 0.75rem);
    color: var(--color-error, #b3261e);
    font-weight: 500;
  }
</style>
