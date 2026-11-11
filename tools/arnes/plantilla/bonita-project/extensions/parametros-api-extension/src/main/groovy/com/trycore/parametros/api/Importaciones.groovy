package com.trycore.parametros.api

import com.trycore.parametros.core.Resultado
import com.trycore.parametros.core.ServicioDeImportaciones
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiController
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

import javax.servlet.http.HttpServletRequest

/**
 * POST parametros/importaciones: `{csv, motivo, confirmar, huella}`. Sin
 * confirmar, la vista previa (200, nada escrito); confirmando con motivo y la huella de esa vista, el
 * lote (200), o 409 con la vista nueva si lo guardado cambió.
 */
class Importaciones implements RestApiController {

    private static final Logger LOG = LoggerFactory.getLogger(Importaciones)

    @Override
    RestApiResponse doHandle(HttpServletRequest request, RestApiResponseBuilder rb, RestAPIContext ctx) {
        try {
            Kit.asegurarSemillas(ctx)
            Map pedido = Peticiones.importacionDe(request.reader.text)
            Resultado r = new ServicioDeImportaciones(Kit.conexiones(), Kit.membresias(ctx), Kit.RELOJ, Kit.INTENTOS, Kit.semillas(ctx).invariantes(),
                    Kit.organizacion(ctx), Kit.motor(ctx))
                    .importar(ctx.apiSession.userName, (String) pedido.csv, (String) pedido.motivo, (boolean) pedido.confirmar, (String) pedido.huella)
            Map respuesta = Peticiones.respuesta(r)
            rb.withResponseStatus((int) respuesta.estado).withMediaType("application/json").withResponse((String) respuesta.cuerpo).build()
        } catch (Throwable t) {
            LOG.error("parametros/importaciones: falló y no se aplicó nada", t)
            Kit.json(rb, 500, [error: "la importación falló y no se aplicó nada"])
        }
    }
}
