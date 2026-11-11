/**
 * Las escrituras de una lista, ligadas a su contenedor: cada una arma la petición con los datos
 * CRUDOS y su versión (`acciones.ts`), la ejecuta, y si se aplicó refresca la lista y su historial. Una
 * petición que no pasó la validación previa (sin motivo, sin nombre) no llega al kit.
 */
import type { Kit } from './kit';
import {
  bien,
  pedir,
  peticionAnadir,
  peticionDeAmbito,
  peticionDeEstado,
  peticionEditar,
  peticionOrdenar,
  type Resultado,
} from './acciones';
import type { Ambito } from './ambitos';
import type { ValoresAdministracion } from './tipos';

interface Contexto {
  valores: ValoresAdministracion;
  ambito: Ambito;
  padre: string | null;
}

export function acciones(
  kit: Kit,
  contexto: () => Contexto | null,
  refrescar: (definicion: string) => Promise<void>,
  historial: () => Promise<void>,
  yo?: string,
) {
  async function con(construir: (c: Contexto) => Parameters<typeof pedir>[1]): Promise<Resultado> {
    const c = contexto();
    if (!c) return bien();
    const r = await pedir(kit, construir(c), yo);
    // Sin respuesta no se sabe si se aplicó: se relee igual que tras un guardado, antes de que nadie repita.
    if (r.ok || r.explicacion.desconocido) {
      await refrescar(c.valores.definicion.codigo);
      void historial();
    }
    return r;
  }
  return {
    editar: (d: { clave: string; etiqueta: string; ayuda: string; motivo: string }) =>
      con((c) => peticionEditar({ valores: c.valores, ambito: c.ambito, ...d })),
    anadir: (d: { codigo: string; etiqueta: string; ayuda: string; motivo: string }) =>
      con((c) => peticionAnadir({ valores: c.valores, ambito: c.ambito, codigoPadre: c.padre, ...d })),
    cambiarEstado: (d: { clave: string; activar: boolean; motivo: string }) =>
      con((c) => peticionDeEstado({ valores: c.valores, ambito: c.ambito, ...d })),
    ordenar: (d: { ordenNuevo: string[]; motivo: string }) =>
      con((c) => peticionOrdenar({ valores: c.valores, ambito: c.ambito, codigoPadre: c.padre, ...d })),
    versionPropia: (motivo: string) =>
      con((c) => peticionDeAmbito({ valores: c.valores, ambito: c.ambito, accion: 'CREAR_VERSION_PROPIA', motivo })),
    volverAHeredar: (motivo: string) =>
      con((c) => peticionDeAmbito({ valores: c.valores, ambito: c.ambito, accion: 'VOLVER_A_HEREDAR', motivo })),
  };
}
