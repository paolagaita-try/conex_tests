package com.trycore.parametros.api

import com.trycore.parametros.core.Membresias
import org.bonitasoft.engine.api.IdentityAPI
import org.bonitasoft.engine.identity.UserMembership
import org.bonitasoft.engine.identity.UserMembershipCriterion

/**
 * Membresías vigentes de quien llama, leídas de identityAPI en cada petición y paginadas hasta
 * agotar. El grupo se da por su ruta completa (/padre/grupo) y con los IDs del
 * grupo y del rol, que es por donde casa una delegación.
 */
class MembresiasBonita implements Membresias {

    static final int PAGINA = 100

    private final IdentityAPI identidad
    private final long idUsuario

    MembresiasBonita(IdentityAPI identidad, long idUsuario) {
        this.identidad = identidad
        this.idUsuario = idUsuario
    }

    List<Map<String, Object>> de(String usuario) {
        // El usuario técnico (`install`, id -1) no tiene membresías. Preguntarlas al motor 11.1.0 (Bonita 2026.2)
        // dispara la query `getUserMembershipsWithRole`, que no existe en su identity.queries.hbm.xml: sería un 500
        // donde toca un 403.
        if (idUsuario < 0) {
            return []
        }
        List<Map<String, Object>> todas = []
        for (int desde = 0; ; desde += PAGINA) {
            List<UserMembership> pagina = identidad.getUserMemberships(idUsuario, desde, PAGINA, UserMembershipCriterion.ROLE_NAME_ASC)
            pagina.each { todas << [grupo: ruta(it), rol: it.roleName, grupoId: it.groupId, rolId: it.roleId] }
            if (pagina.size() < PAGINA) {
                return todas
            }
        }
    }

    static String ruta(UserMembership m) {
        String padre = m.groupParentPath
        (padre ? padre : "") + "/" + m.groupName
    }
}
