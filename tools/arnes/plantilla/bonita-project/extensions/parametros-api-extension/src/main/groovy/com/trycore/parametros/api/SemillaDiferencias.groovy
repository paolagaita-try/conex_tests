package com.trycore.parametros.api

import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** GET parametros/semilla/diferencias: lo que cada semilla trae distinto de lo guardado. Solo la familia interna (nombra procesos y actividades). */
class SemillaDiferencias implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(SemillaDiferencias)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_DIFERENCIAS")
            if (no != null) {
                return no
            }
            Kit.json(rb, 200, Kit.semillas(ctx).diferencias())
        } catch (Throwable t) {
            LOG.error("parametros/semilla/diferencias: falló", t)
            Kit.json(rb, 500, [error: "falló la consulta"])
        }
    }
}
