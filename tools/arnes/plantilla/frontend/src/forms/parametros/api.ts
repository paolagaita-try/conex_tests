/**
 * La única puerta de la aplicación hacia el kit de parámetros: el cliente real.
 * Los tipos, la interfaz `Kit` y los fallos viven en `kit.ts`, para que la galería viva pinte las mismas
 * vistas con un cliente de ejemplo sin arrastrar las rutas reales (`check_permisos_llamados` mide lo que
 * una pantalla alcanza por sus imports).
 *
 * - Habla **solo** con `extension/parametros/*` (más la sesión y las membresías de la organización).
 * - **Valida la forma** de lo que llega; traduce los rechazos a una clase cerrada (`FalloDelKit`).
 * - Cada llamada escribe su recurso como LITERAL y su método en la propia llamada.
 */
import { peticion, TIEMPO_MAXIMO_DE_CONSULTA_MS } from '$lib/bonita/cliente';
import { consulta, quienSoy } from '$lib/bonita/bandeja';
import { ErrorDeBonita } from '$lib/bonita/tipos';
import { nombreDeSujetoPorId } from './identidad';
import {
  FalloDelKit,
  type Kit,
  type ResultadoDeEscritura,
} from './kit';
import type {
  Definicion,
  Delegacion,
  Editor,
  EntradaDeTraza,
  Fila,
  Propuesta,
  VistaPreviaDeImportacion,
} from './tipos';

/** Las páginas de la traza, por texto: 0 a 9 de 100 entradas (la verificación y los filtros acotan el resto). */
export const PAGINAS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] as const;
export const POR_PAGINA_DE_TRAZA = '100';
/** Cuántas entradas trae una página llena (lo que dice `POR_PAGINA_DE_TRAZA`, como número para comparar). */
const LLENA = 100;

// ─── Forma de lo que llega ───────────────────────────────────────────────────────────────────────

type Objeto = Record<string, unknown>;

const esObjeto = (v: unknown): v is Objeto => typeof v === 'object' && v !== null && !Array.isArray(v);

function forma(donde: string, porque: string): never {
  throw new FalloDelKit('FORMA', donde, porque);
}

function texto(o: Objeto, k: string, donde: string): string {
  const v = o[k];
  if (typeof v !== 'string') forma(donde, `«${k}» no es texto`);
  return v;
}
function textoONulo(o: Objeto, k: string): string | null {
  const v = o[k];
  return typeof v === 'string' ? v : null;
}
function booleano(o: Objeto, k: string, donde: string): boolean {
  const v = o[k];
  if (typeof v !== 'boolean') forma(donde, `«${k}» no es sí/no`);
  return v;
}
function numero(o: Objeto, k: string, donde: string): number {
  const v = o[k];
  if (typeof v !== 'number') forma(donde, `«${k}» no es un número`);
  return v;
}
function numeroONulo(o: Objeto, k: string): number | null {
  const v = o[k];
  return typeof v === 'number' ? v : null;
}
function lista(v: unknown, donde: string): unknown[] {
  if (!Array.isArray(v)) forma(donde, 'se esperaba una lista');
  return v;
}
function objeto(v: unknown, donde: string): Objeto {
  if (!esObjeto(v)) forma(donde, 'se esperaba un objeto');
  return v;
}

function definicionDe(v: unknown): Definicion {
  const o = objeto(v, 'definición');
  const clase = texto(o, 'clase', 'definición');
  const tipoDato = texto(o, 'tipoDato', 'definición');
  const impacto = texto(o, 'impacto', 'definición');
  if (clase !== 'LISTA' && clase !== 'PARAMETRO') forma('definición', 'clase desconocida');
  if (impacto !== 'NORMAL' && impacto !== 'ALTO') forma('definición', 'impacto desconocido');
  return {
    codigo: texto(o, 'codigo', 'definición'),
    nombre: texto(o, 'nombre', 'definición'),
    descripcion: textoONulo(o, 'descripcion'),
    clase,
    tipoDato: tipoDato as Definicion['tipoDato'],
    unidad: textoONulo(o, 'unidad'),
    minimo: textoONulo(o, 'minimo'),
    maximo: textoONulo(o, 'maximo'),
    decimales: numeroONulo(o, 'decimales'),
    dependeDe: textoONulo(o, 'dependeDe') ?? '*',
    impacto,
    fallback: textoONulo(o, 'fallback'),
    origen: textoONulo(o, 'origen') ?? '',
    visibilidad: textoONulo(o, 'visibilidad') ?? 'INTERNA',
    activo: booleano(o, 'activo', 'definición'),
    persistenceVersion: numero(o, 'persistenceVersion', 'definición'),
  };
}

