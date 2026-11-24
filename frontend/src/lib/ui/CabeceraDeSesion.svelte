<script lang="ts">
  /**
   * La cabecera de una bandeja: la marca del proyecto a la izquierda y la
   * persona de la sesión con «Salir» a la derecha.
   *
   * Sustituye a la cabecera de la plataforma: la aplicación usa el layout **sin menú**, así que
   * esta es la única cabecera que la persona ve. «Salir» va al servicio de cierre de sesión de la
   * plataforma; ella manda al login.
   */
  import type { Snippet } from 'svelte';
  import { EVENTO_MARCA } from '$lib/parametros/marca';
  import LanzadorDeApps from './LanzadorDeApps.svelte';
  import MarcaCabecera from './MarcaCabecera.svelte';
  import MenuDeCuenta from './MenuDeCuenta.svelte';

  interface Props {
    /** Texto accesible de la marca. Por defecto lo toma del token `--marca-nombre`. */
    marca?: string;
    /** Nombre de la persona («Ana Analista»). */
    persona: string;
    /** Usuario de inicio de sesión, cargo e icono de Bonita: lo que enseña el menú de cuenta. */
    usuario?: string;
    cargo?: string;
    icono?: string;
    /** Adónde lleva «Salir». */
    urlSalir?: string;
    rotuloSalir?: string;
    /** Nombre estable para la automatización (`data-testid`) */
    prueba?: string;
    /** Los momentos de la bandeja: van EN la misma fila, entre la marca y la persona. */
    children?: Snippet;
  }

  const {
    marca,
    persona,
    usuario,
    cargo,
    icono,
    urlSalir = '/bonita/logoutservice?redirect=true',
    rotuloSalir = 'Salir',
    prueba,
    children,
  }: Props = $props();

  /**
   * La marca llega del módulo de parámetros DESPUÉS de montar la bandeja: cuando se aplica, el documento lo avisa y
   * el nombre se vuelve a leer del token. Los colores cambian solos porque son variables CSS vivas; el nombre es una
   * cadena que se copia a JavaScript, y sin esto se quedaba con la de antes de que llegara la del proyecto.
   */
  let marcaAplicada = $state(0);
  $effect(() => {
    const avisar = () => (marcaAplicada += 1);
    document.addEventListener(EVENTO_MARCA, avisar);
    return () => document.removeEventListener(EVENTO_MARCA, avisar);
  });

  const nombreDeMarca = $derived.by(() => {
    void marcaAplicada;
    if (marca) return marca;
    if (typeof window === 'undefined') return undefined;
    const valor = getComputedStyle(document.documentElement)
      .getPropertyValue('--marca-nombre')
      .trim()
      .replace(/^['"]|['"]$/g, '');
    return valor || undefined;
  });
</script>

<div class="cabecera" data-testid={prueba}>
  <MarcaCabecera nombre={nombreDeMarca} />
  {#if children}<div class="centro">{@render children()}</div>{/if}
  <nav class="sesion" aria-label="Sesión">
    <LanzadorDeApps />
    <MenuDeCuenta nombre={persona} {usuario} {cargo} {icono} {urlSalir} {rotuloSalir} />
  </nav>
</div>

<style>
  /* UNA sola fila (billboard: el espacio es para la tarea): marca | momentos | persona y «Salir».
     Convención de cabecera: marca a la izquierda, navegación junto a ella, persona a la derecha. */
  .cabecera {
    display: flex;
    align-items: center;
    gap: var(--esp-4, 1rem);
    min-block-size: var(--alto-cabecera, 3.25rem);
    margin-block-end: var(--esp-1, 0.25rem);
    border-block-end: 1px solid var(--color-borde, #e4e1e8);
  }

  /* La marca ya trae su margen inferior para las pantallas; aquí la alinea la fila. */
  .cabecera :global(.marca) {
    margin-block-end: 0;
    flex: none;
  }

  /* Los momentos llenan la altura de la fila: el indicador de la activa se apoya en su línea. */
  .centro {
    flex: 1 1 auto;
    min-inline-size: 0;
    align-self: stretch;
    display: flex;
    overflow-x: auto;
    /* `overflow-x: auto` vuelve `auto` también el vertical, y el indicador de la pestaña activa se apoya 1 px sobre el
       borde de la cabecera: ese píxel de más dibujaba una barra de scroll vertical pegada al nombre. Se recorta lo que
       sobra en vertical y la caja ocupa también el borde, para que la línea de la activa se vea entera. */
    overflow-y: hidden;
    margin-block-end: -2px;
  }

  .centro :global(.pestanas) {
    border-block-end: 0;
    margin-block-end: 0;
    flex: none;
  }

  /* Si no caben, los momentos se desplazan en SU fila (nunca la página); no se parten en dos líneas. */
  .centro :global(.pestanas button) {
    white-space: nowrap;
  }

  .sesion {
    margin-inline-start: auto;
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  /* Estrecho: dos filas (marca + persona, y debajo los momentos), nunca más de ~96 px. */
  @media (max-width: 48rem) {
    .cabecera {
      flex-wrap: wrap;
      gap: 0 var(--esp-3, 0.75rem);
      min-block-size: 0;
    }

    .cabecera :global(.marca) {
      min-block-size: 3rem;
    }

    .sesion {
      min-block-size: 3rem;
    }

    .centro {
      order: 3;
      flex-basis: 100%;
    }
  }
</style>
