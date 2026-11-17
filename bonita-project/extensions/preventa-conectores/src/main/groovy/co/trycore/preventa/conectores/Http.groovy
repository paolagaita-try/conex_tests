package co.trycore.preventa.conectores

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

/**
 * Cliente HTTP mínimo hacia HubSpot (REST nativo), sobre java.net.http.HttpClient (JDK 17): soporta GET, POST y PATCH
 * nativos. El token de la Private App se lee de la variable de entorno HUBSPOT_PRIVATE_APP_TOKEN y viaja como
 * «Authorization: Bearer …»; nunca es una entrada del conector ni va al repo. En Local, urlBase apunta al mock
 * (mock.json); contra HubSpot real nunca se ejecuta sin autorización.
 */
class Http {

    private static final HttpClient CLIENTE = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15)).build()

    static String token() {
        String t = System.getenv('HUBSPOT_PRIVATE_APP_TOKEN')
        return (t == null) ? '' : t.trim()
    }

    static String get(String url) { enviar('GET', url, null) }

    static String post(String url, String cuerpoJson) { enviar('POST', url, cuerpoJson) }

    static String patch(String url, String cuerpoJson) { enviar('PATCH', url, cuerpoJson) }

    private static String enviar(String metodo, String url, String cuerpoJson) {
        def cuerpo = (cuerpoJson == null) ? HttpRequest.BodyPublishers.noBody()
                                          : HttpRequest.BodyPublishers.ofString(cuerpoJson)
        def b = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(15))
                .header('Accept', 'application/json')
                .method(metodo, cuerpo)
        if (cuerpoJson != null) {
            b.header('Content-Type', 'application/json')
        }
        String t = token()
        if (!t.isEmpty()) {
            b.header('Authorization', 'Bearer ' + t)
        }
        HttpResponse<String> resp = CLIENTE.send(b.build(), HttpResponse.BodyHandlers.ofString())
        int codigo = resp.statusCode()
        if (codigo < 200 || codigo >= 300) {
            throw new RuntimeException("HTTP ${codigo} de ${metodo} ${url}: ${resp.body()}")
        }
        return resp.body()
    }
}
