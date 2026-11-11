package com.trycore.parametros.core

import java.sql.Connection

/**
 * GET parametros/avisos: ámbitos huérfanos, es decir, filas de
 * KpValorParametro cuyo proceso no está desplegado o cuya actividad no es un flow node con nombre de
 * ese proceso, agrupadas por definición y ámbito con su recuento. Se calcula en vivo contra lo que el
 * motor tiene: un despliegue que renombre una tarea aparece aquí en la siguiente consulta.
 */
final class Avisos {

    static final String TODO = "*"

    private Avisos() {}

    static List<Map> huerfanos(Connection c, Motor motor) {
        Map<String, Set<String>> desplegado = motor.nodosPorProceso()
        List<Map<String, Object>> filas = new Filas(c, Dialecto.de(c)).leer("KPVALORPARAMETRO", [:]).findAll { it.PROCESO != TODO }
        filas.groupBy { [it.DEFINICION, it.PROCESO, it.ACTIVIDAD] }.collect { List k, List grupo ->
            String proceso = (String) k[1]
            String actividad = (String) k[2]
            String motivo = !desplegado.containsKey(proceso) ? "PROCESO_NO_DESPLEGADO"
                    : actividad != TODO && !(actividad in desplegado[proceso]) ? "ACTIVIDAD_INEXISTENTE" : null
            motivo == null ? null : [definicion: k[0], proceso: proceso, actividad: actividad, filas: grupo.size(), motivo: motivo]
        }.findAll { it != null }
    }

    /**
     * Cada versión propia —un ámbito con alguna opción activa copiada de otro— con
     * las opciones que su origen tiene activas hoy y no tenía al copiarla. Los códigos van con el mismo
     * formato que escribe CREAR_VERSION_PROPIA en codigosOrigen («padre|codigo», o «codigo» sin padre).
     */
    static List<Map> desfasadas(Connection c) {
        List<Map<String, Object>> todas = valores(c)
        todas.findAll { it.copiadoDe != TODO }.groupBy { [it.definicion, it.proceso, it.actividad] }.collect { List k, List<Map> grupo ->
            if (!grupo.any { it.activo }) {
                return null // volvió a heredar: ya no es una versión propia
            }
            String copiadoDe = (String) grupo[0].copiadoDe
            List<String> origen = copiadoDe.split("\\|", 2) as List
            Set<String> alCopiar = new groovy.json.JsonSlurper().parseText((String) grupo[0].codigosOrigen ?: "[]") as Set
            List<String> hoy = todas.findAll { it.definicion == k[0] && it.activo && it.proceso == origen[0] && it.actividad == origen[1] }
                    .collect { it.codigoPadre == TODO ? it.codigo : it.codigoPadre + "|" + it.codigo }
            List<String> nuevas = (hoy - alCopiar).unique().sort()
            nuevas ? [definicion: k[0], proceso: k[1], actividad: k[2], copiadoDe: copiadoDe, nuevas: nuevas] : null
        }.findAll { it != null }
    }

    /**
     * En cada ámbito donde la madre o la hija de una cascada tienen filas, los
     * códigos padre de la hija resuelta que no están activos en la madre resuelta en ese mismo ámbito.
     * La hija LISTA se toma entera del ámbito del que la hereda; la hija PARAMETRO, de toda la
     * cadena de ámbitos, porque hereda por padre.
     */
    static List<Map> huerfanosDeCascada(Connection c) {
        List<Map<String, Object>> todas = valores(c)
        new Filas(c, Dialecto.de(c)).leer("KPDEFINICIONPARAMETRO", [:]).findAll { it.DEPENDEDE != TODO && it.ACTIVO }.collectMany { Map hija ->
            String madre = (String) hija.DEPENDEDE
            List<Map> filasHija = todas.findAll { it.definicion == hija.CODIGO }
            List<Map> filasMadre = todas.findAll { it.definicion == madre }
            (filasHija + filasMadre).collect { [it.proceso, it.actividad] }.unique().sort { it.join("|") }.collect { List<String> amb ->
                Set<String> ofrecidos = activosDelAmbitoDeLista(filasMadre, amb[0], amb[1])
                Set<String> padres = padresDeLaHija(hija, filasHija, amb[0], amb[1])
                List<String> huerfanos = (padres - ofrecidos).sort()
                huerfanos ? [definicion: hija.CODIGO, proceso: amb[0], actividad: amb[1], padres: huerfanos] : null
            }.findAll { it != null }
        }
    }

    private static Set<String> activosDelAmbitoDeLista(List<Map> filas, String proceso, String actividad) {
        List<String> a = Resolucion.ambitoDeLista(filas, proceso, actividad)
        a == null ? [] as Set : filas.findAll { it.activo && it.proceso == a[0] && it.actividad == a[1] }*.codigo as Set
    }

    private static Set<String> padresDeLaHija(Map hija, List<Map> filas, String proceso, String actividad) {
        if (hija.CLASE == "LISTA") {
            List<String> a = Resolucion.ambitoDeLista(filas, proceso, actividad)
            return a == null ? [] as Set : filas.findAll { it.activo && it.proceso == a[0] && it.actividad == a[1] }*.codigoPadre as Set
        }
        List<List<String>> cadena = Resolucion.cadena(proceso, actividad)
        filas.findAll { f -> f.activo && cadena.any { it[0] == f.proceso && it[1] == f.actividad } }*.codigoPadre as Set
    }

    private static List<Map<String, Object>> valores(Connection c) {
        new Filas(c, Dialecto.de(c)).leer("KPVALORPARAMETRO", [:]).collect { Campos.json(Campos.VALOR, it) }
    }
}
