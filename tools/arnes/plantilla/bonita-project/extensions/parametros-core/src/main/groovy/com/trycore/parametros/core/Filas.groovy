package com.trycore.parametros.core

import java.sql.Clob
import java.sql.Connection
import java.sql.PreparedStatement
import java.sql.ResultSet
import java.sql.Savepoint
import java.sql.Types

/**
 * El único punto por el que parametros-core emite SQL. Toda tabla y columna pasa antes por la
 * PuertaUnica, así que un nombre fuera del paquete falla sin tocar la conexión. SQL sin comillas:
 * PostgreSQL guarda los identificadores en minúsculas y H2 en mayúsculas (medido), y solo sin
 * comillas resuelven en los dos. Las filas se devuelven con las columnas en mayúsculas y el texto
 * largo (CLOB en H2, text en PostgreSQL) como String.
 */
final class Filas {

    private final Connection c
    private final Dialecto d

    Filas(Connection c, Dialecto d) {
        this.c = c
        this.d = d
    }

    /** Inserta con el siguiente identificador de hibernate_sequence y versión 0; devuelve el identificador. */
    long insertar(String tabla, Map<String, Object> valores) {
        String t = PuertaUnica.tabla(tabla)
        List<String> cols = valores.keySet().collect { PuertaUnica.columna(t, it) }
        long id = d.siguienteId(c)
        String sql = "INSERT INTO " + t + " (" + (["PERSISTENCEID", "PERSISTENCEVERSION"] + cols).join(", ") +
                ") VALUES (" + (["?", "0"] + cols.collect { "?" }).join(", ") + ")"
        ejecutar(sql, [id] + valores.values().toList())
        id
    }

    /** Bloqueo optimista: solo cambia la fila si su versión es la leída; devuelve las filas cambiadas (0 o 1). */
    int actualizar(String tabla, long id, long version, Map<String, Object> valores) {
        String t = PuertaUnica.tabla(tabla)
        List<String> cols = valores.keySet().collect { PuertaUnica.columna(t, it) }
        String sql = "UPDATE " + t + " SET " + (cols.collect { it + " = ?" } + ["PERSISTENCEVERSION = PERSISTENCEVERSION + 1"]).join(", ") +
                " WHERE PERSISTENCEID = ? AND PERSISTENCEVERSION = ?"
        ejecutar(sql, valores.values().toList() + [id, version])
    }

    List<Map<String, Object>> leer(String tabla, Map<String, Object> donde, String ordenarPor = "PERSISTENCEID") {
        String t = PuertaUnica.tabla(tabla)
        String orden = PuertaUnica.columna(t, ordenarPor)
        List<String> cols = donde.keySet().collect { PuertaUnica.columna(t, it) }
        String sql = "SELECT * FROM " + t + filtro(cols) + " ORDER BY " + orden
        c.prepareStatement(sql).withCloseable { PreparedStatement ps ->
            poner(ps, donde.values().toList())
            ps.executeQuery().withCloseable { ResultSet rs -> leidas(rs) }
        }
    }

    /** Hasta {@code n} filas con {@code columna} mayor que {@code valor}, en orden de esa columna. */
    List<Map<String, Object>> leerDespuesDe(String tabla, String columna, Object valor, int n) {
        String t = PuertaUnica.tabla(tabla)
        String col = PuertaUnica.columna(t, columna)
        String sql = "SELECT * FROM " + t + " WHERE " + col + " > ? ORDER BY " + col + d.primeras(n)
        c.prepareStatement(sql).withCloseable { PreparedStatement ps ->
            poner(ps, [valor])
            ps.executeQuery().withCloseable { ResultSet rs -> leidas(rs) }
        }
    }

    /**
     * Filas que cumplen las igualdades y los rangos de texto [desde, hasta) (un extremo null no
     * acota), ordenadas por las columnas dadas de mayor a menor, a partir de {@code desde} y como
     * mucho {@code cuantas}. Sobre las fechas canónicas del kit, de ancho fijo, el orden de texto es
     * el del tiempo.
     */
    List<Map<String, Object>> buscar(String tabla, Map<String, Object> iguales, Map<String, List> rangos, List<String> ordenDescendente,
                                     int desde, int cuantas) {
        String t = PuertaUnica.tabla(tabla)
        List params = []
        String donde = condiciones(t, iguales, rangos, params)
        String orden = ordenDescendente.collect { PuertaUnica.columna(t, it) + " DESC" }.join(", ")
        String sql = "SELECT * FROM " + t + donde + " ORDER BY " + orden + d.pagina(desde, cuantas)
        c.prepareStatement(sql).withCloseable { PreparedStatement ps ->
            poner(ps, params)
            ps.executeQuery().withCloseable { ResultSet rs -> leidas(rs) }
        }
    }

    /** Cuántas filas cumplen las igualdades y los rangos de texto [desde, hasta). */
    long contar(String tabla, Map<String, Object> iguales, Map<String, List> rangos) {
        String t = PuertaUnica.tabla(tabla)
        List params = []
        String sql = "SELECT COUNT(*) FROM " + t + condiciones(t, iguales, rangos, params)
        c.prepareStatement(sql).withCloseable { PreparedStatement ps ->
            poner(ps, params)
            ps.executeQuery().withCloseable { ResultSet rs ->
                rs.next()
                rs.getLong(1)
            }
        }
    }

