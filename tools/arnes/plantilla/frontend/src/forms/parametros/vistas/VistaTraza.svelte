<script lang="ts">
  /**
   * Traza (`p09-traza`): consultar, filtrar, verificar la cadena y exportar. Solo lectura:
   * no hay ningún control que edite o borre una entrada. Quien no es de la superadministración consulta y
   * exporta, pero no verifica (decisión pendiente: lo más conservador).
   */
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import { recuentoDe } from '$lib/bonita/marcas';
  import type { EventoVM } from '../historial';
  import { filtrar, type FiltrosDeLaVista, type ResultadoDeVerificacion } from '../traza';
  import * as T from '../textos';
  import ErrorDeLectura from '../componentes/ErrorDeLectura.svelte';
  import BuscadorServidor from '../componentes/BuscadorServidor.svelte';
  import Eventos from '../componentes/Eventos.svelte';
  import '../estilos.css';

  interface Props {
    eventos: EventoVM[] | 'cargando' | 'error';
    puedeVerificar: boolean;
    verificacion: ResultadoDeVerificacion | 'verificando' | 'error' | null;
    hayMasFallo?: boolean;
    onreintentar?: () => void;
    hayMas: boolean;
    /** El servidor tiene entradas más antiguas que las leídas (aunque ya no se pidan). */
    quedaMas?: boolean;
    /** Buscar personas en el servidor (la organización puede tener más de 20). */
    buscarPersonas: (q: string) => Promise<string[]>;
    /** Qué dice exactamente el CSV exportado cuando no es todo lo filtrado. */
    avisoDeExportacion?: string | null;
    filtros: FiltrosDeLaVista;
    onfiltros: (f: FiltrosDeLaVista) => void;
    onverificar: () => void;
    onmas: () => void;
    onexportar: (visibles: EventoVM[]) => void;
  }
  const props: Props = $props();

  const visibles = $derived(props.eventos === 'cargando' || props.eventos === 'error' ? [] : filtrar(props.eventos, props.filtros));
  const cuantas = $derived(recuentoDe(visibles));
  const ACCIONES: Array<[FiltrosDeLaVista['accion'], string]> = [
    ['todas', T.ACCIONES_DE_TRAZA.todas],
    ['cambios', T.ACCIONES_DE_TRAZA.cambios],
    ['aprobaciones', T.ACCIONES_DE_TRAZA.aprobaciones],
    ['permisos', T.ACCIONES_DE_TRAZA.permisos],
    ['importaciones', T.ACCIONES_DE_TRAZA.importaciones],
  ];

  const poner = (parcial: Partial<FiltrosDeLaVista>) => props.onfiltros({ ...props.filtros, ...parcial });
</script>

<div class="cuerpo-panel" data-testid="vista-traza">
  {#if props.verificacion === 'verificando'}
    <p role="status">{T.VERIFICANDO}</p>
  {:else if props.verificacion === 'error'}
    <Aviso tono="error" titulo={T.ERROR_VERIFICAR}><p data-testid="verificacion-error">{T.ERROR_CADENA}</p></Aviso>
  {:else if props.verificacion}
    <Aviso tono={props.verificacion.coherente ? 'exito' : 'error'} titulo={props.verificacion.titulo}>
      <p data-testid="resultado-de-verificacion">{props.verificacion.cuerpo} {props.verificacion.limites}</p>
    </Aviso>
  {/if}

  <form class="rejilla" aria-label={T.FILTRAR_LA_TRAZA} onsubmit={(e) => e.preventDefault()}>
    <div class="campo-libre">
      <BuscadorServidor id="f-persona" etiqueta={T.FILTRO_PERSONA} valor={props.filtros.persona} buscar={props.buscarPersonas} onelegir={(v) => poner({ persona: v })} />
      {#if props.filtros.persona !== ''}<button type="button" class="enlace" onclick={() => poner({ persona: '' })}>{T.TODAS_LAS_PERSONAS}</button>{/if}
    </div>
    <div class="campo-libre">
      <label for="f-que">{T.FILTRO_QUE}</label>
      <input id="f-que" class="control" placeholder={T.CUALQUIERA} value={props.filtros.lista} oninput={(e) => poner({ lista: e.currentTarget.value })} />
    </div>
    <div class="campo-libre">
      <label for="f-accion">{T.FILTRO_ACCION}</label>
      <select id="f-accion" class="control" value={props.filtros.accion} onchange={(e) => poner({ accion: e.currentTarget.value as FiltrosDeLaVista['accion'] })}>
        {#each ACCIONES as [clave, rotulo] (clave)}<option value={clave}>{rotulo}</option>{/each}
      </select>
    </div>
    <div class="campo-libre">
      <label for="f-desde">{T.FILTRO_DESDE}</label>
      <input id="f-desde" class="control" type="date" value={props.filtros.desde} onchange={(e) => poner({ desde: e.currentTarget.value })} />
    </div>
    <div class="campo-libre">
      <label for="f-hasta">{T.FILTRO_HASTA}</label>
      <input id="f-hasta" class="control" type="date" value={props.filtros.hasta} onchange={(e) => poner({ hasta: e.currentTarget.value })} />
    </div>
  </form>

  <div class="cabecera-seccion">
    <h3>{props.hayMas || props.quedaMas ? T.entradasCargadas(cuantas) : T.entradasTitulo(cuantas)}</h3>
    <div class="acciones">
      {#if props.puedeVerificar}<Boton variante="secundario" onclick={props.onverificar} prueba="verificar">{T.VERIFICAR_LA_CADENA}</Boton>{/if}
      <Boton variante="secundario" onclick={() => props.onexportar(visibles)} prueba="exportar-traza">{T.EXPORTAR_CSV}</Boton>
    </div>
  </div>

  {#if props.eventos === 'error'}
    <ErrorDeLectura onreintentar={props.onreintentar} prueba="traza-error" />
  {:else if props.eventos === 'cargando'}
    <p role="status">{T.CARGANDO_HISTORIAL}</p>
  {:else if visibles.length === 0 && props.hayMas}
    <!-- Con entradas más antiguas por leer, «ninguna» sería afirmar lo que no se sabe. -->
    <p role="status" data-testid="traza-buscando">{T.TRAZA_SIGUE_BUSCANDO}</p>
    <p class="acciones"><Boton variante="secundario" onclick={props.onmas} prueba="traza-mas">{T.VER_ENTRADAS_MAS_ANTIGUAS}</Boton></p>
  {:else if visibles.length === 0 && props.quedaMas}
    <p role="status" data-testid="traza-tope">{T.TRAZA_TOPE}</p>
  {:else if visibles.length === 0}
    <EstadoVacio titulo={T.TRAZA_VACIA_TITULO} detalle={T.TRAZA_VACIA_CUERPO} prueba="traza-vacia" />
  {:else}
    <Eventos eventos={visibles} />
    {#if props.hayMasFallo}<ErrorDeLectura onreintentar={props.onmas} prueba="traza-mas-error" />{/if}
    {#if props.hayMas}<p class="acciones"><Boton variante="secundario" onclick={props.onmas} prueba="traza-mas">{T.VER_MAS}</Boton></p>{/if}
  {/if}
  {#if props.avisoDeExportacion}<Aviso tono="aviso"><p data-testid="aviso-de-exportacion">{props.avisoDeExportacion}</p></Aviso>{/if}
  <p class="ayuda">{T.TRAZA_AYUDA}</p>
  <p class="ayuda">{T.LO_QUE_DETECTA}</p>
  <p class="ayuda" data-testid="traza-sin-rechazados">{T.HISTORIAL_RECHAZOS_AYUDA}</p>
</div>
