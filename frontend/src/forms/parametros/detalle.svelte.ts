/**
 * Lo que una lista y un parámetro leen de más al abrirse: quién puede editarlos, dónde se
 * usan, su historial y —si la persona es de la superadministración— el estado de la cadena. Es el mismo
 * estado para las dos pantallas, así que vive aquí y no se escribe dos veces.
 */
import type { Aplicacion } from './aplicacion';
import { completarSujetos, idsDeSujetos, trazaDeUnaDefinicion } from './carga';
import { aCsv, descargar } from './csv';
import { horaDeHoy } from './formatos';
import { delegacionesDe, dentroDelPeriodo, eventoDeTraza, usuariosDeLaEntrada, type EventoVM, type Periodo } from './historial';
import * as T from './textos';
import type { Editor, EntradaDeTraza } from './tipos';
import { usosVM, type UsosVM } from './usos';

/** El kit sirve hasta 10 páginas de traza de 100: más allá ya no hay forma de pedirlas. */
const TOPE_DE_PAGINAS = 10;

export function cargarDetalle(app: Aplicacion, definicion: () => string, etiquetas: () => { etiquetas: ReadonlyMap<string, string>; inactivas: ReadonlySet<string> }) {
  let editores = $state<Editor[]>([]);
  let nombres = $state<Record<string, string>>({});
  let usos = $state<UsosVM | null | 'cargando' | 'error'>('cargando');
  let entradas = $state<EntradaDeTraza[] | 'cargando' | 'error'>('cargando');
  let siguiente = $state(0);
  let agotada = $state(false);
  let periodo = $state<Periodo>('noventa');
  let cadena = $state<string | null>(null);
  let topeAlcanzado = $state(false);
  let cadenaFallo = $state(false);
  let cadenaRota = $state(false);
  let editoresFallo = $state(false);
  const ahora = new Date();

  async function cargarEditores(): Promise<void> {
    editoresFallo = false;
    try {
      const leidos = await app.kit.editores(definicion());
      const n: Record<string, string> = {};
      await Promise.all(
        leidos.filter((e) => e.tipo === 'USUARIO' && e.sujeto).map(async (e) => {
          n[e.sujeto as string] = await app.kit.nombreDe(e.sujeto as string);
        }),
      );
      nombres = { ...nombres, ...n };
      editores = leidos;
    } catch {
      editores = [];
      editoresFallo = true;
    }
  }

  let lecturaDeUsos = 0;
  /** Lee los usos de ESTA definición. Mientras lee, `usos` es «cargando»: ni cifras viejas ni «0». Una lectura vieja que llega tarde no pisa a la nueva. */
  async function cargarUsos(): Promise<void> {
    const esta = ++lecturaDeUsos;
    usos = 'cargando';
    try {
      const u = await app.kit.usos(definicion());
      const { etiquetas: e, inactivas } = etiquetas();
      if (esta === lecturaDeUsos) usos = usosVM(u, e, inactivas);
    } catch {
      if (esta === lecturaDeUsos) usos = 'error';
    }
  }

  async function cargarHistorial(mas = false): Promise<void> {
    if (!mas) {
      entradas = 'cargando';
      siguiente = 0;
      agotada = false;
      topeAlcanzado = false;
    }
    try {
      const r = await trazaDeUnaDefinicion(app.kit, definicion(), siguiente, 3);
      // Quien hizo cada cambio se cuenta por su nombre, no por su usuario.
      if (app.contexto().capacidades.perfil === 'superadministracion') await completarSujetos(app.kit, app.contexto().sujetos, idsDeSujetos(delegacionesDe(r.entradas)));
      const faltan = [...new Set(r.entradas.flatMap(usuariosDeLaEntrada))].filter((u) => !(u in nombres) && !(u in app.contexto().nombres));
      const nuevos: Record<string, string> = {};
      await Promise.all(faltan.map(async (u) => { nuevos[u] = await app.kit.nombreDe(u); }));
      nombres = { ...nombres, ...nuevos };
      const acumuladas = [...(mas && entradas !== 'cargando' && entradas !== 'error' ? entradas : []), ...r.entradas];
      entradas = acumuladas;
      siguiente = r.siguiente;
      agotada = r.agotada;
      // Sin ningún cambio suyo en lo leído, no se dice «no hay cambios» mientras queden páginas: se sigue (hasta el tope de la API).
      if (acumuladas.length === 0 && !agotada && siguiente < TOPE_DE_PAGINAS) {
        await cargarHistorial(true);
        return;
      }
      if (siguiente >= TOPE_DE_PAGINAS && !agotada) {
        agotada = true;
        topeAlcanzado = true;
      }
    } catch {
      if (!mas || entradas === 'cargando') entradas = 'error';
      agotada = true;
    }
  }

  async function verificar(): Promise<void> {
    if (app.contexto().capacidades.perfil !== 'superadministracion') return;
    try {
      cadenaFallo = false;
      const v = await app.kit.verificar(true);
      cadena = v.coherente && v.entradas > 0 ? `${T.CADENA_COHERENTE} · verificada ${horaDeHoy()}` : null;
      cadenaRota = !v.coherente;
    } catch {
      cadena = null;
      cadenaFallo = true;
    }
  }

  const todos = (): EventoVM[] | 'cargando' | 'error' =>
    entradas === 'cargando' || entradas === 'error'
      ? entradas
      : entradas.map((e) => eventoDeTraza(e, { nombres: { ...app.contexto().nombres, ...nombres }, definiciones: app.contexto().datos.definiciones, sujetos: app.contexto().sujetos }));

  function exportar(): void {
    const e = delPeriodo();
    if (e === 'cargando' || e === 'error') return;
    descargar(T.NOMBRE_DEL_FICHERO_DE_HISTORIAL, aCsv(T.COLUMNAS_DE_HISTORIAL, e.map((x) => [x.cuando, x.quien, x.texto, x.cambio, x.motivo])));
  }

  const delPeriodo = (): EventoVM[] | 'cargando' | 'error' => {
    const t = todos();
    return t === 'cargando' || t === 'error' ? t : t.filter((e) => dentroDelPeriodo(e, periodo, ahora));
  };

  return {
    get editores() {
      return editores;
    },
    get nombres() {
      return nombres;
    },
    get usos() {
      return usos;
    },
    get eventos() {
      return delPeriodo();
    },
    /** La última modificación en una línea: «Ana Pérez, 27 sep 2026 · 10:32 · «motivo».» */
    get ultima(): string {
      const t = todos();
      if (t === 'cargando' || t === 'error') return '';
      const e = t.find((x) => x.categoria === 'cambios' || x.categoria === 'aprobaciones');
      return e ? `${e.quien}, ${e.cuando}${e.motivo ? ` · «${e.motivo}»` : ''}.` : '';
    },
    get periodo() {
      return periodo;
    },
    set periodo(p: Periodo) {
      periodo = p;
    },
    get cadena() {
      return cadena;
    },
    get topeAlcanzado() {
      return topeAlcanzado;
    },
    get cadenaFallo() {
      return cadenaFallo;
    },
    get cadenaRota() {
      return cadenaRota;
    },
    get editoresFallo() {
      return editoresFallo;
    },
    get hayMas() {
      return !agotada && entradas !== 'error';
    },
    reintentarEditores: () => cargarEditores(),
    reintentarUsos: () => cargarUsos(),
    /** Tras escribir (estado, nombre, orden, propuesta…): las cifras y las etiquetas de «Dónde se usa» pueden haber cambiado. */
    recargarUsos: () => cargarUsos(),
    reintentarCadena: () => verificar(),
    cargarTodo(): void {
      void cargarEditores();
      void cargarHistorial();
      void cargarUsos();
      void verificar();
    },
    recargarHistorial: () => cargarHistorial(),
    masHistorial: () => cargarHistorial(true),
    exportar,
  };
}
