<script lang="ts">
  /**
   * Una lista en un ámbito (`p02-lista`, `--editar`, `--desactivar`, `--heredada`, `--cascada`,
   * `p03-donde-se-usa`, `p04-historial`). Vista PURA: recibe el modelo (`construirLista`) y devuelve
   * eventos; lo que escribe lo decide el contenedor, que devuelve un `Resultado` ya explicado.
   *
   * Dos reglas de diseño viven aquí a la vista de todos:
   *  - **la confirmación cuelga del RESULTADO**: desactivar, reactivar, volver a heredar y crear una
   *    versión propia pasan por el mismo punto —`confirmar()`— tras validar el motivo, venga la orden
   *    del botón que venga; renombrar una opción (reversible, impacto normal) se guarda sin diálogo;
   *  - **todo guardado pide motivo**: sin él, el campo lo dice y no se llama a nada (esc. 4).
   */
  import Flecha from '../componentes/Flecha.svelte';
  import { cerrarConEscape, enfocarAlMostrar } from '../componentes/enfocar';
  import AreaTexto from '$lib/ui/AreaTexto.svelte';
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import Entrada from '$lib/ui/Entrada.svelte';
  import Pestanas, { type Pestana } from '$lib/ui/Pestanas.svelte';
  import type { Ambito } from '../ambitos';
  import type { Resultado } from '../acciones';
  import type { Explicacion } from '../fallos';
  import type { EventoVM, Periodo } from '../historial';
  import type { ListaVM, OpcionVM } from '../lista';
  import type { PestanaDeDefinicion } from '../ruta';
  import * as T from '../textos';
  import type { UsosVM } from '../usos';
  import Chip from '../componentes/Chip.svelte';
  import ErrorDeLectura from '../componentes/ErrorDeLectura.svelte';
  import PanelDeHistorial from '../componentes/PanelDeHistorial.svelte';
  import PanelDeUsos from '../componentes/PanelDeUsos.svelte';
  import VistaPrevia from '../componentes/VistaPrevia.svelte';
  import '../estilos.css';

  interface Props {
    lista: ListaVM;
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
    onpestana: (p: PestanaDeDefinicion) => void;
    onvolver: () => void;
    onambito: (a: Ambito) => void;
    onpadre: (codigo: string) => void;
    onperiodo: (p: Periodo) => void;
    onmasHistorial: () => void;
    onexportarHistorial: () => void;
    onverPermisos?: (() => void) | null;
    guardarEdicion: (d: { clave: string; etiqueta: string; ayuda: string; motivo: string }) => Promise<Resultado>;
    anadir: (d: { codigo: string; etiqueta: string; ayuda: string; motivo: string }) => Promise<Resultado>;
    cambiarEstado: (d: { clave: string; activar: boolean; motivo: string }) => Promise<Resultado>;
    guardarOrden: (d: { ordenNuevo: string[]; motivo: string }) => Promise<Resultado>;
    versionPropia: (motivo: string) => Promise<Resultado>;
    volverAHeredar: (motivo: string) => Promise<Resultado>;
  }

  const props: Props = $props();
  const lista = $derived(props.lista);

  // ─── Estado de los formularios (solo de la vista) ───────────────────────────────────────────────
  type Formulario = 'editar' | 'anadir' | 'estado' | 'version' | 'heredar';
  let abierto = $state<Formulario | null>(null);
  let claveElegida = $state<string | null>(null);
  let activarElegida = $state(false);
  let etiqueta = $state('');
  let ayuda = $state('');
  let codigo = $state('');
  let motivo = $state('');
  let errores = $state<Partial<Record<Explicacion['campo'], string>>>({});
  let ocupado = $state(false);
  let aviso = $state<{ tono: 'exito' | 'informacion'; texto: string } | null>(null);
  /** El orden que la persona está armando, antes de guardarlo con su motivo. */
  let ordenLocal = $state<string[] | null>(null);

  const elegida = $derived(lista.opciones.find((o) => o.clave === claveElegida) ?? null);
  const filasEnPantalla = $derived.by<OpcionVM[]>(() => {
    if (ordenLocal === null) return lista.opciones;
    return ordenLocal.map((c) => lista.opciones.find((o) => o.codigo === c)).filter((o): o is OpcionVM => o !== undefined);
  });
  const editable = $derived(lista.puedeEditar && lista.modo === 'propia');

  function cerrar(): void {
    abierto = null;
    claveElegida = null;
    motivo = '';
    etiqueta = '';
    ayuda = '';
    codigo = '';
    errores = {};
  }

  function abrirEdicion(o: OpcionVM): void {
    cerrar();
    abierto = 'editar';
    claveElegida = o.clave;
    etiqueta = o.etiqueta;
    ayuda = o.ayuda;
  }
  function abrirEstado(o: OpcionVM, activar: boolean): void {
    cerrar();
    abierto = 'estado';
    claveElegida = o.clave;
    activarElegida = activar;
  }
  function abrirAnadir(): void {
    cerrar();
    abierto = 'anadir';
  }
  function abrir(f: 'version' | 'heredar'): void {
    cerrar();
    abierto = f;
  }

  /**
   * EL ÚNICO punto por el que pasa todo guardado: valida el motivo, ejecuta y explica. Un guardado sin
   * motivo no llega al contenedor ni, por tanto, a la API.
   */
  async function confirmar(accion: () => Promise<Resultado>, extra: { ordenAlTerminar?: boolean } = {}): Promise<void> {
    if (motivo.trim() === '') {
      errores = { ...errores, motivo: T.ERROR_MOTIVO };
      return;
    }
    ocupado = true;
    errores = {};
    try {
      const r = await accion();
      if (r.ok) {
        aviso = { tono: r.propuesta ? 'informacion' : 'exito', texto: r.propuesta ? T.ENVIADO_A_APROBACION : T.GUARDADO };
        if (extra.ordenAlTerminar) ordenLocal = null;
        cerrar();
      } else {
        errores = { [r.explicacion.campo]: r.explicacion.mensaje };
      }
    } finally {
      ocupado = false;
    }
  }

  const guardarEdicion = () => confirmar(() => props.guardarEdicion({ clave: claveElegida ?? '', etiqueta, ayuda, motivo }));
  const guardarAnadir = () => confirmar(() => props.anadir({ codigo, etiqueta, ayuda, motivo }));
  const guardarEstado = () => confirmar(() => props.cambiarEstado({ clave: claveElegida ?? '', activar: activarElegida, motivo }));
  const guardarVersion = () => confirmar(() => props.versionPropia(motivo));
  const guardarHeredar = () => confirmar(() => props.volverAHeredar(motivo));
  const guardarOrden = () => confirmar(() => props.guardarOrden({ ordenNuevo: ordenLocal ?? [], motivo }), { ordenAlTerminar: true });

  function mover(o: OpcionVM, hacia: -1 | 1): void {
    const actual = ordenLocal ?? lista.opciones.map((x) => x.codigo);
    const i = actual.indexOf(o.codigo);
    const j = i + hacia;
    if (i < 0 || j < 0 || j >= actual.length) return;
    const nuevo = [...actual];
    [nuevo[i], nuevo[j]] = [nuevo[j], nuevo[i]];
    cerrar();
    ordenLocal = nuevo;
  }

  const pestanas: Pestana[] = [
    { id: 'valores', rotulo: T.PESTANA_VALORES },
    { id: 'usos', rotulo: T.PESTANA_DONDE_SE_USA },
    { id: 'historial', rotulo: T.PESTANA_HISTORIAL },
  ];
