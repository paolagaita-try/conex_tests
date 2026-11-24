package co.trycore.preventa.conectores

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import java.util.function.Supplier

/**
 * Cliente HTTP mínimo hacia HubSpot (REST nativo), sobre java.net.http.HttpClient (JDK 17): soporta GET, POST, PATCH
 * y POST multipart/form-data (Files API). El token de la Private App se lee de la variable de entorno
 * HUBSPOT_PRIVATE_APP_TOKEN y viaja como «Authorization: Bearer …»; nunca es una entrada del conector ni va al repo.
 * En Local, urlBase apunta al mock (mock.json); contra HubSpot real nunca se ejecuta sin autorización.
 *
 * Un código no 2xx lanza {@link HubspotHttpException} con el status y el cuerpo truncado; el mensaje nunca incluye
 * el token (solo método y URL, que no lo llevan).
 */
class Http {

    static final String VARIABLE_TOKEN = 'HUBSPOT_PRIVATE_APP_TOKEN'
    static final int MAX_CUERPO_ERROR = 500

    private static final HttpClient CLIENTE = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15)).build()

    /** Fuente del token. En producción, la variable de entorno; las pruebas la sustituyen (no se puede fijar env). */
    static Supplier<String> fuenteToken = { System.getenv(VARIABLE_TOKEN) } as Supplier<String>

    static String token() {
        String t = fuenteToken.get()
        return (t == null) ? '' : t.trim()
    }

    static String get(String url) { enviar('GET', url, null) }

    static String post(String url, String cuerpoJson) { enviar('POST', url, cuerpoJson) }

    static String patch(String url, String cuerpoJson) { enviar('PATCH', url, cuerpoJson) }

    private static String enviar(String metodo, String url, String cuerpoJson) {
        def cuerpo = (cuerpoJson == null) ? HttpRequest.BodyPublishers.noBody()
                                          : HttpRequest.BodyPublishers.ofString(cuerpoJson)
        def b = base(url).method(metodo, cuerpo)
        if (cuerpoJson != null) {
            b.header('Content-Type', 'application/json')
        }
        return ejecutar(b, metodo, url)
    }

    /**
     * POST multipart/form-data. partes: lista de mapas {nombre, valor (String)} o {nombre, nombreArchivo, mime,
     * contenido (byte[])}.
     */
    static String postMultipart(String url, List<Map> partes) {
        String frontera = 'preventa-' + UUID.randomUUID().toString().replace('-', '')
        def salida = new ByteArrayOutputStream()
        def escribir = { String s -> salida.write(s.getBytes('UTF-8')) }
        partes.each { Map p ->
            escribir("--${frontera}\r\n")
            if (p.contenido != null) {
                String nombreArchivo = p.nombreArchivo.toString().replace('"', '')
                escribir("Content-Disposition: form-data; name=\"${p.nombre}\"; filename=\"${nombreArchivo}\"\r\n")
                escribir("Content-Type: ${p.mime ?: 'application/octet-stream'}\r\n\r\n")
                salida.write((byte[]) p.contenido)
            } else {
                escribir("Content-Disposition: form-data; name=\"${p.nombre}\"\r\n\r\n")
                escribir(p.valor.toString())
            }
            escribir('\r\n')
        }
        escribir("--${frontera}--\r\n")
        def b = base(url)
                .header('Content-Type', 'multipart/form-data; boundary=' + frontera)
                .POST(HttpRequest.BodyPublishers.ofByteArray(salida.toByteArray()))
        return ejecutar(b, 'POST', url)
    }

    private static HttpRequest.Builder base(String url) {
        def b = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(30))
                .header('Accept', 'application/json')
        String t = token()
        if (!t.isEmpty()) {
            b.header('Authorization', 'Bearer ' + t)
        }
        return b
    }

    private static String ejecutar(HttpRequest.Builder b, String metodo, String url) {
        HttpResponse<String> resp = CLIENTE.send(b.build(), HttpResponse.BodyHandlers.ofString())
        int codigo = resp.statusCode()
        if (codigo < 200 || codigo >= 300) {
            throw new HubspotHttpException(codigo, metodo, url, truncar(resp.body()))
        }
        return resp.body()
    }

    static String truncar(String s) {
        if (s == null) return ''
        String limpio = s
        String t = token()
        if (!t.isEmpty()) {
            limpio = limpio.replace(t, '***')   // defensa: nunca reflejar el token aunque el servidor lo devuelva
        }
        return limpio.length() <= MAX_CUERPO_ERROR ? limpio : limpio.substring(0, MAX_CUERPO_ERROR) + '…'
    }
}

/** Respuesta no 2xx de HubSpot: status y cuerpo ya truncado y sin token. */
class HubspotHttpException extends RuntimeException {
    final int status

    HubspotHttpException(int status, String metodo, String url, String cuerpoTruncado) {
        super("HTTP ${status} de ${metodo} ${url}: ${cuerpoTruncado}")
        this.status = status
    }
}
