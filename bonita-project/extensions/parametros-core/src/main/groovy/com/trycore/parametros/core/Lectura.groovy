package com.trycore.parametros.core

import java.sql.Connection

/**
 * La lectura resuelta que consumen los formularios:
 * el ámbito más específico, solo lo activo y en su orden, y la cascada contra la lista madre YA
 * resuelta en el mismo ámbito. No decide familia ni permisos, no aplica fallback ni registra usos:
 * eso es del llamante (la API) y de usar(). La respuesta no lleva nombres de proceso ni de
 * actividad, ni identificadores.
 */
final class Lectura {

    static final String TODO = "*"

    private Lectura() {}

    /** La definición con sus metadatos (nombres del BDM), o null si no existe. */
    static Map<String, Object> definicion(Connection c, String codigo) {
        List<Map<String, Object>> d = new Filas(c, Dialecto.de(c)).leer("KPDEFINICIONPARAMETRO", [CODIGO: codigo])
        d ? Campos.json(Campos.DEFINICION, d[0]) : null
    }

    /**
     * Lista u opción resuelta de {@code codigo} en (proceso, actividad) para {@code padre} ({@code '*'} si
     * la definición no depende de otra), o null si la definición no existe.
     */
    static Map<String, Object> valores(Connection c, String codigo, String proceso, String actividad, String padre) {
        Map<String, Object> d = definicion(c, codigo)
        if (d == null) {
            return null
        }
        boolean depende = d.dependeDe != TODO
        if (depende && padre == TODO) {
            rechaza("padre", "«${codigo}» depende de «${d.dependeDe}»: hace falta el código del padre")
        }
        if (!depende && padre != TODO) {
            rechaza("padre", "«${codigo}» no depende de ninguna lista")
        }
        boolean padreVivo = !depende || padre in codigosActivos(c, (String) d.dependeDe, proceso, actividad)
        List<Map<String, Object>> filas = filas(c, codigo)
        if (d.clase == "LISTA") {
            List<Map> opciones = padreVivo ? Resolucion.lista(filas, proceso, actividad, padre) : []
            return [definicion: codigo, clase: "LISTA", tipoDato: d.tipoDato,
                    opciones  : opciones.collect { [codigo: it.codigo, etiqueta: it.etiqueta, ayuda: it.ayuda, orden: it.orden, valor: it.valor] }]
        }
        Map fila = padreVivo ? Resolucion.parametro(filas, proceso, actividad, padre) : null
        [definicion: codigo, clase: "PARAMETRO", tipoDato: d.tipoDato, unidad: d.unidad, valor: fila?.valor]
    }

    /**
     * GET parametros/definiciones?proceso (familia interna): todas las definiciones con sus
     * metadatos y su versión, por código; con {@code proceso}, solo las que tienen filas en ese proceso
     * o en el global.
     */
    static List<Map<String, Object>> catalogo(Connection c, String proceso) {
        Filas f = new Filas(c, Dialecto.de(c))
        List<Map<String, Object>> defs = f.leer("KPDEFINICIONPARAMETRO", [:], "CODIGO").collect { Campos.json(Campos.DEFINICION, it) }
        if (proceso == null) {
            return defs
        }
        Set<String> conFilas = f.leer("KPVALORPARAMETRO", [:]).findAll { it.PROCESO in [proceso, TODO] }*.DEFINICION as Set
        defs.findAll { it.codigo in conFilas }
    }

    /** Códigos activos de la lista {@code codigo} en el ámbito del que (proceso, actividad) la toma entera. */
    static Set<String> codigosActivos(Connection c, String codigo, String proceso, String actividad) {
        List<Map<String, Object>> filas = filas(c, codigo)
        List<String> ambito = Resolucion.ambitoDeLista(filas, proceso, actividad)
        ambito == null ? [] as Set : filas.findAll { it.activo && it.proceso == ambito[0] && it.actividad == ambito[1] }*.codigo as Set
    }

    private static List<Map<String, Object>> filas(Connection c, String codigo) {
        new Filas(c, Dialecto.de(c)).leer("KPVALORPARAMETRO", [DEFINICION: codigo]).collect { Campos.json(Campos.VALOR, it) }
    }

    private static void rechaza(String campo, String detalle) {
        throw new Rechazo(new Resultado(aplicado: false, motivo: "VALIDACION", campo: campo, detalle: detalle))
    }
}
