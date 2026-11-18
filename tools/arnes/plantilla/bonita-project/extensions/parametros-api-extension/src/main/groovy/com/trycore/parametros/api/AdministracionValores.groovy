package com.trycore.parametros.api

import com.trycore.parametros.core.Rechazo
import com.trycore.parametros.core.ServicioDeAdministracion
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/** GET parametros/administracion/valores?definicion: la familia interna lee TODAS las filas con su versión, sin persistenceId. */
class AdministracionValores implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(AdministracionValores)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            RestApiResponse no = Kit.siNoEsInterna(ctx, rb, "LEER_ADMINISTRACION")
            if (no != null) {
                return no
            }
            ServicioDeAdministracion s = new ServicioDeAdministracion(Kit.conexiones(), Kit.membresias(ctx), Kit.organizacion(ctx), Kit.RELOJ, Kit.INTENTOS)
            Kit.json(rb, 200, s.valores(request.getParameter("definicion")))
        } catch (Rechazo r) {
            Kit.json(rb, r.resultado.estadoHttp(), r.resultado.motivo == "VALIDACION"
                    ? [motivo: r.resultado.motivo, campo: r.resultado.campo, detalle: r.resultado.detalle] : [motivo: r.resultado.motivo])
        } catch (Throwable t) {
            LOG.error("AdministracionValores: falló", t)
            Kit.json(rb, 500, [error: "falló la consulta"])
        }
    }
}
