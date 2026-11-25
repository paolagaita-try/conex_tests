<script lang="ts">
  /**
   * Pantalla «Validar la solicitud» (`frm_10_validarSolicitud`). Del proyecto (el esqueleto lo escribió el arnés);
   * el contrato y su esquema viven en `generado/` y se regeneran con `tools/arnes.sh generar`.
   */
  import { leerContexto } from '$lib/bonita/contexto';
  import { ejecutarTarea } from '$lib/bonita/cliente';
  import Encabezado from '$lib/preventa/Encabezado.svelte';
  import PanelesContexto from '$lib/preventa/PanelesContexto.svelte';
  import NotaRica from '$lib/preventa/NotaRica.svelte';
  import { precargar, type Precarga } from '$lib/preventa/contexto';
  import { CAMPOS, ENTRADAS, type CuerpoDelContrato } from './generado/contrato';
  import { TEXTOS } from './textos';
  import { CONCEPTOS, CONCEPTO_NO_VIABLE, erroresDePantalla } from './validacion';

  interface Props {
    /** Envía el cuerpo del contrato al motor; las pruebas inyectan un doble. */
    enviar?: (cuerpo: CuerpoDelContrato) => Promise<unknown>;
    /** Carga el caso y la precarga de HubSpot; las pruebas inyectan un doble. */
    cargar?: () => Promise<Precarga>;
  }

  const contexto = leerContexto();

  async function alMotor(cuerpo: CuerpoDelContrato): Promise<unknown> {
    if (!contexto.idTarea) throw new Error(TEXTOS.sinContexto);
    return ejecutarTarea(contexto.idTarea, { ...cuerpo });
  }

  const { enviar = alMotor, cargar = () => precargar(contexto) }: Props = $props();

  let datos = $state<Precarga | null>(null);
  let falloLectura = $state<string | null>(null);
  cargar().then(
    (d) => (datos = d),
    (e: unknown) => (falloLectura = e instanceof Error ? e.message : TEXTOS.errorGenerico),
  );

  const OPCIONES = [
    { valor: 'viable', titulo: 'Viable', icono: '✓', explica: 'La solicitud pasa a Diseño de la propuesta.' },
    { valor: 'bloqueado', titulo: 'Bloqueado', icono: '⏸', explica: 'El ticket queda «En espera información del lead» hasta que llegue lo que falta.' },
    { valor: 'no_viable', titulo: 'No viable', icono: '✕', explica: 'El ticket se cierra como «cerrado por viabilidad».' },
  ] as const;

  let resultado = $state<string | null>(null);
  let conceptoViabilidad = $state('');
  let notaValidacion = $state('');
  let supuestos = $state('');
  let errores = $state<Record<string, string>>({});
  let estado = $state<'ocioso' | 'enviando' | 'enviado' | 'error'>('ocioso');
  let fallo = $state<string | null>(null);

  const exigeConcepto = $derived(resultado === 'viable' || resultado === 'no_viable');

  /** «No viable» solo admite «No Viable (Rechazado)» (constraint del contrato): se elige solo. */
  function alCambiarResultado(): void {
    if (resultado === 'no_viable') conceptoViabilidad = CONCEPTO_NO_VIABLE;
  }
  const etiqueta = (ruta: string) => CAMPOS.find((c) => c.ruta === ruta)?.etiqueta ?? ruta;

  function cuerpo(): CuerpoDelContrato {
    const t = (v: string) => (v.trim() === '' ? null : v.trim());
    return { resultado, conceptoViabilidad: t(conceptoViabilidad), notaValidacion: t(notaValidacion), supuestos: t(supuestos) };
  }

  async function alEnviar(evento: SubmitEvent): Promise<void> {
    evento.preventDefault();
    if (!datos) return;
    const c = cuerpo();
    errores = erroresDePantalla(c);
    if (Object.keys(errores).length > 0) {
      document.getElementById(`campo-${Object.keys(errores)[0]}`)?.focus();
      return;
    }
    estado = 'enviando';
    fallo = null;
    try {
      await enviar(c);
      estado = 'enviado';
    } catch (e) {
      estado = 'error';
      fallo = e instanceof Error ? e.message : TEXTOS.errorGenerico;
    }
  }
</script>

