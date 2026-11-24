<script lang="ts">
  /**
   * Campo de fecha con calendario — patrón «Date Picker Dialog» de WAI-ARIA APG.
   *
   * Por qué existe: la regla de widget por defecto pide calendario para una fecha, y la
   * fecha nativa del navegador ni respeta días no hábiles ni se deja verificar por teclado y ARIA en
   * el cimiento. Se escribe la fecha como `dd/mm/aaaa` o se elige en una rejilla operable
   * solo con el teclado; al contrato viaja en ISO `aaaa-mm-dd`, como la de `Entrada tipo="date"`.
   *
   * Lo que garantiza:
   *  · la rejilla es un `grid` y cada día un `gridcell` nombrado con su fecha completa; el día con
   *    foco recibe el foco DOM real (el lector lo anuncia) y es el único en el orden de tabulación;
   *  · flechas (día/semana), Re Pág/Av Pág (mes), Inicio/Fin (lunes/domingo), Enter/Espacio
   *    (elegir), Escape (cerrar sin cambiar); al cerrar, el foco vuelve al campo; el Tab no se
   *    escapa del diálogo mientras está abierto;
   *  · `minimo`, `maximo` y `noHabiles` llegan COMO DATO:
   *    esos días se ven deshabilitados y no se eligen; lo tecleado que los incumple, o que no es
   *    una fecha, se rechaza con el error asociado por `Campo` y el valor queda vacío;
   *  · en el teléfono el diálogo es una hoja inferior: se cambia la composición, no se encoge el
   *    control por debajo de 44 px (sistema de diseño).
   */
  import { tick, untrack } from 'svelte';
  import Campo from './Campo.svelte';
  import {
    aIso,
    aTexto,
    deIso,
    deTexto,
    iguales,
    mensajeDeError,
    motivoNoElegible,
    nombreCompleto,
    nombreDelMes,
    rejillaDelMes,
    sumarDias,
    sumarMeses,
    inicioDeSemana,
    finDeSemana,
    DIAS_DE_LA_SEMANA,
    diaCorto,
    type Dia,
    type Restricciones,
  } from './fechasDelCalendario';

  interface Props {
    id: string;
    etiqueta: string;
    /** ISO `aaaa-mm-dd`, o vacío. */
    valor: string | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    /** Primer día elegible, ISO, incluido. */
    minimo?: string;
    /** Último día elegible, ISO, incluido. */
    maximo?: string;
    /** Días de la semana (0 = domingo) y feriados (ISO) que no se pueden elegir. */
    noHabiles?: Restricciones['noHabiles'];
    /** Hoy, ISO. Por defecto, el día local de quien usa la pantalla. */
    hoy?: string;
    /** Nombre estable para la automatización (`data-testid`) */
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
    minimo,
    maximo,
    noHabiles,
    hoy,
    prueba,
  }: Props = $props();

  const restricciones = $derived<Restricciones>({ minimo, maximo, noHabiles });

  /** Hoy en el calendario LOCAL de la persona: «hoy» es un día suyo, no un instante UTC. */
  const diaDeHoy = $derived.by<Dia>(() => {
    const dado = hoy ? deIso(hoy) : null;
    if (dado) return dado;
    const ahora = new Date();
    return { a: ahora.getFullYear(), m: ahora.getMonth() + 1, d: ahora.getDate() };
  });

  const elegido = $derived(valor ? deIso(valor) : null);

  let texto = $state('');
  let errorPropio = $state<string | null>(null);
  let abierto = $state(false);
  let enfoque = $state<Dia>({ a: 2000, m: 1, d: 1 });

  let contenedor: HTMLDivElement | undefined = $state();
  let campo: HTMLInputElement | undefined = $state();
  let dialogo: HTMLDivElement | undefined = $state();

  /** Un valor válido que llega de fuera manda sobre el texto. Depende SOLO de `valor`. */
  $effect(() => {
    const dia = valor ? deIso(valor) : null;
    if (!dia) return;
    const escrito = untrack(() => deTexto(texto));
    if (!escrito || !iguales(escrito, dia)) texto = aTexto(dia);
  });

  const semanas = $derived(rejillaDelMes(enfoque.a, enfoque.m));
  const idDialogo = $derived(`${id}-calendario`);
  const idMes = $derived(`${id}-mes`);

  const elegible = (dia: Dia) => motivoNoElegible(dia, restricciones) === null;

  /** Lunes a domingo, con sus iniciales: «X» es el miércoles (dos «M» no se distinguen). */
  const CABECERAS = [
    { n: 1, inicial: 'L' },
    { n: 2, inicial: 'M' },
    { n: 3, inicial: 'X' },
    { n: 4, inicial: 'J' },
    { n: 5, inicial: 'V' },
    { n: 6, inicial: 'S' },
    { n: 0, inicial: 'D' },
  ];
  const ultimoElegible = $derived(maximo ? deIso(maximo) : null);

  async function enfocarDia(dia: Dia) {
    enfoque = dia;
    await tick();
    dialogo?.querySelector<HTMLElement>(`[data-dia="${aIso(dia)}"]`)?.focus();
  }

  async function abrir() {
    if (deshabilitado) return;
    abierto = true;
    await enfocarDia(elegido ?? diaDeHoy);
  }

  async function cerrar(devolverFoco: boolean) {
    abierto = false;
    if (devolverFoco) {
      await tick();
      campo?.focus();
    }
  }

  function elegir(dia: Dia) {
    if (!elegible(dia)) return;
    valor = aIso(dia);
    texto = aTexto(dia);
    errorPropio = null;
    void cerrar(true);
  }

  /** Lo tecleado se confirma al salir del campo o con Enter. */
  function confirmarTexto() {
    if (texto.trim() === '') {
      errorPropio = null;
      valor = null;
      return;
    }
    const mensaje = mensajeDeError(texto, restricciones);
    if (mensaje) {
      errorPropio = mensaje;
      valor = null;
      return;
    }
    const dia = deTexto(texto) as Dia;
    errorPropio = null;
    valor = aIso(dia);
    texto = aTexto(dia);
  }

  function alTeclearEnCampo(evento: KeyboardEvent) {
    if (evento.key === 'Enter') {
      evento.preventDefault();
      confirmarTexto();
    }
  }

  function alTeclearEnDia(evento: KeyboardEvent, dia: Dia) {
    const destino: Record<string, () => Dia> = {
      ArrowRight: () => sumarDias(dia, 1),
      ArrowLeft: () => sumarDias(dia, -1),
      ArrowDown: () => sumarDias(dia, 7),
      ArrowUp: () => sumarDias(dia, -7),
      PageDown: () => sumarMeses(dia, 1),
      PageUp: () => sumarMeses(dia, -1),
      Home: () => inicioDeSemana(dia),
      End: () => finDeSemana(dia),
    };
    if (destino[evento.key]) {
      evento.preventDefault();
      void enfocarDia(destino[evento.key]());
    } else if (evento.key === 'Enter' || evento.key === ' ') {
      evento.preventDefault();
      elegir(dia);
    }
  }

  /** Escape cierra desde cualquier control; el Tab da la vuelta dentro del diálogo. */
  function alTeclearEnDialogo(evento: KeyboardEvent) {
    if (evento.key === 'Escape') {
      evento.preventDefault();
      void cerrar(true);
      return;
    }
    if (evento.key !== 'Tab' || !dialogo) return;
    const enfocables = [
      ...dialogo.querySelectorAll<HTMLElement>('button, [tabindex="0"]'),
    ];
    const primero = enfocables[0];
    const ultimo = enfocables[enfocables.length - 1];
    if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primero.focus();
    } else if (evento.shiftKey && document.activeElement === primero) {
      evento.preventDefault();
      ultimo.focus();
    }
  }

  /** Un clic fuera cierra sin robar el foco a lo que se pulsó. */
  function alPulsarFuera(evento: PointerEvent) {
    if (abierto && contenedor && !contenedor.contains(evento.target as Node)) void cerrar(false);
  }

  function cambiarMes(n: number) {
    enfoque = sumarMeses(enfoque, n);
  }
