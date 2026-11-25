<script lang="ts">
  /** Área de texto con barra ligera (negrita, lista, viñeta numerada) que escribe Markdown sencillo, y contador. */
  interface Props {
    id: string;
    testid: string;
    etiqueta: string;
    ayuda?: string;
    requerido?: boolean;
    valor: string;
    error?: string;
    maximo?: number;
  }
  let { id, testid, etiqueta, ayuda = '', requerido = false, valor = $bindable(''), error, maximo = 4000 }: Props = $props();
  let area: HTMLTextAreaElement | undefined = $state();

  function envolver(antes: string, despues = antes): void {
    if (!area) return;
    const { selectionStart: a, selectionEnd: b } = area;
    valor = valor.slice(0, a) + antes + valor.slice(a, b) + despues + valor.slice(b);
    queueMicrotask(() => area?.focus());
  }
  function prefijo(p: string): void {
    if (!area) return;
    const a = area.selectionStart;
    const inicio = valor.lastIndexOf('\n', a - 1) + 1;
    valor = valor.slice(0, inicio) + p + valor.slice(inicio);
    queueMicrotask(() => area?.focus());
  }
</script>

<div class="tc-campo" data-testid={testid}>
  <label for={id}>{etiqueta}{#if requerido}<span class="tc-requerido" aria-hidden="true">*</span>{/if}</label>
  {#if ayuda}<p class="tc-ayuda" id={`${id}-ayuda`}>{ayuda}</p>{/if}
  <div class="marco" class:invalido={!!error}>
    <div class="barra" role="toolbar" aria-label={`Formato de ${etiqueta}`}>
      <button type="button" onclick={() => envolver('**')} aria-label="Negrita"><b>B</b></button>
      <button type="button" onclick={() => envolver('_')} aria-label="Cursiva"><i>I</i></button>
      <button type="button" onclick={() => prefijo('- ')} aria-label="Lista con viñetas">•</button>
      <button type="button" onclick={() => prefijo('1. ')} aria-label="Lista numerada">1.</button>
    </div>
    <textarea
      {id}
      bind:this={area}
      bind:value={valor}
      rows="6"
      maxlength={maximo}
      aria-required={requerido}
      aria-invalid={!!error}
      aria-describedby={[ayuda ? `${id}-ayuda` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined}
    ></textarea>
    <div class="pie" aria-live="polite">{valor.length} / {maximo}</div>
  </div>
  {#if error}<p class="tc-error" id={`${id}-error`}>{error}</p>{/if}
</div>

<style>
  .marco {
    border: 1px solid #8a91ad;
    border-radius: 10px;
    background: #fff;
    overflow: hidden;
  }
  .marco:focus-within {
    border-color: var(--tc-marino);
    box-shadow: 0 0 0 3px rgb(0 204 192 / 0.35);
  }
  .marco.invalido {
    border-color: #b3261e;
  }
  .barra {
    display: flex;
    gap: 0.25rem;
    padding: 0.35rem;
    background: #f4f6fb;
    border-block-end: 1px solid var(--tc-borde);
  }
  .barra button {
    font: inherit;
    min-inline-size: 2rem;
    block-size: 2rem;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    color: var(--tc-marino);
    cursor: pointer;
  }
  .barra button:hover {
    background: #fff;
    border-color: var(--tc-borde);
  }
  textarea {
    font: inherit;
    inline-size: 100%;
    box-sizing: border-box;
    border: 0;
    padding: 0.7rem 0.8rem;
    resize: vertical;
    min-block-size: 8rem;
    outline: none;
  }
  .pie {
    text-align: end;
    font-size: 0.75rem;
    color: var(--tc-texto-suave);
    padding: 0 0.6rem 0.4rem;
  }
</style>
