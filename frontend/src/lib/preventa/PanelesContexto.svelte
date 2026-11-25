<script lang="ts">
  /** Paneles de SOLO LECTURA con todo lo que trae `preventa/contexto`, en secciones plegables. */
  import { etiquetaDe, fecha, nombreDe, valor, type ContextoPreventa, type ObjetoHubspot } from './contexto';

  interface Props {
    hubspot: ContextoPreventa | null;
    fallo?: string | null;
  }
  const { hubspot, fallo = null }: Props = $props();

  function filas(o: ObjetoHubspot | null, ocultar: string[] = []): [string, string][] {
    if (!o) return [];
    return Object.entries(o.properties)
      .filter(([k, v]) => !ocultar.includes(k) && v !== null && v !== '')
      .map(([k, v]) => [etiquetaDe(k), fecha(v)]);
  }
  function monto(o: ObjetoHubspot | null): string {
    const a = o?.properties.amount;
    if (!a) return '—';
    const n = Number(a);
    const moneda = o?.properties.deal_currency_code ?? 'COP';
    try {
      return Number.isNaN(n) ? a : n.toLocaleString('es-CO', { style: 'currency', currency: moneda, maximumFractionDigits: 0 });
    } catch {
      return a;
    }
  }
</script>

<section class="tc-tarjeta paneles" aria-labelledby="titulo-contexto" aria-busy={!hubspot && !fallo}>
  <h2 id="titulo-contexto">Información del caso <span class="lectura">Solo lectura</span></h2>
  {#if fallo}
    <p class="tc-aviso tc-aviso--error" role="alert"><strong>No se pudo cargar la información de HubSpot</strong>{fallo}</p>
  {:else if !hubspot}
    <div class="esqueleto" aria-label="Cargando la información del caso"><span></span><span></span><span></span></div>
  {:else}
    <details open data-panel="ticket">
      <summary>Ticket</summary>
      {#if hubspot.ticket.properties.content}<p class="descripcion">{hubspot.ticket.properties.content}</p>{/if}
      <dl>
        {#each filas(hubspot.ticket, ['subject', 'content']) as [k, v] (k)}<div><dt>{k}</dt><dd>{v}</dd></div>{/each}
      </dl>
    </details>
    <details open data-panel="negocio">
      <summary>Negocio</summary>
      {#if hubspot.deal}
        <div class="destacado">
          <span>{valor(hubspot.deal.properties.dealname)}</span><strong>{monto(hubspot.deal)}</strong>
        </div>
        <dl>
          {#each filas(hubspot.deal, ['dealname', 'amount', 'deal_currency_code']) as [k, v] (k)}<div><dt>{k}</dt><dd>{v}</dd></div>{/each}
        </dl>
      {:else}<p class="vacio">El ticket no tiene un negocio asociado.</p>{/if}
    </details>
    <details data-panel="empresa">
      <summary>Empresa</summary>
      {#if hubspot.company}
        <dl>{#each filas(hubspot.company) as [k, v] (k)}<div><dt>{k}</dt><dd>{v}</dd></div>{/each}</dl>
      {:else}<p class="vacio">Sin empresa asociada.</p>{/if}
    </details>
    <details data-panel="contactos">
      <summary>Contactos <span class="cuenta">{hubspot.contacts.length}</span></summary>
      {#if hubspot.contacts.length === 0}<p class="vacio">Sin contactos asociados.</p>{/if}
      <ul class="contactos">
        {#each hubspot.contacts as c (c.id)}
          {@const q = c.properties}
          <li>
            <span class="avatar" aria-hidden="true">{(q.firstname ?? '?').charAt(0)}{(q.lastname ?? '').charAt(0)}</span>
            <div>
              <strong>{nombreDe({ firstName: q.firstname, lastName: q.lastname })}</strong>
              <span>{valor(q.jobtitle)}</span>
              {#if q.email}<a href={`mailto:${q.email}`}>{q.email}</a>{/if}
              {#if q.phone}<span>{q.phone}</span>{/if}
            </div>
          </li>
        {/each}
      </ul>
    </details>
    <details data-panel="comercial">
      <summary>Comercial (owner)</summary>
      <dl>
        <div><dt>Nombre</dt><dd>{nombreDe(hubspot.owner)}</dd></div>
        <div><dt>Correo</dt><dd>{valor(hubspot.owner?.email)}</dd></div>
      </dl>
    </details>
  {/if}
</section>

<style>
  .lectura {
    margin-inline-start: auto;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--tc-turquesa-texto);
    background: var(--tc-turquesa-suave);
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
  }
  details {
    border: 1px solid var(--tc-borde);
    border-radius: 12px;
    margin-block-end: 0.75rem;
    background: #fbfcfe;
  }
  summary {
    cursor: pointer;
    padding: 0.75rem 1rem;
    font-weight: 600;
    color: var(--tc-marino);
    list-style: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  summary::after {
    content: '▾';
    margin-inline-start: auto;
    transition: transform 0.2s;
    color: var(--tc-turquesa-texto);
  }
  details:not([open]) summary::after {
    transform: rotate(-90deg);
  }
  details > :not(summary) {
    margin-inline: 1rem;
  }
  dl {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
    gap: 0.6rem 1rem;
    margin-block: 0 1rem;
  }
  dl div {
    min-inline-size: 0;
  }
  dt {
    font-size: 0.75rem;
    color: var(--tc-texto-suave);
  }
  dd {
    margin: 0;
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  .descripcion {
    background: #fff;
    border-inline-start: 3px solid var(--tc-turquesa);
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    margin-block: 0 0.75rem;
  }
  .destacado {
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
    background: var(--color-primario-suave);
    border-radius: 10px;
    padding: 0.6rem 0.8rem;
    margin-block-end: 0.75rem;
  }
  .destacado strong {
    color: var(--tc-marino);
  }
  .cuenta {
    background: var(--tc-marino);
    color: #fff;
    border-radius: 999px;
    font-size: 0.72rem;
    padding: 0 0.5rem;
  }
  .contactos {
    list-style: none;
    padding: 0;
    display: grid;
    gap: 0.6rem;
    margin-block: 0 1rem;
  }
  .contactos li {
    display: flex;
    gap: 0.75rem;
    background: #fff;
    border: 1px solid var(--tc-borde);
    border-radius: 10px;
    padding: 0.6rem 0.75rem;
  }
  .contactos div {
    display: grid;
    font-size: 0.88rem;
    min-inline-size: 0;
  }
  .contactos a {
    color: var(--tc-marino-2);
    overflow-wrap: anywhere;
  }
  .avatar {
    flex: none;
    inline-size: 2.4rem;
    block-size: 2.4rem;
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-weight: 700;
    color: var(--tc-marino);
    background: var(--tc-turquesa-suave);
    border: 2px solid var(--tc-turquesa);
  }
  .vacio {
    color: var(--tc-texto-suave);
    font-style: italic;
  }
  .esqueleto {
    display: grid;
    gap: 0.6rem;
  }
  .esqueleto span {
    block-size: 2.6rem;
    border-radius: 10px;
    background: linear-gradient(90deg, #eef1f8, #f8f9fc, #eef1f8);
    background-size: 200% 100%;
    animation: brillo 1.2s infinite;
  }
  @keyframes brillo {
    to {
      background-position: -200% 0;
    }
  }
</style>
