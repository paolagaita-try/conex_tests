package com.trycore.consultas

/**
 * Validación de la petición. Solo pasan los parámetros DECLARADOS, cada uno con un único valor, y el identificador de
 * caso como entero positivo que cabe en un `long`. Cualquier otro parámetro —una «familia» en la URL, por
 * ejemplo— invalida la petición entera: no se ignora, porque ignorarlo dejaría creer a quien llama que lo pidió con
 * éxito.
 */
class Peticion {

    /** Los parámetros que son un identificador de caso. */
    private static final Set<String> CASOS = ["caso", "caseId"] as Set

    /** Los parámetros si la petición es válida; `null` si no (quien llama responde 403 sin datos). */
    static Map<String, String> validar(Map<String, String[]> recibidos, Set<String> declarados) {
        if (recibidos == null || recibidos.keySet() != declarados) return null
        Map<String, String> salida = [:]
        for (String nombre : declarados) {
            String[] valores = recibidos[nombre]
            if (valores == null || valores.length != 1 || !valores[0]) return null
            if (nombre in CASOS && !esCaso(valores[0])) return null
            salida[nombre] = valores[0]
        }
        salida
    }

    private static boolean esCaso(String v) {
        v ==~ /[0-9]{1,18}/ && (v as long) > 0
    }
}
