<script lang="ts">
  /**
   * Visor documental de SOLO LECTURA con carrusel — para que el funcionario revise los
   * documentos del caso sin salir de su pantalla.
   *
   * Lo necesitan las pantallas internas que deciden mirando papeles. Vive en la galería
   * porque si cada pantalla construyera el suyo tendríamos varios visores distintos.
   *
   * **Sin dependencias nuevas.** El stack autorizado no incluye ninguna librería de PDF ni
   * de carrusel, y no hace falta: el navegador ya trae visor de PDF, así que el documento
   * se incrusta y la navegación entre documentos es nuestra. Menos peso, menos superficie
   * y nada que pedirle a la allowlist.
   *
   * **Qué significa «solo lectura» aquí, con precisión**: esta interfaz no permite
   * sustituir, borrar ni anotar el documento — no hay ninguna acción que escriba. Lo que
   * **no** puede hacer (y conviene no prometerlo) es impedir que quien lo ve guarde una
   * copia: el visor de PDF del navegador ofrece descargar e imprimir, y eso no está bajo
   * nuestro control. Si el requisito fuera evitar la copia, haría falta una marca de agua
   * server-side o un visor por imágenes, y es una decisión de negocio, no de esta pantalla.
   *
   * En Bonita el contenido se sirve por la `url` que devuelve `GET /API/bpm/caseDocument`
   * (`documentDownload?fileName=…&contentStorageId=…`), relativa al portal. Este componente
   * no la construye: la recibe ya resuelta, para no acoplar la presentación a la API.
   */
  export interface DocumentoVisible {
    /** Identificador estable, para la clave de la lista. */
    id: string;
    /** Cómo lo llama el negocio: «Justificante médico», «Calendario del equipo». */
    tipo: string;
    nombreArchivo: string;
    /** Dirección del contenido, ya resuelta por quien llama. */
    url: string;
    /** Texto libre del estado de validación, si lo hay. */
    estado?: string;
    fecha?: string;
    /** Tipo de contenido, para elegir cómo se muestra. */
    contenido?: 'pdf' | 'imagen' | 'otro';
  }

  interface Props {
    documentos: readonly DocumentoVisible[];
    /** Documento mostrado al abrir. */
    inicial?: number;
    /** Alto del área de visualización. En una bandeja conviene fijarlo. */
    alto?: string;
  }

  const { documentos, inicial = 0, alto = '32rem' }: Props = $props();

  /**
   * `elegido` es null mientras nadie ha navegado: así la prop `inicial` sigue mandando
   * (y si cambia, se respeta) en vez de quedar congelada en el primer valor. En cuanto
   * alguien pasa un documento, su elección gobierna.
   */
  let elegido = $state<number | null>(null);

  const posicion = $derived.by(() => {
    const base = elegido ?? inicial ?? 0;
    return Math.min(Math.max(base, 0), Math.max(documentos.length - 1, 0));
  });
  const actual = $derived(documentos[posicion]);
  const hayVarios = $derived(documentos.length > 1);

  function anterior(): void {
    // Circular: en una revisión se va y se vuelve, y toparse con un botón muerto molesta.
    elegido = (posicion - 1 + documentos.length) % documentos.length;
  }

  function siguiente(): void {
    elegido = (posicion + 1) % documentos.length;
  }

  /** Las flechas del teclado son el gesto natural para pasar documentos. */
  function alPulsarTecla(evento: KeyboardEvent): void {
    if (!hayVarios) return;
    if (evento.key === 'ArrowLeft') {
      evento.preventDefault();
      anterior();
    } else if (evento.key === 'ArrowRight') {
      evento.preventDefault();
      siguiente();
    }
  }


  function claseDeContenido(doc: DocumentoVisible): 'pdf' | 'imagen' | 'otro' {
    if (doc.contenido) return doc.contenido;
    const n = doc.nombreArchivo.toLowerCase();
    if (n.endsWith('.pdf')) return 'pdf';
    if (/\.(png|jpe?g|gif|webp|bmp|tiff?)$/.test(n)) return 'imagen';
    return 'otro';
  }
</script>