</script>

<svelte:window onpointerdown={alPulsarFuera} />

<Campo {id} {etiqueta} {ayuda} error={errorPropio ?? error} {obligatorio}>
  {#snippet children({ describedBy, invalid })}
    <div class="contenedor" bind:this={contenedor}>
      <div class="control">
        <input
          data-testid={prueba}
          {id}
          type="text"
          inputmode="numeric"
          autocomplete="off"
          placeholder="dd/mm/aaaa"
          bind:this={campo}
          bind:value={texto}
          onblur={confirmarTexto}
          onkeydown={alTeclearEnCampo}
          disabled={deshabilitado}
          aria-describedby={describedBy}
          aria-invalid={invalid}
          aria-required={obligatorio}
        />
        <button
          type="button"
          class="abrir"
          aria-label="Elegir fecha"
          aria-haspopup="dialog"
          aria-expanded={abierto}
          aria-controls={abierto ? idDialogo : undefined}
          disabled={deshabilitado}
          onclick={abrir}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            stroke-width="2" aria-hidden="true">
            <rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" />
          </svg>
        </button>
      </div>

      {#if abierto}
        <div
          class="calendario"
          id={idDialogo}
          role="dialog"
          aria-modal="true"
          aria-label="Elegir fecha"
          tabindex="-1"
          bind:this={dialogo}
          onkeydown={alTeclearEnDialogo}
        >
          <div class="mes">
            <button type="button" aria-label="Mes anterior" onclick={() => cambiarMes(-1)}>
              <span aria-hidden="true">‹</span>
            </button>
            <p class="nombre-mes" id={idMes} aria-live="polite">{nombreDelMes(enfoque.a, enfoque.m)}</p>
            <button type="button" aria-label="Mes siguiente" onclick={() => cambiarMes(1)}>
              <span aria-hidden="true">›</span>
            </button>
          </div>

          <table role="grid" aria-labelledby={idMes}>
            <thead>
              <tr>
                {#each CABECERAS as c (c.n)}
                  <th role="columnheader" scope="col" abbr={DIAS_DE_LA_SEMANA[c.n]}>{c.inicial}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each semanas as semana (aIso(semana[0]))}
                <tr>
                  {#each semana as dia (aIso(dia))}
                    {@const esElegido = elegido !== null && iguales(dia, elegido)}
                    {@const noElegible = !elegible(dia)}
                    <td
                      role="gridcell"
                      data-dia={aIso(dia)}
                      tabindex={iguales(dia, enfoque) ? 0 : -1}
                      aria-label={nombreCompleto(dia)}
                      aria-selected={esElegido}
                      aria-disabled={noElegible ? true : undefined}
                      aria-current={iguales(dia, diaDeHoy) ? 'date' : undefined}
                      class:fuera={dia.m !== enfoque.m}
                      onclick={() => elegir(dia)}
                      onkeydown={(e) => alTeclearEnDia(e, dia)}
                    >
                      {dia.d}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
          <p class="pie">
            <span>Hoy: {diaCorto(diaDeHoy)}</span>
            {#if ultimoElegible}<span>Hasta el {diaCorto(ultimoElegible)}</span>{/if}
          </p>
        </div>
      {/if}
    </div>
  {/snippet}
</Campo>

<style>
  .contenedor {
    position: relative;
  }
  .control {
    position: relative;
    display: flex;
  }
  input {
    flex: 1;
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-3, 0.75rem);
    /* Sitio para el botón del calendario, que ocupa un objetivo táctil completo. */
    padding-inline-end: calc(var(--objetivo-min, 44px) + var(--esp-1, 0.25rem));
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
  .abrir {
    position: absolute;
    inset-block: 0;
    inset-inline-end: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-inline-size: var(--objetivo-min, 44px);
    min-block-size: var(--objetivo-min, 44px);
    color: var(--color-texto-suave, #5f5b66);
    background: transparent;
    border: 0;
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
  }
  .abrir:disabled {
    cursor: not-allowed;
  }
  .abrir:focus-visible,
  .mes button:focus-visible,
  td:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 1px;
  }

  .calendario {
    position: absolute;
    z-index: 10;
    inset-block-start: calc(100% + var(--esp-1, 0.25rem));
    inset-inline-start: 0;
    padding: var(--esp-3, 0.75rem);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    box-shadow: var(--sombra-lg);
  }
  .mes {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--esp-2, 0.5rem);
    margin-block-end: var(--esp-2, 0.5rem);
  }
  .mes button {
    min-inline-size: var(--objetivo-min, 44px);
    min-block-size: var(--objetivo-min, 44px);
    font: inherit;
    font-size: var(--texto-lg, 1.25rem);
    color: var(--color-texto, #1c1b1f);
    background: transparent;
    border: 0;
    border-radius: var(--radio-md, 8px);
    cursor: pointer;
  }
  .nombre-mes {
    margin: 0;
    font-weight: var(--peso-fuerte, 600);
    color: var(--color-texto, #1c1b1f);
  }
  /* «octubre de 2026» → «Octubre de 2026» sin cambiar el texto que se anuncia. */
  .nombre-mes::first-letter {
    text-transform: uppercase;
  }
  table {
    border-collapse: separate;
    border-spacing: 0;
  }
  th {
    padding-block-end: var(--esp-1, 0.25rem);
    font-size: var(--texto-xs, 0.75rem);
    font-weight: var(--peso-normal, 400);
    color: var(--color-texto-suave, #5f5b66);
  }
  td {
    inline-size: var(--objetivo-min, 44px);
    block-size: var(--objetivo-min, 44px);
    min-inline-size: var(--objetivo-min, 44px);
    text-align: center;
    color: var(--color-texto, #1c1b1f);
    /* Círculos, como el diseño aprobado: el elegido relleno, hoy con aro. */
    border-radius: var(--radio-completo, 999px);
    cursor: pointer;
  }
  td.fuera {
    color: var(--color-texto-suave, #5f5b66);
  }
  td[aria-current='date'] {
    font-weight: var(--peso-fuerte, 600);
    box-shadow: inset 0 0 0 1px var(--color-borde-control, #79747e);
  }
  td[aria-selected='true'] {
    color: var(--color-texto-inverso, #fff);
    background: var(--color-primario, #6b21a8);
  }
  /* Deshabilitado no solo por color: también tachado. */
  td[aria-disabled='true'] {
    color: var(--color-texto-suave, #5f5b66);
    text-decoration: line-through;
    cursor: not-allowed;
  }

.pie {
    display: flex;
    justify-content: space-between;
    gap: var(--esp-3, 0.75rem);
    margin: var(--esp-2, 0.5rem) 0 0;
    padding-block-start: var(--esp-2, 0.5rem);
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    border-block-start: 1px solid var(--color-borde, #e4e1e8);
  }

    /* En el teléfono, hoja inferior (sistema de diseño: se cambia la composición, no se encoge el
     control). 40rem deja la tableta de 768 px con el desplegable anclado al campo. El corte se
     escribe a mano porque un @media no puede leer una custom property (como en PanelDeDetalle). */
  @media (max-width: 40rem) {
    .calendario {
      position: fixed;
      inset-block-start: auto;
      inset-block-end: 0;
      inset-inline: 0;
      border-radius: var(--radio-xl, 24px) var(--radio-xl, 24px) 0 0;
    }
    /* La rejilla se centra con celdas cuadradas de 44: estirada al ancho, los días en círculo
       salían óvalos (medido a 390 en la galería desplegada). 7 × 44 = 308 px caben en 390. */
    table {
      margin-inline: auto;
    }
  }
</style>
