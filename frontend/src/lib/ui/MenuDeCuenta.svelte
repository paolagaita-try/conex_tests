<script lang="ts" module>
  let siguiente = 0;
</script>

<script lang="ts">
  /**
   * La cuenta de la persona de la sesión: su avatar de Bonita (o sus iniciales) junto al nombre, y un panel con su
   * información y «Salir». Es lo que las suites de oficina ponen en la esquina, y lo que el directorio de aplicaciones
   * de Bonita ya enseña.
   *
   * ## El avatar
   * Bonita guarda en el usuario la ruta de su icono (`icons/default/icon_user.png` si nunca subió uno). Una persona con
   * avatar propio lo ve (ver `rutaDelAvatar`: la misma imagen que usa el portal). Con la silueta
   * por defecto —33 px, que se ve borrosa a este tamaño— o si la imagen no carga, se pintan las iniciales: nunca un
   * hueco ni una imagen rota. La ruta solo se acepta si cuelga de `icons/`: un valor que intente salir del tema se
   * ignora.
   *
   * ## El panel
   * Nombre completo, usuario, cargo (si lo hay) y «Salir». Se cierra con Escape (el foco vuelve al botón), con un clic
   * fuera y al volver a pulsar el botón. Es un panel de información, no un menú de acciones: un lector de pantalla lo
   * encuentra como una sección que se abre y se cierra.
   */
  interface Props {
    /** Nombre para mostrar («Ana Pérez»). */
    nombre: string;
    /** Usuario de inicio de sesión (`ana.perez`). */
    usuario?: string;
    /** Cargo de la persona en Bonita (`job_title`). */
    cargo?: string;
    /** Ruta del icono del usuario en Bonita (`icons/default/icon_user.png`). */
    icono?: string;
    urlSalir?: string;
    rotuloSalir?: string;
  }

  const { nombre, usuario, cargo, icono, urlSalir = '/bonita/logoutservice?redirect=true', rotuloSalir = 'Salir' }: Props = $props();

  const ICONO_POR_DEFECTO = 'icons/default/icon_user.png';
  const id = `panel-de-cuenta-${siguiente++}`;

  let abierto = $state(false);
  let imagenRota = $state(false);
  let raiz: HTMLElement | undefined = $state();
  let boton: HTMLButtonElement | undefined = $state();

  /**
   * La URL del avatar propio, o `null`. Bonita guarda el icono de dos formas: un recurso del tema (`icons/…`, relativo
   * a la pantalla vía `../theme/`) y, cuando la persona sube su imagen, `../API/avatars/<n>` (la API de la plataforma,
   * que desde una pantalla de aplicación hay que pedir en absoluto). Solo esas dos formas exactas: cualquier otra cosa
   * se ignora.
   */
  const rutaDelAvatar = $derived.by(() => {
    if (!icono || icono === ICONO_POR_DEFECTO) return null;
    const subido = /^\.\.\/API\/avatars\/([0-9]+)$/.exec(icono);
    if (subido) return `/bonita/API/avatars/${subido[1]}`;
    if (!/^icons\/[A-Za-z0-9_\-./]+$/.test(icono) || icono.includes('..')) return null;
    return `../theme/${icono}`;
  });
  const verImagen = $derived(rutaDelAvatar !== null && !imagenRota);

  const iniciales = $derived.by(() => {
    const palabras = nombre.trim().split(/\s+/).filter(Boolean);
    if (palabras.length === 0) return (usuario ?? '?').slice(0, 1).toUpperCase();
    const primera = palabras[0].slice(0, 1);
    const segunda = palabras.length > 1 ? palabras[palabras.length - 1].slice(0, 1) : '';
    return (primera + segunda).toUpperCase();
  });

  function cerrar(devolverFoco: boolean): void {
    abierto = false;
    if (devolverFoco) boton?.focus();
  }

  $effect(() => {
    if (!abierto) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (e.key === 'Escape') cerrar(true);
    };
    const alPulsar = (e: Event) => {
      if (raiz && !raiz.contains(e.target as Node)) cerrar(false);
    };
    window.addEventListener('keydown', alTeclear);
    document.addEventListener('pointerdown', alPulsar);
    return () => {
      window.removeEventListener('keydown', alTeclear);
      document.removeEventListener('pointerdown', alPulsar);
    };
  });
