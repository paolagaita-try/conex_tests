<script lang="ts">
  /**
   * Un campo para ELEGIR una persona, un grupo o un rol que se BUSCA EN EL SERVIDOR mientras se escribe. La organización
   * puede tener cientos de personas y el kit devuelve 20 por búsqueda: una lista cargada al arrancar (y filtrada aquí)
   * dice «ninguna coincide» sobre la persona 21. Sin texto libre: lo que no se elige no cuenta. WAI-ARIA APG, combobox
   * con listbox: foco en el campo, `aria-activedescendant`, flechas, Enter elige, Escape cierra.
   */
  import { onDestroy } from 'svelte';
  import Campo from '$lib/ui/Campo.svelte';
  import * as T from '../textos';

  interface Props {
    id: string;
    etiqueta: string;
    /** La etiqueta elegida (vacía si no hay). */
    valor: string;
    buscar: (q: string) => Promise<string[]>;
    error?: string | null;
    obligatorio?: boolean;
    prueba?: string;
    /** Avisa de lo elegido (para quien no lo ata con `bind:`). */
    onelegir?: (etiqueta: string) => void;
  }

  let { id, etiqueta, valor = $bindable(), buscar, error = null, obligatorio = false, prueba, onelegir }: Props = $props();

  let texto = $state('');
  let abierto = $state(false);
  let activa = $state(-1);
  let opciones = $state<string[]>([]);
  let estado = $state<'quieto' | 'buscando' | 'fallo'>('quieto');
  let temporizador: ReturnType<typeof setTimeout> | undefined;
  let busqueda = 0;
  const idLista = $derived(`${id}-lista`);
  /** El kit devuelve 20 como máximo: la posición de una opción se nombra con una letra (un número no se escribe en un identificador). */
  const CLAVES: readonly string[] = 'a b c d e f g h i j k l m n o p q r s t u v w x y z'.split(' ');

  $effect(() => {
    // Un valor que llega de fuera se pinta con su etiqueta.
    if (valor !== '') texto = valor;
  });

  async function consultar(q: string): Promise<void> {
    const esta = ++busqueda;
    estado = 'buscando';
    try {
      const r = await buscar(q);
      if (esta !== busqueda) return; // una respuesta vieja no pisa a la nueva
      opciones = r;
      activa = r.length > 0 ? 0 : -1;
      estado = 'quieto';
    } catch {
      if (esta !== busqueda) return;
      opciones = [];
      estado = 'fallo';
    }
  }

  function alEscribir(t: string): void {
    texto = t;
    abierto = true;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => void consultar(t.trim()), 200);
  }

  function elegir(o: string): void {
    valor = o;
    texto = o;
    abierto = false;
    onelegir?.(o);
  }

  function alTeclear(e: KeyboardEvent): void {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      abierto = true;
      if (opciones.length > 0) activa = (activa + (e.key === 'ArrowDown' ? 1 : -1) + opciones.length) % opciones.length;
    } else if (e.key === 'Enter' && abierto && activa >= 0 && opciones[activa] !== undefined) {
      e.preventDefault();
      elegir(opciones[activa]!);
    } else if (e.key === 'Escape') {
      abierto = false;
      texto = valor;
    }
  }

  onDestroy(() => clearTimeout(temporizador));
</script>

<Campo {id} {etiqueta} {error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <div class="buscador-servidor">
      <input
        {id}
        class="control"
        type="text"
        role="combobox"
        autocomplete="off"
        aria-expanded={abierto}
        aria-controls={idLista}
        aria-activedescendant={abierto && activa >= 0 ? `${id}-opcion-${CLAVES[activa]}` : undefined}
        aria-describedby={describedBy}
        aria-invalid={invalid}
        aria-required={obligatorio}
        value={texto}
        data-testid={prueba}
        onfocus={() => { abierto = true; void consultar(texto.trim()); }}
        oninput={(e) => alEscribir(e.currentTarget.value)}
        onkeydown={alTeclear}
        onblur={() => setTimeout(() => { abierto = false; texto = valor; }, 150)}
      />
      {#if abierto}
        <ul id={idLista} role="listbox" aria-label={etiqueta} class="resultados">
          {#each opciones as o, i (i)}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <li id="{id}-opcion-{CLAVES[i]}" role="option" aria-selected={o === valor} class:activa={i === activa} onmousedown={(e) => { e.preventDefault(); elegir(o); }} onclick={() => elegir(o)}>{o}</li>
          {/each}
        </ul>
        {#if estado === 'buscando'}
          <p role="status" class="ayuda">{T.BUSCANDO}</p>
        {:else if estado === 'fallo'}
          <p role="alert" class="error-campo">{T.BUSQUEDA_FALLIDA}</p>
        {:else if opciones.length === 0}
          <p role="status" class="ayuda">{T.NINGUNA_COINCIDE}</p>
        {/if}
      {/if}
    </div>
  {/snippet}
</Campo>
