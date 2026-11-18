package com.trycore.consultas

import org.slf4j.Logger
import org.slf4j.LoggerFactory

/**
 * GET consultas/caso?caseId= — el objeto raíz del caso (la variable de negocio del proceso) con sus atributos por
 * nombre, para que un formulario lo lea UNA vez al abrirse. Es el único camino por el que las pantallas leen el
 * caso: nunca `/API/bdm` ni `/API/bpm/processParameter`.
 *
 * Orden: validar la petición → implicación en el caso y familia ({@link Guarda}) → leer. Se autoriza ANTES de mirar si
 * el caso existe: quien no está autorizado recibe 403 siempre, exista el caso o no.
 *
 *   200  {atributo: valor, ...}   los atributos escalares del objeto raíz
 *   403  {"motivo": "..."}        petición inválida, usuario fuera de las familias o no implicado en el caso, o caso inexistente
 *   404  {"motivo": "sin-objeto"}  SOLO para un usuario autorizado: el caso no tiene objeto raíz
 *   500  {"motivo": "..."}        la lectura falló (sin datos)
 *
 * Pueden leerlo las dos familias, cada una EN SUS casos: las dos exigen estar implicadas en el caso (lo inició, o tiene
 * o tuvo una tarea humana suya); además, la cliente estar mapeada a un actor cliente y la interna a un actor interno
 * del proceso del caso.
 */
class ConsultaCaso {

    private static final Logger LOG = LoggerFactory.getLogger(ConsultaCaso)

    static final Set<String> PARAMETROS = ["caseId"] as Set

    static Respuesta responder(Map<String, String[]> parametros, long usuario, Motor motor,
                               LectorDeCaso lector, Configuracion configuracion) {
        Guarda.Resultado g = Guarda.autorizar(parametros, PARAMETROS, usuario, motor, configuracion)
        if (g.denegada != null) return g.denegada
        long caso = g.caso
        Map<String, Object> objeto
        try {
            objeto = lector.objetoRaiz(caso)
        } catch (Exception e) {
            LOG.error("consultas/caso: falló la lectura del caso {}", caso, e)
            return Respuesta.fallo()
        }
        objeto == null ? Respuesta.noEncontrado("sin-objeto") : new Respuesta(200, objeto)
    }
}
