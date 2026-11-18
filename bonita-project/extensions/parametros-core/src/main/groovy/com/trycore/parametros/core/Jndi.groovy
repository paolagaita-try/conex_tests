package com.trycore.parametros.core

import javax.naming.InitialContext
import javax.sql.DataSource

/**
 * La ÚNICA puerta del proyecto al datasource del BDM: la usan la API
 * del kit y el adaptador de proceso. Que ninguna otra fuente del proyecto nombre el datasource lo
 * vigila check_kit_proc_sin_escritura.py [D].
 */
final class Jndi {

    static final String NOMBRE = "java:comp/env/NotManagedBizDataDS"

    private Jndi() {}

    static Conexiones conexiones() {
        { -> ((DataSource) new InitialContext().lookup(NOMBRE)).connection } as Conexiones
    }
}
