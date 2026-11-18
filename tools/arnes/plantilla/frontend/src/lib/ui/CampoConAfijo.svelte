<script lang="ts">
  /**
   * Campo con prefijo o sufijo: montos y porcentajes con su unidad a la vista
   * («$», «%», «días»), según la regla de widget por defecto.
   *
   * Lo que garantiza:
   *  · el afijo visible está oculto al lector y la unidad se anuncia UNA vez, como descripción
   *    («en $») desde un nodo `hidden`: ni el lector la lee dos veces ni la persona tiene que
   *    adivinarla;
   *  · rango y decimales permitidos se validan al salir del campo, con el error asociado por
   *    `Campo`; lo que no vale deja el valor vacío, no un número a medias;
   *  · el valor entregado es un NÚMERO, sin separadores ni unidad. Se acepta el separador de miles
   *    del `LOCALE` de `formato.ts` («,») y el punto decimal; «2.350.000» no se adivina: se dice que no vale.
   *
   * El formateo es solo de lo que la persona TECLEÓ, no de una cifra del caso.
   */
  import { untrack } from 'svelte';
  import Campo from './Campo.svelte';
  import { LOCALE } from './formato';
  import { numeroTecleado, type NumeroTecleado } from '$lib/ui/valores';

  interface Props {
    id: string;
    etiqueta: string;
    /**
     * Un número, solo TECLEADO: lo pone `numeroTecleado()` al leer el texto del campo. Una pantalla
     * no puede pasar aquí un número calculado.
     */
    valor: NumeroTecleado | null | undefined;
    /** Unidad delante del número («$»). */
    prefijo?: string;
    /** Unidad detrás del número («%», «días»). */
    sufijo?: string;
    minimo?: number;
    maximo?: number;
    /** Decimales permitidos: 2 por defecto (montos); 0 para enteros (plazos). */
    decimales?: number;
    /** Cómo se anuncia la unidad; por defecto «en <afijo>». */
    unidadLeida?: string;
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
    prefijo,
    sufijo,
    minimo,
    maximo,
    decimales = 2,
    unidadLeida,
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    marcador,
    prueba,
  }: Props = $props();

  const unidad = $derived(unidadLeida ?? `en ${prefijo ?? sufijo ?? ''}`.trim());
  const idUnidad = $derived(`${id}-unidad`);
  const conUnidad = $derived(Boolean(prefijo || sufijo));

  const formato = $derived(
    new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 0, maximumFractionDigits: decimales }),
  );

  /** Un límite dicho con su unidad: «$2,000,000», «48 días». */
  function conAfijo(n: number): string {
    const cifra = formato.format(n);
    if (prefijo) return `${prefijo}${cifra}`;
    if (sufijo) return `${cifra} ${sufijo}`;
    return cifra;
  }

  let texto = $state('');
  let errorPropio = $state<string | null>(null);

  /** Un valor numérico que llega de fuera manda sobre el texto. Depende SOLO de `valor`. */
  $effect(() => {
    const v = valor;
    if (typeof v !== 'number' || !Number.isFinite(v)) return;
    untrack(() => {
      if (leer(texto) !== v) texto = formato.format(v);
    });
  });

  /** Lo que la persona escribió, leído como número (miles con «,», punto decimal) por el lector del cimiento. */
  function leer(t: string): NumeroTecleado | null {
    return numeroTecleado(t);
  }

  function confirmar() {
    const limpio = texto.trim();
    if (limpio === '') {
      errorPropio = null;
      valor = null;
      return;
    }
    const n = leer(limpio);
    const decimalesEscritos = limpio.split('.')[1]?.length ?? 0;
    let mensaje: string | null = null;
    if (n === null) mensaje = 'Escribe solo números, con punto para los decimales.';
    else if (decimalesEscritos > decimales) {
      mensaje = decimales === 0 ? 'Escribe un número entero.' : `Usa como máximo ${decimales} decimales.`;
    } else if (minimo !== undefined && n < minimo) mensaje = `El mínimo es ${conAfijo(minimo)}.`;
    else if (maximo !== undefined && n > maximo) mensaje = `Supera el máximo de ${conAfijo(maximo)}.`;

    if (mensaje !== null || n === null) {
      errorPropio = mensaje;
      valor = null;
      return;
    }
    errorPropio = null;
    valor = n;
    texto = formato.format(n);
  }
</script>

<Campo {id} {etiqueta} {ayuda} error={errorPropio ?? error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <div class="grupo" class:invalido={invalid} class:deshabilitado>
      {#if prefijo}<span class="afijo" aria-hidden="true">{prefijo}</span>{/if}
      <input
        data-testid={prueba}
        {id}
        type="text"
        inputmode={decimales === 0 ? 'numeric' : 'decimal'}
        autocomplete="off"
        placeholder={marcador}
        bind:value={texto}
        onblur={confirmar}
        onkeydown={(e) => e.key === 'Enter' && confirmar()}
        disabled={deshabilitado}
        aria-describedby={[conUnidad ? idUnidad : undefined, describedBy].filter(Boolean).join(' ') ||
          undefined}
        aria-invalid={invalid}
        aria-required={obligatorio}
      />
      {#if sufijo}<span class="afijo" aria-hidden="true">{sufijo}</span>{/if}
      <!-- `hidden`: la unidad viaja SOLO como descripción del campo (aria-describedby lee un nodo
           oculto); visible para el árbol de accesibilidad, un lector en modo lectura la anunciaba
           dos veces (H1 de la verificación adversarial). -->
      {#if conUnidad}<span id={idUnidad} hidden>{unidad}</span>{/if}
    </div>
  {/snippet}
</Campo>

<style>
  /* El borde es del GRUPO: afijo y número se leen como un solo control (WCAG 1.4.11, 3:1). */
  .grupo {
    position: relative;
    display: flex;
    align-items: stretch;
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
    overflow: hidden;
  }
  .grupo:focus-within {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }
  .grupo.invalido {
    border-color: var(--color-error, #b3261e);
  }
  .grupo.deshabilitado {
    background: var(--color-superficie, #faf9fc);
  }
  .afijo {
    display: inline-flex;
    align-items: center;
    padding: 0 var(--esp-3, 0.75rem);
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto-suave, #5f5b66);
    background: var(--color-superficie, #faf9fc);
    white-space: nowrap;
  }
  /* El objetivo táctil es el CAMPO: con el mínimo en el grupo, su borde se comía 2 px y el input
     medía 42 (medido en Chromium). El grupo crece con su borde. */
  input {
    flex: 1;
    min-inline-size: 0;
    min-block-size: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    font: inherit;
    font-size: var(--texto-md, 1rem);
    color: var(--color-texto, #1c1b1f);
    background: transparent;
    border: 0;
    outline: none;
  }
  input:disabled {
    color: var(--color-texto-suave, #5f5b66);
    cursor: not-allowed;
  }
</style>
