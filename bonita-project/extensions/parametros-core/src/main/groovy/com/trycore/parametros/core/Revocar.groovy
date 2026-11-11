package com.trycore.parametros.core

/**
 * REVOCAR: desactiva la delegación de un sujeto en un proceso, directo —quitar
 * permisos no amplía a nadie—. Surte efecto en la petición siguiente: la autorización se lee en vivo.
 */
class Revocar extends Delegar {

    Revocar(Cambio cambio, Filas f) {
        super(cambio, f)
    }

    void comprobar() {
        Map d = cambio.datos
        if (!(d.tipoSujeto in Delegaciones.TIPOS)) {
            falla("datos.tipoSujeto", "«${d.tipoSujeto}» no es uno de ${Delegaciones.TIPOS}")
        }
        guardada = la((String) d.tipoSujeto, id(d.sujetoUsuarioId), id(d.sujetoGrupoId), id(d.sujetoRolId))
        if (guardada == null || !guardada.ACTIVO) {
            falla("datos", "no hay una delegación activa de ese sujeto en «${cambio.proceso}»")
        }
        columnas = [ACTIVO: false]
    }
}
