<script lang="ts">
  /**
   * El contenedor de Aprobaciones: lee TODAS las propuestas (pendientes y resueltas), arma el modelo
   * y convierte «aprobar», «rechazar» o «retirar» en la orden al kit con la versión de la propuesta que leyó.
   * Tras decidir, vuelve a leer y refresca la definición afectada y el contador de la pestaña.
   */
  import { onMount, untrack } from 'svelte';
  import { SvelteMap } from 'svelte/reactivity';
  import { etiquetasDeOpciones, usosVM, type UsosVM } from '../usos';
  import { bien, mal, type Resultado } from '../acciones';
  import { usarAplicacion } from '../aplicacion';
  import { construirAprobaciones, type SujetosPorId } from '../aprobaciones';
  import { completarSujetos, idsDeSujetos, propuestasDe } from '../carga';
  import { explicar } from '../fallos';
  import type { Propuesta } from '../tipos';
  import * as T from '../textos';
  import ErrorDeLectura from '../componentes/ErrorDeLectura.svelte';
  import VistaAprobaciones from '../vistas/VistaAprobaciones.svelte';
  import { propuestaVM } from '../aprobaciones';

  const app = usarAplicacion();
  const ctx = $derived(app.contexto());

  let propuestas = $state<Propuesta[] | 'cargando' | 'error'>('cargando');
  let seleccionada = $state<string | null>(null);
  let nombres = $state<Record<string, string>>({});

  async function cargar(trasEscritura = false): Promise<void> {
    try {
      await leer();
      app.avisarRefresco('propuestas', null);
    } catch {
      // Tras una escritura la lista vieja se conserva y se avisa; al abrir, no hay nada que conservar: error.
      if (trasEscritura && propuestas !== 'cargando' && propuestas !== 'error') app.avisarRefresco('propuestas', () => cargar(true));
      else propuestas = 'error';
    }
  }
  async function leer(): Promise<void> {
    // TODAS las pendientes (páginas) y, aparte, lo resuelto reciente: con >100 propuestas la primera página sola esconde pendientes.
    const [pendientes, aprobadas, rechazadas, retiradas] = await Promise.all([
      propuestasDe(app.kit, 'PENDIENTE'),
      app.kit.propuestas('APROBADA', 0),
      app.kit.propuestas('RECHAZADA', 0),
      app.kit.propuestas('RETIRADA', 0),
    ]);
    const lista = { propuestas: [...pendientes.propuestas, ...aprobadas.propuestas, ...rechazadas.propuestas, ...retiradas.propuestas] };
    if (ctx.capacidades.perfil === 'superadministracion') {
      const datos = lista.propuestas.filter((p) => p.accion === 'DELEGAR').map((p) => p.valorPropuesto.datos as Record<string, unknown>);
      await completarSujetos(app.kit, ctx.sujetos, idsDeSujetos(datos));
    }
    const usuarios = [...new Set([ctx.sesion.usuario, ...lista.propuestas.flatMap((p) => [p.proponente, p.aprobador ?? ''])])].filter(Boolean);
    const n: Record<string, string> = {};
    await Promise.all(usuarios.map(async (u) => { n[u] = await app.kit.nombreDe(u); }));
    nombres = n;
    propuestas = lista.propuestas;
  }

  onMount(() => void cargar());

  /** Dónde se usa cada definición con propuestas (`GET parametros/usos`): una lectura por definición, no por clic. `Map`: un código como `constructor` no es una clave heredada. */
  const usos = new SvelteMap<string, UsosVM | 'cargando' | 'error'>();
  const lecturaDeUsos = new Map<string, number>();
  function leerUsosDe(d: string): void {
    const esta = (lecturaDeUsos.get(d) ?? 0) + 1;
    lecturaDeUsos.set(d, esta);
    usos.set(d, 'cargando'); // mientras lee, ni cifras viejas ni «0»
    void app.kit.usos(d).then(
      (u) => { if (esta === lecturaDeUsos.get(d)) usos.set(d, usosVM(u, etiquetasDe(d), new Set())); },
      () => { if (esta === lecturaDeUsos.get(d)) usos.set(d, 'error'); },
    );
  }
  $effect(() => {
    if (propuestas === 'cargando' || propuestas === 'error') return;
    const pendientes = [...new Set(propuestas.filter((p) => p.accion !== 'DELEGAR').map((p) => p.definicion))].filter((d) => d !== '*' && d !== '' && !untrack(() => usos.has(d)));
    for (const d of pendientes) leerUsosDe(d);
  });
  const usosDeLa = (d: string): UsosVM | 'cargando' | 'error' | null => usos.get(d) ?? null;
  const etiquetasDe = (d: string): ReadonlyMap<string, string> => etiquetasDeOpciones(d, ctx.datos.valores, ctx.datos.definiciones.find((x) => x.codigo === d)?.dependeDe ?? '*');

  const vacio: SujetosPorId = { usuario: [], grupo: [], rol: [] };
  const modelo = $derived(
    propuestas === 'cargando' || propuestas === 'error'
      ? null
      : construirAprobaciones(propuestas, ctx.datos.definiciones, { ...ctx.nombres, ...nombres }, ctx.sujetos ?? vacio),
  );

  async function decidir(d: { clave: string; decision: 'APROBAR' | 'RECHAZAR' | 'RETIRAR'; comentario: string }): Promise<Resultado> {
    if (propuestas === 'cargando' || propuestas === 'error') return bien();
    const cruda = propuestas.find((p) => propuestaVM(p, ctx.datos.definiciones, nombres, ctx.sujetos ?? vacio, new Date()).clave === d.clave);
    if (!cruda) return mal({ campo: 'general', mensaje: explicar(null).mensaje });
    try {
      await app.kit.decidir(cruda, d.decision, d.comentario.trim());
    } catch (e) {
      const x = explicar(e, ctx.sesion.usuario);
      if (x.desconocido) {
        await cargar(true);
        await app.refrescar('');
      }
      return mal(x);
    }
    await cargar(true);
    // Una decisión cambia lo que se usa (un valor aplicado, una opción activa): lo leído antes puede estar viejo.
    for (const d of [...usos.keys()]) leerUsosDe(d);
    if (cruda.definicion !== '*' && ctx.datos.valores[cruda.definicion]) await app.refrescar(cruda.definicion);
    else await app.refrescar('');
    return bien();
  }
</script>

{#if propuestas === 'error'}
  <ErrorDeLectura onreintentar={() => void cargar()} prueba="aprobaciones-error" />
{:else if modelo}
  <VistaAprobaciones aprobaciones={modelo} usosDe={usosDeLa} {seleccionada} onseleccionar={(c) => (seleccionada = c)} {decidir} />
{:else}
  <p role="status">{T.CARGANDO}</p>
{/if}
