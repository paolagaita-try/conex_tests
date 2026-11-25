<script lang="ts">
  /**
   * Pantalla «Diseñar la propuesta» (`frm_20_disenarPropuesta`). Del proyecto (el esqueleto lo escribió el arnés);
   * el contrato y su esquema viven en `generado/` y se regeneran con `tools/arnes.sh generar`.
   */
  import { leerContexto } from '$lib/bonita/contexto';
  import { ejecutarTarea } from '$lib/bonita/cliente';
  import { subirArchivo, type ArchivoSubido } from '$lib/bonita/archivos';
  import Encabezado from '$lib/preventa/Encabezado.svelte';
  import PanelesContexto from '$lib/preventa/PanelesContexto.svelte';
  import NotaRica from '$lib/preventa/NotaRica.svelte';
  import { esUrl, precargar, valor, type Precarga } from '$lib/preventa/contexto';
  import { CAMPOS, ENTRADAS, type CuerpoDelContrato } from './generado/contrato';
  import { TEXTOS } from './textos';
  import { erroresDePantalla } from './validacion';

  interface Props {
    enviar?: (cuerpo: CuerpoDelContrato) => Promise<unknown>;
    cargar?: () => Promise<Precarga>;
    /** Sube un archivo a Bonita (`formFileUpload`); las pruebas inyectan un doble. */
    subir?: (archivo: File) => Promise<ArchivoSubido>;
  }

  const contexto = leerContexto();

  async function alMotor(cuerpo: CuerpoDelContrato): Promise<unknown> {
    if (!contexto.idTarea) throw new Error(TEXTOS.sinContexto);
    return ejecutarTarea(contexto.idTarea, { ...cuerpo });
  }
  async function subirABonita(archivo: File): Promise<ArchivoSubido> {
    const bytes = new Uint8Array(await archivo.arrayBuffer());
    let binario = '';
    for (const b of bytes) binario += String.fromCharCode(b);
    return subirArchivo({ nombre: archivo.name, contenido: btoa(binario) } as Parameters<typeof subirArchivo>[0]);
  }

  const { enviar = alMotor, cargar = () => precargar(contexto), subir = subirABonita }: Props = $props();

  let datos = $state<Precarga | null>(null);
  let falloLectura = $state<string | null>(null);
  cargar().then(
    (d) => (datos = d),
    (e: unknown) => (falloLectura = e instanceof Error ? e.message : TEXTOS.errorGenerico),
  );

  let valoracionOperaciones = $state('');
  let urlPptaPreventa = $state('');
  let linkRepoPreventa = $state('');
  let notaPropuesta = $state('');
  let archivos = $state<File[]>([]);
  let arrastrando = $state(false);
  let errores = $state<Record<string, string>>({});
  let estado = $state<'ocioso' | 'enviando' | 'enviado' | 'error'>('ocioso');
  let fallo = $state<string | null>(null);
  let selector: HTMLInputElement | undefined = $state();

  const etiqueta = (ruta: string) => CAMPOS.find((c) => c.ruta === ruta)?.etiqueta ?? ruta;
  const ENLACES = [
    { ruta: 'urlPptaPreventa', ayuda: 'Presentación de la propuesta (Google Slides, PowerPoint en línea…).' },
    { ruta: 'linkRepoPreventa', ayuda: 'Carpeta o repositorio con todo el material de la preventa.' },
  ] as const;
  const enlaces: Record<string, string> = $derived({ urlPptaPreventa, linkRepoPreventa });

  function agregar(lista: FileList | null | undefined): void {
    if (!lista) return;
    const nuevos = [...lista].filter((f) => !archivos.some((a) => a.name === f.name && a.size === f.size));
    archivos = [...archivos, ...nuevos];
  }
  function quitar(i: number): void {
    archivos = archivos.filter((_, j) => j !== i);
  }
  function tamano(n: number): string {
    return n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
  }
  function soltar(e: DragEvent): void {
    e.preventDefault();
    arrastrando = false;
    agregar(e.dataTransfer?.files);
  }

  function cuerpo(adjuntos: ArchivoSubido[] | null): CuerpoDelContrato {
    const t = (v: string) => (v.trim() === '' ? null : v.trim());
    return {
      valoracionOperaciones: t(valoracionOperaciones),
      urlPptaPreventa: t(urlPptaPreventa),
      linkRepoPreventa: t(linkRepoPreventa),
      notaPropuesta: t(notaPropuesta),
      adjuntos,
    };
  }

  async function alEnviar(evento: SubmitEvent): Promise<void> {
    evento.preventDefault();
    if (!datos) return;
    errores = erroresDePantalla(cuerpo([]));
    if (Object.keys(errores).length > 0) {
      document.getElementById(`campo-${Object.keys(errores)[0]}`)?.focus();
      return;
    }
    estado = 'enviando';
    fallo = null;
    try {
      const subidos = await Promise.all(archivos.map((a) => subir(a)));
      await enviar(cuerpo(subidos));
      estado = 'enviado';
    } catch (e) {
      estado = 'error';
      fallo = e instanceof Error ? e.message : TEXTOS.errorGenerico;
    }
  }