</script>

<section class="panel" aria-labelledby="titulo-lista" data-testid="vista-lista">
  <header class="cabecera-panel">
    <div class="linea">
      <button type="button" class="volver" onclick={props.onvolver}><span aria-hidden="true"><Flecha direccion="izquierda" /></span> {T.VOLVER_A_TODOS}</button>
      <h2 id="titulo-lista">{lista.nombre}</h2>
      {#if lista.impactoAlto}<Chip tono="atencion">{T.CHIP_IMPACTO_ALTO}</Chip>{/if}
    </div>
    {#if lista.descripcion}<p class="subtitulo">{lista.descripcion}</p>{/if}
  </header>

  <div class="cuerpo-panel">
    <div class="ambito">
      <div class="linea">
        <span class="rotulo">{T.ROTULO_AMBITO}</span>
        <ol class="migas" aria-label={T.ROTULO_AMBITO}>
          {#each lista.migas as m, i (i)}
            <li>
              {#if m.actual}<span aria-current="location">{m.rotulo}</span>
              {:else}<button type="button" onclick={() => props.onambito(m.ambito)}>{m.rotulo}</button>{/if}
            </li>
          {/each}
        </ol>
      </div>
      <div class="acciones">
        <Chip tono={lista.modo === 'heredada' ? 'neutro' : 'marca'}>{lista.procedencia}</Chip>
        {#if lista.puedeVolverAHeredar}
          <button type="button" class="enlace" onclick={() => abrir('heredar')}>{T.VOLVER_A_HEREDAR}</button>
        {/if}
      </div>
    </div>

    {#if aviso}
      <Aviso tono={aviso.tono === 'exito' ? 'exito' : 'informacion'}><p>{aviso.texto}</p></Aviso>
    {/if}

    {#if lista.modo === 'heredada'}
      <Aviso tono="informacion" titulo={T.heredaTitulo(lista.heredaDe)}>
        <p>{T.HEREDA_CUERPO}</p>
        {#if lista.puedeCrearVersionPropia}
          <p class="acciones">
            <Boton variante="primario" onclick={() => abrir('version')} prueba="crear-version-propia">{T.CREAR_VERSION_PROPIA}</Boton>
          </p>
        {/if}
      </Aviso>
    {/if}

    {#if abierto === 'version' || abierto === 'heredar'}
      <form
        class="confirmacion {abierto === 'heredar' ? '' : 'decision'}"
        aria-labelledby="titulo-confirmar"
        data-testid="confirmacion-ambito"
        onsubmit={(e) => { e.preventDefault(); void (abierto === 'version' ? guardarVersion() : guardarHeredar()); }}
      >
        <h3 id="titulo-confirmar">{abierto === 'version' ? T.crearVersionTitulo : T.volverAHeredarTitulo}</h3>
        <p>{abierto === 'version' ? T.CREAR_VERSION_CUERPO : T.VOLVER_A_HEREDAR_CUERPO}</p>
        <AreaTexto id="motivo-ambito" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} ayuda={T.MOTIVO_AYUDA} obligatorio />
        {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
        <div class="acciones">
          <Boton tipo="submit" variante={abierto === 'heredar' ? 'peligro' : 'primario'} ocupado={ocupado} prueba="confirmar-ambito">{abierto === 'version' ? T.CREAR_VERSION_PROPIA : T.VOLVER_A_HEREDAR_ACCION}</Boton>
          <Boton variante="secundario" onclick={cerrar}>{T.CANCELAR}</Boton>
        </div>
      </form>
    {/if}

    <Pestanas {pestanas} activa={props.pestana} nombre={T.SECCIONES_DE_LA_LISTA} onchange={(id) => props.onpestana(id as PestanaDeDefinicion)} />

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
    {:else}
      <div class="dos-columnas">
        <div class="cuerpo-panel">
          {#if lista.padres !== null}
            <div class="linea">
              <span class="etiqueta">{lista.padres.length > 0 ? T.elegirPadre(lista.nombre) : ''}</span>
              <div class="segmentos" role="group" aria-label={T.PRODUCTO_ROTULO}>
                {#each lista.padres as p (p.codigo)}
                  <button type="button" aria-pressed={lista.padreElegido === p.codigo} onclick={() => props.onpadre(p.codigo)}>
                    {T.padreConCuantas(p.etiqueta, p.cuantas)}
                  </button>
                {/each}
              </div>
            </div>
          {/if}

          <div class="cabecera-seccion">
            <h3>{T.opcionesYActivas(lista.total, lista.activas)}</h3>
            {#if editable}
              <Boton variante="secundario" onclick={abrirAnadir} prueba="anadir-opcion">{T.ANADIR_OPCION_ROTULO}</Boton>
            {/if}
          </div>

          {#if filasEnPantalla.length === 0}
            <EstadoVacio titulo={T.SIN_OPCIONES} prueba="lista-sin-opciones" />
          {:else}
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <div class="tabla-marco" role="region" tabindex="0" aria-label={T.TABLA_OPCIONES}>
              <table class="tabla" data-testid="tabla-de-valores">
                <thead>
                  <tr>
                    <th scope="col">{T.COLUMNA_ORDEN}</th>
                    <th scope="col">{T.COLUMNA_OPCION}</th>
                    <th scope="col" class="ocultable">{T.COLUMNA_CODIGO}</th>
                    <th scope="col">{lista.modo === 'heredada' ? T.COLUMNA_VIENE_DE : T.COLUMNA_ESTADO}</th>
                    {#if editable}<th scope="col"><span class="solo-lectores">{T.COLUMNA_ACCIONES}</span></th>{/if}
                  </tr>
                </thead>
                <tbody>
                  {#each filasEnPantalla as o, i (o.clave)}
                    <tr class:inactiva={!o.activa} class:editando={claveElegida === o.clave} data-testid="opcion-{o.codigo}">
                      <td>
                        {#if editable}
                          <span class="orden">
                            <button type="button" aria-label={T.subirA(o.etiqueta)} disabled={i === 0} onclick={() => mover(o, -1)}><Flecha direccion="arriba" /></button>
                            <button type="button" aria-label={T.bajarA(o.etiqueta)} disabled={i === filasEnPantalla.length - 1} onclick={() => mover(o, 1)}><Flecha direccion="abajo" /></button>
                          </span>
                        {:else}
                          <span class="num">{o.posicion}</span>
                        {/if}
                      </td>
                      <td>{o.etiqueta}{#if claveElegida === o.clave && abierto === 'editar'}{' '}<strong>· editando</strong>{/if}</td>
                      <td class="ocultable"><span class="codigo">{o.codigo}</span></td>
                      <td>
                        {#if lista.modo === 'heredada'}{lista.heredaDe}
                        {:else if o.activa}<Chip tono="exito">{T.CHIP_ACTIVA}</Chip>
                        {:else}<Chip tono="neutro">{T.CHIP_INACTIVA}</Chip>{/if}
                      </td>
                      {#if editable}
                        <td class="acciones-fila">
                          <button type="button" class="enlace" onclick={() => abrirEdicion(o)}>{T.EDITAR}</button>
                          {#if o.activa}
                            <button type="button" class="enlace grave" onclick={() => abrirEstado(o, false)}>{T.DESACTIVAR}</button>
                          {:else}
                            <button type="button" class="enlace" onclick={() => abrirEstado(o, true)}>{T.REACTIVAR}</button>
                          {/if}
                        </td>
                      {/if}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}

          {#if ordenLocal !== null}
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <form class="confirmacion decision" aria-labelledby="titulo-orden" data-testid="confirmacion-orden" use:enfocarAlMostrar onkeydown={cerrarConEscape(cerrar)} onsubmit={(e) => { e.preventDefault(); void guardarOrden(); }}>
              <h3 id="titulo-orden">{T.ORDEN_SIN_GUARDAR}</h3>
              <AreaTexto id="motivo-orden" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} ayuda={T.MOTIVO_AYUDA} obligatorio />
              {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
              <div class="acciones">
                <Boton tipo="submit" ocupado={ocupado} prueba="guardar-orden">{T.GUARDAR_ORDEN}</Boton>
                <Boton variante="secundario" onclick={() => { ordenLocal = null; cerrar(); }}>{T.DESCARTAR}</Boton>
              </div>
            </form>
          {/if}

          {#if abierto === 'editar' && elegida}
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <form class="confirmacion decision" aria-labelledby="titulo-editar" data-testid="formulario-edicion" use:enfocarAlMostrar onkeydown={cerrarConEscape(cerrar)} onsubmit={(e) => { e.preventDefault(); void guardarEdicion(); }}>
              <h3 id="titulo-editar">{T.EDITAR_OPCION(elegida.etiqueta)}</h3>
              <div class="rejilla">
                <Entrada id="etiqueta" etiqueta={T.CAMPO_NOMBRE} bind:valor={etiqueta} error={errores.etiqueta ?? null} obligatorio />
                <Entrada id="codigo" etiqueta={T.CAMPO_CODIGO} valor={elegida.codigo} soloLectura ayuda={T.CODIGO_BLOQUEADO} />
                <div class="completo">
                  <Entrada id="ayuda-opcion" etiqueta={T.CAMPO_AYUDA} bind:valor={ayuda} marcador={T.AYUDA_PLACEHOLDER} />
                </div>
                <div class="completo">
                  <AreaTexto id="motivo" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} ayuda={T.MOTIVO_AYUDA} obligatorio />
                </div>
              </div>
              {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
              <div class="acciones">
                <Boton tipo="submit" ocupado={ocupado} prueba="guardar-edicion">{T.GUARDAR_CAMBIO}</Boton>
                <Boton variante="secundario" onclick={cerrar}>{T.CANCELAR}</Boton>
                <span class="ayuda">{T.IMPACTO_NORMAL_SE_APLICA}</span>
              </div>
            </form>
          {/if}

          {#if abierto === 'anadir'}
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <form class="confirmacion decision" aria-labelledby="titulo-nueva" data-testid="formulario-nueva" use:enfocarAlMostrar onkeydown={cerrarConEscape(cerrar)} onsubmit={(e) => { e.preventDefault(); void guardarAnadir(); }}>
              <h3 id="titulo-nueva">{T.NUEVA_OPCION}</h3>
              <div class="rejilla">
                <Entrada id="etiqueta-nueva" etiqueta={T.CAMPO_NOMBRE} bind:valor={etiqueta} error={errores.etiqueta ?? null} obligatorio />
                <Entrada id="codigo-nuevo" etiqueta={T.CAMPO_CODIGO} bind:valor={codigo} error={errores.codigo ?? null} ayuda={T.CODIGO_NUEVO_AYUDA} obligatorio />
                <div class="completo">
                  <Entrada id="ayuda-nueva" etiqueta={T.CAMPO_AYUDA} bind:valor={ayuda} marcador={T.AYUDA_PLACEHOLDER} />
                </div>
                <div class="completo">
                  <AreaTexto id="motivo-nueva" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} ayuda={T.MOTIVO_AYUDA} obligatorio />
                </div>
              </div>
              {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
              <div class="acciones">
                <Boton tipo="submit" ocupado={ocupado} prueba="guardar-nueva">{T.GUARDAR_CAMBIO}</Boton>
                <Boton variante="secundario" onclick={cerrar}>{T.CANCELAR}</Boton>
              </div>
            </form>
          {/if}

          {#if abierto === 'estado' && elegida}
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <form class="confirmacion {activarElegida ? 'decision' : ''}" aria-labelledby="titulo-estado" data-testid="confirmacion-estado" use:enfocarAlMostrar onkeydown={cerrarConEscape(cerrar)} onsubmit={(e) => { e.preventDefault(); void guardarEstado(); }}>
              <h3 id="titulo-estado">{activarElegida ? T.reactivarTitulo(elegida.etiqueta) : T.desactivarTitulo(elegida.etiqueta)}</h3>
              <p>{activarElegida ? T.REACTIVAR_CUERPO : T.DESACTIVAR_CUERPO}</p>
              {#if !activarElegida}
                <div class="aviso-de-usos" data-testid="usos-de-la-opcion">
                  {#if props.usos === 'error'}
                    <p>{T.DESACTIVAR_USOS_ERROR}</p>
                  {:else if props.usos === null}
                    <p>{T.DESACTIVAR_SIN_USOS}</p>
                  {:else if props.usos !== 'cargando'}
                    {@const suyos = props.usos.expedientes.find((x) => x.codigo === elegida?.codigo)}
                    <p>{T.DESACTIVAR_SE_USA_EN}{' '}{props.usos.lugares.map((l) => l.titulo).join(', ') || T.DESACTIVAR_NINGUN_LUGAR}.</p>
                    {#if suyos}<p>{T.DESACTIVAR_EXPEDIENTES(suyos.guardados, suyos.enCurso)}</p>{/if}
                  {/if}
                </div>
              {/if}
              <AreaTexto id="motivo-estado" etiqueta={T.CAMPO_MOTIVO} bind:valor={motivo} error={errores.motivo ?? null} obligatorio />
              {#if errores.general}<p class="error-campo" role="alert">{errores.general}</p>{/if}
              <div class="acciones">
                <Boton tipo="submit" variante={activarElegida ? 'primario' : 'peligro'} ocupado={ocupado} prueba="confirmar-estado">{activarElegida ? T.REACTIVAR_OPCION : T.DESACTIVAR_OPCION}</Boton>
                <Boton variante="secundario" onclick={cerrar}>{T.CANCELAR}</Boton>
              </div>
            </form>
          {/if}

          {#if lista.modo !== 'heredada' && props.ultimaModificacion}
            <p class="ayuda">{T.ULTIMA_MODIFICACION}: {props.ultimaModificacion} {T.OPCIONES_INACTIVAS_AYUDA}</p>
          {:else if lista.modo === 'heredada'}
            <p class="ayuda">{T.HEREDADA_SE_EDITA_EN_EL_ORIGEN}</p>
          {/if}

          {#if lista.sinHijas}
            <Aviso tono="informacion" titulo={T.sinHijasTitulo(lista.etiquetaDelPadre)}>
              <p>{T.sinHijasCuerpo(lista.etiquetaDelPadre, lista.nombre)}</p>
            </Aviso>
          {/if}
          {#if lista.huerfanas.length > 0}
            <Aviso tono="aviso" titulo={T.huerfanasTitulo}>
              <p>{T.huerfanasCuerpo(lista.huerfanas.map((h) => h.etiqueta).join(', '))}</p>
            </Aviso>
          {/if}
          {#if lista.nuevasDelOrigen > 0}
            <Aviso tono="aviso" titulo={T.nuevasDelOrigen(lista.nuevasDelOrigen)}>
              <p>{T.NUEVAS_DEL_ORIGEN_AYUDA}</p>
            </Aviso>
          {/if}
        </div>

        <aside class="cuerpo-panel" aria-label={T.VISTA_PREVIA}>
          {#if lista.vistaPrevia.length > 0}<VistaPrevia campos={lista.vistaPrevia} />{/if}
          {#if lista.actividades.length > 0}
            <div class="ficha" data-testid="versiones-propias">
              <h4>{T.VERSIONES_PROPIAS}</h4>
              {#each lista.actividades as a, i (i)}
                <p><button type="button" class="enlace" onclick={() => props.onambito(a.ambito)}>{a.nombre}</button> · {a.propia ? T.TIENE_VERSION_PROPIA : T.HEREDA_ESTA}</p>
              {/each}
            </div>
          {/if}
          <div class="ficha">
            <h4>{T.QUIEN_PUEDE_EDITAR}</h4>
            {#each lista.quienEdita as q, i (i)}<p>{q}</p>{/each}
            {#if props.editoresFallo}<ErrorDeLectura titulo={T.ERROR_EDITORES} onreintentar={props.onreintentarEditores} prueba="editores-error" />{/if}
            {#if props.onverPermisos}<p><button type="button" class="enlace" onclick={props.onverPermisos}>{T.VER_PERMISOS}</button></p>{/if}
          </div>
          <div class="contexto">
            <h3>{T.DEFINICION}</h3>
            <dl>
              {#each lista.definicion as d (d.rotulo)}
                <div class="par"><dt>{d.rotulo}</dt><dd>{#if d.codigo}<span class="codigo">{d.valor}</span>{:else}{d.valor}{/if}</dd></div>
              {/each}
            </dl>
          </div>
        </aside>
      </div>
    {/if}
  </div>
</section>