function filaDe(v: unknown): Fila {
  const o = objeto(v, 'fila');
  return {
    definicion: texto(o, 'definicion', 'fila'),
    proceso: texto(o, 'proceso', 'fila'),
    actividad: texto(o, 'actividad', 'fila'),
    codigoPadre: texto(o, 'codigoPadre', 'fila'),
    codigo: texto(o, 'codigo', 'fila'),
    etiqueta: textoONulo(o, 'etiqueta'),
    ayuda: textoONulo(o, 'ayuda'),
    orden: numeroONulo(o, 'orden'),
    valor: textoONulo(o, 'valor'),
    activo: booleano(o, 'activo', 'fila'),
    copiadoDe: textoONulo(o, 'copiadoDe') ?? '*',
    codigosOrigen: textoONulo(o, 'codigosOrigen'),
    persistenceVersion: numero(o, 'persistenceVersion', 'fila'),
  };
}

function propuestaDe(v: unknown): Propuesta {
  const o = objeto(v, 'propuesta');
  const estado = texto(o, 'estado', 'propuesta');
  if (!['PENDIENTE', 'APROBADA', 'RECHAZADA', 'RETIRADA'].includes(estado)) forma('propuesta', 'estado desconocido');
  const op = objeto(o.valorPropuesto, 'propuesta.valorPropuesto');
  return {
    id: numero(o, 'id', 'propuesta'),
    definicion: texto(o, 'definicion', 'propuesta'),
    proceso: texto(o, 'proceso', 'propuesta'),
    actividad: texto(o, 'actividad', 'propuesta'),
    codigoPadre: texto(o, 'codigoPadre', 'propuesta'),
    codigo: texto(o, 'codigo', 'propuesta'),
    accion: texto(o, 'accion', 'propuesta'),
    valorAnterior: Array.isArray(o.valorAnterior) ? (o.valorAnterior as Array<Record<string, unknown>>) : [],
    valorPropuesto: {
      accion: texto(op, 'accion', 'propuesta.valorPropuesto'),
      definicion: texto(op, 'definicion', 'propuesta.valorPropuesto'),
      proceso: texto(op, 'proceso', 'propuesta.valorPropuesto'),
      actividad: texto(op, 'actividad', 'propuesta.valorPropuesto'),
      codigoPadre: textoONulo(op, 'codigoPadre') ?? '*',
      codigo: textoONulo(op, 'codigo') ?? '*',
      datos: esObjeto(op.datos) ? op.datos : {},
    },
    proponente: texto(o, 'proponente', 'propuesta'),
    motivo: texto(o, 'motivo', 'propuesta'),
    estado: estado as Propuesta['estado'],
    aprobador: textoONulo(o, 'aprobador'),
    comentario: textoONulo(o, 'comentario'),
    creadaEn: texto(o, 'creadaEn', 'propuesta'),
    resueltaEn: textoONulo(o, 'resueltaEn'),
    persistenceVersion: numero(o, 'persistenceVersion', 'propuesta'),
    esPropia: booleano(o, 'esPropia', 'propuesta'),
    puedesAprobar: booleano(o, 'puedesAprobar', 'propuesta'),
  };
}

