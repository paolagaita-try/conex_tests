<script lang="ts">
  /**
   * El contenedor de un parámetro: construye su modelo, valida el valor contra la definición y
   * convierte lo que la vista pide en peticiones al kit con la versión que leyó. En impacto alto el kit
   * responde con una propuesta (doble control); si OTRA persona propuso primero, responde un conflicto y
   * aquí se cuenta QUIÉN y CUÁNDO, sin perder lo que la persona había escrito.
   */
  import { onMount } from 'svelte';
  import { etiquetasDeOpciones } from '../usos';
  import { bien, mal, pedir, peticionDeValor, type Resultado } from '../acciones';
  import type { Ambito } from '../ambitos';
  import { usarAplicacion } from '../aplicacion';
  import { cargarDetalle } from '../detalle.svelte';
  import { cuando, valorLegible } from '../formatos';
  import { construirParametro, pendienteDe, valorPropuesto } from '../parametro';
  import type { PestanaDeDefinicion } from '../ruta';
  import { validarValor } from '../valores';
  import VistaParametro, { type ConflictoVM } from '../vistas/VistaParametro.svelte';
  import { explicar } from '../fallos';

  interface Props {
    definicion: string;
    ambito: Ambito;
    pestana: PestanaDeDefinicion;
    onpestana: (p: PestanaDeDefinicion) => void;
    onambito: (a: Ambito) => void;
    onvolver: () => void;
    onaprobaciones: () => void;
    onverPermisos?: (() => void) | null;
  }

  const props: Props = $props();
  const app = usarAplicacion();
  const ctx = $derived(app.contexto());

  let padreElegido = $state<string | null>(null);
  let conflicto = $state<ConflictoVM | null>(null);
  let reinicio = $state(0);

  const valores = $derived(ctx.datos.valores[props.definicion]);
  const padre = $derived(valores && valores.definicion.dependeDe !== '*' ? (ctx.datos.valores[valores.definicion.dependeDe] ?? null) : null);

  const detalle = cargarDetalle(app, () => props.definicion, () => ({ etiquetas: etiquetasDeOpciones(props.definicion, ctx.datos.valores, ctx.datos.definiciones.find((x) => x.codigo === props.definicion)?.dependeDe ?? '*'), inactivas: new Set<string>() }));

  const modelo = $derived(
    valores
      ? construirParametro({
          valores,
          padre,
          ambito: props.ambito,
          procesos: ctx.datos.procesos,
          capacidades: ctx.capacidades,
          editores: detalle.editores,
          pendientes: ctx.propuestas,
          nombres: { ...ctx.nombres, ...detalle.nombres },
          padreElegido,
        })
      : null,
  );

  onMount(() => {
    void app.releer(props.definicion);
    detalle.cargarTodo();
  });

  async function guardar(d: { valor: string; motivo: string }): Promise<Resultado> {
    if (!valores || !modelo) return bien();
    const r = await pedir(
      app.kit,
      peticionDeValor({ valores, ambito: props.ambito, codigoPadre: modelo.padreElegido, valor: d.valor, motivo: d.motivo }),
      ctx.sesion.usuario,
    );
    if (r.ok || r.explicacion.desconocido) {
      await app.refrescar(props.definicion);
      void detalle.recargarHistorial();
      void detalle.recargarUsos();
      return r;
    }
    if (r.conflicto) {
      // Alguien se adelantó: se vuelve a leer lo pendiente para contar su propuesta.
      await app.refrescar(props.definicion);
      const suya = pendienteDe(app.contexto().propuestas, props.definicion, props.ambito, modelo.padreElegido ?? '*');
      const quien = r.conflicto.por ? await app.kit.nombreDe(r.conflicto.por) : (modelo.pendiente?.quien ?? '');
      conflicto = {
        quien,
        cuando: r.conflicto.en ? cuando(r.conflicto.en) : '',
        antes: modelo.vigente,
        propuesto: suya ? valorLegible(valores.definicion, valorPropuesto(suya)) : '',
      };
    }
    return r;
  }

  async function retirar(): Promise<Resultado> {
    const propia = ctx.propuestas.find(
      (p) => p.estado === 'PENDIENTE' && p.esPropia && p.definicion === props.definicion && p.proceso === props.ambito.proceso && p.actividad === props.ambito.actividad && p.codigoPadre === (modelo?.padreElegido ?? '*'),
    );
    if (!propia) return mal({ campo: 'general', mensaje: explicar(null).mensaje });
    try {
      await app.kit.decidir(propia, 'RETIRAR', '');
    } catch (e) {
      const x = explicar(e, ctx.sesion.usuario);
      if (x.desconocido) await app.refrescar(props.definicion);
      return mal(x);
    }
    // Retirada: si leerlo de vuelta falla, `refrescar` lo avisa; la retirada no se convierte en error.
    await app.refrescar(props.definicion);
    void detalle.recargarHistorial();
    void detalle.recargarUsos();
    return bien();
  }
</script>

{#if modelo && valores}
  {#key reinicio}
    <VistaParametro
      parametro={modelo}
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
      {conflicto}
      onpestana={props.onpestana}
      onvolver={props.onvolver}
      onambito={props.onambito}
      onpadre={(c) => (padreElegido = c)}
      onperiodo={(p) => (detalle.periodo = p)}
      onmasHistorial={() => void detalle.masHistorial()}
      onexportarHistorial={() => detalle.exportar()}
      onaprobaciones={props.onaprobaciones}
      onverPermisos={props.onverPermisos}
      oncargarActual={() => {
        conflicto = null;
        reinicio = reinicio + 1;
      }}
      validar={(v) => validarValor(valores.definicion, v)}
      {guardar}
      {retirar}
    />
  {/key}
{/if}
