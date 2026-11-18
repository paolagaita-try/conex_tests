package com.trycore.parametros.api

import com.trycore.parametros.core.Resultado
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * POST parametros/semilla/restablecer. Solo existe con
 * `entorno=demo` en la configuración del proyecto: si no, 404 para todo el mundo. En demo, solo la
 * superadministración, sin doble control.
 */
class SemillaRestablecer implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(SemillaRestablecer)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Resultado r = Kit.semillas(ctx).restablecer(Kit.autor(ctx), Peticiones.motivoDe(request.reader.text),
                    Kit.configuracion(ctx).getProperty("entorno"))
            Map respuesta = Peticiones.respuesta(r)
            rb.withResponseStatus((int) respuesta.estado).withMediaType("application/json").withResponse((String) respuesta.cuerpo).build()
        } catch (Throwable t) {
            LOG.error("parametros/semilla/restablecer: falló y no se aplicó nada", t)
            Kit.json(rb, 500, [error: "el restablecimiento falló y no se aplicó nada"])
        }
    }
}
