<script lang="ts">
  /**
   * El buscador del inicio (`p01`): un campo de búsqueda con su etiqueta para lectores de pantalla y la
   * lupa dentro. Busca por el nombre que usa el negocio, no por el código técnico.
   */
  interface Props {
    id: string;
    etiqueta: string;
    pista?: string;
    valor: string;
    onescribir: (valor: string) => void;
  }

  const { id, etiqueta, pista, valor, onescribir }: Props = $props();
</script>

<div class="buscar">
  <label class="solo-lectores" for={id}>{etiqueta}</label>
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </svg>
  <input {id} type="search" placeholder={pista} value={valor} oninput={(e) => onescribir(e.currentTarget.value)} />
</div>

<style>
  .buscar {
    position: relative;
  }
  .buscar svg {
    position: absolute;
    inset-inline-start: var(--esp-3, 0.75rem);
    inset-block-start: 50%;
    transform: translateY(-50%);
    color: var(--color-texto-suave, #5f5b66);
    pointer-events: none;
  }
  input {
    box-sizing: border-box;
    inline-size: 100%;
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    padding-inline-start: 2.5rem;
    font: inherit;
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto, #1c1b1f);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
  }
  input:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  .solo-lectores {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