function delegacionDe(v: unknown): Delegacion {
  const o = objeto(v, 'delegación');
  const tipo = texto(o, 'tipoSujeto', 'delegación');
  if (!['USUARIO', 'GRUPO', 'ROL', 'GRUPO_ROL'].includes(tipo)) forma('delegación', 'tipo de sujeto desconocido');
  return {
    persistenceVersion: numero(o, 'persistenceVersion', 'delegación'),
    tipoSujeto: tipo as Delegacion['tipoSujeto'],
    sujetoUsuarioId: numeroONulo(o, 'sujetoUsuarioId'),
    sujetoGrupoId: numeroONulo(o, 'sujetoGrupoId'),
    sujetoRolId: numeroONulo(o, 'sujetoRolId'),
    sujetoRuta: textoONulo(o, 'sujetoRuta'),
    incluyeSubgrupos: o.incluyeSubgrupos === true,
    proceso: texto(o, 'proceso', 'delegación'),
    actividades: lista(o.actividades ?? [], 'delegación.actividades').filter((a): a is string => typeof a === 'string'),
    vigenteDesde: textoONulo(o, 'vigenteDesde'),
    vigenteHasta: textoONulo(o, 'vigenteHasta'),
    activo: o.activo === true,
    otorgadoPor: textoONulo(o, 'otorgadoPor') ?? '',
    motivo: textoONulo(o, 'motivo') ?? '',
  };
}

function trazaDe(v: unknown): EntradaDeTraza {
  const o = objeto(v, 'traza');
  return {
    id: numero(o, 'id', 'traza'),
    fechaHora: texto(o, 'fechaHora', 'traza'),
    usuario: texto(o, 'usuario', 'traza'),
    rolesVigentes: o.rolesVigentes ?? null,
    accion: texto(o, 'accion', 'traza'),
    claveNegocio: texto(o, 'claveNegocio', 'traza'),
    valorAnterior: o.valorAnterior ?? null,
    valorNuevo: o.valorNuevo ?? null,
    motivo: textoONulo(o, 'motivo') ?? '',
    origen: textoONulo(o, 'origen') ?? 'PANTALLA',
    lote: textoONulo(o, 'lote'),
    hashAnterior: textoONulo(o, 'hashAnterior') ?? '',
    hash: textoONulo(o, 'hash') ?? '',
  };
}

function vistaPreviaDe(v: unknown): VistaPreviaDeImportacion {
  const o = objeto(v, 'importación');
  const filas = lista(o.filas, 'importación.filas').map((f) => {
    const x = objeto(f, 'importación.fila');
    return {
      fila: numero(x, 'fila', 'importación.fila'),
      clase: texto(x, 'clase', 'importación.fila') as VistaPreviaDeImportacion['filas'][number]['clase'],
      definicion: texto(x, 'definicion', 'importación.fila'),
      proceso: textoONulo(x, 'proceso') ?? '*',
      actividad: textoONulo(x, 'actividad') ?? '*',
      codigoPadre: textoONulo(x, 'codigoPadre') ?? '*',
      codigo: textoONulo(x, 'codigo') ?? '*',
      detalle: textoONulo(x, 'detalle') ?? '',
    };
  });
  return { resumen: resumenDe(o.resumen), filas, huella: textoONulo(o, 'huella') ?? '' };
}

function resumenDe(v: unknown): VistaPreviaDeImportacion['resumen'] {
  const o = objeto(v ?? {}, 'importación.resumen');
  const n = (k: string) => (typeof o[k] === 'number' ? (o[k] as number) : 0);
  return {
    altas: n('altas'),
    cambios: n('cambios'),
    bajas: n('bajas'),
    sinCambios: n('sinCambios'),
    propuestas: n('propuestas'),
    errores: n('errores'),
  };
}

// ─── Fallos del transporte y del servidor ────────────────────────────────────────────────────────

/** Traduce el rechazo de la plataforma o del kit a un `FalloDelKit`. */
function falloDe(e: unknown): FalloDelKit {
  if (e instanceof FalloDelKit) return e;
  if (!(e instanceof ErrorDeBonita)) return new FalloDelKit('SIN_RESPUESTA');
  const cuerpo = esObjeto(e.cuerpo) ? e.cuerpo : {};
  const estado = e.estado;
  if (estado === 0) return new FalloDelKit('SIN_RESPUESTA');
  const campo = typeof cuerpo.campo === 'string' ? cuerpo.campo : null;
  const detalle = typeof cuerpo.detalle === 'string' ? cuerpo.detalle : null;
  if (estado === 403) return new FalloDelKit('SIN_PERMISO');
  if (estado === 404) return new FalloDelKit('NO_EXISTE');
  if (estado === 409) {
    const nueva = esObjeto(cuerpo.vistaPrevia) ? vistaPreviaDe(cuerpo.vistaPrevia) : null;
    return new FalloDelKit('CONFLICTO', campo, detalle, textoONulo(cuerpo, 'guardadoPor'), textoONulo(cuerpo, 'guardadoEn'), nueva);
  }
  if (estado === 422) return new FalloDelKit('VALIDACION', campo, detalle);
  return new FalloDelKit('SERVIDOR');
}

