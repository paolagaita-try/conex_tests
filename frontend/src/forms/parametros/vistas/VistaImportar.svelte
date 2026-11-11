<script lang="ts">
  /**
   * Importar desde CSV (`p08-importar`): tres pasos —subir, revisar, confirmar— y nada se
   * aplica hasta confirmar con motivo. Vista PURA: devuelve el texto del fichero y el motivo; el contenedor
   * habla con el kit. Un fichero con errores NO se confirma (decisión pendiente: lo más conservador).
   */
  import Flecha from '../componentes/Flecha.svelte';
  import AreaTexto from '$lib/ui/AreaTexto.svelte';
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import type { VistaPreviaVM } from '../importar';
  import * as T from '../textos';
  import Chip from '../componentes/Chip.svelte';
  import '../estilos.css';

  interface Props {
    /** La vista previa del fichero subido, o `null` si todavía no hay fichero. */
    vista: VistaPreviaVM | null;
    nombreDelFichero: string;
    /** Resultado de confirmar: el lote aplicado, con o sin propuestas. */
    aplicada: { lote: string; conPropuestas: boolean } | null;
    /** El servidor dijo que lo importado cambió desde la vista previa. */
    cambioLaVista: boolean;
    error: string | null;
    subir: (fichero: File) => void;
    confirmar: (motivo: string) => Promise<void>;
    onvolver: () => void;
    oncambiar: () => void;
  }

  const props: Props = $props();
  let motivo = $state('');
  let errorMotivo = $state<string | null>(null);
  let ocupado = $state(false);

  const paso = $derived(props.aplicada ? 2 : props.vista ? 1 : 0);

  async function enviar(): Promise<void> {
    if (!props.vista?.confirmable) return;
    errorMotivo = null;
    if (motivo.trim() === '') {
      errorMotivo = T.ERROR_MOTIVO;
      return;
    }
    ocupado = true;
    try {
      await props.confirmar(motivo);
    } finally {
      ocupado = false;
    }
  }
</script>

<section class="panel" aria-labelledby="titulo-importar" data-testid="vista-importar">
  <header class="cabecera-panel">
    <div class="linea">
      <button type="button" class="volver" onclick={props.onvolver}><span aria-hidden="true"><Flecha direccion="izquierda" /></span> {T.VOLVER_A_TODOS}</button>
      <h2 id="titulo-importar">{T.IMPORTAR_TITULO}</h2>
    </div>
    <p class="subtitulo">{T.IMPORTAR_SUBTITULO}</p>
  </header>
  <div class="cuerpo-panel">
    <ol class="migas" aria-label={T.PASOS_ROTULO}>
      {#each T.PASOS as p, i (p)}
        <li><span aria-current={paso === i ? 'step' : undefined}>{p}</span></li>
      {/each}
    </ol>

    {#if props.error}<Aviso tono="error"><p role="alert">{props.error}</p></Aviso>{/if}
    {#if props.cambioLaVista}<Aviso tono="aviso" titulo={T.IMPORTACION_CAMBIO_TITULO}><p>{T.IMPORTACION_CAMBIO_CUERPO}</p></Aviso>{/if}

    {#if props.aplicada}
      <Aviso tono="exito" titulo={T.importacionAplicada(props.aplicada.lote)}>
        <p data-testid="importacion-aplicada">{props.aplicada.conPropuestas ? T.IMPORTACION_PROPUESTAS : T.GUARDADO}</p>
      </Aviso>
    {:else if !props.vista}
      <div class="campo-libre">
        <label for="fichero-csv">{T.ELEGIR_FICHERO}</label>
        <input
          id="fichero-csv"
          type="file"
          accept=".csv,text/csv"
          data-testid="fichero-csv"
          onchange={(e) => { const f = e.currentTarget.files?.[0]; if (f) props.subir(f); }}
        />
        <p class="ayuda">{T.FICHERO_AYUDA}</p>
      </div>
    {:else}
      <div class="ambito">
        <div class="linea"><span class="rotulo">Fichero</span><span class="codigo">{props.nombreDelFichero}</span></div>
        <button type="button" class="enlace" onclick={props.oncambiar}>{T.CAMBIAR_FICHERO}</button>
      </div>

      <div class="fichas" data-testid="resumen-de-importacion">
        <div class="ficha"><Chip tono="exito">{T.plural_altas(props.vista.altas)}</Chip><p>{T.CLASES_DE_IMPORTACION.ALTA[2]}</p></div>
        <div class="ficha"><Chip tono="marca">{T.plural_cambios(props.vista.cambios)}</Chip><p>{T.CLASES_DE_IMPORTACION.CAMBIO[2]}</p></div>
        <div class="ficha"><Chip tono="atencion">{T.plural_bajas(props.vista.bajas)}</Chip><p>{T.CLASES_DE_IMPORTACION.BAJA[2]}</p></div>
        <div class="ficha"><Chip tono="neutro">{T.plural_sin(props.vista.sinCambios)}</Chip><p>{T.CLASES_DE_IMPORTACION.SIN_CAMBIOS[2]}</p></div>
        {#if props.vista.propuestas > 0}
          <div class="ficha"><Chip tono="marca">{T.plural_propuestas(props.vista.propuestas)}</Chip><p>{T.CLASES_DE_IMPORTACION.PROPUESTA[2]}</p></div>
        {/if}
      </div>

      {#if props.vista.errores > 0}
        <Aviso tono="error" titulo={T.erroresTitulo(props.vista.errores)}>
          {#each props.vista.explicacionDeErrores as e, i (i)}<p>{e}</p>{/each}
          <p>{T.ERRORES_CUERPO}</p>
        </Aviso>
      {/if}

      <!-- svelte-ignore a11y_no_noninteractive_tabindex -->

      <div class="tabla-marco" role="region" tabindex="0" aria-label={T.TABLA_IMPORTACION}>
        <table class="tabla" data-testid="filas-de-importacion">
          <thead>
            <tr><th scope="col">{T.COLUMNA_QUE_PASA}</th><th scope="col">{T.COLUMNA_LISTA}</th><th scope="col">{T.COLUMNA_OPCION}</th><th scope="col">{T.COLUMNA_DETALLE}</th></tr>
          </thead>
          <tbody>
            {#each props.vista.filas as f (f.clave)}
              <tr class:inactiva={f.clase === 'ERROR'}>
                <td><Chip tono={f.tono}>{f.etiquetaDeClase}</Chip></td>
                <td>{f.lista}</td>
                <td>{f.opcion}</td>
                <td>{f.detalle}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if props.vista.confirmable}
        <form onsubmit={(e) => { e.preventDefault(); void enviar(); }}>
          <AreaTexto id="motivo-importacion" etiqueta={T.MOTIVO_DE_LA_IMPORTACION} bind:valor={motivo} error={errorMotivo} ayuda={T.MOTIVO_IMPORTACION_AYUDA} obligatorio />
          <div class="barra">
            <div class="acciones">
              <Boton tipo="submit" ocupado={ocupado} prueba="confirmar-importacion">{T.importarN(props.vista.aAplicar)}</Boton>
              <Boton variante="secundario" onclick={props.onvolver}>{T.CANCELAR}</Boton>
            </div>
          </div>
        </form>
      {:else if props.vista.errores === 0}
        <Aviso tono="informacion"><p>{T.NADA_QUE_IMPORTAR}</p></Aviso>
      {/if}
    {/if}
  </div>
</section>
