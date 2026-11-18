package com.trycore.parametros.core

import java.time.OffsetDateTime

/** La hora del servidor, inyectable para las pruebas. */
interface Reloj {
    OffsetDateTime ahora()
}
