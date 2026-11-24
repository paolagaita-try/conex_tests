<script lang="ts">
  /**
   * Pantalla de MUESTRA del sistema de diseño — técnica, no de negocio.
   *
   * Es la referencia visual viva de la galería: una solicitud de vacaciones realista que
   * ejercita **todos** los tipos de campo que producen los contratos de tarea (TEXT corto,
   * conjunto cerrado, TEXT largo, DECIMAL, INTEGER, DATE, BOOLEAN, FILE) más las acciones y
   * los avisos. Los formularios del proyecto la toman como referencia en vez de inventar
   * cada uno su propio aspecto.
   *
   * No sustituye a ninguna pantalla de negocio; su contrato es inventado y no persiste nada.
   *
   * Toda la identidad —logotipo, color y tipografía— llega por tokens desde el tema de la
   * Living Application. Cambiar de marca no toca este archivo.
   */
  import {
    Aviso,
    AreaTexto,
    Boton,
    CargaArchivo,
    Casilla,
    Entrada,
    MarcaCabecera,
    Seleccion,
    type Opcion,
  } from '$lib/ui';
  import type { ArchivoContrato } from '$lib/bonita/tipos';
  import { tecleadoDeEjemplo, type NumeroTecleado } from '$lib/ui/valores';
  import { IMPORTE, LOCALE, SIN_DATO } from '$lib/ui/formato';
  import { nombreDeLaMarca } from '$lib/ui/marca';

  const marca = $derived(nombreDeLaMarca());

  // ── Estado del formulario de muestra ─────────────────────────────────────────
  let nombre = $state('Camila Ejemplo Demo');
  let identificacion = $state('EMP-00123');
  let email = $state('camila@demo.example');
  let telefono = $state('555-0101');
  let area = $state<string | null>('operaciones');
  // Los números de ejemplo entran como TECLEADOS y solo como literales: un widget no admite otros.
  let saldo = $state<NumeroTecleado | null>(tecleadoDeEjemplo(22));
  let dias = $state<NumeroTecleado | null>(tecleadoDeEjemplo(10));
  let anticipo = $state<NumeroTecleado | null>(tecleadoDeEjemplo(600));
  let fechaInicio = $state('2026-12-14');
  let motivo = $state<string | null>(null);
  let comentario = $state('');
  let justificante = $state<ArchivoContrato | null>(null);
  let aceptaPolitica = $state(false);
  let avisaEquipo = $state(false);
  let intentado = $state(false);
  let enviando = $state(false);
  let enviado = $state(false);

  const AREAS: readonly Opcion[] = [
    { valor: 'operaciones', etiqueta: 'Operaciones' },
    { valor: 'comercial', etiqueta: 'Comercial' },
    { valor: 'tecnologia', etiqueta: 'Tecnología' },
    { valor: 'personas', etiqueta: 'Personas' },
  ];

  const MOTIVOS: readonly Opcion[] = [
    { valor: 'descanso', etiqueta: 'Descanso' },
    { valor: 'viaje', etiqueta: 'Viaje' },
    { valor: 'familia', etiqueta: 'Asuntos familiares' },
    { valor: 'estudios', etiqueta: 'Estudios' },
  ];

  /**
   * Validación de MUESTRA: enseña cómo se ve un error, no reimplanta reglas de negocio.
   * En una pantalla real la verdad la impone el contrato de la tarea.
   */
  const errorMotivo = $derived(intentado && !motivo ? 'Elija el motivo de la solicitud.' : null);
  const errorPolitica = $derived(
    intentado && !aceptaPolitica ? 'Debe aceptar la política de vacaciones para continuar.' : null,
  );

  /** El saldo que queda es un cálculo ilustrativo: el real lo decide el proceso. */
  const restante = $derived(saldo != null && dias != null ? Math.max(0, saldo - dias) : null);

  function importe(valor: number | null): string {
    if (valor === null) return SIN_DATO;
    return new Intl.NumberFormat(LOCALE, IMPORTE).format(valor);
  }

  async function enviar(evento: SubmitEvent): Promise<void> {
    evento.preventDefault();
    intentado = true;
    if (!motivo || !aceptaPolitica) return;
    enviando = true;
    // La muestra no persiste nada: solo enseña el ciclo de envío del componente.
    await new Promise((r) => setTimeout(r, 600));
    enviando = false;
    enviado = true;
  }
</script>

