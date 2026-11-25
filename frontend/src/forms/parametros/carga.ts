/**
 * Lo que la aplicación lee al abrirse: la persona, qué puede hacer y los datos del
 * inicio. Una función pura de `Kit`, para que el contenedor y los tests la usen igual.
 *
 * Reglas:
 * - La primera lectura del kit es el catálogo de definiciones: si el servidor la rechaza (403), la
 *   aplicación entera no está disponible para esa persona y NO se pide nada más.
 * - Lo accesorio (la traza para «último cambio», los editores para deducir delegaciones, los nombres de
 *   las personas) es mejor esfuerzo: si falla, el inicio sale sin ese dato, no sin inicio.
 */
import { etiquetasUnicas, nombreDeGrupo, nombreDeRol, nombresUnicos } from './nombres';
import type { Sesion } from '$lib/bonita/bandeja';
import type { Kit, Membresia } from './kit';
import { FalloDelKit } from './kit';
import { capacidadesDe, esSuperadministracion, type Capacidades } from './capacidades';
import type { DatosDelInicio, UltimoCambio } from './inicio';
import type { Editor, EntradaDeTraza, ListaDePropuestas, Propuesta } from './tipos';
import type { SujetosPorId } from './aprobaciones';

export interface Contexto {
  sesion: Sesion;
  membresias: Membresia[];
  capacidades: Capacidades;
  datos: DatosDelInicio;
  /** Los pendientes de TODO el módulo, para el contador y las listas de Aprobaciones. */
  propuestas: Propuesta[];
  /** Nombre para mostrar por nombre de inicio de sesión. */
  nombres: Record<string, string>;
  /** Personas, grupos y roles por identificador (solo la superadministración los puede buscar). */
  sujetos: SujetosPorId;
  /** La búsqueda de personas, grupos y roles falló: solo Permisos y Nueva delegación lo necesitan, y lo dicen. */
  sujetosFallo: boolean;
}

/** Las acciones de la traza que cambian el valor o las opciones de una definición. */
const CAMBIA_UNA_DEFINICION = new Set([
  'CREAR',
  'EDITAR',
  'DESACTIVAR',
  'REACTIVAR',
  'ORDENAR',
  'CREAR_VERSION_PROPIA',
  'VOLVER_A_HEREDAR',
  'APROBAR',
  'IMPORTAR',
  'EDITAR_DEFINICION',
]);

/** El último cambio de cada definición según la traza (la más reciente primero). */
export function ultimosCambios(entradas: EntradaDeTraza[]): Record<string, { usuario: string; fechaHora: string }> {
  const salida: Record<string, { usuario: string; fechaHora: string }> = {};
  for (const e of entradas) {
    if (!CAMBIA_UNA_DEFINICION.has(e.accion)) continue;
    const definicion = e.claveNegocio.split('|')[0];
    if (!definicion || definicion === '*' || salida[definicion]) continue;
    salida[definicion] = { usuario: e.usuario, fechaHora: e.fechaHora };
  }
  return salida;
}

/** Cuántas propuestas trae una página del kit (`c=100`): una página llena puede tener otra detrás. */
const POR_PAGINA = 100;
const MAXIMO_DE_PAGINAS = 10;

/**
 * TODAS las propuestas de un estado, página a página (el kit pagina a 100 y ordena por fecha DESC: leer solo la primera
 * esconde las pendientes antiguas en cuanto hay más de 100 propuestas en total). Los contadores son los de la primera página.
 */
export async function propuestasDe(kit: Kit, estado: string): Promise<ListaDePropuestas> {
  const primera = await kit.propuestas(estado, 0);
  const todas = [...primera.propuestas];
  let llena = primera.propuestas.length >= POR_PAGINA;
  for (let pagina = 1; llena && pagina < MAXIMO_DE_PAGINAS; pagina++) {
    const siguiente = await kit.propuestas(estado, pagina);
    todas.push(...siguiente.propuestas);
    llena = siguiente.propuestas.length >= POR_PAGINA;
  }
  return { ...primera, propuestas: todas };
}

const mejorEsfuerzo = async <T>(lectura: Promise<T>, vacio: T): Promise<T> => {
  try {
    return await lectura;
  } catch (e) {
    // Una compuerta de familia cerrada no es «accesorio»: se propaga.
    if (e instanceof FalloDelKit && e.clase === 'SIN_PERMISO') throw e;
    return vacio;
  }
};

