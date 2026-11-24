package com.trycore.preventa.contexto

import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** GET preventa/contexto. Toda la decisión vive en `ContextoPreventa`; aquí solo se cablean el cliente real, el token y la configuración. */
class LecturaDelContexto implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(LecturaDelContexto)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Configuracion cfg = Http.configuracion(ctx)
            Http.json(rb, ContextoPreventa.responder(request.parameterMap, System.getenv("HUBSPOT_PRIVATE_APP_TOKEN"), cfg,
                    { String token -> new ClienteHubspotHttp(cfg.urlBase, token, cfg.timeoutMs) }))
        } catch (Throwable t) {
            LOG.error("preventa/contexto: falló la consulta ({})", t.class.simpleName)
            Http.json(rb, Respuesta.fallo())
        }
    }
}
