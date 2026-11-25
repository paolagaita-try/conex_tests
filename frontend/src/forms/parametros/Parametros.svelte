<script lang="ts">
  /**
   * La aplicación de administración de parámetros: una sola página con
   * navegación propia. Este contenedor lee lo que la persona puede ver (`cargarContexto`), decide qué
   * vista pintar según la ruta y pasa a las vistas —puras— los datos y los eventos.
   *
   * La compuerta de familia está AQUÍ y es la primera lectura: si la API `parametros` responde 403, la
   * aplicación entera dice que no está disponible, sin nombrar nada, y no pide nada más.
   */
  import ErrorDeLectura from './componentes/ErrorDeLectura.svelte';
  import { onMount, untrack } from 'svelte';
  import { recuentoDe } from '$lib/bonita/marcas';
  import Aviso from '$lib/ui/Aviso.svelte';
  import Boton from '$lib/ui/Boton.svelte';
  import EstadoVacio from '$lib/ui/EstadoVacio.svelte';
  import { ofrecer } from './aplicacion';
  import { FalloDelKit, type Kit } from './kit';
  import { cargarContexto, propuestasDe, type Contexto } from './carga';
  import { descargar } from './csv';
  import { inicioACsv } from './exportar';
  import { construirInicio, type FiltroDeTipo } from './inicio';
  import { nombreDeProceso } from './nombres';
  import { hashDe, leerRuta, type Ruta, type Seccion } from './ruta';
  import * as T from './textos';
  import Marco from './componentes/Marco.svelte';
  import PantallaDeLista from './contenedores/PantallaDeLista.svelte';
  import PantallaDeAprobaciones from './contenedores/PantallaDeAprobaciones.svelte';
  import PantallaDeImportar from './contenedores/PantallaDeImportar.svelte';
  import PantallaDePermisos from './contenedores/PantallaDePermisos.svelte';
  import PantallaDeTraza from './contenedores/PantallaDeTraza.svelte';
  import PantallaDeParametro from './contenedores/PantallaDeParametro.svelte';
  import VistaInicio from './vistas/VistaInicio.svelte';
  import './estilos.css';

  interface Props {
    /** El cliente del kit. Los tests y la galería inyectan el suyo; la aplicación usa el de la plataforma. */
    kit: Kit;
    /** La galería viva pinta la aplicación sin tocar la dirección de su propia página. */
    sinHash?: boolean;
    rutaInicial?: Ruta;
  }

  const { kit, sinHash = false, rutaInicial }: Props = $props();

  ofrecer({
    get kit() {
      return kit;
    },
    contexto: () => {
      if (!ctx) throw new Error('la aplicación aún no cargó');
      return ctx;
    },
    refrescar: (codigo) => refrescar(codigo),
    avisarRefresco: (clave, r) => avisarRefresco(clave, r),
    releer: (codigo) => releer(codigo),
  });

  type Estado = 'cargando' | 'listo' | 'noDisponible' | 'error';

  let estado = $state<Estado>('cargando');
  let ctx = $state<Contexto | null>(null);
  let ruta = $state<Ruta>(untrack(() => rutaInicial ?? leerRuta(typeof location === 'undefined' || sinHash ? '' : location.hash)));
  let filtro = $state<FiltroDeTipo>('todo');
  let busqueda = $state('');
  /** La lectura posterior a una escritura falló: se conserva cómo reintentarla. */
  /** Definiciones cuya lectura al abrirlas falló: lo que se ve de ellas puede estar viejo. */
  let lecturasViejas = $state<Record<string, () => Promise<void>>>({});
  let refrescosFallidos = $state<Record<string, () => Promise<void>>>({});

  async function cargar(): Promise<void> {
    estado = 'cargando';
    try {
      ctx = await cargarContexto(kit);
      // Con delegación se ve lo suyo primero y lo global en solo lectura detrás: "Todo" ordenado.
      filtro = 'todo';
      estado = 'listo';
    } catch (e) {
      ctx = null;
      estado = e instanceof FalloDelKit && e.clase === 'SIN_PERMISO' ? 'noDisponible' : 'error';
    }
  }

  onMount(() => {
    const alCambiar = () => {
      ruta = leerRuta(location.hash);
    };
    if (!sinHash) window.addEventListener('hashchange', alCambiar);
    void cargar();
    return () => window.removeEventListener('hashchange', alCambiar);
  });

  function navegar(destino: Ruta): void {
    ruta = destino;
    if (!sinHash && typeof location !== 'undefined') location.hash = hashDe(destino);
  }

  const seccionDe = (r: Ruta): Seccion =>
    r.vista === 'aprobaciones' ? 'aprobaciones' : r.vista === 'permisos' || r.vista === 'nuevaDelegacion' ? 'permisos' : r.vista === 'traza' ? 'traza' : 'parametros';

  function irA(seccion: Seccion): void {
    navegar(
      seccion === 'aprobaciones' ? { vista: 'aprobaciones' } : seccion === 'permisos' ? { vista: 'permisos' } : seccion === 'traza' ? { vista: 'traza' } : { vista: 'inicio' },
    );
  }

  const inicio = $derived(ctx ? construirInicio(ctx.datos, ctx.capacidades, filtro, busqueda) : null);
  const paraAprobar = $derived.by(() => {
    if (!ctx) return null;
    const mias = ctx.propuestas.filter((p) => p.puedesAprobar);
    return recuentoDe(mias);
  });
  const procesosDelDelegado = $derived(
    ctx ? [...new Set(ctx.capacidades.permisos.map((p) => nombreDeProceso(p.proceso)))].join(', ') : '',
  );
  const titular = $derived.by(() => {
    if (!ctx || ruta.vista !== 'inicio') return null;
    if (ctx.capacidades.perfil === 'superadministracion' && paraAprobar !== null) return T.titularDeSuperadministracion(paraAprobar);
    if (ctx.capacidades.perfil === 'delegado') return T.titularDelDelegado(procesosDelDelegado);
    return T.TITULAR_DE_CONSULTA;
  });

  function abrir(clave: string): void {
    const fila = inicio?.grupos.flatMap((g) => g.filas).find((f) => f.clave === clave);
    if (fila) navegar({ vista: 'definicion', definicion: fila.codigo, ambito: fila.ambito, pestana: 'valores' });
  }

  /** Tras una escritura aplicada: vuelve a leer la definición y lo pendiente (el contador de Aprobaciones). */
  /** Al volver a Inicio se relee todo (lo que se ve ahí es lo leído al arrancar): en silencio, sin parpadeo de «cargando». */
  let salioDeInicio = false;
  async function recargarInicio(): Promise<void> {
    const { ['*']: _quitada, ...resto } = lecturasViejas;
    try {
      ctx = await cargarContexto(kit);
      lecturasViejas = resto;
    } catch {
      lecturasViejas = { ...resto, '*': () => recargarInicio() };
    }
  }
  $effect(() => {
    const vista = ruta.vista;
    if (estado !== 'listo') return;
    if (vista !== 'inicio') salioDeInicio = true;
    else if (salioDeInicio) {
      salioDeInicio = false;
      untrack(() => void recargarInicio());
    }
  });

  async function releer(codigo: string): Promise<void> {
    if (!ctx) return;
    const { [codigo]: _quitada, ...resto } = lecturasViejas;
    try {
      const v = await kit.valores(codigo);
      ctx.datos.valores[codigo] = v;
      lecturasViejas = resto;
    } catch {
      // Un valor viejo NO se pinta mudo como vigente: se dice que no se pudo releer.
      lecturasViejas = { ...resto, [codigo]: () => releer(codigo) };
    }
  }
  function avisarRefresco(clave: string, r: (() => Promise<void>) | null): void {
    const { [clave]: _quitada, ...resto } = refrescosFallidos;
    refrescosFallidos = r ? { ...resto, [clave]: r } : resto;
  }
  async function reintentarRefrescos(): Promise<void> {
    for (const r of Object.values(refrescosFallidos)) await r();
  }

  async function refrescar(codigo: string): Promise<void> {
    if (!ctx) return;
    try {
      // `codigo` vacío = solo lo pendiente (una decisión sobre algo que no es una lista ni un parámetro).
      const [v, p] = await Promise.all([codigo && ctx.datos.valores[codigo] ? kit.valores(codigo) : null, propuestasDe(kit, 'PENDIENTE')]);
      if (v) ctx.datos.valores[codigo] = v;
      ctx.propuestas = p.propuestas;
      ctx.datos.pendientes = p.propuestas.filter((x) => x.estado === 'PENDIENTE');
      avisarRefresco('vista', null);
    } catch {
      // La escritura ya se aplicó: leerla de vuelta que falle no la deshace ni la convierte en error (B2).
      avisarRefresco('vista', () => refrescar(codigo));
    }
  }

  function exportar(): void {
    if (inicio) descargar(T.NOMBRE_DEL_FICHERO_DE_PARAMETROS, inicioACsv(inicio));
  }
