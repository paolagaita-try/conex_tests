package {{GRUPO}}.parametros

import java.sql.Connection
import java.sql.PreparedStatement
import java.sql.ResultSet

/**
 * Expedientes por opción de una definición («Dónde se usa»): lo que el kit no puede saber porque depende de DÓNDE
 * guarda este proceso la elección de cada expediente. La API lo carga por nombre (`usos.conteo.clase` de
 * `bonita-project/parametros/configuration.properties`) y llama a {@link #conteos}; solo lee.
 *
 * Se declara una consulta por definición en {@link #CONSULTAS}: un `SELECT` de UNA fila por expediente con las
 * columnas `opcion`, `estado` y `expediente` (y, si hace falta filtrar por definición, `definicion`), sobre tablas
 * que genera el motor del BDM. NO se agrupa en SQL (la base del runtime se abre con IGNORECASE en H2; PostgreSQL
 * no): se suma aquí, sensible a mayúsculas, igual en los dos motores.
 *
 * Criterio: un expediente cuenta como EN CURSO mientras su estado NO es terminal ({@link #TERMINALES}) y como
 * GUARDADO cuando ya lo es. Los espacios de los extremos se recortan; una opción vacía solo cuenta (con clave
 * vacía) en las definiciones de {@link #CON_SIN_ELEGIR}. Una definición sin consulta devuelve null: la API responde
 * sin expedientes.
 */
class ConteoDeOpciones {

    /** Estados en que el caso ya se cerró (de tu catálogo de estados); en minúsculas. */
    static final List<String> TERMINALES = ["completado", "cancelado"].asImmutable()

    /** Definiciones donde «todavía no eligió» es un dato: salen con la clave vacía. */
    static final Set<String> CON_SIN_ELEGIR = [] as Set

    /** definición → SELECT (opcion, estado, expediente); se rellena al incorporar cada proceso. */
    static final Map<String, String> CONSULTAS = [:].asImmutable()

    private final Map<String, String> consultas

    ConteoDeOpciones() {
        this(CONSULTAS)
    }

    ConteoDeOpciones(Map<String, String> consultas) {
        this.consultas = consultas
    }

    /** @return código de opción (recortado, sensible a mayúsculas) → [guardados: n, enCurso: m]; null si la definición no es de opciones de un expediente */
    Map<String, Map<String, Integer>> conteos(Connection conexion, String definicion) {
        String sql = consultas[definicion]
        if (sql == null) {
            return null
        }
        boolean conSinElegir = definicion in CON_SIN_ELEGIR
        Map<String, Map<String, Integer>> r = [:]
        Set<String> vistos = new HashSet<>()
        PreparedStatement ps = conexion.prepareStatement(sql)
        try {
            ResultSet rs = ps.executeQuery()
            try {
                boolean conDefinicion = (1..rs.metaData.columnCount).any { rs.metaData.getColumnLabel(it).equalsIgnoreCase("definicion") }
                while (rs.next()) {
                    // el filtro por definición se hace AQUÍ, sensible a mayúsculas (H2 con IGNORECASE casaría también otra capitalización)
                    String deLaFila = conDefinicion ? rs.getString("definicion") : null
                    if (deLaFila != null && deLaFila != definicion) {
                        continue
                    }
                    String opcion = rs.getString("opcion")?.trim() ?: ""
                    if (opcion == "" && !conSinElegir) {
                        continue
                    }
                    if (!vistos.add(rs.getLong("expediente") + "|" + opcion)) {
                        continue   // un expediente cuenta UNA vez por opción
                    }
                    String estado = rs.getString("estado")?.trim()?.toLowerCase()
                    Map<String, Integer> par = r.get(opcion, [guardados: 0, enCurso: 0])
                    String clave = (estado != null && TERMINALES.contains(estado)) ? "guardados" : "enCurso"
                    par[clave] = par[clave] + 1
                }
            } finally {
                rs.close()
            }
        } finally {
            ps.close()
        }
        r
    }
}
