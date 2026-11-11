package com.trycore.parametros.core

/** Una tabla o columna fuera del paquete del kit: se lanza antes de tocar la conexión. */
class PuertaCerrada extends RuntimeException {
    PuertaCerrada(String mensaje) {
        super(mensaje)
    }
}
