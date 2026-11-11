package com.trycore.parametros.api

import com.trycore.parametros.core.ConsultaDeTraza
import com.trycore.parametros.core.Rechazo
import groovy.json.JsonOutput
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * GET parametros/traza?claveNegocio&usuario&desde&hasta&p&c: solo la familia
 * interna, decidida en el servidor. Cualquier otra → 403 sin ningún nombre ni valor. La
 * respuesta es la lista de la página con Content-Range «p-c/total», como la API REST de Bonita.
 */
class Traza implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Traza)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_TRAZA")
            if (no != null) {
                return no
            }
            Map filtros = ConsultaDeTraza.FILTROS.collectEntries { [(it): request.getParameter(it)] }.findAll { it.value != null }
            int p = entero(request.getParameter("p"), 0)
            int c = entero(request.getParameter("c"), 20)
            Map r = Kit.conConexion { ConsultaDeTraza.consultar(it, filtros, p, c) }
            rb.withResponseStatus(200).withMediaType("application/json").withContentRange(p, c, (long) r.total)
                    .withResponse(JsonOutput.toJson(r.elementos)).build()
        } catch (Rechazo r) {
            Kit.json(rb, 422, [motivo: r.resultado.motivo, campo: r.resultado.campo, detalle: r.resultado.detalle])
        } catch (Throwable t) {
            LOG.error("parametros/traza: falló la consulta", t)
            Kit.json(rb, 500, [error: "falló la consulta de la traza"])
        }
    }

    /** Un entero de la URL; lo que no lo es se vuelve -1 para que la consulta lo rechace con su campo. */
    static int entero(String valor, int porDefecto) {
        valor == null ? porDefecto : (valor ==~ /[0-9]{1,6}/ ? valor as int : -1)
    }
}
