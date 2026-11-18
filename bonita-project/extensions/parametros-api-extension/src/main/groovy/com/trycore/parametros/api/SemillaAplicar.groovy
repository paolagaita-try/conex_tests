package com.trycore.parametros.api

import com.trycore.parametros.core.Rechazo
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** POST parametros/semilla/aplicar: la superadministración fuerza la comprobación ahora. */
class SemillaAplicar implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(SemillaAplicar)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.json(rb, 200, Kit.semillas(ctx).aplicar(Kit.autor(ctx), new MotorBonita(ctx.apiClient.processAPI)))
        } catch (Rechazo r) {
            Kit.json(rb, 403, [motivo: r.resultado.motivo])
        } catch (Throwable t) {
            LOG.error("parametros/semilla/aplicar: falló", t)
            Kit.json(rb, 500, [error: "falló la aplicación de la semilla; no quedó nada a medias"])
        }
    }
}
