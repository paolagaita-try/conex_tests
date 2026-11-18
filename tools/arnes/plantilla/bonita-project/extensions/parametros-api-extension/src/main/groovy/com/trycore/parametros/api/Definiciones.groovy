package com.trycore.parametros.api

import com.trycore.parametros.core.Lectura
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** GET parametros/definiciones?proceso: el catálogo. Solo la familia interna. */
class Definiciones implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Definiciones)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_DEFINICIONES")
            if (no != null) {
                return no
            }
            Kit.json(rb, 200, Kit.conConexion { Lectura.catalogo(it, request.getParameter("proceso")) })
        } catch (Throwable t) {
            LOG.error("parametros/definiciones: falló", t)
            Kit.json(rb, 500, [error: "falló la consulta"])
        }
    }
}