{#if documentos.length === 0}
  <p class="vacio">Este expediente todavía no tiene documentos cargados.</p>
{:else}
  <section
    class="visor"
    aria-roledescription="visor de documentos"
    aria-label="Documentos del expediente"
  >
    <header>
      <div class="identidad">
        <p class="tipo">{actual.tipo}</p>
        <p class="archivo">
          {actual.nombreArchivo}
          {#if actual.fecha}<span class="fecha">· {actual.fecha}</span>{/if}
        </p>
      </div>

      {#if actual.estado}
        <span class="estado" class:conforme={/conforme|válid|valid/i.test(actual.estado)}>
          {actual.estado}
        </span>
      {/if}
    </header>

    <!-- Visualización. `object` deja el visor del navegador y permite un contenido
         alternativo si no puede incrustarlo (no todos los navegadores incrustan PDF). -->
    <div class="lienzo" style:block-size={alto}>
      {#key actual.id}
        {#if claseDeContenido(actual) === 'imagen'}
          <img src={actual.url} alt="Documento: {actual.tipo}" />
        {:else}
          <object data={actual.url} type="application/pdf" title="Documento: {actual.tipo}">
            <div class="alterno">
              <p>Su navegador no puede mostrar este documento incrustado.</p>
              <a href={actual.url} target="_blank" rel="noopener noreferrer">
                Abrir «{actual.nombreArchivo}» en una pestaña nueva
              </a>
            </div>
          </object>
        {/if}
      {/key}
    </div>

    {#if hayVarios}
      <!-- Carrusel: la posición se anuncia como texto, no solo por la miniatura activa. -->
      <footer>
        <button type="button" class="paso" onclick={anterior} aria-label="Documento anterior">
          <span aria-hidden="true">‹</span>
        </button>

        <div
          class="tiras"
          role="tablist"
          aria-label="Documentos del expediente"
          tabindex="0"
          onkeydown={alPulsarTecla}
        >
          {#each documentos as doc, i (doc.id)}
            <button
              type="button"
              role="tab"
              class="tira"
              class:activa={i === posicion}
              aria-selected={i === posicion}
              onclick={() => (elegido = i)}
            >
              <span class="orden">{i + 1}</span>
              <span class="etiqueta">{doc.tipo}</span>
            </button>
          {/each}
        </div>

        <button type="button" class="paso" onclick={siguiente} aria-label="Documento siguiente">
          <span aria-hidden="true">›</span>
        </button>
      </footer>

      <p class="posicion" aria-live="polite">
        Documento {posicion + 1} de {documentos.length}: {actual.tipo}
      </p>
    {/if}
  </section>
{/if}

<style>
  .visor {
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    overflow: hidden;
    background: var(--color-fondo, #fff);
  }

  .vacio {
    margin: 0;
    padding: var(--esp-5, 1.5rem);
    border: 1px dashed var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    color: var(--color-texto-suave, #5f5b66);
    font-size: var(--texto-sm, 0.875rem);
  }

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: var(--esp-4, 1rem);
    padding: var(--esp-4, 1rem) var(--esp-5, 1.5rem);
    border-block-end: 1px solid var(--color-borde, #e4e1e8);
  }

  .tipo {
    margin: 0;
    font-weight: var(--peso-fuerte, 600);
  }

  .archivo {
    margin: var(--esp-1, 0.25rem) 0 0;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    font-family: var(--fuente-mono, monospace);
  }

  .fecha {
    font-family: var(--fuente-base, system-ui, sans-serif);
  }

  .estado {
    flex: none;
    font-size: var(--texto-xs, 0.75rem);
    padding: 0.15rem 0.6rem;
    border-radius: var(--radio-completo, 999px);
    background: var(--color-aviso-suave, #fdf3e2);
    color: var(--color-aviso, #8a5a00);
    white-space: nowrap;
  }

  .conforme {
    background: var(--color-exito-suave, #e7f4ec);
    color: var(--color-exito, #1b6b3a);
  }

  /* El gris de fondo es el del visor de PDF: da el borde del papel sin dibujarlo. */
  .lienzo {
    display: grid;
    background: #f1f0f4;
  }

  .lienzo object,
  .lienzo img {
    inline-size: 100%;
    block-size: 100%;
    border: none;
  }

  .lienzo img {
    object-fit: contain;
  }

  .alterno {
    align-self: center;
    justify-self: center;
    text-align: center;
    padding: var(--esp-5, 1.5rem);
    font-size: var(--texto-sm, 0.875rem);
  }

  footer {
    display: flex;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    padding: var(--esp-3, 0.75rem) var(--esp-3, 0.75rem);
    border-block-start: 1px solid var(--color-borde, #e4e1e8);
    background: var(--color-superficie, #faf9fc);
  }

  .paso {
    flex: none;
    inline-size: var(--objetivo-min, 44px);
    block-size: var(--objetivo-min, 44px);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-md, 8px);
    background: var(--color-fondo, #fff);
    color: var(--color-texto, #1c1b1f);
    font-size: var(--texto-lg, 1.125rem);
    cursor: pointer;
    line-height: 1;
  }

  .paso:hover {
    background: var(--color-primario-suave, #f3e8ff);
  }

  .paso:focus-visible,
  .tira:focus-visible {
    outline: var(--ancho-foco, 2px) solid var(--color-foco, #6b21a8);
    outline-offset: 2px;
  }

  .tiras {
    display: flex;
    gap: var(--esp-2, 0.5rem);
    overflow-x: auto;
    flex: 1;
    padding-block: 0.15rem;
  }

  .tira {
    display: flex;
    align-items: center;
    gap: var(--esp-2, 0.5rem);
    flex: none;
    min-block-size: var(--objetivo-min, 44px);
    padding-inline: var(--esp-3, 0.75rem);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-md, 8px);
    background: var(--color-fondo, #fff);
    cursor: pointer;
    font: inherit;
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
    white-space: nowrap;
  }

  /* El documento activo se distingue por color Y por peso: no solo por color. */
  .activa {
    border-color: var(--color-primario, #6b21a8);
    background: var(--color-primario-suave, #f3e8ff);
    color: var(--color-primario-fuerte, #581c87);
    font-weight: var(--peso-fuerte, 600);
  }

  .orden {
    font-variant-numeric: tabular-nums;
    font-size: var(--texto-xs, 0.75rem);
  }

  .posicion {
    margin: 0;
    padding: var(--esp-2, 0.5rem) var(--esp-5, 1.5rem) var(--esp-3, 0.75rem);
    font-size: var(--texto-xs, 0.75rem);
    color: var(--color-texto-suave, #5f5b66);
    background: var(--color-superficie, #faf9fc);
  }
</style>