</script>

<div class="cuenta" bind:this={raiz}>
  <button
    bind:this={boton}
    type="button"
    class="disparador"
    aria-expanded={abierto}
    aria-controls={abierto ? id : undefined}
    aria-label={`Cuenta de ${nombre}`}
    onclick={() => (abierto = !abierto)}
    data-testid="menu-de-cuenta"
  >
    <span class="avatar" data-testid="avatar">
      {#if verImagen}
        <img src={rutaDelAvatar} alt="" onerror={() => (imagenRota = true)} />
      {:else}
        <span aria-hidden="true">{iniciales}</span>
      {/if}
    </span>
    <span class="nombre">{nombre}</span>
  </button>

  {#if abierto}
    <section {id} class="panel" aria-label="Tu cuenta" data-testid="panel-de-cuenta">
      <div class="ficha">
        <span class="avatar grande" aria-hidden="true">
          {#if verImagen}<img src={rutaDelAvatar} alt="" />{:else}<span>{iniciales}</span>{/if}
        </span>
        <div class="datos">
          <strong class="nombre-completo">{nombre}</strong>
          {#if usuario}<span class="usuario">{usuario}</span>{/if}
          {#if cargo}<span class="cargo" data-testid="cargo-de-cuenta">{cargo}</span>{/if}
        </div>
      </div>
      <a class="salir" href={urlSalir}>{rotuloSalir}</a>
    </section>
  {/if}
</div>

<style>
  .cuenta {
    position: relative;
    display: inline-flex;
  }

  .disparador {
    display: inline-flex;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    min-block-size: var(--objetivo-min, 44px);
    padding: 0 var(--esp-2, 0.5rem) 0 var(--esp-1, 0.25rem);
    font: inherit;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto, #1c1b1f);
    background: transparent;
    border: 0;
    border-radius: 999px;
    cursor: pointer;
  }
  .disparador:hover {
    background: var(--color-primario-suave, #f3e8ff);
  }
  .disparador:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }

  .nombre {
    font-weight: var(--peso-medio, 500);
  }
  /* Estrecho: solo el avatar (el nombre sigue en el nombre accesible del botón y en el panel). */
  @media (max-width: 40rem) {
    .nombre {
      display: none;
    }
  }

  .avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    inline-size: 2rem;
    block-size: 2rem;
    overflow: hidden;
    font-size: var(--texto-sm, 0.875rem);
    font-weight: var(--peso-fuerte, 600);
    color: var(--color-primario-fuerte, #581c87);
    background: var(--color-primario-suave, #f3e8ff);
    border-radius: 50%;
  }
  .avatar.grande {
    inline-size: 3rem;
    block-size: 3rem;
    font-size: var(--texto-lg, 1.125rem);
  }
  .avatar img {
    inline-size: 100%;
    block-size: 100%;
    object-fit: cover;
  }

  .panel {
    position: absolute;
    inset-block-start: calc(100% + var(--esp-1, 0.25rem));
    inset-inline-end: 0;
    z-index: 20;
    inline-size: max-content;
    min-inline-size: 15rem;
    max-inline-size: min(22rem, 90vw);
    display: flex;
    flex-direction: column;
    gap: var(--esp-3, 0.75rem);
    padding: var(--esp-4, 1rem);
    background: var(--color-fondo, #fff);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 12px);
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.12);
  }

  .ficha {
    display: flex;
    align-items: center;
    gap: var(--esp-3, 0.75rem);
  }
  .datos {
    display: flex;
    flex-direction: column;
    min-inline-size: 0;
  }
  .nombre-completo {
    font-size: var(--texto-md, 1rem);
    overflow-wrap: anywhere;
  }
  .usuario,
  .cargo {
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    overflow-wrap: anywhere;
  }

  .salir {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-block-size: var(--objetivo-min, 44px);
    padding: 0 var(--esp-4, 1rem);
    color: var(--color-primario-fuerte, #581c87);
    text-decoration: none;
    font-weight: var(--peso-medio, 500);
    border: 1px solid var(--color-borde-control, #79747e);
    border-radius: var(--radio-md, 8px);
  }
  .salir:hover {
    background: var(--color-primario-suave, #f3e8ff);
  }
  .salir:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }
</style>
