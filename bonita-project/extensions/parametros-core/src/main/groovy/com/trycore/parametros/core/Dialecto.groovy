package com.trycore.parametros.core

import java.sql.Connection
import java.sql.ResultSet
import java.sql.Statement

/**
 * El SQL que cambia entre motores, aislado en un único punto (reglas de SQL). Hoy,
 * el siguiente valor de hibernate_sequence: la secuencia del SequenceStyleGenerator con el que el
 * motor asigna el persistenceId de todas las entidades del BDM (incremento 1, sin reserva).
 */
enum Dialecto {

    H2("SELECT NEXT VALUE FOR hibernate_sequence"),
    POSTGRES("SELECT nextval('hibernate_sequence')")

    private final String siguiente

    private Dialecto(String siguiente) {
        this.siguiente = siguiente
    }

    /** El dialecto del motor de la conexión. Un motor sin dialecto se rechaza (fallo cerrado). */
    static Dialecto de(Connection c) {
        String producto = c.metaData.databaseProductName
        switch (producto) {
            case "H2": return H2
            case "PostgreSQL": return POSTGRES
            default: throw new UnsupportedOperationException("el kit de parámetros no tiene dialecto para «${producto}»")
        }
    }

    /** Solo las primeras n filas de una consulta ordenada (SQL:2008: lo admiten H2 1.4.200 y PostgreSQL). */
    String primeras(int n) {
        " FETCH FIRST " + n + " ROWS ONLY"
    }

    /** Una página de una consulta ordenada (SQL:2008, lo admiten H2 1.4.200 y PostgreSQL); enteros ya validados. */
    String pagina(int desde, int cuantas) {
        " OFFSET " + desde + " ROWS FETCH NEXT " + cuantas + " ROWS ONLY"
    }

    long siguienteId(Connection c) {
        c.createStatement().withCloseable { Statement s ->
            s.executeQuery(siguiente).withCloseable { ResultSet rs ->
                rs.next()
                rs.getLong(1)
            }
        }
    }
}
