<script lang="ts">
  /**
   * El historial de una lista o de un parámetro (`p04`): su traza en lenguaje de negocio, con el periodo,
   * el estado de la cadena (solo si la persona puede verificarla) y la exportación a CSV.
   */
  import Boton from '$lib/ui/Boton.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import type { EventoVM, Periodo } from '../historial';
  import * as T from '../textos';
  import ErrorDeLectura from './ErrorDeLectura.svelte';
  import Chip from './Chip.svelte';
  import Eventos from './Eventos.svelte';

  interface Props {
    eventos: EventoVM[] | 'cargando' | 'error';
    periodo: Periodo;
    /** La cadena está verificada y es coherente (texto ya escrito: «Cadena coherente · verificada hoy 09:12»). */
    cadena: string | null;
    /** La verificación no se pudo completar, o encontró la cadena rota: no se calla ninguna de las dos. */
    cadenaFallo?: boolean;
    cadenaRota?: boolean;
    topeDeLectura?: boolean;
    onreintentar?: () => void;
    hayMas: boolean;
    onperiodo: (p: Periodo) => void;
    onmas: () => void;
    onexportar: () => void;
  }

  const { eventos, periodo, cadena, cadenaFallo = false, cadenaRota = false, topeDeLectura = false, onreintentar, hayMas, onperiodo, onmas, onexportar }: Props = $props();

  const PERIODOS: Array<[Periodo, string]> = [
    ['noventa', T.PERIODOS.noventa],
    ['anio', T.PERIODOS.anio],
    ['todo', T.PERIODOS.todo],
  ];
</script>

<div class="cabecera-seccion">
  <div class="segmentos" role="group" aria-label="Periodo">
    {#each PERIODOS as [clave, rotulo] (clave)}
      <button type="button" aria-pressed={periodo === clave} onclick={() => onperiodo(clave)}>{rotulo}</button>
    {/each}
  </div>
  <div class="acciones">
    {#if cadena}<Chip tono="exito">{cadena}</Chip>{/if}
    {#if cadenaRota}<Chip tono="error">{T.CADENA_NO_COHERENTE_CHIP}</Chip>{/if}
    {#if cadenaFallo}<Chip tono="atencion">{T.ERROR_CADENA}</Chip>{/if}
    <Boton variante="secundario" onclick={onexportar} prueba="exportar-historial">{T.EXPORTAR_CSV}</Boton>
  </div>
</div>

{#if eventos === 'error'}
  <ErrorDeLectura {onreintentar} prueba="historial-error" />
{:else if eventos === 'cargando'}
  <p role="status">{T.CARGANDO_HISTORIAL}</p>
{:else if eventos.length === 0 && hayMas}
  <!-- Con entradas más antiguas por leer, «no hay cambios» sería afirmar lo que no se sabe. -->
  <p role="status" data-testid="historial-sigue-buscando">{T.HISTORIAL_SIGUE_BUSCANDO}</p>
  <p class="acciones"><Boton variante="secundario" onclick={onmas} prueba="historial-mas">{T.VER_CAMBIOS_MAS_ANTIGUOS}</Boton></p>
{:else if eventos.length === 0 && topeDeLectura}
  <p role="status" data-testid="historial-tope">{T.HISTORIAL_TOPE}</p>
{:else if eventos.length === 0}
  <EstadoVacio titulo={T.HISTORIAL_VACIO_TITULO} detalle={T.HISTORIAL_VACIO_CUERPO} prueba="historial-vacio" />
{:else}
  <Eventos {eventos} />
  {#if hayMas}
    <p class="acciones"><Boton variante="secundario" onclick={onmas} prueba="historial-mas">{T.VER_MAS}</Boton></p>
  {/if}
{/if}
<p class="ayuda">{T.HISTORIAL_AYUDA} {T.HISTORIAL_RECHAZOS_AYUDA}</p>
