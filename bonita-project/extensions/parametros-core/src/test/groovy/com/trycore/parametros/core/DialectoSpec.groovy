package com.trycore.parametros.core

import spock.lang.Specification

import java.lang.reflect.Proxy
import java.sql.DatabaseMetaData

/**
 * Un motor que el kit no sabe hablar se rechaza antes de emitir SQL (Oracle y SQL Server no
 * están soportados todavía; fallo cerrado).
 */
class DialectoSpec extends Specification {

    def "un motor sin dialecto se rechaza sin emitir SQL"() {
        given:
        def meta = (DatabaseMetaData) Proxy.newProxyInstance(DatabaseMetaData.classLoader, [DatabaseMetaData] as Class[],
                { p, m, a -> m.name == "getDatabaseProductName" ? producto : null })
        def espia = new BdPrueba.Espia(null, [getMetaData: { a -> meta }])

        when:
        Dialecto.de(BdPrueba.Espia.conexion(espia))

        then:
        thrown(UnsupportedOperationException)
        espia.llamadas == ["getMetaData"]

        where:
        producto << ["Oracle", "Microsoft SQL Server", "MySQL", ""]
    }
}
