<script lang="ts">
  /**
   * El contenedor de la traza: lee las páginas más recientes de la cadena completa, las cuenta en
   * frases de negocio y, si la persona es de la superadministración, verifica la cadena a petición.
   */
  import { onMount } from 'svelte';
  import { usarAplicacion } from '../aplicacion';
  import { aCsv, descargar } from '../csv';
  import { completarSujetos, idsDeSujetos } from '../carga';
  import { delegacionesDe, eventoDeTraza, usuariosDeLaEntrada, type EventoVM } from '../historial';
  import { recuentoDe } from '$lib/bonita/marcas';
  import * as T from '../textos';
  import { filtrar, resultadoDeVerificacion, SIN_FILTROS, type FiltrosDeLaVista, type ResultadoDeVerificacion } from '../traza';
  import type { EntradaDeTraza } from '../tipos';
  import VistaTraza from '../vistas/VistaTraza.svelte';

  const app = usarAplicacion();
  const ctx = $derived(app.contexto());

  let entradas = $state<EntradaDeTraza[] | 'cargando' | 'error'>('cargando');
  let siguiente = $state(0);
  let hayMas = $state(false);
  let filtros = $state<FiltrosDeLaVista>(SIN_FILTROS);
  let verificacion = $state<ResultadoDeVerificacion | 'verificando' | 'error' | null>(null);
  let hayMasFallo = $state(false);
  let nombres = $state<Record<string, string>>({});
  let avisoDeExportacion = $state<string | null>(null);

  /** Etiqueta de persona → usuario (login) que se manda al servidor: la identidad, no el nombre que se ve. */
  const registro = new Map<string, string>();
  async function buscarPersonas(q: string): Promise<string[]> {
    const r = await app.kit.organizacion('usuario', q);
    const con = await Promise.all(r.map(async (x) => ({ login: x.nombre, nombre: await app.kit.nombreDe(x.nombre) })));
    return con.map((x) => {
      const etiqueta = x.nombre === x.login ? x.login : `${x.nombre} · ${x.login}`;
      registro.set(etiqueta, x.login);
      return etiqueta;
    });
  }

  /** Lo que el SERVIDOR filtra (persona y fechas): filtrar aquí solo sobre las 100 entradas cargadas diría «ninguna» sin saberlo. */
  function filtrosDelServidor() {
    return {
      ...(filtros.persona !== '' && registro.has(filtros.persona) ? { usuario: registro.get(filtros.persona) } : {}),
      ...(filtros.desde !== '' ? { desde: `${filtros.desde}T00:00:00.000Z` } : {}),
      ...(filtros.hasta !== '' ? { hasta: `${filtros.hasta}T23:59:59.999Z` } : {}),
    };
  }

  const MAXIMO_DE_PAGINAS = 10;
  let paginasLeidas = $state(0);
  let quedaMas = $state(false);

  async function cargar(mas: boolean): Promise<void> {
    hayMasFallo = false;
    try {
      const r = await app.kit.traza(filtrosDelServidor(), mas ? siguiente : 0);
      const previas = mas && entradas !== 'cargando' && entradas !== 'error' ? entradas : [];
      if (ctx.capacidades.perfil === 'superadministracion') await completarSujetos(app.kit, ctx.sujetos, idsDeSujetos(delegacionesDe(r.elementos)));
      entradas = [...previas, ...r.elementos];
      siguiente = (mas ? siguiente : 0) + 1;
      paginasLeidas = mas ? paginasLeidas + 1 : 1;
      quedaMas = r.hayMas; // el servidor tiene más, aunque ya no se pidan (tope de páginas)
      hayMas = r.hayMas && paginasLeidas < MAXIMO_DE_PAGINAS;
      const faltan = [...new Set(r.elementos.flatMap(usuariosDeLaEntrada))].filter((u) => !(u in nombres) && !(u in ctx.nombres));
      const nuevos: Record<string, string> = {};
      await Promise.all(faltan.map(async (u) => { nuevos[u] = await app.kit.nombreDe(u); }));
      nombres = { ...nombres, ...nuevos };
    } catch {
      if (!mas || entradas === 'cargando') entradas = 'error';
      else hayMasFallo = true;
      return;
    }
    // Un filtro local (lista, acción) sobre pocas entradas cargadas no puede decir «ninguna» mientras queden páginas: sigue leyendo.
    while (hayMas && !hayMasFallo && (filtros.lista !== '' || filtros.accion !== 'todas') && visiblesAhora().length < 25) await cargarSiguiente();
  }
  const cargarSiguiente = () => cargar(true);
  const visiblesAhora = (): EventoVM[] => (eventos === 'cargando' || eventos === 'error' ? [] : filtrar(eventos, filtros));

  function alCambiarFiltros(f: FiltrosDeLaVista): void {
    const antes = filtros;
    filtros = f;
    avisoDeExportacion = null;
    // Persona y fechas se piden al servidor: cambian lo que hay que leer. Lista y acción filtran lo ya leído (y siguen leyendo si hace falta).
    if (antes.persona !== f.persona || antes.desde !== f.desde || antes.hasta !== f.hasta) void cargar(false);
    else if (antes.lista !== f.lista || antes.accion !== f.accion) void (async () => { while (hayMas && visiblesAhora().length < 25) await cargarSiguiente(); })();
  }
  onMount(() => void cargar(false));

  const eventos = $derived<EventoVM[] | 'cargando' | 'error'>(
    entradas === 'cargando' || entradas === 'error' ? entradas : entradas.map((e) => eventoDeTraza(e, { nombres: { ...ctx.nombres, ...nombres }, definiciones: ctx.datos.definiciones, sujetos: ctx.sujetos })),
  );

  async function verificar(): Promise<void> {
    verificacion = 'verificando';
    try {
      verificacion = resultadoDeVerificacion(await app.kit.verificar(true), (c) => ctx.datos.definiciones.find((d) => d.codigo === c)?.nombre ?? T.UNA_DEFINICION);
    } catch {
      verificacion = 'error';
    }
  }

  async function exportar(): Promise<void> {
    // Todo lo filtrado: se terminan de leer las páginas que falten (hasta el tope) y se dice exactamente cuánto se exporta.
    while (hayMas && !hayMasFallo) await cargarSiguiente();
    const visibles = visiblesAhora();
    descargar(T.NOMBRE_DEL_FICHERO_DE_TRAZA, aCsv(T.COLUMNAS_DE_HISTORIAL, visibles.map((e) => [e.cuando, e.quien, e.texto, e.cambio, e.motivo])));
    avisoDeExportacion = quedaMas || hayMasFallo ? T.exportoParcial(recuentoDe(visibles)) : null;
  }
</script>

<VistaTraza
  {eventos}
  puedeVerificar={ctx.capacidades.perfil === 'superadministracion'}
  {verificacion}
  {hayMas}
  {quedaMas}
  {hayMasFallo}
  onreintentar={() => void cargar(false)}
  {filtros}
  {buscarPersonas}
  {avisoDeExportacion}
  onfiltros={alCambiarFiltros}
  onverificar={() => void verificar()}
  onmas={() => void cargar(true)}
  onexportar={() => void exportar()}
/>
