package com.trycore.parametros.core

/**
 * La familia interna, decidida en el servidor: la superadministración,
 * quien tenga una delegación VIGENTE que case con él (administra un proceso, así que lee la
 * administración y sus pendientes; lo demás, en solo lectura), o quien esté mapeado a alguno de los
 * actores de la LISTA BLANCA de actores internos. Sin lista, nadie más es interno y lo interno responde
 * 403 (fallo cerrado): la lista protege del mapeo, y la delegación la concede la
 * superadministración de forma explícita.
 */
final class Familia {

    static final String CLAVE = "familia.interna.actores"

    private Familia() {}

    static boolean esInterna(Autor autor, Collection<String> actoresInternos, MapeoDeActores mapeo, Autorizacion autorizacion = null) {
        if (Autorizacion.esSuperadministracion(autor)) {
            return true
        }
        if (actoresInternos && mapeo.mapeadoAAlguno(actoresInternos)) {
            return true
        }
        autorizacion != null && !autorizacion.de(autor).delegaciones.isEmpty()
    }

    /**
     * Solo de la familia cliente: mapeado a algún actor que no está
     * en la lista blanca interna y a ninguno de ella. Una delegación no le da nada —ni escribir, ni
     * aprobar, ni ser interno—, aunque comparta rol o grupo con el personal. Sin lista blanca, cualquier
     * mapeo cuenta como de fuera: fallo cerrado. Quien está mapeado también a un actor interno (el
     * oficial que puede abrir una solicitud) no lo es.
     */
    static boolean soloCliente(Collection<String> actoresInternos, MapeoDeActores mapeo) {
        mapeo.mapeadoAAlgunoFueraDe(actoresInternos ?: []) && !(actoresInternos && mapeo.mapeadoAAlguno(actoresInternos))
    }

    /** La lista blanca de la configuración de la API: separada por comas; sin clave, vacía. */
    static List<String> actoresInternos(Properties configuracion) {
        (configuracion.getProperty(CLAVE) ?: "").split(",")*.trim().findAll { it }
    }
}
