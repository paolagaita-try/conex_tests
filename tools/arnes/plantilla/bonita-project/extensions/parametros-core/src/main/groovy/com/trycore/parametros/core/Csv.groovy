package com.trycore.parametros.core

/**
 * El CSV de una importación, leído entero antes de clasificar nada. Cabecera
 * obligatoria con columnas conocidas —en cualquier orden y sin distinguir mayúsculas—, separador `,`
 * o `;` (el que use la cabecera), comillas RFC 4180, UTF-8 con o sin BOM, como mucho {@link #MAXIMO}
 * filas. Un fichero que no se puede leer se rechaza entero (VALIDACION, campo `csv`): lo que tiene
 * mal una fila concreta lo dice después la clasificación, fila a fila.
 *
 * Cada fila sale con su número en el fichero (la cabecera es la 1), el que ve quien lo abre en una
 * hoja de cálculo, y sus celdas por nombre de columna; las que faltan al final, vacías.
 */
final class Csv {

    static final int MAXIMO = 500

    /** La marca de orden de bytes con la que algunas hojas de cálculo empiezan un UTF-8. */
    private static final char BOM = (char) 0xFEFF

    static final List<String> COLUMNAS = ["definicion", "proceso", "actividad", "codigoPadre", "codigo", "etiqueta", "ayuda", "orden",
                                          "valor", "activo"].asImmutable()

    private Csv() {}

    static List<Map<String, Object>> leer(String texto) {
        String t = texto == null ? "" : (!texto.isEmpty() && texto.charAt(0) == BOM ? texto.substring(1) : texto)
        if (!t.trim()) {
            falla("el fichero está vacío")
        }
        char separador = separadorDe(t)
        List<List<String>> registros = registros(t, separador)
        List<String> cabecera = registros[0].collect { String c ->
            String nombre = COLUMNAS.find { it.equalsIgnoreCase(c.trim()) }
            if (nombre == null) {
                falla("columna desconocida «${c.trim()}» (se admiten ${COLUMNAS.join(', ')})")
            }
            nombre
        }
        String repetida = cabecera.find { String c -> cabecera.count(c) > 1 }
        if (repetida != null) {
            falla("la columna «${repetida}» está repetida")
        }
        if (!("definicion" in cabecera)) {
            falla("falta la columna «definicion»")
        }
        List<Map<String, Object>> filas = []
        registros.drop(1).eachWithIndex { List<String> celdas, int i ->
            int fila = i + 2
            if (celdas.every { !it.trim() }) {
                return
            }
            if (celdas.size() > cabecera.size()) {
                falla("la fila ${fila} tiene más celdas que la cabecera")
            }
            filas << [fila: fila, celdas: cabecera.withIndex().collectEntries { String c, int j -> [(c): j < celdas.size() ? celdas[j].trim() : ""] }]
        }
        if (filas.isEmpty()) {
            falla("el fichero no tiene ninguna fila después de la cabecera")
        }
        if (filas.size() > MAXIMO) {
            falla("como mucho ${MAXIMO} filas por importación (trae ${filas.size()})")
        }
        filas
    }

    /** El de la cabecera: el que más aparece fuera de comillas en la primera línea; sin ninguno, la coma. */
    private static char separadorDe(String t) {
        int puntoYComa = 0, coma = 0
        boolean entreComillas = false
        for (char ch : t.toCharArray()) {
            if (ch == '"' as char) entreComillas = !entreComillas
            else if (!entreComillas && (ch == '\n' as char || ch == '\r' as char)) break
            else if (!entreComillas && ch == ';' as char) puntoYComa++
            else if (!entreComillas && ch == ',' as char) coma++
        }
        puntoYComa > coma ? ';' as char : ',' as char
    }

    /** RFC 4180: comillas que encierran el separador y los saltos, comillas dobladas dentro, CRLF o LF. */
    private static List<List<String>> registros(String t, char separador) {
        List<List<String>> todos = []
        List<String> actual = []
        StringBuilder celda = new StringBuilder()
        boolean entreComillas = false
        int i = 0
        while (i < t.length()) {
            char ch = t.charAt(i)
            if (entreComillas) {
                if (ch == '"' as char && i + 1 < t.length() && t.charAt(i + 1) == '"' as char) {
                    celda.append('"')
                    i++
                } else if (ch == '"' as char) {
                    entreComillas = false
                } else {
                    celda.append(ch)
                }
            } else if (ch == '"' as char) {
                entreComillas = true
            } else if (ch == separador) {
                actual << celda.toString()
                celda.setLength(0)
            } else if (ch == '\r' as char && i + 1 < t.length() && t.charAt(i + 1) == '\n' as char) {
                // el \n del CRLF cierra el registro en la vuelta siguiente
            } else if (ch == '\n' as char || ch == '\r' as char) {
                actual << celda.toString()
                celda.setLength(0)
                todos << actual
                actual = []
            } else {
                celda.append(ch)
            }
            i++
        }
        if (entreComillas) {
            falla("comillas sin cerrar")
        }
        if (celda.length() > 0 || !actual.isEmpty()) {
            actual << celda.toString()
            todos << actual
        }
        todos
    }

    private static void falla(String detalle) {
        Validacion.falla("csv", detalle)
    }
}
