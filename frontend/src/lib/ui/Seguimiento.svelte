<script lang="ts">
  /**
   * Seguimiento del recorrido: en qué etapa va la solicitud y qué queda por delante.
   *
   * Patrón de timeline vertical con hitos (hecho / en curso / pendiente), el estándar de
   * las apps de servicio para «¿en qué va lo mío?». Responde la pregunta antes de que el
   * usuario tenga que interpretar un estado suelto.
   *
   * **RESTRICCIÓN DE VISIBILIDAD**: las etapas son las del recorrido VISIBLE
   * del cliente. Ninguna nombra verificaciones ni revisiones internas.
   * Todo lo interno transcurre dentro de «En
   * análisis», que es deliberadamente neutro. Un hito más «informativo» aquí sería una
   * filtración: no se añade.
   *
   * Este componente no decide en qué etapa está nadie: recibe la etapa activa ya calculada
   * desde el estado visible del expediente.
   */
  interface Etapa {
    id: string;
    titulo: string;
    /** Qué significa para el solicitante, en su idioma. */
    detalle?: string;
  }

  interface Props {
    etapas: Etapa[];
    /** `id` de la etapa en curso. */
    activa: string;
    /** Etapas ya superadas. */
    completadas: string[];
  }

  const { etapas, activa, completadas }: Props = $props();

  function estadoDe(id: string): 'hecha' | 'actual' | 'pendiente' {
    if (completadas.includes(id)) return 'hecha';
    return id === activa ? 'actual' : 'pendiente';
  }

  const ETIQUETA = {
    hecha: 'Completada',
    actual: 'En curso',
    pendiente: 'Pendiente',
  } as const;
</script>

<ol class="linea">
  {#each etapas as etapa (etapa.id)}
    {@const estado = estadoDe(etapa.id)}
    <li class={estado} aria-current={estado === 'actual' ? 'step' : undefined}>
      <span class="marca" aria-hidden="true"></span>
      <div class="texto">
        <p class="titulo">
          {etapa.titulo}
          <span class="sr-solo">({ETIQUETA[estado]})</span>
        </p>
        {#if etapa.detalle}<p class="detalle">{etapa.detalle}</p>{/if}
      </div>
    </li>
  {/each}
</ol>

<style>
  .linea {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  li {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--esp-4, 1rem);
    padding-block-end: var(--esp-5, 1.5rem);
    position: relative;
  }

  /* El hilo que une los hitos. No se dibuja bajo el último. */
  li:not(:last-child)::before {
    content: '';
    position: absolute;
    inset-block: 1.35rem var(--esp-1, 0.25rem);
    inset-inline-start: 0.5rem;
    inline-size: 2px;
    background: var(--color-borde, #e4e1e8);
  }

  li:last-child {
    padding-block-end: 0;
  }

  .marca {
    inline-size: 1.125rem;
    block-size: 1.125rem;
    border-radius: var(--radio-completo, 999px);
    border: 2px solid var(--color-borde, #e4e1e8);
    background: var(--color-fondo, #fff);
    margin-block-start: 0.2rem;
    z-index: 1;
  }

  .hecha .marca {
    background: var(--color-primario, #6b21a8);
    border-color: var(--color-primario, #6b21a8);
  }

  /* La etapa en curso es la única con anillo: el ojo va ahí primero. */
  .actual .marca {
    border-color: var(--color-primario, #6b21a8);
    box-shadow: 0 0 0 4px var(--color-primario-suave, #f3e8ff);
  }

  .titulo {
    margin: 0;
    font-size: var(--texto-md, 1rem);
    font-weight: var(--peso-medio, 500);
    color: var(--color-texto, #1c1b1f);
  }

  .actual .titulo {
    font-weight: var(--peso-fuerte, 600);
  }

  /* Lo que aún no ocurre se atenúa, pero conservando contraste legible (WCAG AA). */
  .pendiente .titulo {
    color: var(--color-texto-suave, #5f5b66);
    font-weight: var(--peso-normal, 400);
  }

  .detalle {
    margin: var(--esp-1, 0.25rem) 0 0;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    line-height: var(--linea-normal, 1.5);
  }

  /* El estado de cada hito se transmite por color y forma; para quien no los percibe,
     viaja además como texto solo para lectores de pantalla. */
  .sr-solo {
    position: absolute;
    inline-size: 1px;
    block-size: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
</style>
