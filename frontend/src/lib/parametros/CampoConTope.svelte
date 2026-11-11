<script lang="ts">
  /**
   * Un campo de monto cuyo máximo sale del módulo de parámetros.
   *
   * El máximo se pide a `GET parametros/valores` con el id de la tarea y, si depende de una lista
   * madre (p. ej. el tipo de solicitud), con el código elegido: al cambiar de opción cambia el máximo. El control es el
   * campo con afijo de la regla por defecto (monto → afijo); él es quien dice «Supera el máximo de
   * $…» con el formato de la galería, así que aquí no se formatea ninguna cifra.
   *
   * ## Si no hay máximo que comprobar, no se envía
   *
   * Una lectura que falla, o un padre sin tope definido, bloquea el envío con un aviso: dejar pasar «sin
   * tope» sería un default silencioso, justo lo que el fallo cerrado del módulo prohíbe. La validación de
   * verdad es del servidor; esto es el reflejo para la experiencia.
   */
  import { untrack } from 'svelte';
  import CampoConAfijo from '$lib/ui/CampoConAfijo.svelte';
  import type { NumeroTecleado } from '$lib/ui/valores';
  import { maximoDeAyuda, MONEDA, simboloDeMoneda } from '$lib/ui/formato';
  import { leerValores, type LectorDeValores } from './opciones';

  type Lectura =
    | { estado: 'espera-padre' }
    | { estado: 'cargando' }
    | { estado: 'lista'; maximo: number; unidad: string | undefined }
    | { estado: 'sin-tope' }
    | { estado: 'error' };

  interface Props {
    id: string;
    prueba?: string;
    etiqueta: string;
    /** Código del parámetro que fija el máximo (`tope_importe_por_tipo`). */
    tope: string;
    tarea: string | null | undefined;
    /** Formulario de instanciación (sin tarea): el id de la definición del proceso con el que pedir. */
    instanciacion?: string | null;
    depende?: boolean;
    padre?: string;
    valor: NumeroTecleado | null | undefined;
    ayuda?: string;
    error?: string | null;
    obligatorio?: boolean;
    deshabilitado?: boolean;
    lector?: LectorDeValores;
    alProblema?: (problema: string | null) => void;
  }

  let {
    id,
    prueba,
    etiqueta,
    tope,
    tarea,
    instanciacion,
    depende = false,
    padre,
    valor = $bindable(),
    ayuda,
    error = null,
    obligatorio = false,
    deshabilitado = false,
    lector = leerValores,
    alProblema,
  }: Props = $props();

  let lectura = $state<Lectura>({ estado: 'cargando' });
  /** Lo escrito superaba el máximo NUEVO (cambió el producto): se vació y se dice por qué, sin cifras. */
  let avisoDeCambio = $state(false);

  $effect(() => {
    const idTarea = tarea;
    const idInstanciacion = instanciacion;
    const codigo = tope;
    const codigoPadre = padre;
    const conPadre = depende;
    if (!idTarea && !idInstanciacion) {
      lectura = { estado: 'error' };
      return;
    }
    if (conPadre && !codigoPadre) {
      lectura = { estado: 'espera-padre' };
      return;
    }
    lectura = { estado: 'cargando' };
    let vigente = true;
    lector({
      definicion: codigo,
      tarea: idTarea || undefined,
      instanciacion: idTarea ? undefined : idInstanciacion || undefined,
      padre: conPadre ? codigoPadre : undefined,
    })
      .then((leido) => {
        if (!vigente) return;
        if (leido.clase !== 'PARAMETRO') {
          lectura = { estado: 'error' };
          return;
        }
        // Un texto decimal del servidor → el número con el que el campo compara. No se pinta.
        const maximo = leido.valor === null ? Number.NaN : Number(leido.valor);
        lectura = Number.isFinite(maximo) ? { estado: 'lista', maximo, unidad: leido.unidad } : { estado: 'sin-tope' };
        // Si lo ya escrito supera el nuevo máximo (cambió el producto), no se conserva en silencio.
        const actual = untrack(() => valor);
        if (Number.isFinite(maximo) && typeof actual === 'number' && actual > maximo) {
          valor = null;
          avisoDeCambio = true;
        }
      })
      .catch(() => {
        if (vigente) lectura = { estado: 'error' };
      });
    return () => {
      vigente = false;
    };
  });

  const problema = $derived.by((): string | null => {
    switch (lectura.estado) {
      case 'error':
        return `No se pudo comprobar el máximo de «${etiqueta}». No se puede enviar hasta que vuelva a estar disponible.`;
      case 'sin-tope':
        return `No hay un máximo definido para «${etiqueta}». No se puede enviar hasta que lo haya.`;
      case 'cargando':
        return `El máximo de «${etiqueta}» se está cargando.`;
      default:
        return null;
    }
  });

  // Cuando la persona vuelve a poner un monto, el aviso de «se vació» ya cumplió.
  $effect(() => {
    if (typeof valor === 'number') avisoDeCambio = false;
  });

  $effect(() => {
    const p = problema;
    untrack(() => alProblema?.(p));
  });
  $effect(() => () => untrack(() => alProblema?.(null)));

  const maximo = $derived(lectura.estado === 'lista' ? lectura.maximo : undefined);
  // El servidor sirve la unidad como código ISO 4217; el campo la dice con el símbolo del locale. Solo para la moneda del proyecto.
  const prefijo = $derived(lectura.estado === 'lista' && lectura.unidad === MONEDA ? simboloDeMoneda() : undefined);
  // «Máximo $X», con el tope que sirve el módulo y el formato de la galería: la cifra no se escribe aquí.
  const ayudaDelMaximo = $derived(prefijo !== undefined && maximo !== undefined ? maximoDeAyuda(maximo) : null);
  // Lo que se dice mientras NO hay fallo: esperar al padre o al servidor. Un fallo sale como error del
  // campo (una sola vez), no además como ayuda.
  const mensajeDeEstado = $derived(
    lectura.estado === 'espera-padre'
      ? 'El máximo depende de la opción que elija arriba.'
      : lectura.estado === 'cargando'
        ? 'Cargando el máximo…'
        : undefined,
  );
</script>

<CampoConAfijo
  {id}
  {prueba}
  {etiqueta}
  bind:valor
  {prefijo}
  {maximo}
  ayuda={[ayuda, ayudaDelMaximo, mensajeDeEstado].filter(Boolean).join(' · ') || undefined}
  error={error ??
    (lectura.estado === 'error' || lectura.estado === 'sin-tope' ? problema : null) ??
    (avisoDeCambio ? 'El monto supera el máximo de la opción elegida: escríbalo de nuevo.' : null)}
  {obligatorio}
  {deshabilitado}
/>
