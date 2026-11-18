package com.trycore.parametros.core

/**
 * Resolución por ámbito: actividad → proceso → global, gana el más
 * específico.
 *
 * - Una LISTA se resuelve por definición entera: el ámbito que tiene al menos una opción activa de
 *   esa definición reemplaza la lista heredada completa, también para las opciones de cada padre.
 * - Un PARAMETRO se resuelve por opción del padre: cada valor hereda por separado.
 *
 * Trabaja sobre filas en memoria ({@code proceso, actividad, codigoPadre, codigo, orden, activo, …})
 * de UNA definición; quién las lee es asunto del llamante.
 */
final class Resolucion {

    static final String TODO = "*"

    private Resolucion() {}

    /** Ámbitos candidatos, del más específico al global. */
    static List<List<String>> cadena(String proceso, String actividad) {
        if (proceso == TODO && actividad != TODO) {
            throw new IllegalArgumentException("un ámbito de actividad necesita su proceso: ${actividad}")
        }
        List<List<String>> c = []
        if (actividad != TODO) c << [proceso, actividad]
        if (proceso != TODO) c << [proceso, TODO]
        c << [TODO, TODO]
        c
    }

    /** El ámbito cuya lista entera se usa en (proceso, actividad), o null si ninguno tiene opciones activas. */
    static List<String> ambitoDeLista(List<Map> filas, String proceso, String actividad) {
        cadena(proceso, actividad).find { List<String> a -> filas.any { activaEn(it, a) } }
    }

    /** Opciones activas de la lista resuelta para un padre (o {@code '*'}), en su orden. */
    static List<Map> lista(List<Map> filas, String proceso, String actividad, String codigoPadre) {
        List<String> a = ambitoDeLista(filas, proceso, actividad)
        if (a == null) return []
        filas.findAll { activaEn(it, a) && it.codigoPadre == codigoPadre }.sort { it.orden }
    }

    /** El valor activo más específico de un parámetro para un padre (o {@code '*'}), o null. */
    static Map parametro(List<Map> filas, String proceso, String actividad, String codigoPadre) {
        for (List<String> a : cadena(proceso, actividad)) {
            Map f = filas.find { activaEn(it, a) && it.codigoPadre == codigoPadre }
            if (f != null) return f
        }
        null
    }

    private static boolean activaEn(Map fila, List<String> ambito) {
        fila.activo && fila.proceso == ambito[0] && fila.actividad == ambito[1]
    }
}
