<script lang="ts">
  /**
   * El acceso al home de las aplicaciones de Bonita: el icono de cuadrícula de nueve puntos que las suites de oficina
   * ponen junto a la persona. Está en TODA cabecera de sesión (las bandejas y la aplicación de parámetros), así que
   * desde cualquier aplicación creada se vuelve al directorio sin escribir una dirección.
   *
   * `/bonita/` es el home de la plataforma: redirige al directorio «Lista de aplicaciones» de la persona. Es un enlace
   * normal (misma pestaña, ventana completa: las pantallas viven dentro de un iframe de la aplicación y el home no
   * debe abrirse dentro de él): un lector de pantalla lo anuncia como enlace y se llega a él con el teclado.
   */
  interface Props {
    /** Adónde lleva. Por defecto, el home de Bonita. */
    url?: string;
    /** Nombre accesible y tooltip. */
    rotulo?: string;
  }

  const { url = '/bonita/', rotulo = 'Todas mis aplicaciones' }: Props = $props();

  // Nueve puntos en una cuadrícula de 3×3 (viewBox 24): centros en 5, 12 y 19.
  const CENTROS = [5, 12, 19] as const;
</script>

<a class="lanzador" href={url} target="_top" title={rotulo} aria-label={rotulo} data-testid="lanzador-de-apps">
  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
    {#each CENTROS as cy (cy)}
      {#each CENTROS as cx (cx)}
        <circle {cx} {cy} r="1.9" fill="currentColor" />
      {/each}
    {/each}
  </svg>
</a>

<style>
  .lanzador {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    inline-size: var(--objetivo-min, 44px);
    block-size: var(--objetivo-min, 44px);
    color: var(--color-texto-suave, #5f5b66);
    border-radius: 50%;
  }
  .lanzador:hover {
    background: var(--color-primario-suave, #f3e8ff);
    color: var(--color-primario-fuerte, #581c87);
  }
  .lanzador:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }
</style>
