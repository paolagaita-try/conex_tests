<script lang="ts">
  /** Vista del caso (`frm_overview`): resumen, línea de tiempo y la información de HubSpot, todo de solo lectura. */
  import { leerContexto } from '$lib/bonita/contexto';
  import Encabezado from '$lib/preventa/Encabezado.svelte';
  import PanelesContexto from '$lib/preventa/PanelesContexto.svelte';
  import { fecha, precargar, valor, type Precarga } from '$lib/preventa/contexto';
  import { TEXTOS } from './textos';

  interface Hito {
    titulo: string;
    detalle: string;
    fecha: string | null;
    estado: 'hecho' | 'actual' | 'pendiente';
  }
  interface Props {
    cargar?: () => Promise<Precarga>;
  }

  const contexto = leerContexto();
  const { cargar = () => precargar(contexto) }: Props = $props();

  let datos = $state<Precarga | null>(null);
  let falloLectura = $state<string | null>(null);
  cargar().then(
    (d) => (datos = d),
    (e: unknown) => (falloLectura = e instanceof Error ? e.message : TEXTOS.errorGenerico),
  );

  const RESULTADOS: Record<string, string> = {
    viable: 'Viable: pasa a diseño',
    bloqueado: 'Bloqueado: en espera información del lead',
    'no viable': 'No viable: cerrado por viabilidad',
  };

  /** Los hitos del caso, deducidos del objeto Preventa y del ticket. */
  function hitos(d: Precarga): Hito[] {
    const c = d.caso;
    const r = typeof c.resultadoValidacion === 'string' ? c.resultadoValidacion : null;
    const propuesta = typeof c.fechaPropuesta === 'string' ? c.fechaPropuesta : null;
    const lista: Hito[] = [
      { titulo: 'Ticket creado en HubSpot', detalle: valor(d.hubspot.ticket.properties.source_type), fecha: d.hubspot.ticket.properties.createdate ?? null, estado: 'hecho' },
      { titulo: 'Caso asignado', detalle: `Consultora: ${valor(c.consultor)}`, fecha: (c.fechaAsignacion as string) ?? null, estado: c.consultor ? 'hecho' : 'actual' },
      { titulo: 'Validación de la solicitud', detalle: r ? (RESULTADOS[r] ?? r) : 'Pendiente', fecha: (c.fechaValidacion as string) ?? null, estado: r ? 'hecho' : c.consultor ? 'actual' : 'pendiente' },
    ];
    if (r !== 'no viable') {
      lista.push({ titulo: 'Diseño de la propuesta', detalle: propuesta ? 'Artefactos entregados' : r === 'viable' ? 'En curso' : 'Pendiente', fecha: propuesta, estado: propuesta ? 'hecho' : r === 'viable' ? 'actual' : 'pendiente' });
    }
    return lista;
  }
</script>

<main class="tc-pagina" data-formulario="caso">
  <Encabezado titulo={TEXTOS.titulo} etapa="Vista del caso" hubspot={datos?.hubspot ?? null} caso={datos?.caso ?? null} />
  <div class="tc-rejilla">
    <section class="tc-tarjeta" aria-labelledby="titulo-linea">
      <h2 id="titulo-linea">Línea de tiempo del caso</h2>
      {#if datos}
        <ol class="linea">
          {#each hitos(datos) as h (h.titulo)}
            <li data-estado={h.estado}>
              <span class="punto" aria-hidden="true"></span>
              <div>
                <strong>{h.titulo}</strong>
                <span class="tc-sr">({h.estado === 'hecho' ? 'completado' : h.estado === 'actual' ? 'en curso' : 'pendiente'})</span>
                <p>{h.detalle}</p>
                {#if h.fecha}<time datetime={h.fecha}>{fecha(h.fecha)}</time>{/if}
              </div>
            </li>
          {/each}
        </ol>
      {:else if !falloLectura}
        <p aria-busy="true">{TEXTOS.cargando}</p>
      {/if}
    </section>
    <PanelesContexto hubspot={datos?.hubspot ?? null} fallo={falloLectura} />
  </div>
</main>

<style>
  .linea {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .linea li {
    display: flex;
    gap: 1rem;
    position: relative;
    padding-block-end: 1.25rem;
  }
  .linea li:not(:last-child)::before {
    content: '';
    position: absolute;
    inset-inline-start: 0.55rem;
    inset-block: 1.4rem 0;
    inline-size: 2px;
    background: var(--tc-borde);
  }
  .linea li[data-estado='hecho']:not(:last-child)::before {
    background: var(--tc-turquesa);
  }
  .punto {
    flex: none;
    inline-size: 1.15rem;
    block-size: 1.15rem;
    border-radius: 50%;
    margin-block-start: 0.15rem;
    border: 3px solid var(--tc-borde);
    background: #fff;
  }
  [data-estado='hecho'] .punto {
    background: var(--tc-turquesa);
    border-color: var(--tc-turquesa);
  }
  [data-estado='actual'] .punto {
    border-color: var(--tc-marino);
    box-shadow: 0 0 0 4px rgb(0 204 192 / 0.35);
  }
  .linea p {
    margin: 0.1rem 0;
    color: var(--tc-texto-suave);
    font-size: 0.9rem;
  }
  time {
    font-size: 0.8rem;
    color: var(--tc-turquesa-texto);
    font-weight: 600;
  }
  [data-estado='pendiente'] strong {
    color: var(--tc-texto-suave);
  }
</style>
