<script lang="ts">
  /**
   * Aprobaciones (`p06-aprobaciones`, `--propia`): los cambios de impacto alto que
   * esperan a quien los puede aprobar, los que propuso la propia persona y lo resuelto. Vista PURA.
   *
   * El doble control se ve, no solo se aplica: en un cambio propio «Aprobar y aplicar» va deshabilitado y
   * dice por qué, y solo se ofrece retirarlo. Rechazar pide comentario. Lo que el servidor decida
   * (`puedesAprobar`) es lo que la pantalla obedece; si la orden llega igualmente, el servidor la rechaza.
   */
  import Flecha from '../componentes/Flecha.svelte';
  import AreaTexto from '$lib/ui/AreaTexto.svelte';
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import { metaDe, type Aprobaciones, type PropuestaVM } from '../aprobaciones';
  import type { Resultado } from '../acciones';
  import type { UsosVM } from '../usos';
  import * as T from '../textos';
  import Chip from '../componentes/Chip.svelte';
  import '../estilos.css';

  interface Props {
    aprobaciones: Aprobaciones;
    /** La clave de la propuesta abierta a la derecha. */
    seleccionada: string | null;
    onseleccionar: (clave: string) => void;
    /** Dónde se usa lo que se decide: lo lee el contenedor del kit. `null` = no aplica (una delegación). */
    usosDe?: (definicion: string) => UsosVM | 'cargando' | 'error' | null;
    decidir: (d: { clave: string; decision: 'APROBAR' | 'RECHAZAR' | 'RETIRAR'; comentario: string }) => Promise<Resultado>;
  }

  const props: Props = $props();

  const todas = $derived([...props.aprobaciones.esperan, ...props.aprobaciones.propias, ...props.aprobaciones.resueltas]);
  const abierta = $derived<PropuestaVM | null>(todas.find((p) => p.clave === props.seleccionada) ?? todas[0] ?? null);

  let comentario = $state('');
  let errorComentario = $state<string | null>(null);
  let errorGeneral = $state<string | null>(null);
  let ocupado = $state(false);
  let aviso = $state<string | null>(null);

  // Cambiar de propuesta limpia lo escrito: el comentario es de ESA decisión.
  $effect(() => {
    void abierta?.clave;
    comentario = '';
    errorComentario = errorGeneral = null;
  });

  async function decidir(decision: 'APROBAR' | 'RECHAZAR' | 'RETIRAR'): Promise<void> {
    if (!abierta) return;
    errorComentario = errorGeneral = null;
    // EL ÚNICO punto por el que pasa toda decisión: rechazar sin comentario no llega a la API.
    if (decision === 'RECHAZAR' && comentario.trim() === '') {
      errorComentario = T.ERROR_COMENTARIO;
      return;
    }
    const esDelegacion = abierta.esDelegacion;
    ocupado = true;
    try {
      const r = await props.decidir({ clave: abierta.clave, decision, comentario });
      if (r.ok) {
        aviso = decision === 'APROBAR' ? T.APROBADO_Y_APLICADO : decision === 'RECHAZAR' ? (esDelegacion ? T.RECHAZADA_LA_DELEGACION : T.RECHAZADO_QUEDA_EN_LA_TRAZA) : T.PROPUESTA_RETIRADA;
        comentario = '';
      } else if (r.explicacion.campo === 'comentario') errorComentario = r.explicacion.mensaje;
      else errorGeneral = r.explicacion.mensaje;
    } finally {
      ocupado = false;
    }
  }

  const grupos = $derived([
    { id: 'esperan', titulo: T.ESPERAN_TU_APROBACION, filas: props.aprobaciones.esperan },
    { id: 'propias', titulo: T.PROPUESTOS_POR_TI, filas: props.aprobaciones.propias },
    { id: 'resueltas', titulo: T.RESUELTOS_RECIENTEMENTE, filas: props.aprobaciones.resueltas },
  ].filter((g) => g.filas.length > 0));