/** Espera una llamada ya hecha y entiende su cuerpo; cualquier rechazo sale clasificado. */
async function entender<T>(llamada: Promise<unknown>, entender: (cuerpo: unknown) => T): Promise<T> {
  try {
    return entender(await llamada);
  } catch (e) {
    throw falloDe(e);
  }
}

/** Una escritura: el cuerpo de la respuesta, o el rechazo clasificado. */
async function escrito(llamada: Promise<unknown>): Promise<unknown> {
  try {
    return await llamada;
  } catch (e) {
    throw falloDe(e);
  }
}

function resultadoDe(v: unknown): ResultadoDeEscritura {
  const o = objeto(v ?? {}, 'escritura');
  if (o.aplicado === true) {
    const filas = Array.isArray(o.filas) ? o.filas : [];
    return {
      aplicado: true,
      filas: filas.filter(esObjeto).map((f) => ({
        codigo: typeof f.codigo === 'string' ? f.codigo : '*',
        persistenceVersion: typeof f.persistenceVersion === 'number' ? f.persistenceVersion : 0,
      })),
    };
  }
  const p = objeto(o.propuesta, 'escritura.propuesta');
  return { aplicado: false, propuesta: { id: numero(p, 'id', 'propuesta'), estado: texto(p, 'estado', 'propuesta') } };
}

/** Los parámetros de una consulta del kit: `a=1&b=2` con lo que viene (sin el `?`, que va en el literal de la ruta). */
const parametros = (pares: Array<[string, string | undefined]>): string => {
  const q = new URLSearchParams();
  for (const [k, v] of pares) if (v !== undefined && v !== '') q.set(k, v);
  return q.toString();
};

const ESPERA = { tiempoMaximoMs: TIEMPO_MAXIMO_DE_CONSULTA_MS };

