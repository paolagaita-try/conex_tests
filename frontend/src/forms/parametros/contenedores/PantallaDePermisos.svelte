<script lang="ts">
  /**
   * Permisos y nueva delegación: lee las delegaciones, resuelve nombres a identificadores al
   * enviar y convierte revocar, prorrogar y delegar en órdenes al kit. Delegar y prorrogar quedan como
   * PROPUESTA (doble control); revocar surte efecto en la petición siguiente.
   */
  import { onMount } from 'svelte';
  import { bien, mal, type Resultado } from '../acciones';
  import { completarSujetos, idsDeSujetos } from '../carga';
  import { etiquetasUnicas, nombreDeGrupo, nombreDeRol } from '../nombres';
  import { usarAplicacion } from '../aplicacion';
  import type { DatosDeDelegacion } from '../kit';
  import { explicar } from '../fallos';
  import { nombreDeProceso } from '../nombres';
  import { construirPermisos, opcionesDeActividad, type DelegacionVM, type Par } from '../permisos';
  import type { Delegacion } from '../tipos';
  import ErrorDeLectura from '../componentes/ErrorDeLectura.svelte';
  import VistaNuevaDelegacion, { type FormularioDeDelegacion } from '../vistas/VistaNuevaDelegacion.svelte';
  import VistaPermisos from '../vistas/VistaPermisos.svelte';
  import * as T from '../textos';

  interface Props {
    nueva: boolean;
    onnueva: () => void;
    onpermisos: () => void;
  }
  const props: Props = $props();
  const app = usarAplicacion();
  const ctx = $derived(app.contexto());

  let delegaciones = $state<Delegacion[] | 'cargando' | 'error'>('cargando');

  async function cargar(trasEscritura = false): Promise<void> {
    try {
      const leidas = await app.kit.delegaciones();
      // Quien no vino en la búsqueda de 20 se pide por su id: nunca «una persona» si el id existe.
      if (ctx.capacidades.perfil === 'superadministracion') await completarSujetos(app.kit, ctx.sujetos, idsDeSujetos(leidas as unknown as Array<Record<string, unknown>>));
      delegaciones = leidas;
      app.avisarRefresco('delegaciones', null);
    } catch {
      // Tras una escritura se conserva la lista vieja y se avisa; al abrir no hay nada que conservar.
      if (trasEscritura && delegaciones !== 'cargando' && delegaciones !== 'error') app.avisarRefresco('delegaciones', () => cargar(true));
      else delegaciones = 'error';
    }
  }
  onMount(() => void cargar());

  const permisos = $derived(delegaciones === 'cargando' || delegaciones === 'error' ? null : construirPermisos(delegaciones, ctx.sujetos, ctx.nombres));
  // Se recupera por CONTENIDO, no por identidad: el modelo se reconstruye cuando cambia lo leído, y dos
  // delegaciones con el mismo texto en todos sus campos son la misma para quien las lee.
  const cruda = (vm: DelegacionVM): Par | undefined =>
    [...(permisos?.vigentes ?? []), ...(permisos?.vencidas ?? [])].find((p) => JSON.stringify(p.vm) === JSON.stringify(vm));

  async function revocar(vm: DelegacionVM, motivo: string): Promise<Resultado> {
    const par = cruda(vm);
    if (!par) return mal({ campo: 'general', mensaje: T.FALLO_NO_EXISTE });
    try {
      await app.kit.revocar(par.cruda, motivo.trim());
    } catch (e) {
      const x = explicar(e, ctx.sesion.usuario);
      if (x.desconocido) await cargar(true);
      return mal(x);
    }
    await cargar(true);
    return bien();
  }

  async function prorrogar(vm: DelegacionVM, hasta: string, motivo: string): Promise<Resultado> {
    const par = cruda(vm);
    if (!par) return mal({ campo: 'general', mensaje: T.FALLO_NO_EXISTE });
    const d = par.cruda;
    const datos: DatosDeDelegacion = {
      tipoSujeto: d.tipoSujeto,
      incluyeSubgrupos: d.incluyeSubgrupos,
      proceso: d.proceso,
      actividades: d.actividades,
      vigenteHasta: `${hasta}T23:59:59.000Z`,
      ...(d.sujetoUsuarioId !== null ? { sujetoUsuarioId: d.sujetoUsuarioId } : {}),
      ...(d.sujetoGrupoId !== null ? { sujetoGrupoId: d.sujetoGrupoId } : {}),
      ...(d.sujetoRolId !== null ? { sujetoRolId: d.sujetoRolId } : {}),
      ...(d.vigenteDesde ? { vigenteDesde: d.vigenteDesde } : {}),
    };
    try {
      await app.kit.delegar(datos, motivo.trim());
    } catch (e) {
      const x = explicar(e, ctx.sesion.usuario);
      if (x.desconocido) await app.refrescar('');
      return mal(x);
    }
    await app.refrescar('');
    return bien(true);
  }

  const procesos = $derived(
    ctx.datos.procesos.map((p) => ({ valor: p.proceso, nombre: nombreDeProceso(p.proceso), actividades: opcionesDeActividad(p.actividades) })),
  );
  // Lo elegido se identifica por su ID: cada búsqueda anota «etiqueta → id» y el envío resuelve por ahí (dos «Ana Ruiz» son dos ids).
  const registro = { usuario: new Map<string, number>(), grupo: new Map<string, number>(), rol: new Map<string, number>() };
  async function buscarPersonas(q: string): Promise<string[]> {
    const r = await app.kit.organizacion('usuario', q);
    const nombres = await Promise.all(r.map(async (x) => ({ id: x.id, login: x.nombre, nombre: await app.kit.nombreDe(x.nombre) })));
    // Siempre con el usuario: la etiqueta identifica a UNA persona, aunque otra búsqueda traiga a su homónima.
    return nombres.map((x) => {
      const etiqueta = x.nombre === x.login ? x.login : `${x.nombre} · ${x.login}`;
      registro.usuario.set(etiqueta, x.id);
      return etiqueta;
    });
  }
  async function buscarGrupos(q: string): Promise<string[]> {
    const r = etiquetasUnicas((await app.kit.organizacion('grupo', q)).map((x) => ({ id: x.id, nombre: nombreDeGrupo(x.nombre), extra: x.nombre })));
    for (const x of r) registro.grupo.set(x.nombre, x.id);
    return r.map((x) => x.nombre);
  }
  async function buscarRoles(q: string): Promise<string[]> {
    const r = etiquetasUnicas((await app.kit.organizacion('rol', q)).map((x) => ({ id: x.id, nombre: nombreDeRol(x.nombre), extra: x.nombre })));
    for (const x of r) registro.rol.set(x.nombre, x.id);
    return r.map((x) => x.nombre);
  }
  const buscar = (mapa: Map<string, number>, etiqueta: string): number | undefined => mapa.get(etiqueta);

  async function delegar(f: FormularioDeDelegacion): Promise<Resultado> {
    // Si la etiqueta ya no se reconoce (nunca debería), no se envía un sujeto equivocado ni vacío.
    if ((f.tipo === 'USUARIO' && registro.usuario.get(f.usuario) === undefined) || ((f.tipo === 'GRUPO' || f.tipo === 'GRUPO_ROL') && registro.grupo.get(f.grupo) === undefined) || ((f.tipo === 'ROL' || f.tipo === 'GRUPO_ROL') && registro.rol.get(f.rol) === undefined)) {
      return mal({ campo: 'general', mensaje: T.ERROR_ELIGE_PERSONA });
    }
    const datos: DatosDeDelegacion = {
      tipoSujeto: f.tipo,
      incluyeSubgrupos: f.subgrupos,
      proceso: f.proceso,
      actividades: f.actividades,
      ...(f.vigencia === 'hasta' ? { vigenteHasta: `${f.hasta}T23:59:59.000Z` } : {}),
      ...(f.tipo === 'USUARIO' ? { sujetoUsuarioId: buscar(registro.usuario, f.usuario) } : {}),
      ...(f.tipo === 'GRUPO' || f.tipo === 'GRUPO_ROL' ? { sujetoGrupoId: buscar(registro.grupo, f.grupo) } : {}),
      ...(f.tipo === 'ROL' || f.tipo === 'GRUPO_ROL' ? { sujetoRolId: buscar(registro.rol, f.rol) } : {}),
    };
    try {
      await app.kit.delegar(datos, f.motivo.trim());
    } catch (e) {
      const x = explicar(e, ctx.sesion.usuario);
      if (x.desconocido) await app.refrescar('');
      return mal(x);
    }
    await app.refrescar('');
    props.onpermisos();
    return bien(true);
  }
</script>

{#if ctx.sujetosFallo}
  <ErrorDeLectura titulo={T.ERROR_ORGANIZACION} cuerpo={T.ERROR_ORGANIZACION_CUERPO} prueba="organizacion-error" />
{:else if props.nueva}
  <VistaNuevaDelegacion
    {procesos}
    {buscarPersonas}
    {buscarGrupos}
    {buscarRoles}
    {delegar}
    oncancelar={props.onpermisos}
  />
{:else if delegaciones === 'error'}
  <ErrorDeLectura onreintentar={() => void cargar()} prueba="permisos-error" />
{:else if permisos}
  <VistaPermisos
    vigentes={permisos.vigentes.map((p) => p.vm)}
    vencidas={permisos.vencidas.map((p) => p.vm)}
    ondelegar={props.onnueva}
    {revocar}
    {prorrogar}
  />
{:else}
  <p role="status">{T.CARGANDO}</p>
{/if}