<main class="tc-pagina" data-formulario="tarea" data-entradas={ENTRADAS.join(',')}>
  <Encabezado titulo={TEXTOS.titulo} etapa="Validación" hubspot={datos?.hubspot ?? null} caso={datos?.caso ?? null} />

  <div class="tc-rejilla">
    <PanelesContexto hubspot={datos?.hubspot ?? null} fallo={falloLectura} />

    <section class="tc-tarjeta" aria-labelledby="titulo-validacion">
      <h2 id="titulo-validacion">Validación de la solicitud</h2>
      {#if estado === 'enviado'}
        <div class="tc-aviso tc-aviso--exito" role="status">
          <strong>Validación enviada</strong>
          {OPCIONES.find((o) => o.valor === resultado)?.explica}
        </div>
      {:else}
        {#if estado === 'error'}
          <div class="tc-aviso tc-aviso--error" role="alert"><strong>{TEXTOS.error}</strong>{fallo}</div>
        {/if}
        {#if falloLectura}
          <p class="tc-aviso tc-aviso--info">{TEXTOS.sinDatosNoSeEnvia}</p>
        {/if}
        <form onsubmit={alEnviar} novalidate>
          <fieldset class="resultado" data-testid="campo-resultado" aria-describedby={errores.resultado ? 'error-resultado' : undefined}>
            <legend class="tc-leyenda">{etiqueta('resultado')}<span class="tc-requerido" aria-hidden="true">*</span></legend>
            <div class="opciones">
              {#each OPCIONES as o, i (o.valor)}
                <label class="opcion" data-valor={o.valor}>
                  <input
                    type="radio"
                    name="resultado"
                    value={o.valor}
                    id={i === 0 ? 'campo-resultado' : undefined}
                    bind:group={resultado}
                    onchange={alCambiarResultado}
                    required
                  />
                  <span class="icono" aria-hidden="true">{o.icono}</span>
                  <span class="texto"><strong>{o.titulo}</strong><span>{o.explica}</span></span>
                </label>
              {/each}
            </div>
            {#if errores.resultado}<p class="tc-error" id="error-resultado">{errores.resultado}</p>{/if}
          </fieldset>

          <div class="tc-campo" data-testid="campo-conceptoViabilidad">
            <label for="campo-conceptoViabilidad">
              {etiqueta('conceptoViabilidad')}{#if exigeConcepto}<span class="tc-requerido" aria-hidden="true">*</span>{/if}
            </label>
            <p class="tc-ayuda" id="ayuda-concepto">
              Obligatorio si la solicitud es viable o no viable («No viable» lleva «No Viable (Rechazado)»). Se escribe en
              el Negocio de HubSpot.
            </p>
            <select
              id="campo-conceptoViabilidad"
              class="tc-control"
              bind:value={conceptoViabilidad}
              aria-required={exigeConcepto}
              aria-invalid={!!errores.conceptoViabilidad}
              aria-describedby={errores.conceptoViabilidad ? 'ayuda-concepto error-concepto' : 'ayuda-concepto'}
            >
              <option value="">Elija un concepto…</option>
              {#each CONCEPTOS as c (c)}
                <option value={c}>{c}</option>
              {/each}
            </select>
            {#if errores.conceptoViabilidad}<p class="tc-error" id="error-concepto">{errores.conceptoViabilidad}</p>{/if}
          </div>

          <NotaRica
            id="campo-notaValidacion"
            testid="campo-notaValidacion"
            etiqueta={etiqueta('notaValidacion')}
            ayuda="Lo que el equipo necesita saber de esta validación. Admite **negrita** y listas."
            requerido
            bind:valor={notaValidacion}
            error={errores.notaValidacion}
          />

          <div class="tc-campo" data-testid="campo-supuestos">
            <label for="campo-supuestos">{etiqueta('supuestos')}</label>
            <p class="tc-ayuda" id="ayuda-supuestos">Opcional. Supuestos sobre los que se apoya la validación.</p>
            <textarea id="campo-supuestos" class="tc-control" rows="3" bind:value={supuestos} aria-describedby="ayuda-supuestos"></textarea>
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
  .resultado {
    border: 0;
    padding: 0;
    margin: 0 0 1.25rem;
  }
  .resultado legend {
    margin-block-end: 0.5rem;
  }
  .opciones {
    display: grid;
    gap: 0.6rem;
  }
  .opcion {
    display: flex;
    gap: 0.8rem;
    align-items: flex-start;
    border: 1.5px solid var(--tc-borde);
    border-radius: 12px;
    padding: 0.8rem 1rem;
    cursor: pointer;
    background: #fff;
    transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
  }
  .opcion:hover {
    border-color: #8a91ad;
  }
  .opcion:has(input:checked) {
    border-color: var(--tc-turquesa);
    background: var(--tc-turquesa-suave);
    box-shadow: 0 0 0 3px rgb(0 204 192 / 0.2);
  }
  .opcion:has(input:focus-visible) {
    outline: 3px solid var(--tc-marino);
    outline-offset: 2px;
  }
  .opcion input {
    margin-block-start: 0.35rem;
    accent-color: var(--tc-marino);
  }
  .icono {
    flex: none;
    inline-size: 2rem;
    block-size: 2rem;
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-weight: 700;
    color: #fff;
    background: var(--tc-marino);
  }
  .opcion[data-valor='bloqueado'] .icono {
    background: #8a5a00;
  }
  .opcion[data-valor='no_viable'] .icono {
    background: #a3221b;
  }
  .texto {
    display: grid;
    gap: 0.1rem;
  }
  .texto span {
    font-size: 0.85rem;
    color: var(--tc-texto-suave);
  }
</style>
