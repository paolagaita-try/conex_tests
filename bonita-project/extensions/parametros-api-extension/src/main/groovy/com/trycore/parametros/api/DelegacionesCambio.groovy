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
 * POST parametros/delegaciones: DELEGAR —siempre propuesta, 202— o REVOCAR
 * —directo—, solo la superadministración. Lo decide parametros-core por el mismo camino que un cambio.
 */
class DelegacionesCambio implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(DelegacionesCambio)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            Resultado r = new ServicioDeCambios(Kit.conexiones(), Kit.membresias(ctx), Kit.RELOJ, Kit.INTENTOS, Kit.semillas(ctx).invariantes(),
                    Kit.organizacion(ctx), Kit.motor(ctx)).cambiar(ctx.apiSession.userName, Peticiones.delegacionDe(request.reader.text))
            Map respuesta = Peticiones.respuesta(r)
            rb.withResponseStatus((int) respuesta.estado).withMediaType("application/json").withResponse((String) respuesta.cuerpo).build()
        } catch (Throwable t) {
            LOG.error("parametros/delegaciones: falló y no se aplicó nada", t)
            Kit.json(rb, 500, [error: "la delegación falló y no se aplicó nada"])
        }
    }
}
