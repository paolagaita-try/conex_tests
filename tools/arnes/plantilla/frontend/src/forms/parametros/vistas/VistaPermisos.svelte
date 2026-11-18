<script lang="ts">
  /**
   * Permisos (`p07-permisos`): las delegaciones vigentes y las vencidas o revocadas, con
   * «Delegar», «Prorrogar» y «Revocar». Vista PURA: devuelve el MODELO de la delegación y el contenedor
   * recupera el dato crudo. Revocar y prorrogar pasan por el mismo punto —`confirmar()`— tras validar el
   * motivo: todo guardado pide motivo, venga la orden del botón que venga.
   */
  import { cerrarConEscape, enfocarAlMostrar } from '../componentes/enfocar';
  import AreaTexto from '$lib/ui/AreaTexto.svelte';
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import Calendario from '$lib/ui/Calendario.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import { recuentoDe } from '$lib/bonita/marcas';
  import { recuento } from '$lib/ui/formato';
  import type { Resultado } from '../acciones';
  import type { DelegacionVM } from '../permisos';
  import * as T from '../textos';
  import Chip from '../componentes/Chip.svelte';
  import '../estilos.css';

  interface Props {
    vigentes: DelegacionVM[];
    vencidas: DelegacionVM[];
    ondelegar: () => void;
    revocar: (d: DelegacionVM, motivo: string) => Promise<Resultado>;
    prorrogar: (d: DelegacionVM, hasta: string, motivo: string) => Promise<Resultado>;
  }

  const props: Props = $props();

  let ver = $state<'vigentes' | 'vencidas'>('vigentes');
  let elegida = $state<DelegacionVM | null>(null);
  let accion = $state<'revocar' | 'prorrogar' | null>(null);
  let hasta = $state('');
  let motivo = $state('');
  let errores = $state<{ motivo?: string; hasta?: string; general?: string }>({});
  let ocupado = $state(false);
  let aviso = $state<string | null>(null);

  const cuantasVigentes = $derived(recuentoDe(props.vigentes));
  const cuantasVencidas = $derived(recuentoDe(props.vencidas));
  const lista = $derived(ver === 'vigentes' ? props.vigentes : props.vencidas);

  function abrir(d: DelegacionVM, a: 'revocar' | 'prorrogar'): void {
    elegida = d;
    accion = a;
    motivo = '';
    hasta = '';
    errores = {};
  }
  function cerrar(): void {
    elegida = null;
    accion = null;
    errores = {};
  }

  /** EL ÚNICO punto por el que pasa todo guardado: valida y ejecuta. */
  async function confirmar(): Promise<void> {
    if (!elegida || !accion) return;
    errores = {};
    if (accion === 'prorrogar' && !/^\d{4}-\d{2}-\d{2}$/.test(hasta ?? '')) errores.hasta = T.ERROR_ELIGE_FECHA;
    if (motivo.trim() === '') errores.motivo = T.ERROR_MOTIVO;
    if (errores.hasta || errores.motivo) return;
    ocupado = true;
    try {
      const r = accion === 'revocar' ? await props.revocar(elegida, motivo) : await props.prorrogar(elegida, hasta, motivo);
      if (r.ok) {
        aviso = accion === 'revocar' ? T.REVOCADA : T.PRORROGA_ENVIADA;
        cerrar();
      } else errores = { [r.explicacion.campo === 'motivo' ? 'motivo' : 'general']: r.explicacion.mensaje };
    } finally {
      ocupado = false;
    }
  }
</script>