</script>

{#if estado === 'cargando'}
  <main class="pa" aria-busy="true">
    <p role="status">{T.CARGANDO}</p>
  </main>
{:else if estado === 'noDisponible'}
  <main class="pa">
    <EstadoVacio titulo={T.NO_DISPONIBLE_TITULO} detalle={T.NO_DISPONIBLE_CUERPO} prueba="no-disponible" />
  </main>
{:else if estado === 'error' || !ctx || !inicio}
  <main class="pa">
    <Aviso tono="error" titulo={T.ERROR_TITULO}>
      <p>{T.ERROR_CUERPO}</p>
      <p class="acciones"><Boton variante="secundario" onclick={() => void cargar()} prueba="reintentar">{T.REINTENTAR}</Boton></p>
    </Aviso>
  </main>
{:else}
  <Marco
    persona={ctx.nombres[ctx.sesion.usuario] ?? ctx.sesion.nombre}
    usuario={ctx.sesion.usuario}
    cargo={ctx.sesion.cargo}
    icono={ctx.sesion.icono}
    capacidades={ctx.capacidades}
    procesos={procesosDelDelegado}
    seccion={seccionDe(ruta)}
    dentro={ruta.vista !== 'inicio' && ruta.vista !== 'aprobaciones' && ruta.vista !== 'permisos' && ruta.vista !== 'traza'}
    porAprobar={paraAprobar}
    {titular}
    onir={irA}
  >
    {#if Object.keys(lecturasViejas).length > 0}
      <ErrorDeLectura titulo={T.VALOR_POSIBLEMENTE_VIEJO_TITULO} cuerpo={T.VALOR_POSIBLEMENTE_VIEJO_CUERPO} onreintentar={() => void Promise.all(Object.values(lecturasViejas).map((r) => r()))} prueba="lectura-vieja" />
    {/if}
    {#if Object.keys(refrescosFallidos).length > 0}
      <ErrorDeLectura titulo={T.GUARDADO_SIN_ACTUALIZAR_TITULO} cuerpo={T.GUARDADO_SIN_ACTUALIZAR_CUERPO} onreintentar={() => void reintentarRefrescos()} prueba="refresco-fallido" />
    {/if}
    {#if ruta.vista === 'inicio'}
      <VistaInicio
        {inicio}
        capacidades={ctx.capacidades}
        {filtro}
        {busqueda}
        onfiltro={(f) => (filtro = f)}
        onbusqueda={(q) => (busqueda = q)}
        onabrir={abrir}
        onimportar={() => navegar({ vista: 'importar' })}
        onexportar={exportar}
      />
    {:else if ruta.vista === 'aprobaciones'}
      <PantallaDeAprobaciones />
    {:else if ruta.vista === 'traza'}
      <PantallaDeTraza />
    {:else if ruta.vista === 'importar' || ruta.vista === 'permisos' || ruta.vista === 'nuevaDelegacion'}
      <!-- Permisos e importar son de la superadministración: a otra persona la dirección directa no le abre nada. -->
      {#if ctx.capacidades.perfil !== 'superadministracion'}
        <EstadoVacio titulo={T.NO_DISPONIBLE_TITULO} detalle={T.NO_DISPONIBLE_CUERPO} prueba="seccion-no-disponible" />
      {:else if ruta.vista === 'importar'}
        <PantallaDeImportar onvolver={() => navegar({ vista: 'inicio' })} />
      {:else}
        <PantallaDePermisos nueva={ruta.vista === 'nuevaDelegacion'} onnueva={() => navegar({ vista: 'nuevaDelegacion' })} onpermisos={() => navegar({ vista: 'permisos' })} />
      {/if}
    {:else if ruta.vista === 'definicion'}
      {#key [ruta.definicion, ruta.ambito.proceso, ruta.ambito.actividad].join('|')}
        {#if ctx.datos.valores[ruta.definicion]?.definicion.clase === 'PARAMETRO'}
          <PantallaDeParametro
            definicion={ruta.definicion}
            ambito={ruta.ambito}
            pestana={ruta.pestana}
            onpestana={(p) => ruta.vista === 'definicion' && navegar({ ...ruta, pestana: p })}
            onambito={(a) => ruta.vista === 'definicion' && navegar({ ...ruta, ambito: a, pestana: 'valores' })}
            onvolver={() => navegar({ vista: 'inicio' })}
            onaprobaciones={() => navegar({ vista: 'aprobaciones' })}
            onverPermisos={ctx.capacidades.perfil === 'superadministracion' ? () => navegar({ vista: 'permisos' }) : null}
          />
        {:else}
          <PantallaDeLista
            definicion={ruta.definicion}
            ambito={ruta.ambito}
            pestana={ruta.pestana}
            onpestana={(p) => ruta.vista === 'definicion' && navegar({ ...ruta, pestana: p })}
            onambito={(a) => ruta.vista === 'definicion' && navegar({ ...ruta, ambito: a, pestana: 'valores' })}
            onvolver={() => navegar({ vista: 'inicio' })}
            onverPermisos={ctx.capacidades.perfil === 'superadministracion' ? () => navegar({ vista: 'permisos' }) : null}
          />
        {/if}
      {/key}
    {/if}
  </Marco>
{/if}
