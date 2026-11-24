<script lang="ts">
  import logo from './trycore-logo.png';
  import { PRIORIDADES, valor, type ContextoPreventa, type DatosDelCaso } from './contexto';

  interface Props {
    titulo: string;
    etapa: string;
    hubspot: ContextoPreventa | null;
    caso: DatosDelCaso | null;
  }
  const { titulo, etapa, hubspot, caso }: Props = $props();

  const p = $derived(hubspot?.ticket.properties ?? {});
  const prioridad = $derived(p.hs_ticket_priority ? (PRIORIDADES[p.hs_ticket_priority] ?? p.hs_ticket_priority) : '—');
</script>

<header class="encabezado">
  <div class="barra">
    <img src={logo} alt="Trycore" class="logo" />
    <span class="etapa">{etapa}</span>
  </div>
  <div class="cuerpo">
    <p class="sobre">{titulo}</p>
    <h1>{hubspot ? valor(p.subject) : 'Cargando el ticket…'}</h1>
    <ul class="chips" aria-label="Resumen del ticket">
      <li><span>Ticket</span><strong>#{hubspot?.ticket.id ?? (caso?.ticketId as string | undefined) ?? '—'}</strong></li>
      <li data-prioridad={p.hs_ticket_priority ?? ''}><span>Prioridad</span><strong>{prioridad}</strong></li>
      <li><span>Consultora</span><strong>{valor(caso?.consultor)}</strong></li>
      <li><span>Estado</span><strong>{valor(caso?.estado ?? etapa)}</strong></li>
    </ul>
  </div>
</header>

<style>
  .encabezado {
    border-radius: var(--tc-radio);
    overflow: hidden;
    background: linear-gradient(135deg, #000c4c 0%, #0b1a6b 70%, #08306e 100%);
    color: #fff;
    box-shadow: var(--tc-sombra);
    position: relative;
  }
  .encabezado::after {
    content: '';
    position: absolute;
    inset: auto -4rem -6rem auto;
    inline-size: 16rem;
    block-size: 16rem;
    border-radius: 50%;
    background: radial-gradient(circle, rgb(0 204 192 / 0.35), transparent 70%);
    pointer-events: none;
  }
  .barra {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1.5rem;
    background: #fff;
    border-block-end: 3px solid var(--tc-turquesa);
  }
  .logo {
    block-size: 2rem;
    inline-size: auto;
  }
  .etapa {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--tc-marino);
    background: var(--tc-turquesa-suave);
    border: 1px solid #7fe3dc;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
  }
  .cuerpo {
    padding: 1.25rem 1.5rem 1.5rem;
    position: relative;
    z-index: 1;
  }
  .sobre {
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.75rem;
    font-weight: 600;
    color: #8ff0ea;
  }
  h1 {
    margin: 0.25rem 0 1rem;
    font-size: clamp(1.3rem, 2.5vw, 1.75rem);
    line-height: 1.25;
  }
  .chips {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
  }
  .chips li {
    background: rgb(255 255 255 / 0.1);
    border: 1px solid rgb(255 255 255 / 0.22);
    border-radius: 10px;
    padding: 0.4rem 0.8rem;
    display: grid;
    min-inline-size: 7rem;
  }
  .chips span {
    font-size: 0.72rem;
    color: #c9d0ec;
  }
  .chips strong {
    font-size: 0.95rem;
  }
  li[data-prioridad='HIGH'] {
    border-color: #ff9c94;
  }
</style>
