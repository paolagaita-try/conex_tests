<script lang="ts">
  /**
   * Página semilla de la capa de formularios.
   *
   * NO es una pantalla de negocio y es deliberadamente desechable. Su único trabajo es
   * demostrar, con la salida real observable, que el circuito completo funciona:
   *
   *   1. el paquete construido se sirve como custom page (los recursos cargan con
   *      rutas relativas bajo /bonita/portal/resource/...),
   *   2. la sesión del portal se reconoce sin manejar credenciales,
   *   3. la API REST responde,
   *   4. el contexto de la tarea llega por la dirección con la que abre el portal,
   *   5. si hay tarea, su contrato se puede leer — que es la frontera real del
   *      formulario con el motor —,
   *   6. y la tarea se puede ejecutar con un cuerpo construido desde ese contrato.
   */
  import { estaEnMarcoDeBonita, estaServidoPorBonita } from '$lib/bonita/config';
  import { leerContexto } from '$lib/bonita/contexto';
  import {
    autenticarEnDesarrollo,
    contratoDeTarea,
    ejecutarTarea,
    haySesion,
  } from '$lib/bonita/cliente';
  import type { Contrato, EntradaDeContrato } from '$lib/bonita/tipos';

  /**
   * El texto de un fallo: su mensaje, si lo trae. Lo que se lanza sin tipo no se convierte a texto:
   * podría ser un número, y `String(e)` lo pintaría.
   */
  function textoDelFallo(e: unknown): string {
    if (e instanceof Error) return e.message;
    return typeof e === 'string' ? e : 'fallo sin mensaje';
  }

  const contexto = leerContexto();
  const servidoPorBonita = estaServidoPorBonita();
  const enMarco = estaEnMarcoDeBonita();

  let sesion = $state<boolean | null>(null);
  let contrato = $state<Contrato | null>(null);
  let error = $state<string | null>(null);
  let listo = $state(false);

  /**
   * Punto de integración que se ejercita aquí **con los módulos reales del front**, no con
   * `fetch` a mano: «el front ejecuta la tarea por contrato». Esperar a una pantalla de negocio
   * para verlo funcionar dejaría todos los formularios construidos sobre un circuito que nadie
   * había observado.
   */
  let ejecucion = $state<{ estado: 'ocioso' | 'enviando' | 'ok' | 'error'; detalle: string }>({
    estado: 'ocioso',
    detalle: '',
  });

  /**
   * Contrato mínimo que satisface una tarea: un valor por cada entrada que declara.
   *
   * Recorre los inputs **complejos** en profundidad. No es un detalle: los contratos suelen
   * agrupar sus entradas en inputs complejos (`solicitud`, `decision`…), y un cuerpo plano lo
   * rechaza el motor. Que el front sepa construir el cuerpo a partir del contrato
   * que le sirve la API es justamente el punto de integración que aquí se demuestra.
   */
  function valorDe(entrada: EntradaDeContrato): unknown {
    // FILE va ANTES de descender por los hijos, y esto costó un diagnóstico: un input de tipo
    // FILE se expone como complejo con `filename` y `tempPath`, así que la rama de complejos
    // lo rellenaba con valores inventados. El motor entonces intenta LEER ese fichero temporal
    // y responde `404 {"exception":"class java.io.FileNotFoundException"}` — que parece un
    // problema de ruta o de permisos de la página y no lo es. Sin archivo real se manda `null`,
    // igual que hace el journey del proceso.
    if (entrada.type === 'FILE') return entrada.multiple ? [] : null;
    if (entrada.inputs?.length) {
      const objeto = Object.fromEntries(entrada.inputs.map((e) => [e.name, valorDe(e)]));
      return entrada.multiple ? [objeto] : objeto;
    }
    const simple =
      entrada.type === 'BOOLEAN' ? true
      : entrada.type === 'INTEGER' || entrada.type === 'LONG' ? 1
      : entrada.type === 'DOUBLE' || entrada.type === 'DECIMAL' ? 1.0
      : entrada.type === 'DATE' || entrada.type === 'LOCALDATE' ? '2026-09-10'
      : entrada.type === 'LOCALDATETIME' || entrada.type === 'OFFSETDATETIME'
        ? '2026-09-10T12:00:00.000Z'
        : entrada.type === 'FILE' ? null
        : 'semilla';
    return entrada.multiple ? (simple === null ? [] : [simple]) : simple;
  }

  function contratoMinimo(c: Contrato): Record<string, unknown> {
    return Object.fromEntries(c.inputs.map((e) => [e.name, valorDe(e)]));
  }

  async function probarEjecucion(): Promise<void> {
    if (!contexto.idTarea || !contrato) return;
    ejecucion = { estado: 'enviando', detalle: '' };
    try {
      await ejecutarTarea(contexto.idTarea, contratoMinimo(contrato));
      ejecucion = {
        estado: 'ok',
        detalle: `tarea ${contexto.idTarea} ejecutada (204): el motor aceptó el contrato`,
      };
    } catch (e) {
      ejecucion = { estado: 'error', detalle: textoDelFallo(e) };
    }
  }

  async function comprobar(): Promise<void> {
    try {
      if (!servidoPorBonita) {
        // En desarrollo hay que abrir sesión; en producción ya existe.
        await autenticarEnDesarrollo().catch((e) => {
          error = textoDelFallo(e);
        });
      }
      sesion = await haySesion();
      if (sesion && contexto.idTarea) {
        contrato = await contratoDeTarea(contexto.idTarea);
      }
    } catch (e) {
      error = textoDelFallo(e);
    } finally {
      listo = true;
    }
  }

  void comprobar();
