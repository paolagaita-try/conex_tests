package com.trycore.preventa.contexto

import com.sun.net.httpserver.HttpServer
import spock.lang.Specification

/** El cliente real contra un servidor HTTP local en loopback (sin red externa): cabecera, 404 → null, no 2xx → FalloHubspot. */
class ClienteHubspotHttpSpec extends Specification {

    HttpServer servidor = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0)
    List<String> autorizaciones = []
    List<String> rutas = []

    boolean detenido

    def cleanup() { if (!detenido) servidor.stop(0) }

    def setup() {
        servidor.createContext("/") { ex ->
            autorizaciones << ex.requestHeaders.getFirst("Authorization")
            rutas << ex.requestURI.toString()
            String p = ex.requestURI.path
            int codigo = p.endsWith("/404") ? 404 : (p.endsWith("/500") ? 500 : 200)
            byte[] cuerpo = (codigo == 200 ? '{"id":"7","properties":{"subject":"á"}}' : '{"message":"detalle interno largo"}').getBytes("UTF-8")
            ex.sendResponseHeaders(codigo, cuerpo.length)
            ex.responseBody.withCloseable { it.write(cuerpo) }
        }
        servidor.start()
    }

    ClienteHubspot cliente() { new ClienteHubspotHttp("http://127.0.0.1:${servidor.address.port}/hubspot", "tok-1", 2000) }

    def "lee JSON con el token en la cabecera y respeta el prefijo de la raíz (mock /hubspot)"() {
        expect:
        cliente().leer("/crm/v3/objects/tickets/7?properties=subject") == [id: "7", properties: [subject: "á"]]
        autorizaciones == ["Bearer tok-1"]
        rutas == ["/hubspot/crm/v3/objects/tickets/7?properties=subject"]
    }

    def "404 → null"() {
        expect:
        cliente().leer("/crm/v3/objects/tickets/404") == null
    }

    def "500 → FalloHubspot con el código y sin el cuerpo ni el token en el mensaje"() {
        when:
        cliente().leer("/crm/v3/objects/tickets/500?properties=x")

        then:
        FalloHubspot f = thrown()
        f.estado == 500
        !f.message.contains("detalle interno")
        !f.message.contains("tok-1")
        !f.message.contains("properties")
    }

    def "sin servidor → FalloHubspot sin código"() {
        given:
        int puerto = servidor.address.port
        servidor.stop(0); detenido = true

        when:
        new ClienteHubspotHttp("http://127.0.0.1:" + puerto, "tok-1", 500).leer("/crm/v3/owners/1")

        then:
        FalloHubspot f = thrown()
        f.estado == null
    }
}