export async function cargarContexto(kit: Kit): Promise<Contexto> {
  const sesion = await kit.sesion();
  // La puerta: si el servidor rechaza al catálogo, no hay nada más que pedir.
  const definiciones = await kit.definiciones();
  // Sin membresías leídas no se sabe quién es la persona: un fallo es un error, no «consulta» (B2).
  const membresias: Membresia[] = await kit.membresias(sesion.id);
  const esSuper = esSuperadministracion(membresias);

  const [procesos, valoresLeidos, lista, traza, editores] = await Promise.all([
    kit.procesos(),
    Promise.all(definiciones.map((d) => kit.valores(d.codigo))),
    propuestasDe(kit, 'PENDIENTE'),
    mejorEsfuerzo(kit.traza({}, 0), { elementos: [], hayMas: false }),
    esSuper
      ? Promise.resolve([] as Editor[])
      : Promise.all(definiciones.map((d) => kit.editores(d.codigo))).then((x) => x.flat()),
  ]);

  const capacidades = capacidadesDe(sesion.usuario, membresias, editores);

  const brutos = ultimosCambios(traza.elementos);
  const usuarios = [...new Set([...Object.values(brutos).map((u) => u.usuario), ...lista.propuestas.map((p) => p.proponente), ...lista.propuestas.map((p) => p.aprobador ?? '')])].filter(Boolean);
  const nombres: Record<string, string> = {};
  await Promise.all(usuarios.map(async (u) => { nombres[u] = await kit.nombreDe(u); }));
  // La persona de la sesión cuenta como una más: si otra se llama igual, las dos se distinguen (y la regla «no apruebas lo tuyo» se lee bien).
  nombres[sesion.usuario] = sesion.nombre;

  // Los nombres de a quién se delega: solo la superadministración los puede buscar; el resto no los necesita.
  const sujetos: SujetosPorId = { usuario: [], grupo: [], rol: [] };
  let sujetosFallo = false;
  if (esSuper) {
    try {
      const [usuarios, grupos, roles] = await Promise.all([
        kit.organizacion('usuario', ''),
        kit.organizacion('grupo', ''),
        kit.organizacion('rol', ''),
      ]);
      // Las personas por su nombre y los roles en lenguaje de negocio, no por login ni por nombre técnico.
      // Por ID, no por nombre: lo que se lee igual se distingue (login, ruta, nombre técnico) para poder elegirlo y no mezclarlo.
      const conNombre = await Promise.all(usuarios.map(async (u) => ({ id: u.id, nombre: await kit.nombreDe(u.nombre), extra: u.nombre })));
      sujetos.usuario.push(...etiquetasUnicas(conNombre));
      sujetos.grupo.push(...etiquetasUnicas(grupos.map((g) => ({ id: g.id, nombre: nombreDeGrupo(g.nombre), extra: g.nombre }))));
      sujetos.rol.push(...etiquetasUnicas(roles.map((r) => ({ id: r.id, nombre: nombreDeRol(r.nombre), extra: r.nombre }))));
    } catch {
      // Un fallo de la búsqueda NO tumba la aplicación entera (ni dice «no disponible»): degrada Permisos y Nueva delegación.
      sujetosFallo = true;
    }
  }

  const ultimos: Record<string, UltimoCambio> = {};
  for (const [definicion, u] of Object.entries(brutos)) ultimos[definicion] = { usuario: nombresUnicos(nombres)[u.usuario] ?? u.usuario, fechaHora: u.fechaHora };

  return {
    sesion,
    membresias,
    capacidades,
    datos: {
      definiciones,
      valores: Object.fromEntries(valoresLeidos.map((v) => [v.definicion.codigo, v])),
      procesos,
      pendientes: lista.propuestas.filter((p) => p.estado === 'PENDIENTE'),
      ultimos,
    },
    propuestas: lista.propuestas,
    nombres: nombresUnicos(nombres),
    sujetos,
    sujetosFallo,
  };
}

/**
 * La traza de UNA definición. El kit filtra por clave exacta, y la clave de una opción lleva su ámbito y su
 * código (`definicion|proceso|actividad|padre|codigo`), así que se leen las páginas más recientes y se
 * queda con las que empiezan por `<definicion>|`. Es un barrido acotado: `paginas` páginas desde `desde`;
 * `agotada` dice si ya no hay más antiguas.
 */
export async function trazaDeUnaDefinicion(
  kit: Kit,
  codigo: string,
  desde: number,
  paginas: number,
): Promise<{ entradas: EntradaDeTraza[]; siguiente: number; agotada: boolean }> {
  const entradas: EntradaDeTraza[] = [];
  let pagina = desde;
  let agotada = false;
  for (let leidas = 0; leidas < paginas && pagina < MAXIMO_DE_PAGINAS; leidas++) {
    const r = await kit.traza({}, pagina);
    entradas.push(...r.elementos.filter((e) => e.claveNegocio.startsWith(`${codigo}|`)));
    pagina++;
    if (!r.hayMas) {
      agotada = true;
      break;
    }
  }
  return { entradas, siguiente: pagina, agotada };
}

export interface IdsDeSujetos {
  usuario: number[];
  grupo: number[];
  rol: number[];
}

/** Los ids de personas, grupos y roles que nombra una lista de filas de delegación o de datos de delegación. */
export function idsDeSujetos(filas: ReadonlyArray<Record<string, unknown>>): IdsDeSujetos {
  const n = (v: unknown): number[] => (typeof v === 'number' ? [v] : []);
  return {
    usuario: [...new Set(filas.flatMap((f) => n(f.sujetoUsuarioId)))],
    grupo: [...new Set(filas.flatMap((f) => n(f.sujetoGrupoId)))],
    rol: [...new Set(filas.flatMap((f) => n(f.sujetoRolId)))],
  };
}

/**
 * Los sujetos que el kit no sirvió en su búsqueda de 20 se piden POR SU ID: una delegación a la persona 21 no puede
 * salir como «una persona» si su id existe. Añade lo que encuentre a `sujetos` y dice si añadió algo.
 */
export async function completarSujetos(kit: Kit, sujetos: SujetosPorId, ids: IdsDeSujetos): Promise<boolean> {
  let nuevo = false;
  const por = [['usuario', sujetos.usuario, ids.usuario], ['grupo', sujetos.grupo, ids.grupo], ['rol', sujetos.rol, ids.rol]] as const;
  await Promise.all(
    por.flatMap(([tipo, lista, pedidos]) =>
      pedidos
        .filter((id) => !lista.some((x) => x.id === id))
        .map(async (id) => {
          const r = await kit.nombreDeSujeto(tipo, id);
          if (!r || lista.some((x) => x.id === id)) return;
          const etiqueta = tipo === 'usuario' ? r.nombre : tipo === 'rol' ? nombreDeRol(r.nombre) : nombreDeGrupo(r.extra);
          lista.push({ id, nombre: lista.some((x) => x.nombre === etiqueta) ? `${etiqueta} · ${r.extra}` : etiqueta });
          nuevo = true;
        }),
    ),
  );
  return nuevo;
}
