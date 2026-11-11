<script lang="ts">
  /**
   * Nueva delegación (`p07-permisos--delegar`): a quién (una persona, un grupo con o sin
   * subgrupos, un rol, o un rol dentro de un grupo), sobre qué (un proceso, entero o algunas actividades) y
   * hasta cuándo. Vista PURA: valida lo que falta y devuelve nombres; el contenedor los resuelve a
   * identificadores. Dice qué podrán y qué no podrán hacer antes de enviar.
   */
  import Flecha from '../componentes/Flecha.svelte';
  import AreaTexto from '$lib/ui/AreaTexto.svelte';
  import BuscadorServidor from '../componentes/BuscadorServidor.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import Calendario from '$lib/ui/Calendario.svelte';
  import Casilla from '$lib/ui/Casilla.svelte';
  import OpcionesEnFicha from '$lib/ui/OpcionesEnFicha.svelte';
  import Seleccion from '$lib/ui/Seleccion.svelte';
  import type { Resultado } from '../acciones';
  import * as T from '../textos';
  import '../estilos.css';

  export type TipoDeDestinatario = 'USUARIO' | 'GRUPO' | 'ROL' | 'GRUPO_ROL';

  export interface FormularioDeDelegacion {
    tipo: TipoDeDestinatario;
    usuario: string;
    grupo: string;
    rol: string;
    subgrupos: boolean;
    proceso: string;
    alcance: 'todo' | 'algunas';
    actividades: string[];
    vigencia: 'sin' | 'hasta';
    hasta: string;
    motivo: string;
  }

  interface Props {
    procesos: Array<{ valor: string; nombre: string; actividades: Array<{ valor: string; nombre: string }> }>;
    /** A quién se puede delegar: se BUSCA en el servidor mientras se escribe (devuelve etiquetas). */
    buscarPersonas: (q: string) => Promise<string[]>;
    buscarGrupos: (q: string) => Promise<string[]>;
    buscarRoles: (q: string) => Promise<string[]>;
    delegar: (f: FormularioDeDelegacion) => Promise<Resultado>;
    oncancelar: () => void;
  }

  const props: Props = $props();

  const TIPOS: TipoDeDestinatario[] = ['USUARIO', 'GRUPO', 'ROL', 'GRUPO_ROL'];

  let tipo = $state<TipoDeDestinatario>('GRUPO_ROL');
  let usuario = $state('');
  let grupo = $state('');
  let rol = $state('');
  let subgrupos = $state(false);
  let proceso = $state('');
  let alcance = $state<string | null>('todo');
  let marcadas = $state<Record<string, boolean>>({});
  let vigencia = $state<string | null>('sin');
  let hasta = $state('');
  let motivo = $state('');
  let errores = $state<Record<string, string>>({});
  let ocupado = $state(false);

  const procesoElegido = $derived(props.procesos.find((p) => p.valor === proceso) ?? props.procesos[0] ?? null);
  const usaGrupo = $derived(tipo === 'GRUPO' || tipo === 'GRUPO_ROL');
  const usaRol = $derived(tipo === 'ROL' || tipo === 'GRUPO_ROL');

  function validar(): FormularioDeDelegacion | null {
    const e: Record<string, string> = {};
    if (tipo === 'USUARIO' && usuario === '') e.usuario = T.ERROR_ELIGE_PERSONA;
    if (usaGrupo && grupo === '') e.grupo = T.ERROR_ELIGE_GRUPO;
    if (usaRol && rol === '') e.rol = T.ERROR_ELIGE_ROL;
    if (!procesoElegido) e.proceso = T.ERROR_ELIGE_PROCESO;
    const actividades = procesoElegido ? procesoElegido.actividades.filter((a) => marcadas[a.valor]).map((a) => a.valor) : [];
    if (alcance === 'algunas' && actividades.length === 0) e.actividades = T.ERROR_ELIGE_ACTIVIDAD;
    if (vigencia === 'hasta' && !/^\d{4}-\d{2}-\d{2}$/.test(hasta ?? '')) e.hasta = T.ERROR_ELIGE_FECHA;
    if (motivo.trim() === '') e.motivo = T.ERROR_MOTIVO;
    errores = e;
    if (Object.keys(e).length > 0 || !procesoElegido) return null;
    return {
      tipo,
      usuario,
      grupo,
      rol,
      subgrupos: usaGrupo && subgrupos,
      proceso: procesoElegido.valor,
      alcance: alcance === 'algunas' ? 'algunas' : 'todo',
      actividades: alcance === 'algunas' ? actividades : [],
      vigencia: vigencia === 'hasta' ? 'hasta' : 'sin',
      hasta,
      motivo,
    };
  }

  /** EL ÚNICO punto por el que pasa todo envío: valida y ejecuta. */
  async function enviar(): Promise<void> {
    const f = validar();
    if (!f) return;
    ocupado = true;
    try {
      const r = await props.delegar(f);
      if (!r.ok) errores = { [r.explicacion.campo === 'motivo' ? 'motivo' : 'general']: r.explicacion.mensaje };
    } finally {
      ocupado = false;
    }
  }
</script>

