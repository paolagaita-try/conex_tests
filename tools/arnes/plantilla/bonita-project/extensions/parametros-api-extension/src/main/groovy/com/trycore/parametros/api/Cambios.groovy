package com.trycore.parametros.api

import com.trycore.parametros.core.Resultado
import com.trycore.parametros.core.ServicioDeCambios
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * POST parametros/cambios. El token CSRF lo exige el filtro de la plataforma
 * (POST sin token → 401). Quién puede escribir, la transacción de 7 pasos y el
 * registro de los rechazos los decide parametros-core (ServicioDeCambios).
 */
class Cambios implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Cambios)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            def servicio = new ServicioDeCambios(Kit.conexiones(), Kit.membresias(ctx), Kit.RELOJ, Kit.INTENTOS, Kit.semillas(ctx).invariantes(),
                    Kit.organizacion(ctx), Kit.motor(ctx))
            Resultado r = servicio.cambiar(ctx.apiSession.userName, Peticiones.cambioDe(request.reader.text))
            Map respuesta = Peticiones.respuesta(r)
            rb.withResponseStatus((int) respuesta.estado).withMediaType("application/json").withResponse((String) respuesta.cuerpo).build()
        } catch (Throwable t) {
            LOG.error("parametros/cambios: la escritura falló y no se aplicó nada", t)
            Kit.json(rb, 500, [error: "la escritura falló y no se aplicó nada"])
        }
    }
}