<main>
  <MarcaCabecera nombre={marca} />

  <p class="sobretitulo">Solicitud de vacaciones · Paso 1 de 3</p>
  <h1>Cuéntenos qué necesita</h1>
  <p class="entrada-texto">
    Con estos datos revisamos su solicitud. Puede guardar y continuar más tarde.
  </p>

  {#if enviado}
    <Aviso tono="exito" titulo="Solicitud enviada">
      <p>Recibimos sus datos. El estado se actualiza en esta página.</p>
    </Aviso>
  {/if}

  <!-- Dos columnas en escritorio: el formulario a la izquierda y el resumen a la vista
       mientras se rellena. En pantallas estrechas se apila y el resumen queda al final. -->
  <div class="disposicion">
  <form onsubmit={enviar} novalidate>
    <fieldset>
      <legend>Sus datos</legend>

      <Entrada id="nombre" etiqueta="Nombre completo" bind:valor={nombre} obligatorio />

      <div class="pareja">
        <Entrada
          id="identificacion"
          etiqueta="Código de empleado"
          bind:valor={identificacion}
          ayuda="Formato EMP-00000"
          obligatorio
        />
        <Entrada
          id="inicio"
          etiqueta="Fecha de inicio"
          tipo="date"
          bind:valor={fechaInicio}
          obligatorio
        />
      </div>

      <div class="pareja">
        <Entrada id="email" etiqueta="Correo electrónico" tipo="email" bind:valor={email} obligatorio />
        <Entrada id="telefono" etiqueta="Teléfono" tipo="tel" bind:valor={telefono} obligatorio />
      </div>

      <Seleccion
        id="area"
        etiqueta="Área"
        opciones={AREAS}
        bind:valor={area}
        obligatorio
      />

      <Entrada
        id="saldo"
        etiqueta="Días disponibles"
        tipo="number"
        bind:valor={saldo}
        ayuda="Los que le quedan este año, según su registro."
        obligatorio
      />
    </fieldset>

    <fieldset>
      <legend>Lo que necesita</legend>

      <div class="pareja">
        <Entrada id="dias" etiqueta="Días solicitados" tipo="number" bind:valor={dias} obligatorio />
        <Entrada
          id="anticipo"
          etiqueta="Anticipo para gastos"
          tipo="number"
          paso="0.01"
          bind:valor={anticipo}
        />
      </div>

      <!-- Devolver el cálculo al instante evita que el usuario tenga que imaginárselo. -->
      <p class="calculo" aria-live="polite">
        Le quedarían <strong>{restante ?? SIN_DATO}</strong> días
        <span class="matiz">· referencial, sujeto a aprobación</span>
      </p>

      <Seleccion
        id="motivo"
        etiqueta="Motivo"
        opciones={MOTIVOS}
        bind:valor={motivo}
        error={errorMotivo}
        vacio="Seleccione una opción"
        obligatorio
      />

      <AreaTexto
        id="comentario"
        etiqueta="Comentario (opcional)"
        bind:valor={comentario}
        maximo={280}
        filas={3}
        ayuda="Si hay algo que debamos saber sobre su solicitud."
      />
    </fieldset>

    <fieldset>
      <legend>Documentos y conformidad</legend>

      <CargaArchivo
        id="justificante"
        etiqueta="Justificante (si aplica)"
        bind:valor={justificante}
        acepta="image/*,application/pdf"
        maximoMb={5}
      />

      <Casilla
        id="acepta-politica"
        etiqueta="He leído y acepto la política de vacaciones"
        bind:valor={aceptaPolitica}
        error={errorPolitica}
        obligatorio
      />
      <Casilla
        id="avisa-equipo"
        etiqueta="Avisar a mi equipo cuando se apruebe"
        bind:valor={avisaEquipo}
        ayuda="Puede continuar sin marcarla."
      />
    </fieldset>

    <div class="acciones">
      <Boton tipo="submit" ocupado={enviando}>
        {enviando ? 'Enviando…' : 'Continuar'}
      </Boton>
      <Boton tipo="button" variante="secundario">Guardar y salir</Boton>
    </div>
  </form>

  <!-- Acompaña al formulario sin robarle protagonismo: en un formulario largo, ver lo
       que se lleva pedido evita tener que recordarlo. -->
  <aside class="resumen" aria-labelledby="titulo-resumen">
    <h2 id="titulo-resumen">Resumen</h2>
    <dl>
      <div class="fila">
        <dt>Días solicitados</dt>
        <dd>{dias ?? SIN_DATO}</dd>
      </div>
      <div class="fila">
        <dt>Inicio</dt>
        <dd>{fechaInicio || SIN_DATO}</dd>
      </div>
      <div class="fila">
        <dt>Días que quedarían</dt>
        <dd>{restante ?? SIN_DATO}</dd>
      </div>
      <div class="fila">
        <dt>Anticipo</dt>
        <dd class="cifra">{importe(anticipo)}</dd>
      </div>
    </dl>
    <p class="nota">
      Las cifras son referenciales y quedan sujetas a la revisión de su solicitud.
    </p>
  </aside>
  </div>
</main>

<style>
  /* Foco en escritorio (directriz de diseño): la pantalla ocupa el ancho útil y se
     organiza en rejilla; no es una columna estrecha centrada. */
  main {
    font-family: var(--fuente-base, system-ui, sans-serif);
    max-inline-size: none;
    margin: 0 auto;
    padding: var(--esp-3, 0.75rem) var(--esp-6, 2rem) var(--esp-7, 3rem);
    color: var(--color-texto, #1c1b1f);
    line-height: var(--linea-normal, 1.5);
  }

  .disposicion {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(18rem, 1fr);
    gap: var(--esp-6, 2rem);
    align-items: start;
  }

  /* El resumen acompaña al desplazamiento mientras el formulario es largo. */
  .resumen {
    position: sticky;
    inset-block-start: var(--esp-5, 1.5rem);
    background: var(--color-superficie, #faf9fc);
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    padding: var(--esp-5, 1.5rem);
  }

  .resumen h2 {
    margin: 0 0 var(--esp-3, 0.75rem);
    font-size: var(--texto-xs, 0.75rem);
    font-weight: var(--peso-fuerte, 600);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-texto-suave, #5f5b66);
  }

  .resumen dl {
    margin: 0;
  }

  .resumen .fila {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--esp-3, 0.75rem);
    padding-block: var(--esp-3, 0.75rem);
    border-block-end: 1px solid var(--color-borde, #e4e1e8);
  }

  .resumen .fila:last-child {
    border-block-end: none;
  }

  .resumen dt {
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  .resumen dd {
    margin: 0;
    text-align: end;
    font-variant-numeric: tabular-nums;
  }

  .resumen .cifra {
    font-weight: var(--peso-fuerte, 600);
  }

  .nota {
    margin: var(--esp-4, 1rem) 0 0;
    font-size: var(--texto-xs, 0.75rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  /* Responsive: sin ancho para dos columnas, se apila y el resumen deja de ser sticky
     (pegarlo en una pantalla corta taparía el formulario). */
  @media (max-width: 60rem) {
    .disposicion {
      grid-template-columns: 1fr;
    }

    .resumen {
      position: static;
    }
  }

  .sobretitulo {
    margin: 0 0 var(--esp-2, 0.5rem);
    font-size: var(--texto-sm, 0.875rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  h1 {
    font-family: var(--fuente-marca, var(--fuente-base, system-ui, sans-serif));
    font-size: var(--texto-2xl, 2rem);
    font-weight: var(--peso-fuerte, 600);
    line-height: var(--linea-apretada, 1.25);
    letter-spacing: -0.02em;
    color: var(--color-primario-fuerte, #581c87);
    margin: 0;
  }

  /* El texto corrido sí lleva medida de lectura: una línea de 80rem se lee peor. */
  .entrada-texto {
    margin: var(--esp-3, 0.75rem) 0 var(--esp-6, 2rem);
    max-inline-size: var(--ancho-lectura, 34rem);
    color: var(--color-texto-suave, #5f5b66);
  }

  /* Cada bloque agrupa una sola idea: quién es, qué necesita, qué autoriza. */
  fieldset {
    border: 1px solid var(--color-borde, #e4e1e8);
    border-radius: var(--radio-lg, 16px);
    padding: var(--esp-5, 1.5rem);
    margin: 0 0 var(--esp-5, 1.5rem);
    background: var(--color-fondo, #fff);
  }

  legend {
    padding-inline: var(--esp-2, 0.5rem);
    font-size: var(--texto-xs, 0.75rem);
    font-weight: var(--peso-fuerte, 600);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-texto-suave, #5f5b66);
  }

  /* Dos campos cortos comparten fila en pantalla ancha; en móvil se apilan solos. */
  .pareja {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
    gap: var(--esp-4, 1rem);
  }

  .calculo {
    margin: var(--esp-2, 0.5rem) 0 var(--esp-4, 1rem);
    padding: var(--esp-3, 0.75rem) var(--esp-4, 1rem);
    background: var(--color-primario-suave, #f3e8ff);
    border-radius: var(--radio-md, 8px);
    font-size: var(--texto-sm, 0.875rem);
    font-variant-numeric: tabular-nums;
  }

  .calculo strong {
    font-size: var(--texto-lg, 1.125rem);
    color: var(--color-primario-fuerte, #581c87);
  }

  .matiz {
    color: var(--color-texto-suave, #5f5b66);
  }

  .acciones {
    display: flex;
    gap: var(--esp-3, 0.75rem);
    flex-wrap: wrap;
  }
</style>