</script>

{#if aviso}
  <!-- La decisión tomada se confirma AQUÍ, no dentro del panel de otra propuesta: ese panel habla de la que está abierta. Se retira al elegir otra. -->
  <div data-testid="aviso-de-decision"><Aviso tono="exito"><p>{aviso}</p></Aviso></div>
{/if}
{#if todas.length === 0}
  <EstadoVacio titulo={T.NADA_PARA_APROBAR_TITULO} detalle={T.NADA_PARA_APROBAR_CUERPO} prueba="aprobaciones-vacio" />
{:else}
  <div class="lista-detalle" data-testid="vista-aprobaciones">
    <section aria-label={T.CAMBIOS_POR_APROBAR}>
      {#each grupos as g (g.id)}
        <h2 class="grupo">{g.titulo}</h2>
        <ul class="filas" data-testid="grupo-{g.id}">
          {#each g.filas as f (f.clave)}
            <li>
              <button type="button" class="fila" class:seleccionada={abierta?.clave === f.clave} aria-current={abierta?.clave === f.clave ? 'true' : undefined} onclick={() => { aviso = null; props.onseleccionar(f.clave); }}>
                <span class="texto"><span class="titulo">{f.nombre}</span><span class="meta">{metaDe(f)}</span></span>
                <span class="chevron" aria-hidden="true"><Flecha direccion="derecha" /></span>
              </button>
            </li>
          {/each}
        </ul>
      {/each}
    </section>

    {#if abierta}
      <section class="panel" aria-labelledby="titulo-aprobar" data-testid="detalle-de-aprobacion">
        <header class="cabecera-panel">
          <div class="linea">
            <h2 id="titulo-aprobar">{abierta.nombre}</h2>
            {#if abierta.impactoAlto}<Chip tono="atencion">{T.CHIP_IMPACTO_ALTO}</Chip>{/if}
            {#if abierta.estado !== 'PENDIENTE'}<Chip tono={abierta.estado === 'APROBADA' ? 'exito' : 'neutro'}>{T.estadoResuelto(abierta.estado)}</Chip>{/if}
          </div>
          <p class="subtitulo">{abierta.ambito}</p>
        </header>
        <div class="cuerpo-panel">
          {#if abierta.esDelegacion}
            <ul class="detalle-delegacion" data-testid="detalle-de-delegacion">
              {#each abierta.detalle as linea, i (i)}<li>{linea}</li>{/each}
            </ul>
          {:else}
            <p class="valor-grande">
              <span class="diff"><span class="antes">{abierta.antes}</span><span aria-hidden="true"><Flecha direccion="derecha" /></span><span class="despues">{abierta.despues}</span></span>
            </p>
          {/if}
          <div class="contexto">
            <dl>
              <div class="par"><dt>{T.PROPUESTO_POR}</dt><dd>{abierta.quien}</dd></div>
              <div class="par"><dt>{T.CUANDO}</dt><dd>{abierta.cuandoCompleto}</dd></div>
              {#if abierta.estado !== 'PENDIENTE' && abierta.resueltaPor}
                <div class="par"><dt>{T.estadoResuelto(abierta.estado)} por</dt><dd>{abierta.resueltaPor}</dd></div>
              {/if}
            </dl>
          </div>
          {#if !abierta.esDelegacion && abierta.definicion !== '' && props.usosDe}
            {@const usos = props.usosDe(abierta.definicion)}
            <div class="contexto" data-testid="usos-de-la-aprobacion">
              <h3>{T.DONDE_SE_USA_LO_QUE_DECIDES}</h3>
              {#if usos === 'cargando'}
                <p role="status">{T.CARGANDO}</p>
              {:else if usos === 'error'}
                <p role="alert" class="error-campo">{T.USOS_DE_LA_APROBACION_ERROR}</p>
              {:else if usos}
                {#if usos.lugares.length === 0}
                  <p>{T.USOS_NINGUN_LUGAR}</p>
                {:else}
                  <ul>{#each usos.lugares as l, i (i)}<li><strong>{l.titulo}</strong> · {l.tipo}</li>{/each}</ul>
                {/if}
                {#if usos.expedientes.length > 0 || usos.otros}
                  <p>{T.EXPEDIENTES_EN_CURSO_POR_OPCION}</p>
                  <ul data-testid="expedientes-en-curso">
                    {#each usos.expedientes as e, i (i)}<li><span class="opcion">{e.opcion}</span>: <span class="en-curso">{e.enCurso}</span></li>{/each}
                    {#if usos.otros}<li data-testid="usos-otros-aprobacion"><span class="opcion">{T.OTROS_FUERA_DE_LISTA}</span>: <span class="en-curso">{usos.otros.enCurso}</span></li>{/if}
                  </ul>
                {:else}
                  <p class="ayuda" data-testid="expedientes-afectados-sin-dato">{T.EXPEDIENTES_AFECTADOS_NO_INFORMADOS}</p>
                {/if}
              {/if}
            </div>
          {/if}
          <Aviso tono="informacion" titulo={T.MOTIVO_DE_QUIEN_PROPONE}><p>«{abierta.motivo}»</p></Aviso>
          {#if abierta.estado !== 'PENDIENTE' && abierta.comentario}
            <Aviso tono="informacion" titulo={T.TU_COMENTARIO.replace('Tu', 'El')}><p>«{abierta.comentario}»</p></Aviso>
          {/if}

          {#if errorGeneral}<p class="error-campo" role="alert">{errorGeneral}</p>{/if}

          {#if abierta.estado === 'PENDIENTE' && abierta.esPropia}
            <Aviso tono="informacion" titulo={T.LA_PROPUSISTE_TU_TITULO}><p>{T.LA_PROPUSISTE_TU_CUERPO}</p></Aviso>
            <div class="barra">
              <div class="acciones">
                <span class="boton-falso" role="button" aria-disabled="true" tabindex="-1" data-testid="aprobar-deshabilitado">{T.APROBAR_Y_APLICAR}</span>
                <button type="button" class="enlace grave" disabled={ocupado} onclick={() => void decidir('RETIRAR')} data-testid="retirar-propuesta">{T.RETIRAR_MI_PROPUESTA}</button>
              </div>
              <p class="ayuda">{T.NO_PUEDES_APROBAR_LO_TUYO}</p>
            </div>
          {:else if abierta.estado === 'PENDIENTE' && abierta.puedeAprobar}
            <AreaTexto
              id="comentario"
              etiqueta="{T.TU_COMENTARIO} {T.COMENTARIO_AYUDA}"
              bind:valor={comentario}
              error={errorComentario}
            />
            <div class="barra">
              <div class="acciones">
                <Boton ocupado={ocupado} onclick={() => void decidir('APROBAR')} prueba="aprobar">{T.APROBAR_Y_APLICAR}</Boton>
                <Boton variante="secundario" ocupado={ocupado} onclick={() => void decidir('RECHAZAR')} prueba="rechazar">{T.RECHAZAR}</Boton>
              </div>
              <p class="ayuda">{T.APROBAR_AYUDA}</p>
            </div>
          {/if}
        </div>
      </section>
    {/if}
  </div>
{/if}

<style>
  .boton-falso {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: var(--objetivo-min, 44px);
    padding: var(--esp-2, 0.5rem) var(--esp-5, 1.5rem);
    font-size: var(--texto-md, 1rem);
    font-weight: var(--peso-medio, 500);
    color: var(--color-texto-inverso, #fff);
    background: var(--color-primario, #6b21a8);
    border-radius: var(--radio-md, 8px);
    opacity: 0.55;
    cursor: not-allowed;
    box-sizing: border-box;
  }
  .detalle-delegacion {
    margin: 0;
    padding-inline-start: var(--esp-5, 1.5rem);
    font-size: var(--texto-lg, 1.125rem);
  }
</style>
