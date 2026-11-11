<script lang="ts">
  /**
   * Una flecha DECORATIVA como dibujo, no como letra: una flecha escrita («→», «←», «↑», «↓») es un texto de un solo
   * carácter y axe no puede decidir su contraste (queda «sin decidir»); un trazo en `currentColor` no es texto y
   * hereda el color del contexto. Siempre `aria-hidden`: el sentido lo dice el texto de al lado.
   */
  interface Props {
    direccion?: 'derecha' | 'izquierda' | 'arriba' | 'abajo';
  }
  const { direccion = 'derecha' }: Props = $props();
  const giro = $derived({ derecha: 0, abajo: 90, izquierda: 180, arriba: 270 }[direccion]);
</script>

<svg class="flecha-icono" viewBox="0 0 16 16" aria-hidden="true" focusable="false" style:transform="rotate({giro}deg)">
  <path d="M2 8h11M9 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
</svg>
