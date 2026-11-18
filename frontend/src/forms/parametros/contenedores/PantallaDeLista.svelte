<script lang="ts">
  /**
   * El contenedor de una lista: lee lo que la vista necesita (los editores, los usos, el
   * historial), construye el modelo y convierte lo que la vista pide en peticiones al kit con la versión
   * que leyó. Tras cada escritura aplicada refresca la lista y el contador de lo pendiente.
   */
  import { onMount } from 'svelte';
  import { etiquetasDeOpciones } from '../usos';
  import { acciones as accionesDeLista } from '../acciones-de-lista';
  import { type Ambito } from '../ambitos';
  import { usarAplicacion } from '../aplicacion';
  import { cargarDetalle } from '../detalle.svelte';
  import { construirLista } from '../lista';
  import type { PestanaDeDefinicion } from '../ruta';
  import VistaLista from '../vistas/VistaLista.svelte';

  interface Props {
    definicion: string;
    ambito: Ambito;
    pestana: PestanaDeDefinicion;
    onpestana: (p: PestanaDeDefinicion) => void;
    onambito: (a: Ambito) => void;
    onvolver: () => void;
    onverPermisos?: (() => void) | null;
  }

  const props: Props = $props();
  const app = usarAplicacion();
  const ctx = $derived(app.contexto());

  let padreElegido = $state<string | null>(null);

  const valores = $derived(ctx.datos.valores[props.definicion]);
  const padre = $derived(valores && valores.definicion.dependeDe !== '*' ? (ctx.datos.valores[valores.definicion.dependeDe] ?? null) : null);

  const detalle = cargarDetalle(app, () => props.definicion, () => {
    const filas = valores?.filas ?? [];
    return {
      etiquetas: etiquetasDeOpciones(props.definicion, ctx.datos.valores, ctx.datos.definiciones.find((x) => x.codigo === props.definicion)?.dependeDe ?? '*'),
      inactivas: new Set(filas.filter((f) => !f.activo).map((f) => f.codigo)),
    };
  });

  const lista = $derived(
    valores
      ? construirLista({
          valores,
          padre,
          ambito: props.ambito,
          procesos: ctx.datos.procesos,
          capacidades: ctx.capacidades,
          editores: detalle.editores,
          nombres: { ...ctx.nombres, ...detalle.nombres },
          padreElegido,
        })
      : null,
  );

  onMount(() => {
    void app.releer(props.definicion);
    detalle.cargarTodo();
  });

  const ejecutar = () =>
    accionesDeLista(
      app.kit,
      () => (valores ? { valores, ambito: props.ambito, padre: lista?.padreElegido ?? null } : null),
      app.refrescar,
      // Tras escribir cambian el historial Y «Dónde se usa» (opciones activas/inactivas, nombres, cifras): se releen los dos.
      async () => {
        void detalle.recargarUsos();
        await detalle.recargarHistorial();
      },
      ctx.sesion.usuario,
    );
</script>

{#if lista}
  <VistaLista
    {lista}
    pestana={props.pestana}
    usos={detalle.usos}
    eventos={detalle.eventos}
    periodo={detalle.periodo}
    cadena={detalle.cadena}
    cadenaFallo={detalle.cadenaFallo}
    topeDeLectura={detalle.topeAlcanzado}
    cadenaRota={detalle.cadenaRota}
    editoresFallo={detalle.editoresFallo}
    onreintentarEditores={() => void detalle.reintentarEditores()}
    onreintentarUsos={() => void detalle.reintentarUsos()}
    onreintentarHistorial={() => void detalle.recargarHistorial()}
    hayMasHistorial={detalle.hayMas}
    ultimaModificacion={detalle.ultima}
    onpestana={props.onpestana}
    onvolver={props.onvolver}
    onambito={props.onambito}
    onpadre={(c) => (padreElegido = c)}
    onperiodo={(p) => (detalle.periodo = p)}
    onmasHistorial={() => void detalle.masHistorial()}
    onexportarHistorial={() => detalle.exportar()}
    onverPermisos={props.onverPermisos}
    guardarEdicion={(d) => ejecutar().editar(d)}
    anadir={(d) => ejecutar().anadir(d)}
    cambiarEstado={(d) => ejecutar().cambiarEstado(d)}
    guardarOrden={(d) => ejecutar().ordenar(d)}
    versionPropia={(m) => ejecutar().versionPropia(m)}
    volverAHeredar={(m) => ejecutar().volverAHeredar(m)}
  />
{/if}
