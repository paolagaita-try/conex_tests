package co.trycore.preventa.conectores

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer

/**
 * HubSpot simulado para las pruebas (com.sun.net.httpserver, sin red real): responde según una tabla
 * «MÉTODO /ruta» -> [status, cuerpo] y guarda cada petición (método, ruta, cabeceras, cuerpo en bytes).
 */
class ServidorSimulado {

    static class Peticion {
        String metodo
        String ruta
        Map<String, List<String>> cabeceras
        byte[] cuerpo

        String cabecera(String n) { cabeceras.find { it.key?.equalsIgnoreCase(n) }?.value?.first() }

        String texto() { new String(cuerpo, 'UTF-8') }
    }

    final List<Peticion> peticiones = Collections.synchronizedList([])
    final Map<String, List> respuestas = [:]
    private HttpServer servidor

    ServidorSimulado responder(String metodoRuta, int status, String cuerpo) {
        respuestas[metodoRuta] = [status, cuerpo]
        return this
    }

    String iniciar() {
        servidor = HttpServer.create(new InetSocketAddress('127.0.0.1', 0), 0)
        servidor.createContext('/') { HttpExchange ex ->
            def p = new Peticion(metodo: ex.requestMethod, ruta: ex.requestURI.path,
                    cabeceras: new LinkedHashMap(ex.requestHeaders), cuerpo: ex.requestBody.bytes)
            peticiones << p
            def r = respuestas["${p.metodo} ${p.ruta}".toString()] ?: [404, '{"error":"sin ruta"}']
            byte[] datos = r[1].toString().getBytes('UTF-8')
            ex.responseHeaders.add('Content-Type', 'application/json')
            ex.sendResponseHeaders((int) r[0], datos.length)
            ex.responseBody.withStream { it.write(datos) }
        }
        servidor.start()
        return "http://127.0.0.1:${servidor.address.port}/hubspot"
    }

    void detener() { servidor?.stop(0) }
}
