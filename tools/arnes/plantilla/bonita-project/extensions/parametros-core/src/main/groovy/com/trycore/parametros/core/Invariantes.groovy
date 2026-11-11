package com.trycore.parametros.core

/**
 * Las invariantes entre parámetros, declaradas por las semillas. CRECIENTE:
 * en cada ámbito y para cada código padre, los valores RESUELTOS —el del propio ámbito, o el heredado
 * del proceso o del global— de las definiciones de la cadena que tengan valor son estrictamente
 * crecientes, en el orden declarado. Si falta un valor, ese eslabón no se compara: no se inventa.
 *
 * Se comprueban sobre lo que deja la escritura, por la misma conexión de la transacción, así que la
 * herencia la da la propia base de datos y no un cálculo aparte. Solo los ámbitos que dependen del
 * tocado: un ámbito sin valores propios de la cadena resuelve igual que el de arriba.
 */
final class Invariantes {

    static final Invariantes NINGUNA = new Invariantes([])
    static final Set<String> TIPOS = ["CRECIENTE"] as Set
    static final Set<String> TIPOS_DE_DATO = ["ENTERO", "DECIMAL", "PORCENTAJE", "MONTO"] as Set

    private static final String TODO = "*"

    final List<Invariante> todas

    Invariantes(List<Invariante> todas) {
        this.todas = todas.asImmutable()
    }

    /** Tras el paso 4: null si se cumplen; si no, el rechazo VALIDACION que nombra los dos valores. */
    Resultado comprobar(Filas f, Cambio tocado) {
        for (Invariante inv : todas.findAll { tocado.definicion in it.definiciones }) {
            List<Map> filas = inv.definiciones.collectMany { f.leer("KPVALORPARAMETRO", [DEFINICION: it]) }
            Map<String, String> nombres = inv.definiciones.collectEntries { String d ->
                [(d): f.leer("KPDEFINICIONPARAMETRO", [CODIGO: d]).with { it ? (String) it[0].NOMBRE : d }]
            }
            String fallo = incumplimiento(inv, filas, nombres, { List<String> ambito -> bajo(ambito, tocado.proceso, tocado.actividad) },
                    tocado.codigoPadre)
            if (fallo != null) {
                return Validacion.rechazo("invariante", fallo)
            }
        }
        null
    }

    /**
     * El primer incumplimiento de {@code inv} entre las filas dadas (columnas del BDM en mayúsculas),
     * en los ámbitos que acepta {@code ambitoQueCuenta} y para {@code soloPadre} (todos si es null).
     */
    static String incumplimiento(Invariante inv, List<Map> filas, Map<String, String> nombres, Closure<Boolean> ambitoQueCuenta,
                                 String soloPadre) {
        List<Map> activas = filas.findAll { it.ACTIVO && it.VALOR != null && it.DEFINICION in inv.definiciones }
        Set<List<String>> ambitos = ([[TODO, TODO]] + activas.collect { [(String) it.PROCESO, (String) it.ACTIVIDAD] }).toSet()
        Set<String> padres = soloPadre != null ? [soloPadre] as Set : activas.collect { (String) it.CODIGOPADRE }.toSet()
        for (List<String> ambito : ambitos.sort { it.join("|") }.findAll(ambitoQueCuenta)) {
            for (String padre : padres.sort()) {
                List<Map> presentes = inv.definiciones.collect { resuelto(activas, it, ambito, padre) }.findAll { it != null }
                for (int i = 0; i + 1 < presentes.size(); i++) {
                    Map a = presentes[i], b = presentes[i + 1]
                    if (new BigDecimal((String) b.VALOR) <= new BigDecimal((String) a.VALOR)) {
                        return "«${nombres[b.DEFINICION] ?: b.DEFINICION}» (${b.VALOR}) tiene que ser mayor que «${nombres[a.DEFINICION] ?: a.DEFINICION}» (${a.VALOR})" +
                                " ${donde(ambito, padre)}".toString()
                    }
                }
            }
        }
        null
    }

    /** El valor de {@code definicion} que ve el ámbito: el suyo, el de su proceso o el global. */
    private static Map resuelto(List<Map> activas, String definicion, List<String> ambito, String padre) {
        List<List<String>> cadena = [ambito, [ambito[0], TODO], [TODO, TODO]].unique()
        for (List<String> a : cadena) {
            Map fila = activas.find { it.DEFINICION == definicion && it.PROCESO == a[0] && it.ACTIVIDAD == a[1] && it.CODIGOPADRE == padre }
            if (fila != null) {
                return fila
            }
        }
        null
    }

    /** Los ámbitos cuya resolución depende de un cambio en (proceso, actividad). */
    private static boolean bajo(List<String> ambito, String proceso, String actividad) {
        proceso == TODO || (ambito[0] == proceso && (actividad == TODO || ambito[1] == actividad))
    }

    private static String donde(List<String> ambito, String padre) {
        String a = ambito == [TODO, TODO] ? "en el ámbito global" : ambito[1] == TODO ? "en el proceso «${ambito[0]}»" :
                "en la actividad «${ambito[1]}» de «${ambito[0]}»"
        padre == TODO ? a : "${a}, para «${padre}»"
    }
}
