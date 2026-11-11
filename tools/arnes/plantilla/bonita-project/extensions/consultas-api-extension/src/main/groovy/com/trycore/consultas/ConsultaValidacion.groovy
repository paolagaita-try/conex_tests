package com.trycore.consultas

import org.slf4j.Logger
import org.slf4j.LoggerFactory

import groovy.json.JsonSlurper

import java.time.OffsetDateTime

/**
 * GET consultas/validacion?caso= — por qué la tarea volvió: el veredicto de la última validación del caso, que deja
 * el paso de validación del proceso como una fila `validacion-catalogo` en `ejecucionesServicio` del objeto raíz.
 *
 * Lo que sale es una LISTA CERRADA: campo del contrato + un motivo de un vocabulario neutro. El texto lo pone la
 * pantalla (`$lib/parametros/rechazo.ts`). Todo lo que la fila traiga fuera de ese vocabulario se descarta.
 *
 *   200  {"rechazos": [{"campo": "...", "motivo": "..."}]}   vacía = nada que avisar
 *   403 / 500  {"motivo": "..."}                            igual que consultas/caso (un caso inexistente es 403)
 *
 * La familia cliente solo ve el veredicto de las actividades del canal de cliente (`familia.cliente.tareas`): el de
 * una interna no existe para ella (200 con lista vacía, indistinguible de «sin rechazo»).
 */
class ConsultaValidacion {

    private static final Logger LOG = LoggerFactory.getLogger(ConsultaValidacion)

    static final Set<String> PARAMETROS = ["caso"] as Set
    static final String SERVICIO = "validacion-catalogo"
    static final String RECHAZADO = "RECHAZADO"
    static final Set<String> MOTIVOS = ["no-vigente", "sobre-tope", "sin-comprobar", "sin-elegir"] as Set
    static final int MAX_RECHAZOS = 20

    static Respuesta responder(Map<String, String[]> parametros, long usuario, Motor motor,
                               LectorDeCaso lector, Configuracion configuracion) {
        Guarda.Resultado g = Guarda.autorizar(parametros, PARAMETROS, usuario, motor, configuracion)
        if (g.denegada != null) return g.denegada
        long caso = g.caso
        boolean interna = g.interna
        List<Map<String, Object>> filas
        try {
            filas = lector.ejecucionesServicio(caso)
        } catch (Exception e) {
            LOG.error("consultas/validacion: falló la lectura del caso {}", caso, e)
            return Respuesta.fallo()
        }
        new Respuesta(200, [rechazos: rechazosDe(filas, interna ? null : configuracion.tareasCliente)])
    }

    /** Los rechazos de la ÚLTIMA validación (por fecha de inicio), o vacío si no rechazó. */
    static List<Map<String, String>> rechazosDe(List<Map<String, Object>> filas, List<String> actividadesPermitidas = null) {
        def ultima = (filas ?: []).findAll {
            it.servicio == SERVICIO && (actividadesPermitidas == null || actividadesPermitidas.contains(it.actividadCodigo))
        }.max { fecha(it.fechaInicio) }
        if (ultima == null || ultima.codigoRespuesta != RECHAZADO) return []
        Object crudo
        try {
            crudo = new JsonSlurper().parseText((ultima.valoresDevueltos ?: "{}").toString())
        } catch (Exception ignorada) {
            // Un rechazo cuyo detalle no se lee sigue siendo un rechazo: se dice sin campo, no se calla.
            return [[campo: "", motivo: "sin-comprobar"]]
        }
        List filasCrudas = crudo instanceof Map && crudo.rechazos instanceof List ? crudo.rechazos : []
        List<Map<String, String>> salida = []
        filasCrudas.each { f ->
            if (salida.size() >= MAX_RECHAZOS || !(f instanceof Map)) return
            String campo = String.valueOf(f.campo ?: "")
            String motivo = String.valueOf(f.motivo ?: "")
            salida << [campo : (campo ==~ /[A-Za-z0-9]{1,64}/) ? campo : "",
                       motivo: MOTIVOS.contains(motivo) ? motivo : "sin-comprobar"]
        }
        salida.isEmpty() ? [[campo: "", motivo: "sin-comprobar"]] : salida
    }

    private static long fecha(Object f) {
        if (f instanceof Number) return f.longValue()
        if (f instanceof Date) return f.time
        try {
            return OffsetDateTime.parse(f.toString()).toInstant().toEpochMilli()
        } catch (Exception ignorada) {
            return Long.MIN_VALUE
        }
    }
}
