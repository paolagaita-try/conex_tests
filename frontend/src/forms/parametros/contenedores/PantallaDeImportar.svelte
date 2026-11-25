<script lang="ts">
  /**
   * Importar: lee el CSV en el navegador, pide la vista previa al kit (que no escribe
   * nada) y, al confirmar con motivo, manda el MISMO texto con la huella de esa vista. Si lo guardado cambió
   * entre medias, el kit responde un conflicto con la vista nueva y se vuelve a enseñar sin aplicar nada.
   */
  import { usarAplicacion } from '../aplicacion';
  import { explicar } from '../fallos';
  import { FalloDelKit, type Usos } from '../kit';
  import { construirVistaPrevia, etiquetasDelCsv, type VistaPreviaVM } from '../importar';
  import * as T from '../textos';
  import type { VistaPreviaDeImportacion } from '../tipos';
  import VistaImportar from '../vistas/VistaImportar.svelte';

  interface Props {
    onvolver: () => void;
  }
  const props: Props = $props();
  const app = usarAplicacion();

  let csv = $state('');
  let nombre = $state('');
  let cruda = $state<VistaPreviaDeImportacion | null>(null);
  let aplicada = $state<{ lote: string; conPropuestas: boolean } | null>(null);
  let cambioLaVista = $state(false);
  let error = $state<string | null>(null);

  let usosDeBajas = $state<ReadonlyMap<string, Usos | 'error'>>(new Map());
  const vista = $derived<VistaPreviaVM | null>(cruda ? construirVistaPrevia(cruda, app.contexto().datos.definiciones, app.contexto().datos.valores, etiquetasDelCsv(csv), usosDeBajas) : null);

  /** Una baja dice qué expedientes usan la opción: se pide `GET parametros/usos` de cada definición con bajas. */
  async function leerUsosDeLasBajas(v: VistaPreviaDeImportacion): Promise<void> {
    const definiciones = [...new Set(v.filas.filter((f) => f.clase === 'BAJA').map((f) => f.definicion))];
    const leidos = new Map<string, Usos | 'error'>();
    await Promise.all(definiciones.map(async (d) => { leidos.set(d, await app.kit.usos(d).catch(() => 'error' as const)); }));
    usosDeBajas = leidos;
  }

  function leer(f: File): Promise<string> {
    return new Promise((resolver, rechazar) => {
      const lector = new FileReader();
      lector.onload = () => resolver(String(lector.result ?? ''));
      lector.onerror = () => rechazar(new Error('lectura'));
      lector.readAsText(f);
    });
  }

  async function subir(f: File): Promise<void> {
    error = null;
    usosDeBajas = new Map(); // lo leído para el fichero anterior no vale para este
    cambioLaVista = false;
    try {
      csv = await leer(f);
    } catch {
      error = T.FICHERO_ILEGIBLE;
      return;
    }
    nombre = f.name;
    try {
      cruda = await app.kit.vistaPreviaDeImportacion(csv);
      await leerUsosDeLasBajas(cruda);
    } catch (e) {
      cruda = null;
      error = e instanceof FalloDelKit && e.clase === 'VALIDACION' ? T.CSV_RECHAZADO : T.FALLO_VISTA_PREVIA;
    }
  }

  /** Vuelve a leer cada definición que la importación pudo tocar; sin ninguna, solo lo pendiente. */
  async function releer(definiciones: string[]): Promise<void> {
    const unicas = [...new Set(definiciones)].filter((d) => d !== '');
    if (unicas.length === 0) await app.refrescar('');
    for (const d of unicas) await app.refrescar(d);
  }

  async function confirmar(motivo: string): Promise<void> {
    if (!cruda) return;
    error = null;
    let resultado: Awaited<ReturnType<typeof app.kit.importar>>;
    try {
      resultado = await app.kit.importar(csv, motivo.trim(), cruda.huella);
      aplicada = { lote: resultado.lote, conPropuestas: resultado.filas.some((f) => f.clase === 'PROPUESTA') };
    } catch (e) {
      if (e instanceof FalloDelKit && e.clase === 'CONFLICTO' && e.vistaNueva) {
        cruda = e.vistaNueva;
        cambioLaVista = true;
      } else if (e instanceof FalloDelKit && e.clase === 'VALIDACION' && e.campo === 'motivo') error = T.ERROR_MOTIVO;
      else {
        const x = explicar(e, app.contexto().sesion.usuario);
        error = x.desconocido ? T.IMPORTACION_SIN_RESPUESTA : x.mensaje;
        // Sin respuesta no se sabe si se aplicó: se relee lo que el fichero tocaba, antes de que nadie repita.
        if (x.desconocido) await releer(cruda?.filas.map((f) => f.definicion) ?? []);
      }
      return;
    }
    // Ya aplicada: se releen las definiciones que tocó (no solo lo pendiente) y, si falla, `refrescar` lo avisa.
    await releer(resultado.filas.map((f) => f.definicion));
  }
</script>

<VistaImportar
  {vista}
  nombreDelFichero={nombre}
  {aplicada}
  {cambioLaVista}
  {error}
  subir={(f) => void subir(f)}
  {confirmar}
  onvolver={props.onvolver}
  oncambiar={() => { cruda = null; csv = ''; cambioLaVista = false; }}
/>