</script>

<main>
  <h1>Semilla técnica de formularios</h1>
  <p class="nota">
    Cimiento de la capa de formularios. Esta página no es una pantalla del proceso:
    verifica el circuito de construcción, empaquetado, despliegue, sesión y contrato.
  </p>

  <h2>Entorno</h2>
  <dl>
    <dt>Servida por Bonita</dt>
    <dd data-testid="servida-por-bonita">{servidoPorBonita ? 'sí' : 'no (desarrollo)'}</dd>
    <dt>Embebida en el portal</dt>
    <dd data-testid="en-marco">{enMarco ? 'sí' : 'no'}</dd>
    <dt>Sesión de Bonita</dt>
    <dd data-testid="sesion">
      {#if sesion === null}comprobando…{:else if sesion}reconocida{:else}sin sesión{/if}
    </dd>
  </dl>

  <h2>Contexto recibido</h2>
  <dl>
    <dt>Tipo de formulario</dt>
    <dd data-testid="tipo">{contexto.tipo}</dd>
    <dt>Tarea</dt>
    <dd data-testid="id-tarea">{contexto.idTarea ?? '—'}</dd>
    <dt>Proceso</dt>
    <dd data-testid="id-proceso">{contexto.idProceso ?? '—'}</dd>
    <dt>Caso</dt>
    <dd data-testid="id-caso">{contexto.idCaso ?? '—'}</dd>
  </dl>

  {#if contrato}
    <h2>Contrato de la tarea</h2>
    <ul data-testid="entradas-contrato">
      {#each contrato.inputs as entrada (entrada.name)}
        <li><code>{entrada.name}</code> · {entrada.type}{entrada.multiple ? '[]' : ''}</li>
      {/each}
    </ul>
  {/if}

  <h2>Punto de integración</h2>
  <p class="nota">
    Se ejercita con el módulo real del front (<code>$lib/bonita/cliente</code>), contra el
    runtime, no con peticiones a mano.
  </p>

  <p>
    <button
      type="button"
      data-testid="probar-ejecucion"
      disabled={!contexto.idTarea || !contrato}
      onclick={probarEjecucion}
    >
      Ejecutar la tarea con su contrato
    </button>
    <span data-testid="resultado-ejecucion">
      {#if !contexto.idTarea}sin tarea en el contexto (abre la página desde una tarea)
      {:else if ejecucion.estado === 'ocioso'}—
      {:else if ejecucion.estado === 'enviando'}enviando…
      {:else if ejecucion.estado === 'ok'}✓ {ejecucion.detalle}
      {:else}✗ {ejecucion.detalle}{/if}
    </span>
  </p>

  {#if error}
    <p class="error" data-testid="error" role="alert">{error}</p>
  {/if}

  {#if listo}
    <p class="listo" data-testid="listo">Comprobación finalizada.</p>
  {/if}
</main>

<style>
  main {
    font-family: system-ui, sans-serif;
    max-width: 44rem;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    line-height: 1.5;
  }
  h1 {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
  }
  h2 {
    font-size: 1rem;
    margin-top: 2rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.6;
  }
  .nota {
    opacity: 0.7;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.25rem 1.5rem;
    margin: 0;
  }
  dt {
    font-weight: 600;
  }
  dd {
    margin: 0;
    font-variant-numeric: tabular-nums;
  }
  code {
    font-family: ui-monospace, monospace;
  }
  .error {
    padding: 0.75rem 1rem;
    border-left: 3px solid currentColor;
    background: color-mix(in srgb, currentColor 6%, transparent);
  }
  .listo {
    opacity: 0.6;
  }
</style>
