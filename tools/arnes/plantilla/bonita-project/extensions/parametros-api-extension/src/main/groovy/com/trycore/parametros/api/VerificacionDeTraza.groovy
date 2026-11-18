package com.trycore.parametros.api

import com.trycore.parametros.core.Cambio
import com.trycore.parametros.core.Autorizacion
import com.trycore.parametros.core.Verificacion
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * GET parametros/traza/verificacion[?completa=true]: solo la
 * superadministración. Incremental desde el último punto verificado; completa desde el génesis.
 */
class VerificacionDeTraza implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(VerificacionDeTraza)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            if (!Autorizacion.esSuperadministracion(Kit.autor(ctx))) {
                Kit.conConexion { c -> Kit.INTENTOS.registrar(c, Kit.autor(ctx), new Cambio(accion: "VERIFICAR_TRAZA", definicion: "*"), "SIN_PERMISO", "solo la superadministración") }
                return Kit.json(rb, 403, [motivo: "SIN_PERMISO"])
            }
            boolean completa = request.getParameter("completa") == "true"
            Map v = Kit.conConexion { new Verificacion(Kit.RELOJ).verificar(it, completa) }
            Kit.json(rb, 200, v)
        } catch (Throwable t) {
            LOG.error("parametros/traza/verificacion: falló la verificación", t)
            Kit.json(rb, 500, [error: "falló la verificación"])
        }
    }
}