</script>

<main class="tc-pagina" data-formulario="tarea" data-entradas={ENTRADAS.join(',')}>
  <Encabezado titulo={TEXTOS.titulo} etapa="Diseño de la propuesta" hubspot={datos?.hubspot ?? null} caso={datos?.caso ?? null} />

  <div class="tc-rejilla">
    <div class="columna">
      {#if datos?.caso}
        <section class="tc-tarjeta validacion" aria-labelledby="titulo-validacion-previa">
          <h2 id="titulo-validacion-previa">Resultado de la validación</h2>
          <p class="sello">{valor(datos.caso.resultadoValidacion)}</p>
          <dl>
            <div><dt>Concepto</dt><dd>{valor(datos.caso.conceptoViabilidad)}</dd></div>
            <div><dt>Nota</dt><dd>{valor(datos.caso.notaValidacion)}</dd></div>
            <div><dt>Supuestos</dt><dd>{valor(datos.caso.supuestos)}</dd></div>
          </dl>
        </section>
      {/if}
      <PanelesContexto hubspot={datos?.hubspot ?? null} fallo={falloLectura} />
    </div>

    <section class="tc-tarjeta" aria-labelledby="titulo-propuesta">
      <h2 id="titulo-propuesta">Artefactos de la propuesta</h2>
      {#if estado === 'enviado'}
        <div class="tc-aviso tc-aviso--exito" role="status">
          <strong>Propuesta enviada</strong>Los artefactos quedaron en el caso y se reflejan en el Negocio de HubSpot.
        </div>
      {:else}
        {#if estado === 'error'}
          <div class="tc-aviso tc-aviso--error" role="alert"><strong>{TEXTOS.error}</strong>{fallo}</div>
        {/if}
        <form onsubmit={alEnviar} novalidate>
          <div class="tc-campo" data-testid="campo-valoracionOperaciones">
            <label for="campo-valoracionOperaciones">{etiqueta('valoracionOperaciones')}<span class="tc-requerido" aria-hidden="true">*</span></label>
            <p class="tc-ayuda" id="ayuda-valoracion">
              Enlace al documento con el esfuerzo, el equipo y los riesgos operativos estimados para la solución.
            </p>
            <div class="url" class:ok={esUrl(valoracionOperaciones)}>
              <span class="prefijo" aria-hidden="true">🔗</span>
              <input
                id="campo-valoracionOperaciones"
                class="tc-control"
                type="url"
                inputmode="url"
                placeholder="https://"
                bind:value={valoracionOperaciones}
                aria-required="true"
                aria-invalid={!!errores.valoracionOperaciones}
                aria-describedby={errores.valoracionOperaciones ? 'ayuda-valoracion error-valoracion' : 'ayuda-valoracion'}
              />
              {#if esUrl(valoracionOperaciones)}<span class="valida">URL válida</span>{/if}
            </div>
            {#if errores.valoracionOperaciones}<p class="tc-error" id="error-valoracion">{errores.valoracionOperaciones}</p>{/if}
          </div>

          {#each ENLACES as e (e.ruta)}
            <div class="tc-campo" data-testid={`campo-${e.ruta}`}>
              <label for={`campo-${e.ruta}`}>{etiqueta(e.ruta)}<span class="tc-requerido" aria-hidden="true">*</span></label>
              <p class="tc-ayuda" id={`ayuda-${e.ruta}`}>{e.ayuda}</p>
              <div class="url" class:ok={esUrl(enlaces[e.ruta])}>
                <span class="prefijo" aria-hidden="true">🔗</span>
                {#if e.ruta === 'urlPptaPreventa'}
                  <input id="campo-urlPptaPreventa" class="tc-control" type="url" inputmode="url" placeholder="https://"
                    bind:value={urlPptaPreventa} aria-required="true" aria-invalid={!!errores.urlPptaPreventa}
                    aria-describedby={errores.urlPptaPreventa ? 'ayuda-urlPptaPreventa error-urlPptaPreventa' : 'ayuda-urlPptaPreventa'} />
                {:else}
                  <input id="campo-linkRepoPreventa" class="tc-control" type="url" inputmode="url" placeholder="https://"
                    bind:value={linkRepoPreventa} aria-required="true" aria-invalid={!!errores.linkRepoPreventa}
                    aria-describedby={errores.linkRepoPreventa ? 'ayuda-linkRepoPreventa error-linkRepoPreventa' : 'ayuda-linkRepoPreventa'} />
                {/if}
                {#if esUrl(enlaces[e.ruta])}<span class="valida">URL válida</span>{/if}
              </div>
              {#if errores[e.ruta]}<p class="tc-error" id={`error-${e.ruta}`}>{errores[e.ruta]}</p>{/if}
            </div>
          {/each}

          <NotaRica id="campo-notaPropuesta" testid="campo-notaPropuesta" etiqueta={etiqueta('notaPropuesta')}
            ayuda="Opcional. Contexto para el comercial: alcance, supuestos, próximos pasos." bind:valor={notaPropuesta} />

          <div class="tc-campo" data-testid="campo-adjuntos">
            <span class="tc-leyenda" id="etiqueta-adjuntos">{etiqueta('adjuntos')}</span>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
              class="zona"
              class:activa={arrastrando}
              ondragover={(e) => { e.preventDefault(); arrastrando = true; }}
              ondragleave={() => (arrastrando = false)}
              ondrop={soltar}
            >
              <span class="nube" aria-hidden="true">⬆</span>
              <p><strong>Arrastre y suelte los archivos aquí</strong><br />o</p>
              <button type="button" class="secundario" onclick={() => selector?.click()} aria-describedby="etiqueta-adjuntos">
                Elegir archivos
              </button>
              <input id="campo-adjuntos" class="tc-sr" type="file" multiple bind:this={selector} tabindex="-1"
                aria-labelledby="etiqueta-adjuntos" onchange={(e) => agregar((e.currentTarget as HTMLInputElement).files)} />
            </div>
            {#if archivos.length > 0}
              <ul class="adjuntos" aria-label="Archivos adjuntos">
                {#each archivos as a, i (a.name + a.size)}
                  <li>
                    <span class="ext" aria-hidden="true">{a.name.split('.').pop()?.slice(0, 4).toUpperCase()}</span>
                    <span class="nombre">{a.name}<small>{tamano(a.size)}</small></span>
                    <button type="button" class="quitar" onclick={() => quitar(i)} aria-label={`Quitar ${a.name}`}>✕</button>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>

          <div class="tc-acciones">
            <button class="tc-boton" type="submit" disabled={estado === 'enviando' || !datos}>
              {#if estado === 'enviando'}<span class="tc-giro" aria-hidden="true"></span>Enviando…{:else}{TEXTOS.accion}{/if}
            </button>
          </div>
        </form>
      {/if}
    </section>
  </div>
</main>

<style>
  .columna {
    display: grid;
    gap: 1.25rem;
  }
  .validacion dl {
    display: grid;
    gap: 0.5rem;
    margin: 0;
  }
  .validacion dt {
    font-size: 0.75rem;
    color: var(--tc-texto-suave);
  }
  .validacion dd {
    margin: 0;
  }
  .sello {
    display: inline-block;
    margin: 0 0 0.75rem;
    padding: 0.2rem 0.8rem;
    border-radius: 999px;
    background: var(--tc-turquesa-suave);
    color: var(--tc-turquesa-texto);
    font-weight: 700;
    text-transform: capitalize;
  }
  .url {
    position: relative;
    display: flex;
    align-items: center;
  }
  .url .prefijo {
    position: absolute;
    inset-inline-start: 0.75rem;
  }
  .url input {
    padding-inline-start: 2.3rem;
  }
  .url.ok input {
    border-color: #1b8f86;
  }
  .valida {
    position: absolute;
    inset-inline-end: 0.75rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--tc-turquesa-texto);
  }
  .zona {
    border: 2px dashed #9aa3c4;
    border-radius: 14px;
    padding: 1.25rem;
    text-align: center;
    background: #fafbff;
    transition: background 0.15s, border-color 0.15s;
  }
  .zona.activa {
    border-color: var(--tc-turquesa);
    background: var(--tc-turquesa-suave);
  }
  .zona p {
    margin: 0.25rem 0 0.6rem;
    color: var(--tc-texto-suave);
  }
  .nube {
    font-size: 1.5rem;
    color: var(--tc-marino);
  }
  .secundario {
    font: inherit;
    font-weight: 600;
    color: var(--tc-marino);
    background: #fff;
    border: 1.5px solid var(--tc-marino);
    border-radius: 999px;
    padding: 0.45rem 1.2rem;
    cursor: pointer;
  }
  .adjuntos {
    list-style: none;
    padding: 0;
    margin: 0.75rem 0 0;
    display: grid;
    gap: 0.5rem;
  }
  .adjuntos li {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    border: 1px solid var(--tc-borde);
    border-radius: 10px;
    padding: 0.5rem 0.75rem;
    background: #fff;
  }
  .ext {
    font-size: 0.7rem;
    font-weight: 700;
    color: #fff;
    background: var(--tc-marino);
    border-radius: 6px;
    padding: 0.3rem 0.4rem;
    min-inline-size: 2.4rem;
    text-align: center;
  }
  .nombre {
    flex: 1;
    display: grid;
    min-inline-size: 0;
    overflow-wrap: anywhere;
  }
  .nombre small {
    color: var(--tc-texto-suave);
  }
  .quitar {
    border: 0;
    background: transparent;
    color: #8c1d16;
    cursor: pointer;
    font-size: 1rem;
    inline-size: 2rem;
    block-size: 2rem;
    border-radius: 50%;
  }
  .quitar:hover {
    background: #fdeceb;
  }
</style>
