<script lang="ts">
  /**
   * El marco de la aplicación: cabecera con la marca y la sesión, saludo y titular, y las pestañas que
   * le corresponden a cada perfil (`p01`, `p10`, `p11`). Lo usan el contenedor real y la galería viva:
   * las mismas piezas en los dos sitios.
   *
   * El menú de la plataforma va vacío (layout sin menú): esta es la única navegación que la persona ve.
   */
  import type { Snippet } from 'svelte';
  import LanzadorDeApps from '$lib/ui/LanzadorDeApps.svelte';
  import MenuDeCuenta from '$lib/ui/MenuDeCuenta.svelte';
  import MarcaCabecera from '$lib/ui/MarcaCabecera.svelte';
  import Pestanas, { type Pestana } from '$lib/ui/Pestanas.svelte';
  import type { Recuento } from '$lib/bonita/marcas';
  import { veLasAprobaciones, veLosPermisos, type Capacidades } from '../capacidades';
  import * as T from '../textos';
  import type { Seccion } from '../ruta';
  import Chip from './Chip.svelte';
  import '../estilos.css';

  interface Props {
    persona: string;
    /** Usuario, cargo e icono de Bonita: lo que enseña el menú de cuenta. */
    usuario?: string;
    cargo?: string;
    icono?: string;
    capacidades: Capacidades;
    /** Los procesos que el delegado administra, ya en lenguaje de negocio («Becas de estudio»). */
    procesos?: string;
    seccion: Seccion;
    /** Cuántos cambios esperan a esta persona (el contador de Aprobaciones). */
    porAprobar?: Recuento | null;
    /** El saludo y el titular de la pantalla de inicio. */
    titular?: string | null;
    /** La persona está DENTRO de una sección (una lista, importar…): pulsar su pestaña activa vuelve a su inicio. */
    dentro?: boolean;
    onir: (seccion: Seccion) => void;
    urlSalir?: string;
    children: Snippet;
  }

  const { persona, usuario, cargo, icono, capacidades, procesos = '', seccion, porAprobar = null, titular = null, dentro = false, onir, urlSalir, children }: Props = $props();

  const pestanas = $derived.by<Pestana[]>(() => {
    const p: Pestana[] = [{ id: 'parametros', rotulo: T.PESTANAS.parametros }];
    if (veLasAprobaciones(capacidades)) {
      p.push({ id: 'aprobaciones', rotulo: T.PESTANAS.aprobaciones, contador: porAprobar !== null && porAprobar > 0 ? porAprobar : null });
    }
    if (veLosPermisos(capacidades)) p.push({ id: 'permisos', rotulo: T.PESTANAS.permisos });
    p.push({ id: 'traza', rotulo: T.PESTANAS.traza });
    return p;
  });
</script>

<main class="pa">
  <header class="cabecera">
    <MarcaCabecera />
    <nav class="sesion" aria-label="Sesión">
      <LanzadorDeApps />
      {#if capacidades.perfil === 'superadministracion'}
        <Chip tono="marca">{T.CHIP_SUPERADMINISTRACION}</Chip>
      {:else if capacidades.perfil === 'delegado'}
        <Chip tono="neutro">{T.chipDelegado(procesos)}</Chip>
      {/if}
      <MenuDeCuenta nombre={persona} {usuario} {cargo} {icono} urlSalir={urlSalir ?? '/bonita/logoutservice?redirect=true'} />
    </nav>
  </header>

  {#if titular !== null}
    <header class="saludo">
      <h1>{T.saludo(persona)}</h1>
      <p class="titular">{titular}</p>
    </header>
  {/if}

  <!-- `Pestanas` no avisa de un clic en la pestaña YA activa; desde dentro de una sección ese clic es «volver al inicio». -->
  <div
    role="presentation"
    onclick={(e) => {
      const pestana = (e.target as HTMLElement).closest('[role="tab"]');
      if (dentro && pestana?.getAttribute('aria-selected') === 'true') onir(seccion);
    }}
  >
    <Pestanas {pestanas} activa={seccion} nombre={T.NOMBRE_DE_LAS_SECCIONES} onchange={(id) => onir(id as Seccion)} />
  </div>

  {@render children()}
</main>

<style>
  .cabecera {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: var(--esp-4, 1rem);
    row-gap: var(--esp-2, 0.5rem);
    margin-block-end: var(--esp-6, 2rem);
  }
  .cabecera :global(.marca) {
    margin-block-end: 0;
  }
  .sesion {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }
</style>
