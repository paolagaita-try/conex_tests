<script lang="ts">
  /**
   * Autocompletar — patrón «Combobox with listbox popup» de WAI-ARIA APG.
   *
   * Para las listas de más de 15 opciones: escribir tres
   * letras es más rápido que recorrer cuarenta. Lo que garantiza:
   *  · un `combobox` con su `listbox`; la opción activa se anuncia por `aria-activedescendant` (el
   *    foco DOM se queda en el campo);
   *  · filtra por «contiene», sin distinguir mayúsculas ni tildes, y resalta lo que coincide;
   *  · flechas con vuelta, Enter elige, Escape cierra (y, cerrado, devuelve el texto de lo elegido);
   *  · SIN TEXTO LIBRE: al salir, lo escrito que no es una opción se descarta y el valor no cambia
   *    —que es exactamente el defecto que el módulo de parámetros corrige, con `∈ catálogo` pintado como texto—;
   *  · sin coincidencias, el vacío se anuncia en una región viva (`role="status"`), no como una
   *    opción deshabilitada: una opción que no se puede elegir no es un aviso.
   */
  import { tick, untrack } from 'svelte';
  import Campo from './Campo.svelte';
  import type { Opcion } from './Seleccion.svelte';

  interface Props {
    id: string;
    etiqueta: string;
    valor: string | null | undefined;
    opciones: readonly Opcion[];
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    marcador?: string;
    /** Nombre estable para la automatización (`data-testid`) */
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
    marcador,
    prueba,
  }: Props = $props();

  /** Sin tildes ni mayúsculas. Sobre un texto NFC conserva la longitud: sirve para resaltar. */
  const normalizar = (t: string) => t.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

  let texto = $state('');
  let abierto = $state(false);
  let activa = $state(-1);
  let lista: HTMLUListElement | undefined = $state();

  const elegida = $derived(opciones.find((o) => o.valor === valor));
  const buscado = $derived(normalizar(texto.trim()));
  const filtradas = $derived(
    buscado === '' || (elegida && texto === elegida.etiqueta)
      ? opciones
      : opciones.filter((o) => normalizar(o.etiqueta).includes(buscado)),
  );
  const sinCoincidencias = $derived(abierto && filtradas.length === 0);
  const idLista = $derived(`${id}-lista`);
  const idOpcion = (i: number) => `${id}-opcion-${i}`;

  /** Un valor que llega de fuera se pinta con su etiqueta. Depende SOLO de `valor`. */
  $effect(() => {
    const etiquetaElegida = opciones.find((o) => o.valor === valor)?.etiqueta;
    if (etiquetaElegida !== undefined) untrack(() => (texto = etiquetaElegida));
  });

  /** Las partes de una etiqueta: antes, lo que coincide y después (para el `<mark>`). */
  function partes(etiquetaOpcion: string): [string, string, string] {
    const i = buscado === '' ? -1 : normalizar(etiquetaOpcion).indexOf(buscado);
    if (i < 0) return [etiquetaOpcion, '', ''];
    return [
      etiquetaOpcion.slice(0, i),
      etiquetaOpcion.slice(i, i + buscado.length),
      etiquetaOpcion.slice(i + buscado.length),
    ];
  }

  function cerrar() {
    abierto = false;
    activa = -1;
  }

  function elegir(opcion: Opcion) {
    valor = opcion.valor;
    texto = opcion.etiqueta;
    cerrar();
  }

  /** Sin texto libre: lo escrito vuelve a lo elegido, o se elige si es exactamente una opción. */
  function restaurar() {
    const exacta = opciones.find((o) => normalizar(o.etiqueta) === buscado);
    if (exacta && buscado !== '') elegir(exacta);
    else texto = elegida?.etiqueta ?? '';
  }

  function alEscribir() {
    abierto = true;
    activa = -1;
  }

  async function mover(paso: 1 | -1) {
    if (!abierto) abierto = true;
    const n = filtradas.length;
    if (n === 0) return;
    activa = activa < 0 ? (paso === 1 ? 0 : n - 1) : (activa + paso + n) % n;
    await tick();
    lista?.children[activa]?.scrollIntoView?.({ block: 'nearest' });
  }

  function alTeclear(evento: KeyboardEvent) {
    if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
      evento.preventDefault();
      void mover(evento.key === 'ArrowDown' ? 1 : -1);
    } else if (evento.key === 'Enter' && abierto && activa >= 0) {
      evento.preventDefault();
      elegir(filtradas[activa]);
    } else if (evento.key === 'Escape') {
      evento.preventDefault();
      if (abierto) cerrar();
      else texto = elegida?.etiqueta ?? '';
    }
  }

  function alSalir() {
    cerrar();
    restaurar();
  }
