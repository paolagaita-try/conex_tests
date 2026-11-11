package com.trycore.parametros.api

import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** GET parametros/avisos: ámbitos huérfanos y semillas que no validan. Solo la familia interna (nombra procesos y actividades). */
class Avisos implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Avisos)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_AVISOS")
            if (no != null) {
                return no
            }
            Kit.json(rb, 200, Kit.semillas(ctx).avisos(new MotorBonita(ctx.apiClient.processAPI)))
        } catch (Throwable t) {
            LOG.error("parametros/avisos: falló", t)
            Kit.json(rb, 500, [error: "falló la consulta"])
        }
    }
}
