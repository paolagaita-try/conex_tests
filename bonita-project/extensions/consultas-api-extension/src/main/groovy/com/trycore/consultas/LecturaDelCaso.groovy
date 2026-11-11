package com.trycore.consultas

import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** GET consultas/caso. Toda la decisión vive en `ConsultaCaso`; aquí solo se cablea el motor real y la configuración del zip. */
class LecturaDelCaso implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(LecturaDelCaso)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Configuracion configuracion = Http.configuracion(ctx)
            Http.json(rb, ConsultaCaso.responder(request.parameterMap, ctx.apiSession.userId, new MotorBonita(ctx.apiClient.processAPI),
                    new LectorBonita(ctx.apiClient, configuracion.variableDelCaso), configuracion))
        } catch (Throwable t) {
            LOG.error("consultas/caso: falló la consulta", t)
            Http.json(rb, Respuesta.fallo())
        }
    }
}