export function crearKit(): Kit {
  return {
    sesion: () => quienSoy(),

    async membresias(idUsuario) {
      const r = await peticion<unknown>(consulta('/identity/membership', { user_id: idUsuario }, { porPagina: 100, despliega: ['role_id', 'group_id'] }), ESPERA).catch((e) => {
        throw falloDe(e);
      });
      return lista(r, 'membresías')
        .filter(esObjeto)
        .map((m) => {
          const rol = esObjeto(m.role_id) ? textoONulo(m.role_id, 'name') : null;
          const g = esObjeto(m.group_id) ? m.group_id : null;
          const padre = g ? (textoONulo(g, 'parent_path') ?? '') : '';
          const nombre = g ? (textoONulo(g, 'name') ?? '') : '';
          return { rol: rol ?? '', grupo: nombre ? `${padre}/${nombre}`.replace(/\/{2,}/g, '/') : '' };
        });
    },

    async nombreDe(usuario) {
      try {
        const r = await peticion<unknown>(consulta('/identity/user', { userName: usuario }, { porPagina: 1 }), ESPERA);
        const u = Array.isArray(r) && esObjeto(r[0]) ? r[0] : null;
        const completo = u ? [textoONulo(u, 'firstname'), textoONulo(u, 'lastname')].filter(Boolean).join(' ').trim() : '';
        return completo || usuario;
      } catch {
        return usuario;
      }
    },

    procesos: () =>
      entender(peticion<unknown>('/extension/parametros/procesos', ESPERA), (c) =>
        lista(c, 'procesos')
          .map((p) => objeto(p, 'proceso'))
          .map((p) => ({
            proceso: texto(p, 'proceso', 'proceso'),
            actividades: lista(p.actividades ?? [], 'proceso.actividades').filter((a): a is string => typeof a === 'string'),
          })),
      ),

    definiciones: () => entender(peticion<unknown>('/extension/parametros/definiciones', ESPERA), (c) => lista(c, 'definiciones').map(definicionDe)),

    valores: (definicion) => {
      const filtro = parametros([['definicion', definicion]]);
      const rutaValores = `/extension/parametros/administracion/valores?${filtro}`;
      return entender(peticion<unknown>(rutaValores, ESPERA), (c) => {
        const o = objeto(c, 'valores');
        return { definicion: definicionDe(o.definicion), filas: lista(o.filas, 'valores.filas').map(filaDe) };
      });
    },

    propuestas: (estado, pagina = 0) => {
      const filtro = parametros([['estado', estado], ['p', PAGINAS[pagina] ?? PAGINAS[0]], ['c', '100']]);
      const rutaPropuestas = `/extension/parametros/propuestas?${filtro}`;
      return entender(peticion<unknown>(rutaPropuestas, ESPERA), (c) => {
        const o = objeto(c, 'propuestas');
        return {
          paraAprobar: numero(o, 'paraAprobar', 'propuestas'),
          propias: numero(o, 'propias', 'propuestas'),
          total: numero(o, 'total', 'propuestas'),
          propuestas: lista(o.propuestas, 'propuestas.propuestas').map(propuestaDe),
        };
      });
    },

    editores: (definicion) => {
      const filtro = parametros([['definicion', definicion]]);
      const rutaEditores = `/extension/parametros/editores?${filtro}`;
      return entender(peticion<unknown>(rutaEditores, ESPERA), (c) =>
        lista(c, 'editores').map((e) => {
          const o = objeto(e, 'editor');
          return {
            tipo: texto(o, 'tipo', 'editor') as Editor['tipo'],
            sujeto: textoONulo(o, 'sujeto') ?? undefined,
            incluyeSubgrupos: o.incluyeSubgrupos === true,
            proceso: textoONulo(o, 'proceso') ?? undefined,
            actividades: Array.isArray(o.actividades) ? o.actividades.filter((a): a is string => typeof a === 'string') : [],
            vigenteHasta: textoONulo(o, 'vigenteHasta'),
          };
        }),
      );
    },

    traza: (filtros, pagina) => {
      const filtro = parametros([
        ['usuario', filtros.usuario],
        ['claveNegocio', filtros.claveNegocio],
        ['desde', filtros.desde],
        ['hasta', filtros.hasta],
        ['p', PAGINAS[pagina] ?? PAGINAS[0]],
        ['c', POR_PAGINA_DE_TRAZA],
      ]);
      const rutaTraza = `/extension/parametros/traza?${filtro}`;
      return entender(peticion<unknown>(rutaTraza, ESPERA), (c) => {
        const elementos = lista(c, 'traza').map(trazaDe);
        return { elementos, hayMas: elementos.length >= LLENA };
      });
    },

    verificar: (completa) => {
      const rutaVerificacion = completa ? '/extension/parametros/traza/verificacion?completa=true' : '/extension/parametros/traza/verificacion';
      return entender(peticion<unknown>(rutaVerificacion, ESPERA), (c) => {
        const o = objeto(c, 'verificación');
        if (o.coherente === true) {
          return { coherente: true, entradas: numeroONulo(o, 'entradas') ?? 0, desde: numeroONulo(o, 'desde'), hasta: numeroONulo(o, 'hasta') };
        }
        const p = objeto(o.primeraQueNoCasa, 'verificación.primeraQueNoCasa');
        return {
          coherente: false,
          primeraQueNoCasa: { id: numero(p, 'id', 'verificación'), fechaHora: texto(p, 'fechaHora', 'verificación'), claveNegocio: texto(p, 'claveNegocio', 'verificación') },
        };
      });
    },

    delegaciones: () => entender(peticion<unknown>('/extension/parametros/delegaciones', ESPERA), (c) => lista(c, 'delegaciones').map(delegacionDe)),

    organizacion: (tipo, q) => {
      const filtro = parametros([['tipo', tipo], ['q', q]]);
      const rutaOrganizacion = `/extension/parametros/organizacion?${filtro}`;
      return entender(peticion<unknown>(rutaOrganizacion, ESPERA), (c) =>
        lista(c, 'organización').map((r) => {
          const o = objeto(r, 'organización');
          return { id: numero(o, 'id', 'organización'), nombre: texto(o, 'nombre', 'organización') };
        }),
      );
    },

    nombreDeSujeto: (tipo, id) => nombreDeSujetoPorId(tipo, id),

    async cambiar(p) {
      const cuerpo = {
        accion: p.accion,
        definicion: p.definicion,
        ambito: p.ambito,
        codigoPadre: p.codigoPadre ?? '*',
        codigo: p.codigo ?? '*',
        datos: p.datos ?? {},
        persistenceVersion: p.persistenceVersion,
        motivo: p.motivo,
      };
      return resultadoDe(await escrito(peticion<unknown>('/extension/parametros/cambios', { metodo: 'POST', cuerpo, ...ESPERA })));
    },

    async decidir(propuesta, decision, comentario) {
      const cuerpo = { propuesta: propuesta.id, decision, comentario, persistenceVersion: propuesta.persistenceVersion };
      await escrito(peticion<unknown>('/extension/parametros/propuestas/decision', { metodo: 'POST', cuerpo, ...ESPERA }));
    },

    async vistaPreviaDeImportacion(csv) {
      return vistaPreviaDe(await escrito(peticion<unknown>('/extension/parametros/importaciones', { metodo: 'POST', cuerpo: { csv, confirmar: false }, ...ESPERA })));
    },

    async importar(csv, motivo, huella) {
      const respuesta = await escrito(peticion<unknown>('/extension/parametros/importaciones', { metodo: 'POST', cuerpo: { csv, motivo, confirmar: true, huella }, ...ESPERA }));
      const o = objeto(respuesta, 'importación');
      const v = vistaPreviaDe({ ...o, huella: '' });
      return { lote: texto(o, 'lote', 'importación'), resumen: v.resumen, filas: v.filas };
    },

    async delegar(datos, motivo) {
      const cuerpo = { accion: 'DELEGAR', motivo, ...datos };
      return resultadoDe(await escrito(peticion<unknown>('/extension/parametros/delegaciones', { metodo: 'POST', cuerpo, ...ESPERA })));
    },

    async revocar(d, motivo) {
      const cuerpo = {
        accion: 'REVOCAR',
        proceso: d.proceso,
        motivo,
        tipoSujeto: d.tipoSujeto,
        sujetoUsuarioId: d.sujetoUsuarioId ?? undefined,
        sujetoGrupoId: d.sujetoGrupoId ?? undefined,
        sujetoRolId: d.sujetoRolId ?? undefined,
      };
      await escrito(peticion<unknown>('/extension/parametros/delegaciones', { metodo: 'POST', cuerpo, ...ESPERA }));
    },

    /** «Dónde se usa» (`GET parametros/usos`): los lugares que usan una definición y, por opción, los expedientes que la eligieron. */
    usos: (definicion) => {
      const filtro = parametros([['definicion', definicion]]);
      const rutaUsos = `/extension/parametros/usos?${filtro}`;
      return entender(peticion<unknown>(rutaUsos, ESPERA), (c) => {
        const o = objeto(c, 'usos');
        const otros = esObjeto(o.otros) ? { guardados: texto(o.otros, 'guardados', 'usos.otros'), enCurso: texto(o.otros, 'enCurso', 'usos.otros') } : undefined;
        return {
          lugares: lista(o.lugares, 'usos.lugares').map((l) => {
            const x = objeto(l, 'usos.lugares');
            return { tipo: texto(x, 'tipo', 'usos.lugares'), titulo: texto(x, 'titulo', 'usos.lugares'), detalle: texto(x, 'detalle', 'usos.lugares') };
          }),
          expedientes: lista(o.expedientes, 'usos.expedientes').map((e) => {
            const x = objeto(e, 'usos.expedientes');
            const etiqueta = textoONulo(x, 'etiqueta');
            return {
              codigo: typeof x.codigo === 'string' ? x.codigo : '',
              guardados: texto(x, 'guardados', 'usos.expedientes'),
              enCurso: texto(x, 'enCurso', 'usos.expedientes'),
              ...(etiqueta !== null ? { etiqueta } : {}),
              ...(x.truncado === true ? { truncado: true } : {}),
              ...(x.fueraDeLista === true ? { fueraDeLista: true } : {}),
              ...(x.sinElegir === true ? { sinElegir: true } : {}),
            };
          }),
          ...(otros ? { otros } : {}),
        };
      });
    },
  };
}
