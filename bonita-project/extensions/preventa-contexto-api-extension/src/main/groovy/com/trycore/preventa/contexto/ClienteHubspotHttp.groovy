package com.trycore.preventa.contexto

import groovy.json.JsonSlurper

/** El cliente real: HttpURLConnection con el token en la cabecera `Authorization` (nunca en la URL ni en los logs). */
class ClienteHubspotHttp implements ClienteHubspot {

    private final String urlBase
    private final String token
    private final int timeoutMs

    ClienteHubspotHttp(String urlBase, String token, int timeoutMs) {
        this.urlBase = urlBase
        this.token = token
        this.timeoutMs = timeoutMs
    }

    @Override
    Map leer(String ruta) {
        HttpURLConnection c
        try {
            c = (HttpURLConnection) new URL(urlBase + ruta).openConnection()
            c.requestMethod = "GET"
            c.connectTimeout = timeoutMs
            c.readTimeout = timeoutMs
            c.setRequestProperty("Authorization", "Bearer " + token)
            c.setRequestProperty("Accept", "application/json")
            int estado = c.responseCode
            if (estado == 404) return null
            if (estado < 200 || estado >= 300) throw new FalloHubspot(estado, "HubSpot respondió " + estado + " en " + sinConsulta(ruta))
            (Map) new JsonSlurper().parse(c.inputStream, "UTF-8")
        } catch (FalloHubspot f) {
            throw f
        } catch (Exception e) {
            throw new FalloHubspot(null, "HubSpot no respondió en " + sinConsulta(ruta) + ": " + e.class.simpleName, e)
        } finally {
            c?.disconnect()
        }
    }

    private static String sinConsulta(String ruta) { ruta.split("[?]")[0] }
}
