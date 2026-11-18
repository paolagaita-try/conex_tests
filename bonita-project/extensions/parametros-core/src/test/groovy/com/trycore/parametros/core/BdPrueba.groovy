package com.trycore.parametros.core

import groovy.json.JsonSlurper

import java.lang.reflect.InvocationHandler
import java.lang.reflect.InvocationTargetException
import java.lang.reflect.Method
import java.lang.reflect.Proxy
import java.sql.Clob
import java.sql.Connection
import java.sql.DriverManager
import java.sql.ResultSet

/**
 * Utilidades de prueba contra base de datos real (solo las usan los tests). Las URLs llegan con
 * -Dkit.h2.url / -Dkit.pg.url; el esquema lo crea el motor (SchemaManagerUpdate del bundle) a partir del BDM.
 */
class BdPrueba {

    /** Manifiesto del paquete, escrito a mano: la expectativa de «todas las tablas del kit». Vive en los recursos de prueba. */
    static final File MANIFIESTO = recurso("/fixtures/paquete-v1.json")

    /** Un fichero de src/test/resources: las pruebas nunca leen fuera del módulo. */
    static File recurso(String ruta) {
        URL url = BdPrueba.getResource(ruta)
        if (url == null) {
            throw new IllegalStateException("falta el recurso de prueba " + ruta)
        }
        new File(url.toURI())
    }

    static List<String> tablasDelKit() {
        Map m = (Map) new JsonSlurper().parse(MANIFIESTO)
        ((Map) m.entidades).keySet().collect { String e -> e.toUpperCase() }.sort()
    }

    static Connection conectar(String motor) {
        if (motor == "h2") {
            return DriverManager.getConnection(System.getProperty("kit.h2.url"), "sa", "")
        }
        DriverManager.getConnection(System.getProperty("kit.pg.url"))
    }

    static void vaciarKit(Connection c) {
        boolean ac = c.autoCommit
        c.autoCommit = true
        tablasDelKit().each { c.createStatement().withCloseable { s -> s.executeUpdate("DELETE FROM " + it) } }
        c.autoCommit = ac
    }

    /** Contenido completo de todas las tablas del kit, fila a fila, para comparar antes y después. */
    static Map<String, List<Map>> foto(Connection c) {
        tablasDelKit().collectEntries { String t -> [(t): filas(c, "SELECT * FROM " + t + " ORDER BY PERSISTENCEID")] }
    }

    static List<Map> filas(Connection c, String sql, List params = []) {
        c.prepareStatement(sql).withCloseable { ps ->
            params.eachWithIndex { Object v, int i -> ps.setObject(i + 1, v) }
            ps.executeQuery().withCloseable { ResultSet rs ->
                List<Map> r = []
                int n = rs.metaData.columnCount
                while (rs.next()) {
                    Map f = [:]
                    (1..n).each { int i ->
                        Object v = rs.getObject(i)
                        f[rs.metaData.getColumnLabel(i).toUpperCase()] = v instanceof Clob ? ((Clob) v).characterStream.text : v
                    }
                    r << f
                }
                r
            }
        }
    }

    static long valorActualDeLaSecuencia(Connection c, String motor) {
        String sql = motor == "h2"
                ? "SELECT CURRENT_VALUE FROM INFORMATION_SCHEMA.SEQUENCES WHERE SEQUENCE_NAME = 'HIBERNATE_SEQUENCE'"
                : "SELECT last_value FROM hibernate_sequence"
        ((Number) filas(c, sql)[0].values().first()).longValue()
    }

    /**
     * Conexión espía: registra cada método invocado; si hay una real detrás, delega en ella, y
     * {@code alterar} permite sustituir la respuesta de un método concreto.
     */
    static class Espia implements InvocationHandler {
        final List<String> llamadas = Collections.synchronizedList([])
        final Object real
        final Map<String, Closure> alterar

        Espia(Object real = null, Map<String, Closure> alterar = [:]) {
            this.real = real
            this.alterar = alterar
        }

        static Connection conexion(Espia e) {
            (Connection) Proxy.newProxyInstance(Connection.classLoader, [Connection] as Class[], e)
        }

        @Override
        Object invoke(Object proxy, Method m, Object[] args) {
            llamadas << m.name
            if (alterar.containsKey(m.name)) {
                return alterar[m.name].call(args)
            }
            if (real == null) {
                throw new AssertionError("se tocó la conexión: ${m.name}")
            }
            try {
                m.invoke(real, args)
            } catch (InvocationTargetException ex) {
                throw ex.cause
            }
        }
    }
}
