package com.trycore.parametros.api

import com.trycore.parametros.core.Rechazo
import com.trycore.parametros.core.ServicioDePropuestas
import groovy.json.JsonOutput
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * GET parametros/propuestas?estado&p&c: solo la familia interna. Cada
 * propuesta dice si quien llama puede aprobarla y si es suya; `paraAprobar` es el contador de la
 * pestaña Aprobaciones (sin correo). Content-Range «p-c/total», como la traza.
 */
class PropuestasLista implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(PropuestasLista)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_PROPUESTAS")
            if (no != null) {
                return no
            }
            int p = Traza.entero(request.getParameter("p"), 0)
            int c = Traza.entero(request.getParameter("c"), 20)
            Map r = new ServicioDePropuestas(Kit.conexiones(), Kit.membresias(ctx), Kit.RELOJ, Kit.INTENTOS, Kit.semillas(ctx).invariantes(),
                    Kit.organizacion(ctx), Kit.motor(ctx))
                    .listar(ctx.apiSession.userName, request.getParameter("estado"), p, c)
            rb.withResponseStatus(200).withMediaType("application/json").withContentRange(p, c, (long) r.total)
                    .withResponse(JsonOutput.toJson(r)).build()
        } catch (Rechazo r) {
            Kit.json(rb, 422, [motivo: r.resultado.motivo, campo: r.resultado.campo, detalle: r.resultado.detalle])
        } catch (Throwable t) {
            LOG.error("parametros/propuestas: falló la consulta", t)
            Kit.json(rb, 500, [error: "falló la consulta de las propuestas"])
        }
    }
}
