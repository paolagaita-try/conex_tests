<script lang="ts">
  /**
   * Devuelve el «submit implícito» a un formulario cuya barra de acciones vive fuera de él.
   *
   * El navegador solo envía con Enter si el formulario tiene un botón de envío **dentro**. Cuando
   * la barra es el pie del área de trabajo —está fuera de la rejilla, y por tanto fuera del
   * `<form>`—, así que Enter deja de hacer nada. Lo midió una verificación adversarial.
   *
   * Es un botón sin texto y `hidden`: no añade superficie de lectura, no entra en el recorrido de
   * foco, y quien lo dispara es el mismo `onsubmit` de siempre — el punto único donde vive la
   * intercepción de lo grave. Vive en el cimiento y no en cada pantalla porque ahí el
   * literal `type="submit"` sería texto escrito a mano, que las pantallas tienen prohibido.
   */
</script>

<!-- `input` y no `button`: un botón sin texto dispara el aviso de accesibilidad de Svelte, y
     ponerle rótulo sería inventar una superficie de lectura para algo que nadie ve. Un `input`
     `hidden` hace el mismo trabajo (devolver el submit implícito) sin anunciarse. -->
<input type="submit" hidden />
