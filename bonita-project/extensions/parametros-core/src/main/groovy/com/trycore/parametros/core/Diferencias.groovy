package com.trycore.parametros.core

import java.sql.Connection

/**
 * GET parametros/semilla/diferencias: lo que la semilla trae distinto de lo
 * guardado, campo a campo, con la persistenceVersion para aplicarlo por POST cambios con su motivo
 * (los metadatos de una definición, por PropuestaCambio). Lo que aún no existe no es una
 * diferencia: lo insertará la propia semilla.
 */
final class Diferencias {

    static final List<String> DE_DEFINICION = ["nombre", "descripcion", "clase", "tipoDato", "unidad", "minimo", "maximo", "decimales",
                                               "dependeDe", "impacto", "fallback", "visibilidad"].asImmutable()
    static final List<String> DE_VALOR = ["etiqueta", "ayuda", "orden", "valor", "activo"].asImmutable()

    private Diferencias() {}

    static List<Map> de(Connection c, Semilla semilla) {
        Filas f = new Filas(c, Dialecto.de(c))
        List<Map> diferencias = []
        semilla.definiciones.each { Map d ->
            Map actual = f.leer("KPDEFINICIONPARAMETRO", [CODIGO: d.CODIGO]).with { it ? it[0] : null }
            if (actual != null) {
                diferencias += comparar("DEFINICION", (String) d.CODIGO, DE_DEFINICION, d, actual)
            }
        }
        semilla.valores.each { Map v ->
            Map clave = v.subMap(["DEFINICION", "PROCESO", "ACTIVIDAD", "CODIGOPADRE", "CODIGO"])
            Map actual = f.leer("KPVALORPARAMETRO", clave).with { it ? it[0] : null }
            if (actual != null) {
                diferencias += comparar("VALOR", clave.values().join("|"), DE_VALOR, v, actual)
            }
        }
        diferencias
    }

    private static List<Map> comparar(String tipo, String clave, List<String> campos, Map enSemilla, Map actual) {
        campos.findAll { enSemilla[it.toUpperCase()] != actual[it.toUpperCase()] }.collect {
            [tipo            : tipo, clave: clave, campo: it, enSemilla: enSemilla[it.toUpperCase()], actual: actual[it.toUpperCase()],
             persistenceVersion: actual.PERSISTENCEVERSION]
        }
    }
}
