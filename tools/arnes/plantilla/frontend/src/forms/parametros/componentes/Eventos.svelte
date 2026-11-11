<script lang="ts">
  /**
   * La línea de tiempo (`p04`, `p09`): cada eslabón como una frase de negocio con su antes → después y su
   * motivo. Solo lectura: la aplicación no ofrece editar ni borrar una entrada.
   */
  import Flecha from './Flecha.svelte';
  import type { EventoVM } from '../historial';
  import * as T from '../textos';
  import Chip from './Chip.svelte';

  interface Props {
    eventos: EventoVM[];
  }

  const { eventos }: Props = $props();
</script>

<ul class="eventos" data-testid="eventos">
  {#each eventos as e (e.clave)}
    <li>
      <time datetime={e.cuandoIso}>{e.cuando}</time>
      <div>
        <p class="que">
          {#if e.conQuien}<strong>{e.quien}</strong>{' '}{/if}{#each e.partes as p, i (i)}{#if p.t === 'fuerte'}<strong>{p.texto}</strong>{:else if p.t === 'cambio'}<span class="diff"><span class="antes">{p.antes}</span><span aria-hidden="true"><Flecha direccion="derecha" /></span><span class="despues">{p.despues}</span></span>{' '}{:else if p.t === 'chip'}{' '}<Chip tono={p.tono}>{p.texto}</Chip>{:else}{p.texto}{/if}{/each}
        </p>
        {#if e.motivo || e.origen}
          <p class="porque">
            {#if e.motivo}{T.MOTIVO_ROTULO}{' '}<strong>«{e.motivo}»</strong>{/if}{#if e.motivo && e.origen}{' · '}{/if}{e.origen}
          </p>
        {/if}
      </div>
    </li>
  {/each}
</ul>
