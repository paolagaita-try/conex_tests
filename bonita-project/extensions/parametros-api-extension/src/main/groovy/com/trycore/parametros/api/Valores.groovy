package com.trycore.parametros.api

import com.trycore.parametros.core.Rechazo
import com.trycore.parametros.core.Resultado
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * GET parametros/valores?definicion&tarea&padre (o &instanciacion=<id de la definición> en un formulario de
 * instanciación): la lista u opción resuelta para la tarea o el proceso, con la familia y el ámbito decididos en el
 * servidor. Un 403 no lleva nada
 * más que el motivo.
 */
class Valores implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Valores)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            Map<String, String> parametros = request.parameterMap.collectEntries { String k, String[] v -> [(k): v ? v[0] : null] }
            Kit.json(rb, 200, Kit.lectura(ctx).valores(Kit.autor(ctx), parametros, new TareasBonita(ctx.apiClient.processAPI, ctx.apiSession.userId)))
        } catch (Rechazo r) {
            Resultado x = r.resultado
            Kit.json(rb, x.estadoHttp(), x.motivo == "VALIDACION" ? [motivo: x.motivo, campo: x.campo, detalle: x.detalle] : [motivo: x.motivo])
        } catch (Throwable t) {
            LOG.error("parametros/valores: falló la lectura", t)
            Kit.json(rb, 500, [error: "falló la lectura"])
        }
    }
}
