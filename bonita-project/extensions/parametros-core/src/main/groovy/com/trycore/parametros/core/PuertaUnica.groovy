package com.trycore.parametros.core

/**
 * Puerta única: parametros-core solo emite SQL sobre las tablas y columnas del
 * paquete {@code com.trycore.parametros.model}, declaradas en {@link Campos#TABLAS}. Mientras el
 * datasource tenga permisos sobre todo el BDM, esta puerta es lo único que impide escribir en
 * EXPEDIENTE; el custodio check_kit_nombres_sql.py contrasta la declaración con el bom.xml.
 */
final class PuertaUnica {

    static final Set<String> TABLAS = Campos.TABLAS.keySet().asImmutable()

    private static final Map<String, Set<String>> COLUMNAS = Campos.TABLAS.collectEntries { String t, List<String> campos ->
        [(t): (campos + Campos.DEL_MOTOR).collect { it.toUpperCase() }.toSet().asImmutable()]
    }.asImmutable()

    private PuertaUnica() {}

    /** El nombre canónico (mayúsculas) de una tabla del kit; cualquier otra cosa → PuertaCerrada. */
    static String tabla(String nombre) {
        String t = nombre?.toUpperCase()
        if (!(t in TABLAS)) {
            throw new PuertaCerrada("tabla fuera del paquete del kit: «${nombre}»")
        }
        t
    }

    /** Una columna declarada de ESA tabla del paquete (Campos.TABLAS), en mayúsculas; cualquier otra → PuertaCerrada. */
    static String columna(String tabla, String nombre) {
        if (!(nombre ==~ /[A-Za-z][A-Za-z0-9]*/)) {
            throw new PuertaCerrada("columna que no es un identificador simple: «${nombre}»")
        }
        String c = nombre.toUpperCase()
        if (!(c in COLUMNAS[PuertaUnica.tabla(tabla)])) {
            throw new PuertaCerrada("«${nombre}» no es una columna de ${tabla} en el paquete del kit")
        }
        c
    }
}
