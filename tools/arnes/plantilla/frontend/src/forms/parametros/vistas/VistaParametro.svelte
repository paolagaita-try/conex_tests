<script lang="ts">
  /**
   * Un parámetro en un ámbito (`p05-parametro`, `--confirmar`, `--pendiente`, `--conflicto`). Vista
   * PURA: recibe el modelo (`construirParametro`) y devuelve eventos; lo que escribe lo decide el contenedor.
   *
   * Dos reglas de diseño a la vista de todos:
   *  - **la confirmación cuelga del RESULTADO**: un cambio de impacto alto se REVISA antes de enviarse (se
   *    enseña su efecto y el aviso del doble control); uno de impacto normal se guarda sin diálogo. La
   *    gravedad la decide la definición, no el botón por el que se pida;
   *  - **todo guardado pide motivo**: sin él, el campo lo dice y no se llama a nada.
   */
  import { cerrarConEscape, enfocarAlMostrar } from '../componentes/enfocar';
  import Flecha from '../componentes/Flecha.svelte';
  import { untrack } from 'svelte';
  import AreaTexto from '$lib/ui/AreaTexto.svelte';
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import Pestanas, { type Pestana } from '$lib/ui/Pestanas.svelte';
  import type { Ambito } from '../ambitos';
  import type { Resultado } from '../acciones';
  import type { EventoVM, Periodo } from '../historial';
  import type { ParametroVM } from '../parametro';
  import type { PestanaDeDefinicion } from '../ruta';
  import * as T from '../textos';
  import type { UsosVM } from '../usos';
  import type { ValidacionDeValor } from '../valores';
  import CampoDeValor from '../componentes/CampoDeValor.svelte';
  import Chip from '../componentes/Chip.svelte';
  import ErrorDeLectura from '../componentes/ErrorDeLectura.svelte';
  import PanelDeHistorial from '../componentes/PanelDeHistorial.svelte';
  import PanelDeUsos from '../componentes/PanelDeUsos.svelte';
  import '../estilos.css';

  /** Otra persona propuso antes sobre el mismo parámetro (p05--conflicto). */
  export interface ConflictoVM {
    quien: string;
    cuando: string;
    antes: string;
    propuesto: string;
  }

  interface Props {
    parametro: ParametroVM;
    pestana: PestanaDeDefinicion;
    usos: UsosVM | null | 'cargando' | 'error';
    onreintentarUsos?: () => void;
    editoresFallo?: boolean;
    onreintentarEditores?: () => void;
    cadenaFallo?: boolean;
    /** Se leyeron todas las páginas que la API sirve y puede haber cambios más antiguos. */
    topeDeLectura?: boolean;
    cadenaRota?: boolean;
    onreintentarHistorial?: () => void;
    eventos: EventoVM[] | 'cargando' | 'error';
    periodo: Periodo;
    cadena: string | null;
    hayMasHistorial: boolean;
    ultimaModificacion: string;
    conflicto: ConflictoVM | null;
    onpestana: (p: PestanaDeDefinicion) => void;
    onvolver: () => void;
    onambito: (a: Ambito) => void;
    onpadre: (codigo: string) => void;
    onperiodo: (p: Periodo) => void;
    onmasHistorial: () => void;
    onexportarHistorial: () => void;
    onaprobaciones: () => void;
    onverPermisos?: (() => void) | null;
    oncargarActual: () => void;
    /** Valida lo tecleado contra la definición (rango, decimales): la vista no conoce la definición. */
    validar: (valor: string) => ValidacionDeValor;
    guardar: (d: { valor: string; motivo: string }) => Promise<Resultado>;
    retirar: () => Promise<Resultado>;
  }

  const props: Props = $props();
  const p = $derived(props.parametro);

  let valor = $state(untrack(() => props.parametro.paraEditar));
  let motivo = $state('');
  let errorValor = $state<string | null>(null);
  let errorMotivo = $state<string | null>(null);
  let errorGeneral = $state<string | null>(null);
  let revisando = $state(false);
  let ocupado = $state(false);
  let aviso = $state<{ tono: 'exito' | 'informacion'; texto: string } | null>(null);

  // Si lo que rige cambia (se aplicó un cambio, se eligió otra modalidad), el campo vuelve a lo vigente.
  const vigente = $derived(p.paraEditar);
  const padreSeleccionado = $derived(p.padreElegido);
  $effect(() => {
    // Solo si CAMBIA lo vigente o la modalidad elegida (cadenas iguales no vuelven a disparar el efecto).
    const nuevo = vigente;
    void padreSeleccionado;
    untrack(() => {
      valor = nuevo;
      motivo = '';
      revisando = false;
      errorValor = errorMotivo = errorGeneral = null;
    });
  });

  const etiquetaDelCampo = $derived(
    T.campoValor(p.nombre, p.migas.at(-1)?.rotulo ?? '') + (p.padres && p.etiquetaDelPadre ? ` · ${p.etiquetaDelPadre}` : ''),
  );
  const bloqueado = $derived(!p.puedeEditar || p.pendiente !== null);
  /** Lo que se va a proponer, con su unidad, tal como lo leerá quien apruebe. */
  const valorEnPantalla = (v: string): string => (p.prefijo ? [p.prefijo, v].join('') : p.sufijo ? [v, p.sufijo].join(' ') : v);

  /** Valida el valor y el motivo. Devuelve el valor canónico si todo vale; si no, pinta los errores y no sigue. */
  function validar(): string | null {
    errorValor = errorMotivo = errorGeneral = null;
    const v = props.validar(valor);
    if (!v.ok) errorValor = v.mensaje;
    if (motivo.trim() === '') errorMotivo = T.ERROR_MOTIVO;
    return v.ok && errorMotivo === null ? v.canonico : null;
  }

  function revisar(): void {
    const canonico = validar();
    if (canonico !== null) {
      valor = canonico;
      revisando = true;
    }
  }

  /** EL ÚNICO punto por el que pasa todo envío: valida y ejecuta, venga la orden del botón que venga. */
  async function enviar(): Promise<void> {
    const canonico = validar();
    if (canonico === null) {
      revisando = false;
      return;
    }
    ocupado = true;
    try {
      const r = await props.guardar({ valor: canonico, motivo });
      if (r.ok) {
        aviso = { tono: r.propuesta ? 'informacion' : 'exito', texto: r.propuesta ? T.ENVIADO_A_APROBACION : T.GUARDADO };
        revisando = false;
      } else if (r.explicacion.campo === 'valor') {
        errorValor = r.explicacion.mensaje;
        revisando = false;
      } else if (r.explicacion.campo === 'motivo') {
        errorMotivo = r.explicacion.mensaje;
        revisando = false;
      } else if (!r.conflicto) {
        errorGeneral = r.explicacion.mensaje;
        revisando = false;
      }
    } finally {
      ocupado = false;
    }
  }

  async function retirar(): Promise<void> {
    ocupado = true;
    try {
      const r = await props.retirar();
      if (!r.ok) errorGeneral = r.explicacion.mensaje;
      else aviso = { tono: 'exito', texto: T.GUARDADO };
    } finally {
      ocupado = false;
    }
  }

  const pestanas: Pestana[] = [
    { id: 'valores', rotulo: T.PESTANA_VALOR },
    { id: 'usos', rotulo: T.PESTANA_DONDE_SE_USA },
    { id: 'historial', rotulo: T.PESTANA_HISTORIAL },
  ];
