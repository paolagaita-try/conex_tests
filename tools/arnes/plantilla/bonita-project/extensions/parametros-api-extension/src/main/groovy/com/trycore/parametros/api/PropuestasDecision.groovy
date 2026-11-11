package com.trycore.parametros.api

import com.trycore.parametros.core.Resultado
import com.trycore.parametros.core.ServicioDePropuestas
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * POST parametros/propuestas/decision: aprobar, rechazar o retirar una propuesta.
 * Quién puede, la transacción y el registro de los rechazos —también el del proponente que intenta
 * aprobar (B4)— los decide parametros-core (ServicioDePropuestas).
 */
class PropuestasDecision implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(PropuestasDecision)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            Resultado r = new ServicioDePropuestas(Kit.conexiones(), Kit.membresias(ctx), Kit.RELOJ, Kit.INTENTOS, Kit.semillas(ctx).invariantes(),
                    Kit.organizacion(ctx), Kit.motor(ctx))
                    .decidir(ctx.apiSession.userName, Peticiones.decisionDe(request.reader.text))
            Map respuesta = Peticiones.respuesta(r)
            rb.withResponseStatus((int) respuesta.estado).withMediaType("application/json").withResponse((String) respuesta.cuerpo).build()
        } catch (Throwable t) {
            LOG.error("parametros/propuestas/decision: falló y no se aplicó nada", t)
            Kit.json(rb, 500, [error: "la decisión falló y no se aplicó nada"])
        }
    }
}
