package com.trycore.parametros.api

import com.trycore.parametros.core.Autor
import com.trycore.parametros.core.Familia
import com.trycore.parametros.core.Organizacion
import org.bonitasoft.engine.api.IdentityAPI
import org.bonitasoft.engine.api.ProcessAPI
import org.bonitasoft.engine.exception.NotFoundException
import org.bonitasoft.engine.search.SearchOptionsBuilder

/**
 * La organización de Bonita, leída EN VIVO en cada petición por identityAPI: lo que
 * una delegación guarda por ID se resuelve aquí, así que renombrar un grupo no la rompe.
 */
class OrganizacionBonita implements Organizacion {

    static final int MAXIMO = 20

    private final IdentityAPI identidad
    private final ProcessAPI procesos
    private final Collection<String> actoresInternos

    OrganizacionBonita(IdentityAPI identidad, ProcessAPI procesos = null, Collection<String> actoresInternos = []) {
        this.identidad = identidad
        this.procesos = procesos
        this.actoresInternos = actoresInternos
    }

    /** Por el mapeo de actores del motor, con la lista blanca interna de la configuración. */
    boolean soloCliente(Autor autor) {
        autor.usuarioId != null && procesos != null && Familia.soloCliente(actoresInternos, new MapeoBonita(procesos, autor.usuarioId))
    }

    String rutaDeGrupo(Long id) { o { identidad.getGroup(id).path } }

    Long idDeUsuario(String usuario) { o { identidad.getUserByUserName(usuario).id } }

    boolean existeUsuario(Long id) { o { identidad.getUser(id) } != null }

    boolean existeRol(Long id) { o { identidad.getRole(id) } != null }

    String nombreDeUsuario(Long id) { o { identidad.getUser(id).userName } }

    String nombreDeRol(Long id) { o { identidad.getRole(id).name } }

    List<Map<String, Object>> buscar(String tipo, String q) {
        def opciones = new SearchOptionsBuilder(0, MAXIMO).searchTerm(q).done()
        switch (tipo) {
            case "usuario": return identidad.searchUsers(opciones).result.collect { [id: it.id, nombre: it.userName] }
            case "grupo": return identidad.searchGroups(opciones).result.collect { [id: it.id, nombre: it.path] }
            default: return identidad.searchRoles(opciones).result.collect { [id: it.id, nombre: it.name] }
        }
    }

    /** Lo que no existe es null, no una excepción: una delegación a un grupo borrado simplemente no casa. */
    private static <T> T o(Closure<T> leer) {
        try {
            leer()
        } catch (NotFoundException ignorada) {
            null
        }
    }
}
