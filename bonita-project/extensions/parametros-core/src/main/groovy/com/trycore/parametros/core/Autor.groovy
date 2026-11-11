package com.trycore.parametros.core

import groovy.transform.EqualsAndHashCode
import groovy.transform.ToString

/**
 * Quién escribe, sus membresías vigentes ([grupo, rol] y sus IDs [grupoId, rolId]) y su ID
 * de usuario, leídos en el paso 0. Inmutable; el ID es opcional (sin organización, null).
 */
@ToString
@EqualsAndHashCode
final class Autor {
    final String usuario
    final List<Map<String, Object>> roles
    final Long usuarioId

    Autor(String usuario, List<Map<String, Object>> roles, Long usuarioId = null) {
        this.usuario = usuario
        this.roles = (roles ?: []).asImmutable()
        this.usuarioId = usuarioId
    }
}
