package com.trycore.parametros.core

/**
 * Lo que puede quien llama en ESTA petición: la superadministración, o las
 * delegaciones vigentes que casan con él, leídas en el paso 0. Un delegado nunca toca el ámbito global
 * ni las definiciones, ni delega, ni revoca, ni restablece la semilla (no re-delega).
 */
final class Permisos {

    static final Set<String> SOLO_SUPERADMINISTRACION = ["CREAR_DEFINICION", "EDITAR_DEFINICION", "DELEGAR", "REVOCAR",
                                                         "RESTABLECER_SEMILLA"] as Set

    final boolean superadministracion
    final List<Map> delegaciones

    Permisos(boolean superadministracion, List<Map> delegaciones) {
        this.superadministracion = superadministracion
        this.delegaciones = delegaciones.asImmutable()
    }

    boolean puedeEscribir(Cambio c) {
        superadministracion || enAlcance(c.accion, c.proceso, c.actividad)
    }

    /** Aprobar o rechazar una propuesta (fila con nombres del BDM): por su ámbito y su acción. */
    boolean puedeResolver(Map propuesta) {
        superadministracion || enAlcance((String) propuesta.accion, (String) propuesta.proceso, (String) propuesta.actividad)
    }

    boolean puedeImportar() {
        superadministracion || !delegaciones.isEmpty()
    }

    private boolean enAlcance(String accion, String proceso, String actividad) {
        !(accion in SOLO_SUPERADMINISTRACION) && proceso != "*" && delegaciones.any { Delegaciones.cubre(it, proceso, actividad) }
    }
}
