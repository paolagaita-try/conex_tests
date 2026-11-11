<script lang="ts">
  /**
   * Cabecera de marca del proyecto. **Es el punto donde la marca neutra se hace visible.**
   *
   * El logotipo NO se incrusta aquí: se pinta desde el token `--marca-logo`, que el tema
   * de la Living Application sobreescribe. Así un proyecto cambia su identidad —logotipo,
   * color y tipografía— sin recompilar ni un formulario (verificado: la
   * misma página, con el ZIP idéntico byte a byte, servida por dos aplicaciones con temas
   * distintos).
   *
   * Si el tema no define logotipo, se muestra el nombre de marca como texto. Nunca se cae
   * a una imagen ajena ni a un hueco: la marca por defecto es neutra (`Empresa Demo`).
   *
   * Accesibilidad: el logotipo va como imagen CSS y el nombre viaja SIEMPRE en el texto
   * accesible, de modo que un lector de pantalla anuncia la entidad aunque el logotipo sea
   * decorativo.
   */
  import { EVENTO_MARCA } from '$lib/parametros/marca';

  interface Props {
    /** Texto accesible de la marca. Por defecto lo toma del token `--marca-nombre`. */
    nombre?: string;
  }

  const { nombre }: Props = $props();

  /**
   * La marca llega del módulo de parámetros DESPUÉS de montar la pantalla: cuando se aplica, el documento
   * lo avisa y la cabecera vuelve a leer el token (sin esto, un logo que llega tarde no se pintaría).
   */
  let marcaAplicada = $state(0);
  $effect(() => {
    const avisar = () => (marcaAplicada += 1);
    document.addEventListener(EVENTO_MARCA, avisar);
    return () => document.removeEventListener(EVENTO_MARCA, avisar);
  });

  /**
   * Si el tema trae logotipo, el nombre NO se repite al lado: casi todo logotipo ya
   * contiene el nombre y verlo dos veces se lee como un error. Sigue estando para los
   * lectores de pantalla, que no ven la imagen.
   */
  const tieneLogo = $derived.by(() => {
    void marcaAplicada;
    if (typeof window === 'undefined') return false;
    const valor = getComputedStyle(document.documentElement)
      .getPropertyValue('--marca-logo')
      .trim();
    return valor !== '' && valor !== 'none';
  });
</script>

<header class="marca">
  <span class="logo" class:sin-logo={!tieneLogo} role="img" aria-label={nombre ?? 'Logotipo del proyecto'}></span>
  {#if nombre}
    <span class="nombre" class:solo-lectores={tieneLogo}>{nombre}</span>
  {/if}
</header>

<style>
  .marca {
    display: flex;
    align-items: center;
    gap: var(--esp-3, 0.75rem);
    margin-block-end: var(--esp-3, 0.75rem);
  }

  /* El logotipo es un token: `--marca-logo: url(...)`. Con el default (`none`) la caja
     no ocupa espacio y solo queda el nombre. */
  .logo {
    display: block;
    block-size: var(--marca-logo-alto, 2rem);
    inline-size: var(--marca-logo-ancho, 8rem);
    background-image: var(--marca-logo, none);
    background-repeat: no-repeat;
    background-position: left center;
    background-size: contain;
  }

  /* Sin logotipo la caja no reserva 8 rem en blanco antes del nombre. */
  .sin-logo {
    display: none;
  }

  /* Sin logotipo, el nombre ES la marca y se compone con la tipografía de marca. */
  .nombre {
    font-family: var(--fuente-marca, var(--fuente-base, system-ui, sans-serif));
    font-size: var(--texto-lg, 1.125rem);
    font-weight: var(--peso-fuerte, 600);
    color: var(--color-primario, #6b21a8);
    letter-spacing: -0.01em;
  }

  /* Con logotipo, el nombre sigue existiendo para quien no ve la imagen. */
  .solo-lectores {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
