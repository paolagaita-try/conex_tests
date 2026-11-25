<script lang="ts">
  /**
   * El inicio (`p01`, `p01--sin-resultados`, `p10`, `p11`): lo que cada perfil puede ajustar, agrupado
   * por ámbito y con buscador. Vista PURA: recibe el modelo ya construido (`construirInicio`) y devuelve
   * eventos. La misma pinta la aplicación real y la galería viva.
   */
  import Boton from '$lib/ui/Boton.svelte';
  import Aviso from '$lib/ui/Aviso.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import { fechaLegible } from '../formatos';
  import type { Capacidades } from '../capacidades';
  import type { FiltroDeTipo, FilaDeInicio, Inicio } from '../inicio';
  import { nombreDeActividad, nombreDeProceso } from '../nombres';
  import * as T from '../textos';
  import Buscador from '../componentes/Buscador.svelte';
  import FilaDeParametro, { type ChipDeFila } from '../componentes/FilaDeParametro.svelte';
  import '../estilos.css';

  interface Props {
    inicio: Inicio;
    capacidades: Capacidades;
    filtro: FiltroDeTipo;
    busqueda: string;
    onfiltro: (f: FiltroDeTipo) => void;
    onbusqueda: (q: string) => void;
    onabrir: (clave: string) => void;
    onimportar: () => void;
    onexportar: () => void;
  }

  const { inicio, capacidades, filtro, busqueda, onfiltro, onbusqueda, onabrir, onimportar, onexportar }: Props = $props();

  const esSuper = $derived(capacidades.perfil === 'superadministracion');
  const esDelegado = $derived(capacidades.perfil === 'delegado');
  const esConsulta = $derived(capacidades.perfil === 'consulta');

  const SEGMENTOS_DE_SUPERADMINISTRACION: Array<[FiltroDeTipo, string]> = [
    ['todo', T.SEGMENTOS_DE_SUPERADMINISTRACION.todo],
    ['listas', T.SEGMENTOS_DE_SUPERADMINISTRACION.listas],
    ['parametros', T.SEGMENTOS_DE_SUPERADMINISTRACION.parametros],
  ];
  const SEGMENTOS_DEL_DELEGADO: Array<[FiltroDeTipo, string]> = [
    ['editable', T.SEGMENTOS_DEL_DELEGADO.editable],
    ['todo', T.SEGMENTOS_DEL_DELEGADO.todo],
  ];
  const segmentos = $derived(esSuper ? SEGMENTOS_DE_SUPERADMINISTRACION : esDelegado ? SEGMENTOS_DEL_DELEGADO : []);

  const hayBusqueda = $derived(busqueda.trim() !== '');
  const sinResultados = $derived(inicio.visibles === 0 && (hayBusqueda || filtro !== 'todo') && inicio.total > 0);

  function metaDe(f: FilaDeInicio): string {
    const partes = [f.tipo, f.contenido];
    if (f.dependientes) partes.push(T.deEllaDependen(f.dependientes));
    else if (f.ultimo) partes.push(f.ultimo);
    return partes.join(' · ');
  }

  function chipsDe(f: FilaDeInicio): ChipDeFila[] {
    const chips: ChipDeFila[] = [];
    if (f.impactoAlto) chips.push({ tono: 'atencion', texto: T.CHIP_IMPACTO_ALTO });
    if (f.porAprobar) chips.push({ tono: 'marca', texto: esSuper ? T.CHIP_POR_APROBAR_SUPERADMINISTRACION : T.CHIP_POR_APROBAR });
    if (f.conVersionPropia > 0) chips.push({ tono: 'neutro', texto: T.versionPropiaEn(f.conVersionPropia) });
    if (esDelegado && f.soloLectura) chips.push({ tono: 'neutro', texto: T.CHIP_SOLO_LECTURA });
    return chips;
  }

  /** Lo que se escribe de un permiso del delegado: proceso, actividades y vigencia, sin códigos. */
  function alcanceDe(p: Capacidades['permisos'][number]): { proceso: string; resto: string } {
    const donde = p.actividades.length === 0 ? T.TODAS_SUS_ACTIVIDADES : T.soloEn(p.actividades.map(nombreDeActividad).join(', '));
    const hasta = p.vigenteHasta === null ? T.SIN_FECHA_DE_FIN : T.hastaEl(fechaLegible(p.vigenteHasta.slice(0, 10)));
    return { proceso: nombreDeProceso(p.proceso), resto: `, ${donde}, ${hasta}.` };
  }
</script>

<div class="cuerpo-panel">
  <div class="barra-busqueda">
    <Buscador id="buscar" etiqueta={T.BUSCAR_ROTULO} pista={T.BUSCAR_PISTA} valor={busqueda} onescribir={onbusqueda} />
    {#if segmentos.length > 0}
      <div class="segmentos" role="group" aria-label={T.QUE_MOSTRAR}>
        {#each segmentos as [clave, rotulo] (clave)}
          <button type="button" aria-pressed={filtro === clave} onclick={() => onfiltro(clave)}>{rotulo}</button>
        {/each}
      </div>
    {/if}
    <div class="acciones">
      {#if esSuper}
        <Boton variante="secundario" onclick={onimportar} prueba="importar">{T.IMPORTAR_CSV}</Boton>
      {/if}
      <Boton variante="secundario" onclick={onexportar} prueba="exportar">{T.EXPORTAR}</Boton>
    </div>
  </div>

  {#if esDelegado && capacidades.permisos.length > 0}
    <Aviso tono="informacion" titulo={T.TUS_PERMISOS}>
      {#each capacidades.permisos as p, i (i)}
        {@const a = alcanceDe(p)}
        <p>{T.PUEDES_EDITAR} <strong>{a.proceso}</strong>{a.resto}</p>
      {/each}
      <p>{T.TUS_PERMISOS_COLA}</p>
    </Aviso>
  {/if}
  {#if esConsulta}
    <Aviso tono="informacion" titulo={T.MODO_CONSULTA_TITULO}>
      <p>{T.MODO_CONSULTA_CUERPO}</p>
    </Aviso>
  {/if}

  {#if sinResultados}
    <EstadoVacio titulo={T.sinResultadosTitulo(busqueda.trim())} detalle={T.SIN_RESULTADOS_CUERPO} prueba="sin-resultados">
      <Boton variante="secundario" onclick={() => { onbusqueda(''); onfiltro('todo'); }}>{T.VER_TODOS}</Boton>
    </EstadoVacio>
  {:else}
    {#each inicio.grupos as g (g.clave)}
      <section aria-label={g.titulo}>
        <h2 class="grupo">{g.titulo}</h2>
        {#if g.sinParametros}
          <EstadoVacio titulo={T.PROCESO_SIN_PARAMETROS_TITULO} detalle={T.PROCESO_SIN_PARAMETROS_CUERPO} prueba="proceso-sin-parametros" />
        {:else}
          <ul class="filas">
            {#each g.filas as f (f.clave)}
              <li>
                <FilaDeParametro
                  titulo={f.nombre}
                  meta={metaDe(f)}
                  chips={chipsDe(f)}
                  soloLectura={f.soloLectura}
                  rotuloVer={T.VER}
                  onabrir={() => onabrir(f.clave)}
                  prueba="fila-{f.codigo}"
                />
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {/each}
  {/if}
</div>
