package com.trycore.preventa.contexto

import groovy.json.JsonOutput
import org.bonitasoft.web.extension.rest.RestAPIContext
import org.bonitasoft.web.extension.rest.RestApiResponse
import org.bonitasoft.web.extension.rest.RestApiResponseBuilder

/** Configuración del zip + entorno, y respuesta JSON. */
class Http {

    static Configuracion configuracion(RestAPIContext ctx) {
        Properties p = new Properties()
        ctx.resourceProvider.getResourceAsStream("configuration.properties")?.withCloseable { p.load(it) } // ISO-8859-1
        Configuracion.de(p, System.getenv())
    }

    static RestApiResponse json(RestApiResponseBuilder rb, Respuesta r) {
        rb.withResponseStatus(r.estado).withMediaType("application/json").withResponse(JsonOutput.toJson(r.cuerpo)).build()
    }
}
