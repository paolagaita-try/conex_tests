<script lang="ts">
  /**
   * Pantalla «Revisar el saludo» (`frm_holaRevisar`). ESQUELETO: el arnés lo escribió una vez y es del
   * proyecto; edítalo. Lo que sale de la documentación —los campos, el cuerpo del contrato y su esquema— está
   * en `generado/` y se regenera con `tools/arnes.sh generar`.
   */
  import { Aviso, AccionesDeFormulario, CamposDeContrato, type ValoresDelFormulario } from '$lib/ui';
  import { leerContexto } from '$lib/bonita/contexto';
  import { ejecutarTarea } from '$lib/bonita/cliente';
  import { cargarLecturas } from '$lib/bonita/caso';
  import type { LectorDeValores } from '$lib/parametros/opciones';
  import { CAMPOS, LECTURAS, cuerpoDelContrato, type CuerpoDelContrato } from './generado/contrato';
  import { ETIQUETAS, TEXTOS } from './textos';
  import { erroresDe } from './validacion';

  const contexto = leerContexto();

  function textoDelFallo(e: unknown): string {
    return e instanceof Error ? e.message : TEXTOS.errorGenerico;
  }

  // Los datos de solo lectura se cargan una vez al abrir; si la lectura falla, se dice (no se pintan vacíos).
  let lecturas = $state<string[] | null>(null);
  let falloLectura = $state<string | null>(null);

  async function cargar(): Promise<void> {
    try {
      lecturas = await cargarLecturas(LECTURAS, contexto, false);
    } catch (e) {
      falloLectura = textoDelFallo(e);
    }
  }

  if (LECTURAS.length > 0) void cargar();

  interface Props {
    /** Envía el cuerpo del contrato al motor; las pruebas inyectan un doble. */
    enviar?: (cuerpo: CuerpoDelContrato) => Promise<unknown>;
    /** Quién lee el módulo de parámetros (listas y topes); las pruebas inyectan un doble. */
    lector?: LectorDeValores;
  }

  async function alMotor(cuerpo: CuerpoDelContrato): Promise<unknown> {
    if (!contexto.idTarea) throw new Error(TEXTOS.sinContexto);
    return ejecutarTarea(contexto.idTarea, { ...cuerpo });
  }

  const { enviar = alMotor, lector }: Props = $props();

  let valores = $state<ValoresDelFormulario>({});
  let errores = $state<Record<string, string | null>>({});
  let problemas = $state<Record<string, string>>({});
  let estado = $state<'ocioso' | 'enviando' | 'enviado' | 'error'>('ocioso');
  let fallo = $state<string | null>(null);

  /** Con datos del caso que leer, no se envía mientras cargan ni si la lectura falló. */
  const sinDatosDelCaso = $derived(LECTURAS.length > 0 && (lecturas === null || falloLectura !== null));

  /** La etiqueta propia (`textos.ts`) o la «Campo» de la matriz. */
  const etiquetas = Object.fromEntries(CAMPOS.map((c) => [c.ruta, ETIQUETAS[c.ruta] ?? c.etiqueta]));

  async function alEnviar(evento: SubmitEvent): Promise<void> {
    evento.preventDefault();
    if (sinDatosDelCaso) return;
    const cuerpo = cuerpoDelContrato(valores);
    errores = erroresDe(cuerpo);
    if (Object.keys(errores).length > 0 || Object.keys(problemas).length > 0) return;
    estado = 'enviando';
    fallo = null;
    try {
      await enviar(cuerpo);
      estado = 'enviado';
    } catch (e) {
      estado = 'error';
      fallo = textoDelFallo(e);
    }
  }
</script>

<main data-formulario={contexto.tipo}>
  <header class="cabecera">
    <h1>{TEXTOS.titulo}</h1>
  </header>

  {#if LECTURAS.length > 0}
    {#if falloLectura}
      <Aviso tono="error" titulo={TEXTOS.errorLectura}><p>{falloLectura}</p><p>{TEXTOS.sinDatosNoSeEnvia}</p></Aviso>
    {:else}
      <!-- Datos del caso de solo lectura, de la extensión de lecturas del caso. -->
      <dl class="lecturas" aria-busy={lecturas === null}>
        {#each LECTURAS as lectura, i (i)}
          <dt>{lectura.etiqueta}</dt>
          <dd data-lee={lectura.lee}>{lecturas ? lecturas[i] : TEXTOS.cargando}</dd>
        {/each}
      </dl>
    {/if}
  {/if}

  {#if estado === 'enviado'}
    <Aviso tono="exito" titulo={TEXTOS.enviado}><p>{TEXTOS.enviadoDetalle}</p></Aviso>
  {:else}
    {#if estado === 'error'}
      <Aviso tono="error" titulo={TEXTOS.error}><p>{fallo ?? TEXTOS.errorGenerico}</p></Aviso>
    {/if}
    <form id="formulario" onsubmit={alEnviar} novalidate>
      <CamposDeContrato
        campos={CAMPOS}
        bind:valores
        {errores}
        {etiquetas}
        tarea={contexto.idTarea}
        {lector}
        bind:problemas
      />
      <AccionesDeFormulario
        principal={TEXTOS.accion}
        ocupado={estado === 'enviando'}
        deshabilitado={sinDatosDelCaso}
      />
    </form>
  {/if}
</main>

<style>
  main {
    max-inline-size: 60rem;
    margin-inline: auto;
    padding: var(--esp-5, 1.5rem);
  }

  .lecturas {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: var(--esp-2, 0.5rem) var(--esp-4, 1rem);
    margin: 0 0 var(--esp-5, 1.5rem);
  }
</style>
