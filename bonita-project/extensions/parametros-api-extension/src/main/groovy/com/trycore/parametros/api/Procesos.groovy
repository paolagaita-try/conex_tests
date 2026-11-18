package com.trycore.parametros.api

import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * GET parametros/procesos: los procesos y sus actividades, descubiertos
 * del motor —todo flow node con nombre, de cualquier versión—. Solo la familia interna: nombra
 * actividades internas (F6d…).
 */
class Procesos implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Procesos)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_PROCESOS")
            if (no != null) {
                return no
            }
            Map<String, Set<String>> nodos = new MotorBonita(ctx.apiClient.processAPI).nodosPorProceso()
            Kit.json(rb, 200, nodos.keySet().sort().collect { [proceso: it, actividades: nodos[it].sort()] })
        } catch (Throwable t) {
            LOG.error("parametros/procesos: falló", t)
            Kit.json(rb, 500, [error: "falló la consulta"])
        }
    }
}
