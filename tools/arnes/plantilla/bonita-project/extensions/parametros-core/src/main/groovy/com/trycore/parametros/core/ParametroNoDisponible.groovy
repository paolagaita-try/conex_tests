package com.trycore.parametros.core

/**
 * usar() no tiene valor válido ni fallback declarado que dar: el caso se detiene a
 * la vista en esa tarea en lugar de seguir con un valor inventado.
 */
class ParametroNoDisponible extends RuntimeException {
    ParametroNoDisponible(String mensaje) {
        super(mensaje)
    }
}
