<script lang="ts">
  /**
   * «Así se verá en el formulario» (`p02-lista`): el widget REAL del cimiento que pintará el formulario
   * con esta lista, elegido por la regla de widget por defecto —fichas, desplegable o
   * autocompletar— y con los nombres que se están escribiendo. En cascada, primero el campo madre y
   * luego el de esta lista, con las opciones del padre elegido.
   */
  import Autocompletar from '$lib/ui/Autocompletar.svelte';
  import OpcionesEnFicha from '$lib/ui/OpcionesEnFicha.svelte';
  import Seleccion from '$lib/ui/Seleccion.svelte';
  import type { CampoDeVistaPrevia } from '../lista';
  import * as T from '../textos';

  interface Props {
    campos: CampoDeVistaPrevia[];
    /** Una nota bajo la vista previa (la regla de cuántas opciones, o «cambia mientras escribes»). */
    nota?: string;
  }

  const { campos, nota = T.VISTA_PREVIA_REGLA }: Props = $props();

  // La elección de la persona en la vista previa es solo de la vista previa: no se guarda en ninguna parte.
  let elegidas = $state<Record<string, string | null>>({});
  const valorDe = (c: CampoDeVistaPrevia): string | null => (c.id in elegidas ? elegidas[c.id] : c.elegida);
</script>

<div class="vista-previa" data-testid="vista-previa">
  <p class="rotulo">{T.VISTA_PREVIA}</p>
  {#each campos as c (c.id)}
    {#if c.widget === 'fichas'}
      <OpcionesEnFicha
        id={c.id}
        etiqueta={c.etiqueta}
        valor={valorDe(c)}
        opciones={c.opciones}
        disposicion="fila"
        obligatorio
      />
    {:else if c.widget === 'autocompletar'}
      <Autocompletar id={c.id} etiqueta={c.etiqueta} valor={valorDe(c)} opciones={c.opciones} obligatorio />
    {:else}
      <Seleccion id={c.id} etiqueta={c.etiqueta} valor={valorDe(c)} opciones={c.opciones} vacio={T.OPCION_VACIA} obligatorio />
    {/if}
  {/each}
  <p class="ayuda">{nota}</p>
</div>