    private static String condiciones(String t, Map<String, Object> iguales, Map<String, List> rangos, List params) {
        List<String> partes = []
        iguales.each { k, v ->
            partes << PuertaUnica.columna(t, k) + " = ?"
            params << v
        }
        rangos.each { k, List extremos ->
            String col = PuertaUnica.columna(t, k)
            if (extremos[0] != null) {
                partes << col + " >= ?"
                params << extremos[0]
            }
            if (extremos[1] != null) {
                partes << col + " < ?"
                params << extremos[1]
            }
        }
        partes.isEmpty() ? "" : " WHERE " + partes.join(" AND ")
    }

    /**
     * Cuántos valores distintos de {@code columna} empiezan por {@code prefijo}. Con LIKE y no con un
     * rango de texto: en PostgreSQL con una intercalación de idioma la puntuación pesa menos al comparar,
     * y «IMP-2026-1001-01» queda por encima de «IMP-2026-1001.» (medido); LIKE casa el
     * prefijo carácter a carácter con cualquier intercalación.
     */
    long contarDistintosConPrefijo(String tabla, String columna, String prefijo) {
        String t = PuertaUnica.tabla(tabla)
        String col = PuertaUnica.columna(t, columna)
        String patron = prefijo.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
        c.prepareStatement("SELECT COUNT(DISTINCT " + col + ") FROM " + t + " WHERE " + col + " LIKE ? ESCAPE '!'").withCloseable { PreparedStatement ps ->
            poner(ps, [patron])
            ps.executeQuery().withCloseable { ResultSet rs ->
                rs.next()
                rs.getLong(1)
            }
        }
    }

    /**
     * Cuántas filas cumplen las igualdades y tienen {@code columna} en [desde, hasta). Sobre texto de
     * ancho fijo (las fechas canónicas del kit) el orden de texto es el del tiempo.
     */
    long contarEntre(String tabla, Map<String, Object> donde, String columna, Object desde, Object hasta) {
        String t = PuertaUnica.tabla(tabla)
        String rango = PuertaUnica.columna(t, columna)
        List<String> cols = donde.keySet().collect { PuertaUnica.columna(t, it) }
        String sql = "SELECT COUNT(*) FROM " + t + " WHERE " + (cols.collect { it + " = ?" } + [rango + " >= ?", rango + " < ?"]).join(" AND ")
        c.prepareStatement(sql).withCloseable { PreparedStatement ps ->
            poner(ps, donde.values().toList() + [desde, hasta])
            ps.executeQuery().withCloseable { ResultSet rs ->
                rs.next()
                rs.getLong(1)
            }
        }
    }

    /**
     * Ejecuta y DESHACE: lo que pasaría, sin que quede. Un savepoint de la transacción
     * en curso; pase lo que pase dentro —también una violación de restricción, que en PostgreSQL deja
     * la transacción abortada hasta volver al savepoint—, se vuelve a él.
     */
    def <T> T simular(Closure<T> accion) {
        Savepoint antes = c.setSavepoint()
        try {
            accion()
        } finally {
            c.rollback(antes)
            c.releaseSavepoint(antes)
        }
    }

    /** El candado portable: UPDATE sin cambios que toma el bloqueo de fila; devuelve las filas bloqueadas. */
    int tocar(String tabla, Map<String, Object> donde) {
        String t = PuertaUnica.tabla(tabla)
        List<String> cols = donde.keySet().collect { PuertaUnica.columna(t, it) }
        if (cols.isEmpty()) {
            throw new IllegalArgumentException("el candado necesita un filtro: no se bloquea la tabla entera")
        }
        ejecutar("UPDATE " + t + " SET PERSISTENCEVERSION = PERSISTENCEVERSION" + filtro(cols), donde.values().toList())
    }

    private static String filtro(List<String> cols) {
        cols.isEmpty() ? "" : " WHERE " + cols.collect { it + " = ?" }.join(" AND ")
    }

    private int ejecutar(String sql, List params) {
        c.prepareStatement(sql).withCloseable { PreparedStatement ps ->
            poner(ps, params)
            ps.executeUpdate()
        }
    }

    private static void poner(PreparedStatement ps, List params) {
        params.eachWithIndex { Object v, int i ->
            if (v == null) {
                ps.setNull(i + 1, Types.NULL)
            } else {
                ps.setObject(i + 1, v)
            }
        }
    }

    private static List<Map<String, Object>> leidas(ResultSet rs) {
        List<Map<String, Object>> r = []
        int n = rs.metaData.columnCount
        while (rs.next()) {
            Map<String, Object> f = [:]
            for (int i = 1; i <= n; i++) {
                Object v = rs.getObject(i)
                f[rs.metaData.getColumnLabel(i).toUpperCase()] = v instanceof Clob ? ((Clob) v).characterStream.text : v
            }
            r << f
        }
        r
    }
}
