package com.trycore.parametros.core

import java.sql.Connection

/** De dónde sale una conexión nueva: en el runtime, NotManagedBizDataDS por JNDI. Quien abre, cierra. */
interface Conexiones {
    Connection abrir()
}