<div class="cuerpo-panel" data-testid="vista-permisos">
  <div class="cabecera-seccion">
    <div class="segmentos" role="group" aria-label="Qué delegaciones mostrar">
      <button type="button" aria-pressed={ver === 'vigentes'} onclick={() => (ver = 'vigentes')}>{T.PERMISOS_VIGENTES} · {recuento(cuantasVigentes)}</button>
      <button type="button" aria-pressed={ver === 'vencidas'} onclick={() => (ver = 'vencidas')}>{T.PERMISOS_VENCIDAS} · {recuento(cuantasVencidas)}</button>
    </div>
    <Boton onclick={props.ondelegar} prueba="delegar">{T.DELEGAR}</Boton>
  </div>

  <Aviso tono="informacion" titulo={T.SUPERADMIN_PUEDE_TODO_TITULO}><p>{T.SUPERADMIN_PUEDE_TODO_CUERPO}</p></Aviso>
  {#if aviso}<Aviso tono="exito"><p>{aviso}</p></Aviso>{/if}

  {#if lista.length === 0}
    <EstadoVacio titulo={ver === 'vigentes' ? T.SIN_DELEGACIONES_TITULO : T.SIN_VENCIDAS_TITULO} detalle={ver === 'vigentes' ? T.SIN_DELEGACIONES_CUERPO : undefined} prueba="permisos-vacio" />
  {:else}
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="tabla-marco" role="region" tabindex="0" aria-label={T.TABLA_DELEGACIONES}>
      <table class="tabla" data-testid="tabla-de-permisos">
        <thead>
          <tr>
            <th scope="col">{T.COLUMNA_A_QUIEN}</th>
            <th scope="col">{T.COLUMNA_SOBRE_QUE}</th>
            <th scope="col">{T.COLUMNA_VIGENCIA}</th>
            <th scope="col" class="ocultable">{T.COLUMNA_OTORGADA_POR}</th>
            <th scope="col"><span class="solo-lectores">{T.COLUMNA_ACCIONES}</span></th>
          </tr>
        </thead>
        <tbody>
          {#each lista as d (d)}
            <tr data-testid="delegacion">
              <td>
                <Chip tono="neutro">{d.tipo}</Chip> {d.quien}
                {#if d.conSubgrupos}<br /><span class="ayuda">{T.INCLUYE_SUBGRUPOS}</span>{/if}
              </td>
              <td>{d.sobreQue}</td>
              <td>{d.vigencia}{#if d.venceManana}{' '}<Chip tono="atencion">{T.VENCE_MANANA}</Chip>{/if}</td>
              <td class="ocultable">{d.otorgadaPor}</td>
              <td class="acciones-fila">
                {#if d.vigente}
                  {#if d.puedeProrrogar}<button type="button" class="enlace" onclick={() => abrir(d, 'prorrogar')}>{T.PRORROGAR}</button>{/if}
                  <button type="button" class="enlace grave" onclick={() => abrir(d, 'revocar')}>{T.REVOCAR}</button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
  <p class="ayuda">{T.REVOCAR_TIENE_EFECTO_INMEDIATO}</p>
  <p class="ayuda">{T.LIMITE_DE_LA_ORGANIZACION}</p>

  {#if elegida && accion}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <form
      class="confirmacion {accion === 'prorrogar' ? 'decision' : ''}"
      aria-labelledby="titulo-permiso"
      data-testid="confirmacion-permiso" use:enfocarAlMostrar onkeydown={cerrarConEscape(cerrar)}
      onsubmit={(e) => { e.preventDefault(); void confirmar(); }}
    >
      <h3 id="titulo-permiso">{accion === 'revocar' ? T.revocarTitulo(elegida.quien) : T.prorrogarTitulo(elegida.quien)}</h3>
      <p>{accion === 'revocar' ? T.REVOCAR_CUERPO : T.PRORROGAR_CUERPO}</p>
      {#if accion === 'prorrogar'}
        <Calendario id="nueva-fecha" etiqueta={T.NUEVA_FECHA} bind:valor={hasta} error={errores.hasta ?? null} obligatorio />
      {/if}
      <AreaTexto id="motivo-permiso" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} obligatorio />
      {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
      <div class="acciones">
        <Boton tipo="submit" variante={accion === 'revocar' ? 'peligro' : 'primario'} ocupado={ocupado} prueba="confirmar-permiso">{accion === 'revocar' ? T.REVOCAR_ACCION : T.PRORROGAR_ACCION}</Boton>
        <Boton variante="secundario" onclick={cerrar}>{T.CANCELAR}</Boton>
      </div>
    </form>
  {/if}
</div>