</script>

<Campo {id} {etiqueta} {ayuda} {error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <div class="contenedor">
      <input
        data-testid={prueba}
        {id}
        type="text"
        role="combobox"
        autocomplete="off"
        placeholder={marcador}
        aria-autocomplete="list"
        aria-expanded={abierto && filtradas.length > 0}
        aria-controls={idLista}
        aria-activedescendant={abierto && activa >= 0 ? idOpcion(activa) : undefined}
        aria-describedby={describedBy}
        aria-invalid={invalid}
        aria-required={obligatorio}
        disabled={deshabilitado}
        bind:value={texto}
        oninput={alEscribir}
        onkeydown={alTeclear}
        onblur={alSalir}
      />
      <svg class="lupa" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>

      {#if abierto && filtradas.length > 0}
        <ul class="lista" id={idLista} role="listbox" aria-label={etiqueta} bind:this={lista}>
          {#each filtradas as opcion, i (opcion.valor)}
            {@const [antes, coincide, despues] = partes(opcion.etiqueta)}
            <!-- El foco no sale del campo (aria-activedescendant): la opción no es enfocable, y el
                 teclado lo atiende el combobox. `mousedown` evita el blur antes del clic. El nombre
                 es la etiqueta entera: no depende de cómo parta el resaltado al texto. -->
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <li
              id={idOpcion(i)}
              role="option"
              aria-label={opcion.etiqueta}
              class:activa={i === activa}
              class:elegida={opcion.valor === valor}
              aria-selected={i === activa}
              onmousedown={(e) => e.preventDefault()}
              onclick={() => elegir(opcion)}
            >
              {antes}{#if coincide}<mark>{coincide}</mark>{/if}{despues}
            </li>
          {/each}
        </ul>
      {/if}
      <p class="vacio" class:visible={sinCoincidencias} role="status">
        {sinCoincidencias ? `Ninguna opción coincide con «${texto.trim()}».` : ''}
      </p>
    </div>
  {/snippet}
</Campo>

<style>
  .contenedor {
    position: relative;
  }
  input {
    inline-size: 100%;
    box-sizing: border-box;
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    padding-inline-end: calc(var(--esp-3, 0.75rem) * 2 + 18px);
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
  input[aria-invalid='true'] {
    border-color: var(--color-error, #b3261e);
  }
  input:disabled {
    background: var(--color-superficie, #faf9fc);
    color: var(--color-texto-suave, #5f5b66);
    cursor: not-allowed;
  }
  .lupa {
    position: absolute;
    inset-block-start: calc((var(--objetivo-min, 44px) - 18px) / 2);
    inset-inline-end: var(--esp-3, 0.75rem);
    color: var(--color-texto-suave, #5f5b66);
    pointer-events: none;
  }
  .lista {
    position: absolute;
    z-index: 10;
    inset-block-start: calc(100% + var(--esp-1, 0.25rem));
    inset-inline: 0;
    max-block-size: calc(var(--objetivo-min, 44px) * 6);
    margin: 0;
    padding: var(--esp-1, 0.25rem);
    overflow-y: auto;
    list-style: none;
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    box-shadow: var(--sombra-lg);
  }
  li {
    display: flex;
    align-items: center;
    min-block-size: var(--objetivo-min, 44px);
    padding: 0 var(--esp-3, 0.75rem);
    color: var(--color-texto, #1c1b1f);
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
  }
  /* La activa se marca por fondo Y por un borde lateral: no solo por color. */
  li.activa {
    background: var(--color-primario-suave, #f3e8ff);
    box-shadow: inset 3px 0 0 var(--color-primario, #6b21a8);
  }
  li.elegida {
    font-weight: var(--peso-fuerte, 600);
  }
  mark {
    color: inherit;
    background: transparent;
    font-weight: var(--peso-fuerte, 600);
    text-decoration: underline;
  }
  .vacio {
    margin: 0;
  }
  .vacio.visible {
    margin-block-start: var(--esp-1, 0.25rem);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    background: var(--color-superficie, #faf9fc);
    border-radius: var(--radio-md, 8px);
  }
</style>