</script>

<section class="panel" aria-labelledby="titulo-param" data-testid="vista-parametro">
  <header class="cabecera-panel">
    <div class="linea">
      <button type="button" class="volver" onclick={props.onvolver}><span aria-hidden="true"><Flecha direccion="izquierda" /></span> {T.VOLVER_A_TODOS}</button>
      <h2 id="titulo-param">{p.nombre}</h2>
      {#if p.impactoAlto}<Chip tono="atencion">{T.CHIP_IMPACTO_ALTO}</Chip>{/if}
      {#if p.pendiente}<Chip tono="marca">{T.CHIP_POR_APROBAR_SUPERADMINISTRACION}</Chip>{/if}
    </div>
    {#if p.descripcion}<p class="subtitulo">{p.descripcion}</p>{/if}
  </header>

  <div class="cuerpo-panel">
    {#if props.conflicto}
      <Aviso tono="error" titulo={T.OTRA_PERSONA_CAMBIO_TITULO}>
        <p data-testid="conflicto">
          {props.conflicto.quien} propuso <span class="diff"><span class="antes">{props.conflicto.antes}</span><span aria-hidden="true"><Flecha direccion="derecha" /></span><span class="despues">{props.conflicto.propuesto}</span></span>
          {props.conflicto.cuando}, antes que tú. {T.TU_PROPUESTA_NO_SE_ENVIO}
        </p>
        <p class="acciones">
          <Boton onclick={props.onaprobaciones} prueba="revisar-su-propuesta">{T.REVISAR_SU_PROPUESTA}</Boton>
          <Boton variante="secundario" onclick={props.oncargarActual} prueba="cargar-valor-actual">{T.CARGAR_EL_VALOR_ACTUAL}</Boton>
        </p>
      </Aviso>
      <fieldset>
        <legend>{T.LO_QUE_TENIAS_ESCRITO}</legend>
        <div class="rejilla">
          <CampoDeValor id="valor-escrito" etiqueta={etiquetaDelCampo} bind:valor tipoDato={p.tipoDato} prefijo={p.prefijo} sufijo={p.sufijo} deshabilitado prueba="valor-escrito" />
          <div class="completo">
            <AreaTexto id="motivo-escrito" etiqueta={T.TU_MOTIVO} bind:valor={motivo} ayuda={T.LO_CONSERVAMOS} deshabilitado />
          </div>
        </div>
      </fieldset>
    {:else}
      <div class="ambito">
        <div class="linea">
          <span class="rotulo">{T.ROTULO_AMBITO}</span>
          <ol class="migas" aria-label={T.ROTULO_AMBITO}>
            {#each p.migas as m, i (i)}
              <li>
                {#if m.actual}<span aria-current="location">{m.rotulo}</span>
                {:else}<button type="button" onclick={() => props.onambito(m.ambito)}>{m.rotulo}</button>{/if}
              </li>
            {/each}
          </ol>
        </div>
        <div class="acciones"><Chip tono="marca">{p.procedencia}</Chip></div>
      </div>

      {#if p.pendiente}
        <Aviso tono="aviso" titulo={T.HAY_UN_CAMBIO_ESPERANDO}>
          <p data-testid="aviso-pendiente">
            {p.pendiente.esPropia ? 'Propusiste' : `${p.pendiente.quien} propuso`}
            <span class="diff"><span class="antes">{p.pendiente.actual}</span><span aria-hidden="true"><Flecha direccion="derecha" /></span><span class="despues">{p.pendiente.propuesto}</span></span>
            {p.pendiente.cuando}. Motivo: «{p.pendiente.motivo}». Mientras tanto <strong>{T.SIGUE_VALIENDO} {p.pendiente.actual}</strong>.
          </p>
          <p class="acciones">
            <button type="button" class="enlace" onclick={props.onaprobaciones}>{T.VER_EN_APROBACIONES}</button>
            {#if p.pendiente.esPropia}
              <button type="button" class="enlace grave" disabled={ocupado} onclick={() => void retirar()} data-testid="retirar">{T.RETIRAR_MI_PROPUESTA}</button>
            {/if}
          </p>
        </Aviso>
      {/if}
      {#if aviso}<Aviso tono={aviso.tono}><p>{aviso.texto}</p></Aviso>{/if}
    {/if}

    <Pestanas {pestanas} activa={props.pestana} nombre={T.SECCIONES_DEL_PARAMETRO} onchange={(id) => props.onpestana(id as PestanaDeDefinicion)} />

    {#if props.pestana === 'usos'}
      <PanelDeUsos usos={props.usos} onreintentar={props.onreintentarUsos} />
    {:else if props.pestana === 'historial'}
      <PanelDeHistorial
        eventos={props.eventos}
        periodo={props.periodo}
        cadena={props.cadena}
        cadenaFallo={props.cadenaFallo}
        topeDeLectura={props.topeDeLectura}
        cadenaRota={props.cadenaRota}
        onreintentar={props.onreintentarHistorial}
        hayMas={props.hayMasHistorial}
        onperiodo={props.onperiodo}
        onmas={props.onmasHistorial}
        onexportar={props.onexportarHistorial}
      />
    {:else if !props.conflicto}
      <div class="dos-columnas">
        {#if revisando}
          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <form
            class="confirmacion decision"
            aria-labelledby="titulo-confirmar"
            data-testid="revision"
            use:enfocarAlMostrar
            onkeydown={cerrarConEscape(() => (revisando = false))}
            onsubmit={(e) => { e.preventDefault(); void enviar(); }}
          >
            <h3 id="titulo-confirmar">{T.ENVIAR_A_APROBACION}</h3>
            <p class="valor-grande">
              <span class="diff"><span class="antes">{p.vigente}</span><span aria-hidden="true"><Flecha direccion="derecha" /></span><span class="despues" data-testid="valor-propuesto">{valorEnPantalla(valor)}</span></span>
            </p>
            <p><strong>{T.mientrasNadieLoApruebe(p.vigente)}</strong> {T.CUANDO_OTRA_PERSONA_LO_APRUEBE}</p>
            <div class="contexto">
              <dl>
                <div class="par"><dt>{T.DONDE_APLICA}</dt><dd>{p.migas.at(-1)?.rotulo}</dd></div>
              </dl>
            </div>
            <div class="espacio-arriba">
              <AreaTexto id="motivo-revision" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errorMotivo} obligatorio />
            </div>
            {#if errorGeneral}<p class="error-campo" role="alert">{errorGeneral}</p>{/if}
            <div class="acciones">
              <Boton tipo="submit" ocupado={ocupado} prueba="enviar-a-aprobacion">{T.ENVIAR_A_APROBACION}</Boton>
              <Boton variante="secundario" onclick={() => (revisando = false)} prueba="volver-a-editar">{T.VOLVER_A_EDITAR}</Boton>
            </div>
          </form>
        {:else}
          <div class="cuerpo-panel">
            {#if p.padres !== null}
              <div class="linea">
                <span class="etiqueta">{T.elegirValorDe(T.VALORES_POR_OPCION)}</span>
                <div class="segmentos" role="group" aria-label={T.VALORES_POR_OPCION}>
                  {#each p.padres as o (o.codigo)}
                    <button type="button" aria-pressed={p.padreElegido === o.codigo} onclick={() => props.onpadre(o.codigo)}>{o.etiqueta} · {o.valor}</button>
                  {/each}
                </div>
              </div>
            {/if}

            <div>
              <div class="cabecera-seccion"><h3>{T.QUE_VALOR_APLICA}</h3></div>
              <p class="ayuda">{T.QUE_VALOR_APLICA_AYUDA}</p>
            </div>
            <ol class="herencia" aria-label={T.CADENA_DE_HERENCIA} data-testid="cadena">
              {#each p.cadena as n, i (n.clave)}
                {#if i > 0}<li class="flecha" aria-hidden="true"><Flecha direccion="derecha" /></li>{/if}
                <li class={n.estado === 'aplica' ? 'aplica' : n.estado === 'hereda' ? 'hereda' : ''}>
                  <span class="donde">{n.donde}</span>
                  <span class="cuanto">{n.cuanto}</span>
                  <span class="nota">{n.nota}</span>
                </li>
              {/each}
            </ol>

            <form
              data-testid="formulario-valor"
              onsubmit={(e) => { e.preventDefault(); if (p.impactoAlto) revisar(); else void enviar(); }}
            >
              <fieldset disabled={bloqueado}>
                <legend>{T.NUEVO_VALOR}</legend>
                <div class="rejilla">
                  <CampoDeValor
                    id="valor"
                    etiqueta={etiquetaDelCampo}
                    bind:valor
                    tipoDato={p.tipoDato}
                    prefijo={p.prefijo}
                    sufijo={p.sufijo}
                    ayuda={bloqueado && p.pendiente ? T.NO_SE_PUEDE_EDITAR_MIENTRAS : p.rango}
                    error={errorValor}
                    obligatorio
                    deshabilitado={bloqueado}
                    prueba="campo-valor"
                    imagen={p.codigo === 'marca_logo'}
                  />
                  <div class="completo">
                    <AreaTexto id="motivo" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errorMotivo} ayuda={p.impactoAlto ? T.VALOR_AYUDA_MOTIVO_APROBADOR : T.MOTIVO_AYUDA} obligatorio deshabilitado={bloqueado} />
                  </div>
                </div>
              </fieldset>
              {#if errorGeneral}<p class="error-campo" role="alert">{errorGeneral}</p>{/if}
              {#if p.puedeEditar && !p.pendiente}
                <div class="barra">
                  <div class="acciones">
                    <Boton tipo="submit" ocupado={ocupado} prueba={p.impactoAlto ? 'revisar-cambio' : 'guardar-valor'}>{p.impactoAlto ? T.REVISAR_EL_CAMBIO : T.GUARDAR_VALOR}</Boton>
                    <Boton variante="secundario" onclick={props.onvolver}>{T.CANCELAR}</Boton>
                    <span class="ayuda">{p.impactoAlto ? T.IMPACTO_ALTO_NECESITA_APROBACION : T.IMPACTO_NORMAL_AL_GUARDAR}</span>
                  </div>
                </div>
              {/if}
            </form>
          </div>
        {/if}

        <aside class="cuerpo-panel" aria-label={T.QUIEN_PUEDE_EDITAR}>
          {#if revisando || p.impactoAlto}
            <Aviso tono="informacion" titulo={T.DOBLE_CONTROL_TITULO}><p>{T.DOBLE_CONTROL_CUERPO}</p></Aviso>
          {/if}
          <div class="ficha">
            <h4>{T.QUIEN_PUEDE_EDITAR}</h4>
            {#each p.quienEdita as q, i (i)}<p>{q}</p>{/each}
            {#if props.editoresFallo}<ErrorDeLectura titulo={T.ERROR_EDITORES} onreintentar={props.onreintentarEditores} prueba="editores-error" />{/if}
            {#if props.onverPermisos}<p><button type="button" class="enlace" onclick={props.onverPermisos}>{T.VER_PERMISOS}</button></p>{/if}
          </div>
          <div class="contexto">
            <h3>{T.DEFINICION}</h3>
            <dl>
              {#each p.definicion as d (d.rotulo)}
                <div class="par"><dt>{d.rotulo}</dt><dd>{#if d.codigo}<span class="codigo">{d.valor}</span>{:else}{d.valor}{/if}</dd></div>
              {/each}
            </dl>
          </div>
        </aside>
      </div>
    {/if}
  </div>
</section>
