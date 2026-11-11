<script lang="ts">
  /**
   * «Dónde se usa» (`p03`): fichas de los formularios, documentos y reglas que leen la lista, y la tabla
   * de expedientes por opción. Si el módulo todavía no sirve los usos, lo dice —no pinta un vacío que
   * parezca «nadie la usa»—: un dato que falta no es un cero.
   */
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import type { UsosVM } from '../usos';
  import * as T from '../textos';
  import ErrorDeLectura from './ErrorDeLectura.svelte';
  import Chip from './Chip.svelte';

  interface Props {
    usos: UsosVM | null | 'cargando' | 'error';
    onreintentar?: () => void;
  }

  const { usos, onreintentar }: Props = $props();
</script>

{#if usos === 'cargando'}
  <p role="status">{T.CARGANDO}</p>
{:else if usos === 'error'}
  <ErrorDeLectura {onreintentar} prueba="usos-error" />
{:else if usos === null}
  <EstadoVacio titulo={T.USOS_NO_DISPONIBLE_TITULO} detalle={T.USOS_NO_DISPONIBLE_CUERPO} prueba="usos-no-disponible" />
{:else if usos.lugares.length === 0 && usos.expedientes.length === 0 && !usos.otros}
  <EstadoVacio titulo={T.USOS_VACIO_TITULO} detalle={T.USOS_VACIO_CUERPO} prueba="usos-vacio" />
{:else}
  <div class="fichas" data-testid="usos-lugares">
    {#each usos.lugares as l (l.clave)}
      <div class="ficha">
        <Chip tono={l.tipo === T.TIPO_DE_USO.FORMULARIO ? 'marca' : 'neutro'}>{l.tipo}</Chip>
        <h4>{l.titulo}</h4>
        <p>{l.detalle}</p>
      </div>
    {/each}
  </div>
  {#if usos.expedientes.length > 0 || usos.otros}
    <div class="cabecera-seccion"><h3>{T.EXPEDIENTES_QUE_LA_USAN}</h3></div>
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div class="tabla-marco" role="region" tabindex="0" aria-label={T.TABLA_USOS}>
      <table class="tabla" data-testid="usos-expedientes">
        <thead>
          <tr>
            <th scope="col">{T.COLUMNA_OPCION}</th>
            <th scope="col" class="num">{T.COLUMNA_GUARDADOS}</th>
            <th scope="col" class="num">{T.COLUMNA_EN_CURSO}</th>
          </tr>
        </thead>
        <tbody>
          {#each usos.expedientes as e (e.clave)}
            <tr class:inactiva={e.inactiva}>
              <!-- Se pinta la etiqueta; el código completo (hasta 255 caracteres) queda en el título, no en la fila. -->
              <td title={e.codigo === '' ? undefined : e.codigo}>{e.opcion}{#if e.inactiva}{' '}<Chip tono="neutro">{T.CHIP_INACTIVA}</Chip>{/if}{#if e.fuera}{' '}<Chip tono="neutro">{T.CHIP_FUERA_DE_LISTA}</Chip>{/if}</td>
              <td class="num">{e.guardados}</td>
              <td class="num">{e.enCurso}</td>
            </tr>
          {/each}
          {#if usos.otros}
            <tr data-testid="usos-otros">
              <td>{T.OTROS_FUERA_DE_LISTA}</td>
              <td class="num">{usos.otros.guardados}</td>
              <td class="num">{usos.otros.enCurso}</td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  {/if}
  <p class="ayuda">{T.USOS_AYUDA}</p>
{/if}
