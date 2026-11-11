package com.trycore.parametros.api

import com.trycore.parametros.core.Rechazo
import com.trycore.parametros.core.ServicioDeUsos
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * GET parametros/usos?definicion: «Dónde se usa» de una definición —los lugares que el
 * proceso registró al usarla, con su tipo, y los expedientes por opción, guardados y en curso—. Solo la
 * familia interna, la misma que ve la definición en administración: la persona solicitante recibe 403 sin
 * ningún dato y el intento queda registrado.
 */
class Usos implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Usos)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_USOS")
            if (no != null) {
                return no
            }
            String definicion = request.getParameter("definicion")
            if (!definicion) {
                return Kit.json(rb, 422, [motivo: "VALIDACION", campo: "definicion", detalle: "hace falta la definición"])
            }
            Kit.json(rb, 200, new ServicioDeUsos(Kit.conexiones(), Kit.conteoDeOpciones(ctx)).usos(definicion))
        } catch (Rechazo r) {
            Kit.json(rb, r.resultado.estadoHttp(), [motivo: r.resultado.motivo])
        } catch (Throwable t) {
            LOG.error("parametros/usos: falló", t)
            Kit.json(rb, 500, [error: "falló la consulta"])
        }
    }
}