<section class="panel" aria-labelledby="titulo-delegar" data-testid="vista-nueva-delegacion">
  <header class="cabecera-panel">
    <div class="linea">
      <button type="button" class="volver" onclick={props.oncancelar}><span aria-hidden="true"><Flecha direccion="izquierda" /></span> {T.VOLVER_A_PERMISOS}</button>
      <h2 id="titulo-delegar">{T.NUEVA_DELEGACION}</h2>
    </div>
    <p class="subtitulo">{T.NUEVA_DELEGACION_SUBTITULO}</p>
  </header>
  <div class="dos-columnas">
    <form class="cuerpo-panel" aria-labelledby="titulo-delegar" onsubmit={(e) => { e.preventDefault(); void enviar(); }}>
      <fieldset>
        <legend>{T.LEYENDA_A_QUIEN}</legend>
        <div class="campo-libre">
          <span class="etiqueta">{T.TIPO_DESTINATARIO}</span>
          <div class="segmentos" role="group" aria-label={T.TIPO_DESTINATARIO}>
            {#each TIPOS as t (t)}
              <button type="button" aria-pressed={tipo === t} onclick={() => (tipo = t)}>{T.DESTINATARIOS[t]}</button>
            {/each}
          </div>
        </div>
        <div class="rejilla">
          {#if tipo === 'USUARIO'}
            <BuscadorServidor id="persona" etiqueta={T.CAMPO_PERSONA} bind:valor={usuario} buscar={props.buscarPersonas} error={errores.usuario ?? null} obligatorio />
          {/if}
          {#if usaGrupo}
            <BuscadorServidor id="grupo" etiqueta={T.CAMPO_GRUPO} bind:valor={grupo} buscar={props.buscarGrupos} error={errores.grupo ?? null} obligatorio />
          {/if}
          {#if usaRol}
            <BuscadorServidor id="rol" etiqueta={T.CAMPO_ROL} bind:valor={rol} buscar={props.buscarRoles} error={errores.rol ?? null} obligatorio />
          {/if}
        </div>
        {#if usaGrupo}
          <Casilla id="subgrupos" etiqueta={T.INCLUIR_SUBGRUPOS} bind:valor={subgrupos} />
        {/if}
      </fieldset>

      <fieldset>
        <legend>{T.LEYENDA_SOBRE_QUE}</legend>
        <Seleccion
          id="proceso"
          etiqueta={T.CAMPO_PROCESO}
          bind:valor={proceso}
          opciones={props.procesos.map((p) => ({ valor: p.valor, etiqueta: p.nombre }))}
          error={errores.proceso ?? null}
          obligatorio
          vacio={T.OPCION_VACIA}
        />
        <OpcionesEnFicha
          id="alcance"
          etiqueta={T.ALCANCE}
          bind:valor={alcance}
          opciones={[{ valor: 'todo', etiqueta: T.ALCANCE_TODO }, { valor: 'algunas', etiqueta: T.ALCANCE_ALGUNAS }]}
          disposicion="fila"
        />
        {#if alcance === 'algunas' && procesoElegido}
          <div class="rejilla" data-testid="actividades">
            {#each procesoElegido.actividades as a (a.valor)}
              <Casilla id="act-{a.valor}" etiqueta={a.nombre} bind:valor={marcadas[a.valor]} />
            {/each}
          </div>
          {#if errores.actividades}<p class="error-campo" role="alert">{errores.actividades}</p>{/if}
          <p class="ayuda">{T.ACTIVIDADES_AYUDA}</p>
        {/if}
      </fieldset>

      <fieldset>
        <legend>{T.LEYENDA_CUANTO_TIEMPO}</legend>
        <OpcionesEnFicha
          id="vigencia"
          etiqueta={T.VIGENCIA}
          bind:valor={vigencia}
          opciones={[{ valor: 'sin', etiqueta: T.VIGENCIA_SIN_FIN }, { valor: 'hasta', etiqueta: T.VIGENCIA_HASTA }]}
          disposicion="fila"
        />
        {#if vigencia === 'hasta'}
          <div class="espacio-arriba">
            <Calendario id="hasta" etiqueta={T.CAMPO_HASTA} bind:valor={hasta} error={errores.hasta ?? null} obligatorio />
          </div>
        {/if}
      </fieldset>

      <AreaTexto id="motivo" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} obligatorio />
      {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
      <div class="barra">
        <div class="acciones">
          <Boton tipo="submit" ocupado={ocupado} prueba="enviar-delegacion">{T.DELEGAR}</Boton>
          <Boton variante="secundario" onclick={props.oncancelar}>{T.CANCELAR}</Boton>
        </div>
        <p class="ayuda">{T.DELEGACION_LIMITE_UNA_SUPERADMIN}</p>
      </div>
    </form>

    <aside class="cuerpo-panel" aria-label="Qué podrá hacer">
      <div class="ficha">
        <h4>{T.QUE_PODRAN_HACER}</h4>
        <p>{T.QUE_PODRAN_HACER_1}</p>
        <p>{T.QUE_PODRAN_HACER_2}</p>
      </div>
      <div class="ficha">
        <h4>{T.QUE_NO_PODRAN_HACER}</h4>
        <p>{T.QUE_NO_PODRAN_HACER_1}</p>
        <p>{T.QUE_NO_PODRAN_HACER_2}</p>
      </div>
    </aside>
  </div>
</section>
